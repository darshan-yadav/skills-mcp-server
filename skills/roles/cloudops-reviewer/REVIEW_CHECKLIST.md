# CloudOps Review Checklist

## 1. SLIs / SLOs

- [ ] SLIs user-observable (not just "CPU").
- [ ] 3 SLIs per user-facing service minimum (availability, latency, quality).
- [ ] SLOs have number + window.
- [ ] Error budget defined and visible.
- [ ] Burn-rate alerts: fast (page) + slow (ticket).

## 2. Alert set

- [ ] Each alert has: severity, owner team, runbook link, SLA (ack / resolve).
- [ ] Pages only on user-visible symptoms.
- [ ] Tickets on causes that aren't user-visible yet.
- [ ] No alerts on raw cause-metrics (CPU/disk/mem alone) without correlation to symptoms.
- [ ] Noise rate tracked; target < 20% of pages.
- [ ] Silencing has an expiry and an owner.

## 3. Runbooks

- [ ] Last-reviewed within the team's cadence.
- [ ] First 3 actions explicit.
- [ ] Dashboards + log queries linked.
- [ ] Escalation path defined with names / rotations.
- [ ] Communication templates for user-visible incidents.

## 4. On-call

- [ ] Rotation fair, with follow-the-sun where needed.
- [ ] Primary + secondary + escalation tiers.
- [ ] Handoff ritual exists and is logged.
- [ ] Page load tracked per rotation; outliers investigated.

## 5. Recovery drills

- [ ] Backup restore exercised (on cadence).
- [ ] AZ / region failover rehearsed.
- [ ] Rollback rehearsed.
- [ ] Secret rotation tested.
- [ ] Chaos / game days with hypotheses, not just "we turned things off."

## 6. Capacity

- [ ] Utilisation targets set.
- [ ] Scale-up + scale-down policies documented.
- [ ] Load-shedding strategy defined.
- [ ] Cold-start behaviour acceptable for p99.
- [ ] Forecast against seasonality / known events.

## 7. Cost

- [ ] Per-service attribution.
- [ ] Owner per service.
- [ ] $/unit-of-value tracked, not just total.
- [ ] Idle / non-prod shutdowns automated.
- [ ] Egress understood and monitored.

## 8. Postmortem quality

- [ ] Blameless throughout.
- [ ] Fact timeline first; analysis second.
- [ ] Impact quantified.
- [ ] Contributing factors (plural), not a single "root cause."
- [ ] Action items: SMART, owned by name, due-dated, tracked.
- [ ] Broader-org lessons section present.

## 9. Observability hygiene

- [ ] Trace / request IDs in logs.
- [ ] No PII / secrets in logs.
- [ ] Metric cardinality under control.
- [ ] Retention policies match compliance + budget.
- [ ] Dashboards have owners and review cadence.

## Comment style

- Lead with signal / noise risk or recovery-readiness gap.
- Concrete: name the alert / runbook / service.
- Severity on every comment: **blocker**, **non-blocker**, **nit**.
- Praise at least one thing.
