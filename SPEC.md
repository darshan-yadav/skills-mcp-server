# skills-mcp-server — Specification

**Status:** Draft, pending review
**Owner:** Darshan Yadav
**Last updated:** 2026-04-23

---

## 1. Overview

`skills-mcp-server` is an open-source Model Context Protocol (MCP) server, written in Python, that hosts a library of "skills" and serves them to any MCP-capable agent — Claude Code, Cursor, OpenAI Codex CLI, and others.

A **skill** is a self-contained folder with a `SKILL.md` file at its root plus optional supporting files (reference docs, scripts, templates, assets). The `SKILL.md` carries YAML frontmatter — `name` and a natural-language `description` — followed by markdown instructions that tell an agent how to perform a class of tasks.

The project exists because skills today are fragmented: the same instructions get re-authored inside each tool's native convention (Claude Code's `~/.claude/skills/`, Cursor's rules, Codex's `AGENTS.md`, etc.). This server is the single source of truth — skills are defined once and exposed to every agent over the common MCP wire protocol.

## 2. Phased delivery

The project ships in phases. v0.1 is deliberately **tight and read-only**; more complex capabilities land in later phases only after the read path is stable in the field.

| Phase | Version | Theme | What's in it |
|---|---|---|---|
| **1** | **v0.1** | **Trustworthy read-only consumer + native auto-trigger** | Local + git sources with pinned refs, audit via recorded git SHA, skills exposed as MCP **prompts + resources only**, stdio transport + optional HTTP, minimal operator CLI (`run`, `init`, `reload`, `selftest`), scheduled git pull, plus the `skills-sync` companion CLI (§17.1) that materialises skills into `~/.claude/skills/` so Claude Code's native description-based auto-trigger works day one. **No writes, no server-side execution, no webhooks, no agent edits.** |
| **2** | **v0.2** | **Execution, reload automation, ops maturity** | Opt-in server-side script execution as MCP tools (subprocess-invoked, §16.1), webhook reload endpoint, agent-facing `refresh_skills` MCP tool, extended operator CLI (`pull`, `sync`, `pin`, `rollback`, `diff`, `add-source`, `remove-source`). **Authoring stays in git** — no MCP-driven skill mutation, ever. |
| **3** | **v0.3** | **Sync maturity** | `skills-sync` gains watch/daemon mode, richer conflict handling, and additional target layouts (Cursor `.cursor/rules/<name>.mdc`, Codex once that settles). §17.3. |
| **4** | **v1.0** | **Execution hardening + registry** | Per-skill virtualenvs, cgroups-based CPU/memory/wall-clock limits on subprocess invocation, opt-in public skills index with search/ratings/signed manifests. |

**Why this order?** The v0.1 surface is what an organisation can trust with no additional governance — it's a pure consumer of content the org already reviews via git pull-requests and CI. Phase 2 adds the capabilities that need the most careful safety work (mutation, execution, new network ingress). Phase 3 closes the UX gap for Claude Code's native skill loader. Phase 4 is hardening and ecosystem.

For the rest of this document, **§§3–15 are normative for v0.1**. **§17.1 is also normative for v0.1** (the `skills-sync` CLI ships alongside the server). **§16 fully specifies phase 2**; §17.3 sketches the phase-3 sync work and §18 sketches phase 4.

## 3. Goals (v0.1)

v0.1 is a **read-only consumer**. Organisations handle authoring through the workflow they already trust: git + pull-request review + CI. The server subscribes to the result.

1. **Single source of truth.** One canonical store of skills, consumable by every MCP-capable agent.
2. **Best-effort compatibility with the common `SKILL.md` format.** Skills following the usual Anthropic-style layout (required `name` + `description`, optional fields) should work **without modification**. Treat upstream-corpus compatibility as best-effort — pin a tested git revision and run a conformance check (see §19).
3. **Read-only.** The server never mutates skill content. Updates flow in via git pull from the upstream the operator pins.
4. **Pinnable and auditable.** Each source pins a git ref; the server records the exact commit SHA for every loaded skill and exposes it via `list_skills`.
5. **Filesystem + git storage.** Load from local directories and/or remote git repositories in any combination.
6. **Two transports: stdio + HTTP.** stdio for per-client local use; optional HTTP for a shared team-hosted deployment.
7. **Open-source friendly.** No proprietary dependencies. Safe defaults — nothing writes, nothing executes server-side. Strangers can run it without footguns.

## 4. Non-goals (v0.1)

Everything in this list is explicitly out of v0.1 scope. Most items are fully designed in §16 (phase 2) — the design work is done, the shipping is staged.

- **No writable sources — permanently.** Agents and clients cannot mutate skills over MCP in v0.1, phase 2, or ever. Authoring is a git-and-PR activity; the server is a read-only consumer of the org's reviewed output. This is a design commitment, not a phasing decision. See §11.4.
- **No server-side script execution.** Skills may ship bundled scripts, but v0.1 exposes them only as MCP *resources* (readable files) — it never runs them. Scripts continue to execute client-side in the agent's own sandbox exactly as they do today. Moves to phase 2 (§16.1).
- **No webhook endpoint.** Operators trigger reloads with the CLI or rely on the scheduled-pull loop. Phase 2 (§16.3).
- **No rich operator CLI.** v0.1 ships `run`, `init`, `reload`, and `selftest`. Commands like `pull`, `sync`, `pin`, `rollback`, `diff`, `add-source`, `remove-source` are phase 2 (§16.4).
- **No agent-facing refresh MCP tool.** Phase 2 (§16.2).
- **No Claude Code filesystem sync.** Companion CLI that materialises skills into `~/.claude/skills/` is phase 3 (§17).
- **No hardened execution sandbox.** When execution lands in phase 2 it runs in a subprocess (§16.1.2) — fresh interpreter per call, timeout-enforced, but sharing the server container's Python environment with no cgroups limits. Per-skill venvs, CPU/memory/wall-clock caps, and read-only mount hardening are phase 4 (§18).
- **No package registry with uploads.** There is no `skills publish` to a central index in v0.1 or phase 2. Skills are distributed by git URL. Opt-in registry is phase 4 (§18).
- **No authoring UI.** Skills are authored in files, version-controlled externally.

## 5. Glossary

- **Skill** — a folder containing `SKILL.md` and optional supporting files.
- **Skill bundle** — the folder and everything inside it.
- **Skill manifest** — the YAML frontmatter of `SKILL.md`.
- **Skill source** — a location the server loads skills from: a local directory or a git repo.
- **MCP primitive** — one of *prompt*, *resource*, or *tool* as defined by the MCP spec.
- **Client / host** — any MCP-speaking agent (Claude Code, Cursor, Codex, etc.).
- **Phase** — a shipping milestone; v0.1 = phase 1, v0.2 = phase 2, etc. (§2).

## 6. Skill format

### 6.1 Required and optional frontmatter

Required fields are unchanged from the existing `SKILL.md` convention. Additive optional fields are preserved, and unknown frontmatter keys pass through untouched so skills stay forward-compatible.

| Field | Required | Type | v0.1 behaviour | Phase 2+ |
|---|---|---|---|---|
| `name` | yes | string | Used as prompt name and in URIs. Unique per source. | |
| `description` | yes | string | Used verbatim as the MCP prompt description. | |
| `license` | no | string | Passed through in `list_skills`. | |
| `version` | no | string (semver) | Reported in `list_skills`. Defaults to `0.0.0` if absent. | |
| `tags` | no | list of strings | Reported in `list_skills`. | |
| `resources` | no | list | If present, only these paths are exposed as MCP resources. Absent = expose all files in bundle. | |
| `tools` | no | list | **Parsed but not acted upon in v0.1.** Skills that declare tools still load; their scripts are exposed only as resources. | Activated in §16.1. |
| `trust_level` | no | enum: `instructions-only` / `scripts-allowed` | Parsed but not acted upon in v0.1 (no execution). | Gates execution in §16.1. |
| `dependencies` | no | list | Informational. | Used by §16.1 import check. |

### 6.2 Bundle layout

```
my-skill/
├── SKILL.md            # required
├── LICENSE.txt         # optional
├── REFERENCE.md        # optional supporting docs
├── templates/          # optional
│   └── cover.docx
└── scripts/            # optional; bundled scripts are readable-only in v0.1
    ├── extract_text.py
    └── merge.py
```

### 6.3 Minimum skill

A conforming skill needs only `SKILL.md` with `name` and `description`:

```
summarize-meeting/
└── SKILL.md
```

```markdown
---
name: summarize-meeting
description: Use when the user asks to turn a meeting transcript into a concise summary with action items and owners.
---

# Meeting summarizer

Given a transcript, produce:
1. Three-sentence TL;DR.
2. Decisions made.
3. Action items as `- [owner] action (due date if given)`.
```

The server loads it and exposes it as an MCP prompt.

## 7. Storage

The server loads skills from **sources**. A source is either:

- **`local`** — a directory on the server's filesystem, scanned recursively for `SKILL.md` files.
- **`git`** — a remote git repository, cloned into a local cache, pulled on a schedule, then scanned the same way.

Multiple sources may be configured. If two sources produce skills with the same `name`, the one listed first wins and the server logs a warning at load time.

### 7.1 Example configuration

Paths are interpreted inside the server process. When running via the Docker image (§13), `path:` values should match container-side bind-mount points (e.g. `/skills`), not host paths.

```yaml
# mounted at /config/config.yaml inside the container
sources:
  - name: local-dev
    type: local
    path: /skills               # bind-mounted from the host

  - name: team-shared
    type: git
    url: git@github.com:my-org/skills.git
    ref: main
    refresh_interval: 1h

  - name: anthropic-core
    type: git
    url: https://github.com/anthropics/skills.git
    ref: v2.3.1                 # pinned — recommended for production
```

### 7.2 Refresh behaviour (v0.1)

- Local sources are re-scanned on filesystem change (v0.1: polled every 10s; phase 2 replaces polling with OS filesystem events).
- Git sources are pulled every `refresh_interval` (default `1h`, accepts Go-style durations like `30s`, `10m`, `never`) or on-demand via the `reload` CLI command (§11.2).
- The server registry hot-swaps atomically (§11.3) after any successful reload.
- **Client-side caveat:** MCP hosts are inconsistent about refetching `prompts/list` / `resources/list` / `tools/list` within a session. The server emits list-changed notifications where supported, but some clients will only see updates after the MCP session reconnects or the host restarts. Treat hot-reload as server-side only until verified per client (see §19.2).

### 7.3 Cache contention (shape B, multiple concurrent stdio containers)

In shape B (§13.3.1, per-editor stdio container), a developer with three editor windows open launches three containers simultaneously, all sharing the same `skills-mcp-data` named volume. Without coordination, three concurrent `git fetch` / `git pull` operations race on the same `.git/index.lock` and at least two fail — the user sees their editor fail to initialize the MCP server.

**Normative behaviour:** the server takes an exclusive OS-level file lock (`flock(2)` on POSIX, equivalent on Windows) before any mutating git operation on a cached clone, and before writing to the registry index on disk. Lock file lives at `/data/locks/<source-name>.lock`. The lock is held for the duration of the fetch/pull + write, released on completion or process exit (kernel-guaranteed release on exit, so crashes don't wedge the cache).

Behaviour when the lock is held by another container:

- Waiting container blocks on the lock with a 30-second timeout.
- If the holder completes first (the common case), the waiter acquires the lock, sees the cache is already up-to-date (its own `git fetch` is a cheap no-op), and proceeds.
- **On lock-acquisition timeout, behaviour depends on whether the cache is initialized.** The waiter checks for the presence of `/data/skills/<source>/.git/HEAD` (or the equivalent local-source sentinel) to distinguish a usable cache from a cold-start one:
  - **Cache is initialized** (normal case): waiter logs a warning, skips its own fetch, and proceeds with the existing (possibly slightly stale) cache. The result is a slightly stale view — far better than a hard failure for a read-only consumer.
  - **Cache is empty or half-cloned** (cold-start case — e.g., first launch on a new laptop where another container is mid-`git clone` of a large repo): waiter **hard-fails** with a specific error message (`cache uninitialized and lock contended — another instance is likely performing the initial clone; retry in a moment`) and exits non-zero. This prevents a container booting successfully with zero skills loaded, which would silently degrade every MCP session that connects through it.
- Shape A (single shared HTTP daemon) takes the same lock path but never contends with itself. The lock is cheap when uncontended.

Read paths (`prompts/list`, `resources/read`) do not take the write lock; they take the registry read lock from §11.3. The two lock layers compose: the registry swap completes inside the flock-protected section, so readers never see a torn state.

## 8. MCP surface (v0.1)

Two MCP primitives are populated from skills; a small fixed set of server-management tools is also exposed.

### 8.1 Skills as MCP prompts

Every loaded skill becomes one MCP prompt. The prompt's `name` matches the skill's `name`, its `description` matches the skill's `description`, and its body is the markdown contents of `SKILL.md` below the frontmatter — with internal references (`REFERENCE.md`, etc.) left intact so the client can follow up via resources.

Example `prompts/list` response:

```json
{
  "prompts": [
    {
      "name": "pdf",
      "description": "Use this skill whenever the user wants to do anything with PDF files...",
      "arguments": []
    },
    {
      "name": "summarize-meeting",
      "description": "Use when the user asks to turn a meeting transcript...",
      "arguments": []
    }
  ]
}
```

### 8.2 Bundle files as MCP resources

Every file in a skill bundle is exposed as an MCP resource with URI:

```
skill://<skill-name>/<relative-path>
```

Examples:

- `skill://pdf/REFERENCE.md`
- `skill://pdf/scripts/extract_pdf_text.py`
- `skill://pdf/LICENSE.txt`

If the manifest has a `resources:` allowlist, only those paths are exposed. Otherwise all files are exposed. Binary files are base64-encoded per the MCP spec.

### 8.3 Bundled scripts (v0.1)

Scripts in `scripts/` are exposed **only as resources** in v0.1. They are not registered as MCP tools, not executed server-side. A client that wants to run them does so in its own sandbox, the same way Claude Code and Cursor handle bundled scripts today. Server-side execution is fully specified for phase 2 in §16.1.

### 8.4 Server-management tools

Four server-level tools, always present:

| Tool | Purpose |
|---|---|
| `list_skills` | Returns the full skill index — name, description, version, source, git ref, tag list. Callable by any client. |
| `get_skill_manifest` | Returns the parsed frontmatter for one skill. |
| `reload` | Triggers an immediate `reload()` of all sources (re-scan local, pull git). |
| `server_info` | Returns server version, loaded-source summary, counts. |

Phase 2 adds conditionally-registered tools: execution tools per skill (§16.1) and the `refresh_skills` admin tool (§16.2) when enabled.

## 9. Versioning

- Each skill carries an optional semver `version` field in its manifest (default `0.0.0`).
- The server additionally records the **git ref** (commit SHA when source is git; `local` sentinel otherwise) at load time.
- `list_skills` returns both. Example entry:

  ```json
  {
    "name": "pdf",
    "version": "1.2.0",
    "description": "...",
    "source": "anthropic-core",
    "git_ref": "a3f19c2...",
    "tags": ["files", "pdf"]
  }
  ```

- No server-side version resolution or pinning in v0.1. If two sources provide `pdf`, the first-wins rule from §7 applies; operators pin by setting `ref:` in source config.

## 10. Security (v0.1)

- **Default posture:** nothing writes, nothing executes server-side. A freshly-installed v0.1 server is a pure read-only content server. Safe for anyone to run.
- **Resource exposure:** the server refuses to expose any path outside a skill's own bundle directory. `..` and absolute paths in `resources:` entries are rejected at load time. **Symlinks are resolved to their real target** (via `os.path.realpath`, or the equivalent) at both load time and every read; a resource whose real path escapes the bundle root — including a symlink pointing at `/config/config.yaml`, `/data/`, or any sibling skill's bundle — is rejected. This applies whether `resources:` is an explicit allowlist or implicit "expose everything in the bundle." A skill whose bundle itself contains an escaping symlink fails to load, not just to serve — so the condition is visible at startup, not lurking until a client happens to request the file.
- **Git clone destinations** are scoped to the server's data directory (`/data` under the Docker image). The server never writes outside its configured data dir.
- **Container isolation (Docker image).** The official image runs as non-root UID 1000 with a read-only root filesystem; only `/data` and `/config` are writable/readable mounts. This is defense in depth, not a substitute for the per-skill isolation landing in phase 4 (§18).
- **Secrets:** skills must not contain secrets. The server logs a warning if it detects well-known secret patterns (AWS keys, GitHub tokens) in any loaded file, but does not block loading.
- **No authentication on `list_skills` / `get_skill_manifest` / `reload` / `server_info`** in v0.1 — they are read-only and cheap to call. `reload` may trigger outbound git fetches; rate-limit it if the server is HTTP-exposed to untrusted clients.
- **Large-resource guidance:** if `resources:` is omitted, the server exposes every file in a bundle. For published or team-shared skills, prefer an explicit `resources:` allowlist rather than the implicit expose-all (see §19.8).

Phase 2 expands the security model to cover execution, writability, and webhook ingress (§16).

### 10.1 HTTP deployment hardening

v0.1 ships **no built-in authentication** on the HTTP transport. For any HTTP deployment reachable by more than a single trusted operator, the server is expected to sit behind a reverse proxy that handles TLS and authentication. This section is normative guidance for operators running the HTTP daemon (§13.3.2).

- **Don't expose the HTTP transport directly to the public internet.** Terminate TLS and enforce authentication at a reverse proxy (nginx, Caddy, Traefik), a service-mesh ingress, or a zero-trust gateway (Cloudflare Access, Tailscale, Teleport). The skills-mcp-server container binds to `0.0.0.0` inside its own network namespace — publish the port only on the proxy-facing network.
- **Minimum auth bar for team-internal deployments:** the proxy requires a valid SSO session (for browser-mediated clients) or a per-user bearer token (for editor clients). Editors vary in their HTTP MCP auth support — verify per client.
- **Rate-limit `reload`** at the proxy. The tool is cheap locally but triggers outbound `git fetch` against your configured remotes; an unauthenticated attacker can use it to burn your git provider's rate limit. A proxy rule capping `reload` to, say, 6/minute/IP is sufficient.
- **Network egress from the server.** The daemon needs outbound network only to the git remotes listed in `sources`. If your policy allows, constrain container egress with an `egress-allowlist` (Docker/k8s NetworkPolicy) to just those hosts.
- **Audit logging.** Stdout JSON logs cover every `reload`, every git fetch, and every MCP tool call. Ship them to your log aggregator; do not rely on the container's stdout buffer alone.

Phase 2 may add a native bearer-token auth mode for deployments where a proxy is not available.

## 11. Update mechanisms (v0.1)

v0.1 supports **two** update pathways. Richer options — agent-triggered refresh, webhooks, diff/rollback commands — are phase 2 (§16).

### 11.1 Scheduled pull + local poll

- Git sources: pulled every `refresh_interval` (default `1h`). A no-op pull is cheap; `reload()` runs only when something changed.
- Local sources: polled at `local_poll_interval` (default `10s`) in v0.1. Replaced by OS filesystem events in phase 2.

### 11.2 Operator CLI

v0.1 ships exactly four commands. They operate **offline-first**: they mutate the git cache / re-scan sources on disk and exit. A running daemon picks the change up on its own next poll cycle (or immediately via the `reload` MCP tool §8.4). Live admin-socket IPC between CLI and daemon is phase 2.

Under the Docker image (§13.6), each CLI invocation is a one-shot `docker run --rm ... <cmd>` against the same volumes the daemon uses. `docker exec <container-name> <cmd>` also works against a running HTTP daemon.

| Command | What it does |
|---|---|
| `skills-mcp-server` | Start the server (default stdio transport). |
| `skills-mcp-server init` | Write a starter `config.yaml`. |
| `skills-mcp-server reload` | Re-scan all sources and (for git sources) pull. Updates cache; running daemon sees it on next poll. |
| `skills-mcp-server --selftest` | Load config, resolve sources, report counts. Exits without starting the server. |

### 11.3 Atomicity

- `reload()` acquires a single write lock on the registry and publishes the new state in one swap.
- Read paths (`prompts/list`, `resources/read`, `list_skills`) take a read lock against a consistent snapshot — a reload mid-request never tears.
- If a reload produces a parse error on some skill, that skill retains its previous state and an error is logged. One bad skill does not take down the server.

### 11.4 Authoring workflow (permanent)

**PR-based authoring is the permanent and only path for skill mutation.** The server is a read-only consumer of the git state the organisation already reviews. Agent-initiated MCP edits are an explicit non-goal — not "deferred to phase 2," not "off by default," but **never in scope** for this server. If a contributor wants an agent's help authoring a skill, the agent edits the file in the contributor's editor; the contributor reviews, commits, and opens a PR through the org's normal flow.

The authoring loop:

1. Author a new skill or edit an existing one on a branch (in the contributor's editor, with or without agent assistance).
2. Open a pull request. CI runs any conformance checks (lint frontmatter, spell-check, load-test against a pinned server build).
3. Merge to the branch the source `ref:` points at (often `main`, or a release tag).
4. Running servers pick the change up on their next scheduled pull, or the operator runs `skills-mcp-server reload` for immediate adoption.

This is deliberately the same flow organisations already use for code. It keeps review quality high, uses tools contributors already know, and removes an entire class of safety and coordination problems that would otherwise arise from a parallel MCP mutation path.

## 12. Client compatibility

| Client | Prompts | Resources | Server-mgmt tools | Native auto-trigger |
|---|---|---|---|---|
| Claude Code | ✅ visible in prompt picker | ✅ fetchable | ✅ callable | ✅ via `skills-sync` (§17.1) |
| Cowork mode | ✅ | ✅ | ✅ | ✅ via `skills-sync` (§17.1) |
| Cursor | ✅ | ✅ | ✅ | phase 3 (§17.3) |
| OpenAI Codex CLI | prompts support pending | ✅ | ✅ | phase 3 (§17.3) |

**Auto-trigger via filesystem materialisation.** Claude Code's and Cowork's *native* skills mechanism — where a skill's `description` is pre-loaded and auto-triggered from the user's phrasing — runs off the local filesystem directory, not MCP. To preserve that experience, v0.1 ships the `skills-sync` companion CLI (§17.1). Developers run `skills-sync pull` once (or wire it into a shell hook) to materialise the server's loaded skills into `~/.claude/skills/`. Cursor and Codex support lands in phase 3 (§17.3) — in v0.1 those clients use MCP prompts directly.

**List caching.** MCP hosts cache `prompts/list` and `resources/list` inconsistently. After a reload, users may need to reconnect the MCP session or restart the host to see new/renamed entries until per-host behaviour is verified (§19.2).

## 13. Installation & configuration

The primary distribution format is an **OCI container image**. Running inside a container is the supported install path for both stdio (per-client local launch) and HTTP (shared team-hosted daemon) use. A PyPI package is available as a secondary option for developer use; it is not the blessed deployment surface.

### 13.1 Install (Docker image)

Published to GitHub Container Registry as:

```
ghcr.io/<org>/skills-mcp-server:<tag>
```

Tag conventions:

- `latest` — floating tag on the latest stable release. Avoid for production.
- `0.1`, `0.1.3` — release tags. Recommended for production pinning.
- `sha-<short>` — immutable per-commit tag. Use when you need bit-for-bit reproducibility.
- `edge` — rolling tag built from `main`. For previews only.

Image properties:

- Base: `python:3.12-slim` (multi-arch manifests for `linux/amd64` and `linux/arm64`).
- Installed: `git` (required for `git`-type sources), `ca-certificates`, the server itself via `pip install`.
- User: non-root `skills` (UID 1000); filesystem read-only except for two mount points — `/data` (server data dir: git cache, audit log) and `/config` (config file).
- Default command: `skills-mcp-server --config /config/config.yaml` (stdio).
- Exposed port: `7425` (only relevant when `--transport http`).
- Healthcheck: for HTTP mode, `GET /health` returns `200` when the registry is loaded. No healthcheck defined in stdio mode (container is expected to be short-lived and client-driven).

Pull:

```bash
docker pull ghcr.io/<org>/skills-mcp-server:0.1
```

A single-file PyPI install is also available for developer workflows:

```bash
uvx skills-mcp-server --help
pipx install skills-mcp-server
```

The PyPI path is officially supported but not the recommended deployment target.

### 13.2 First-run config

Create a config directory on the host and generate a starter config. The image runs `init` as a one-shot subcommand:

```bash
mkdir -p ~/.config/skills-mcp-server ~/skills
docker run --rm \
  -v ~/.config/skills-mcp-server:/config \
  -v ~/skills:/skills \
  ghcr.io/<org>/skills-mcp-server:0.1 \
  skills-mcp-server init --config /config/config.yaml
```

The generated `~/.config/skills-mcp-server/config.yaml`:

```yaml
sources:
  - name: local
    type: local
    path: /skills            # inside-container path; bind-mounted from host

data_dir: /data              # git cache + audit log live here
log_level: info
```

**Path convention.** Inside the container, bind-mount points are stable: `/config` for the config file, `/data` for the server's writable data dir, `/skills` (or any name you choose) for local skill directories. Configure `path:` for local sources using the container-side path; the host side is chosen at `docker run` time.

### 13.3 Running

Two deployment shapes are supported. Pick based on client HTTP-MCP support across your fleet:

- **Shape A — shared HTTP daemon (recommended for teams).** One long-lived container, every client connects over HTTP. Skills update centrally, devs see changes within `refresh_interval` with no per-laptop action. Requires every client in your mix to support HTTP MCP transport. See §14.4 for the team deployment walkthrough.
- **Shape B — per-client stdio container.** Each editor launches its own container on MCP session open. Works with every MCP client today (stdio is universally supported). Costs a small cold-start per session and each dev has a separate git cache. Use this when HTTP MCP isn't reliable across your client mix, or for single-developer / laptop-only setups.

Both shapes run the same image with the same config; only the launch invocation differs.

#### 13.3.1 stdio (per-client local use)

The MCP client launches the container per session with `docker run -i --rm`. `-i` keeps stdin open for the MCP protocol; `--rm` cleans up on exit:

```bash
docker run -i --rm \
  -v ~/.config/skills-mcp-server:/config:ro \
  -v skills-mcp-data:/data \
  -v ~/skills:/skills:ro \
  ghcr.io/<org>/skills-mcp-server:0.1
```

Named volume `skills-mcp-data` persists the git cache across invocations — avoids re-cloning every launch.

**Latency caveat.** Container cold-start adds a few hundred milliseconds to each MCP session open. Acceptable for editor-driven workflows (session opens once per editor launch). If you hit this often enough for it to matter, run the HTTP deployment (§13.3.2) and point stdio clients at an HTTP MCP proxy.

#### 13.3.2 HTTP (shared team daemon)

Run as a long-lived background container:

```bash
docker run -d --name skills-mcp \
  -v ~/.config/skills-mcp-server:/config:ro \
  -v skills-mcp-data:/data \
  -v ~/skills:/skills:ro \
  -p 7425:7425 \
  ghcr.io/<org>/skills-mcp-server:0.1 \
  skills-mcp-server --config /config/config.yaml \
  --transport http --host 0.0.0.0 --port 7425
```

Docker Compose equivalent for a team-shared deployment:

```yaml
# docker-compose.yaml
services:
  skills-mcp:
    image: ghcr.io/<org>/skills-mcp-server:0.1
    restart: unless-stopped
    command: >
      skills-mcp-server
      --config /config/config.yaml
      --transport http
      --host 0.0.0.0
      --port 7425
    ports:
      - "7425:7425"
    volumes:
      - ./config:/config:ro
      - skills-mcp-data:/data
      - ./skills:/skills:ro
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:7425/health"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  skills-mcp-data:
```

### 13.4 Wiring into clients

All examples use the stdio container command (§13.3.1) as the MCP launcher. Replace `<org>` and tag with your values.

**Claude Code** — add to `~/.claude/mcp_servers.json` (or via `claude mcp add`):

```json
{
  "mcpServers": {
    "skills": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "${HOME}/.config/skills-mcp-server:/config:ro",
        "-v", "skills-mcp-data:/data",
        "-v", "${HOME}/skills:/skills:ro",
        "ghcr.io/<org>/skills-mcp-server:0.1"
      ]
    }
  }
}
```

**Cursor** — add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "skills": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "${HOME}/.config/skills-mcp-server:/config:ro",
        "-v", "skills-mcp-data:/data",
        "-v", "${HOME}/skills:/skills:ro",
        "ghcr.io/<org>/skills-mcp-server:0.1"
      ]
    }
  }
}
```

**OpenAI Codex CLI** — add to `~/.codex/config.toml`:

```toml
[mcp_servers.skills]
command = "docker"
args = [
  "run", "-i", "--rm",
  "-v", "${HOME}/.config/skills-mcp-server:/config:ro",
  "-v", "skills-mcp-data:/data",
  "-v", "${HOME}/skills:/skills:ro",
  "ghcr.io/<org>/skills-mcp-server:0.1",
]
```

**Pointing a client at a shared HTTP deployment.** If the team runs the HTTP daemon (§13.3.2), each client configures an HTTP MCP transport pointing at `http://<host>:7425` instead of launching a container. Exact config key depends on the client; MCP HTTP support is still stabilising, so verify against the current client docs.

### 13.5 Verifying the install

One-shot selftest against the same mounts the daemon would use:

```bash
$ docker run --rm \
    -v ~/.config/skills-mcp-server:/config:ro \
    -v skills-mcp-data:/data \
    -v ~/skills:/skills:ro \
    ghcr.io/<org>/skills-mcp-server:0.1 \
    skills-mcp-server --selftest
[ok]  config loaded:   /config/config.yaml
[ok]  sources:         1 local, 0 git
[ok]  skills loaded:   3 (summarize-meeting, pdf, darshan-voice)
[ok]  mcp handshake:   prompts=3, resources=11, server-mgmt tools=4
```

### 13.6 Operator CLI inside Docker

The v0.1 CLI commands (§11.2) run as one-shot container invocations against the same volumes:

```bash
# Force a reload of the cache (then running daemon picks it up on next poll)
docker run --rm \
  -v ~/.config/skills-mcp-server:/config:ro \
  -v skills-mcp-data:/data \
  -v ~/skills:/skills:ro \
  ghcr.io/<org>/skills-mcp-server:0.1 \
  skills-mcp-server reload

# If the HTTP daemon is running under a known container name, docker exec works too
docker exec skills-mcp skills-mcp-server reload
```

Phase 2 adds an admin socket (§16.4, §19.7) — the equivalent inside Docker will be either a Unix socket exposed on a shared volume or an HTTP admin endpoint bound to localhost inside the container.

## 14. Usage walkthroughs (v0.1)

### 14.1 Adding a skill via git (the v0.1 authoring flow)

A team member wants to add a `release-notes` skill.

1. On a branch in the team's skills repo:

   ```
   release-notes/
   └── SKILL.md
   ```

   ```markdown
   ---
   name: release-notes
   description: Use when the user wants to turn a list of merged PRs into user-facing release notes grouped by theme.
   version: 0.1.0
   tags: [writing, eng]
   ---

   # Release notes writer

   Given a list of PRs...
   ```

2. Open a PR. CI does a conformance check (can the target server load this skill cleanly?).

3. Merge to `main`.

4. Within `refresh_interval` (default `1h`), every running server pulls and picks it up. Operators in a hurry run `skills-mcp-server reload` on their server instance.

### 14.2 Using a skill from Claude Code

```
[user]  I've got a dump of merged PRs for this sprint — can you turn it into release notes?

[claude code]  may call skills.list_skills / prompts.list and pick release-notes
               (exact routing is host-dependent — not guaranteed)

[claude code → user]  I'll use the release-notes skill. Paste the PR list?

[user]  <pastes list>

[claude code]  reads skill://release-notes/SKILL.md, follows the instructions, produces output.
```

> _Screenshot placeholder: Claude Code's prompt picker showing the `skills` server with its prompts listed. To be captured once v0.1 is running._

### 14.3 Inspecting loaded skills

```
[any client] → tools/call  list_skills
```

```json
[
  { "name": "summarize-meeting", "version": "0.0.0", "source": "local-dev", "git_ref": "local" },
  { "name": "release-notes",     "version": "0.1.0", "source": "team-shared", "git_ref": "c11e8d4..." },
  { "name": "pdf",               "version": "1.2.0", "source": "anthropic-core", "git_ref": "a3f19c2..." }
]
```

(Server-side script execution, and the `skill.pdf.extract_text`-style tool invocations it enables, are phase 2 — see §16.1.)

### 14.4 Deploying for a team (shape A, ~20 developers)

The most common deployment: one shared HTTP daemon, a team git repo of skills, every developer's editor pointed at the same URL. Walkthrough assumes an ops person doing the day-0 setup and 20 developers onboarding to an existing deployment.

#### 14.4.1 Topology

```
   20 dev laptops                 Team infra                        Upstream
   ─────────────                  ──────────                        ────────
   Claude Code   ─┐
   Cursor         │── HTTPS ──►  reverse proxy ──►  skills-mcp-server  ── git pull ──►  git.acme.com/skills
   Codex CLI      │                (TLS + auth)       (one container,                    (main, PR-reviewed)
                  │                                    one host)
   …17 more    ──┘                                        │
                                                          └── /data volume: git cache + audit log
```

One container, one URL (e.g. `https://skills.acme.internal:7425`), one git repo of skills. Every dev connects to the same endpoint; skills update centrally.

#### 14.4.2 Ops day-0 setup (one-time)

1. **Set up the skills repo.** Create `git@git.acme.com:platform/skills.git`. Skills live as `SKILL.md` folders at the repo root. Protect `main` with required PR review + a CI job running `skills-mcp-server --selftest --config ./ci-config.yaml` against the PR branch. That CI job is the conformance check from §19.3.
2. **Stand up the daemon.** Small VM or k8s Deployment (2 vCPU / 2 GB is generous). Use the Docker Compose template from §13.3.2 with the team repo wired in:
   ```yaml
   # /etc/skills-mcp/config.yaml
   sources:
     - name: team
       type: git
       url: git@git.acme.com:platform/skills.git
       ref: main
       refresh_interval: 15m

   data_dir: /data
   log_level: info
   ```
3. **Put it behind your reverse proxy.** Terminate TLS, authenticate per-user (SSO or per-user bearer tokens), rate-limit `reload`. See §10.1. Do not expose the container port directly to anything beyond the proxy's network.
4. **Publish the connection info** on the team wiki: the URL, the 4-line editor config snippet, and a link to the skills repo for authors. This one-pager *is* the developer onboarding doc.

#### 14.4.3 Developer onboarding (≈5 min per dev)

Each developer edits their MCP client config once, then restarts the editor. For Claude Code:

```json
{
  "mcpServers": {
    "skills": {
      "url": "https://skills.acme.internal:7425",
      "headers": { "Authorization": "Bearer ${SKILLS_MCP_TOKEN}" }
    }
  }
}
```

Cursor and Codex have equivalent HTTP blocks — exact keys vary per client and are still stabilising; check current client docs. No `docker pull`, no local cache, no daily maintenance.

#### 14.4.4 Day-to-day flows

- **Using a skill:** identical to §14.2 — the skill shows up in the editor's prompt picker.
- **Authoring a new skill:** dev follows §14.1 — branch, author, PR, merge. Within `refresh_interval` (15 min above), every teammate's editor has the new skill. Ops can force immediate adoption with `docker exec skills-mcp skills-mcp-server reload` if needed.
- **Rolling back a bad skill:** revert the PR on `main`. Next pull picks up the revert. Per-source ref rollback via CLI is phase 2 (§16.4).

#### 14.4.5 When to pick shape B instead

Fall back to per-client stdio containers (§13.3.1) when:

- One or more MCP clients in your mix don't yet support HTTP transport reliably.
- Your security policy forbids a shared HTTP endpoint at all.
- You're a solo developer — the shared-daemon setup isn't worth the VM.

The image, config format, and skill layout are identical; only the launch invocation changes. A team can migrate from shape B to shape A later without re-authoring skills or configs.

## 15. Architecture (v0.1 one-pager)

```
                        ┌─────────────────────────────────────┐
                        │            skills-mcp-server         │
                        │                                      │
   local dirs  ───┐     │  ┌──────────┐   ┌──────────────────┐ │
                  ├────►│  │  Source  │──►│  Skill registry  │ │
   git repos  ───┘      │  │  loaders │   │  (hot-swappable) │ │
                        │  └──────────┘   └────────┬─────────┘ │
                        │                          │           │
                        │              ┌───────────┴─────────┐ │
                        │              ▼                     ▼ │
                        │          Prompts             Resources│
                        │           (N)                (M files)│
                        │              │                     │ │
                        │      + server-mgmt tools: list_skills,
                        │        get_skill_manifest, reload,
                        │        server_info                   │
                        │                 │                    │
                        │        ┌────────┴─────────┐          │
                        │        │  MCP transport   │          │
                        │        │  (stdio | HTTP)  │          │
                        │        └────────┬─────────┘          │
                        └─────────────────┼────────────────────┘
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              ▼                           ▼                           ▼
        Claude Code                    Cursor                  Codex CLI
```

Phase 2 adds a tool dispatch path (§16.1), webhook ingress (§16.3), an agent-facing refresh tool (§16.2), and the extended operator CLI (§16.4) on top of this same core. No mutation path is added — authoring stays in git.

---

## 16. Phase 2 (v0.2) — Execution, reload automation, ops maturity

Phase 2 is fully specified here so implementation can begin immediately once v0.1 is field-stable. It adds four capability groups on top of the v0.1 core: server-side script execution (§16.1), an agent-facing refresh tool (§16.2), a webhook endpoint (§16.3), and an extended operator CLI (§16.4).

**Authoring is not a phase-2 concern.** The server remains a read-only consumer of git-curated content in phase 2, phase 3, and beyond. See §4 and §11.4.

### 16.1 Server-side script execution

Skills that declare `tools:` in their manifest get those scripts registered as MCP tools, gated by three independent checks — all must pass:

1. **Operator setting.** Global `execution.enabled = true` in config. Defaults to `false`.
2. **Manifest declaration.** `trust_level: scripts-allowed` plus at least one entry in `tools:`.
3. **Source trust allowlist.** The skill's source name appears in `execution.trusted_sources`.

When all three pass, each declared script is registered as an MCP tool named `skill.<skill>.<tool>` (e.g. `skill.pdf.extract_text`).

#### 16.1.1 Example manifest

```yaml
---
name: pdf
description: "Use this skill whenever the user wants to do anything with PDF files..."
version: 1.2.0
trust_level: scripts-allowed
tools:
  - name: extract_text
    entry: scripts/extract_pdf_text.py        # script path relative to skill bundle
    description: "Extract all text from a PDF file at a given path."
    input_schema:
      type: object
      required: [path]
      properties:
        path: { type: string, description: "Absolute path to a .pdf file" }
  - name: merge
    entry: scripts/merge.py
    description: "Merge multiple PDFs into one."
    input_schema:
      type: object
      required: [paths, output]
      properties:
        paths: { type: array, items: { type: string } }
        output: { type: string }
dependencies:
  - pypdf>=4.0
---
```

#### 16.1.2 Execution contract — subprocess invocation

Phase 2 execution runs each tool call in a **fresh Python subprocess**. This is an explicit design choice, chosen after rejecting the earlier in-process model: subprocess isolation keeps a runaway or blocking script from hanging the server's event loop for every connected client, and it makes skill script updates trivially consistent (every invocation gets a clean interpreter — no `sys.modules` cache to invalidate).

The contract:

- **Entry point:** a path to a Python script (`.py` file) relative to the skill bundle root. The server resolves the path, verifies it's inside the bundle (symlink-safe; see §10), and invokes it as `python <bundle>/<entry>`.
- **Interpreter:** in phase 2 the subprocess inherits the server container's Python and installed packages. Phase 4 (§18) layers per-skill virtualenvs on top of this same subprocess model.
- **Argument passing:** the `dict` parsed from the MCP tool-call JSON (after validation against `input_schema`) is written to the subprocess's stdin as a single JSON object terminated by a newline.
- **Return channel — result file, not stdout.** stdout is *unreliable* as a structured-data channel because Python libraries, CLI wrappers, and progress bars routinely write to it without asking. Instead, the server passes an environment variable `MCP_RESULT_FILE=/tmp/skills-mcp/<invocation-id>/result.json` and the script writes its final JSON payload to that file. On subprocess exit with code 0, the server reads the file and returns its contents as the structured MCP tool result. If the file is absent or unparseable, the tool call fails with `error: missing_result` and the subprocess's captured stdout + stderr are attached to the failure for debugging. stdout and stderr are both captured to the server's audit log — never returned to the caller directly — so scripts are free to print progress, warnings, or debug logs without corrupting the protocol.
- **Expected script skeleton:**
  ```python
  # scripts/extract_pdf_text.py
  import json, os, sys

  args = json.loads(sys.stdin.read())
  result = do_work(args["path"])          # skill's own logic; free to print() anywhere

  with open(os.environ["MCP_RESULT_FILE"], "w") as f:
      json.dump({"text": result}, f)
  ```
  A helper library (`skills_runtime` — published alongside the server) wraps this boilerplate for authors who want it, but is not required.
- **Working directory:** a fresh temp dir at `/tmp/skills-mcp/<invocation-id>/` is created and set as the subprocess `cwd`; `MCP_RESULT_FILE` lives inside it. The whole dir is deleted after the call completes (success or failure).
- **Environment:** the server passes `SKILL_BUNDLE=<absolute path to bundle>`, `SKILL_INVOCATION_ID=<id>`, and `MCP_RESULT_FILE=<path>` in the environment. The rest of the container environment is **not** propagated — no `HOME`, no `PATH` beyond a minimal default, no host secrets.
- **Timeout and process-group reaping.** 60s default, overridable per-tool in manifest via `timeout_seconds`. The server launches the subprocess with `start_new_session=True` (new process group / session) so the script and everything it spawns live in one reapable group. On timeout the server sends `SIGTERM` to the entire process group via `os.killpg(pgid, SIGTERM)`, waits 2s, then `SIGKILL`s the group. This reaps grandchildren too — a script that did `subprocess.Popen("curl ...")` or `os.system(...)` cannot leave orphans burning CPU or holding sockets after its parent dies. Returns `error: timeout` to the caller and logs the event.
- **Concurrency:** the server may run multiple subprocesses in parallel (one per concurrent MCP tool call). No in-process global locks are needed because each call has its own process.
- **Reloads are automatic.** Because every call spawns a fresh interpreter, on-disk updates to skill scripts are picked up on the very next invocation. No module-cache invalidation, no in-flight "old code" problem.
- **`dependencies:`** are informational in phase 2; operators install them into the server container's Python env (or publish a custom image with them baked in). `--selftest` optionally dry-imports each declared script when execution is enabled, surfacing missing packages before a real invocation fails.

#### 16.1.3 Cost, safety, and what subprocess doesn't give you

- **Cold-start cost.** A fresh Python interpreter takes ~100–300 ms depending on imports. That's visible per tool call. Acceptable for human-in-the-loop interactions; not acceptable for tight-loop automation. Skill authors should avoid registering tools that are called thousands of times per session.
- **Shared Python env.** All skill subprocesses in phase 2 share the server container's installed packages. One skill pinning `pypdf==3.0` and another wanting `pypdf==5.0` can't both be satisfied. Phase 4 (§18) introduces per-skill venvs to resolve this — the subprocess model then just invokes the venv's interpreter instead of the container's default.
- **No hard resource limits in phase 2.** Subprocess isolation contains hangs and crashes but not memory usage or CPU burn. A script that allocates 8 GB will still OOM the container. Phase 4 adds cgroups-based CPU/memory caps and wall-clock limits via the same subprocess contract.
- **Filesystem exposure.** Scripts run as the same UID as the server (non-root `skills` under the Docker image). They can read the skill bundle and the temp cwd; they cannot write outside `/tmp/skills-mcp/<id>/` without going through filesystem permissions. Phase 4 tightens this with read-only bind mounts.

The three-gate opt-in model (operator flag + manifest declaration + source allowlist) is unchanged. Subprocess isolation is defense in depth on top of that, not a substitute for it.

#### 16.1.4 Protecting the skill cache from subprocess tampering

The server and the subprocesses it spawns run as the **same UID** (non-root `skills` under the Docker image). This means standard POSIX filesystem permissions do not, on their own, stop a subprocess from writing back into its own skill bundle — a malicious or buggy script could overwrite its `SKILL.md` to flip `trust_level`, rewrite a sibling skill's code, or plant persistence that survives the next `reload()`.

v0.2 addresses this by **dropping write permissions on the cache after each pull**. The flow:

1. `reload()` acquires the flock (§7.3), `chmod -R u+w` on the affected cache subtree, and runs the `git fetch` / `git pull`.
2. After the pull completes and the registry has been re-scanned, the server runs `chmod -R u-w` across the cache subtree. Files become read-only to the owner; directories stay searchable (`u+rx` preserved) so the subprocess can still traverse them to read bundle contents.
3. On the next `reload()`, the cycle repeats: re-add write bits, pull, drop them.

Effect: during the windows when skill scripts are actually invoked, the cache is read-only to the `skills` UID, and any script that tries to write to its own bundle or a sibling's fails with `EACCES`. The server's own pull path still works because the `reload()` flow explicitly re-enables writes for its own critical section.

Per-invocation writable state lives only in the temp cwd (`/tmp/skills-mcp/<invocation-id>/`) which is scoped to one call and deleted on completion. The result file lives there too.

This is a phase-2 hardening, not a full sandbox. A script can still read any file readable to the `skills` UID, including `/data`'s git cache contents (reading is fine; writing is what we block). Phase 4 (§18) replaces the chmod dance with read-only bind mounts and, optionally, a distinct UID per subprocess — tighter guarantees at the cost of the additional container plumbing that phase 4 is scoped for.

### 16.2 Agent-facing refresh tool

Optional MCP tool `refresh_skills` that lets a connected agent ask the server to pull/reload mid-conversation. Off by default.

```yaml
mcp_admin_tools:
  refresh_skills:
    enabled: true
    allowed_sources: [local-dev]    # which sources this tool may touch
    rate_limit: 1/minute
```

Input schema:

```json
{
  "type": "object",
  "properties": {
    "source": { "type": "string", "description": "Source name, or omit for all." },
    "mode":   { "type": "string", "enum": ["reload", "pull", "sync"], "default": "sync" }
  }
}
```

Returns the same structured diff `skills-mcp-server diff` produces (§16.4).

### 16.3 Webhook reload endpoint

When running with HTTP transport, the server can expose `POST /webhook/reload`. Point a GitHub / GitLab / Bitbucket push webhook at it and git sources pull-and-reload as soon as upstream advances.

**Authentication:** intentionally simple — a shared secret presented as `Authorization: Bearer <token>`, value sourced from an env var, never written to config. This is **not** GitHub/GitLab's native HMAC signature header; operators either configure the provider to send a custom `Authorization` bearer or place a small reverse proxy that verifies the provider's native signature and forwards to this endpoint with the bearer.

```yaml
webhook:
  enabled: true
  secret_env: SKILLS_MCP_WEBHOOK_SECRET
  allowed_sources: [team-shared]
```

Request shape:

```
POST /webhook/reload
Authorization: Bearer <shared-secret>
Content-Type: application/json

{ "source": "team-shared" }     # optional; omit = refresh all webhook-allowed sources
```

Response:

```json
{ "pulled": true, "changed": 3, "ref_before": "f0ca221", "ref_after": "b77a19e" }
```

### 16.4 Extended operator CLI

Phase 2 adds the commands v0.1 deferred. They operate against the same `config.yaml` and can run offline or — stretch goal — against a running daemon via a local admin socket (Unix domain socket on POSIX, named pipe on Windows).

| Command | What it does |
|---|---|
| `skills-mcp-server pull [--source=<name>]` | Force a `git pull` now. No-op for local sources. |
| `skills-mcp-server sync` | `pull` then `reload`. "Make everything current" one-liner. |
| `skills-mcp-server pin --source=<name> --ref=<ref>` | Pin a source to a specific git ref. Rewrites config. |
| `skills-mcp-server rollback --source=<name>` | Revert a source to its previous loaded ref (server keeps the last N — default 5). |
| `skills-mcp-server diff` | Show which skills would change if `reload` ran now. Read-only, safe for CI. |
| `skills-mcp-server add-source ...` | Register a new source without hand-editing YAML. |
| `skills-mcp-server remove-source <name>` | Unregister and purge the cache. |

Example:

```bash
$ skills-mcp-server diff
source=anthropic-core  current=a3f19c2  target=c11e8d4
  ~ pdf           1.2.0 → 1.3.0
  + html-report   (new)
  - csv-cleaner   (removed)

$ skills-mcp-server sync
[ok]  pulled anthropic-core: a3f19c2 → c11e8d4 (2 files changed)
[ok]  reload: +1 new, ~1 changed, -1 removed, 2 unchanged
```

---

## 17. `skills-sync` — filesystem materialisation for native auto-trigger

Claude Code's magic is auto-triggering a skill from the user's phrasing without them having to open a prompt picker. That auto-trigger runs off a local directory (`~/.claude/skills/`), not off MCP. If the MCP server is the org's single source of truth but it only exposes skills as MCP prompts, Claude Code users lose the best part of the experience. A sizeable share of the product's value is in that auto-trigger loop — without it, the server feels like a file browser, not a skills layer.

To close this gap without waiting for a future phase, a companion CLI called `skills-sync` materialises the MCP server's loaded skills into the local filesystem layout Claude Code (and Cowork) expect. It's distributed as a separate PyPI package (pipx-installable) and runs on the developer's laptop.

### 17.1 v0.1 scope — minimum viable sync (ships with the server)

`skills-sync` ships alongside v0.1 of the server. Its v0.1 scope is intentionally small: one command, one target layout, one conflict policy.

- **Command:** `skills-sync pull --from <mcp-url-or-command> --to ~/.claude/skills`. Connects to the named MCP server (HTTP URL for shape A, or a stdio command string for shape B), lists prompts + resources, and materialises each skill into `~/.claude/skills/<name>/` with `SKILL.md` and bundle files.
- **Target layouts in v0.1:** Claude Code (`~/.claude/skills/<name>/`) and Cowork (same directory). Cursor and Codex are deferred to phase 3 because their native skills conventions are still stabilising; in v0.1 those clients continue to reach skills via MCP directly.
- **Conflict policy (v0.1):** server wins. If the target directory contains a file the server doesn't have, or with different content, the local copy is moved to `~/.claude/skills/.skills-sync-backup/<timestamp>/<name>/<path>` and a warning is printed. This is safe (nothing is destroyed) and simple (no prompts, no merge UI).
- **Identity:** a `.skills-sync-meta.json` file lives at the root of the sync target with the last-synced server URL, timestamps, and per-skill git SHAs from `list_skills`. This makes `skills-sync pull` idempotent and gives `--dry-run` something useful to diff against.
- **Scope boundary:** no watch mode, no subscribing to MCP list-changed notifications, no automatic re-run on merge. The developer runs `skills-sync pull` manually — or wires it into their shell login, a cron job, or a `git pull` hook on the team skills repo. It's a one-shot tool in v0.1.

### 17.2 Typical developer flow

```bash
# Install once
pipx install skills-sync

# Point at the team's shared HTTP deployment
skills-sync pull \
  --from https://skills.acme.internal:7425 \
  --to ~/.claude/skills \
  --auth-header "Authorization: Bearer $SKILLS_MCP_TOKEN"

# Verify
ls ~/.claude/skills/
# pdf/  release-notes/  summarize-meeting/  .skills-sync-meta.json
```

After this runs, Claude Code's native auto-trigger works against the team's canonical skills without any manual copying. The developer re-runs `skills-sync pull` whenever they want fresh content; it's a second or two at most.

### 17.3 Phase 3 (v0.3) — sync maturity

Phase 3 extends `skills-sync` along three axes:

- **Daemon / watch mode.** `skills-sync watch` subscribes to the MCP server's list-changed notifications (where supported) and updates the filesystem on push. No more manual re-runs.
- **Additional target layouts.** `.cursor/rules/<name>.mdc` for Cursor (format conversion: description → frontmatter, body → rule text). Codex layout once Codex settles on a skills convention.
- **Richer conflict handling.** Three-way merge against the last-synced state so local edits that don't conflict with server changes are preserved. Interactive resolution for genuine conflicts instead of unconditional backup-and-overwrite.

Phase 3 scope stays deliberately focused on the sync tool — no other phase-3 server work is planned. The server itself is already full-featured through phase 2.

### 17.4 Split-brain avoidance: sync + server-side execution (phase 2+)

In v0.1 this concern does not arise — the server never executes anything, so materialised bundles and MCP resources are fully interchangeable views of the same read-only content. Phase 2 introduces server-side execution (§16.1), and at that point `skills-sync` has to decide what to do with a skill that declares `tools:` while also being materialised into `~/.claude/skills/`:

- The materialised copy is what Claude Code's native loader reads. If it keeps `tools:` + `scripts/`, the agent now has two ways to run the same functionality: (a) invoke the MCP tool `skill.<name>.<tool>` (server-side, timeout-enforced, audited), or (b) follow the local SKILL.md instructions and execute scripts in its own sandbox. Which path fires is non-deterministic and defeats the point of having a central execution path.

**Normative sync-time rewrite rule (phase 2):** when `skills-sync` materialises a skill whose manifest declares `tools:` **and** the server's `list_skills` reports that skill as having executable tools registered (i.e., the server's gating conditions pass and the MCP tools actually exist), `skills-sync` rewrites the materialised copy to force MCP-side execution:

1. Strip the `tools:` block entirely from the materialised `SKILL.md`.
2. Omit the `scripts/` directory from the materialised bundle (it's never needed locally when the server is the execution path).
3. Prepend a short note to the body explaining that scripted actions for this skill run on the shared skills server, and that the agent should invoke the MCP tools `skill.<name>.<tool>` rather than attempting to run code locally.

For skills that do **not** declare `tools:`, or where the server reports no executable tools registered (execution disabled, trust gates not met, etc.), `skills-sync` materialises the bundle unchanged — `scripts/` and all — and those scripts continue to execute client-side as today. This is the only v0.1 behaviour because no skill in v0.1 has server-side execution.

Effect: at any point in time, for any given skill, there is exactly one execution path visible to the client — either local (scripts in the materialised bundle, no server-side MCP tools) or server-side (MCP tools, no materialised scripts). No split brain.

## 18. Phase 4 (v1.0) — Isolation + registry

Two tracks converge at v1.0:

- **Execution hardening.** Builds on the phase-2 subprocess contract (§16.1.2), not a replacement of it. Adds: per-skill virtualenvs (the server auto-installs each skill's declared `dependencies:` into an isolated env and invokes the venv's interpreter instead of the container's); cgroups-based CPU/memory/wall-clock limits; optional read-only bind mounts so a script can read its bundle but not write outside its temp cwd. The subprocess invocation path stays identical — operators get hardening without any change to the skill format or script code.
- **Opt-in community registry.** Public index at `registry.skills-mcp.org` (or similar) with search, author identity, ratings, signed manifests (Sigstore or similar), and vulnerability reports. The server can point a source at the registry the same way it points at a git URL today. Zero change to the skill format.

---

## 19. Specification review & design amendments

*Incorporates an internal spec review (2026-04-23). These items clarify feasibility, tighten inconsistent wording, and set v0.1 defaults — they are normative where they override earlier ambiguous text. After the v0.1 rephase, some review items now apply to phase 2 scope (§16) rather than v0.1; they remain listed here as the originating rationale.*

### 19.1 Execution model (phase 2, resolved as subprocess)

An earlier draft specified in-process `importlib`-based execution. This was rejected for two reasons raised in review: (a) a runaway or blocking script would hang the server's event loop for every connected client, and (b) `sys.modules` hot-reload is notoriously unreliable and would produce half-old / half-new module state after skill updates. **Normative phase-2 rule (§16.1):** declared tools are invoked in a **fresh Python subprocess** per call, with JSON on stdin, JSON (or text) on stdout. Fresh interpreter per call means timeouts actually kill the runaway, and on-disk updates are picked up automatically on the next invocation. Phase 4 (§18) adds per-skill venvs and resource limits on top of this same subprocess contract.

### 19.2 Hot reload vs MCP clients (v0.1 + phase 2)

The server can reload atomically and emit list-changed notifications where applicable, but many MCP hosts cache tool/prompt lists for the session lifetime. Do not promise universal "no reconnect" behaviour; see §7.2, §12.

### 19.3 Anthropic / public corpus compatibility (v0.1)

Goal §3.2 and §6.1 use **best-effort** language: unknown frontmatter keys are preserved, but "drops in unchanged forever" is not guaranteed against a moving upstream. **Recommendation:** pin `ref:` in config and run a minimal CI job that loads the server against that ref.

### 19.4 Writable sources and agent-initiated edits — removed from scope

An earlier draft specified MCP tools for agents to propose and apply skill edits with a guarded-field approval workflow. **This is permanently out of scope** — authoring goes through git + PR review, never through an MCP mutation path. See §4 and §11.4. Consequence: no `skill_edit` / `skill_create` / `skill_delete` / `skill_propose` tools; no `writable:` / `agent_branch:` / `auto_push:` source options; no `approvals` / `approve` / `reject` / `scaffold` CLI commands.

### 19.5 Webhook authentication (phase 2)

The `POST /webhook/reload` endpoint uses a bearer shared secret, not provider-native HMAC headers. Operators use a custom header, a generic secret in payload, or a verifying proxy (§16.3).

### 19.6 CLI vs live daemon (phase 2)

Full live `skills-mcp-server sync` against a running process requires IPC and careful locking. Acceptable phase-2 delivery: offline-first CLI; live admin socket as stretch/follow-up.

### 19.7 Subprocess execution — what's covered and what isn't (phase 2)

Subprocess invocation resolves the availability and staleness risks of in-process execution (§19.1). What it does **not** give you in phase 2: (a) dependency isolation — all subprocesses share the server container's installed packages, so conflicting version pins break; (b) hard resource limits — a script allocating 8 GB still OOMs the container; (c) filesystem sandboxing beyond POSIX UID checks. All three are phase-4 work (§18). Phase 2 operators should treat `execution.trusted_sources` as load-bearing — it's the only barrier between "your PR-reviewed skill" and "arbitrary code running under your server's identity."

### 19.8 Default resource exposure (v0.1)

"If `resources:` absent, expose all bundle files" is simple but can leak large or unintended trees. **Operator guidance:** prefer explicit `resources:` for published skills; optional future caps (max file size, deny dotfiles) are not required in v0.1.

---

## 20. Open questions

1. **MCP prompt arguments:** some skills might benefit from structured arguments (e.g. `summarize-meeting` taking `style: tl;dr | detailed`). Introduce via an optional `arguments:` frontmatter field in phase 2?
2. **Description-triggered prompts on non-Claude clients:** Cursor/Codex don't auto-trigger prompts by description. Worth also exposing each skill as a tool whose description matches, so agents can invoke a skill as a no-op tool call? Possible UX win, possible noise.
3. **Binary assets (images, fonts) inside skills:** fine as resources, but the server needs a content-type map. Python `mimetypes` with a small override table?
4. **Cache eviction for git sources:** do we keep old refs around for rollback, or prune aggressively? Leaning prune with a `--keep-refs=N` flag (phase 2).
5. **Metrics / telemetry:** none by default. Add an optional `--metrics` flag exposing Prometheus on a side port later?
6. **Container registry for the official image:** GHCR (`ghcr.io/<org>/skills-mcp-server`) is the working assumption. Mirror to Docker Hub (`docker.io/<org>/skills-mcp-server`) for discoverability, or GHCR-only to keep a single source of truth? If mirrored, who owns the sync job?
7. **Rootless / non-docker container runtimes:** the image should work under Podman, containerd, and rootless Docker. Are there runtime-specific quirks — particularly around `-i` for stdio MCP and named volumes — that need explicit mention in §13, or is "any OCI runtime works" a safe claim?

---

*End of spec (v0.1 scope + phase-2 detailed design). Review comments welcome — especially on §2 phased delivery, §11.4 PR-only authoring commitment, §16.1 execution contract, §19 design amendments, and §20 open questions.*
