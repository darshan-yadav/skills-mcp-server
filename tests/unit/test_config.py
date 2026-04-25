"""Unit tests for :mod:`skills_mcp_server.config` (T07).

Covers the YAML loader's happy path, env-var substitution, path resolution,
and every validation failure mode that the CLI surfaces to operators. Each
test writes a temporary YAML file and calls ``load_config`` — the exception
surface (``ConfigError``) is what we assert against, because that's what
the CLI prints verbatim.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from skills_mcp_server.config import (
    Config,
    ConfigError,
    GitSourceConfig,
    LocalSourceConfig,
    load_config,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, data: dict[str, Any] | str) -> Path:
    """Dump *data* (dict via safe_dump, str verbatim) to *path* and return it."""
    if isinstance(data, str):
        path.write_text(data)
    else:
        path.write_text(yaml.safe_dump(data, sort_keys=False))
    return path


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_load_minimal_valid_config(tmp_path: Path, local_sample_skills_dir: Path) -> None:
    """A minimal single-local-source config loads and carries sensible defaults."""
    config_path = _write_yaml(
        tmp_path / "config.yaml",
        {
            "sources": [
                {
                    "name": "local-sample",
                    "type": "local",
                    "path": str(local_sample_skills_dir),
                }
            ],
        },
    )

    config = load_config(config_path)

    assert isinstance(config, Config)
    assert len(config.sources) == 1
    source = config.sources[0]
    assert isinstance(source, LocalSourceConfig)
    assert source.type == "local"
    assert source.name == "local-sample"
    # Defaults land on the top-level Config.
    assert config.log_level == "info"
    assert config.refresh_interval_seconds == 300


def test_load_git_source_with_defaults(tmp_path: Path) -> None:
    """Git sources only require name + url; ref defaults to 'main', subpath None."""
    config_path = _write_yaml(
        tmp_path / "config.yaml",
        {
            "sources": [
                {
                    "name": "team",
                    "type": "git",
                    "url": "https://github.com/example/skills.git",
                }
            ],
        },
    )

    config = load_config(config_path)

    source = config.sources[0]
    assert isinstance(source, GitSourceConfig)
    assert source.url == "https://github.com/example/skills.git"
    assert source.ref == "main"
    assert source.subpath is None


# ---------------------------------------------------------------------------
# Env-var substitution
# ---------------------------------------------------------------------------


def test_env_var_substitution_basic(
    tmp_path: Path,
    local_sample_skills_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``${VAR}`` is replaced with the process env value."""
    monkeypatch.setenv("SKILLS_MCP_TEST_URL", "https://example.com/skills.git")
    yaml_text = f"""\
sources:
  - name: team
    type: git
    url: ${{SKILLS_MCP_TEST_URL}}
  - name: local-sample
    type: local
    path: {local_sample_skills_dir}
"""
    config_path = _write_yaml(tmp_path / "config.yaml", yaml_text)

    config = load_config(config_path)

    git_source = config.sources[0]
    assert isinstance(git_source, GitSourceConfig)
    assert git_source.url == "https://example.com/skills.git"


def test_env_var_substitution_default(
    tmp_path: Path,
    local_sample_skills_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``${VAR:-fallback}`` uses the fallback when the var is unset."""
    monkeypatch.delenv("SKILLS_MCP_MISSING_VAR", raising=False)
    yaml_text = f"""\
sources:
  - name: team
    type: git
    url: ${{SKILLS_MCP_MISSING_VAR:-https://fallback.example.com/repo.git}}
  - name: local-sample
    type: local
    path: {local_sample_skills_dir}
"""
    config_path = _write_yaml(tmp_path / "config.yaml", yaml_text)

    config = load_config(config_path)

    git_source = config.sources[0]
    assert isinstance(git_source, GitSourceConfig)
    assert git_source.url == "https://fallback.example.com/repo.git"


def test_env_var_missing_raises(
    tmp_path: Path,
    local_sample_skills_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Referencing an unset var with no default raises, naming the variable."""
    monkeypatch.delenv("UNSET_VAR", raising=False)
    yaml_text = f"""\
sources:
  - name: team
    type: git
    url: ${{UNSET_VAR}}
  - name: local-sample
    type: local
    path: {local_sample_skills_dir}
"""
    config_path = _write_yaml(tmp_path / "config.yaml", yaml_text)

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_path)

    assert "UNSET_VAR" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Schema validation failures
# ---------------------------------------------------------------------------


def test_invalid_source_type_rejected(tmp_path: Path, local_sample_skills_dir: Path) -> None:
    """An unknown discriminator value surfaces a readable error."""
    config_path = _write_yaml(
        tmp_path / "config.yaml",
        {
            "sources": [
                {
                    "name": "bucket",
                    "type": "s3",
                    "path": str(local_sample_skills_dir),
                }
            ],
        },
    )

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_path)

    message = str(exc_info.value)
    # The error message should help the operator find the bad value — either
    # by naming the offending tag ("s3") or the field path ("sources.0").
    assert "s3" in message or "sources.0" in message or "sources" in message


def test_missing_required_field_rejected(tmp_path: Path) -> None:
    """A source missing ``name`` fails validation."""
    config_path = _write_yaml(
        tmp_path / "config.yaml",
        {
            "sources": [
                {
                    "type": "git",
                    "url": "https://github.com/example/skills.git",
                }
            ],
        },
    )

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_path)

    assert "name" in str(exc_info.value)


def test_duplicate_source_names_rejected(tmp_path: Path, local_sample_skills_dir: Path) -> None:
    """Two sources sharing a ``name`` are rejected, and the name is surfaced."""
    config_path = _write_yaml(
        tmp_path / "config.yaml",
        {
            "sources": [
                {
                    "name": "duplicated",
                    "type": "local",
                    "path": str(local_sample_skills_dir),
                },
                {
                    "name": "duplicated",
                    "type": "git",
                    "url": "https://github.com/example/skills.git",
                },
            ],
        },
    )

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_path)

    assert "duplicated" in str(exc_info.value)


def test_admin_ui_enabled_requires_credentials(tmp_path: Path, local_sample_skills_dir: Path) -> None:
    config_path = _write_yaml(
        tmp_path / "config.yaml",
        {
            "sources": [
                {
                    "name": "local-sample",
                    "type": "local",
                    "path": str(local_sample_skills_dir),
                }
            ],
            "admin_ui": {
                "enabled": True,
                "username": "admin",
            },
        },
    )

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_path)

    message = str(exc_info.value)
    assert "admin_ui" in message
    assert "password" in message
    assert "session_secret" in message


def test_local_path_nonexistent_rejected(tmp_path: Path) -> None:
    """A local source pointing at a non-existent directory fails."""
    missing = tmp_path / "does-not-exist"
    config_path = _write_yaml(
        tmp_path / "config.yaml",
        {
            "sources": [
                {
                    "name": "local",
                    "type": "local",
                    "path": str(missing),
                }
            ],
        },
    )

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_path)

    assert "does not exist" in str(exc_info.value) or "exist" in str(exc_info.value)


def test_local_path_not_a_directory_rejected(tmp_path: Path) -> None:
    """A local source whose path is a regular file (not a dir) fails."""
    file_path = tmp_path / "not-a-dir.txt"
    file_path.write_text("i am a file\n")
    config_path = _write_yaml(
        tmp_path / "config.yaml",
        {
            "sources": [
                {
                    "name": "local",
                    "type": "local",
                    "path": str(file_path),
                }
            ],
        },
    )

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_path)

    assert "not a directory" in str(exc_info.value) or "directory" in str(exc_info.value)


def test_local_path_is_realpath_resolved(tmp_path: Path, local_sample_skills_dir: Path) -> None:
    """A symlinked local path resolves to its realpath on the loaded config."""
    symlink_path = tmp_path / "skills-link"
    symlink_path.symlink_to(local_sample_skills_dir, target_is_directory=True)

    config_path = _write_yaml(
        tmp_path / "config.yaml",
        {
            "sources": [
                {
                    "name": "via-symlink",
                    "type": "local",
                    "path": str(symlink_path),
                }
            ],
        },
    )

    config = load_config(config_path)
    source = config.sources[0]
    assert isinstance(source, LocalSourceConfig)

    expected_realpath = Path(os.path.realpath(local_sample_skills_dir))
    assert source.path == expected_realpath
    # And specifically: not the symlink.
    assert source.path != symlink_path


def test_empty_sources_list_rejected(tmp_path: Path) -> None:
    """``sources: []`` is rejected — the server needs at least one."""
    config_path = _write_yaml(
        tmp_path / "config.yaml",
        {"sources": []},
    )

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_path)

    assert "sources" in str(exc_info.value)


def test_file_not_found_raises_configerror(tmp_path: Path) -> None:
    """Loading a non-existent path raises ConfigError, not FileNotFoundError."""
    missing = tmp_path / "no-such-config.yaml"

    with pytest.raises(ConfigError) as exc_info:
        load_config(missing)

    assert "not found" in str(exc_info.value) or str(missing) in str(exc_info.value)


def test_unknown_top_level_key_rejected(tmp_path: Path, local_sample_skills_dir: Path) -> None:
    """An unknown top-level key (typo) is rejected — extra='forbid'."""
    config_path = _write_yaml(
        tmp_path / "config.yaml",
        {
            "sources": [
                {
                    "name": "local",
                    "type": "local",
                    "path": str(local_sample_skills_dir),
                }
            ],
            "foo": "bar",
        },
    )

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_path)

    assert "foo" in str(exc_info.value) or "extra" in str(exc_info.value).lower()
