from pathlib import Path

import mcp.types as types
import pytest

from skills_mcp_server.mcp_app import create_mcp_server
from skills_mcp_server.models import SkillBundle, SkillManifest, ToolManifest


@pytest.mark.asyncio
async def test_mcp_end_to_end(tmp_path: Path) -> None:
    asset = tmp_path / "asset.png"
    asset.write_text("dummy")

    script = tmp_path / "test.py"
    script.write_text("print('x')")

    tool_man = ToolManifest(
        name="test-tool",
        description="Test Tool",
        script="test.py",
        arguments={"type": "object", "properties": {}},
    )

    bundle1 = SkillBundle(
        source_name="local-dev",
        slug="test-skill",
        bundle_path=tmp_path,
        manifest=SkillManifest(name="test-prompt", description="Test Desc", tools=(tool_man,)),
        body="This is a test body",
        resources=(Path("asset.png"),),
    )

    class MockRegistry:
        def iter_bundles(self):
            yield bundle1

        def get_bundle(self, name):
            return bundle1 if name == "test-prompt" else None

        def iter_tools(self):
            yield bundle1, tool_man

        def get_tool(self, name):
            return (bundle1, tool_man) if name == "test-tool" else None

        def reload(self) -> None:
            pass

    app = create_mcp_server(MockRegistry())

    prompts_result = await app.request_handlers[types.ListPromptsRequest](
        types.ListPromptsRequest(method="prompts/list")
    )
    assert len(prompts_result.root.prompts) == 1
    assert prompts_result.root.prompts[0].name == "test-prompt"

    get_res = await app.request_handlers[types.GetPromptRequest](
        types.GetPromptRequest(
            method="prompts/get",
            params=types.GetPromptRequestParams(name="test-prompt"),
        )
    )
    assert get_res.root.messages[0].content.text == "This is a test body"

    res_list = await app.request_handlers[types.ListResourcesRequest](
        types.ListResourcesRequest(method="resources/list")
    )
    assert len(res_list.root.resources) == 1

    tools_result = await app.request_handlers[types.ListToolsRequest](types.ListToolsRequest(method="tools/list"))
    names = [t.name for t in tools_result.root.tools]
    assert names == ["list_skills", "get_skill_manifest", "reload", "server_info"]

    call_refresh = await app.request_handlers[types.CallToolRequest](
        types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(name="reload", arguments={}),
        )
    )
    assert "reloaded successfully" in call_refresh.root.content[0].text.lower()
