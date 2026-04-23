# Security Audit (v0.1)

## Findings

1.  **Symlink Traversal Bug (Fixed)**
    *   **Issue:** `_list_bundle_resources` checked if a symlink pointed to a valid file, but didn't verify that the resolved path was inside the bundle.
    *   **Resolution:** Enforced `os.path.realpath` boundary checking. Resolved symlinks that escape the `bundle_path` are now rejected safely.

2.  **Git Cache Contention (Fixed)**
    *   **Issue:** Multiple MCP stdio connections would spawn multiple `skills-mcp-server` instances attempting to `git clone` / `git fetch` the same repository concurrently.
    *   **Resolution:** Implemented `fcntl.flock` on a lockfile outside the `.git` directory (`/data/locks/<name>.lock`).

3.  **Git Cache Permissions (Phase 2 Pre-Hardening)**
    *   **Issue:** In Phase 2, `skills-mcp-server` will execute arbitrary subprocesses. If those subprocesses run under the same UID and the git cache is writable, the skill could mutate its own source code or other skills.
    *   **Resolution:** `GitSource` now actively strips the owner-write bit (`chmod u-w`) from the clone cache recursively immediately after pulling.

4.  **Process UID Escalation**
    *   **Issue:** Running as `root` inside the container increases the blast radius of any RCE or zero-day in python.
    *   **Resolution:** The Dockerfile runs as `appuser` (UID 1000) and is explicitly read-only rootfs compatible.

**Conclusion:** The codebase is cleared for the `v0.1` release.
