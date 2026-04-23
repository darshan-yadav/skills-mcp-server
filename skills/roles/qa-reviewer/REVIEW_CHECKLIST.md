# QA Review Checklist

## 1. Scope clarity

- [ ] In-scope and out-of-scope are both written down.
- [ ] Every stated requirement maps to at least one test case or exploratory charter.
- [ ] NFRs (perf, security, a11y, i18n, compatibility) are addressed or explicitly deferred.

## 2. Risk coverage matrix

Cross-check the plan against:

- Happy path, unhappy paths, boundaries
- Roles × permissions
- State transitions (create → update → delete → restore)
- Concurrency (same entity, multiple users)
- Time (timezone, DST, stale cache)
- Compatibility (browsers / OS / device)
- Localisation (RTL, CJK, long strings)
- Accessibility (keyboard, screen reader, contrast)
- Observability (does on-call get a useful log?)
- Upgrade / migration / rollback

Any category not addressed and not explicitly deferred is a gap.

## 3. Test case quality (spot-check sample)

- [ ] Preconditions are specific (role, flag, data).
- [ ] Steps are atomic — one action per step.
- [ ] Expected result is observable by a user or operator, not internal state.
- [ ] Priority (P0–P3) is justified by business impact, not test complexity.
- [ ] Case is deterministic (no "if X then maybe Y").

## 4. Execution record

- [ ] Build / commit / environment / dataset captured per run.
- [ ] Pass / fail / blocked / not-run counts given separately.
- [ ] Flaky tests flagged and tracked — not re-run until green.
- [ ] Exploratory sessions have charters, timeboxes, and findings logged.

## 5. Defect quality

- [ ] Severity (user impact) and Priority (business urgency) are separate.
- [ ] Reproducer is reliable or explicitly "intermittent — N/M".
- [ ] Evidence attached (logs with trace ID, screenshots, network capture).
- [ ] Impact stated: who, how many, how often, workaround.
- [ ] Title describes behaviour, not a guessed root cause.

## 6. Release readiness

- [ ] All P0/P1 defects fixed or risk-accepted in writing.
- [ ] Residual risk section exists and is specific.
- [ ] Rollback rehearsed.
- [ ] Runbook / known-limitations updated.
- [ ] Go / no-go / conditional-go recommendation, with conditions named.

## 7. Automation / manual balance

- [ ] Anything run manually more than twice is a candidate for automation — called out.
- [ ] Automation gaps feeding "manual regression forever" are flagged to SDET.

## Comment style

- Coverage gaps first — they're the highest-leverage finding.
- Concrete examples, not abstract concerns ("case TC-042 tests happy path only; add a failure-path variant").
- Severity on every comment: **blocker**, **non-blocker**, **nit**.
- Praise at least one thing.
