# Subprocess Execution Protocol (v0.2)

As part of Phase 2 (T22), `skills-mcp-server` transitions from a purely read-only provider to an execution orchestrator for skill-bundled scripts. To maintain the highest security guarantees and prevent blocking the `mcp.server.Server` event loop, script execution runs out-of-process via standard OS `subprocess`.

## JSON-over-stdio Protocol

When an MCP client invokes `call_tool(name, arguments)`, the server performs the following:

1.  **Resolution:** Looks up the requested tool in the `SkillRegistry`. Identifies the `bundle_path` and the `script` path (e.g., `scripts/tool.py`).
2.  **Invocation:** Spawns `python {bundle_path}/{script}` as a fresh process.
    *   **Stdin:** The server passes the exact JSON `arguments` map into the subprocess's `stdin`.
    *   **Cwd:** The Current Working Directory is set to `bundle_path`.
3.  **Output Parsing:** The script executes its logic. It *MUST* print a single valid JSON object to its `stdout` representing the result.
    *   `stderr` is captured and passed through to the server's logs (useful for `print()` debugging by the skill author).
4.  **Schema:** The `stdout` JSON MUST match the following structure:
    ```json
    {
      "isError": false,
      "content": [
        {
          "type": "text",
          "text": "The result of the tool execution"
        }
      ]
    }
    ```
5.  **Timeouts:** The subprocess is hard-capped at 60 seconds (configurable). If it exceeds this, the server sends `SIGTERM`, waits 2 seconds, then `SIGKILL`, and returns a timeout error to the MCP client.

## Security Boundaries

*   The process executes using the server's Python interpreter and installed packages (`sys.executable`). (Per-skill venvs are deferred to Phase 4).
*   Because git cache paths are enforced as read-only (`chmod u-w`), the script cannot mutate its own source code on disk during execution.
*   Because `flock(2)` is used on pulls, executing scripts are guaranteed not to be overwritten mid-execution by a scheduled pull.
