# Developer Reference

Detailed checklist and anti-patterns for the `dev` skill.

## Pre-code checklist

- [ ] Requirement restated in one sentence; unknowns surfaced.
- [ ] Acceptance criteria understood (what does "done" look like?).
- [ ] Existing feature flag / experimentation framework identified.
- [ ] Owner of the touched module/service identified for reviewer routing.

## Code checklist

- [ ] Names describe intent, not implementation (`hasExpired`, not `checkExpiryFlag`).
- [ ] Functions do one thing; cyclomatic complexity stays reasonable.
- [ ] No dead code, commented-out blocks, or "TODO: fix later" without a ticket link.
- [ ] Null/empty/error paths handled explicitly.
- [ ] Input validation at trust boundaries (HTTP, queue, CLI, SDK surface).
- [ ] Timeouts, retries, and backoff on every remote call.
- [ ] Idempotency for anything that writes.
- [ ] No blocking I/O in async paths; no CPU-heavy work on request threads.
- [ ] Lock ordering / transaction scope is explicit and minimal.
- [ ] Pagination / streaming for anything that could return unbounded data.

## Data & migrations

- [ ] Schema changes are backward-compatible or gated behind a flag.
- [ ] Destructive migrations have a documented rollback procedure.
- [ ] Read path tolerates both old and new shapes during the rollout window.
- [ ] Indexes added/dropped with explicit justification.
- [ ] PII / sensitive fields are classified; encryption-at-rest confirmed.

## Security

- [ ] No secrets in code, tests, or logs.
- [ ] AuthN + AuthZ checked on every new entry point.
- [ ] User-controlled input never interpolated into SQL, shell, HTML, log format strings.
- [ ] Dependencies pinned; no new transitive dependency introduced without a look at its maintainer/LICENSE/CVE history.
- [ ] CSRF, SSRF, IDOR considered where relevant.

## Observability

- [ ] Structured logs include request/trace IDs.
- [ ] Metrics emitted for new failure modes, not just success paths.
- [ ] Error messages are actionable for an on-call engineer who's never seen the code.
- [ ] No log lines contain secrets, full request bodies, or PII.

## Tests

- [ ] Happy-path test.
- [ ] At least one failure-path test per new branch.
- [ ] Boundary tests (empty, one, many, max).
- [ ] Concurrency / race cases for shared state.
- [ ] Fixtures reset cleanly; no test depends on another test's order.
- [ ] Flakiness risk assessed (time, network, randomness, parallelism).

## Anti-patterns (reject on sight)

- Catching `Exception` / `Throwable` and swallowing.
- Copy-pasted code blocks that differ in one constant — factor them.
- "God" PRs mixing refactor + feature + dependency bump.
- New config knobs without a documented default and blast-radius note.
- `sleep()` in production code paths to work around a race.
- Tests that assert on log output instead of behaviour.
- Feature flags with no removal plan.

## Repo conventions to confirm before committing

- Linter / formatter (ruff, prettier, gofmt, ktlint…) configuration respected.
- Commit message convention (Conventional Commits, ticket prefixes).
- Branch naming convention.
- PR size and review SLA expectations.
