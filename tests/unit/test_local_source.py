"""Unit tests for ``skills_mcp_server.sources.local.LocalSource``.

Covers the behaviour contract spelled out in SPEC §6 (skill format), §7
(storage), and §10 (security — symlink realpath resolution is load-bearing).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from skills_mcp_server.models import SkillBundle, SkillManifest
from skills_mcp_server.sources.base import Source, SourceError
from skills_mcp_server.sources.local import LocalSource

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_SKILL_MD = """\
---
name: {name}
description: {description}
---

# {name}

Body paragraph for {name}.
"""


def _write_skill_md(bundle_dir: Path, name: str, description: str) -> Path:
    """Write a minimal valid SKILL.md to ``bundle_dir`` and return its path."""
    bundle_dir.mkdir(parents=True, exist_ok=True)
    skill_md = bundle_dir / "SKILL.md"
    skill_md.write_text(_VALID_SKILL_MD.format(name=name, description=description))
    return skill_md


# ---------------------------------------------------------------------------
# 1. Fixtures path — happy path
# ---------------------------------------------------------------------------


def test_load_fixtures_yields_valid_bundles(local_sample_skills_dir: Path) -> None:
    """``load()`` against the checked-in fixtures returns exactly the two
    valid bundles (``hello-world`` and ``summarize-text``). The broken
    fixture (``broken-skill``) must be absent. Each bundle carries a
    non-empty ``manifest.name`` / ``manifest.description``.
    """
    source = LocalSource("sample", local_sample_skills_dir)
    bundles = list(source.load())

    assert all(isinstance(b, SkillBundle) for b in bundles)
    slugs = sorted(b.slug for b in bundles)
    assert slugs == ["hello-world", "summarize-text"]

    for bundle in bundles:
        assert isinstance(bundle.manifest, SkillManifest)
        assert bundle.manifest.name.strip()
        assert bundle.manifest.description.strip()


# ---------------------------------------------------------------------------
# 2. Broken bundle is skipped, not fatal
# ---------------------------------------------------------------------------


def test_broken_skill_is_skipped_not_raised(
    local_sample_skills_dir: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``broken-skill`` is missing ``description`` — the loader skips it
    with a warning log line instead of raising.
    """
    source = LocalSource("sample", local_sample_skills_dir)

    with caplog.at_level(logging.WARNING, logger="skills_mcp_server.sources.local"):
        bundles = list(source.load())

    slugs = {b.slug for b in bundles}
    assert "broken-skill" not in slugs

    # Confirm a warning mentioning the broken bundle was emitted. The
    # loader's warning contains the bundle path; check for the slug.
    matching = [rec for rec in caplog.records if "broken-skill" in rec.getMessage()]
    assert matching, (
        f"expected a WARNING-or-above log mentioning 'broken-skill'; got {[r.getMessage() for r in caplog.records]}"
    )
    assert all(rec.levelno >= logging.WARNING for rec in matching)


# ---------------------------------------------------------------------------
# 3. Resources enumeration for summarize-text
# ---------------------------------------------------------------------------


def test_summarize_text_resources_include_reference_md(
    local_sample_skills_dir: Path,
) -> None:
    """``summarize-text`` ships both ``SKILL.md`` and ``reference.md``.
    The bundle's ``resources`` tuple must include both (as paths relative
    to the bundle root) and be sorted.
    """
    source = LocalSource("sample", local_sample_skills_dir)
    bundles = {b.slug: b for b in source.load()}

    summarize = bundles["summarize-text"]
    resources = list(summarize.resources)

    assert Path("SKILL.md") in resources
    assert Path("reference.md") in resources
    # Must be sorted (the loader's contract per local.py::_list_bundle_resources).
    assert resources == sorted(resources)


# ---------------------------------------------------------------------------
# 4. Realpath resolution of bundle_path
# ---------------------------------------------------------------------------


def test_bundle_path_is_realpath_resolved(tmp_path: Path) -> None:
    """If the operator points ``LocalSource`` at a symlinked directory,
    loaded bundles' ``bundle_path`` must be resolved via realpath —
    otherwise downstream symlink-escape checks are fooled by the user-
    visible path.
    """
    real_root = tmp_path / "real-root"
    real_root.mkdir()
    _write_skill_md(
        real_root / "my-bundle",
        name="my-bundle",
        description="A sample bundle for realpath testing.",
    )

    symlink_parent = tmp_path / "parent"
    symlink_parent.mkdir()
    symlink_root = symlink_parent / "link-to-root"
    os.symlink(real_root, symlink_root)

    source = LocalSource("sample", symlink_root)
    bundles = list(source.load())
    assert len(bundles) == 1
    bundle = bundles[0]

    expected = Path(os.path.realpath(real_root / "my-bundle"))
    assert bundle.bundle_path == expected
    # Sanity: the visible (symlinked) path is not what got stored.
    assert str(bundle.bundle_path).startswith(str(Path(os.path.realpath(real_root))))


# ---------------------------------------------------------------------------
# 5. Symlink escape is rejected
# ---------------------------------------------------------------------------


def test_symlink_escape_rejected(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A bundle reachable only via a symlink that points outside the
    configured root must be rejected and logged. SPEC §10.
    """
    root = tmp_path / "root"
    root.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()
    evil_bundle = outside / "evil-bundle"
    _write_skill_md(
        evil_bundle,
        name="evil-bundle",
        description="This bundle lives outside root; it must not load.",
    )

    # root/evil-link -> outside/evil-bundle/
    os.symlink(evil_bundle, root / "evil-link")

    source = LocalSource("sample", root)
    with caplog.at_level(logging.WARNING, logger="skills_mcp_server.sources.local"):
        bundles = list(source.load())

    assert bundles == []
    # Escape was logged — message phrasing is internal but must mention
    # "escape" per the implementation. Stay flexible on wording.
    escape_records = [rec for rec in caplog.records if "escape" in rec.getMessage().lower()]
    assert escape_records, (
        f"expected a WARNING log about the symlink escape; got {[r.getMessage() for r in caplog.records]}"
    )


# ---------------------------------------------------------------------------
# 6. Empty source dir yields nothing
# ---------------------------------------------------------------------------


def test_empty_source_dir_yields_nothing(tmp_path: Path) -> None:
    """An empty source directory is valid — the loader produces zero
    bundles without raising.
    """
    empty = tmp_path / "empty-root"
    empty.mkdir()
    source = LocalSource("sample", empty)
    assert list(source.load()) == []


# ---------------------------------------------------------------------------
# 7. Missing root is a configuration error
# ---------------------------------------------------------------------------


def test_nonexistent_root_raises_sourceerror_in_init(tmp_path: Path) -> None:
    """A non-existent root is a misconfiguration; surface it eagerly at
    construction time as ``SourceError`` rather than at first ``load()``.
    """
    missing = tmp_path / "does-not-exist"
    with pytest.raises(SourceError):
        LocalSource("sample", missing)


# ---------------------------------------------------------------------------
# 8. Root is a file, not a directory
# ---------------------------------------------------------------------------


def test_root_is_a_file_raises_sourceerror_in_init(tmp_path: Path) -> None:
    """A root that resolves to a regular file is a misconfiguration."""
    not_a_dir = tmp_path / "regular-file"
    not_a_dir.write_text("hello")
    with pytest.raises(SourceError):
        LocalSource("sample", not_a_dir)


# ---------------------------------------------------------------------------
# 9. Malformed YAML frontmatter is skipped, not fatal
# ---------------------------------------------------------------------------


def test_skill_md_malformed_frontmatter_is_skipped(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A bundle whose SKILL.md has invalid YAML in its frontmatter must
    be skipped with a warning log, not crash the whole load.
    """
    root = tmp_path / "root"
    (root / "bad").mkdir(parents=True)
    # Invalid YAML: unclosed list.
    (root / "bad" / "SKILL.md").write_text("---\nname: [unclosed\ndescription: this will never parse\n---\n\n# body\n")
    # Include one good bundle to confirm only the bad one is dropped.
    _write_skill_md(
        root / "good",
        name="good",
        description="A valid bundle so the load loop actually produces output.",
    )

    source = LocalSource("sample", root)
    with caplog.at_level(logging.WARNING, logger="skills_mcp_server.sources.local"):
        bundles = list(source.load())

    slugs = {b.slug for b in bundles}
    assert slugs == {"good"}
    assert any("bad" in rec.getMessage() and rec.levelno >= logging.WARNING for rec in caplog.records)


# ---------------------------------------------------------------------------
# 10. SKILL.md with no frontmatter fence is skipped
# ---------------------------------------------------------------------------


def test_skill_md_no_frontmatter_fence_is_skipped(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A SKILL.md without any ``---`` fence is body-only; the required
    ``name`` / ``description`` check then fails and the bundle is skipped.
    """
    root = tmp_path / "root"
    (root / "no-frontmatter").mkdir(parents=True)
    (root / "no-frontmatter" / "SKILL.md").write_text("# Just a heading\n\nNo frontmatter fence at all.\n")

    source = LocalSource("sample", root)
    with caplog.at_level(logging.WARNING, logger="skills_mcp_server.sources.local"):
        bundles = list(source.load())

    assert bundles == []
    assert any("no-frontmatter" in rec.getMessage() and rec.levelno >= logging.WARNING for rec in caplog.records)


# ---------------------------------------------------------------------------
# 11. Depth cap — bundles deeper than the cap are not discovered
# ---------------------------------------------------------------------------


def test_depth_cap(tmp_path: Path) -> None:
    """The walker caps recursion at ``_MAX_BUNDLE_DEPTH`` (3) directories
    below root. A SKILL.md at ``root/a/b/c/d/`` (depth 4) is not
    discovered; ``root/a/b/`` (depth 2) is.
    """
    root = tmp_path / "root"
    root.mkdir()

    # Depth 2 — should load.
    _write_skill_md(
        root / "a" / "b",
        name="shallow",
        description="Bundle at depth 2, within the cap.",
    )
    # Depth 4 — should be skipped by the depth cap.
    _write_skill_md(
        root / "a" / "b" / "c" / "d",
        name="too-deep",
        description="Bundle at depth 4, beyond the cap.",
    )

    source = LocalSource("sample", root)
    slugs = {b.slug for b in source.load()}
    assert "b" in slugs  # root/a/b — bundle slug is its dir name
    assert "d" not in slugs


# ---------------------------------------------------------------------------
# 12. Nested bundles at allowed depths both load
# ---------------------------------------------------------------------------


def test_nested_bundles_at_allowed_depths(tmp_path: Path) -> None:
    """Finding a SKILL.md at ``root/a/`` must not stop the walker from
    descending further; ``root/a/b/SKILL.md`` must also load.
    """
    root = tmp_path / "root"
    root.mkdir()
    _write_skill_md(
        root / "a",
        name="outer",
        description="Outer bundle at depth 1.",
    )
    _write_skill_md(
        root / "a" / "b",
        name="inner",
        description="Inner bundle at depth 2 — must still be discovered.",
    )

    source = LocalSource("sample", root)
    slugs = {b.slug for b in source.load()}
    assert slugs == {"a", "b"}


# ---------------------------------------------------------------------------
# 13. Runtime protocol check
# ---------------------------------------------------------------------------


def test_source_protocol_runtime_check(tmp_path: Path) -> None:
    """``Source`` is a ``@runtime_checkable`` Protocol; a ``LocalSource``
    instance must pass ``isinstance`` against it.
    """
    root = tmp_path / "root"
    root.mkdir()
    source = LocalSource("sample", root)
    assert isinstance(source, Source)
