"""Command-line interface."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from skills_mcp_server.config import load_config, ConfigError
from skills_mcp_server.registry import SkillRegistry
from skills_mcp_server.mcp_app import create_mcp_server

logger = logging.getLogger(__name__)

def main() -> int:
    parser = argparse.ArgumentParser(prog="skills-mcp-server")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the MCP stdio server")
    run_parser.add_argument("--config", type=Path, default=Path("config.yaml"), help="Path to config file")

    init_parser = subparsers.add_parser("init", help="Create a default config.yaml")
    init_parser.add_argument("dir", type=Path, nargs="?", default=Path("."), help="Directory to initialize")

    selftest_parser = subparsers.add_parser("selftest", help="Validate config and load all skills")
    selftest_parser.add_argument("--config", type=Path, default=Path("config.yaml"), help="Path to config file")

    reload_parser = subparsers.add_parser("reload", help="Trigger a live daemon reload via IPC")
    reload_parser.add_argument("--config", type=Path, default=Path("config.yaml"), help="Path to config file")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.command == "init":
        config_path = args.dir / "config.yaml"
        if config_path.exists():
            print(f"Error: {config_path} already exists.", file=sys.stderr)
            return 1
        config_path.write_text("sources:\n  - name: local-dev\n    type: local\n    path: ./skills\ndata_dir: ./data\nlog_level: info\n")
        print(f"Initialized {config_path}")
        return 0

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 1
        
    logging.getLogger().setLevel(config.log_level.upper())

    sources = []
    for s_conf in config.sources:
        if s_conf.type == "local":
            from skills_mcp_server.sources.local import LocalSource
            try:
                sources.append(LocalSource(s_conf.name, s_conf.path))
            except Exception as e:
                logger.error(e)
        elif s_conf.type == "git":
            from skills_mcp_server.sources.git import GitSource
            try:
                sources.append(GitSource(
                    s_conf.name, s_conf.url, s_conf.ref, config.data_dir, s_conf.subpath
                ))
            except Exception as e:
                logger.error(e)

    registry = SkillRegistry(sources)

    if args.command == "selftest":
        print("Running selftest...")
        registry.reload()
        print("Selftest complete.")
        return 0

    if args.command == "run":
        registry.reload()
        app = create_mcp_server(registry)
        
        from aiohttp import web
        from mcp.server.stdio import stdio_server
        
        async def webhook_reload(request):
            if config.webhook_secret:
                auth = request.headers.get("Authorization")
                if auth != f"Bearer {config.webhook_secret}":
                    return web.Response(status=401, text="Unauthorized")
            logger.info("Webhook triggered reload")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, registry.reload)
            return web.Response(text="Reloaded")
            
        async def admin_reload(request):
            # Admin commands must come from localhost
            if request.remote not in ("127.0.0.1", "::1", "localhost"):
                return web.Response(status=403, text="Forbidden")
            logger.info("Admin triggered reload")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, registry.reload)
            return web.Response(text="Reloaded")

        async def run_daemons():
            webapp = web.Application()
            webapp.router.add_post("/webhook/reload", webhook_reload)
            webapp.router.add_post("/admin/reload", admin_reload)
            
            runner = web.AppRunner(webapp)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", config.webhook_port)
            await site.start()
            logger.info("Started admin/webhook server on port %d", config.webhook_port)
            
            async with stdio_server() as (read_stream, write_stream):
                await app.run(read_stream, write_stream, app.create_initialization_options())
                
            await runner.cleanup()
        
        try:
            asyncio.run(run_daemons())
        except KeyboardInterrupt:
            pass
        return 0

    if args.command == "reload":
        import urllib.request
        url = f"http://127.0.0.1:{config.webhook_port}/admin/reload"
        try:
            req = urllib.request.Request(url, method="POST")
            with urllib.request.urlopen(req) as response:
                print(f"Reload successful: {response.read().decode('utf-8')}")
                return 0
        except Exception as e:
            print(f"Failed to trigger reload: {e}", file=sys.stderr)
            return 1

    return 0
