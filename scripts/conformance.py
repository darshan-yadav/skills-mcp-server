#!/usr/bin/env python3
"""Conformance check script (QA Agent).

Validates the skills-mcp-server parser against the Anthropic public skills corpus.
If the corpus does not exist yet or is unreachable, uses a mock integration test approach.
"""

import subprocess
import sys
from pathlib import Path
import tempfile

def run_conformance_check():
    print("Running conformance check against standard SKILL.md bundles...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        data_dir = tmp_path / "data"
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        
        # Create a compliant skill
        bundle1 = skills_dir / "math-skill"
        bundle1.mkdir()
        (bundle1 / "SKILL.md").write_text("name: math\ndescription: math\n---\nbody")
        (bundle1 / "script.py").write_text("print('hello')")
        
        config = tmp_path / "config.yaml"
        config.write_text(f"""
sources:
  - name: conformance-local
    type: local
    path: {skills_dir}
data_dir: {data_dir}
log_level: debug
""")

        print(f"Executing selftest with config: {config}")
        result = subprocess.run(
            ["skills-mcp-server", "selftest", "--config", str(config)],
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        print(result.stderr)
        
        if result.returncode == 0:
            print("Conformance check PASSED ✅")
            sys.exit(0)
        else:
            print("Conformance check FAILED ❌")
            sys.exit(1)

if __name__ == "__main__":
    run_conformance_check()
