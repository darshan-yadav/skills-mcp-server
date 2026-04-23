# Pipeline / Deploy Design Template

## Service / artefact
- Name:
- Repository:
- Language / runtime:
- Target environments:

## Build
- Build system:
- Reproducibility strategy (hermetic / cached / pinned base):
- Output artefact(s):

## Quality gates (in order)
| Stage | Tool | Pass criteria | Required for prod? |
|-------|------|---------------|--------------------|
| Lint  |      |               |                    |
| Unit  |      |               |                    |
| SAST  |      |               |                    |
| Dep scan |   |               |                    |
| Image scan | |               |                    |
| Integration | |              |                    |
| Contract |   |               |                    |

## Publish
- Registry / artefact store:
- Naming (immutable tag strategy):
- Signing (cosign / equivalent):
- SBOM / provenance:

## Deploy
- Strategy (recreate / rolling / blue-green / canary / progressive):
- Auto-promote on (metric + threshold):
- Auto-rollback on (metric + threshold):
- Manual approvals (when required):

## Identity & secrets
- CI ↔ cloud auth (OIDC / workload identity):
- Secret store:
- Rotation cadence:
- Audit log location:

## Rollback
- Mechanism (revert / flag flip / previous artefact):
- Expected time to complete:
- Rehearsal cadence:

## Observability (of the pipeline itself)
- DORA metrics source:
- Alert on: deploy failure rate, pipeline runtime regression, scanner finding unaddressed >N days.

## Runbook links
-
