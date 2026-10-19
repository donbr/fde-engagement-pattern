# Evals

*Written in steps 2–3 of `../../PROCESS.md`, before any code.*

## `golden.jsonl`: stakeholder acceptance cases

Five cases, one per requirement that decides the design. The expected values were worked out by hand from the requirement. They are **not** read off an implementation (none existed yet).

| Case | Stakeholder | Requirement | What it pins down |
| --- | --- | --- | --- |
| `member_chat_survives_refresh_flood` | Member Services operations manager | R1 | Each lower tier stops at its floor; chat spends what's left |
| `tier_comes_from_identity` | CISO / privacy officer | R5 | A claimed tier is ignored and flagged; an unknown caller is rejected (**the escalate case**) |
| `shadow_mode_and_kill_switch` | SRE / on-call lead | R7 | Shadow mode never blocks a known caller; enforcement can be switched on and off mid-run |
| `showback_charges_what_ran` | FinOps lead / CFO delegate | R10 | Spend is charged on actual tokens, including shadow-allowed would-sheds; blocked calls cost nothing |
| `gate_stops_when_cheap_fix_suffices` | Sponsor (CIO) | R12 | **The stop case**: the instrument recommends against building the gateway when option 1 meets the target |

### Format

Each line is `{"input", "output", "why"}`.

**Gateway cases** have these inputs: `config`, `identities` (caller → workload), the initial `enforce` flag, and `steps`. Each step is one of:
- `submit`: caller, id, token_estimate, and optionally `claimed_workload`;
- `settle`: id, token_actual;
- `set_enforce`.

Each step's expected result is one of:
- a dict, checked on its listed keys only (`allowed`, `reason`, `workload`, `spoof_attempt`, `enforced`);
- `null`;
- an exception name.

`showback` is checked at the end.

**The gate case** gives `thresholds` and `metrics`, and expects a verdict for each gate.

Both mixes run against the same workload table: `member_chat` → Member Services, CRITICAL; `claims_summary` → Claims, STANDARD; `policy_refresh` → Content Operations, DEFERRABLE.

## `thresholds.json`: pre-registered decision thresholds

Written in step 3, before any replay ran on the held-out seeds. Each threshold records:
- its value;
- the owner who must sign it;
- its status (`proposed` until that owner signs);
- the reason for the proposed value.

Every verdict the evaluation reports carries the status of the thresholds it used. **A missing threshold produces NOT DECIDABLE, never a default.**

Changing a value after step 5 requires a row in `../decisions.md` saying what changed, why, and who approved it.
