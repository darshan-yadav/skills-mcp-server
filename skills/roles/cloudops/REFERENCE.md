# CloudOps / SRE Reference

## SLIs → SLOs → error budget

- **SLI**: what we measure (e.g. fraction of API requests returning < 500ms with a 2xx).
- **SLO**: target for that SLI over a window (e.g. 99.9% over 30 rolling days).
- **Error budget**: 1 − SLO, translated to downtime / bad requests per window.
- **Burn-rate alerts**: fast alert (2% budget in 1 hour) + slow alert (10% in 6 hours). Page on fast, ticket on slow.

Rule of thumb:

- Start with 3 SLIs per user-facing service: availability, latency, quality (correctness / freshness).
- SLOs are set from what the user needs, not what the system currently does.
- If the SLO is already broken 10 days a month, it's the target that's wrong or the system that's wrong — decide which, don't drift.

## Signals stack

- **Metrics** — low-cardinality, time-series. "How much / how fast / is it OK right now?"
- **Logs** — high-cardinality events. "What exactly happened on this request?"
- **Traces** — distributed span graphs. "Where did time go, which service was at fault?"
- **Events** — discrete state changes (deploy, flag flip, config change). "What *changed* right before the graph bent?"

Each carries trace/request IDs. Retention:
- Metrics: months (aggregated).
- Logs: days-to-weeks; longer for audit.
- Traces: days, sampled.
- Events: months.

## Alerting principles

- **Page on user-visible symptoms.** High error rate, latency SLO burn, freshness stalled.
- **Ticket on causes that aren't user-visible yet.** Disk at 80%, cache hit ratio dropped.
- **Log-only on noise.** Routine things that don't need action.
- Every page has: owner, runbook link, severity, time-to-acknowledge SLO.
- Noise > 20% of pages means the alert is wrong, not the responder.

## Incident response

Roles:
- **Incident Commander** — decides and communicates; does not fix.
- **Ops** — mitigates and fixes.
- **Comms** — external updates, status page.
- **Scribe** — timeline.

Process:
1. Declare. Severity class (SEV1/2/3). Open a channel.
2. Mitigate first — roll back, flag off, drain traffic, scale out.
3. Communicate in known cadence (every 15/30 min for SEV1/2).
4. Resolve when user impact is gone.
5. Postmortem within the postmortem SLA.

## Postmortem rules

- Blameless. Talk about systems, not people.
- Fact timeline first, then analysis.
- Contributing factors, not root cause — there usually isn't just one.
- Action items: SMART, owned by name, due-dated, tracked to closure.
- Share across the org; the blast radius of learning should exceed the blast radius of the incident.

## Capacity & scale

- Steady-state utilisation target: 40–60% of headroom for most services.
- Scale policy: horizontal before vertical; scale up fast, scale down slow.
- Load shedding: degrade gracefully under overload (prioritise critical traffic).
- Cold-start behaviour: warm pools or provisioned concurrency where p99 matters.

## Cost levers

- **Right-size** — actuals vs. requests/limits.
- **Right-shape** — spot / preemptible where tolerable; reserved / savings plans for steady.
- **Storage tiers** — lifecycle to cheaper tiers; expiry on logs and metrics.
- **Egress** — watch cross-AZ / cross-region / internet egress charges.
- **Idle** — automated shutdowns for non-prod.
- **Per-tenant attribution** — necessary for any multi-tenant cost conversation.

## Reliability drills to schedule

- Backup restore (quarterly).
- AZ failover (quarterly).
- Region failover (biannual).
- Secret rotation (per policy).
- Game days / chaos experiments with hypotheses.

## Anti-patterns

- Paging on CPU, disk, or memory alone — these are causes, not symptoms.
- Alerts with no owner, or owned by a channel.
- Runbooks that are last updated two years ago.
- "We know our SLO by feel."
- Dashboards with 40 panels and no owner.
- Postmortems assigning action items to "the team" with no name and no date.
- Cost dashboards at total-level only with no per-service attribution.
- Backups never restored.
