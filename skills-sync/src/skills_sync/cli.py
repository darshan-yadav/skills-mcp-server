import argparse
import asyncio
import logging
import sys
from pathlib import Path

from skills_sync.core import sync_skills


def main():
    parser = argparse.ArgumentParser(
        description="skills-sync: Companion CLI for skills-mcp-server",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    pull_parser = subparsers.add_parser(
        "pull",
        help="Sync skills from an MCP server to a local directory",
    )
    pull_parser.add_argument(
        "--from",
        dest="from_uri",
        required=True,
        help=(
            "MCP base URL (http(s)://…) or stdio command "
            "(e.g. 'python -m skills_mcp_server run --config cfg.yaml')"
        ),
    )
    pull_parser.add_argument(
        "--to",
        required=True,
        type=Path,
        help="Target root (e.g. ~/.claude/skills)",
    )
    pull_parser.add_argument(
        "--auth-header",
        help="Optional HTTP header, e.g. 'Authorization: Bearer …'",
    )
    pull_parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    pull_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Connect and validate, but do not write files (see SPEC §17.1)",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    if args.command == "pull":
        try:
            asyncio.run(
                sync_skills(
                    args.from_uri,
                    args.to,
                    auth_header=args.auth_header,
                    dry_run=args.dry_run,
                )
            )
        except Exception as e:
            logging.error(f"Sync failed: {e}")
            if args.debug:
                raise
            sys.exit(1)

if __name__ == "__main__":
    main()
