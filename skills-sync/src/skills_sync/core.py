"""Sync skills from skills-mcp-server over MCP into local SKILL.md bundles."""

from __future__ import annotations

import base64
import json
import logging
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters, get_default_environment, stdio_client

logger = logging.getLogger(__name__)

_BUILTIN_TOOL_NAMES = frozenset(
    {
        "refresh_skills",
        "reload",
        "list_skills",
        "get_skill_manifest",
        "server_info",
    }
)


def _parse_skill_resource_uri(uri: str) -> tuple[str, str, str] | None:
    """Return (source_name, slug, relative_path) for skill:// URIs, else None."""
    parsed = urlparse(uri)
    if parsed.scheme != "skill":
        return None
    parts = (parsed.netloc + parsed.path).strip("/")
    if not parts:
        return None
    segments = parts.split("/", 2)
    if len(segments) < 3:
        return None
    return segments[0], segments[1], segments[2]


def _flatten_manifest_for_yaml(manifest: dict[str, Any]) -> dict[str, Any]:
    """Merge dataclass-style ``extra`` into a single frontmatter mapping."""
    out: dict[str, Any] = {}
    extra = manifest.get("extra")
    for key, value in manifest.items():
        if key == "extra":
            continue
        if value in (None, [], {}):
            continue
        out[key] = value
    if isinstance(extra, dict):
        for key, value in extra.items():
            if key not in out and value not in (None, [], {}):
                out[key] = value
    return out


def _should_force_server_execution(
    manifest: dict[str, Any],
    tools_registered: list[str],
) -> bool:
    """SPEC §17.4 — strip local tools/scripts when server registers all declared tools."""
    tools = manifest.get("tools")
    if not tools or not isinstance(tools, list):
        return False
    declared = [t.get("name") for t in tools if isinstance(t, dict) and t.get("name")]
    if not declared:
        return False
    reg = set(tools_registered)
    return reg.issuperset(declared)


async def sync_skills(
    from_uri: str,
    to_dir: Path,
    *,
    auth_header: str | None = None,
    dry_run: bool = False,
) -> None:
    """Sync skills from an MCP server to a local directory (Claude Code layout)."""
    if from_uri.startswith("http://") or from_uri.startswith("https://"):
        headers: dict[str, str] = {}
        if auth_header:
            parts = auth_header.split(":", 1)
            if len(parts) == 2:
                headers[parts[0].strip()] = parts[1].strip()

        base = from_uri.rstrip("/")
        async with sse_client(base + "/sse", headers=headers) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                await _perform_sync(session, to_dir, from_uri, dry_run=dry_run)
    else:
        import shlex

        cmd_parts = shlex.split(from_uri)
        if not cmd_parts:
            raise ValueError("Invalid command for stdio client")

        env = {**os.environ, **get_default_environment()}
        server_params = StdioServerParameters(
            command=cmd_parts[0],
            args=cmd_parts[1:],
            env=env,
        )

        async with stdio_client(server_params) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                await _perform_sync(session, to_dir, from_uri, dry_run=dry_run)


async def _perform_sync(
    session: ClientSession,
    to_dir: Path,
    from_uri: str,
    *,
    dry_run: bool,
) -> None:
    to_dir = to_dir.expanduser()
    if not dry_run:
        to_dir.mkdir(parents=True, exist_ok=True)

    prompts_resp = await session.list_prompts()
    prompts = prompts_resp.prompts

    resources_resp = await session.list_resources()
    resources = resources_resp.resources

    tools_resp = await session.list_tools()
    server_tool_names = {t.name for t in tools_resp.tools}
    skill_tool_names = server_tool_names - _BUILTIN_TOOL_NAMES

    list_skills_payload: list[dict[str, Any]] = []
    try:
        ls_resp = await session.call_tool("list_skills", {})
        if ls_resp.content:
            raw = ls_resp.content[0].text
            if isinstance(raw, str):
                list_skills_payload = json.loads(raw)
    except Exception as exc:
        logger.warning(
            "list_skills failed (%s); split-brain uses tools/list fallback",
            exc,
        )

    skills_by_name: dict[str, dict[str, Any]] = {}
    if isinstance(list_skills_payload, list):
        for row in list_skills_payload:
            if isinstance(row, dict) and isinstance(row.get("name"), str):
                skills_by_name[row["name"]] = row

    sync_ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_root = to_dir / ".skills-sync-backup" / sync_ts
    meta_skills: dict[str, dict[str, Any]] = {}

    for prompt in prompts:
        skill_name = prompt.name
        skill_dir = to_dir / skill_name

        try:
            call_resp = await session.call_tool("get_skill_manifest", {"name": skill_name})
            if not call_resp.content:
                raise ValueError("empty get_skill_manifest response")
            manifest = json.loads(call_resp.content[0].text)
        except Exception as exc:
            logger.warning(
                "Failed manifest for %s (%s); using minimal manifest",
                skill_name,
                exc,
            )
            manifest = {
                "name": skill_name,
                "description": prompt.description or "",
            }

        if not isinstance(manifest, dict):
            manifest = {"name": skill_name, "description": prompt.description or ""}

        skill_row = skills_by_name.get(skill_name, {})
        tools_registered = skill_row.get("tools_registered") or []
        if not isinstance(tools_registered, list):
            tools_registered = []

        if not tools_registered and manifest.get("tools"):
            tools_registered = [
                t.get("name")
                for t in manifest["tools"]
                if isinstance(t, dict) and t.get("name") in skill_tool_names
            ]

        force_server_exec = _should_force_server_execution(manifest, tools_registered)
        if force_server_exec:
            manifest = dict(manifest)
            manifest.pop("tools", None)

        try:
            get_prompt_resp = await session.get_prompt(skill_name, None)
            body = get_prompt_resp.messages[0].content.text
        except Exception as exc:
            logger.error("Failed to fetch prompt body for %s: %s", skill_name, exc)
            body = ""

        if force_server_exec:
            note = (
                "> **Note**: Scripted actions for this skill run on the shared skills server. "
                f"The agent should invoke the MCP tools registered for `{skill_name}` "
                "(see `tools/list` on the server), not local bundle scripts.\n\n"
            )
            body = note + body

        flat_manifest = _flatten_manifest_for_yaml(manifest)
        frontmatter_yaml = yaml.safe_dump(
            flat_manifest,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        ).strip()
        skill_md_text = f"---\n{frontmatter_yaml}\n---\n\n{body}"

        if dry_run:
            logger.info("[dry-run] would sync skill %s", skill_name)
            continue

        if skill_dir.exists():
            backup_dest = backup_root / skill_name
            backup_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(skill_dir), str(backup_dest))
            logger.warning("Server wins: moved previous %s to %s", skill_dir, backup_dest)

        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(skill_md_text, encoding="utf-8")

        for res in resources:
            parsed = _parse_skill_resource_uri(str(res.uri))
            if parsed is None:
                continue
            _source, slug, rel_path = parsed
            if slug != skill_name:
                continue
            if rel_path == "SKILL.md":
                continue
            if force_server_exec and rel_path.startswith("scripts/"):
                continue

            try:
                read_resp = await session.read_resource(res.uri)
                content = read_resp.contents[0]
                target_path = skill_dir / rel_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                if getattr(content, "text", None) is not None:
                    target_path.write_text(content.text, encoding="utf-8")
                elif getattr(content, "blob", None) is not None:
                    target_path.write_bytes(base64.b64decode(content.blob))
            except Exception as exc:
                logger.warning("Failed to fetch resource %s: %s", res.uri, exc)

        meta_skills[skill_name] = {
            "source": skill_row.get("source"),
            "git_ref": skill_row.get("git_ref"),
            "version": skill_row.get("version"),
            "tools_registered": tools_registered,
        }

    if dry_run:
        return

    meta = {
        "synced_at": datetime.now(UTC).isoformat(),
        "from": from_uri,
        "target": str(to_dir),
        "skills": meta_skills,
    }
    (to_dir / ".skills-sync-meta.json").write_text(
        json.dumps(meta, indent=2),
        encoding="utf-8",
    )
    logger.info("Successfully synced %d skills to %s", len(prompts), to_dir)
