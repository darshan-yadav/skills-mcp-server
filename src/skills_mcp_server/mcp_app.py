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

CallToolResult = list[types.TextContent | types.ImageContent | types.EmbeddedResource]


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
                    ),
                )
            ],
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
            return real_path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            return real_path.read_bytes()

    @app.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """v0.1: four server tools only — no per-skill execution tools (§8.3–§8.4)."""
        return [
            types.Tool(
                name="list_skills",
                description=(
                    "Returns the full skill index — name, description, version, source, "
                    "git ref, tags, tools_registered (empty in v0.1). Callable by any client."
                ),
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="get_skill_manifest",
                description="Returns the parsed frontmatter for one skill.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the skill",
                        }
                    },
                    "required": ["name"],
                },
            ),
            types.Tool(
                name="reload",
                description=(
                    "Triggers an immediate reload of all skill sources "
                    "(re-scan local, pull git). May perform outbound git fetches."
                ),
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="server_info",
                description="Returns server version, loaded-source summary, counts.",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @app.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None) -> CallToolResult:
        args = arguments or {}
        if name == "reload":
            registry.reload()
            return [types.TextContent(type="text", text="Skills reloaded successfully.")]

        if name == "list_skills":
            skills = []
            for bundle in registry.iter_bundles():
                # v0.1: no server-side skill tools — always empty (phase 2: §16.1).
                tools_registered: list[str] = []
                extra = bundle.manifest.extra or {}
                version = extra.get("version", "0.0.0")
                tags = extra.get("tags") or []
                skills.append(
                    {
                        "name": bundle.manifest.name,
                        "version": version if isinstance(version, str) else "0.0.0",
                        "description": bundle.manifest.description,
                        "source": bundle.source_name,
                        "git_ref": bundle.commit_sha or "local",
                        "tags": tags if isinstance(tags, list) else [],
                        "tools_registered": tools_registered,
                    }
                )
            import json

            return [types.TextContent(type="text", text=json.dumps(skills))]

        if name == "get_skill_manifest":
            skill_name = args.get("name")
            if not skill_name:
                raise ValueError("Missing 'name' argument")
            bundle = registry.get_bundle(skill_name)
            if not bundle:
                raise ValueError(f"Skill not found: {skill_name}")
            import json
            from dataclasses import asdict

            return [types.TextContent(type="text", text=json.dumps(asdict(bundle.manifest)))]

        if name == "server_info":
            info = {
                "version": "0.1",
                "skills_count": sum(1 for _ in registry.iter_bundles()),
                "sources_count": len(registry.sources),
            }
            import json

            return [types.TextContent(type="text", text=json.dumps(info))]

        raise ValueError(f"Unknown tool: {name}")

    return app
