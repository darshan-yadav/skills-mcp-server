# DevOps Reference

## Pipeline stages (a common shape)

1. **Lint / format** — cheap, fast, required.
2. **Build** — reproducible, cacheable, hermetic where possible.
3. **Unit tests** — fast, parallel.
4. **Static analysis / SAST** — as a gate, not a report.
5. **Dependency scan** — known CVEs, licence policy.
6. **Container / artefact build** — from a pinned base, with SBOM.
7. **Integration tests** — on ephemeral infra.
8. **Contract tests** — pact verification.
9. **Security tests** — IaC scan (tfsec / checkov), image scan (trivy / grype), DAST where relevant.
10. **Publish** — signed, immutable artefact to a registry.
11. **Deploy to stage** — automated.
12. **Smoke / soak in stage**.
13. **Deploy to prod** — canary → ramp → full; with automated rollback on SLO breach.

Not every project needs every stage — but skipping one should be a decision, not a default.

## Deploy strategies

- **Recreate** — downtime OK. Simplest.
- **Rolling** — default for stateless services.
- **Blue/green** — instant rollback, doubles infra briefly.
- **Canary** — route a % of traffic; auto-promote on SLO, auto-rollback on breach.
- **Progressive delivery** — canary + feature flags. Changes can be toggled without redeploy.

Match to blast radius, not fashion.

## IaC discipline

- [ ] State is remote, encrypted, locked.
- [ ] Providers and module versions pinned.
- [ ] Modules have inputs/outputs documented.
- [ ] Drift detection runs on schedule.
- [ ] Plan reviewed before apply — no "apply -auto-approve" on prod.
- [ ] Destructive changes behind a separate approval.
- [ ] Environment differences are parameters, not forked code.

## Identity & secrets

- [ ] OIDC / workload identity between CI and cloud.
- [ ] No long-lived cloud keys in repo secrets.
- [ ] Secrets in a managed store (AWS Secrets Manager / Vault / GCP Secret Manager / Azure Key Vault).
- [ ] Rotation cadence defined; rotation tested.
- [ ] Least-privilege IAM reviewed; scoped to the smallest resource set that works.
- [ ] No secret printed in CI logs (use masked env injection).

## Supply chain

- [ ] Base images pinned by digest, not tag.
- [ ] Dependencies pinned (lockfile committed).
- [ ] Images signed (cosign).
- [ ] SBOM produced per artefact.
- [ ] Provenance (SLSA) captured.
- [ ] Vulnerability scan gates set with a policy (fail on high+ for prod).

## Metrics to publish

- **Lead time for changes** — commit → prod.
- **Deploy frequency.**
- **Change failure rate** — deploys that required rollback / hotfix.
- **Mean time to restore.**
- **Pipeline runtime** — per stage + total.
- **Flake rate.**

## Anti-patterns

- Shell scripts doing what IaC should.
- Clicking in consoles for "just this one change."
- One shared long-lived IAM key used by CI.
- `docker push :latest` as the deploy.
- "We'll rollback by deploying the old commit" with no script and no rehearsal.
- Dev and prod diverging because only prod is managed by code.
- Secrets baked into images.
- Pipeline green = deploy succeeded — with no post-deploy verification.
- Running security scanners but ignoring findings because "CI would break."

## Kubernetes / container hygiene (if applicable)

- [ ] Non-root user in the image.
- [ ] Read-only root filesystem where possible.
- [ ] Resource requests + limits set.
- [ ] Liveness + readiness + startup probes distinct and meaningful.
- [ ] Graceful shutdown handles SIGTERM with a drain period.
- [ ] Pod disruption budgets.
- [ ] Network policies default-deny.
- [ ] Secrets mounted, not env-var'd, where possible.
