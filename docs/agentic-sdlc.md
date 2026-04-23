# Agentic SDLC for `skills-mcp-server`

**Status:** Aspirational — role definitions and workflow are documented here as a design; live orchestration is **not yet wired up**. This document captures intent so the project can grow into it incrementally. Today, the human maintainer drives the workflow manually with AI assistance on individual tasks.

**Last updated:** 2026-04-23
**Supersedes:** `implementation_plan.md` (initial 4-role draft)

---

## Why this document exists

`skills-mcp-server` has no Jira, no dedicated PM, and a small maintainer pool. **GitHub is the central nervous system** — issues, source control, pull requests, releases, and (eventually) orchestration all run through it. The workflow below is designed around two commitments:

1. **Human approval is mandatory at two gates**: PR merge to `main`, and release-tag creation. Nothing else is a human-gate.
2. **Agents propose, humans dispose**, especially for anything that mutates the project's authoring surface. See the Architect-SPEC rule in §2.

## 1. The six agent roles

Each role is a named persona with a defined trigger, scope, and output. Any of them can be backed by Claude Code, GitHub Copilot Workspace, a custom GitHub Action invoking an LLM API, or a human — the workflow works regardless of the implementation.

### 1.1 Architect / Product Agent (The Planner)

- **Trigger:** A new issue is labeled `needs-triage` or `enhancement`.
- **Role:** System architect. Reads the issue, cross-references `SPEC.md`, ensures alignment with project goals (e.g., rejects any request that tries to add MCP-driven write capabilities — see `SPEC.md` §11.4).
- **Responsibilities:**
  - Draft a technical implementation plan as an issue comment.
  - Break down large features into smaller sub-issues with clear acceptance criteria.
  - **Propose — but never auto-apply — SPEC changes.** If an architectural change is needed, the Architect opens a `docs/` or `SPEC.md` PR for a human to review and author. The Architect never edits `SPEC.md` directly. This is a permanent rule, matching the PR-only authoring commitment in SPEC §11.4.
- **Output:** Refined GitHub issues with acceptance criteria, technical checklists, and (optionally) draft SPEC-change PRs for human review.

### 1.2 Developer Agent (The Builder)

- **Trigger:** An issue is labeled `approved-for-dev`, or `@agent /implement` appears in a comment.
- **Role:** Primary coder. Executes the plan the Architect laid out.
- **Responsibilities:**
  - Create a feature branch (`feat/<issue-id>-<short-slug>`).
  - Write implementation code.
  - Write adjacent unit tests for new public surface (integration tests are the SDET's job).
  - Open a PR against `main` referencing the issue.
- **Output:** A Pull Request with code, docstrings, and minimal unit tests.

### 1.3 SDET Agent (The Test Builder)

- **Trigger:** A PR is opened with the `needs-integration-tests` label, or an issue is labeled `sdet`.
- **Role:** Builds the test harness and writes integration tests against the public contract, including the security-critical invariants the spec calls out.
- **Responsibilities:**
  - Maintain `tests/conftest.py` and shared fixtures.
  - Write integration tests that exercise real subprocesses, real git repos (as local fixtures), real MCP client round-trips.
  - Write security regression tests: symlink traversal, subprocess timeout kills child processes, cache write escalation attempts fail, etc. These live forever — they're the enforcement mechanism behind SPEC §10 and §16.1.
- **Output:** A PR adding `tests/integration/**` or `tests/security/**`.

### 1.4 QA Agent (The Validator)

- **Trigger:** Before each release tag, or on request via `@agent /qa`.
- **Role:** Validates that the code actually does what the spec says. Distinct from the SDET (who writes tests): the QA Agent treats the system as a black box and checks acceptance criteria end-to-end.
- **Responsibilities:**
  - Run the conformance check against the public Anthropic skills corpus (SPEC §19.3) — load the corpus, verify how many skills parse cleanly, report deviations.
  - Walk through the SPEC §14 usage walkthroughs manually or scripted and verify each one actually works on the built image.
  - File bug issues for any gap between spec and behavior.
- **Output:** A release-readiness report comment on the release PR/tag, with a pass/fail per SPEC §14 walkthrough and per conformance target.

### 1.5 Reviewer / Security Agent (The Gatekeeper)

- **Trigger:** A PR is opened or updated.
- **Role:** Automated code review + security audit.
- **Responsibilities:**
  - Review for anti-patterns, perf regressions, and SPEC adherence (especially §10 security invariants — `os.path.realpath` for resource resolution, subprocess process-group reaping, cache write protection).
  - Leave inline PR comments.
  - Approve / Request Changes.
- **Rate-limit rule:** The Developer Agent may auto-push fixes in response to Reviewer comments **up to 3 rounds**. After 3 rounds of disagreement, the loop escalates to a human maintainer. This caps the infinite-bikeshed failure mode.
- **Output:** PR review states.

### 1.6 DevOps / Release Agent (The Publisher)

- **Trigger:** A merge to `main` (builds `:edge`); a tag push like `v0.1.0` (builds release artifacts).
- **Role:** Automates the CI/CD pipeline. Implemented as GitHub Actions in `.github/workflows/ci.yml` — no separate LLM needed for this role; it is deterministic plumbing.
- **Responsibilities:**
  - Run the full test suite (`pytest`, `ruff`, `skills-mcp-server --selftest` once that command exists).
  - Build the multi-arch OCI image, push to GHCR.
  - Publish PyPI packages on tag (trusted publishing).
  - Generate release notes from merged PRs.
- **Output:** Published Docker images, PyPI releases, GitHub Release notes.

---

## 2. The GitHub-native workflow

### Phase 1 — Ideation & planning
1. A human opens a GitHub issue (bug or feature) using the issue template.
2. The **Architect Agent** comments with a proposed technical design, checked against SPEC.
3. A human labels `approved-for-dev` if the plan is sound. SPEC-impacting proposals get a draft PR for human authoring first; no auto-merge.

### Phase 2 — Implementation
4. The **Developer Agent** picks up `approved-for-dev`, branches, writes code + unit tests, opens a PR.
5. In parallel, if the change needs integration/security coverage, the **SDET Agent** is triggered and opens its own complementary PR (or adds tests to the Developer's PR, depending on PR size).

### Phase 3 — Review & refinement
6. The **Reviewer Agent** runs on PR open/update and leaves feedback.
7. The Developer Agent may auto-push fixes — bounded at 3 rounds before escalation to a human.
8. **Human gate.** A maintainer reviews the PR and merges.

### Phase 4 — Validation & release
9. Merge to `main` triggers the **DevOps Agent** → builds `:edge` image.
10. Before a release, the **QA Agent** runs and posts its readiness report.
11. A human cuts a semver tag (e.g. `v0.1.0`). The **DevOps Agent** publishes the Docker tag + PyPI release.

---

## 3. What's live today vs. what's aspirational

| Component | Status |
|---|---|
| Issue templates (feature, bug) | **Live** — `.github/ISSUE_TEMPLATE/` |
| CI pipeline (lint + test + build + publish) | **Live (skeleton)** — `.github/workflows/ci.yml`; real commands as of T03 |
| Human gates (PR merge, release tag) | **Live** — GitHub-native |
| Architect Agent | **Aspirational** — maintainer does this manually today |
| Developer Agent (autonomous issue → PR) | **Aspirational** — maintainer drives Claude Code per task today |
| SDET Agent | **Aspirational** — same |
| QA Agent | **Aspirational** — manual conformance check on release |
| Reviewer Agent | **Aspirational** — maintainer reviews PRs today |

Each agent graduates from "aspirational" to "live" when:
- There is a clear trigger GitHub Action implementation, or
- The maintainer has enough confidence in the role's output quality to hand it the trigger.

Don't turn on autonomous triggers before v0.1 ships. The manual loop teaches what the agents need to be good at.

---

## 4. Open design questions

1. **Authentication / cost controls for autonomous agents.** If Architect / Developer / Reviewer agents are implemented as GitHub Actions invoking an LLM API, how is the API key scoped and budgeted? A runaway loop could burn significant spend before the 3-round Reviewer cap fires. Leaning towards a hard per-workflow spend cap via the LLM provider's budget feature.
2. **Which agent framework?** Claude Code in background mode, Copilot Workspace, SWE-agent, a custom harness — each has tradeoffs. Defer the decision until after v0.1 ships and we've seen where autonomy actually pays off.
3. **Branch protection rules.** `main` should require: 1 human approving review, CI green, up-to-date branch, no direct pushes. Configure via GitHub branch protection before turning on any autonomous Developer Agent.

---

*This document is the contract between human maintainers and the agent-assisted development model. Changes are via PR.*
