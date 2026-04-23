"""Local filesystem source — walks a directory for SKILL.md bundles.

See SPEC §7 (storage) and SPEC §10 (security; symlink realpath resolution
is load-bearing here).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Iterator

import yaml

from skills_mcp_server.models import SkillBundle, SkillManifest
from skills_mcp_server.sources.base import SourceError

logger = logging.getLogger(__name__)

# Maximum directory depth (relative to root) at which we will accept a
# SKILL.md as defining a bundle. root/SKILL.md is depth 0, root/a/SKILL.md
# is depth 1, root/a/b/SKILL.md is depth 3 (the spec's stated upper bound).
_MAX_BUNDLE_DEPTH = 3


class LocalSource:
    """Load skill bundles from a local directory.

    The constructor resolves the root via ``Path.expanduser()`` plus
    ``os.path.realpath`` so subsequent symlink-escape checks compare
    against a canonical absolute path. A missing or non-directory root is
    a fatal configuration error; it raises ``SourceError`` immediately.
    """

    def __init__(self, name: str, root: Path) -> None:
        self.name = name
        expanded = Path(root).expanduser()
        resolved = Path(os.path.realpath(expanded))
        if not resolved.exists():
            raise SourceError(
                f"local source {name!r}: root does not exist: {resolved}"
            )
        if not resolved.is_dir():
            raise SourceError(
                f"local source {name!r}: root is not a directory: {resolved}"
            )
        self.root = resolved

    def load(self) -> Iterator[SkillBundle]:
        """Yield one ``SkillBundle`` per valid bundle directory under root.

        A bundle is a directory containing ``SKILL.md`` at its top level.
        The walk is bounded to ``_MAX_BUNDLE_DEPTH`` directories below
        root. Bundles with bad frontmatter or escaping symlinks are
        skipped with a warning — never fatal.
        """

        root_real = self.root  # already realpath'd in __init__
        root_str = str(root_real)

        for current_dir, dirnames, filenames in os.walk(root_real, followlinks=True):
            current_path = Path(current_dir)

            # Enforce depth cap: stop descending past _MAX_BUNDLE_DEPTH.
            try:
                rel = current_path.relative_to(root_real)
                depth = 0 if rel == Path(".") else len(rel.parts)
            except ValueError:
                # current_path somehow escaped root_real — refuse to descend.
                dirnames[:] = []
                continue

            if depth >= _MAX_BUNDLE_DEPTH:
                dirnames[:] = []  # do not recurse deeper

            if "SKILL.md" not in filenames:
                continue

            # symlink traversal: resolve the candidate and confirm it still
            # sits inside root's realpath. Anything pointing outside — a
            # symlink into /etc, a sibling skill's bundle, /data — is
            # rejected per SPEC §10.
            candidate_real = Path(os.path.realpath(current_path))
            candidate_str = str(candidate_real)
            if candidate_str != root_str and not candidate_str.startswith(
                root_str + os.sep
            ):
                logger.warning(
                    "source %r: skipping bundle %s — realpath %s escapes root %s",
                    self.name,
                    current_path,
                    candidate_real,
                    root_real,
                )
                # Do not recurse into an escaping directory either.
                dirnames[:] = []
                continue

            skill_md = candidate_real / "SKILL.md"
            try:
                raw = skill_md.read_text(encoding="utf-8")
            except OSError as exc:
                logger.warning(
                    "source %r: cannot read %s: %s", self.name, skill_md, exc
                )
                continue

            try:
                manifest, body = _parse_skill_md(raw, skill_md)
            except SourceError as exc:
                logger.warning("source %r: %s", self.name, exc)
                continue

            resources = _list_bundle_resources(candidate_real)
            slug = candidate_real.name

            yield SkillBundle(
                source_name=self.name,
                slug=slug,
                bundle_path=candidate_real,
                manifest=manifest,
                body=body,
                resources=resources,
                commit_sha=None,  # local sources have no commit pin
            )


def _parse_skill_md(raw: str, path: Path) -> tuple[SkillManifest, str]:
    """Split ``raw`` into (manifest, body).

    Frontmatter is the block between the first pair of ``---`` fences at
    the start of the file. If there is no leading fence, the whole file
    is body and the frontmatter is empty (which means the required
    ``name``/``description`` check below will fail and the bundle is
    skipped).
    """

    frontmatter_text = ""
    body = raw

    # Frontmatter must start on the very first line with "---". Accept a
    # leading BOM but nothing else.
    stripped = raw.lstrip("\ufeff")
    if stripped.startswith("---"):
        # Find the closing fence. Fence lines may be "---\n" or "---\r\n"
        # or "---" at EOF. Work line-by-line to stay robust.
        lines = stripped.splitlines(keepends=True)
        # First line is the opening fence; find the next line that is
        # exactly "---" (ignoring trailing newline).
        close_idx: int | None = None
        for i in range(1, len(lines)):
            if lines[i].rstrip("\r\n") == "---":
                close_idx = i
                break
        if close_idx is not None:
            frontmatter_text = "".join(lines[1:close_idx])
            body = "".join(lines[close_idx + 1 :])
        else:
            # No closing fence — treat entire file as body to avoid
            # silently swallowing content. Frontmatter stays empty, which
            # forces the required-field check to reject the bundle.
            frontmatter_text = ""
            body = raw

    data: Any
    if frontmatter_text.strip():
        try:
            data = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as exc:
            raise SourceError(
                f"{path}: frontmatter is not valid YAML: {exc}"
            ) from exc
    else:
        data = None

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise SourceError(
            f"{path}: frontmatter must be a YAML mapping, got {type(data).__name__}"
        )

    name = data.get("name")
    description = data.get("description")
    if not isinstance(name, str) or not name.strip():
        raise SourceError(f"{path}: frontmatter is missing required string `name`")
    if not isinstance(description, str) or not description.strip():
        raise SourceError(
            f"{path}: frontmatter is missing required string `description`"
        )

    from skills_mcp_server.models import ToolManifest

    extra = {k: v for k, v in data.items() if k not in ("name", "description", "tools")}
    
    tools_data = data.get("tools", [])
    if not isinstance(tools_data, list):
        raise SourceError(f"{path}: frontmatter 'tools' must be a list if present")
    
    parsed_tools = []
    for i, t in enumerate(tools_data):
        if not isinstance(t, dict):
            logger.warning("source %s tool at index %d is not a mapping, skipping", path, i)
            continue
        t_name = t.get("name")
        t_desc = t.get("description")
        t_script = t.get("script")
        t_args = t.get("arguments")
        
        if not isinstance(t_name, str) or not isinstance(t_desc, str) or not isinstance(t_script, str):
            logger.warning("source %s tool %r is missing required string fields (name, description, script), skipping", path, t_name)
            continue
            
        parsed_tools.append(ToolManifest(
            name=t_name,
            description=t_desc,
            script=t_script,
            arguments=t_args if isinstance(t_args, dict) else None
        ))

    manifest = SkillManifest(
        name=name, 
        description=description, 
        tools=tuple(parsed_tools),
        extra=extra
    )
    # Strip leading blank line often left between the closing fence and
    # the real body. Preserves interior whitespace.
    if body.startswith("\n"):
        body = body[1:]
    return manifest, body


def _list_bundle_resources(bundle_path: Path) -> tuple[Path, ...]:
    """Return sorted relative paths of regular files at the top level of
    ``bundle_path``. Non-recursive — subdirectories are not walked here;
    bundle layout in SPEC §6.2 keeps auxiliary assets at the top level,
    and deeper walks would widen the attack surface for symlink escape.
    Always includes ``SKILL.md`` itself.
    """

    names: list[Path] = []
    bundle_real_str = str(os.path.realpath(bundle_path))
    with os.scandir(bundle_path) as it:
        for entry in it:
            try:
                if entry.is_file(follow_symlinks=True):
                    entry_real_str = str(os.path.realpath(entry.path))
                    if entry_real_str == bundle_real_str or entry_real_str.startswith(bundle_real_str + os.sep):
                        names.append(Path(entry.name))
                    else:
                        logger.warning(
                            "skipping resource %s — realpath %s escapes bundle %s",
                            entry.name, entry_real_str, bundle_real_str
                        )
            except OSError:
                continue
    names.sort()
    return tuple(names)
