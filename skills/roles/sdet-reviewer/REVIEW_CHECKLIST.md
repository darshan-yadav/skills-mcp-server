# SDET Review Checklist

## 1. Layer placement

- [ ] Unit logic tested at unit level, not via API or UI.
- [ ] Integration tests cross exactly one real boundary per test.
- [ ] Contract tests cover wire format between consumer and provider.
- [ ] e2e tests limited to user-critical flows.
- [ ] No UI test doing work a unit test could do.

## 2. Determinism

- [ ] Clock is frozen or injected.
- [ ] Randomness is seeded and seed logged.
- [ ] External services stubbed or containerised; no real third-party calls.
- [ ] Test data isolated per test (unique tenant / namespace / prefix).
- [ ] Parallel-safe (verify by running `-p auto` or equivalent).
- [ ] Test order independence verified.

## 3. Reliability

- [ ] No `sleep()` — all waits are explicit polls on an observable condition with a timeout.
- [ ] No conditional skip based on environment unless documented.
- [ ] Teardown runs even on failure.
- [ ] Fixtures reset between tests.
- [ ] Flake rate monitored (per-test).

## 4. Meaning

- [ ] Each test asserts user- or contract-observable behaviour.
- [ ] No assertion on private / internal structure unless explicitly testing an invariant.
- [ ] Test name describes the behaviour, not the code path.
- [ ] Arrange/Act/Assert separation is visible.
- [ ] One concept per test.

## 5. Failure quality

- [ ] On failure, the message says what broke, not "expected true was false".
- [ ] Artefacts captured on failure: logs, screenshot, video, HAR, trace.
- [ ] Artefacts contain no secrets or full PII.
- [ ] Retention policy for artefacts set.

## 6. CI wiring

- [ ] Tests run on every PR at the right stage.
- [ ] Parallelism tuned to feedback SLO (<15 min PR gate is a common target).
- [ ] No auto-retry-until-green.
- [ ] Flake rate reported and enforced.
- [ ] Test selection (affected-only) pursued where possible.
- [ ] Perf / chaos on schedule, not per-PR, with explicit SLO gates.

## 7. Maintainability

- [ ] No giant shared utility that hides what the test is doing.
- [ ] No deep inheritance chains across test classes.
- [ ] Helpers test-only; no prod code leaking into the test path.
- [ ] A new team member could add the next test by copying one of these.

## 8. Coverage — honest signal

- [ ] Behaviour / branch coverage stated, not just line coverage.
- [ ] Untested branches are explicitly acknowledged.
- [ ] Mutation or fault-injection used where affordable.

## Comment style

- Lead with the reliability concern; it's usually the biggest one.
- Name the flake mode (timing / ordering / shared state / external).
- Severity on every comment: **blocker**, **non-blocker**, **nit**.
- Praise at least one thing.
