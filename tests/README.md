# skills-mcp-server test harness

Wave 1 (T02) establishes fixtures only — no assertions live here yet.

Layout:
- `conftest.py` — shared fixtures: `tmp_config_dir`, `local_sample_skills_dir`, `git_repo_factory`, and the `sample_skill_md` helper.
- `fixtures/skills/local-sample/` — checked-in skill bundles used as a `local` source.
  - `hello-world/` — minimum valid skill (SPEC §6.3): `name` + `description` only.
  - `summarize-text/` — fuller bundle with optional frontmatter and a `reference.md` (SPEC §6.1, §6.2).
  - `broken-skill/` — intentionally invalid (missing `description`) for validation tests.

Wave 2+ SDET agents should add `test_*.py` modules alongside this README and import the fixtures above. Prefer `git_repo_factory` over network fetches when exercising the git source loader. When a new fixture file is needed by multiple test modules, add it under `fixtures/` and expose it through a fixture in `conftest.py` rather than hardcoding paths in individual tests.
