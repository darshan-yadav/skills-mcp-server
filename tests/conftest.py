"""Shared pytest fixtures for the skills-mcp-server test suite.

Wave 1 harness only — no assertions live here. Wave 2+ SDET tasks will import
these fixtures to write the actual tests that exercise source loaders,
MCP surface behaviour, conformance checks, etc.

Fixture inventory:
    - tmp_config_dir: writes a minimal ``config.yaml`` (schema per SPEC §7.1
      + §13.2) into a tmp dir whose ``sources:`` points at the checked-in
      local-sample fixture bundle directory. Yields the tmp dir path.
    - local_sample_skills_dir: absolute path to
      ``tests/fixtures/skills/local-sample/``.
    - git_repo_factory: factory that, given ``{path_in_repo: content}``,
      initialises a git repo with those files committed on ``main`` and
      returns the repo path. Uses ``git`` via ``subprocess`` — intentionally
      no GitPython dependency for fixtures.
    - sample_skill_md: pure helper returning a SKILL.md text body given
      frontmatter fields.
"""

from __future__ import annotations

import os
import subprocess
import textwrap
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

TESTS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
LOCAL_SAMPLE_DIR = FIXTURES_DIR / "skills" / "local-sample"


@pytest.fixture
def local_sample_skills_dir() -> Path:
    """Absolute path to the checked-in local-sample skill bundles."""
    return LOCAL_SAMPLE_DIR


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_MINIMAL_CONFIG_TEMPLATE = """\
sources:
  - name: local-sample
    type: local
    path: {path}

data_dir: {data_dir}
log_level: debug
"""


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Create a tmp dir containing a minimal config.yaml.

    The config points its single ``local`` source at the checked-in
    ``tests/fixtures/skills/local-sample/`` directory so tests can exercise
    the full load path without networking or a container.

    Schema follows SPEC §7.1 and §13.2.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    config_path = config_dir / "config.yaml"
    config_path.write_text(
        _MINIMAL_CONFIG_TEMPLATE.format(
            path=str(LOCAL_SAMPLE_DIR),
            data_dir=str(data_dir),
        )
    )
    return config_dir


# ---------------------------------------------------------------------------
# Git repo factory
# ---------------------------------------------------------------------------


def _run_git(cwd: Path, *args: str) -> None:
    """Invoke git with a hermetic env so tests don't pick up user config."""
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "skills-mcp-tests",
            "GIT_AUTHOR_EMAIL": "tests@skills-mcp.invalid",
            "GIT_COMMITTER_NAME": "skills-mcp-tests",
            "GIT_COMMITTER_EMAIL": "tests@skills-mcp.invalid",
            # Avoid reading ~/.gitconfig or system gitconfig inside CI sandboxes.
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        }
    )
    subprocess.run(
        ("git", *args),
        cwd=str(cwd),
        env=env,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def git_repo_factory(tmp_path: Path) -> Callable[[Mapping[str, str]], Path]:
    """Return a factory that materialises a git repo from a file-tree dict.

    Usage::

        repo = git_repo_factory({
            "hello/SKILL.md": "---\\nname: hello\\ndescription: ...\\n---\\n",
            "README.md": "test repo",
        })

    The repo has a single commit on ``main`` containing all provided files.
    Each call creates a fresh repo under a unique sub-directory of ``tmp_path``
    so multiple repos can coexist in one test.
    """
    counter = {"n": 0}

    def _make(files: Mapping[str, str]) -> Path:
        counter["n"] += 1
        repo_path = tmp_path / f"gitrepo-{counter['n']}"
        repo_path.mkdir()

        _run_git(repo_path, "init", "-b", "main")

        for rel_path, content in files.items():
            target = repo_path / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)

        _run_git(repo_path, "add", "-A")
        _run_git(repo_path, "commit", "-m", "initial commit")
        return repo_path

    return _make


# ---------------------------------------------------------------------------
# SKILL.md helper
# ---------------------------------------------------------------------------


def sample_skill_md(
    name: str,
    description: str,
    body: str = "",
    extra_frontmatter: Mapping[str, str] | None = None,
) -> str:
    """Return a SKILL.md text with the given frontmatter fields + body.

    Pure helper — not a pytest fixture. Import directly from ``conftest`` or
    from a ``tests.helpers`` module in Wave 2 if preferred.

    Args:
        name: value of the required ``name`` frontmatter key.
        description: value of the required ``description`` frontmatter key.
        body: markdown body (appended below the ``---`` fence).
        extra_frontmatter: optional additional keys (e.g. ``version``,
            ``tags``) emitted verbatim as ``key: value`` lines. Callers who
            need list/structured values should pre-render them as YAML
            strings.
    """
    lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
    ]
    if extra_frontmatter:
        for key, value in extra_frontmatter.items():
            lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    lines.append(textwrap.dedent(body).lstrip("\n"))
    return "\n".join(lines)
