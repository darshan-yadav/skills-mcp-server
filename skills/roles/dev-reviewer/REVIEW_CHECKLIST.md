# Code Review Checklist

Use as a filter, not a script. If a section isn't relevant to the diff, skip it.

## 0. Is this reviewable at all?

- [ ] PR has a description that states intent and links a ticket.
- [ ] Diff is under ~500 lines of substantive change, or clearly justified.
- [ ] Change is one logical unit (not feature + unrelated refactor + dep bump).
- [ ] Tests, code, and docs moved together.

If any of these fail, the comment is "please split this PR" — not a line-level review.

## 1. Correctness

- [ ] The code does what the PR description says.
- [ ] Edge cases: empty, null, max, concurrent, retried, partial failure.
- [ ] Off-by-one, boundary, timezone, locale, encoding bugs.
- [ ] Async/await, promise chains, and futures correctly awaited.
- [ ] Error paths return or raise — never silently fall through.

## 2. Security & data

- [ ] AuthN + AuthZ on every new entry point.
- [ ] Input validation at the boundary; no trust in upstream services.
- [ ] No SQL/shell/HTML/log injection via string interpolation.
- [ ] Secrets live in a secret store, not in code, env defaults, or tests.
- [ ] PII not logged or emitted as a metric label.
- [ ] Dependencies: new libs checked for maintenance, license, known CVEs.

## 3. Concurrency & data integrity

- [ ] Shared mutable state protected; lock scope minimal.
- [ ] Transactions cover the right boundary; no dangling half-writes.
- [ ] Idempotency keys on writes that can retry.
- [ ] No race between read-then-write without a lock/CAS/version check.

## 4. Resilience

- [ ] Timeouts, retries, backoff on every remote call.
- [ ] Circuit breakers / bulkheads preserved.
- [ ] Graceful degradation if a dependency is down.
- [ ] New code does not block shutdown or health checks.

## 5. Tests

- [ ] Tests assert behaviour, not implementation detail.
- [ ] At least one failure-path test per new branch.
- [ ] Boundary cases covered.
- [ ] No shared mutable fixture that leaks between tests.
- [ ] No time/network/randomness flakiness.
- [ ] Coverage is not the metric — meaningful coverage is.

## 6. Observability

- [ ] Structured logs with trace/request IDs.
- [ ] Metrics for new failure modes, not just success counters.
- [ ] Alert thresholds considered (or explicit "no alert needed, here's why").
- [ ] Log levels used appropriately (info vs. warn vs. error).

## 7. Rollout & rollback

- [ ] Feature flag with a safe default.
- [ ] Rollback path is a revert, a flag flip, or a documented SQL — not "hope".
- [ ] Migration is backward-compatible for at least one deploy cycle.
- [ ] Change is safe to roll out progressively (canary / percentage).

## 8. Design & maintainability

- [ ] Names describe intent.
- [ ] Layering respected (no domain logic leaking into controllers, etc.).
- [ ] No premature abstraction; no duplication that will drift.
- [ ] Public surface area justified — every new export is a commitment.

## Comment style

- Lead with the problem, not the solution.
- One comment per concern; don't stack unrelated issues.
- Mark severity explicitly: **blocker**, **non-blocker**, **nit**.
- If you'd need to think more than 30 seconds to suggest a fix, ask a question instead of proposing code.
- Praise at least one thing. Reviews are a two-way relationship.
