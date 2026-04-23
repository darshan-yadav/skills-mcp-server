# Project Manager Reference

## Milestones (definition of done, not activity)

- Bad: "Design review."
- Good: "Design reviewed and approved by <DACI Approver>; linked ADR merged."
- Bad: "Build the API."
- Good: "API deployed to stage; smoke tests green; consumers pointed at stage endpoint."

If a milestone can't be demonstrated, it isn't one.

## Estimation discipline

- Ask each owner for best / expected / worst.
- Sum **expected** for the plan. Track **worst** as the risk-adjusted date.
- If best ≈ worst, the owner is either hiding uncertainty or not thinking hard enough.
- Re-estimate the tail (next 2 milestones) every cycle. Long-range estimates decay fast.

## Critical path

- The path with the least slack is the one you manage most closely.
- If something on the critical path slips a day, the end slips a day.
- Off-critical-path slips are still real — they eat into buffer and can promote items onto the critical path.

## RACI (one per milestone)

- **R**esponsible — does the work.
- **A**ccountable — answers for the outcome. One person.
- **C**onsulted — input required before decision.
- **I**nformed — told after the decision.

Anti-patterns: more than one A, A is "the team", C lists half the company.

## Risk register (what a good row looks like)

| ID | Description | Likelihood | Impact | Trigger | Mitigation | Owner | Status |
|----|-------------|------------|--------|---------|------------|-------|--------|
| R1 | Third-party auth provider rate limits our bulk import in v1 | M | H | >2k users / minute during onboarding | Negotiate temporary quota; implement client-side backoff; fallback to queued import | D. Yadav | Open |

A description alone is not a risk entry — without a trigger and a mitigation owner, it's a worry.

## Status reporting — RAG with evidence

- **Green** — on track; evidence: completed milestones this week, next milestone on date, no open blockers.
- **Amber** — at risk; evidence: named blocker, named mitigation, date not yet slipped.
- **Red** — off track; evidence: date has slipped or scope has been cut.

Rules:
- You don't get to be green without data.
- Amber means you need something — name it (decision, person, resource).
- Red is followed by a specific recovery plan, not "we'll work harder."

## Change control

- Every change to scope / schedule / owners is a logged event.
- It names: what changed, why, who decided, what compensated (scope cut? date moved? resources added?).
- Unlogged changes breed status fiction later.

## Meeting discipline

- Every recurring meeting has a death-condition ("if X, we cancel this meeting").
- Status goes in writing before the meeting; meeting is for decisions and blockers.
- Round-robin updates are a smell — replace with asynchronous status and meet on decisions.

## Dependencies across teams

- "They'll do it for us" without a dated commitment is not a plan.
- Capture dependency asks in the other team's system of record, not just your own doc.
- Re-confirm at each planning horizon — priorities shift.

## Launch readiness (cross-functional)

- Engineering — code complete, QA sign-off, rollback rehearsed.
- QA — regression + targeted coverage, release notes reviewed.
- SRE / Ops — runbooks, alerts, capacity, on-call aware.
- Support — macros, FAQ, severity routing, training.
- Legal / compliance — review complete.
- Comms — internal + external, docs, status page updated.
- GTM / commercial — pricing, packaging, sales enablement.
- Product — metrics wired, dashboard owned.

See `LAUNCH_CHECKLIST.md`.

## Close-out

- What was in the plan? What actually happened? Where's the delta?
- Estimates vs. actuals per milestone — feed into future estimation.
- Risks that fired: did the mitigation work?
- Risks that didn't fire: lucky, or well-managed?
- Actions for the next project, owned and dated.

## Anti-patterns

- Gantt charts with no owners.
- Single-point estimates.
- "Green" status week after week, then sudden "red."
- Risk register that hasn't been updated in a month.
- Scope changes absorbed silently by the team working overtime.
- Status meetings that are round-robin updates.
- Launch readiness reduced to "QA signed off."
- Closing the project without a retro.
- Project plans that live in a tool nobody opens.
