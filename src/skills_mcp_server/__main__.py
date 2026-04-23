"""Entry point for the `skills-mcp-server` console script."""

from __future__ import annotations

import sys

from skills_mcp_server.cli import main

if __name__ == "__main__":
    sys.exit(main())
