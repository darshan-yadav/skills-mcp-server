import pytest
from mcp.server import Server
from skills_mcp_server.registry import SkillRegistry
from skills_mcp_server.mcp_app import create_mcp_server
from skills_mcp_server.models import SkillBundle, SkillManifest, ToolManifest
from pathlib import Path
import mcp.types as types

@pytest.mark.asyncio
async def test_mcp_end_to_end(tmp_path):
    asset = tmp_path / "asset.png"
    asset.write_text("dummy")

    script = tmp_path / "test.py"
    script.write_text("import json\nprint(json.dumps({'isError': False, 'content': [{'type': 'text', 'text': 'tool output'}]}))")

    tool_man = ToolManifest(name="test-tool", description="Test Tool", script="test.py", arguments={"type": "object", "properties": {}})

    bundle1 = SkillBundle(
        source_name="local-dev",
        slug="test-skill",
        bundle_path=tmp_path,
        manifest=SkillManifest(name="test-prompt", description="Test Desc", tools=(tool_man,)),
        body="This is a test body",
        resources=(Path("asset.png"),)
    )
    
    class MockRegistry:
        def iter_bundles(self): yield bundle1
        def get_bundle(self, name): return bundle1 if name == "test-prompt" else None
        def iter_tools(self): yield bundle1, tool_man
        def get_tool(self, name): return (bundle1, tool_man) if name == "test-tool" else None
        def reload(self): pass
        
    app = create_mcp_server(MockRegistry())
    
    # Prompts
    prompts_result = await app.request_handlers[types.ListPromptsRequest](
        types.ListPromptsRequest(method="prompts/list")
    )
    assert len(prompts_result.root.prompts) == 1
    assert prompts_result.root.prompts[0].name == "test-prompt"
    
    get_res = await app.request_handlers[types.GetPromptRequest](
        types.GetPromptRequest(method="prompts/get", params=types.GetPromptRequestParams(name="test-prompt"))
    )
    assert get_res.root.messages[0].content.text == "This is a test body"
    
    # Resources
    res_list = await app.request_handlers[types.ListResourcesRequest](
        types.ListResourcesRequest(method="resources/list")
    )
    assert len(res_list.root.resources) == 1
    
    # Tools
    tools_result = await app.request_handlers[types.ListToolsRequest](
        types.ListToolsRequest(method="tools/list")
    )
    # 2 tools: built-in refresh_skills + test-tool
    assert len(tools_result.root.tools) == 2
    assert tools_result.root.tools[0].name == "refresh_skills"
    assert tools_result.root.tools[1].name == "test-tool"
    
    # Call tool
    call_res = await app.request_handlers[types.CallToolRequest](
        types.CallToolRequest(method="tools/call", params=types.CallToolRequestParams(name="test-tool", arguments={}))
    )
    assert len(call_res.root.content) == 1
    assert call_res.root.content[0].text == "tool output"

    # Call refresh_skills
    call_refresh = await app.request_handlers[types.CallToolRequest](
        types.CallToolRequest(method="tools/call", params=types.CallToolRequestParams(name="refresh_skills", arguments={}))
    )
    assert "reloaded successfully" in call_refresh.root.content[0].text
