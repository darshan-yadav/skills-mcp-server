# Product Manager Review Checklist

## 1. User & problem

- [ ] Persona / segment named with numbers.
- [ ] Pain described in user language, not internal terms.
- [ ] Frequency and severity of the pain quantified.
- [ ] Current workaround named (or explicit "no workaround").
- [ ] Cost of the problem stated (time, revenue, risk, churn).
- [ ] "Why now" is answered.

## 2. Jobs to be done

- [ ] JTBD statement present: situation / motivation / outcome.
- [ ] The proposed feature directly enables the outcome — not adjacent.

## 3. Hypothesis

- [ ] Stated as "if <change>, then <metric> moves from <A> to <B> within <window>".
- [ ] Mechanism (why this change should move that metric) is explicit.
- [ ] Confidence level stated (not assumed high).

## 4. Metrics

- [ ] **Primary** — one, with definition, source, window, target.
- [ ] **Inputs** — levers that move the primary.
- [ ] **Guardrails** — must-not-regress, named with thresholds.
- [ ] **Counter-metric** — catches the flip side.
- [ ] Proxies labelled as proxies.
- [ ] Instrumentation plan exists; dashboard has an owner.

## 5. Scope

- [ ] In-scope list is finite.
- [ ] Out-of-scope list exists and is specific.
- [ ] No "nice to have" — items are either in v1 or "not v1."
- [ ] Future phases described as *hypotheses*, not promises.

## 6. Requirements

- [ ] User-facing outcomes, not implementation.
- [ ] Edge cases considered (empty, error, permission, offline, read-only).
- [ ] Accessibility and localisation addressed or explicitly deferred.
- [ ] Security / privacy implications noted where relevant.

## 7. Launch criteria

- [ ] Functional bar defined.
- [ ] Quality bar (bug bar, perf SLO, a11y, i18n).
- [ ] Support readiness (runbook, macros, FAQ, severity routing).
- [ ] Legal / compliance review routed.
- [ ] Comms plan (internal, external, docs, status page).
- [ ] Commercial readiness (pricing, billing hooks, packaging).
- [ ] Instrumentation live before launch.

## 8. Rollout plan

- [ ] Phases with entry + exit criteria.
- [ ] Feature flags named.
- [ ] Regions / cohorts / % ramp plan.

## 9. Kill / rollback / iterate

- [ ] Kill criterion pre-committed.
- [ ] Rollback criterion pre-committed.
- [ ] Iterate criterion defined (not a dumping ground).

## 10. Alternatives & dependencies

- [ ] At least one alternative considered.
- [ ] "Do nothing" considered.
- [ ] Cross-team dependencies named with owners.

## 11. Risks & assumptions

- [ ] Assumptions flagged explicitly.
- [ ] Top risks have severity and mitigation.
- [ ] Disagree-and-commit decisions recorded.

## 12. Form

- [ ] Short enough to read (< 5 pages ideal).
- [ ] Links out where duplication would occur.
- [ ] No engineering design sneaking into the PRD.

## Comment style

- Lead with "this will cause ambiguity at build time" or "this metric can't be measured" — concrete consequences.
- Severity on every comment: **blocker**, **non-blocker**, **nit**.
- Surface unstated assumptions as questions.
- Praise at least one thing.
