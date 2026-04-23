# PR Description Template

## Summary
<!-- One paragraph: what this change does and why. Link the ticket. -->

## Changes
<!-- Bullet list, one line per notable change. Group by file or subsystem. -->
-

## Testing
<!-- What you ran, what you added, what you couldn't automate and why. -->
- Unit:
- Integration / e2e:
- Manual:

## Risk & Rollback
<!-- What could break in production, and exactly how to revert. -->
- Blast radius:
- Feature flag: `<flag_name>` (default: off)
- Rollback: revert commit OR flip `<flag_name>` to off

## Observability
<!-- New metrics, logs, alerts, dashboards. -->
-

## Data / Migration Notes
<!-- Schema changes, backfill plans, compatibility window. Write "N/A" if none. -->

## Security Notes
<!-- AuthZ touched? New trust boundary? Secrets handling changed? "N/A" if none. -->

## Screenshots / Output
<!-- For UI or CLI changes. -->

## Reviewer Checklist
- [ ] Scope matches the ticket; no drive-by refactors
- [ ] Tests cover new behaviour and at least one failure path
- [ ] Rollback path is explicit and tested
- [ ] No secrets, PII, or full request bodies in logs
- [ ] Feature flag default is safe
