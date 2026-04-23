import asyncio
from pathlib import Path
import pytest
import aiohttp
from aiohttp import web
from skills_mcp_server.config import Config, LocalSourceConfig
from skills_mcp_server.registry import SkillRegistry

@pytest.mark.asyncio
async def test_webhook_and_admin_endpoints(tmp_path: Path):
    source_cfg = LocalSourceConfig(name="test", type="local", path=tmp_path)
    config = Config(
        sources=[source_cfg],
        data_dir=tmp_path / "data",
        log_level="info",
        refresh_interval_seconds=0,
        webhook_port=18080, # Use a high port for testing
        webhook_secret="test-secret"
    )
    
    registry = SkillRegistry([])
    
    async def webhook_reload(request):
        if config.webhook_secret:
            auth = request.headers.get("Authorization")
            if auth != f"Bearer {config.webhook_secret}":
                return web.Response(status=401, text="Unauthorized")
        return web.Response(text="Reloaded")
        
    async def admin_reload(request):
        if request.remote not in ("127.0.0.1", "::1", "localhost"):
            return web.Response(status=403, text="Forbidden")
        return web.Response(text="Reloaded")

    webapp = web.Application()
    webapp.router.add_post("/webhook/reload", webhook_reload)
    webapp.router.add_post("/admin/reload", admin_reload)
    
    runner = web.AppRunner(webapp)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", config.webhook_port)
    await site.start()
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test 1: Admin reload (Success)
            async with session.post(f"http://127.0.0.1:{config.webhook_port}/admin/reload") as resp:
                assert resp.status == 200
                assert await resp.text() == "Reloaded"
                
            # Test 2: Webhook without auth (Fail)
            async with session.post(f"http://127.0.0.1:{config.webhook_port}/webhook/reload") as resp:
                assert resp.status == 401
                
            # Test 3: Webhook with valid auth (Success)
            headers = {"Authorization": "Bearer test-secret"}
            async with session.post(f"http://127.0.0.1:{config.webhook_port}/webhook/reload", headers=headers) as resp:
                assert resp.status == 200
                assert await resp.text() == "Reloaded"
    finally:
        await runner.cleanup()
