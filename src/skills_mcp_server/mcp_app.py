"""MCP transport layer for the skills server.

Exposes loaded skills as MCP Prompts and Resources.
"""
from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import mcp.types as types
from mcp.server import Server

from skills_mcp_server.registry import SkillRegistry

logger = logging.getLogger(__name__)


def create_mcp_server(registry: SkillRegistry) -> Server:
    """Create and configure the MCP Server instance."""
    app = Server("skills-mcp-server")

    @app.list_prompts()
    async def handle_list_prompts() -> list[types.Prompt]:
        prompts = []
        for bundle in registry.iter_bundles():
            prompts.append(
                types.Prompt(
                    name=bundle.manifest.name,
                    description=bundle.manifest.description,
                    arguments=[],
                )
            )
        return prompts

    @app.get_prompt()
    async def handle_get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
        bundle = registry.get_bundle(name)
        if not bundle:
            raise ValueError(f"Unknown prompt: {name}")

        return types.GetPromptResult(
            description=bundle.manifest.description,
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=bundle.body,
                    )
                )
            ]
        )

    @app.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        resources = []
        for bundle in registry.iter_bundles():
            for res_path in bundle.resources:
                uri = f"skill://{bundle.source_name}/{bundle.slug}/{res_path}"
                mime_type, _ = mimetypes.guess_type(res_path.name)
                resources.append(
                    types.Resource(
                        uri=uri,
                        name=f"{bundle.manifest.name} - {res_path.name}",
                        mimeType=mime_type or "application/octet-stream",
                    )
                )
        return resources

    @app.read_resource()
    async def handle_read_resource(uri: str) -> str | bytes:
        # Some MCP hosts pass pydantic AnyUrl, others pass str. Cast safely.
        parsed = urlparse(str(uri))
        if parsed.scheme != "skill":
            raise ValueError(f"Unsupported URI scheme: {parsed.scheme}")
        
        parts = parsed.netloc + parsed.path
        parts_list = parts.split("/", 2)
        if len(parts_list) < 3:
            raise ValueError(f"Invalid resource URI: {uri}")
        
        source_name, slug, res_path_str = parts_list
        
        target_bundle = None
        for bundle in registry.iter_bundles():
            if bundle.source_name == source_name and bundle.slug == slug:
                target_bundle = bundle
                break
                
        if not target_bundle:
            raise ValueError(f"Resource not found: {uri}")
            
        target_path = Path(res_path_str)
        if target_path not in target_bundle.resources:
            raise ValueError(f"Resource not found or access denied: {uri}")
            
        real_path = target_bundle.bundle_path / target_path
        try:
            return real_path.read_bytes().decode('utf-8')
        except UnicodeDecodeError:
            return real_path.read_bytes()

    @app.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        tools = []
        tools.append(
            types.Tool(
                name="refresh_skills",
                description="Trigger a background reload of all skill sources. Use this after merging a PR to sync the server cache immediately.",
                inputSchema={"type": "object", "properties": {}}
            )
        )
        
        for bundle, tool_man in registry.iter_tools():
            schema = tool_man.arguments or {"type": "object", "properties": {}}
            tools.append(
                types.Tool(
                    name=tool_man.name,
                    description=tool_man.description,
                    inputSchema=schema
                )
            )
        return tools

    @app.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        if name == "refresh_skills":
            # For now, do an in-process reload. T29 will wire this to the admin IPC.
            registry.reload()
            return [types.TextContent(type="text", text="Skills reloaded successfully.")]

        tool_entry = registry.get_tool(name)
        if not tool_entry:
            raise ValueError(f"Unknown tool: {name}")
            
        bundle, tool_man = tool_entry
        from skills_mcp_server.executor import execute_tool, ExecutorError
        
        args = arguments or {}
        try:
            result = await execute_tool(bundle.bundle_path, tool_man.script, args)
        except ExecutorError as e:
            return [types.TextContent(type="text", text=f"Execution error: {e}")]
            
        mcp_content = []
        for c in result.content:
            if c.type == "text":
                mcp_content.append(types.TextContent(type="text", text=c.text))
            # Other types could be mapped here if needed
        return mcp_content

    return app
