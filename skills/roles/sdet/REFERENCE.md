# SDET Reference

## Test pyramid (rough shape, not gospel)

- **Unit** — pure logic, no I/O. Fast (<100ms each), deterministic. 70%+ of cases live here.
- **Integration** — component + real dependency (DB, cache, queue) via container/fake. Slower but still seconds.
- **Contract** — consumer and provider pacts that catch wire-format drift without a full e2e.
- **API / service** — the service over its real transport. Deterministic data, no shared state.
- **End-to-end / UI** — user-critical paths only. Expensive; cap the count.
- **Performance** — explicit SLO per scenario (p95, throughput, resource use).
- **Chaos / resilience** — failure injection with explicit hypotheses and stop conditions.

Rule of thumb: if you can push a test down a level without losing signal, push it.

## Framework selection

- Match the language ecosystem first (pytest for Python, JUnit/Testcontainers for JVM, vitest/jest for TS, Go testing, xUnit for .NET).
- Prefer frameworks that run the *same* test locally and in CI.
- Browser automation: Playwright over Selenium in new code; keep one (not both).
- API: use the real HTTP client your service uses, not a special test client unless unavoidable.
- Contract: Pact or equivalent; keep the broker versioned.
- Perf: k6 / Locust / Gatling. Treat scripts as code (reviewed, in repo).
- Chaos: start with network faults, latency, and process kills. Don't skip the hypothesis.

## Reliability checklist

- [ ] No sleeps — poll with timeout on an observable condition.
- [ ] Clock frozen or injected.
- [ ] Randomness seeded and logged.
- [ ] External services stubbed deterministically, with contract tests covering the real wire format.
- [ ] Test data isolated per test (unique tenant / namespace / prefix).
- [ ] Parallel-safe (no shared fixture that leaks).
- [ ] Teardown runs even when the test fails.
- [ ] No conditional skips based on "if CI" unless documented.

## Flake triage

A flake is a bug. Triage order:

1. Reproduce locally with the same seed / env as CI.
2. Suspect timing first, then ordering, then shared state, then external calls.
3. If you can't reproduce within a reasonable time, **quarantine with an expiry date and an owner** — don't leave it running and unreliable.

## CI wiring

- [ ] Stages: lint → unit → build → integration → contract → e2e → perf (perf usually on a schedule, not per-PR).
- [ ] Parallelism tuned to keep the PR gate under the team's feedback SLO (10–15 min is a common ceiling).
- [ ] Failure artefacts captured: logs, screenshots, video, HAR, traces — with retention policy.
- [ ] Flake rate reported and tracked; PRs tagged if they increase it.
- [ ] Test selection (only run affected tests on PR) is a goal, not a blocker.

## Coverage — what it means, what it doesn't

- Line coverage is a **smoke detector**, not a scoreboard.
- Measure behaviour coverage: list the branches and invariants; confirm each is asserted.
- Mutation testing is the honest signal where you can afford it (even a targeted subset helps).

## Anti-patterns

- "Page Object" layers that leak internal DOM structure to tests.
- UI tests used to cover business logic.
- `sleep(5)` after a click.
- Shared test database without per-test isolation.
- Assertions on log output instead of observable behaviour.
- "Flaky, re-run 3x" CI retry step.
- Snapshots committed without review.
- Giant "all tests" job with no feedback before it completes.
- Perf tests whose results are "looks fine" rather than pass/fail vs. SLO.
