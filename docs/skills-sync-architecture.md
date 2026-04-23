# skills-sync architecture (v0.1)

Companion CLI that materialises skills from `skills-mcp-server` into `~/.claude/skills/<name>/` so Claude Code’s native description-based auto-trigger works. Normative behaviour is defined in SPEC §17; this document is the engineering view for T35.

## Components

| Piece | Role |
|--------|------|
| `skills_sync.cli` | `argparse` entry: `pull --from … --to …` plus optional `--auth-header`, `--dry-run`, `--debug`. |
| `skills_sync.core.sync_skills` | Async orchestration: MCP transport → `_perform_sync`. |
| MCP client | `mcp` SDK: `stdio_client` (shape B) or `sse_client` (shape A, `GET {base}/sse`). |
| `ClientSession` | `initialize`, `list_prompts`, `list_resources`, `list_tools`, `call_tool` (`list_skills`, `get_skill_manifest`), `get_prompt`, `read_resource`. |

## Argument parsing (`pull`)

- **`--from`**: Either an `http(s)://` base URL (SSE transport; optional `--auth-header "Header-Name: value"`), or a **shell tokenisation** of a stdio launch command (e.g. `python -m skills_mcp_server run --config /path/config.yaml`). The stdio branch uses `shlex.split` and `StdioServerParameters`.
- **`--to`**: Target root (expanded with `Path.expanduser`), e.g. `~/.claude/skills`.
- **`--dry-run`**: Connects and walks prompts; logs intent; does not write files or meta.
- **`--debug`**: Tracebacks on failure.

## Conflict policy: server wins (SPEC §17.1)

Before materialising each skill `S`, if `to/S` already exists, the entire directory is **moved** (not copied) to:

`to/.skills-sync-backup/<UTC-timestamp>/S/`

Then a fresh `S/` is created from server content. Nothing is deleted without a prior backup under `.skills-sync-backup/`. Same timestamp bucket is used for all skills in one `pull` invocation.

## Identity / idempotency

After a successful pull (non–dry-run), the CLI writes `to/.skills-sync-meta.json`:

- `synced_at` (ISO-8601 UTC)
- `from` (the `--from` string)
- `target` (resolved path)
- `skills`: per-skill snapshot from `list_skills` (`source`, `git_ref`, `version`, `tools_registered`)

This supports future `--dry-run` diffs and operator audits.

## Materialisation algorithm

1. `list_prompts` → one folder per prompt `name`.
2. For each skill, `call_tool("get_skill_manifest", {"name": …})` → JSON manifest (round-trip via server’s parsed model).
3. `get_prompt(name)` → markdown body (below frontmatter on the server).
4. Merge manifest into YAML frontmatter; append body to produce `SKILL.md`.
5. `list_resources` → for each `skill://…` URI whose slug matches the skill, `read_resource` and write **relative path** from URI (skip `SKILL.md` to avoid clobbering the composed file).

## Split-brain avoidance (SPEC §17.4, phase 2+)

When the server registers MCP tools for a skill (same names as declared in the manifest `tools:` list), the materialised bundle must not invite **local** script execution:

1. `list_skills` provides `tools_registered` per skill (authoritative).
2. If every declared tool name is in `tools_registered`, **strip** the `tools:` block from the written manifest, **skip** materialising paths under `scripts/`, and **prepend** a short note to the body pointing agents at MCP tool invocation.

If `list_skills` fails, the implementation falls back to matching declared tool names against `list_tools` minus built-in server tools.

## Out of scope (v0.1)

- Watch mode / list-changed subscriptions (phase 3, SPEC §17.3).
- Cursor / Codex layouts.
- Three-way merge or interactive conflict resolution.

## Testing strategy (T39)

Integration tests spawn `python -m skills_mcp_server run --config …` via stdio, run `sync_skills`, and assert filesystem layout + `SKILL.md` contents + `.skills-sync-meta.json`. A unique `webhook_port` per test avoids binding collisions when the server opens its sidecar HTTP listener.
