# Stakeholders

*Carried over from an earlier solution-first spike (not included in this repo) in step 1. What changed: what each role is expected to require is now in `requirements.md` (R1–R14). The two owners whose numbers decide the gates are asked for those numbers directly.*

**None of these conversations has happened.** The client is hypothetical (see `CHARTER.md`), so this is the *planned* list: who I'd talk to, in what order, what I'd ask, and what gets me past them. A row becomes real on the day the conversation does. Then *Status* gets the date, and *What I learned* replaces *What clears them*.

Roles only, never names.

> The final readout (`readout.md`) goes to everyone in this file.

| Stage | Who (role) | What I'd ask | What clears them | Status |
| --- | --- | --- | --- | --- |
| Design & Prototype, week 1 | **Member-service agent** (the person with the problem) | "Walk me through the last time the assistant failed mid-chat. What did you do next, and how long did it take?" | Seeing the chat SLA hold at the next peak. | planned |
| Design & Prototype, week 1 | **COO / Member Services owner** (owns the P&L) | "Will your people's numbers move? Who on your side sets the member-chat target?" | M1 against T_chat, which their Member Services operations manager signs. If the cheap fix meets it, the work stops there, and that is good news for them. | planned (added in step 17) |
| Design & Prototype, week 1 | **Member Services operations manager** (owns the SLA; signs the tier table) | "What does a failed or late chat cost you? Which work, if any, counts as more important than a member chat? **What peak failure rate is acceptable (T_chat)?**" | KPI deltas in their own metrics; they decide what counts as CRITICAL. | planned |
| Design & Prototype, week 1 | **Platform engineering lead** | "Where would a small container run here? Is there an API gateway in front of the model provider already?" | A draft deployment pattern to correct, not a blank page (`ecosystem.md`). | planned |
| Design & Prototype, week 2 | **CISO / privacy officer** (veto) | "Can I get on your architecture review in week two, before we build?" | The blast radius: it only decides admit or shed, never reads content, runs under its own identity, has a kill switch. BAA with the model vendor; no PHI in logs. | planned |
| Design & Prototype, week 2 | **CDO / CAIO** (admits the use case) | "Does this go through AI use-case intake when no model makes the decision, and what would you need to see?" | No agent, on purpose: a deterministic control that is fast, explainable and identical on replay (R13; M6 and the golden cases). | planned (added in step 17) |
| Design & Prototype, week 2 | **Data owner for usage and 429 logs** (often platform or FinOps) | "Can I get provider usage and 429s by API key for last open enrollment?" | A written purpose and retention limit. This is the baseline. | planned |
| Design & Prototype, week 2 | **Claims operations manager** | "What does a summary that arrives an hour late cost? Could claims wait while members are on hold? **How many extra points of claims sheds would you accept to protect chat?**" | Seeing the trade-off as numbers: protecting chat raises claims sheds (`CHARTER.md` § Success). | planned |
| Design & Prototype, week 2 | **Content Operations owner** (nightly policy refresh) | "How fresh must the refresh be? Could it run on the provider's batch lane?" | The refresh never competes with members, and it gets cheaper. | planned |
| Build & Deploy | **FinOps lead / CFO delegate** (veto via procurement) | "What showback format do you already read? Do you want spend caps per department?" | Spend by department without manual work. Quota sized from the measured shortfall. | planned |
| Build & Deploy | **Enterprise architect / CTO delegate** | "What review does a new gateway policy need, and how long does it take?" | Eval baseline, runbook with a kill switch, the scaling answer (shared counters at a second replica). | planned |
| Build & Deploy | **SRE / on-call lead** | "Who gets paged when sheds spike, and what's the rollback?" | Runbook, dashboards (sheds by tier and reason), shadow mode first. | planned |
| Each stage gate | **Sponsor (CIO or COO)** (go / no-go) | "Proceed, narrow, or stop at this gate?" | A staged roadmap with gates; one forum with named owners. | planned |
| Throughout | **FDE practice lead** (my own manager) | "Which parts of this can the practice reuse on the next engagement: the discovery method, the option ladder or the gateway policy pack?" | A handover that works without me, and a pattern the next engagement can start from. | planned |

---

## Not everyone is an infrastructure contact

Coverage check against a standard FDE stakeholder checklist:

- **The person with the problem:** the member-service agent. They get shown the shadow-run numbers first.
- **Whoever owns the data:** the usage and 429 logs owner.
- **Whoever runs the platform:** the platform engineering lead and SRE.
- **Whoever approves:** CISO (security), CDO / CAIO (the AI use case), FinOps (spend), enterprise architect (design), sponsor (CIO or COO; go/no-go). The COO / Member Services owner owns the P&L the problem lands on.
- **My own manager:** the FDE practice lead. That is the head of the group for an internal FDE team, or the engagement lead when the FDEs serve outside clients.
