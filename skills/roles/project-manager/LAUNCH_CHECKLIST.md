# Launch Readiness Checklist

- **Project:**
- **Target launch date:**
- **Launch tier:** (silent / beta / GA)
- **Launch owner (one name):**

## Engineering
- [ ] Code complete, merged to release branch
- [ ] Feature flags named and default-set
- [ ] Performance / load tests at target meet SLO
- [ ] Security review complete
- [ ] Rollback rehearsed end-to-end

## QA
- [ ] Regression suite green on release candidate
- [ ] Targeted test coverage reviewed
- [ ] Known issues documented and triaged
- [ ] Release notes reviewed

## SRE / CloudOps
- [ ] Alerts created with runbook links
- [ ] Dashboards updated and owned
- [ ] Capacity headroom validated
- [ ] On-call notified and context shared
- [ ] Backup / restore confirmed for any new data stores

## Support
- [ ] Macros, FAQ, and help-centre docs updated
- [ ] Severity routing agreed
- [ ] Training delivered to front-line support
- [ ] Feedback channel into the product team defined

## Legal / compliance
- [ ] Privacy review complete
- [ ] T&Cs / data-processing updates (if any)
- [ ] Regulatory notifications (where required)
- [ ] Data-residency & retention settings confirmed

## Comms
- [ ] Internal announce drafted and scheduled
- [ ] External announce drafted and scheduled (blog / changelog / email)
- [ ] Docs & API reference updated
- [ ] Status page component set up

## Commercial / GTM
- [ ] Pricing & packaging finalised
- [ ] Billing hooks live
- [ ] Sales enablement materials ready
- [ ] Partner / channel comms (if relevant)

## Product
- [ ] Instrumentation live in prod
- [ ] Dashboard shared and owned
- [ ] Guardrail metrics wired with alerts
- [ ] Kill / rollback / iterate criteria confirmed with stakeholders

## Day-of
- [ ] Go / no-go call scheduled
- [ ] War room / bridge defined if needed
- [ ] Rollback authority named
- [ ] Post-launch review scheduled
