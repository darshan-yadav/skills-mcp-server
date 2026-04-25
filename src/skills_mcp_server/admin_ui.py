"""Browser-based admin UI for local skill management."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import html
import io
import mimetypes
import os
import shutil
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote, urlencode

from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Route
from yaml import YAMLError, safe_dump, safe_load

from skills_mcp_server.config import Config, LocalSourceConfig
from skills_mcp_server.registry import SkillRegistry
from skills_mcp_server.sources.local import _parse_skill_md

_COOKIE_NAME = "skills_admin_session"
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class LocalEditableSource:
    name: str
    root: Path


@dataclass(frozen=True, slots=True)
class BundleSummary:
    source_name: str
    source_kind: str
    path_display: str
    name: str
    description: str
    resource_count: int
    editable: bool
    updated_at: str
    edit_href: str | None


def create_admin_routes(*, registry: SkillRegistry, config: Config) -> list[Route]:
    """Build admin UI routes when enabled in config."""

    if not config.admin_ui or not config.admin_ui.enabled:
        return []

    admin_config = config.admin_ui
    local_sources = _get_local_sources(config)

    def _require_session(request: Request) -> RedirectResponse | None:
        if _has_valid_session(request, admin_config.username or "", admin_config.session_secret or ""):
            return None
        login_url = "/admin/login"
        next_url = request.url.path
        if request.url.query:
            next_url += f"?{request.url.query}"
        return RedirectResponse(f"{login_url}?{urlencode({'next': next_url})}", status_code=303)

    async def _reload_source(source_name: str) -> None:
        await asyncio.get_running_loop().run_in_executor(None, registry.reload_source, source_name)

    async def login_page(request: Request) -> Response:
        if _has_valid_session(request, admin_config.username or "", admin_config.session_secret or ""):
            return RedirectResponse("/admin", status_code=303)
        notice = request.query_params.get("notice")
        next_url = request.query_params.get("next", "/admin")
        return HTMLResponse(
            _render_login_page(
                notice=notice,
                next_url=next_url,
            )
        )

    async def login_submit(request: Request) -> Response:
        form = await request.form()
        username = str(form.get("username", "")).strip()
        password = str(form.get("password", ""))
        next_url = str(form.get("next", "/admin")) or "/admin"

        if not _credentials_match(
            username=username,
            password=password,
            expected_username=admin_config.username or "",
            expected_password=admin_config.password or "",
        ):
            return HTMLResponse(
                _render_login_page(
                    notice="Login failed. Check the admin username and password.",
                    next_url=next_url,
                ),
                status_code=401,
            )

        response = RedirectResponse(_safe_admin_redirect(next_url), status_code=303)
        _set_session_cookie(response, username, admin_config.session_secret or "", admin_config.session_ttl_seconds)
        return response

    async def logout_submit(request: Request) -> Response:
        redirect = RedirectResponse("/admin/login?notice=Signed+out", status_code=303)
        redirect.delete_cookie(_COOKIE_NAME, path="/")
        return redirect

    async def dashboard(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect

        notice = request.query_params.get("notice")
        bundle_summaries = _collect_bundle_summaries(registry, local_sources)
        source_cards = _build_source_cards(config, bundle_summaries, local_sources)
        return HTMLResponse(
            _render_admin_page(
                title="Skills Control Room",
                eyebrow="Admin Console",
                heading="Manage local skills with a safe, source-aware editor.",
                subheading=(
                    "Editable local sources can create, update, upload, and remove bundles. "
                    "Git-backed sources remain visible but read-only."
                ),
                notice=notice,
                current_nav="dashboard",
                content=_render_dashboard_content(bundle_summaries, source_cards, local_sources),
            )
        )

    async def new_skill_page(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect
        return HTMLResponse(
            _render_admin_page(
                title="Create Skill",
                eyebrow="Admin Console",
                heading="Create a new local skill bundle.",
                subheading=(
                    "Use a path that sits inside a writable local source. "
                    "Nested bundle paths up to three levels are supported."
                ),
                current_nav="new-skill",
                content=_render_new_skill_form(local_sources=local_sources),
            )
        )

    async def new_skill_submit(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect

        form = await request.form()
        values = {
            "source_name": str(form.get("source_name", "")).strip(),
            "relative_path": str(form.get("relative_path", "")).strip(),
            "name": str(form.get("name", "")).strip(),
            "description": str(form.get("description", "")).strip(),
            "body": str(form.get("body", "")).rstrip(),
            "extra_yaml": str(form.get("extra_yaml", "")).strip(),
        }

        try:
            source = _require_local_source(local_sources, values["source_name"])
            bundle_rel = _validate_bundle_relative_path(values["relative_path"])
            bundle_path = _resolve_within(source.root, bundle_rel, must_exist=False)
            if bundle_path.exists():
                raise ValueError(f"Bundle path already exists: {bundle_rel.as_posix()}")
            skill_md = _build_skill_md(
                name=values["name"],
                description=values["description"],
                body=values["body"],
                extra_yaml=values["extra_yaml"],
            )
            _parse_skill_md(skill_md, bundle_path / "SKILL.md")
            bundle_path.mkdir(parents=True, exist_ok=False)
            (bundle_path / "SKILL.md").write_text(skill_md, encoding="utf-8")
            await _reload_source(source.name)
            return RedirectResponse(
                _editor_href(source.name, bundle_rel.as_posix(), notice="Skill created."),
                status_code=303,
            )
        except (ValueError, YAMLError) as exc:
            return HTMLResponse(
                _render_admin_page(
                    title="Create Skill",
                    eyebrow="Admin Console",
                    heading="Create a new local skill bundle.",
                    subheading="Fix the validation issue below and try again.",
                    notice=str(exc),
                    current_nav="new-skill",
                    content=_render_new_skill_form(local_sources=local_sources, values=values),
                ),
                status_code=400,
            )

    async def bundle_zip_upload(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect

        source_name = request.path_params["source_name"]
        try:
            source = _require_local_source(local_sources, source_name)
            form = await request.form()
            upload = form.get("bundle_zip")
            if not isinstance(upload, UploadFile) or not upload.filename:
                raise ValueError("Choose a .zip file containing exactly one skill bundle.")
            if not upload.filename.lower().endswith(".zip"):
                raise ValueError("Bundle upload expects a .zip archive.")
            payload = await upload.read()
            if len(payload) > _MAX_UPLOAD_BYTES:
                raise ValueError("Bundle upload exceeds the 10 MB limit.")
            bundle_rel = _extract_bundle_zip(source.root, payload)
            await _reload_source(source.name)
            return RedirectResponse(
                _editor_href(source.name, bundle_rel.as_posix(), notice="Bundle uploaded."),
                status_code=303,
            )
        except (ValueError, zipfile.BadZipFile, OSError) as exc:
            return RedirectResponse(
                f"/admin?{urlencode({'notice': str(exc)})}",
                status_code=303,
            )

    async def bundle_file_upload(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect

        source_name = request.path_params["source_name"]
        bundle_path_raw = request.path_params["bundle_path"]
        try:
            source = _require_local_source(local_sources, source_name)
            bundle_rel = _validate_bundle_relative_path(bundle_path_raw)
            bundle_dir = _require_existing_bundle(source.root, bundle_rel)
            form = await request.form()
            upload = form.get("asset")
            subdir_raw = str(form.get("target_subdir", "")).strip()
            if not isinstance(upload, UploadFile) or not upload.filename:
                raise ValueError("Choose a file to upload into the bundle.")
            payload = await upload.read()
            if len(payload) > _MAX_UPLOAD_BYTES:
                raise ValueError("Uploaded file exceeds the 10 MB limit.")
            target_dir = bundle_dir
            if subdir_raw:
                target_dir = _resolve_within(bundle_dir, _validate_bundle_file_path(subdir_raw), must_exist=False)
                target_dir.mkdir(parents=True, exist_ok=True)
            upload_name = _validate_bundle_file_path(Path(upload.filename).name)
            target_path = _resolve_within(target_dir, upload_name, must_exist=False)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(payload)
            await _reload_source(source.name)
            return RedirectResponse(
                _editor_href(source.name, bundle_rel.as_posix(), notice=f"Uploaded {upload.filename}."),
                status_code=303,
            )
        except (ValueError, OSError) as exc:
            return RedirectResponse(
                _editor_href(source_name, bundle_path_raw, notice=str(exc)),
                status_code=303,
            )

    async def bundle_file_create(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect

        source_name = request.path_params["source_name"]
        bundle_path_raw = request.path_params["bundle_path"]
        try:
            source = _require_local_source(local_sources, source_name)
            bundle_rel = _validate_bundle_relative_path(bundle_path_raw)
            bundle_dir = _require_existing_bundle(source.root, bundle_rel)
            form = await request.form()
            file_path = _validate_bundle_file_path(str(form.get("file_path", "")).strip())
            target_path = _resolve_within(bundle_dir, file_path, must_exist=False)
            if target_path.exists():
                raise ValueError(f"File already exists: {file_path.as_posix()}")
            content = str(form.get("content", ""))
            if file_path.name == "SKILL.md":
                _parse_skill_md(content, target_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            await _reload_source(source.name)
            return RedirectResponse(
                _editor_href(
                    source.name,
                    bundle_rel.as_posix(),
                    file_path=file_path.as_posix(),
                    notice=f"Created {file_path.as_posix()}.",
                ),
                status_code=303,
            )
        except (ValueError, OSError) as exc:
            return RedirectResponse(
                _editor_href(source_name, bundle_path_raw, notice=str(exc)),
                status_code=303,
            )

    async def bundle_file_delete(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect

        source_name = request.path_params["source_name"]
        bundle_path_raw = request.path_params["bundle_path"]
        try:
            source = _require_local_source(local_sources, source_name)
            bundle_rel = _validate_bundle_relative_path(bundle_path_raw)
            bundle_dir = _require_existing_bundle(source.root, bundle_rel)
            form = await request.form()
            file_path = _validate_bundle_file_path(str(form.get("target_path", "")).strip())
            if file_path.as_posix() == "SKILL.md":
                raise ValueError("SKILL.md cannot be deleted from the file list; delete the whole bundle instead.")
            target_path = _resolve_within(bundle_dir, file_path, must_exist=True)
            if target_path.is_dir():
                raise ValueError("Only files can be deleted from the file list.")
            target_path.unlink()
            await _reload_source(source.name)
            return RedirectResponse(
                _editor_href(source.name, bundle_rel.as_posix(), notice=f"Deleted {file_path.as_posix()}."),
                status_code=303,
            )
        except (ValueError, OSError) as exc:
            return RedirectResponse(
                _editor_href(source_name, bundle_path_raw, notice=str(exc)),
                status_code=303,
            )

    async def bundle_delete(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect

        source_name = request.path_params["source_name"]
        bundle_path_raw = request.path_params["bundle_path"]
        try:
            source = _require_local_source(local_sources, source_name)
            bundle_rel = _validate_bundle_relative_path(bundle_path_raw)
            bundle_dir = _require_existing_bundle(source.root, bundle_rel)
            shutil.rmtree(bundle_dir)
            await _reload_source(source.name)
            return RedirectResponse("/admin?notice=Bundle+deleted", status_code=303)
        except (ValueError, OSError) as exc:
            return RedirectResponse(
                _editor_href(source_name, bundle_path_raw, notice=str(exc)),
                status_code=303,
            )

    async def raw_file(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect

        try:
            source_name = request.path_params["source_name"]
            bundle_path_raw = request.path_params["bundle_path"]
            file_raw = request.query_params.get("path", "SKILL.md")
            source = _require_local_source(local_sources, source_name)
            bundle_rel = _validate_bundle_relative_path(bundle_path_raw)
            bundle_dir = _require_existing_bundle(source.root, bundle_rel)
            file_rel = _validate_bundle_file_path(file_raw)
            target_path = _resolve_within(bundle_dir, file_rel, must_exist=True)
            content = target_path.read_bytes()
            media_type, _ = mimetypes.guess_type(target_path.name)
            return Response(content, media_type=media_type or "application/octet-stream")
        except (ValueError, OSError) as exc:
            return RedirectResponse("/admin?" + urlencode({"notice": str(exc)}), status_code=303)

    async def bundle_editor(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect

        try:
            source_name = request.path_params["source_name"]
            bundle_path_raw = request.path_params["bundle_path"]
            source = _require_local_source(local_sources, source_name)
            bundle_rel = _validate_bundle_relative_path(bundle_path_raw)
            selected_file = request.query_params.get("file", "SKILL.md")
            state = _load_bundle_state(source.root, source.name, bundle_rel, selected_file)
            return HTMLResponse(
                _render_admin_page(
                    title=f"Edit {state['bundle_path_display']}",
                    eyebrow="Admin Console",
                    heading=state["manifest_name"] or state["bundle_path_display"],
                    subheading=state["manifest_description"]
                    or "Edit the bundle files and supporting assets for this skill.",
                    notice=request.query_params.get("notice"),
                    current_nav="editor",
                    content=_render_editor_content(state),
                )
            )
        except (ValueError, OSError) as exc:
            return RedirectResponse("/admin?" + urlencode({"notice": str(exc)}), status_code=303)

    async def bundle_save(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect

        source_name = request.path_params["source_name"]
        bundle_path_raw = request.path_params["bundle_path"]
        try:
            source = _require_local_source(local_sources, source_name)
            bundle_rel = _validate_bundle_relative_path(bundle_path_raw)
            bundle_dir = _require_existing_bundle(source.root, bundle_rel)
            form = await request.form()
            file_rel = _validate_bundle_file_path(str(form.get("file_path", "SKILL.md")))
            target_path = _resolve_within(bundle_dir, file_rel, must_exist=True)
            content = str(form.get("content", ""))
            if file_rel.as_posix() == "SKILL.md":
                _parse_skill_md(content, target_path)
            else:
                # Enforce UTF-8 text editing for non-SKILL files.
                content.encode("utf-8")
            target_path.write_text(content, encoding="utf-8")
            await _reload_source(source.name)
            return RedirectResponse(
                _editor_href(
                    source.name,
                    bundle_rel.as_posix(),
                    file_path=file_rel.as_posix(),
                    notice=f"Saved {file_rel.as_posix()}.",
                ),
                status_code=303,
            )
        except (ValueError, OSError) as exc:
            return RedirectResponse(
                _editor_href(source_name, bundle_path_raw, notice=str(exc)),
                status_code=303,
            )

    return [
        Route("/admin/login", endpoint=login_page, methods=["GET"]),
        Route("/admin/login", endpoint=login_submit, methods=["POST"]),
        Route("/admin/logout", endpoint=logout_submit, methods=["POST"]),
        Route("/admin", endpoint=dashboard, methods=["GET"]),
        Route("/admin/new", endpoint=new_skill_page, methods=["GET"]),
        Route("/admin/new", endpoint=new_skill_submit, methods=["POST"]),
        Route("/admin/sources/{source_name:str}/uploads/bundle", endpoint=bundle_zip_upload, methods=["POST"]),
        Route(
            "/admin/sources/{source_name:str}/bundles/{bundle_path:path}/files/upload",
            endpoint=bundle_file_upload,
            methods=["POST"],
        ),
        Route(
            "/admin/sources/{source_name:str}/bundles/{bundle_path:path}/files/create",
            endpoint=bundle_file_create,
            methods=["POST"],
        ),
        Route(
            "/admin/sources/{source_name:str}/bundles/{bundle_path:path}/files/delete",
            endpoint=bundle_file_delete,
            methods=["POST"],
        ),
        Route(
            "/admin/sources/{source_name:str}/bundles/{bundle_path:path}/delete",
            endpoint=bundle_delete,
            methods=["POST"],
        ),
        Route(
            "/admin/sources/{source_name:str}/bundles/{bundle_path:path}/files/raw",
            endpoint=raw_file,
            methods=["GET"],
        ),
        Route("/admin/sources/{source_name:str}/bundles/{bundle_path:path}", endpoint=bundle_editor, methods=["GET"]),
        Route("/admin/sources/{source_name:str}/bundles/{bundle_path:path}", endpoint=bundle_save, methods=["POST"]),
    ]


def _get_local_sources(config: Config) -> dict[str, LocalEditableSource]:
    return {
        source.name: LocalEditableSource(name=source.name, root=source.path)
        for source in config.sources
        if isinstance(source, LocalSourceConfig)
    }


def _credentials_match(*, username: str, password: str, expected_username: str, expected_password: str) -> bool:
    return hmac.compare_digest(username, expected_username) and hmac.compare_digest(password, expected_password)


def _set_session_cookie(response: Response, username: str, secret: str, ttl_seconds: int) -> None:
    expiry = int(time.time()) + ttl_seconds
    payload = f"{username}:{expiry}"
    signature = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode("ascii")
    response.set_cookie(
        _COOKIE_NAME,
        token,
        max_age=ttl_seconds,
        httponly=True,
        samesite="lax",
        path="/",
    )


def _has_valid_session(request: Request, expected_username: str, secret: str) -> bool:
    raw = request.cookies.get(_COOKIE_NAME)
    if not raw:
        return False
    try:
        decoded = base64.urlsafe_b64decode(raw.encode("ascii")).decode("utf-8")
        username, expiry_raw, signature = decoded.split(":", 2)
        expiry = int(expiry_raw)
    except (ValueError, UnicodeDecodeError):
        return False

    if expiry < int(time.time()):
        return False
    if not hmac.compare_digest(username, expected_username):
        return False

    payload = f"{username}:{expiry}"
    expected_signature = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected_signature)


def _safe_admin_redirect(next_url: str) -> str:
    if not next_url.startswith("/") or next_url.startswith("//"):
        return "/admin"
    return next_url


def _validate_bundle_relative_path(raw: str) -> Path:
    rel = _validate_relative_path(raw, label="Bundle path")
    if len(rel.parts) > 3:
        raise ValueError("Bundle path may be at most three directories deep.")
    return rel


def _validate_bundle_file_path(raw: str) -> Path:
    rel = _validate_relative_path(raw, label="File path")
    if len(rel.parts) > 16:
        raise ValueError("File path may be at most sixteen segments deep.")
    return rel


def _validate_relative_path(raw: str, *, label: str) -> Path:
    value = raw.strip().strip("/")
    if not value:
        raise ValueError(f"{label} is required.")
    pure = PurePosixPath(value)
    if pure.is_absolute():
        raise ValueError(f"{label} must be relative.")
    parts = [part for part in pure.parts if part]
    if not parts:
        raise ValueError(f"{label} is required.")
    for part in parts:
        if part in {".", ".."}:
            raise ValueError(f"{label} cannot contain '.' or '..'.")
        if any(ord(ch) < 32 for ch in part):
            raise ValueError(f"{label} contains control characters.")
    return Path(*parts)


def _resolve_within(root: Path, rel: Path, *, must_exist: bool) -> Path:
    candidate = (root / rel).resolve(strict=must_exist)
    root_resolved = root.resolve(strict=True)
    root_str = str(root_resolved)
    candidate_str = str(candidate)
    if candidate != root_resolved and not candidate_str.startswith(root_str + os.sep):
        raise ValueError("Path escapes the configured local source.")
    return candidate


def _require_local_source(local_sources: dict[str, LocalEditableSource], source_name: str) -> LocalEditableSource:
    source = local_sources.get(source_name)
    if not source:
        raise ValueError(f"Local source not found or not editable: {source_name}")
    return source


def _require_existing_bundle(root: Path, bundle_rel: Path) -> Path:
    bundle_dir = _resolve_within(root, bundle_rel, must_exist=True)
    if not bundle_dir.is_dir():
        raise ValueError("Bundle path is not a directory.")
    skill_md = bundle_dir / "SKILL.md"
    if not skill_md.exists():
        raise ValueError("Bundle does not contain SKILL.md.")
    return bundle_dir


def _build_skill_md(*, name: str, description: str, body: str, extra_yaml: str) -> str:
    if not name.strip():
        raise ValueError("Skill name is required.")
    if not description.strip():
        raise ValueError("Skill description is required.")

    frontmatter: dict[str, Any] = {
        "name": name.strip(),
        "description": description.strip(),
    }
    if extra_yaml:
        parsed = safe_load(extra_yaml)
        if parsed is None:
            parsed = {}
        if not isinstance(parsed, dict):
            raise ValueError("Extra frontmatter must be a YAML mapping.")
        for key, value in parsed.items():
            if key in {"name", "description"}:
                raise ValueError("Extra frontmatter cannot redefine name or description.")
            frontmatter[key] = value

    frontmatter_text = safe_dump(frontmatter, sort_keys=False).strip()
    body_text = body.rstrip() or "# New skill\n\nDescribe how and when to use this skill."
    return f"---\n{frontmatter_text}\n---\n\n{body_text}\n"


def _extract_bundle_zip(root: Path, payload: bytes) -> Path:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        entries = [
            PurePosixPath(name)
            for name in archive.namelist()
            if name and not name.endswith("/")
        ]
        if not entries:
            raise ValueError("Archive is empty.")
        for entry in entries:
            if entry.is_absolute() or any(part in {"", ".", ".."} for part in entry.parts):
                raise ValueError("Archive contains unsafe paths.")

        skill_md_entries = [entry for entry in entries if entry.name == "SKILL.md"]
        if len(skill_md_entries) != 1:
            raise ValueError("Archive must contain exactly one SKILL.md file.")

        bundle_rel = Path(*skill_md_entries[0].parent.parts)
        if not bundle_rel.parts:
            raise ValueError("Archive must wrap the bundle in a directory.")
        bundle_rel = _validate_bundle_relative_path(bundle_rel.as_posix())

        for entry in entries:
            entry_prefix = entry.parts[: len(bundle_rel.parts)]
            if entry_prefix != bundle_rel.parts:
                raise ValueError("Archive must contain exactly one bundle subtree.")

        target_bundle = _resolve_within(root, bundle_rel, must_exist=False)
        if target_bundle.exists():
            raise ValueError(f"Bundle path already exists: {bundle_rel.as_posix()}")

        for entry in entries:
            target_path = _resolve_within(root, Path(*entry.parts), must_exist=False)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(archive.read(entry.as_posix()))

        _parse_skill_md((target_bundle / "SKILL.md").read_text(encoding="utf-8"), target_bundle / "SKILL.md")
        return bundle_rel


def _collect_bundle_summaries(
    registry: SkillRegistry,
    local_sources: dict[str, LocalEditableSource],
) -> list[BundleSummary]:
    summaries: list[BundleSummary] = []
    for bundle in registry.iter_bundles():
        editable_source = local_sources.get(bundle.source_name)
        updated_at = _format_timestamp((bundle.bundle_path / "SKILL.md").stat().st_mtime)
        if editable_source:
            path_display = bundle.bundle_path.relative_to(editable_source.root).as_posix()
            edit_href = _editor_href(bundle.source_name, path_display)
            editable = True
            source_kind = "local"
        else:
            path_display = bundle.slug
            edit_href = None
            editable = False
            source_kind = "git"
        summaries.append(
            BundleSummary(
                source_name=bundle.source_name,
                source_kind=source_kind,
                path_display=path_display,
                name=bundle.manifest.name,
                description=bundle.manifest.description,
                resource_count=len(bundle.resources),
                editable=editable,
                updated_at=updated_at,
                edit_href=edit_href,
            )
        )

    return sorted(summaries, key=lambda item: (item.source_name, item.name.lower(), item.path_display))


def _build_source_cards(
    config: Config,
    bundles: list[BundleSummary],
    local_sources: dict[str, LocalEditableSource],
) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for bundle in bundles:
        counts[bundle.source_name] = counts.get(bundle.source_name, 0) + 1

    cards: list[dict[str, Any]] = []
    for source in config.sources:
        source_kind = "local" if isinstance(source, LocalSourceConfig) else "git"
        cards.append(
            {
                "name": source.name,
                "kind": source_kind,
                "editable": source.name in local_sources,
                "path": source.path.as_posix() if isinstance(source, LocalSourceConfig) else getattr(source, "url", ""),
                "count": counts.get(source.name, 0),
            }
        )
    return cards


def _load_bundle_state(root: Path, source_name: str, bundle_rel: Path, current_file_raw: str) -> dict[str, Any]:
    bundle_dir = _require_existing_bundle(root, bundle_rel)
    skill_text = (bundle_dir / "SKILL.md").read_text(encoding="utf-8")
    manifest, _body = _parse_skill_md(skill_text, bundle_dir / "SKILL.md")
    current_file = _validate_bundle_file_path(current_file_raw)
    current_path = _resolve_within(bundle_dir, current_file, must_exist=True)
    current_bytes = current_path.read_bytes()
    try:
        current_text = current_bytes.decode("utf-8")
        editable_text = True
    except UnicodeDecodeError:
        current_text = ""
        editable_text = False

    files = []
    for path in sorted(bundle_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(bundle_dir).as_posix()
        is_binary = False
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            is_binary = True
        files.append(
            {
                "rel": rel,
                "size": _format_bytes(path.stat().st_size),
                "editable": not is_binary,
                "download_href": _raw_file_href(source_name, bundle_rel.as_posix(), rel),
                "open_href": _editor_href(source_name, bundle_rel.as_posix(), file_path=rel),
            }
        )

    return {
        "source_name": source_name,
        "bundle_rel": bundle_rel.as_posix(),
        "bundle_path_display": bundle_rel.as_posix(),
        "bundle_dir": bundle_dir.as_posix(),
        "manifest_name": manifest.name,
        "manifest_description": manifest.description,
        "files": files,
        "current_file": current_file.as_posix(),
        "current_file_text": current_text,
        "current_file_editable": editable_text,
        "current_file_size": _format_bytes(current_path.stat().st_size),
        "current_file_updated": _format_timestamp(current_path.stat().st_mtime),
    }


def _editor_href(source_name: str, bundle_path: str, *, file_path: str | None = None, notice: str | None = None) -> str:
    base = f"/admin/sources/{quote(source_name, safe='')}/bundles/{quote(bundle_path, safe='/')}"
    query: dict[str, str] = {}
    if file_path:
        query["file"] = file_path
    if notice:
        query["notice"] = notice
    if query:
        return f"{base}?{urlencode(query)}"
    return base


def _raw_file_href(source_name: str, bundle_path: str, file_path: str) -> str:
    return (
        f"/admin/sources/{quote(source_name, safe='')}/bundles/{quote(bundle_path, safe='/')}/files/raw"
        f"?{urlencode({'path': file_path})}"
    )


def _format_timestamp(timestamp: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp))


def _format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _render_login_page(*, notice: str | None, next_url: str) -> str:
    login_lede = (
        "Authenticated admins can create, edit, upload, and remove "
        "bundles from writable local sources."
    )
    content = f"""
    <section class="login-shell">
      <div class="login-card">
        <div class="eyebrow">Admin Console</div>
        <h1>Sign in to manage skills</h1>
        <p class="lede">{login_lede}</p>
        {_render_notice(notice)}
        <form method="post" action="/admin/login" class="stack">
          <input type="hidden" name="next" value="{_escape(next_url)}" />
          <label class="field">
            <span>Username</span>
            <input type="text" name="username" autocomplete="username" required />
          </label>
          <label class="field">
            <span>Password</span>
            <input type="password" name="password" autocomplete="current-password" required />
          </label>
          <button class="button button-primary" type="submit">Enter control room</button>
        </form>
      </div>
    </section>
    """
    return _render_document("Admin Login", content, login_mode=True)


def _render_dashboard_content(
    bundles: list[BundleSummary],
    source_cards: list[dict[str, Any]],
    local_sources: dict[str, LocalEditableSource],
) -> str:
    local_count = sum(1 for bundle in bundles if bundle.editable)
    readonly_count = len(bundles) - local_count
    source_markup = []
    for card in source_cards:
        controls = ""
        if card["editable"]:
            upload_action = f"/admin/sources/{quote(card['name'], safe='')}/uploads/bundle"
            controls = f"""
            <form
              method="post"
              action="{_escape(upload_action)}"
              enctype="multipart/form-data"
              class="inline-upload"
            >
              <label class="field compact">
                <span>Upload bundle (.zip)</span>
                <input type="file" name="bundle_zip" accept=".zip" required />
              </label>
              <button class="button button-secondary" type="submit">Upload</button>
            </form>
            """
        source_markup.append(
            f"""
            <article class="source-card">
              <div class="card-chip">{_escape(card['kind'])}</div>
              <h3>{_escape(card['name'])}</h3>
              <p class="meta">{_escape(card['path'])}</p>
              <div class="metric-row">
                <div><strong>{card['count']}</strong><span>Loaded skills</span></div>
                <div><strong>{"Editable" if card['editable'] else "Read-only"}</strong><span>Access mode</span></div>
              </div>
              {controls}
            </article>
            """
        )

    bundle_markup = []
    for bundle in bundles:
        search_text = " ".join(
            [
                bundle.name,
                bundle.description,
                bundle.path_display,
                bundle.source_name,
            ]
        ).lower()
        action = (
            f'<a class="button button-secondary" href="{_escape(bundle.edit_href or "#")}">Open editor</a>'
            if bundle.editable
            else '<span class="readonly-pill">Git source · read-only</span>'
        )
        bundle_markup.append(
            f"""
            <article
              class="skill-card"
              data-skill-card
              data-search-text="{_escape(search_text)}"
            >
              <div class="card-chip">{_escape(bundle.source_name)}</div>
              <h3>{_escape(bundle.name)}</h3>
              <p class="lede small">{_escape(bundle.description)}</p>
              <dl class="meta-grid">
                <div><dt>Bundle</dt><dd>{_escape(bundle.path_display)}</dd></div>
                <div><dt>Files</dt><dd>{bundle.resource_count}</dd></div>
                <div><dt>Updated</dt><dd>{_escape(bundle.updated_at)}</dd></div>
                <div><dt>Mode</dt><dd>{'Editable' if bundle.editable else 'Read-only'}</dd></div>
              </dl>
              <div class="action-row">{action}</div>
            </article>
            """
        )

    return f"""
    <section class="hero-metrics">
      <article><strong>{len(bundles)}</strong><span>Total loaded skills</span></article>
      <article><strong>{len(local_sources)}</strong><span>Writable local sources</span></article>
      <article><strong>{local_count}</strong><span>Editable bundles</span></article>
      <article><strong>{readonly_count}</strong><span>Read-only bundles</span></article>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <div class="eyebrow">Sources</div>
          <h2>Where skills come from</h2>
        </div>
        <a class="button button-primary" href="/admin/new">Create a new skill</a>
      </div>
      <div class="source-grid">
        {''.join(source_markup)}
      </div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <div class="eyebrow">Bundles</div>
          <h2>Loaded skills</h2>
        </div>
        <label class="field compact search">
          <span>Filter</span>
          <input type="search" placeholder="Search by name, source, or path" data-skill-filter />
        </label>
      </div>
      <div class="skill-grid">
        {''.join(bundle_markup) or '<p class="empty-state">No skills are currently loaded.</p>'}
      </div>
    </section>
    """


def _render_new_skill_form(
    *,
    local_sources: dict[str, LocalEditableSource],
    values: dict[str, str] | None = None,
) -> str:
    values = values or {}
    options = []
    selected_source = values.get("source_name", "")
    default_body = (
        "# New skill\n\n"
        "Explain when to use this skill, what workflow to follow, "
        "and what outputs to produce."
    )
    for source in local_sources.values():
        selected = " selected" if source.name == selected_source else ""
        option_label = f"{source.name} · {source.root.as_posix()}"
        options.append(
            f'<option value="{_escape(source.name)}"{selected}>{_escape(option_label)}</option>'
        )

    example_extra = "version: 0.1.0\ntags:\n  - admin\n  - internal"
    relative_path_value = _escape(values.get("relative_path", ""))
    name_value = _escape(values.get("name", ""))
    description_value = _escape(values.get("description", ""))
    body_value = _escape(values.get("body", default_body))
    extra_yaml_value = _escape(values.get("extra_yaml", ""))
    return f"""
    <section class="panel narrow">
      <form method="post" action="/admin/new" class="stack">
        <label class="field">
          <span>Local source</span>
          <select name="source_name" required>
            <option value="">Select a local source</option>
            {''.join(options)}
          </select>
        </label>
        <label class="field">
          <span>Bundle path</span>
          <input
            type="text"
            name="relative_path"
            placeholder="roles/new-skill"
            value="{relative_path_value}"
            required
          />
          <small>Relative to the chosen local source. Up to three path segments.</small>
        </label>
        <label class="field">
          <span>Skill name</span>
          <input type="text" name="name" placeholder="new-skill" value="{name_value}" required />
        </label>
        <label class="field">
          <span>Description</span>
          <textarea name="description" rows="3" required>{description_value}</textarea>
        </label>
        <label class="field">
          <span>Body</span>
          <textarea name="body" rows="14">{body_value}</textarea>
        </label>
        <label class="field">
          <span>Extra frontmatter (optional YAML)</span>
          <textarea name="extra_yaml" rows="6" placeholder="{_escape(example_extra)}">{extra_yaml_value}</textarea>
        </label>
        <div class="action-row">
          <button class="button button-primary" type="submit">Create skill</button>
          <a class="button button-secondary" href="/admin">Back to dashboard</a>
        </div>
      </form>
    </section>
    """


def _render_editor_content(state: dict[str, Any]) -> str:
    file_items = []
    for file in state["files"]:
        is_active = " active" if file["rel"] == state["current_file"] else ""
        delete_form = ""
        if file["rel"] != "SKILL.md":
            delete_action = _bundle_action_href(state["source_name"], state["bundle_rel"], "/files/delete")
            delete_form = f"""
            <form
              method="post"
              action="{_escape(delete_action)}"
              data-confirm="Delete {_escape(file['rel'])}?"
            >
              <input type="hidden" name="target_path" value="{_escape(file['rel'])}" />
              <button class="ghost-link danger" type="submit">Delete</button>
            </form>
            """
        file_items.append(
            f"""
            <li class="file-item{is_active}">
              <a href="{_escape(file['open_href'])}">
                <strong>{_escape(file['rel'])}</strong>
                <span>{_escape(file['size'])} · {'text' if file['editable'] else 'binary'}</span>
              </a>
              <div class="file-actions">
                <a class="ghost-link" href="{_escape(file['download_href'])}" target="_blank" rel="noreferrer">
                  Open raw
                </a>
                {delete_form}
              </div>
            </li>
            """
        )

    editor_block = ""
    if state["current_file_editable"]:
        save_action = _bundle_action_href(state["source_name"], state["bundle_rel"], "")
        editor_block = f"""
        <form method="post" action="{_escape(save_action)}" class="stack">
          <input type="hidden" name="file_path" value="{_escape(state['current_file'])}" />
          <div class="panel-header">
            <div>
              <div class="eyebrow">Editor</div>
              <h2>{_escape(state['current_file'])}</h2>
              <p class="meta">
                {_escape(state['current_file_size'])} · Updated {_escape(state['current_file_updated'])}
              </p>
            </div>
            <div class="status-pill" data-dirty-indicator>Saved</div>
          </div>
          <textarea name="content" rows="24" class="code-editor" data-editor-textarea>
{_escape(state['current_file_text'])}</textarea>
          <div class="action-row">
            <button class="button button-primary" type="submit">Save file</button>
            <a class="button button-secondary" href="/admin">Back to dashboard</a>
          </div>
        </form>
        """
    else:
        raw_href = _raw_file_href(state["source_name"], state["bundle_rel"], state["current_file"])
        editor_block = f"""
        <section class="panel">
          <div class="panel-header">
            <div>
              <div class="eyebrow">Binary file</div>
              <h2>{_escape(state['current_file'])}</h2>
              <p class="meta">This file is available for raw download but not inline editing.</p>
            </div>
          </div>
          <div class="action-row">
            <a class="button button-secondary" href="{_escape(raw_href)}" target="_blank" rel="noreferrer">
              Open raw file
            </a>
            <a class="button button-secondary" href="/admin">Back to dashboard</a>
          </div>
        </section>
        """

    delete_bundle_action = _bundle_action_href(state["source_name"], state["bundle_rel"], "/delete")
    upload_action = _bundle_action_href(state["source_name"], state["bundle_rel"], "/files/upload")
    create_action = _bundle_action_href(state["source_name"], state["bundle_rel"], "/files/create")
    return f"""
    <section class="editor-layout">
      <aside class="editor-sidebar">
        <section class="panel">
          <div class="eyebrow">Bundle</div>
          <h2>{_escape(state['bundle_path_display'])}</h2>
          <p class="lede small">Source <strong>{_escape(state['source_name'])}</strong></p>
          <p class="meta">{_escape(state['bundle_dir'])}</p>
          <div class="action-row stacked">
            <a class="button button-secondary" href="/admin">Dashboard</a>
            <form method="post" action="/admin/logout">
              <button class="button button-secondary" type="submit">Sign out</button>
            </form>
            <form
              method="post"
              action="{_escape(delete_bundle_action)}"
              data-confirm="Delete the entire bundle {_escape(state['bundle_path_display'])}? This cannot be undone."
            >
              <button class="button button-danger" type="submit">Delete bundle</button>
            </form>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div>
              <div class="eyebrow">Files</div>
              <h2>Bundle assets</h2>
            </div>
          </div>
          <ul class="file-list">
            {''.join(file_items)}
          </ul>
        </section>

        <section class="panel">
          <div class="eyebrow">Upload</div>
          <h2>Add files</h2>
          <form method="post" action="{_escape(upload_action)}" enctype="multipart/form-data" class="stack">
            <label class="field">
              <span>Bundle file</span>
              <input type="file" name="asset" required />
            </label>
            <label class="field">
              <span>Optional target subdirectory</span>
              <input type="text" name="target_subdir" placeholder="references" />
            </label>
            <button class="button button-secondary" type="submit">Upload file</button>
          </form>
        </section>

        <section class="panel">
          <div class="eyebrow">Create file</div>
          <h2>New text asset</h2>
          <form method="post" action="{_escape(create_action)}" class="stack">
            <label class="field">
              <span>File path</span>
              <input type="text" name="file_path" placeholder="references/REFERENCE.md" required />
            </label>
            <label class="field">
              <span>Initial content</span>
              <textarea name="content" rows="8"></textarea>
            </label>
            <button class="button button-secondary" type="submit">Create file</button>
          </form>
        </section>
      </aside>

      <main class="editor-main">
        {editor_block}
      </main>
    </section>
    """


def _render_admin_page(
    *,
    title: str,
    eyebrow: str,
    heading: str,
    subheading: str,
    content: str,
    notice: str | None = None,
    current_nav: str,
) -> str:
    header_actions = """
      <div class="top-nav-actions">
        <a class="ghost-link" href="/admin">Dashboard</a>
        <a class="ghost-link" href="/admin/new">Create skill</a>
      </div>
    """
    body = f"""
    <div class="app-shell">
      <header class="top-nav">
        <div>
          <div class="eyebrow">Skills Control Room</div>
          <strong>Admin workspace</strong>
        </div>
        {header_actions}
      </header>
      <main class="main-shell">
        <section class="page-head">
          <div class="eyebrow">{_escape(eyebrow)}</div>
          <h1>{_escape(heading)}</h1>
          <p class="lede">{_escape(subheading)}</p>
          {_render_notice(notice)}
        </section>
        {content}
      </main>
    </div>
    """
    return _render_document(title, body, login_mode=False)


def _render_notice(notice: str | None) -> str:
    if not notice:
        return ""
    return f'<div class="notice">{_escape(notice)}</div>'


def _render_document(title: str, body: str, *, login_mode: bool) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{_escape(title)}</title>
    <style>
      :root {{
        --color-primary: #17191c;
        --color-secondary: #67707a;
        --color-tertiary: #c2623d;
        --color-neutral: #f4efe8;
        --color-surface: #fffdf9;
        --color-surface-alt: #ece4d8;
        --color-border: #d6c8b5;
        --color-success: #1f6a43;
        --color-danger: #9b3c2f;
        --color-text-soft: #4d545c;
        --font-display: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", "Baskerville", serif;
        --font-body: "Avenir Next", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        --font-label: "IBM Plex Mono", "SFMono-Regular", "Menlo", monospace;
        --space-xs: 0.375rem;
        --space-sm: 0.625rem;
        --space-md: 1rem;
        --space-lg: 1.5rem;
        --space-xl: 2rem;
        --radius-sm: 8px;
        --radius-md: 14px;
        --radius-lg: 22px;
        --shadow-soft: 0 16px 40px rgba(23, 25, 28, 0.08);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background:
          radial-gradient(circle at top left, rgba(194, 98, 61, 0.10), transparent 28%),
          linear-gradient(180deg, #faf6ef 0%, var(--color-neutral) 100%);
        color: var(--color-primary);
        font-family: var(--font-body);
      }}
      h1, h2, h3 {{ font-family: var(--font-display); font-weight: 700; letter-spacing: -0.02em; margin: 0; }}
      h1 {{ font-size: clamp(2rem, 4vw, 3.5rem); line-height: 1.02; }}
      h2 {{ font-size: 1.65rem; line-height: 1.1; }}
      h3 {{ font-size: 1.1rem; line-height: 1.15; }}
      p {{ margin: 0; }}
      a {{ color: inherit; text-decoration: none; }}
      small, .meta, .eyebrow, dt, .card-chip, .status-pill, .readonly-pill {{
        font-family: var(--font-label);
        letter-spacing: 0.04em;
      }}
      .app-shell {{
        min-height: 100vh;
      }}
      .top-nav {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--space-lg);
        padding: 1rem 1.5rem;
        border-bottom: 1px solid rgba(214, 200, 181, 0.65);
        background: rgba(255, 253, 249, 0.72);
        backdrop-filter: blur(14px);
        position: sticky;
        top: 0;
        z-index: 20;
      }}
      .top-nav-actions {{
        display: flex;
        gap: var(--space-md);
        align-items: center;
      }}
      .ghost-link {{
        color: var(--color-secondary);
        font-size: 0.86rem;
      }}
      .ghost-link:hover {{ color: var(--color-primary); }}
      .ghost-link.danger {{ color: var(--color-danger); }}
      .main-shell {{
        width: min(1320px, calc(100vw - 2rem));
        margin: 0 auto;
        padding: 2rem 0 4rem;
      }}
      .page-head {{
        display: grid;
        gap: var(--space-sm);
        margin-bottom: 1.5rem;
      }}
      .eyebrow {{
        text-transform: uppercase;
        font-size: 0.76rem;
        color: var(--color-secondary);
      }}
      .lede {{
        color: var(--color-text-soft);
        max-width: 70ch;
        line-height: 1.6;
      }}
      .lede.small {{ font-size: 0.96rem; }}
      .notice {{
        margin-top: var(--space-sm);
        padding: 0.9rem 1rem;
        border-radius: var(--radius-sm);
        border: 1px solid rgba(194, 98, 61, 0.35);
        background: rgba(194, 98, 61, 0.08);
      }}
      .hero-metrics {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: var(--space-md);
        margin-bottom: 1.5rem;
      }}
      .hero-metrics article,
      .source-card,
      .skill-card,
      .panel,
      .login-card {{
        border: 1px solid rgba(214, 200, 181, 0.78);
        background: rgba(255, 253, 249, 0.92);
        box-shadow: var(--shadow-soft);
      }}
      .hero-metrics article {{
        padding: 1rem;
        border-radius: var(--radius-md);
        display: grid;
        gap: 0.25rem;
      }}
      .hero-metrics strong {{
        font-family: var(--font-display);
        font-size: 1.6rem;
      }}
      .hero-metrics span {{
        color: var(--color-secondary);
        font-size: 0.9rem;
      }}
      .panel {{
        border-radius: var(--radius-lg);
        padding: 1.2rem;
        margin-bottom: 1.5rem;
      }}
      .panel.narrow {{
        max-width: 860px;
      }}
      .panel-header {{
        display: flex;
        align-items: end;
        justify-content: space-between;
        gap: var(--space-lg);
        margin-bottom: 1rem;
      }}
      .source-grid, .skill-grid {{
        display: grid;
        gap: var(--space-md);
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      }}
      .source-card, .skill-card {{
        border-radius: var(--radius-md);
        padding: 1rem;
        display: grid;
        gap: 0.8rem;
      }}
      .card-chip, .status-pill, .readonly-pill {{
        display: inline-flex;
        align-items: center;
        width: fit-content;
        border-radius: 999px;
        padding: 0.28rem 0.58rem;
        background: var(--color-surface-alt);
        color: var(--color-secondary);
        font-size: 0.72rem;
        text-transform: uppercase;
      }}
      .status-pill {{
        background: rgba(31, 106, 67, 0.10);
        color: var(--color-success);
      }}
      .readonly-pill {{
        background: rgba(103, 112, 122, 0.12);
      }}
      .metric-row, .meta-grid {{
        display: grid;
        gap: var(--space-sm);
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .metric-row div, .meta-grid div {{
        display: grid;
        gap: 0.2rem;
      }}
      .metric-row strong, .meta-grid dd {{
        margin: 0;
        font-weight: 600;
      }}
      dt {{
        font-size: 0.72rem;
        color: var(--color-secondary);
        text-transform: uppercase;
      }}
      .action-row {{
        display: flex;
        gap: var(--space-sm);
        flex-wrap: wrap;
        align-items: center;
      }}
      .action-row.stacked {{
        flex-direction: column;
        align-items: stretch;
      }}
      .button {{
        border: 1px solid transparent;
        border-radius: var(--radius-sm);
        padding: 0.78rem 1rem;
        font: inherit;
        cursor: pointer;
        transition: transform 140ms ease, box-shadow 140ms ease, background 140ms ease;
      }}
      .button:hover {{
        transform: translateY(-1px);
      }}
      .button-primary {{
        background: var(--color-tertiary);
        color: white;
        box-shadow: 0 10px 24px rgba(194, 98, 61, 0.24);
      }}
      .button-secondary {{
        background: transparent;
        border-color: var(--color-border);
        color: var(--color-primary);
      }}
      .button-danger {{
        background: var(--color-danger);
        color: white;
      }}
      .stack {{
        display: grid;
        gap: var(--space-md);
      }}
      .field {{
        display: grid;
        gap: 0.45rem;
      }}
      .field > span {{
        font-family: var(--font-label);
        font-size: 0.77rem;
        text-transform: uppercase;
        color: var(--color-secondary);
      }}
      input, textarea, select {{
        width: 100%;
        border-radius: var(--radius-sm);
        border: 1px solid var(--color-border);
        padding: 0.82rem 0.9rem;
        background: rgba(255, 253, 249, 0.95);
        color: var(--color-primary);
        font: inherit;
      }}
      input:focus, textarea:focus, select:focus {{
        outline: 2px solid rgba(194, 98, 61, 0.25);
        border-color: rgba(194, 98, 61, 0.62);
      }}
      textarea {{
        resize: vertical;
        line-height: 1.5;
      }}
      .code-editor {{
        min-height: 32rem;
        font-family: var(--font-label);
        font-size: 0.92rem;
        background: #f8f2e9;
      }}
      .editor-layout {{
        display: grid;
        grid-template-columns: 340px minmax(0, 1fr);
        gap: var(--space-lg);
      }}
      .editor-sidebar {{
        display: grid;
        gap: var(--space-md);
        align-content: start;
      }}
      .file-list {{
        list-style: none;
        padding: 0;
        margin: 0;
        display: grid;
        gap: 0.7rem;
      }}
      .file-item {{
        display: grid;
        gap: 0.45rem;
        padding: 0.75rem;
        border: 1px solid rgba(214, 200, 181, 0.65);
        border-radius: var(--radius-sm);
        background: rgba(244, 239, 232, 0.45);
      }}
      .file-item.active {{
        border-color: rgba(194, 98, 61, 0.45);
        background: rgba(194, 98, 61, 0.10);
      }}
      .file-item a strong {{
        display: block;
        margin-bottom: 0.2rem;
      }}
      .file-item span {{
        color: var(--color-secondary);
        font-size: 0.84rem;
      }}
      .file-actions {{
        display: flex;
        gap: var(--space-sm);
        flex-wrap: wrap;
        justify-content: space-between;
      }}
      .inline-upload {{
        display: grid;
        gap: var(--space-sm);
      }}
      .field.compact input,
      .field.compact select {{
        padding: 0.66rem 0.78rem;
      }}
      .search {{
        min-width: min(340px, 100%);
      }}
      .empty-state {{
        color: var(--color-secondary);
        padding: 1rem 0;
      }}
      .login-shell {{
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 1.25rem;
      }}
      .login-card {{
        width: min(520px, 100%);
        border-radius: 28px;
        padding: 2rem;
        display: grid;
        gap: 1rem;
      }}
      @media (max-width: 980px) {{
        .editor-layout {{
          grid-template-columns: 1fr;
        }}
      }}
      @media (max-width: 720px) {{
        .main-shell {{
          width: min(100vw - 1rem, 100%);
          padding-top: 1rem;
        }}
        .top-nav, .panel-header {{
          flex-direction: column;
          align-items: stretch;
        }}
      }}
    </style>
  </head>
  <body>
    {body}
    <script>
      const filterInput = document.querySelector('[data-skill-filter]');
      if (filterInput) {{
        filterInput.addEventListener('input', (event) => {{
          const query = event.target.value.trim().toLowerCase();
          document.querySelectorAll('[data-skill-card]').forEach((card) => {{
            const haystack = card.getAttribute('data-search-text') || '';
            card.style.display = !query || haystack.includes(query) ? '' : 'none';
          }});
        }});
      }}
      document.querySelectorAll('form[data-confirm]').forEach((form) => {{
        form.addEventListener('submit', (event) => {{
          const message = form.getAttribute('data-confirm') || 'Are you sure?';
          if (!window.confirm(message)) {{
            event.preventDefault();
          }}
        }});
      }});
      const editor = document.querySelector('[data-editor-textarea]');
      const dirtyIndicator = document.querySelector('[data-dirty-indicator]');
      if (editor && dirtyIndicator) {{
        const initialValue = editor.value;
        const updateDirty = () => {{
          const dirty = editor.value !== initialValue;
          dirtyIndicator.textContent = dirty ? 'Unsaved changes' : 'Saved';
          dirtyIndicator.style.background = dirty ? 'rgba(194, 98, 61, 0.10)' : 'rgba(31, 106, 67, 0.10)';
          dirtyIndicator.style.color = dirty ? 'var(--color-tertiary)' : 'var(--color-success)';
        }};
        editor.addEventListener('input', updateDirty);
        window.addEventListener('beforeunload', (event) => {{
          if (editor.value !== initialValue) {{
            event.preventDefault();
            event.returnValue = '';
          }}
        }});
      }}
    </script>
  </body>
</html>
"""


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _bundle_action_href(source_name: str, bundle_path: str, suffix: str) -> str:
    return f"/admin/sources/{quote(source_name, safe='')}/bundles/{quote(bundle_path, safe='/')}{suffix}"
