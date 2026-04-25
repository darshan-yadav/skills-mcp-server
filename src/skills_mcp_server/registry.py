"""Central registry of loaded skills."""

import logging
from collections.abc import Iterator

from skills_mcp_server.models import SkillBundle, ToolManifest
from skills_mcp_server.sources.base import Source

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Aggregates skills from multiple sources and provides indexed access."""

    def __init__(self, sources: list[Source]) -> None:
        self.sources = sources
        self._bundles: dict[str, SkillBundle] = {}
        self._tools: dict[str, tuple[SkillBundle, ToolManifest]] = {}
        self._source_bundles: dict[str, list[SkillBundle]] = {}

    def reload(self, source_names: set[str] | None = None) -> None:
        """Reload all sources or a selected subset.

        Collisions (two bundles with the same name) warn and the later source wins.
        """
        if source_names is not None:
            known_sources = {source.name for source in self.sources}
            unknown = sorted(source_names - known_sources)
            if unknown:
                raise ValueError(f"Unknown source(s): {', '.join(unknown)}")
            if not self._source_bundles:
                # No cache yet — fall back to a full load so indexes are complete.
                source_names = None

        new_source_bundles: dict[str, list[SkillBundle]] = {}
        for source in self.sources:
            should_reload = source_names is None or source.name in source_names
            if should_reload:
                logger.info("loading source %r", source.name)
                new_source_bundles[source.name] = list(source.load())
            else:
                new_source_bundles[source.name] = list(self._source_bundles.get(source.name, []))

        self._source_bundles = new_source_bundles
        self._rebuild_indexes()
        logger.info("reload complete. %d skills loaded.", len(self._bundles))

    def reload_source(self, source_name: str) -> None:
        """Reload a single source and rebuild merged indexes."""
        self.reload({source_name})

    def _rebuild_indexes(self) -> None:
        new_bundles: dict[str, SkillBundle] = {}
        new_tools: dict[str, tuple[SkillBundle, ToolManifest]] = {}

        for source in self.sources:
            for bundle in self._source_bundles.get(source.name, []):
                name = bundle.manifest.name
                if name in new_bundles:
                    logger.warning(
                        "skill name collision: %r provided by both %r and %r. Overwriting with the latter.",
                        name,
                        new_bundles[name].source_name,
                        bundle.source_name,
                    )
                new_bundles[name] = bundle

                for tool in bundle.manifest.tools:
                    if tool.name in new_tools:
                        logger.warning(
                            "tool name collision: %r from skill %r overwritten by skill %r.",
                            tool.name,
                            new_tools[tool.name][0].manifest.name,
                            name,
                        )
                    new_tools[tool.name] = (bundle, tool)

        self._bundles = new_bundles
        self._tools = new_tools

    def get_bundle(self, name: str) -> SkillBundle | None:
        """Get a loaded bundle by its manifest name."""
        return self._bundles.get(name)

    def iter_bundles(self) -> Iterator[SkillBundle]:
        """Iterate over all loaded bundles."""
        yield from self._bundles.values()

    def get_tool(self, tool_name: str) -> tuple[SkillBundle, ToolManifest] | None:
        return self._tools.get(tool_name)

    def iter_tools(self) -> Iterator[tuple[SkillBundle, ToolManifest]]:
        yield from self._tools.values()
