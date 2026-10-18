# Readout: which fix keeps member chat up at peak

*To: everyone in `stakeholders.md`. From: the FDE lead. Stage: end of Design & Prototype, simulated.*
*The client is hypothetical and the traffic synthetic (`data/DATASHEET.md`). The thresholds are **proposed and unsigned** (`evals/thresholds.json`). Every number comes from the held-out runs in `evals/results/`, regenerated from code in steps 9 and 10 with label and reporting changes only; every count and verdict is identical to the step 5 run (`../PROCESS.md`).*
*Amended in step 8 (`../PROCESS.md`): the first version judged the gateway only as an enforcer and missed its visibility value. The recommendation changed as a result; the gate verdicts did not.*

## 1. Headline

During open enrollment, member-service agents lose their AI assistant at peak because back-office work uses up the shared model limit. On simulated peaks, **moving the nightly refresh to the batch lane cuts member-chat failures from 18.3% to 5.8%, with no new software.** A thin gateway run **observe-only** gives the numbers nobody has today: which department's calls fail, who uses the peak, and how far off the estimates are. Those numbers decide whether enforcing priority is ever worth it.

## 2. What it does

The product is a **decision instrument** with two parts:

1. **An options replay.** The same peak traffic runs through each fix in cost order. Each fix is scored against thresholds agreed in advance and gets a verdict at each gate.
2. **A gateway that runs in shadow mode first.** It decides each call by **authenticated identity** (a claimed tier is ignored and flagged, an unknown caller is rejected). It **blocks no known caller**, but it records:
   - every provider failure, attributed to the workload that suffered it;
   - what the policy would have held back, and why;
   - spend on actual tokens by department;
   - actual ÷ estimated tokens by workload.

   Enforcement is a separate switch, flipped only if the evidence says so.

**Worked example** (golden case `showback_charges_what_ran`, shadow mode). The refresh job sends a 700-token call. The policy would hold it back (it would leave 300, under its 400 floor), but in shadow mode it runs, and its **650 actual tokens are charged to Content Operations**. A member chat estimated at 300 uses 240 and is charged 240. Finance sees who used what. Member Services sees what protection would have done. Nobody was blocked.

## 3. The numbers

### What shadow mode shows that today's data can't

20 held-out peaks. Nothing enforced; the provider behaves exactly as it does today (`evals/results/2026-10-18_heldout_observability.md`):

| | Today, one shared key | Shadow gateway, `baseline` (spill-over) | Shadow gateway, `waves` (chat bursts) |
| --- | --- | --- | --- |
| Failures by workload | 1,226 failures (`baseline`), **not attributed** | chat 113/618, claims 99/221, refresh 1,014/1,162 | chat 501/1,209, claims 133/221, refresh 1,029/1,162 |
| Peak tokens by department | **none** | Member Services 49%, Content Ops 30%, Claims 21% | Member Services 62%, Content Ops 25%, Claims 14% |
| Actual ÷ estimate | **none** | chat 0.87, claims 0.90, refresh 0.86 | chat 0.88, claims 0.90, refresh 0.86 |

**The token share is the diagnosis.** When back office takes about half the peak (`baseline`), moving the refresh is the lever. When member chat takes 62% (`waves`), the lever is quota. Actual usage comes in 10–14% under the estimate (estimates run 11–16% high), so every hold reserves capacity that's never used.

### What each fix would do

Chat and claims shed / offered:

| Option | `baseline` | `waves` |
| --- | --- | --- |
| Today | chat 113/618 = 18.3%, claims 99/221 = 44.8% | chat 501/1209 = 41.4%, claims 133/221 = 60.2% |
| **1. Refresh to batch lane** | **chat 36/618 = 5.8%**, claims 49/221 = 22.2% | chat 390/1209 = 32.3%, claims 97/221 = 43.9% |
| 2. + Separate limits | chat 110/618 = 17.8%, claims 149/221 = 67.4% | chat 598/1209 = 49.5%, claims 149/221 = 67.4% |
| 3a. + Enforce, starter reserves | chat 31/618 = 5.0%, claims 57/221 = 25.8% | chat 381/1209 = 31.5%, claims 106/221 = 48.0% |
| 3b. + Enforce, claims floor = one chat | chat 16/618 = 2.6%, claims 98/221 = 44.3% | chat 342/1209 = 28.3%, claims 148/221 = 67.0% |
| Member chat alone | chat 6/618 = 1.0% | chat 316/1209 = 26.1% |

| Enforcement gate | `baseline` | `waves` |
| --- | --- | --- |
| G0: is the problem real, and caused by back office? | PROCEED (M2 95%) | NARROW: size quota (M2 37%) |
| G1: was the cheap fix enough? | PROCEED (5.8% vs 5%) | not reached |
| G2: is enforcement worth it? | NARROW: the Claims owner decides (3b: M3 56%, M4 +22.2 pts) | not reached |

**What would flip each verdict:**
- **G1 → STOP** if T_chat ≥ 5.83% (option 1 leaves 36/618 = 5.825%).
- **G2 → PROCEED with 3b** if Claims accepts at least +22.2 points.
- **3a** never passes unless the required benefit drops to 13.8% or less (it removes 5/36 = 13.9%).

**What these numbers don't cover:**
- The traffic mixes are assumed.
- No retries.
- The provider is approximated by a token bucket.
- One replica.
- Latency (p99 about 4–8 µs across runs) was measured on a laptop.

## 4. The cost

| Path | Cost | What you get |
| --- | --- | --- |
| Option 1 | Days; one owner (Content Operations) | 18.3% → 5.8% in `baseline`; 41.4% → 32.3% in `waves` |
| **Shadow gateway** | It sits in the call path, so it needs the architecture review and egress entry. It blocks no known caller (unknown callers are rejected), so there's no enforcement risk. | The metrics above, on real traffic, by department |
| Cheaper attribution: one provider key per workload | Days; platform team | Attributed failures and spend from provider reporting, *if* the provider breaks those out per key (check). **No** would-sheds and no estimate accuracy. |
| Enforcement (3b) | Turn on a switch that's already deployed; Claims sheds 22% → 44% | Chat 5.8% → 2.6% (`baseline`) |
| Quota | About 1.1× (`baseline`) or 1.9× (`waves`) of today | Meets the 5% target with option 1 |

## 5. What it would take to run for real

| When | Step |
| --- | --- |
| Week 1 | Ask the platform lead how many provider keys there are and what provider reporting breaks out (H9). |
| Weeks 1–2 | **Option 1:** move the refresh. It helps in both kinds of peak. |
| Weeks 2–5 | **Shadow gateway:** architecture review, CISO sign-off and egress entry in parallel (`ecosystem.md`), then observe-only in production. |
| Next peak | Read the shadow metrics. Member Services signs T_chat, and Claims signs its limit. Rerun `evaluate` with the signed values and real token shares. |
| Only if G2 says PROCEED on real data | Turn enforcement on. Rollback is turning it off again. |

## 6. The risks

| Risk | Status |
| --- | --- |
| Tier spoofing | Designed out: the tier comes from identity. 0 of 221 spoofing attempts were decided at CRITICAL. |
| A gateway in the call path, even observe-only | Shadow mode never blocks a known caller. A failure in the gateway itself must fail open to today's path; the SRE lead confirms in the runbook. |
| Choosing on simulated traffic | The two mixes disagree, so the shadow metrics on real traffic decide, not this simulation. |
| Thresholds set by the engineer | All six are proposed, labelled in every verdict, and handed to named owners. |
| The visibility value disappears if per-workload keys already exist | H9 is the week-1 question. If it's true, decide the gateway on enforcement alone. |

## 7. Recommendation

**Proceed with option 1 and the shadow gateway. Defer enforcement.**

- The shadow gateway earns its place by producing metrics that don't exist today. It needs no enforcement decision and blocks no known caller.
- Enforcement waits for the real token shares and the two signed thresholds.
- If the shadow metrics show chat's own bursts dominate, the answer is quota, enforcement never turns on, and the gateway stays as the measurement and showback layer.

## 8. Handover

| Item | Where |
| --- | --- |
| Code | `../solution/`. `uv run pytest` runs 82 checks. `uv run python -m fde_gateway.evaluate` reproduces the fixes table; `uv run python -m fde_gateway.observe` reproduces the shadow metrics. |
| Requirements (R1–R16) and acceptance cases | `requirements.md`, `evals/golden.jsonl` |
| Rules fixed before the run | `evals/PREREGISTRATION.md`, `evals/thresholds.json` |
| Decisions, including the step 8 amendment | `decisions.md` |
| Order of work | `../PROCESS.md` |

---

**The ask:**
- **The platform engineering lead, week 1:** how many provider keys there are, and what provider reporting breaks out per key.
- **The enterprise architect and CISO:** an architecture-review slot in week 2, for a gateway that observes only.
- **The Member Services and Claims operations managers:** 30 minutes together after the next peak, to sign T_chat and the Claims limit against the shadow numbers.
