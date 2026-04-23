"""Subprocess execution engine for skill tools."""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ToolResultContent(BaseModel):
    type: str
    text: str


class ToolResult(BaseModel):
    isError: bool = False
    content: list[ToolResultContent]


class ExecutorError(Exception):
    """Raised when execution fails before or during script invocation."""

    pass


async def execute_tool(
    bundle_path: Path, script_rel_path: str, arguments: dict[str, Any], timeout: float = 60.0
) -> ToolResult:
    """Execute a python script in a subprocess.

    Args:
        bundle_path: Absolute realpath to the skill bundle directory.
        script_rel_path: Relative path to the script inside the bundle.
        arguments: JSON-serializable arguments to pass to the script via stdin.
        timeout: Maximum wall-clock time in seconds.
    """
    script_full_path = bundle_path / script_rel_path
    bundle_str = str(bundle_path)

    # Boundary check
    try:
        resolved_script = script_full_path.resolve(strict=True)
        resolved_str = str(resolved_script)
        if resolved_str != bundle_str and not resolved_str.startswith(bundle_str + "/"):
            raise ExecutorError("Script path escapes bundle directory.")
    except FileNotFoundError as exc:
        raise ExecutorError(f"Script {script_rel_path} not found in bundle.") from exc

    cmd = [sys.executable, str(resolved_script)]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=bundle_str,
        )
    except Exception as exc:
        raise ExecutorError(f"Failed to spawn subprocess: {exc}") from exc

    payload = json.dumps(arguments).encode("utf-8")

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(input=payload), timeout=timeout)
    except TimeoutError:
        # Hard kill on timeout
        try:
            process.terminate()
            await asyncio.sleep(0.5)
            if process.returncode is None:
                process.kill()
        except OSError:
            pass
        return ToolResult(
            isError=True, content=[ToolResultContent(type="text", text=f"Execution timed out after {timeout} seconds.")]
        )

    if stderr:
        logger.debug("Subprocess stderr: %s", stderr.decode("utf-8", errors="replace"))

    if process.returncode != 0:
        err = stderr.decode("utf-8", errors="replace")
        msg = f"Process exited with code {process.returncode}. Stderr: {err}"
        return ToolResult(
            isError=True,
            content=[ToolResultContent(type="text", text=msg)],
        )

    # Parse stdout
    stdout_str = stdout.decode("utf-8", errors="replace").strip()
    if not stdout_str:
        return ToolResult(
            isError=True,
            content=[ToolResultContent(type="text", text="Process returned no output. Expected a JSON object.")],
        )

    try:
        data = json.loads(stdout_str)
        return ToolResult.model_validate(data)
    except json.JSONDecodeError as e:
        return ToolResult(
            isError=True,
            content=[
                ToolResultContent(
                    type="text", text=f"Failed to parse script output as JSON: {e}\\nRaw output: {stdout_str}"
                )
            ],
        )
    except Exception as e:
        return ToolResult(
            isError=True,
            content=[
                ToolResultContent(
                    type="text",
                    text=f"Script output did not match expected ToolResult schema: {e}\\nRaw output: {stdout_str}",
                )
            ],
        )
