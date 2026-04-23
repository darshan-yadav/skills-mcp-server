# Product Manager Reference

## Framing the user problem

- **Who exactly?** Persona or segment with numbers (how many, which cohort).
- **What can't they do?** In their language. If you use internal jargon, you haven't listened enough.
- **How often?** Rare, occasional, daily pain.
- **What's the workaround today?** If there's no workaround, revisit whether the problem is real.
- **What's the cost of the problem?** Time, revenue, risk, churn.
- **Why now?** What changed that makes this the right time.

## Jobs-to-be-done template

> When **<situation>**, I want to **<motivation>**, so I can **<outcome>**.

Test: swap in your feature — does it *directly* enable the motivation and the outcome? If not, either the JTBD or the feature is wrong.

## Metric hygiene

- **North-star / primary** — one metric that captures delivered user value.
- **Input metrics** — things you can move that move the primary.
- **Guardrails** — must-not-regress (latency, support volume, cost per action, NPS, error rate, fairness).
- **Counter-metric** — directly checks the flip side of the primary (e.g., engagement + retention as a pair).

Rules:
- Every metric has a definition, a source, and a window.
- "Growth" is not a metric. "MAU in segment X over 28 days" is.
- Proxy metrics are OK if labelled as such.
- If you can't measure it, you're making a promise you can't keep.

## Prioritisation frameworks (tools, not oracles)

- **RICE** = Reach × Impact × Confidence / Effort. Good default.
- **WSJF** = Cost of Delay / Job Size. Better when delay cost is heterogeneous.
- **ICE** = Impact × Confidence × Effort. Quick triage, easily gamed.
- **Kano** = basic / performance / delight. Good for segmentation of *types* of feature, not ordering.
- **Opportunity score** = importance − satisfaction. Good for discovery phase.

Whichever framework:
- Declare weights up front.
- Show what loses and why.
- Recompute when the world changes.

## PRD discipline

- Keep it short — if it's >5 pages, you're probably over-specifying the *how*.
- Link, don't duplicate.
- Separate *what* from *how*. "How" is engineering's turf.
- Every "nice to have" moves to "not now" or gets cut.
- Assumptions flagged explicitly, not buried in prose.

## Launch criteria (write these with the cross-functional team)

- Functional — feature works on primary flows.
- Quality — bug bar met, perf/load SLOs met, a11y / i18n check.
- Support — runbook, macros, FAQ, sev routing.
- Legal / compliance — review complete where required.
- Comms — internal announce, external announce, status page, docs.
- Commercial — pricing & packaging decided, billing hooks ready.
- Metrics — instrumentation live, dashboard owned.

## Kill / rollback criteria

Before launch, write down:

- **Kill:** conditions under which we turn this off and walk away.
- **Rollback:** conditions under which we revert to previous behaviour.
- **Iterate:** conditions under which we keep it on and change it.

Without this, every middling result becomes "we'll keep iterating" forever.

## Stakeholder alignment

- Decide who has **A** (accountable), **C** (consulted), **I** (informed) on the decision.
- Explicit disagree-and-commit record — "X disagreed on <point>, we proceeded because <reason>."
- Don't confuse "no one said no" with alignment.

## Anti-patterns

- Feature-shaped PRDs — "Build a button that…" instead of "Users need to…"
- Metric-less hypotheses — "This will delight users."
- Scope that grew in the last review and no one removed anything to compensate.
- RICE as a tie-breaker for "things we already decided."
- Guardrail metrics invented after launch to explain away a bad result.
- Personas with no numbers attached ("power users" — how many? which segment?).
- PRDs that describe engineering designs.
- "Success = launched on time." Launch is not success; outcome is.
