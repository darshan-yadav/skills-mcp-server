"""Integration tests: skills-sync against a real skills-mcp-server stdio process."""

from __future__ import annotations

import json
import socket
import sys
from pathlib import Path

import pytest

from skills_sync.core import sync_skills


def _free_tcp_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.mark.asyncio
async def test_sync_stdio_skill_with_declared_tools_v0_1(tmp_path: Path) -> None:
    """v0.1: no server-side tools — manifest keeps tools:; no split-brain note."""
    out_dir = tmp_path / "skills_out"
    config_file = tmp_path / "config.yaml"
    data_dir = tmp_path / "data"
    skills_dir = tmp_path / "skills"
    port = _free_tcp_port()

    skills_dir.mkdir()
    data_dir.mkdir()

    skill_mock = skills_dir / "test-skill"
    skill_mock.mkdir()
    manifest = """---
name: test-skill
description: Test skill description
tools:
  - name: test_tool
    description: Test
    script: scripts/run.py
---

Body text
"""
    (skill_mock / "SKILL.md").write_text(manifest, encoding="utf-8")
    scripts_dir = skill_mock / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "run.py").write_text("print('test')", encoding="utf-8")

    config_file.write_text(
        f"""
sources:
  - name: local
    type: local
    path: {skills_dir}
data_dir: {data_dir}
log_level: error
webhook_port: {port}
""",
        encoding="utf-8",
    )

    command = f"{sys.executable} -m skills_mcp_server run --config {config_file}"
    await sync_skills(command, out_dir)

    synced_skill = out_dir / "test-skill"
    assert synced_skill.is_dir()
    skill_md = (synced_skill / "SKILL.md").read_text(encoding="utf-8")
    assert "test-skill" in skill_md
    assert "Test skill description" in skill_md
    assert "tools:" in skill_md
    assert "shared skills server" not in skill_md

    meta = json.loads((out_dir / ".skills-sync-meta.json").read_text(encoding="utf-8"))
    assert meta["skills"]["test-skill"]["tools_registered"] == []

    assert not (out_dir / ".skills-sync-backup").exists()  # first sync: nothing to back up


@pytest.mark.asyncio
async def test_sync_stdio_instructions_only_skill(tmp_path: Path) -> None:
    """Skill without MCP tools keeps frontmatter and does not inject server note."""
    out_dir = tmp_path / "skills_out"
    config_file = tmp_path / "config.yaml"
    data_dir = tmp_path / "data"
    skills_dir = tmp_path / "fixtures"
    port = _free_tcp_port()

    here = Path(__file__).resolve().parent
    fixture_skills = here.parent.parent / "tests" / "fixtures" / "skills" / "local-sample"
    skills_dir.symlink_to(fixture_skills, target_is_directory=True)
    data_dir.mkdir()

    config_file.write_text(
        f"""
sources:
  - name: local
    type: local
    path: {skills_dir}
data_dir: {data_dir}
log_level: error
webhook_port: {port}
""",
        encoding="utf-8",
    )

    command = f"{sys.executable} -m skills_mcp_server run --config {config_file}"
    await sync_skills(command, out_dir)

    hello = out_dir / "hello-world" / "SKILL.md"
    assert hello.is_file()
    text = hello.read_text(encoding="utf-8")
    assert "hello-world" in text
    assert "shared skills server" not in text
