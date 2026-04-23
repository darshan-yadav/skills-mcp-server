# Runbook: <Alert / Condition Name>

- **Service:**
- **Alert:** (alert rule name + link)
- **Severity:** SEV1 / SEV2 / SEV3
- **Owner team (paged):**
- **Escalation path:**
- **Last reviewed:** YYYY-MM-DD

## What this means
<!-- One sentence: what signal is firing, in user-observable terms. -->

## User impact
<!-- Who is affected, how, and how visibly. -->

## First 3 actions (in order)
1.
2.
3.

## Diagnostics
- Dashboards:
- Logs query:
- Traces query:
- Recent deploys / flag flips / config changes:

## Likely causes
- Cause A — signal: — action:
- Cause B — signal: — action:
- Cause C — signal: — action:

## Known remediations
- Rollback command:
- Feature flag to flip:
- Scale action:
- Traffic shift:

## When to escalate
- If <condition> after <time>, page <next tier>.
- If <condition>, declare SEV<N> and open the comms channel.

## Communication
- Status page component:
- Customer-facing messaging template:
- Internal channel:

## After resolution
- Close the incident.
- Capture timeline & evidence.
- Schedule postmortem (see `POSTMORTEM_TEMPLATE.md`).
