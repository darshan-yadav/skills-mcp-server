"""Entry point for the `skills-mcp-server` console script.

The real CLI surface (run / init / reload / selftest) lives in :mod:`cli`
and will be wired up in a subsequent task. For the scaffolding milestone
this module only provides a stub that confirms the package installed
cleanly and the console entry point is reachable.
"""

from __future__ import annotations

import sys


def main() -> int:
    """Print a stub banner and exit successfully."""
    print("skills-mcp-server v0.1.0-dev \u2014 not yet implemented")
    return 0


if __name__ == "__main__":
    sys.exit(main())
