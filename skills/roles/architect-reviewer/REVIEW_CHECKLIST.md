# Architecture Review Checklist

## 1. Problem & success

- [ ] Problem statement is specific, not aspirational.
- [ ] One primary success metric is named and measurable.
- [ ] Scope and non-scope are written down.

## 2. NFRs (all with numbers)

- [ ] Latency (p50 / p95 / p99 per operation).
- [ ] Throughput (target and peak).
- [ ] Availability (target + error budget).
- [ ] Durability / RPO / RTO.
- [ ] Consistency model per data domain.
- [ ] Security posture (threat model summary).
- [ ] Compliance requirements applicable.
- [ ] Cost ceiling.

## 3. Options

- [ ] ≥ 2 real options considered.
- [ ] "Do nothing" considered.
- [ ] Options described in comparable shapes.
- [ ] Trade-offs include cost, operability, reversibility — not just features.

## 4. Failure modes

For each external dependency / critical component:

- [ ] Slow path behaviour.
- [ ] Down path behaviour.
- [ ] Wrong-data behaviour.
- [ ] Stale-data behaviour.
- [ ] Retry semantics + idempotency.
- [ ] Network partition behaviour.
- [ ] Cold-start behaviour.

## 5. Security boundaries

- [ ] Every trust boundary named.
- [ ] AuthN + AuthZ per boundary.
- [ ] Data classification per flow.
- [ ] Encryption in transit + at rest confirmed.
- [ ] Secret management named and safe.
- [ ] PII / regulated data stays in compliant zones.
- [ ] Audit logging for privileged actions.

## 6. Data

- [ ] Entity ownership named (one service = source of truth per entity).
- [ ] Access patterns drive schema.
- [ ] Hot-key / skew risk addressed.
- [ ] Retention + deletion policy per class.
- [ ] Backup + restore drill cadence.
- [ ] Schema evolution strategy.

## 7. Rollout & rollback

- [ ] Phased rollout (dark → internal → canary → ramp).
- [ ] Feature flag per reversible axis.
- [ ] Migration plan (dual-write → backfill → read-switch → cleanup) if data changes.
- [ ] Rollback plan is independent of the rollout succeeding.
- [ ] Per-phase success criteria, measurable.

## 8. Reversibility

- [ ] One-way-door decisions explicitly flagged.
- [ ] Plan B exists for the highest-risk one-way doors.

## 9. Operability

- [ ] Who operates it, on what hours.
- [ ] Runbook location named.
- [ ] SLO + alerting strategy named.
- [ ] Cost model plausible at target load.

## 10. Honesty checks

- [ ] "What would change our mind" section exists and is specific.
- [ ] Risks are listed, not hidden.
- [ ] Assumptions are flagged as assumptions.
- [ ] No "TBD" on a decision that blocks the build.

## Comment style

- Name the assumption or gap, not the feeling.
- Quantify the concern where possible ("at 10x load, this queue depth will…").
- Severity on every comment: **blocker**, **non-blocker**, **nit**.
- Praise at least one thing.
