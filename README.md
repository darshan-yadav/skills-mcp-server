# skills-mcp-server

**Status:** Draft / pre-alpha. v0.1 scaffolding only — not yet functional.

`skills-mcp-server` is an open-source Model Context Protocol (MCP) server,
written in Python, that hosts a library of "skills" (SKILL.md folder bundles)
and serves them to any MCP-capable agent — Claude Code, Cursor, OpenAI Codex
CLI, and others. One canonical store, consumable by every tool that speaks
MCP.

Full design lives in [`SPEC.md`](./SPEC.md). Read §§3–15 for v0.1 scope and
§16 for phase 2.

## Quick start (Docker)

The primary distribution format is an OCI container image published to GHCR
(image is not yet available — placeholder for v0.1).

```bash
# Generate a starter config
mkdir -p ~/.config/skills-mcp-server ~/skills
docker run --rm \
  -v ~/.config/skills-mcp-server:/config \
  -v ~/skills:/skills \
  ghcr.io/darshanyadav/skills-mcp-server:0.1 \
  skills-mcp-server init --config /config/config.yaml

# Run over stdio (per-client local use)
docker run -i --rm \
  -v ~/.config/skills-mcp-server:/config:ro \
  -v skills-mcp-data:/data \
  -v ~/skills:/skills:ro \
  ghcr.io/darshanyadav/skills-mcp-server:0.1
```

See SPEC §13 for the HTTP (team-shared daemon) deployment and editor wiring.

## Development

Always work inside a virtual environment — never install into your system
Python. The repo layout assumes a `.venv/` at the project root (ignored by
git).

```bash
# one-time setup
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

# daily loop
source .venv/bin/activate     # activate once per shell
pytest                        # run tests
ruff check .                  # lint
ruff format .                 # autoformat
```

Python 3.11+ required. Source lives under `src/skills_mcp_server/`.
Configuration for lint/test/build lives in `pyproject.toml`.

If you prefer not to activate, call the venv binaries directly —
`.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/python -m skills_mcp_server`.
This is also the pattern the agent-driven workflow uses for verification.
