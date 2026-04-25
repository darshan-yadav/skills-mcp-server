"""HTTP (SSE) transport for central MCP deployment.

Exposes the same MCP server as stdio mode, using the upstream ``SseServerTransport``
pattern (GET ``/sse``, POST JSON-RPC to ``/messages/?session_id=…``). Operators are
expected to place the service behind network ACLs, VPN, or a reverse proxy; v0.1
does not add application-layer auth on these routes.
"""

from __future__ import annotations

import asyncio
import logging

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route

from skills_mcp_server.admin_ui import create_admin_routes
from skills_mcp_server.config import Config
from skills_mcp_server.registry import SkillRegistry

logger = logging.getLogger(__name__)


def create_http_starlette_app(*, mcp_server: Server, registry: SkillRegistry, config: Config) -> Starlette:
    """Build a Starlette app: MCP over SSE plus webhook/admin reload endpoints."""

    sse_transport = SseServerTransport(
        "/messages/",
        security_settings=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    async def health(_request: Request) -> Response:
        return Response("ok\n", media_type="text/plain")

    async def handle_sse(request: Request) -> Response:
        async with sse_transport.connect_sse(
            request.scope,
            request.receive,
            request._send,  # noqa: SLF001 — Starlette wires ASGI send here; MCP examples use the same.
        ) as streams:
            await mcp_server.run(
                streams[0],
                streams[1],
                mcp_server.create_initialization_options(),
            )
        return Response()

    async def webhook_reload(request: Request) -> Response:
        if config.webhook_secret:
            auth = request.headers.get("Authorization")
            if auth != f"Bearer {config.webhook_secret}":
                return Response("Unauthorized", status_code=401)
        logger.info("Webhook triggered reload")
        await asyncio.get_running_loop().run_in_executor(None, registry.reload)
        return Response("Reloaded", media_type="text/plain")

    async def admin_reload(_request: Request) -> Response:
        # Central mode: no localhost gate — restrict via security groups / private networks.
        logger.info("Admin triggered reload (HTTP)")
        await asyncio.get_running_loop().run_in_executor(None, registry.reload)
        return Response("Reloaded", media_type="text/plain")

    routes: list[Route | Mount] = [
        Route("/health", endpoint=health, methods=["GET"]),
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Mount("/messages/", app=sse_transport.handle_post_message),
        Route("/webhook/reload", endpoint=webhook_reload, methods=["POST"]),
        Route("/admin/reload", endpoint=admin_reload, methods=["POST"]),
    ]
    routes.extend(create_admin_routes(registry=registry, config=config))

    return Starlette(routes=routes)
