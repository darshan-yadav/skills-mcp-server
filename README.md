# skills-mcp-server

This project is an open-source **[Model Context Protocol](https://modelcontextprotocol.io/) (MCP)** server written in Python. You put **skill bundles** (folders with a `SKILL.md` and optional files) on disk; the server loads them and exposes them to Claude Code, Cursor, OpenAI Codex, or any other MCP host.

**What the client sees**

- **Prompts** — one MCP prompt per skill (name + description come from `SKILL.md` frontmatter; body is the markdown below the frontmatter).
- **Resources** — files inside each bundle (e.g. `REFERENCE.md`, `scripts/helper.py`) as readable MCP resources. **v0.1 does not run those scripts on the server**; the agent may run them in its own environment if it chooses.
- **Tools** — only these four server tools: `list_skills`, `get_skill_manifest`, `reload`, `server_info`. There are no per-skill execution tools in v0.1.

**How you are meant to run it (team intent)**

- **Single source of truth for skills** is **git** (shared repo, PR review). Nobody needs Docker to **author** or **review** skills — only a text editor and git access.
- **MCP is how editors consume that library at runtime.** Something must run the **`skills-mcp-server`** process **somewhere** the MCP host can attach to. **Docker on the laptop** is the **default** in this README because it is reproducible and avoids local Python drift — it is **not** a statement that every engineer must have admin rights or Docker.
- If Docker is impossible, use **user-level Python** (`pipx`, `venv` + `pip install`) and point MCP at the **`skills-mcp-server`** binary with **`run --config …`** (see [Without Docker (user-level Python)](#without-docker-user-level-python) under §3).
- If **no local MCP process** is allowed on laptops, run a **central** instance with **`run-http`** (MCP over **SSE** on one TCP port). Clients use a **base URL** such as `http://skills-mcp.internal:8847` (put TLS and network ACLs in front as you prefer; v0.1 does **not** implement app-level auth on MCP or reload routes). **`skills-sync pull --from https://…`** uses that same HTTP MCP surface to materialise skills under `~/.claude/skills/`.

**Docker quick path:** run **`./setup.sh --prepare-only`** once after clone (creates **`./data`**, builds **`skills-mcp-server:local`**, runs **selftest**), then point your editor’s MCP config at **`docker run …`** with **`config/`**, **`skills/`**, and **`data/`** mounted from the repo. For a **terminal** MCP smoke test, run **`./setup.sh`**. You do **not** need `~/.config/...` unless you choose that layout yourself.

---

## Prerequisites

Pick **at least one** way to run the server process your editor will attach to:

- **Docker path (documented first below):** Docker (BuildKit) and **Docker Compose v2** (`docker compose`).
- **No Docker:** Python **3.11+** and permission to install the **`skills-mcp-server`** package into a **user** environment (`pipx`, or a venv under your home directory — often allowed without machine admin).
- **Git**, to clone this repository (for the packaged layout and `setup.sh`). To consume **only** a team skills git repo, git alone is enough for authoring; MCP still needs one of the runtimes above or a hosted URL.

---

## 1. Get the code and create runtime folders

Pick a parent directory where you keep code (examples: `~/code`, `~/Documents/code`). Then:

```bash
mkdir -p ~/code
cd ~/code
git clone https://github.com/darshanyadav/skills-mcp-server.git
cd skills-mcp-server
```

This repository already contains:

- **`config/config.yaml`** — default server config (you can edit later).
- **`skills/`** — where your skill bundles live; includes a tiny **`example-greeting`** sample.
- **`setup.sh`** — creates **`./data`**, builds the image, runs **selftest**, then optionally starts MCP on stdio.

Make the script executable once:

```bash
chmod +x setup.sh
```

The **`data/`** directory is created by **`setup.sh`** (or Compose on first run). It is listed in `.gitignore` so runtime state is never committed.

**Layout after clone**

```text
skills-mcp-server/          # REPO root — use its absolute path in MCP JSON (see §3)
├── config/
│   └── config.yaml         # mounted read-only at /config/config.yaml in the container
├── skills/                 # mounted read-only at /skills — your SKILL.md bundles live here
│   └── example-greeting/
│       └── SKILL.md
├── data/                   # created by setup.sh — git clones and locks
├── setup.sh
├── docker-compose.yml
├── Dockerfile
└── ...
```

---

## 2. Build, validate, and run (`setup.sh`)

From the repository root (`skills-mcp-server/`):

**Before configuring your editor** — build the image and confirm config + skills load (then exit):

```bash
./setup.sh --prepare-only
```

**Terminal MCP smoke test** — same as above, then keep the server running on **stdio** until you press Ctrl+C (handy to verify Docker; your IDE still uses its own `docker run …`):

```bash
./setup.sh
```

This tags the image as **`skills-mcp-server:local`**. If **selftest** fails, fix paths in `config/config.yaml` or add a valid `SKILL.md` under `skills/` before continuing.

Equivalent manual commands (if you prefer not to use the script):

```bash
mkdir -p data
docker compose build
docker compose run --rm skills-mcp-server selftest --config /config/config.yaml
docker compose run --rm -i skills-mcp-server   # start MCP on stdio
```

---

## 3. Point your editor at Docker (stdio MCP)

The server speaks **MCP over stdin/stdout**. The editor runs **`docker`** with **`-i`** so stdin stays open. The image **`ENTRYPOINT`** is already `skills-mcp-server`, so arguments after the image name must be **`run --config /config/config.yaml`** (do **not** add a second `skills-mcp-server` token).

**Replace `REPO` with the absolute path to the repository root** — the directory that contains `config`, `skills`, and `data`. Examples:

- macOS/Linux: run `pwd` while inside that directory, e.g. `/Users/you/code/skills-mcp-server`.
- Use a real path in JSON; most MCP config files do **not** expand `$HOME` or environment variables.

### Cursor

Edit **`~/.cursor/mcp.json`** (user-wide) or **`.cursor/mcp.json`** inside a project.

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

Reload MCP from the Command Palette after saving.

### Claude Code

Edit **`~/.claude/mcp_servers.json`** (or the path your install uses for MCP servers). Use the same `command` / `args` block as Cursor above.

### OpenAI Codex CLI

Edit **`~/.codex/config.toml`**:

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

### Without Docker (user-level Python)

Many laptops allow **pipx** or a **venv** without admin rights. Install the CLI, keep a **config file on disk** whose `path:` and `data_dir:` are **host paths** (not `/skills` / `/data` from the Docker-only file unless you mirror that layout on the host).

Example **`~/.config/skills-mcp-server/config.host.yaml`** (adjust usernames and clone path):

```yaml
sources:
  - name: local
    type: local
    path: /Users/you/code/skills-mcp-server/skills
  - name: team-skills
    type: git
    url: https://github.com/your-org/team-skills.git
    ref: main
data_dir: /Users/you/code/skills-mcp-server/data
log_level: info
```

Point Cursor (or similar) at the installed entrypoint — **no `docker` in `command`**:

```json
{
  "mcpServers": {
    "skills": {
      "command": "/Users/you/.local/bin/skills-mcp-server",
      "args": ["run", "--config", "/Users/you/.config/skills-mcp-server/config.host.yaml"]
    }
  }
}
```

Use the real path from `which skills-mcp-server` after `pipx install skills-mcp-server` (or your venv’s `bin/skills-mcp-server`). The editor still uses **stdio** MCP; nothing in this path requires the Docker daemon.

### No local MCP at all (locked-down laptops)

If policy forbids **any** long-lived local server process, the team needs a **centrally operated** MCP server (or gateway) reachable over the network with **TLS and authentication**, and editors configured to that **remote MCP** product capability. That is an **operational** pattern, not something a single developer can turn on from this README alone: **`skills-mcp-server run` today is stdio-first** for the MCP session. **`skills-sync`** can already target **`--from https://…`** for **pulling skill trees to disk** (Claude Code layout) once your platform exposes a compatible HTTP MCP server.

### Optional: using a published image instead of a local build

If you use an image from a registry (example tag shown for this repo), keep the same three mounts and only change the image reference:

```bash
docker pull ghcr.io/darshanyadav/skills-mcp-server:0.1
```

```text
ghcr.io/darshanyadav/skills-mcp-server:0.1
```

You still need a **`config.yaml`** on the host (for example copy this repo’s `config/config.yaml` next to your skills and mount it at `/config`).

---

## 4. Add and edit skills

### Folder rule

- **One bundle = one directory** under `skills/` with a **`SKILL.md` at that directory’s root** (not only in subfolders).
- You may nest bundles in subdirectories; the scanner walks the tree under `skills/` and discovers each folder that contains `SKILL.md`. Walk depth is **capped** (several levels deep — enough for `skills/team/foo/SKILL.md`-style layouts).
- **Keep the folder name aligned with `name` in frontmatter.** The MCP **prompt** uses the frontmatter `name`, but **resource URIs** use the **directory name** (the folder that contains `SKILL.md`). If they differ, you will reference resources with the folder name, not the frontmatter `name`.

### Minimum `SKILL.md`

YAML **frontmatter** (between `---` lines) at the top is required. For v0.1 you need at least:

| Field           | Required | Purpose |
|-----------------|----------|---------|
| `name`          | yes      | MCP prompt name. Unique per **source** (first wins if duplicated across sources). Resource URIs use the **folder** name — keep them the same. |
| `description`   | yes      | Shown to the model as the prompt description — write it so the host knows *when* to use the skill. |

Optional frontmatter (ignored for execution in v0.1 but preserved): `version`, `tags`, `license`, `resources` (allowlist of files to expose), `tools`, `trust_level`, `dependencies`.

### Example skill (copy and adapt)

Save as `skills/my-first-skill/SKILL.md`:

```markdown
---
name: my-first-skill
description: Use when the user wants a one-line hello as a minimal custom skill example.
---

# My first skill

Respond with exactly one line: "Hello from my-first-skill."
```

Restart MCP or call the `reload` tool after large changes; some hosts cache prompt lists until the session reconnects.

### Bundle files as resources

Each file in the bundle can be read as an MCP resource. URIs use the **source name** from `config.yaml`, the **bundle directory name** (the folder that holds `SKILL.md`), and a **relative path** inside that folder:

```text
skill://<source-name>/<bundle-folder>/<relative-path>
```

The default local source in `config/config.yaml` is named **`local`**. If the directory is `skills/my-first-skill/` and it contains `REFERENCE.md`:

```text
skill://local/my-first-skill/REFERENCE.md
```

If frontmatter includes a `resources:` list, only those paths are exposed; if omitted, all files in the bundle are exposed (prefer an allowlist for shared repos).

---

## 5. Configure sources (`config/config.yaml`)

Default file (already in the repo):

```yaml
sources:
  - name: local
    type: local
    path: /skills
data_dir: /data
log_level: info
# Optional — central HTTP MCP (``run-http`` only; defaults shown):
# http_host: "0.0.0.0"
# http_port: 8847
```

Paths like **`/skills`** and **`/data`** are **inside the container** and must match your `docker run` / Compose volume mounts.

### Add a git source (optional)

Example second source (edit URLs and refs for your org):

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

Git clones are stored under **`data_dir`**. If the same skill `name` appears in more than one source, the **first source in the list wins**.

---

## 6. Docker and Compose behaviour (short)

| Host path (in clone) | Container path | Purpose |
|----------------------|----------------|---------|
| `./config`           | `/config`      | `config.yaml` (mount `:ro` once you are happy with it) |
| `./skills`           | `/skills`      | Skill bundles |
| `./data`             | `/data`        | Writable: git cache, locks |

**Smoke test in a terminal** (MCP on your shell stdin; Ctrl+C to stop): run **`./setup.sh`** (build + selftest + start), or only the last step:

```bash
docker compose run --rm -i skills-mcp-server
```

**Why not `docker compose up -d` for MCP?**

Detached `up` does not give the process a usable stdin for stdio MCP. Editors should launch **`docker run -i …`** (as in the JSON above), or you use **`docker compose run --rm -i …`** for manual testing.

### Central HTTP MCP (`run-http`, SSE)

For a **shared** server (EC2, ECS, internal k8s Service, etc.), run **`skills-mcp-server run-http`** instead of **`run`**. One process serves:

| Method | Path | Purpose |
|--------|------|--------|
| `GET` | `/health` | Liveness (`ok`) |
| `GET` | `/sse` | MCP session (Server-Sent Events) |
| `POST` | `/messages/?session_id=…` | Client JSON-RPC (per session; path advertised in the SSE stream) |
| `POST` | `/webhook/reload` | Same bearer behaviour as stdio mode if `webhook_secret` is set |
| `POST` | `/admin/reload` | Trigger reload from anywhere (restrict with firewall / private network) |

**Compose (central):** from the repo root, with the same `./config`, `./skills`, `./data` layout:

```bash
mkdir -p data
docker compose -f docker-compose.central.yml up --build
```

This publishes **`8847`** (`EXPOSE` in the `Dockerfile`). Override bind address or port in **`config/config.yaml`** with optional keys:

```yaml
http_host: "0.0.0.0"
http_port: 8847
```

**`skills-sync`** over the network (no Docker on the laptop):

```bash
skills-sync pull --from http://YOUR_HOST_OR_IP:8847 --to ~/.claude/skills
```

Editors that support **remote MCP over HTTP/SSE** can point at the same base URL (exact config depends on the product). Stdio-only hosts keep using **`docker run -i … run`** against a local image.

---

## 7. Claude Code auto-trigger (`skills-sync`)

Claude Code can load skills from **`~/.claude/skills/`** on disk. The **`skills-sync`** helper in this repository can pull manifests from the same MCP server you already run via Docker and write that tree. Install and usage:

- [`skills-sync/README.md`](./skills-sync/README.md)
- [`docs/skills-sync-architecture.md`](./docs/skills-sync-architecture.md)

Example `pull` using the same Docker command as in your MCP config (set `REPO` to your clone path):

```bash
skills-sync pull \
  --from "docker run -i --rm -v REPO/config:/config:ro -v REPO/skills:/skills:ro -v REPO/data:/data skills-mcp-server:local run --config /config/config.yaml" \
  --to ~/.claude/skills
```

---

## 8. Local Python (contributors only)

Not required to **use** the server. For working on the code:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install -e "./skills-sync[dev]"

# One-time: writes ./config.yaml with ./skills and ./data (host paths).
skills-mcp-server init .
skills-mcp-server run --config ./config.yaml

pytest tests skills-sync/tests
ruff check .
ruff format .
```

Layout: `src/skills_mcp_server/`. Python **3.11+**.

---

## 9. Maintainer note

`SPEC.md` in this repository is the long-form **design and phase roadmap** (HTTP hardening, future execution, etc.). Everything you need to **install, configure, and wire MCP** is intended to live in this README.
