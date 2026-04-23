# QA Reference

## Risk categories to probe on every feature

- **Happy path** — the demo script.
- **Unhappy paths** — invalid input, missing permissions, expired sessions, network failure, partial failure of a downstream.
- **Boundaries** — empty, one, many, max, limit +1, unicode/emoji, very long strings.
- **State transitions** — what happens if the user reloads mid-flow? Closes the tab? Opens two tabs?
- **Roles & permissions** — each role × each action. Privilege escalation attempts.
- **Data lifecycle** — create → update → delete → restore → export → import.
- **Time** — timezone boundaries, DST, leap day, clock skew, stale caches.
- **Concurrency** — two users editing the same entity; a retry firing twice.
- **Compatibility** — supported browsers / OS / device classes / screen sizes.
- **Localisation** — RTL, CJK, pluralisation, date/number formats.
- **Accessibility** — keyboard-only, screen reader, contrast, focus order.
- **Observability** — does the user see a useful error? Does the on-call get a useful log?

## Test case anatomy

Each test case has:

- **ID** — stable, e.g. `TC-BILLING-042`
- **Title** — what is verified
- **Priority** — P0 (blocker) → P3 (nice to have)
- **Preconditions** — data, role, flag state
- **Steps** — numbered, one action per step
- **Expected result** — observable, not internal
- **Actual result** — filled at execution
- **Environment & build** — at execution

## Exploratory charter template

```
Charter: Explore <area>
With: <tool/data/role>
To discover: <risk hypothesis>
Timebox: <duration>
```

At the end of the session, record: what you did, what you found, questions raised, follow-ups.

## Release readiness gates

- [ ] All P0/P1 defects fixed or explicitly deferred with risk sign-off.
- [ ] Regression subset green on the release build.
- [ ] Perf tests at target load meet SLO.
- [ ] Security review complete (or explicit "not required, here's why").
- [ ] Accessibility check passes on primary flows.
- [ ] i18n check passes on at least one RTL and one CJK locale.
- [ ] Rollback rehearsed.
- [ ] Feature flag default matches rollout plan.
- [ ] Runbook updated.
- [ ] Known limitations documented for support.

## Anti-patterns

- "Smoke test only" as release sign-off for a risky area.
- Test plans that repeat the requirements verbatim without risk analysis.
- Bugs marked "Cannot Reproduce" without recording what was tried.
- 100% case pass rate with no exploratory time spent.
- Automation gaps filled with "manual regression forever."
