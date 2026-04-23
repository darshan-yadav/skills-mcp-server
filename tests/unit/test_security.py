import pytest
from pathlib import Path
from skills_mcp_server.sources.local import _list_bundle_resources

def test_symlink_traversal_bundle_escape(tmp_path):
    root = tmp_path / "skills"
    root.mkdir()
    
    secret = tmp_path / "secret.txt"
    secret.write_text("super secret")
    
    bundle = root / "my-skill"
    bundle.mkdir()
    (bundle / "SKILL.md").write_text("name: foo\ndescription: bar\n---\nbody")
    
    escape_link = bundle / "escape.txt"
    escape_link.symlink_to(secret)
    
    valid_file = bundle / "valid.png"
    valid_file.write_text("png")
    
    resources = _list_bundle_resources(bundle)
    assert Path("escape.txt") not in resources
    assert Path("valid.png") in resources
    assert Path("SKILL.md") in resources
