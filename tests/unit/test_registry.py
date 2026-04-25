from pathlib import Path

from skills_mcp_server.models import SkillBundle, SkillManifest
from skills_mcp_server.registry import SkillRegistry


class MockSource:
    def __init__(self, name, bundles):
        self.name = name
        self.bundles = bundles

    def load(self):
        yield from self.bundles


def test_registry_reload_and_get():
    bundle1 = SkillBundle(
        source_name="src1",
        slug="slug1",
        bundle_path=Path("/tmp"),
        manifest=SkillManifest(name="skill1", description="desc"),
        body="body1",
        resources=(),
    )

    registry = SkillRegistry([MockSource("src1", [bundle1])])
    registry.reload()

    assert registry.get_bundle("skill1") is bundle1
    assert list(registry.iter_bundles()) == [bundle1]


def test_registry_collision():
    bundle1 = SkillBundle(
        source_name="src1",
        slug="slug1",
        bundle_path=Path("/tmp"),
        manifest=SkillManifest(name="skill1", description="desc1"),
        body="body1",
        resources=(),
    )
    bundle2 = SkillBundle(
        source_name="src2",
        slug="slug2",
        bundle_path=Path("/tmp"),
        manifest=SkillManifest(name="skill1", description="desc2"),
        body="body2",
        resources=(),
    )

    registry = SkillRegistry([MockSource("src1", [bundle1]), MockSource("src2", [bundle2])])
    registry.reload()

    # Latter source should win
    assert registry.get_bundle("skill1") is bundle2


def test_registry_reload_single_source_updates_only_that_source():
    bundle1 = SkillBundle(
        source_name="src1",
        slug="slug1",
        bundle_path=Path("/tmp"),
        manifest=SkillManifest(name="skill1", description="desc1"),
        body="body1",
        resources=(),
    )
    bundle2 = SkillBundle(
        source_name="src2",
        slug="slug2",
        bundle_path=Path("/tmp"),
        manifest=SkillManifest(name="skill2", description="desc2"),
        body="body2",
        resources=(),
    )

    src1 = MockSource("src1", [bundle1])
    src2 = MockSource("src2", [bundle2])
    registry = SkillRegistry([src1, src2])
    registry.reload()

    updated_bundle1 = SkillBundle(
        source_name="src1",
        slug="slug1b",
        bundle_path=Path("/tmp"),
        manifest=SkillManifest(name="skill1b", description="desc1b"),
        body="body1b",
        resources=(),
    )
    src1.bundles = [updated_bundle1]

    registry.reload_source("src1")

    assert registry.get_bundle("skill1") is None
    assert registry.get_bundle("skill1b") is updated_bundle1
    assert registry.get_bundle("skill2") is bundle2
