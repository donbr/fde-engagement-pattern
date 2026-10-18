# The CxO story: sell the outcome, pre-register the proof, say the kill criteria out loud

*fde-engagement-pattern · illustrative example · written **before** implementation*

This replaces the story from an earlier solution-first spike (not included in this repo) with one built the FDE way:
1. Start from the problem.
2. Lay out the options in cost order.
3. Write down what would prove the gateway useful, and what would kill it, **before** any data comes in.

The client is hypothetical (a regional health insurer, an illustrative example). Two sets of numbers appear here, both from synthetic traffic: §2 shows what an earlier solution-first spike suggested (not included in this repo), and §8 records this pass's held-out results. Both are labelled, and neither stands in for a real baseline.

> **The trust principle.** Stopping the gateway, or the wider roadmap, is a legitimate outcome, and I tell the sponsor that in the first meeting. A CxO who hears the kill criteria on day one believes the "proceed" recommendation on day sixty.

---

## 1. The 30-second version

> "Picture a payer in open enrollment whose member chats fail because back-office jobs eat the shared model limit. Before I build anything, I'd put a cost on a failed chat and find out which callers are actually using up the limit. The first fix is probably a scheduling change, not software: get the nightly refresh off the live limit. In parallel, a thin gateway in observe-only mode gives you numbers you don't have today: which department's calls fail, who uses the capacity at peak, and how far off the estimates are. If the scheduling change is enough, we stop enforcing anything, and I'll tell you so. If it isn't, the same gateway can protect member chat from what's left. I'll agree with you up front which numbers decide that, and you'll see them at every gate, good or bad."

| Who | What | Wow |
| --- | --- | --- |
| Member-service agents at a regional health insurer | Get answers within their SLA, even at open-enrollment peak | The monthly AI bill becomes predictable by department |

**The problem in one sentence, no solution in it:**

> During open enrollment, member-service agents lose their AI-assisted answers at the moment of highest member demand, because back-office work uses up the shared model capacity first, and nobody can say which department used it.

---

## 2. What we're selling, and what we're not

**We're selling an outcome and a decision process, not a gateway.** The gateway is option 3 of 5. It earns its place only if the cheaper options leave a gap worth closing.

| # | Option | Cost and time | What it fixes | What it can't fix |
| :---: | --- | --- | --- | --- |
| 0 | Do nothing | None | Nothing | Failures in the same weeks every year |
| 1 | **Move the nightly refresh off the live limit**: reschedule it, or send it to the provider's batch lane | Days; a config or scheduler change; batch pricing may lower cost (check your provider's current pricing) | The spill-over flood, if that's the main cause | Claims and chat competing with each other; chat's own bursts; showback |
| 2 | **Separate limits per workload**: separate provider workspaces or keys with their own limits (confirm what the provider supports) | Days to weeks; an account and key change | Hard isolation between departments, and showback by key | Idle capacity can't be borrowed; it splits the pipe instead of prioritizing it |
| 3 | **Tiered gateway**: per-tier reserves, fail closed on unknown callers, showback on actual tokens | Weeks; a security review and an egress entry | Lower tiers can never starve member chat, and CRITICAL can still borrow everything | Chat's own bursts; anything beyond the account's total limit |
| 4 | **Buy more quota** | Fast; recurring cost | Everything, at a price | Nothing technical, but the amount is a guess unless options 1–3 measure it first |

**Order of recommendation:** 1 first. Then measure. Then 3 only if the gap is worth it, compared against 2. Then 4, sized by what remains. Each step's data decides whether the next one happens.

### The gateway has two values, decided separately *(amended in step 8)*

| Value | What it gives | When it earns its place | Risk |
| --- | --- | --- | --- |
| **1. Visibility (shadow mode)** | Metrics that **don't exist today**: provider failures attributed to the workload and department that suffered them; would-sheds by tier and reason; spend on actual tokens by department; estimate accuracy by workload. These make M1, M2 and M4 measurable on real traffic. | When today's data can't attribute: one shared provider key, no gateway in front (H9). Usually from day one. | Low. It never blocks a known caller (unknown callers are rejected); turning it off is today's behaviour. It's still in the call path, so it needs the architecture review. |
| **2. Enforcement** | Lower tiers can't starve member chat | Only if G2 passes on the metrics value 1 produced | Higher: it changes who gets served |

**Measurement comes before the decision it informs.** Option 1 and the shadow gateway run together. The shadow gateway shows whether option 1 worked, and whether enforcement is worth it.

### What the spike suggests (synthetic, so the shape matters and the size doesn't)

20 simulated 120-second peaks. Member chats shed out of 579 (the spike's own traffic spec, not included in this repo):

| | Refresh on the live limit | Refresh moved off (option 1) |
| --- | --- | --- |
| No gateway | 109 | **44** |
| Tiered gateway (starter reserves) | 41 | 35 |
| Gateway, claims reserve sized to one chat | 25 | 17, *with Claims sheds rising from 36 to 91 of 228* |
| Member chat alone, no other traffic | 10 | 10 |

**What I'd tell the sponsor from this:**
- "In simulation, the scheduling change does most of the work. On its own it takes member-chat failures from 109 to 44."
- "The gateway's extra benefit after that is real but smaller. Most of it comes from a trade with Claims, which Claims has to agree to."
- "About 10 of those failures are chat's own bursts, and no policy fixes them. That's the quota to buy."

The real numbers come from the client's logs and a shadow run, measured against the thresholds in §4.

---

## 3. Hypotheses: what has to be true for the gateway to be worth building

Each one can come out false, and if it does, the plan changes.

| # | Hypothesis | How we test it | If it's false |
| :---: | --- | --- | --- |
| H1 | Member-chat failures at peak are real and costly | Provider 429 logs by API key from the last open enrollment; the cost-of-a-failed-chat formula, using the client's own numbers | **Stop.** No problem worth solving. |
| H2 | Back-office traffic, not chat itself, causes most of those failures | The same logs: failures by caller and minute, aligned with refresh and claims volume | Skip options 1–3; go straight to sizing quota (option 4) |
| H3 | Option 1 alone doesn't bring member-chat failures under the target | One peak period after moving the refresh | **Stop the gateway.** Keep option 1, and do showback by key under option 2 if finance wants it. |
| H4 | The gateway removes a worthwhile share of what's left after option 1, and does better than option 2 | A shadow run: the gateway counts would-be sheds and enforces nothing | Narrow (option 2 instead), or stop |
| H5 | Claims can afford what protecting chat costs it | Claims sheds in the shadow run, reviewed by the Claims owner | Narrow: use the starter reserves, not the sized floor; or stop |
| H6 | Each caller's tier can come from its identity, not from the request | Platform answer: workload identity, or one key per workload | **Don't enforce.** A spoofable tier isn't a control. |
| H7 | The gateway adds no meaningful delay | Added latency at p99 during the shadow run | Fix it, or put the policy on the client's existing gateway |
| H8 | Finance actually uses the showback | Finance reads spend by department without manual work, at month end | Drop showback from the pitch; it was a nice-to-have |
| H9 | *(Step 8.)* Today's data can't attribute failures or spend to a workload, because every team shares one provider key | Platform lead: how many keys, and does provider reporting break usage and 429s out per key? | Per-workload keys already exist: the shadow gateway's visibility value shrinks to would-sheds and estimate accuracy. Decide on enforcement alone. |

---

## 4. Pre-registered metrics: written down and signed before any data

**The rule:** thresholds are set by the named owner and recorded *before* the baseline or shadow run is measured. If a threshold changes after the data arrives, the change, the reason and who approved it are logged in `decisions.md`. Otherwise "success" just means whatever the data happened to show.

Every metric has a numerator and a denominator. The proposed starting points are mine. **The owner replaces them before the gate.**

| Metric | Definition | Baseline source | Owner | Proposed threshold (owner to confirm) |
| --- | --- | --- | --- | --- |
| **M1** Member-chat failure rate at peak | Chats failed or shed ÷ chats attempted, in peak windows | Last open enrollment's 429 logs by key | Member Services ops manager | Target **T_chat**, from the chat SLA |
| **M2** Share of failures caused by back-office load | Failures in minutes where refresh or claims volume is above normal ÷ all failures | Same logs | Platform lead | Over half means H2 holds |
| **M3** Gateway's extra benefit | (Failures after option 1 − would-be failures with the gateway) ÷ failures after option 1 | Shadow run, after option 1 | Member Services ops manager | Removes at least half of what's left |
| **M4** What it costs Claims | Claims calls shed ÷ claims calls attempted, gateway vs no gateway | Shadow run | Claims ops manager | Within the Claims owner's stated limit |
| **M5** Remaining shortfall | Chat failures with no other traffic competing (chat-only windows, or the burst analysis) | Shadow run | CIO / FinOps | Sizes the quota purchase; no pass/fail |
| **M6** Added latency | p99 gateway decision time | Shadow run | SRE lead | Small next to model latency; the SRE lead sets the number |
| **M7** Showback used | Finance produces spend by department with no manual reconciliation | Month-end close | FinOps lead | Yes or no |
| **M8** Fail-closed holds | Calls with an unknown workload ÷ all calls, plus spoofing attempts caught in the red-team | Shadow run and red-team | CISO | Zero calls admitted with a spoofed tier |
| **M9** *(step 8)* Metrics that didn't exist before | Can the sponsor read M1, M2, M4 and M7 **by workload and department** without manual work? Before the gateway, and with it in shadow mode. | Platform lead (before); shadow run (with) | Sponsor | Yes/no. "No before, yes with" is the visibility value. |

---

## 5. Decision gates: proceed, narrow, or stop at each one

| Gate | When | Proceed if | Narrow if | **Stop if** |
| --- | --- | --- | --- | --- |
| **G0: Is the problem real?** | End of discovery, ~week 2 | H1 and H2 hold | Failures are real but chat causes them itself: go to quota sizing | H1 fails: the failure rate and cost are too small to matter |
| **G1: Was the cheap fix enough?** | After one peak period with option 1 | M1 is still above T_chat | — | **M1 ≤ T_chat. Stop the gateway program.** Report the win as option 1's. |
| **G2: Does the gateway earn its place?** | After the shadow run | M3 and M4 meet their thresholds, M6 is fine, H6 holds | M3 is met but M4 isn't: starter reserves, or option 2 | M3 isn't met, or H6 fails (tier can't be trusted) |
| **G3: Enforce and hand over** | After a period of enforcement | M1 ≤ T_chat holds through peak, and M7 and M8 are met | Keep enforcing for chat only; drop showback | Incidents caused by the gateway itself. Rollback is "policy off", which is today's behaviour. |

**Stopping the wider roadmap.** The arc goes from one workflow, to a shared platform, to reusable IP. It only goes forward if G3 passes *and* a second business unit has the same shape of problem. If G1 stops the gateway, the reusable asset for the FDE practice is the **discovery method and the option ladder**, not the gateway code. Say that, too.

---

## 6. Selling each CxO: the value, the proof, and what would stop it

| Who | Their question | The value we sell | The metric that proves it | What would stop it | Your line |
| --- | --- | --- | --- | --- | --- |
| **Sponsor (CIO or COO)**: go / no-go | "When do I see value, and what's the risk?" | A staged plan where each stage is paid for by the one before | All gates, published | Any stop rule | "You'll see the kill criteria today, and the numbers at every gate, good or bad." |
| **COO / Member Services owner**: owns the P&L | "Will my people's numbers move?" | Member chat holds at peak | M1 against T_chat | G1 passes with the cheap fix, which is good news for them | "You set the target. If moving one job gets us there, that's where we stop." |
| **Claims owner** | "What does this cost my team?" | A trade they choose, shown as numbers | M4 | M4 over their limit | "Protecting chat costs you sheds. You'll see how many before anything is enforced." |
| **CFO / FinOps**: procurement veto | "What does it cost, and what do we get?" | Quota sized from data; showback by department; estimates that show how much capacity is held as padding | M5, M7, M9 | M7 false: drop showback | "Today one bill covers three departments. In shadow mode you'll see who used the peak, and how much of each hold was padding, before you buy anything." |
| **CDO / CAIO**: admits the use case | "Does this even need an agent?" | A deterministic control: fast, explainable, identical on replay | M6, golden cases | — | "No agent, on purpose. The decision runs on every call." |
| **CISO / privacy**: veto | "What's the blast radius?" | One control point; reads no content; metadata-only logs | M8, red-team | H6 fails | "The obvious attack is a caller claiming to be member chat. If we can't tie the tier to identity, I'll recommend not enforcing." |
| **CIO / CTO**: readiness | "Will it hold up, and who runs it?" | Shadow first, a kill switch, rollback = today | M6, G3 incidents | Incidents caused by the gateway | "If the client already runs a gateway, this becomes a policy there, not a new service." |

---

## 7. Transparency cadence: how the CxO hears bad news early

| When | Who hears it | What they get |
| --- | --- | --- |
| Week 1 | Sponsor | This option ladder, the hypotheses, the gates and the stop rules |
| Before each gate | Each metric's owner | Their threshold to sign. Nothing is measured until it's signed. |
| Weekly | Ops forum (named owners, one RACI) | Status against the metrics, including anything trending toward a stop |
| At each gate | Everyone in `stakeholders.md` | The results log below: proceed, narrow or stop, with the numbers and their denominators |
| Any time | Sponsor | A stop rule being hit, the same day, not at the next steering meeting |

**If we stop, the script:**

> "We set out to keep member chat up at peak. Moving the nightly refresh got us under your target, so the gateway isn't worth building. Here are the numbers. What you have now: the cost model, the failure baseline, and a way to size quota. If peak traffic grows past this, the shadow-run design is ready to pick up."

This is the lesson to apply early: hear the people with inconvenient information before the readout, not after.

---

## 8. Results log: filled in after each gate, never edited afterward

| Gate | Date | Metric | Threshold (signed by, date) | Observed (n / N) | Decision | Signed off by |
| --- | --- | --- | --- | --- | --- | --- |
| G0 | 2026-10-18 **SIM, baseline** | M1, M2 | t_chat 5%, m2_min 50% (*proposed*, unsigned) | M1 113/618 = 18.3%; M2 95% | PROCEED | — (hypothetical owners) |
| G1 | 2026-10-18 **SIM, baseline** | M1 | t_chat 5% (*proposed*) | Option 1: 36/618 = 5.8% | PROCEED (by 0.8 points) | — |
| G2 | 2026-10-18 **SIM, baseline** | M3, M4, M6, M8 | m3 ≥ 50%, m4 ≤ 15 pts, p99 ≤ 1 ms, 0 spoofs (*proposed*) | 3a: M3 14%, M4 +3.6. **3b: M3 56%, M4 +22.2.** Option 2: M3 −206%. p99 4 µs; spoofs 0/221 | **NARROW: the Claims owner decides** | — |
| G0 | 2026-10-18 **SIM, waves** | M1, M2 | as above | M1 501/1209 = 41.4%; **M2 37%** | **NARROW: size quota** (option 1 needs ~1.9×) | — |
| G3 | — | M1, M7, M8 | — | Not reachable in simulation | — | — |

Every SIM row comes from `evals/results/2026-10-18_heldout.md`, regenerated from code in steps 9 and 10 with label and reporting changes only; every count and verdict is identical to the step 5 run (`../PROCESS.md`). M6 is wall-clock timing on a laptop and varies between runs (4–8 µs since step 5); the 4 µs above is what step 5 measured.

### What the first results changed

1. **The two traffic mixes disagree, so the client's own logs decide.** If peaks are spill-over (`baseline`), the gateway is a trade-off between Member Services and Claims. If peaks are bursts (`waves`), the gateway barely helps (it removes at most 12% of what's left), and the fix is quota. **The next step is one query on the last open enrollment's logs (M2), not a build.**
2. **The cheapest fix nearly suffices.** Option 1 alone leaves 5.8% against a 5% target. Option 1 plus about 10% more quota meets it with no gateway at all. If Member Services sets T_chat at 6% or higher, G1 stops the gateway program.
3. **Separate limits per workload (option 2) are the worst option.** Splitting the pipe wastes idle capacity: chat fails 17.8% and Claims 67%. Drop it from the ladder unless real demand shows a very different split.
4. **The gateway's value is narrower than the first pass claimed.** It removes at most 56% of what option 1 leaves, and only by costing Claims 22 points. The starter reserves remove 14%. The gateway enforces cheaply (p99 under 10 µs across runs) and safely (0 spoofed admits), but whether it's *worth* enforcing is a business call.

### Amendment, step 8: the value results 1–4 missed

Results 1–4 judged the gateway only as an enforcer. That missed its first value: **the metrics it produces in shadow mode didn't exist before.** Result 1 assumed "one query on the logs" could tell spill-over from bursts. With one shared provider key, it can't. The shadow replay (`evals/results/2026-10-18_heldout_observability.md`, held-out seeds, nothing enforced):

| What the sponsor can see | Today, shared key | Shadow gateway, `baseline` | Shadow gateway, `waves` |
| --- | --- | --- | --- |
| Failures by workload | 1,226 failures (`baseline`), not attributed | chat 113/618, claims 99/221, refresh 1,014/1,162 | chat 501/1,209, claims 133/221, refresh 1,029/1,162 |
| Share of tokens consumed in the peak window, by department | none | Member Services 49%, **Content Ops 30%**, Claims 21% | **Member Services 62%**, Content Ops 25%, Claims 14% |
| Estimate accuracy (actual ÷ estimate) | none | chat 0.87, claims 0.90, refresh 0.86 | similar |
| Would-sheds by tier and reason | none | yes, per call | yes, per call |

**The share of consumed tokens is what tells the two kinds of peak apart.** When the refresh takes 30% of tokens consumed in the peak window, moving it is the lever. When member chat itself takes 62%, the lever is quota. Actual usage comes in 10–14% under the estimate (estimates run 11–16% high), which is capacity held as padding on every call. **So the gateway earns its place first as the measurement instrument (M9), before any enforcement decision.** The step 5 gate verdicts above are unchanged; they're about enforcement.

---

## 9. How to sound

- **Do:** lead with their outcome, then the cheapest option, then what would make you stop.
- **Do:** give every number its denominator, and say "simulated" until it's measured.
- **Do:** treat a stop as a deliverable: "We measured it and it doesn't clear the bar" is the result that earns the next engagement.
- **Don't:** start with the architecture, or sell the gateway before the cheap fix has had its chance.
- **Don't:** move a threshold after seeing the data without logging who approved the change and why.

## 10. Reusing this pattern

- Put the new scenario's facts on paper first: who has the problem, the shared constraint, the options in cost order, and who owns each number. Then tell it at the CxO altitude, with §1–§7 as the template.
- Don't quote this example's numbers. Reuse the shape: **cheapest fix first, pre-registered thresholds, a gate with a stop rule, the remainder sizes the quota.**
- Keep the order of work as evidence (`../PROCESS.md`): define, accept, pre-register, build, measure, decide, report. Fill in §8 only after each gate, and never edit it afterward.
