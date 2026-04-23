# Architect Reference

## Non-functional requirements (put numbers on all of them)

- **Latency** — p50 / p95 / p99 per key operation.
- **Throughput** — requests/sec or events/sec at peak and average.
- **Availability** — target uptime (e.g. 99.9% monthly) and error budget.
- **Durability** — probability of data loss per object-year.
- **RPO / RTO** — how much data can we lose / how fast must we recover.
- **Scalability** — horizontal/vertical headroom for 3x and 10x.
- **Consistency** — strong / causal / eventual, per data domain.
- **Security** — data classification, threat model summary, attack surface.
- **Compliance** — regulations (GDPR, DPDP, HIPAA, PCI, SOC 2) and implications.
- **Cost** — $/month at target load, $/unit of value (e.g. $/MAU).
- **Operability** — who operates it, at what hours, with what runbook.

## Trade-off frames

- **Build vs. buy vs. borrow** — managed service vs. OSS vs. write our own.
- **Sync vs. async** — request/response vs. queue/event.
- **Push vs. pull** — who initiates state transfer.
- **Stateful vs. stateless** — where does memory live.
- **SQL vs. NoSQL vs. search vs. cache** — access patterns drive storage.
- **Monorepo vs. polyrepo** — team autonomy vs. shared tooling.
- **Strong vs. eventual consistency** — correctness vs. availability vs. latency.
- **Multi-tenant vs. single-tenant** — cost vs. blast radius vs. compliance.

## Failure-mode analysis

For each external dependency and each component, ask:

- What happens if it's slow?
- What happens if it's down?
- What happens if it returns wrong data?
- What happens if it returns stale data?
- What happens if we retry? Is the operation idempotent?
- What happens at 10x load?
- What happens at 0.1x load (cold start)?
- What happens if the network partitions between us and it?

## Security boundaries

- [ ] Every trust boundary identified (user ↔ edge, edge ↔ service, service ↔ service, service ↔ data).
- [ ] AuthN mechanism per boundary.
- [ ] AuthZ mechanism per boundary.
- [ ] Data classification per flow (public / internal / confidential / restricted).
- [ ] Encryption in transit + at rest per flow.
- [ ] Secret management scheme named.
- [ ] PII / regulated data stays within compliant zones.
- [ ] Audit logging for privileged actions.

## Data design

- [ ] Entity ownership (which service is source of truth for each entity).
- [ ] Read patterns and write patterns listed; schema serves the dominant ones.
- [ ] Access paths indexed; hot keys considered.
- [ ] Retention and deletion policy per data class.
- [ ] Backups and restore drill cadence.
- [ ] Schema evolution strategy.

## Rollout shape

- Dark launch → internal → canary (1%) → ramp (10/25/50/100).
- Feature flag per reversible axis.
- Migration: dual-write → backfill → read-switch → cleanup.
- Rollback plan that does not depend on the rollout succeeding.
- Success criteria per phase, measured, not vibes.

## Anti-patterns

- NFRs written as adjectives, not numbers.
- Diagrams with no failure modes.
- A single "happy path" architecture with no rollback story.
- "We'll shard later" without a plan for how.
- "We'll make it async later" with a sync DB call in a tight loop.
- New service per feature.
- Shared databases across services with no ownership.
- Secrets in config files, even "just for dev".
- Ignoring the "do nothing" option.
