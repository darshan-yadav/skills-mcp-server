"""Source abstraction — see SPEC §7.

A source is a thing that produces ``SkillBundle`` values: either a local
directory (``LocalSource``) or a git repo (``GitSource``, landing later).
The contract is intentionally thin — a ``name`` and a ``load()`` iterator —
so the registry can drive any number of sources through the same code path
and hot-swap their output atomically (SPEC §11.3).

One misbehaving bundle must not kill a whole source. Implementations raise
``SourceError`` for non-fatal per-bundle problems (e.g. malformed
frontmatter) so the registry can log and continue. A ``SourceError`` raised
from ``__init__`` means the source itself is unusable (e.g. the configured
root does not exist) — that one is fatal.
"""

from __future__ import annotations

from typing import Iterator, Protocol, runtime_checkable

from skills_mcp_server.models import SkillBundle


class SourceError(Exception):
    """Non-fatal problem loading a skill bundle.

    Implementations either raise this (when giving up on one bundle) or
    log it and continue. Sources should not raise this to abort the whole
    load — a single bad bundle must never take the server down. See
    SPEC §11.3.
    """


@runtime_checkable
class Source(Protocol):
    """Protocol implemented by every skill source.

    ``name`` is the operator-configured source name (e.g. ``local-dev``).
    ``load()`` is called by the registry on startup and again on every
    reload. It yields one ``SkillBundle`` per valid skill found. It must
    not raise for per-bundle problems; skip and log instead.
    """

    name: str

    def load(self) -> Iterator[SkillBundle]:  # pragma: no cover - protocol
        ...
