# skills-mcp-server

Open-source [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server in Python. It loads **skill bundles** (folders with a `SKILL.md` plus optional files) from disk or git, then exposes each skill as an MCP **prompt**, bundle files as **resources**, and a small set of **management tools** (`list_skills`, `get_skill_manifest`, `reload`, `server_info`).

**Recommended:** run from the **Docker image** built by this repo (`docker compose build`). Local `pip install` is for **development and tests** only (see [Development](#development)).

Full behaviour, HTTP mode, and image details: [`SPEC.md`](./SPEC.md) (especially §13).

Replace `ghcr.io/<org>/skills-mcp-server:0.1` in the optional sections below with your published image when you are not building locally.

---

## Quick start (minimal setup, no coding)

From a clone of this repository you only need a few shell commands. **Default layout:** skills in `./skills/`, config in `./config/`, writable state in `./data/` (gitignored).

1. **Clone and enter the repo**

   ```bash
   git clone https://github.com/<org>/skills-mcp-server.git
   cd skills-mcp-server
   ```

2. **Add or replace skills** under `./skills/` (one bundle = one folder with `SKILL.md` at its root). A tiny **`example-greeting`** bundle is included so selftest works immediately; delete or keep it as a template.

3. **Create the data directory** (host bind mount for git cache and server state)

   ```bash
   mkdir -p data
   ```

4. **Build the image**

   ```bash
   docker compose build
   ```

5. **Validate config and loads** (exits after checks; no MCP session required)

   ```bash
   docker compose run --rm skills-mcp-server selftest --config /config/config.yaml
   ```

6. **Use MCP from your editor** — point the client at **`docker`** with image **`skills-mcp-server:local`** and **absolute** host paths for `./config`, `./skills`, and `./data` (see [Wire MCP in Claude Code, Cursor, and Codex](#wire-mcp-in-claude-code-cursor-and-codex)). The server speaks **stdio** MCP; the client must run Docker with **`-i`** so stdin stays open.

**Optional terminal smoke test** (foreground MCP on your shell stdin; Ctrl+C to stop):

```bash
docker compose run --rm -i skills-mcp-server
```

That runs the same command as `docker compose up` would for this service (`run --config /config/config.yaml`). Prefer **`compose run`** for stdio tests so you do not need a long-lived `up` container.

**Note:** `docker compose up -d` runs the process detached from your terminal, which **breaks stdio MCP**. Use **`docker compose run --rm -i …`** or let the **editor** launch **`docker run -i …`** (as in the JSON/TOML snippets below).

---

## Where to put skills (this repo’s defaults)

Skills live in **`./skills/`** on the host (mounted read-only at **`/skills`** in the container). The server loads **one bundle per folder** that contains a **`SKILL.md`** at that folder’s root.

```text
skills/
├── example-greeting/          # shipped example (safe to remove)
│   └── SKILL.md
├── my-skill/
│   └── SKILL.md
└── ...
```

**Minimum `SKILL.md`:** frontmatter must include `name` (slug) and `description` (natural-language trigger text). See `SPEC.md` §6 and `tests/fixtures/skills/local-sample/` for more examples.

---

## Configure the server (`config/config.yaml`)

For the compose workflow, **`config/config.yaml`** is already committed with container paths matching the default mounts:

```yaml
sources:
  - name: local
    type: local
    path: /skills
data_dir: /data
log_level: info
```

**Git source example** (optional second source) — edit `config/config.yaml` after copying the pattern:

```yaml
sources:
  - name: local
    type: local
    path: /skills
  - name: team-repo
    type: git
    url: https://github.com/your-org/skills.git
    ref: main
data_dir: /data
log_level: info
```

Validate **inside the container** (same mounts as `run`):

```bash
docker compose run --rm skills-mcp-server selftest --config /config/config.yaml
```

---

## Run with Docker (three mounts)

The container **`ENTRYPOINT`** is `skills-mcp-server`. Arguments after the **image name** in `docker run` are **subcommand arguments only** (for example `run --config …` or `selftest --config …`), not a second `skills-mcp-server` token.

| Host (this repo) | Container | Purpose |
|------------------|-----------|--------|
| `./config` | `/config` | `config.yaml` (usually `:ro`) |
| `./skills` | `/skills` | Skill bundles (usually `:ro`) |
| `./data` | `/data` | Git cache and writable server state |

### stdio (per editor session) — most common

MCP over stdin/stdout. **`-i`** keeps stdin open for the protocol.

**After `docker compose build`**, using the local image:

```bash
docker run -i --rm \
  -v "$PWD/config:/config:ro" \
  -v "$PWD/skills:/skills:ro" \
  -v "$PWD/data:/data" \
  skills-mcp-server:local \
  run --config /config/config.yaml
```

Published image (replace org/tag):

```bash
docker run -i --rm \
  -v "$HOME/.config/skills-mcp-server:/config:ro" \
  -v "skills-mcp-data:/data" \
  -v "$HOME/skills:/skills:ro" \
  ghcr.io/<org>/skills-mcp-server:0.1 \
  run --config /config/config.yaml
```

Create the named volume once if you use that variant: `docker volume create skills-mcp-data`.

### HTTP (shared team daemon)

One long-lived container; clients that support HTTP MCP connect to it. See **`SPEC.md` §13.3.2** for ports, TLS in front, and deployment notes.

---

## Wire MCP in Claude Code, Cursor, and Codex

Point each client at **`docker`** so every session uses the same image and mounts. Expand **`REPO`** to the **absolute** path of your git clone (the directory that contains `config/`, `skills/`, and `data/`).

### Claude Code

File: `~/.claude/mcp_servers.json` (or your product’s equivalent).

```json
{
  "mcpServers": {
    "skills": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "REPO/config:/config:ro",
        "-v", "REPO/skills:/skills:ro",
        "-v", "REPO/data:/data",
        "skills-mcp-server:local",
        "run", "--config", "/config/config.yaml"
      ]
    }
  }
}
```

### Cursor

File: `~/.cursor/mcp.json` (or project `.cursor/mcp.json`).

```json
{
  "mcpServers": {
    "skills": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "REPO/config:/config:ro",
        "-v", "REPO/skills:/skills:ro",
        "-v", "REPO/data:/data",
        "skills-mcp-server:local",
        "run", "--config", "/config/config.yaml"
      ]
    }
  }
}
```

Reload MCP after changes (Command Palette → MCP-related reload, depending on version).

### OpenAI Codex CLI

File: `~/.codex/config.toml`.

```toml
[mcp_servers.skills]
command = "docker"
args = [
  "run", "-i", "--rm",
  "-v", "REPO/config:/config:ro",
  "-v", "REPO/skills:/skills:ro",
  "-v", "REPO/data:/data",
  "skills-mcp-server:local",
  "run", "--config", "/config/config.yaml",
]
```

### What you get in the client

- **Prompts:** one per skill (`prompts/list` / `prompts/get`).
- **Resources:** `skill://<source-name>/<bundle-folder>/<relative-path>` (see `SPEC.md` §8.2).
- **Tools:** `list_skills`, `get_skill_manifest`, `reload`, `server_info` only in v0.1.

If lists look stale after a git update, **reconnect MCP** or restart the host (`SPEC.md` §12).

---

## Local Python (development only)

Contributors run from a venv to iterate on code; this is **not** the recommended deployment path.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install -e "./skills-sync[dev]"

skills-mcp-server init              # ./config.yaml; edit paths for your machine
skills-mcp-server run --config ./config.yaml

pytest tests skills-sync/tests
ruff check .
ruff format .
```

---

## Claude Code native auto-trigger (`skills-sync`)

Claude Code can auto-match skills from **`~/.claude/skills/`** on disk. **`skills-sync`** pulls from the same MCP server (including a **`docker run …`** stdio command) and writes that tree. Install from the `skills-sync/` package or published wheel.

```bash
skills-sync pull \
  --from "docker run -i --rm -v REPO/config:/config:ro -v REPO/skills:/skills:ro -v REPO/data:/data skills-mcp-server:local run --config /config/config.yaml" \
  --to ~/.claude/skills
```

More detail: [`skills-sync/README.md`](./skills-sync/README.md), [`docs/skills-sync-architecture.md`](./docs/skills-sync-architecture.md).

---

## Development

Clone the repo, use **`.venv`**, run tests and linters as above. Package layout: `src/skills_mcp_server/`. Python **3.11+**.

Without activating the venv: `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/python -m skills_mcp_server`.
