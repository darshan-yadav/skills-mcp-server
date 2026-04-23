import asyncio
import sys
from pathlib import Path

import pytest

from skills_mcp_server.executor import ExecutorError, execute_tool

@pytest.mark.asyncio
async def test_execute_success(tmp_path: Path):
    script_path = tmp_path / "script.py"
    script_path.write_text(
        "import sys, json\n"
        "args = json.load(sys.stdin)\n"
        "print(json.dumps({'isError': False, 'content': [{'type': 'text', 'text': f'Hello {args[\"name\"]}'}]}))\n"
    )
    
    result = await execute_tool(tmp_path, "script.py", {"name": "World"})
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].text == "Hello World"

@pytest.mark.asyncio
async def test_execute_timeout(tmp_path: Path):
    script_path = tmp_path / "script.py"
    script_path.write_text(
        "import time\n"
        "time.sleep(10)\n"
    )
    
    # We set a very short timeout of 0.1s
    result = await execute_tool(tmp_path, "script.py", {}, timeout=0.1)
    assert result.isError
    assert "timed out" in result.content[0].text

@pytest.mark.asyncio
async def test_execute_exit_code(tmp_path: Path):
    script_path = tmp_path / "script.py"
    script_path.write_text(
        "import sys\n"
        "print('this is an error', file=sys.stderr)\n"
        "sys.exit(1)\n"
    )
    
    result = await execute_tool(tmp_path, "script.py", {})
    assert result.isError
    assert "exited with code 1" in result.content[0].text
    assert "this is an error" in result.content[0].text

@pytest.mark.asyncio
async def test_execute_invalid_json(tmp_path: Path):
    script_path = tmp_path / "script.py"
    script_path.write_text(
        "print('this is just text')\n"
    )
    
    result = await execute_tool(tmp_path, "script.py", {})
    assert result.isError
    assert "Failed to parse script output" in result.content[0].text
    assert "this is just text" in result.content[0].text

@pytest.mark.asyncio
async def test_execute_escape_boundary(tmp_path: Path):
    # The script is outside the bundle
    outside_script = tmp_path.parent / "outside.py"
    outside_script.write_text("print('hacked')")
    
    try:
        with pytest.raises(ExecutorError, match="escapes bundle directory"):
            await execute_tool(tmp_path, "../outside.py", {})
    finally:
        if outside_script.exists():
            outside_script.unlink()

@pytest.mark.asyncio
async def test_execute_missing_script(tmp_path: Path):
    with pytest.raises(ExecutorError, match="not found in bundle"):
        await execute_tool(tmp_path, "missing.py", {})
