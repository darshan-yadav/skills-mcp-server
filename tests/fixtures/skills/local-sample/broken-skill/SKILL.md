---
name: broken-skill
version: 0.0.1
tags: [invalid, fixture]
---

# Broken skill (intentionally invalid)

This SKILL.md is missing the required `description` frontmatter field per
SPEC §6.1. Wave 2+ validation tests use it to assert that the loader
rejects the bundle with a clear error rather than silently registering a
description-less prompt.

Do not "fix" this file — the missing field is load-bearing.
