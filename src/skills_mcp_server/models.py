"""Shared domain types for skill bundles and manifests.

Internal runtime types used by sources and the registry. These mirror the
skill format defined in SPEC §6 — frontmatter (§6.1), bundle layout (§6.2),
and the minimum skill shape (§6.3). Pydantic is reserved for config
validation types; these are plain immutable dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ToolManifest:
    """A tool declared in a SKILL.md bundle."""

    name: str
    description: str
    script: str
    arguments: Mapping[str, Any] | None = None

@dataclass(frozen=True, slots=True)
class SkillManifest:
    """Parsed SKILL.md frontmatter — see SPEC §6.1.

    `name` and `description` are required; every other frontmatter key
    (license, version, tags, resources, trust_level, dependencies,
    plus any unknown keys) passes through untouched in ``extra``.
    """

    name: str
    description: str
    tools: tuple[ToolManifest, ...] = field(default_factory=tuple)
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SkillBundle:
    """A single loaded skill bundle — see SPEC §6.2.

    Sources yield these; the registry indexes them. ``bundle_path`` is an
    absolute realpath (symlinks already resolved at load time per
    SPEC §10), and ``resources`` holds the bundle's file list as paths
    relative to ``bundle_path`` — always including ``SKILL.md`` itself.
    """

    source_name: str
    slug: str
    bundle_path: Path
    manifest: SkillManifest
    body: str
    resources: tuple[Path, ...]
    commit_sha: str | None = None
