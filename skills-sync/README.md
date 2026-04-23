# skills-sync

Companion CLI to materialize skills from `skills-mcp-server` into the local filesystem so Claude Code's native auto-trigger works.

```bash
pipx install skills-sync

# HTTP (SSE) deployment
skills-sync pull \
  --from https://skills.acme.internal:7425 \
  --to ~/.claude/skills \
  --auth-header "Authorization: Bearer $SKILLS_MCP_TOKEN"

# stdio (local server process)
skills-sync pull \
  --from "python -m skills_mcp_server run --config ~/.config/skills-mcp-server/config.yaml" \
  --to ~/.claude/skills
```

See SPEC §17 and [docs/skills-sync-architecture.md](../docs/skills-sync-architecture.md) for conflict policy (server wins), split-brain avoidance (§17.4), and testing notes.
