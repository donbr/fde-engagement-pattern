# Requirements, traced to stakeholders

*Written in step 1, before any code. The stakeholders are hypothetical (see `stakeholders.md`), so each requirement is **what I'd expect that role to ask for**, marked to confirm in the first conversation. The role names are the canonical ones from `stakeholders.md` (normalized in step 17; no requirement's text changed). Each one names how it will be checked: a golden case (`evals/golden.jsonl`), a test, or a pre-registered metric (`cxo-story.md` §4).*

| # | Stakeholder (role) | Requirement | Checked by |
| --- | --- | --- | --- |
| R1 | Member Services operations manager | Lower tiers can never starve member chat; chat may spend what they had to leave behind. | Golden `member_chat_survives_refresh_flood`; M1 |
| R2 | Member Services operations manager | **I** set the member-chat target, not the engineer. | `thresholds.json` `t_chat`, with owner and status |
| R3 | Claims operations manager | Show me what protecting chat costs Claims **before** anything is enforced. | M4, reported from the shadow replay |
| R4 | Content Operations owner | If the refresh moves off the live limit, it still completes. | Option 1 models the refresh on a separate batch lane; freshness is an open question for the owner |
| R5 | CISO / privacy officer | The tier comes from the caller's authenticated identity. A tier claimed in the request is ignored and flagged. Unknown callers are rejected. | Golden `tier_comes_from_identity`; M8 |
| R6 | CISO / privacy officer | Decision records carry metadata only, never prompt or response content. | Test on the decision record's fields |
| R7 | SRE / on-call lead | Shadow mode first: it never blocks a known caller, but records what it would have done. (Unknown callers are rejected in both modes; `decisions.md`, step 10.) A kill switch returns to today's behaviour at runtime. | Golden `shadow_mode_and_kill_switch` |
| R8 | SRE / on-call lead | Sheds are counted by tier **and reason**. | Test on the gateway's counts |
| R9 | SRE / on-call lead | The added decision latency is negligible next to the model call. | M6 (p99), threshold `m6_p99_ms_max` |
| R10 | FinOps lead / CFO delegate | Spend is charged on **actual** tokens for every call that ran, including calls that shadow mode allowed but would have shed. Calls that never ran cost nothing. | Golden `showback_charges_what_ran` |
| R11 | FinOps lead / CFO delegate, Sponsor (CIO) | Before buying quota, know how much is needed. | M5 and the quota-scale search |
| R12 | Sponsor (CIO) | Each gate gives PROCEED, NARROW or STOP from thresholds agreed in advance. Proposed thresholds are labelled; a missing threshold gives no verdict. | Golden `gate_stops_when_cheap_fix_suffices`; gate tests |
| R13 | CDO / CAIO | No model in the decision path; decisions are deterministic and identical on replay. | Determinism test; `decisions.md` |
| R14 | Enterprise architect / CTO delegate | Don't build a new service if a gateway already fronts the provider. | Design: the policy is a library, not a server (`decisions.md`) |
| R15 | Sponsor (CIO), FinOps lead / CFO delegate, Member Services operations manager | *(Added in step 8.)* **Metrics that don't exist today, from the first day of shadow mode:** calls, failures and would-sheds by workload, tier and reason; spend on actual tokens by department; estimate accuracy (actual ÷ estimate, overruns) by workload. | `test_observability.py`; the output of `python -m fde_gateway.observe` (`evals/results/2026-10-18_heldout_observability.md`) |
| R16 | Member Services operations manager, Platform engineering lead | *(Added in step 8.)* **Provider failures (429s) attributed to the workload that suffered them**, even when every team shares one provider key. That makes M1 and M2 measurable on real traffic. | `test_observability.py`; shadow replay of `today` |
| R17 | Member-service agent | *(Added in step 17.)* **The people who lose the assistant at peak see the shadow numbers for member chat first,** before any owner signs a threshold and before anything is enforced. | `readout.md` §5 (the first step after the shadow run); M1 for member chat from `python -m fde_gateway.observe` |

## Non-goals (this pass)

- No HTTP server, no queue, no shared counter store, no integration with a real provider.
- No real client data. Synthetic traffic only (`data/DATASHEET.md`).

## Anti-goals: these would make it a failure even if every test passed

- Enforcing priority when the tier can't be tied to identity.
- Quoting simulated numbers as a forecast for a real system.
- Tuning a threshold after seeing the held-out results without logging it.
- Recommending the gateway when a cheaper option meets the same bar.
