# Security Audit (v0.2 - Phase 2)

## Scope
This audit focuses on the new capabilities introduced in Phase 2:
1. Subprocess Execution (`executor.py`)
2. Webhook Ingress (`/webhook/reload`)
3. Admin IPC Socket (`/admin/reload`)

## Findings

1. **Subprocess Isolation Escape Risks (Low)**
   * **Mechanism:** Tools are executed via `asyncio.create_subprocess_exec` with `cwd` pinned to the bundle path.
   * **Safeguards:** `os.path.realpath` is enforced on the `script` path to guarantee it resides strictly inside the bundle. It is physically impossible to execute an arbitrary system binary or a script in a sibling skill.
   * **Limitation (Phase 4):** Subprocesses share the server container's Python environment. Malicious scripts could read container environment variables or exhaust container memory (no cgroups yet).

2. **Webhook Authentication (Medium/Accepted)**
   * **Mechanism:** Simple Bearer token over HTTP (`Authorization: Bearer <secret>`).
   * **Safeguards:** The token is validated using strict string equality.
   * **Recommendation:** HTTPS must be terminated at a proxy/load-balancer in front of the container to prevent token interception.

3. **Admin IPC Payload Injection (None)**
   * **Mechanism:** The `cli.py` sends an empty POST request to `127.0.0.1:webhook_port/admin/reload`.
   * **Safeguards:** The handler strictly enforces `request.remote in ("127.0.0.1", "::1", "localhost")`. Remote clients cannot trigger the admin endpoint even if the port is exposed on `0.0.0.0`.

**Conclusion:** The codebase is cleared for the `v0.2` release.
