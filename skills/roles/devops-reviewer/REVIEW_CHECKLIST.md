# DevOps Review Checklist

## 1. Pipeline gates

- [ ] Lint / format / unit all present and enforcing.
- [ ] Static analysis / SAST as a gate, not advisory.
- [ ] Dependency scan with a policy (fail on high+, or explicit exemption).
- [ ] Image / container scan with the same policy.
- [ ] IaC scan (tfsec / checkov) present if IaC is in scope.
- [ ] Integration + contract tests run before publish.
- [ ] Smoke / soak after deploy to stage.
- [ ] Post-deploy verification gate for prod.

## 2. Identity & secrets

- [ ] CI ↔ cloud via OIDC / workload identity (no long-lived keys).
- [ ] No secret value in logs (verify masking).
- [ ] Secrets stored in a managed store; retrieved per-run.
- [ ] Rotation cadence stated; rotation tested.
- [ ] Least-privilege IAM — scopes audited.
- [ ] No shared human user / key for machine use.

## 3. Supply chain

- [ ] Base images pinned by digest.
- [ ] Dependency lockfile committed.
- [ ] Images signed (cosign or equivalent).
- [ ] SBOM generated per artefact.
- [ ] Provenance / SLSA level considered.
- [ ] Registry is trusted and access-controlled.

## 4. Deploy mechanism

- [ ] Strategy matches blast radius.
- [ ] Canary / progressive rollout has automatic rollback on SLO breach.
- [ ] Stateful services have a documented state-handling plan on deploy.
- [ ] DB migrations gated and reversible.
- [ ] Graceful shutdown / drain behaviour verified.

## 5. Rollback

- [ ] Mechanism is automatic or one command.
- [ ] Expected time to complete is stated.
- [ ] Rollback rehearsed at least once per [cadence].
- [ ] Rollback does not depend on the bad deploy succeeding (e.g., a broken image's sidecar).

## 6. IaC hygiene

- [ ] State backend remote, encrypted, locked.
- [ ] Providers and modules version-pinned.
- [ ] `plan` reviewed before `apply`; no auto-approve on prod.
- [ ] Destructive changes gated (separate approver or explicit flag).
- [ ] Drift detection scheduled.
- [ ] Environment diffs are parameters, not forked trees.

## 7. Kubernetes / container hygiene (if applicable)

- [ ] Non-root user.
- [ ] Resource requests + limits set.
- [ ] Probes distinct and meaningful.
- [ ] Graceful SIGTERM handling with drain.
- [ ] Pod disruption budgets.
- [ ] Network policies default-deny.
- [ ] No secrets baked into images.

## 8. Pipeline observability

- [ ] Pipeline runtime tracked and budgeted.
- [ ] Failure rate tracked.
- [ ] DORA metrics surfaced.
- [ ] Alerts on regressions (longer than budget, failure spike).

## Comment style

- Lead with blast radius / reversibility concerns.
- Quantify when possible ("this change can't be reverted in <15 min because…").
- Severity on every comment: **blocker**, **non-blocker**, **nit**.
- Praise at least one thing.
