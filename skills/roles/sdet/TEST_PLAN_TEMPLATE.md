# Test Automation Plan

## System under test
- Service / feature:
- Boundaries & contracts:
- Invariants to preserve:

## Pyramid
| Level       | Count (rough) | Framework | Runs on      | SLO (runtime) |
|-------------|---------------|-----------|--------------|---------------|
| Unit        |               |           | every commit |               |
| Integration |               |           | every PR     |               |
| Contract    |               |           | every PR     |               |
| API / e2e   |               |           | every PR / nightly |         |
| Perf        |               |           | nightly / release |          |
| Chaos       |               |           | scheduled    |               |

## Determinism plan
- Clock:
- Randomness seed:
- External services (stub / contract-tested):
- Data isolation strategy:

## CI wiring
- Stages and their gates:
- Parallelism:
- Failure artefacts + retention:
- Flake rate target and alerting:

## Ownership
- Unit + integration: team that owns the code.
- Contract: provider + consumer teams.
- e2e / UI: named owner.
- Perf / chaos: named owner.

## Suite SLOs
- PR feedback time: <=
- Flake rate: <=
- Mean-time-to-triage on failure: <=

## Open questions & owners
-
