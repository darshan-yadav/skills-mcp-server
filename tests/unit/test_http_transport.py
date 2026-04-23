"""HTTP (SSE) Starlette app — smoke routes without a full MCP client."""

from pathlib import Path

from starlette.testclient import TestClient

from skills_mcp_server.config import Config, LocalSourceConfig
from skills_mcp_server.http_transport import create_http_starlette_app
from skills_mcp_server.mcp_app import create_mcp_server
from skills_mcp_server.registry import SkillRegistry
from skills_mcp_server.sources.local import LocalSource


def test_http_app_health_and_admin_reload(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    bundle = skills_root / "hello"
    bundle.mkdir(parents=True)
    (bundle / "SKILL.md").write_text("---\nname: hello\ndescription: Hi\n---\n\nBody\n")
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    cfg = Config(
        sources=[LocalSourceConfig(name="local", type="local", path=skills_root)],
        data_dir=data_dir,
        log_level="info",
        refresh_interval_seconds=0,
        webhook_port=18081,
        http_host="127.0.0.1",
        http_port=18082,
    )
    registry = SkillRegistry([LocalSource("local", skills_root)])
    registry.reload()
    mcp = create_mcp_server(registry)
    app = create_http_starlette_app(mcp_server=mcp, registry=registry, config=cfg)
    client = TestClient(app)

    r = client.get("/health")
    assert r.status_code == 200
    assert r.text == "ok\n"

    r2 = client.post("/admin/reload")
    assert r2.status_code == 200
    assert r2.text == "Reloaded"


def test_http_webhook_requires_bearer_when_configured(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    bundle = skills_root / "hello"
    bundle.mkdir(parents=True)
    (bundle / "SKILL.md").write_text("---\nname: hello\ndescription: Hi\n---\n\nBody\n")
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    cfg = Config(
        sources=[LocalSourceConfig(name="local", type="local", path=skills_root)],
        data_dir=data_dir,
        log_level="info",
        refresh_interval_seconds=0,
        webhook_secret="s3cret",
        http_port=18083,
    )
    registry = SkillRegistry([LocalSource("local", skills_root)])
    registry.reload()
    mcp = create_mcp_server(registry)
    app = create_http_starlette_app(mcp_server=mcp, registry=registry, config=cfg)
    client = TestClient(app)

    assert client.post("/webhook/reload").status_code == 401
    r = client.post("/webhook/reload", headers={"Authorization": "Bearer s3cret"})
    assert r.status_code == 200
