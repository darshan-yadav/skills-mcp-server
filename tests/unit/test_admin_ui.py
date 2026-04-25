from __future__ import annotations

import io
import zipfile
from pathlib import Path

from starlette.testclient import TestClient

from skills_mcp_server.config import Config, LocalSourceConfig
from skills_mcp_server.http_transport import create_http_starlette_app
from skills_mcp_server.mcp_app import create_mcp_server
from skills_mcp_server.registry import SkillRegistry
from skills_mcp_server.sources.local import LocalSource


def _make_app(tmp_path: Path):
    skills_root = tmp_path / "skills"
    bundle = skills_root / "hello"
    bundle.mkdir(parents=True)
    (bundle / "SKILL.md").write_text("---\nname: hello\ndescription: Hi\n---\n\nBody\n", encoding="utf-8")
    (bundle / "REFERENCE.md").write_text("# Reference\n", encoding="utf-8")
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    cfg = Config(
        sources=[LocalSourceConfig(name="local", type="local", path=skills_root)],
        data_dir=data_dir,
        log_level="info",
        refresh_interval_seconds=0,
        http_host="127.0.0.1",
        http_port=19001,
        admin_ui={
            "enabled": True,
            "username": "admin",
            "password": "secret-password",
            "session_secret": "session-secret-for-tests",
        },
    )
    registry = SkillRegistry([LocalSource("local", skills_root)])
    registry.reload()
    app = create_http_starlette_app(mcp_server=create_mcp_server(registry), registry=registry, config=cfg)
    return TestClient(app), skills_root


def _login(client: TestClient) -> None:
    response = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret-password", "next": "/admin"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_admin_dashboard_requires_login(tmp_path: Path) -> None:
    client, _skills_root = _make_app(tmp_path)

    response = client.get("/admin", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/admin/login")


def test_admin_can_edit_skill_md_and_create_new_skill(tmp_path: Path) -> None:
    client, skills_root = _make_app(tmp_path)
    _login(client)

    dashboard = client.get("/admin")
    assert dashboard.status_code == 200
    assert "Skills Control Room" in dashboard.text
    assert "hello" in dashboard.text

    editor = client.get("/admin/sources/local/bundles/hello")
    assert editor.status_code == 200
    assert "REFERENCE.md" in editor.text

    save = client.post(
        "/admin/sources/local/bundles/hello",
        data={
            "file_path": "SKILL.md",
            "content": "---\nname: hello\ndescription: Updated description\n---\n\nUpdated body\n",
        },
        follow_redirects=False,
    )
    assert save.status_code == 303
    saved_text = (skills_root / "hello" / "SKILL.md").read_text(encoding="utf-8")
    assert "Updated description" in saved_text

    create = client.post(
        "/admin/new",
        data={
            "source_name": "local",
            "relative_path": "roles/new-skill",
            "name": "new-skill",
            "description": "Create a new skill from the admin console.",
            "body": "# New skill\n\nCreated in tests.\n",
            "extra_yaml": "version: 0.1.0",
        },
        follow_redirects=False,
    )
    assert create.status_code == 303
    assert (skills_root / "roles" / "new-skill" / "SKILL.md").exists()


def test_admin_can_upload_bundle_zip_and_bundle_file(tmp_path: Path) -> None:
    client, skills_root = _make_app(tmp_path)
    _login(client)

    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr(
            "imports/uploaded-skill/SKILL.md",
            "---\nname: uploaded-skill\ndescription: Uploaded through zip\n---\n\nUploaded body\n",
        )
        archive.writestr("imports/uploaded-skill/REFERENCE.md", "# Uploaded reference\n")

    upload_bundle = client.post(
        "/admin/sources/local/uploads/bundle",
        files={"bundle_zip": ("skill.zip", archive_bytes.getvalue(), "application/zip")},
        follow_redirects=False,
    )
    assert upload_bundle.status_code == 303
    assert (skills_root / "imports" / "uploaded-skill" / "SKILL.md").exists()

    upload_file = client.post(
        "/admin/sources/local/bundles/hello/files/upload",
        data={"target_subdir": "references"},
        files={"asset": ("NOTES.md", b"# Notes\n", "text/markdown")},
        follow_redirects=False,
    )
    assert upload_file.status_code == 303
    assert (skills_root / "hello" / "references" / "NOTES.md").read_text(encoding="utf-8") == "# Notes\n"
