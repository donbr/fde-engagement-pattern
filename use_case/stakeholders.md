# Stakeholders

*Carried over from an earlier solution-first spike (not included in this repo) in step 1. What changed: what each role is expected to require is now in `requirements.md` (R1–R17). The two owners whose numbers decide the gates are asked for those numbers directly.*

*Step 17: added the **What they owe** column, and four rows. The CDO / CAIO row is new because R13 was traced to that role but no conversation was planned. Three approvers from the `ecosystem.md` checkpoint map are new because they gate go-live but had no row. Also added the three tables at the end. Each role's bold name is canonical: `requirements.md`, the owners in `evals/thresholds.json` and the readout's ask use it verbatim, and `tests/test_stakeholder_trace.py` checks that.*

**None of these conversations has happened.** The client is hypothetical (see `CHARTER.md`), so this is the *planned* list: who I'd talk to, in what order, what I'd ask, and what gets me past them. A row becomes real on the day the conversation does:
- *Status* gets the date;
- *What I learned* replaces *What clears them*;
- each item in *What they owe* is marked received, with its date, or still owed.

A threshold can't move from `proposed` to `signed` until its owner's row is real.

Roles only, never names.

> The final readout (`readout.md`) goes to everyone in this file.

| Stage | Who (role) | What I'd ask | What clears them | What they owe | Status |
| --- | --- | --- | --- | --- | --- |
| Design & Prototype, week 1 | **Member-service agent** (the person with the problem) | "Walk me through the last time the assistant failed mid-chat. What did you do next, and how long did it take?" | Seeing the chat SLA hold at the next peak. | That walkthrough: the inputs to the cost line in `CHARTER.md`. After the shadow run, their read of the member-chat numbers (R17). | planned |
| Design & Prototype, week 1 | **Member Services operations manager** (owns the SLA; signs the tier table) | "What does a failed or late chat cost you? Which work, if any, counts as more important than a member chat? **What peak failure rate is acceptable (T_chat)?**" | KPI deltas in their own metrics; they decide what counts as CRITICAL. | `t_chat` and `m3_min`; the tier table. | planned |
| Design & Prototype, week 1 | **Platform engineering lead** | "Where would a small container run here? Is there an API gateway in front of the model provider already?" | A draft deployment pattern to correct, not a blank page (`ecosystem.md`). | How many provider keys there are and what provider reporting breaks out (H9); `m2_min`. | planned |
| Design & Prototype, week 2 | **CISO / privacy officer** (veto) | "Can I get on your architecture review in week two, before we build?" | The blast radius: it only decides admit or shed, never reads content, runs under its own identity, has a kill switch. BAA with the model vendor; no PHI in logs. | An architecture-review slot in week 2; `m8_max`. | planned |
| Design & Prototype, week 2 | **CDO / CAIO** (admits AI use cases) | "Does this need to go through AI use-case intake if no model makes the decision?" | No model in the decision path: deterministic, explainable, identical on replay (R13). | The intake decision. | planned (added in step 17) |
| Design & Prototype, week 2 | **Data owner for usage and 429 logs** (often platform or FinOps) | "Can I get provider usage and 429s by API key for last open enrollment?" | A written purpose and retention limit. This is the baseline. | Usage and 429s by key for last open enrollment: the real baseline for M1 and M2. | planned |
| Design & Prototype, week 2 | **Claims operations manager** | "What does a summary that arrives an hour late cost? Could claims wait while members are on hold? **How many extra points of claims sheds would you accept to protect chat?**" | Seeing the trade-off as numbers: protecting chat raises claims sheds (`CHARTER.md` § Success). | `m4_max_points`: the Claims limit. | planned |
| Design & Prototype, week 2 | **Content Operations owner** (nightly policy refresh) | "How fresh must the refresh be? Could it run on the provider's batch lane?" | The refresh never competes with members, and it gets cheaper. | The freshness requirement for the refresh (R4). | planned |
| Build & Deploy | **FinOps lead / CFO delegate** (veto via procurement) | "What showback format do you already read? Do you want spend caps per department?" | Spend by department without manual work. Quota sized from the measured shortfall. | The showback format; a yes or no on spend caps. | planned |
| Build & Deploy | **Enterprise architect / CTO delegate** | "What review does a new gateway policy need, and how long does it take?" | Eval baseline, runbook with a kill switch, the scaling answer (shared counters at a second replica). | The review path and its lead time; whether a gateway already fronts the provider (R14). | planned |
| Build & Deploy | **Network / security engineering** (egress allowlist) | "Who adds the provider host to the egress allowlist, and what do you need from me to do it?" | Provider host, port, purpose and owner, in one request. | The allowlist entry (1–2 weeks, `ecosystem.md` checkpoint map). | planned (added in step 17) |
| Build & Deploy | **Security engineering** (image scanning and signing) | "Must the image be scanned or signed before it runs? Is there DLP on egress?" | An image built from the mandated base. | Scan and signing results; the DLP answer. | planned (added in step 17) |
| Build & Deploy | **Change advisory board** (change approval) | "When is the next board, and what does a change request for an observe-only policy need?" | Runbook, kill switch, and rollback that is just turning the policy off. | Approval at the next scheduled board. | planned (added in step 17) |
| Build & Deploy | **SRE / on-call lead** | "Who gets paged when sheds spike, and what's the rollback?" | Runbook, dashboards (sheds by tier and reason), shadow mode first. | `m6_p99_ms_max`; who is paged, and the fail-open check in the runbook. | planned |
| Each stage gate | **Sponsor (CIO)** (go / no-go) | "Proceed, narrow, or stop at this gate?" | A staged roadmap with gates; one forum with named owners. | A go / no-go at each gate. | planned |
| Throughout | **FDE practice lead** (my own manager) | "Which parts of this can the practice reuse on the next engagement: the discovery method, the option ladder or the gateway policy pack?" | A handover that works without me, and a pattern the next engagement can start from. | Which parts the practice will reuse. | planned |

---

## Rows with no requirement

Every other row is the source of a requirement in `requirements.md` or owns a threshold in `evals/thresholds.json`.

| Role | Why there is no requirement |
| --- | --- |
| Data owner for usage and 429 logs | They supply the baseline rather than use the product. Their condition, a written purpose and retention limit, is a precondition for the data, not a feature. |
| FDE practice lead | My own manager. Their question is what the practice can reuse, which the handover and the README's reuse table answer. It asks nothing of the client's system. |
| Network / security engineering | An approval gate with a lead time (`ecosystem.md` checkpoint map). What they need is a request, not a product requirement. |
| Security engineering | An approval gate (`ecosystem.md` checkpoint map). What they need is an image built from the mandated base, not a product requirement. |
| Change advisory board | An approval gate (`ecosystem.md` checkpoint map). What they need is the runbook and rollback, which R7 already requires. |

## Teams reached through another row

`ecosystem.md` asks these teams factual questions. The named row brokers each conversation; if one becomes a conversation of its own, it gets its own row above.

| Team | Reached through | For |
| --- | --- | --- |
| Identity team | Platform engineering lead | Whether SSO terminates before the app |
| Network engineering | Platform engineering lead | Whether the app is reachable except through the gateway; which VPC or VNet |
| AI CoE | CDO / CAIO | Model registry or approval |

## Not everyone is an infrastructure contact

Coverage check against a standard FDE stakeholder checklist:

| Checklist | Rows |
| --- | --- |
| The person with the problem | Member-service agent |
| Whoever owns the data | Data owner for usage and 429 logs |
| Whoever runs the platform | Platform engineering lead, SRE / on-call lead |
| Whoever approves | CISO / privacy officer, CDO / CAIO, FinOps lead / CFO delegate, Enterprise architect / CTO delegate, Network / security engineering, Security engineering, Change advisory board, Sponsor (CIO) |
| My own manager | FDE practice lead |

- **The person with the problem is shown the shadow-run numbers first,** before any owner signs a threshold (R17, `readout.md` §5).
- **My own manager** is the head of the group for an internal FDE team, or the engagement lead when the FDEs serve outside clients.
