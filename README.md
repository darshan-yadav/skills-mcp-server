# skills-mcp-server

An open-source **[Model Context Protocol](https://modelcontextprotocol.io/) (MCP)** server that hosts your **skill bundles** (folders with a `SKILL.md`) and serves them to Claude Code, Cursor, OpenAI Codex, or any other MCP host.

**Define a skill once — use it everywhere.**

---

## Quick start (Docker, HTTP MCP)

You need **Docker** with **Compose v2**. That's it.

```bash
git clone https://github.com/darshanyadav/skills-mcp-server.git
cd skills-mcp-server
docker compose -f docker-compose.central.yml up --build
```

The server is now running as an HTTP MCP server on **http://localhost:8847**.

Check it's up:

```bash
curl http://localhost:8847/health
# -> ok
```

MCP clients connect to the SSE endpoint: **http://localhost:8847/sse**

---

## Connect your editor

### Claude Code

```bash
claude mcp add --transport sse skills http://localhost:8847/sse
```

### Cursor

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "skills": {
      "url": "http://localhost:8847/sse"
    }
  }
}
```

### OpenAI Codex CLI

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.skills]
url = "http://localhost:8847/sse"
```

Reload MCP from your editor and you'll see your skills as prompts.

---

## Add your first skill

**Put your skills in the `skills/` folder at the repo root.** One folder per skill, each with a `SKILL.md` inside. That folder is mounted into the server as `/skills` — nothing else to configure.

You can keep skills flat directly under `skills/`, or group them into subdirectories (e.g. `skills/roles/`, `skills/security/`). The server walks up to **3 directories deep** and discovers every folder that contains a `SKILL.md`. Resource URIs always use just the leaf folder name — `skill://local/<folder>/<path>` — so grouping is free organisation with no URI impact.

```text
skills-mcp-server/
├── skills/                         ← drop your skills here
│   ├── example-greeting/           ← flat layout (depth 1)
│   │   └── SKILL.md
│   ├── my-first-skill/             ← your new skill
│   │   └── SKILL.md
│   ├── roles/                      ← grouped layout (depth 2)
│   │   ├── dev/
│   │   │   └── SKILL.md
│   │   └── qa/
│   │       └── SKILL.md
│   └── summarize-doc/              ← skills can bundle extra files
│       ├── SKILL.md
│       ├── REFERENCE.md
│       └── scripts/
│           └── helper.py
```

> The **folder name** becomes the slug in the resource URI. Keep folder names unique within a source — if two bundles share a leaf name (`skills/a/dev/` and `skills/b/dev/`), only the first one wins.

Create `skills/my-first-skill/SKILL.md`:

```markdown
---
name: my-first-skill
description: Use when the user wants a simple greeting example.
---

# My first skill

Respond with: "Hello from my-first-skill."
```

Pick up the change without restarting:

```bash
curl -X POST http://localhost:8847/admin/reload
```

Or call the `reload` MCP tool from your editor.

**Frontmatter rules (minimum):**

| Field         | Required | Purpose                                                     |
|---------------|----------|-------------------------------------------------------------|
| `name`        | yes      | MCP prompt name (keep it the same as the folder name).      |
| `description` | yes      | Tells the model *when* to use the skill.                    |

Extra files in the bundle (e.g. `REFERENCE.md`, `scripts/helper.py`) are auto-exposed as MCP **resources** at `skill://local/<folder>/<path>`. No wiring needed — just drop them next to `SKILL.md`.

> Want skills to live **outside** this repo? Point `docker-compose.central.yml` at your own folder:
> `- /path/to/your/skills:/skills:ro`

---

## Pull skills from a git repo

Edit `config/config.yaml` and add a `git` source:

```yaml
sources:
  - name: local
    type: local
    path: /skills
  - name: team
    type: git
    url: https://github.com/your-org/skills.git
    ref: main
data_dir: /data
log_level: info
```

Restart the compose stack. Team skills now appear alongside local ones.

If the same skill `name` appears in multiple sources, the **first one listed wins**.

---

## What the client sees

- **Prompts** — one per skill (from `SKILL.md` frontmatter + body).
- **Resources** — files in each bundle, readable over MCP.
- **Tools** — `list_skills`, `get_skill_manifest`, `reload`, `server_info`.

v0.1 does **not** execute skill scripts on the server — agents run those in their own environment.

---

## Other ways to run

<details>
<summary><b>Stdio mode (per-laptop Docker)</b></summary>

If your editor only supports stdio MCP, point it at `docker compose run` directly:

```json
{
  "mcpServers": {
    "skills": {
      "command": "docker",
      "args": [
        "compose",
        "-f", "/absolute/path/to/skills-mcp-server/docker-compose.yml",
        "run", "--rm", "-i", "skills-mcp-server"
      ]
    }
  }
}
```
</details>

<details>
<summary><b>Without Docker (pipx or venv)</b></summary>

```bash
pipx install skills-mcp-server
skills-mcp-server run-http --config ./config/config.yaml
```

Then connect your editor to `http://localhost:8847/sse` as above.
</details>

<details>
<summary><b>skills-sync — materialise skills to <code>~/.claude/skills/</code></b></summary>

Claude Code auto-loads skills from `~/.claude/skills/`. To mirror what your MCP server exposes into that folder:

```bash
skills-sync pull --from http://localhost:8847 --to ~/.claude/skills
```

See [`skills-sync/README.md`](./skills-sync/README.md) for details.
</details>

<details>
<summary><b>Local development</b></summary>

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install -e "./skills-sync[dev]"
pytest
```

Source layout: `src/skills_mcp_server/`. Python 3.11+.
</details>

---

## HTTP endpoints (for ops)

| Method | Path                             | Purpose                                   |
|--------|----------------------------------|-------------------------------------------|
| `GET`  | `/health`                        | Liveness probe                            |
| `GET`  | `/sse`                           | MCP session (Server-Sent Events)          |
| `POST` | `/messages/?session_id=…`        | Client JSON-RPC (path advertised via SSE) |
| `POST` | `/admin/reload`                  | Trigger a skill reload                    |
| `POST` | `/webhook/reload`                | Reload via webhook (bearer-authenticated) |

Put TLS and network ACLs in front when exposing beyond localhost. v0.1 does not implement app-level auth on the MCP or reload routes.

---

## Docs

- [`SPEC.md`](./SPEC.md) — full design spec and roadmap
- [`docs/agentic-sdlc.md`](./docs/agentic-sdlc.md) — architecture notes
- [`skills-sync/README.md`](./skills-sync/README.md) — the skills-sync helper
