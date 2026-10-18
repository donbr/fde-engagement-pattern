# Project charter

*Hypothetical client (a regional health insurer, an illustrative example). Written in step 1 of `../PROCESS.md`, before any code. The problem framing carries over from an earlier solution-first spike (not included in this repo). **The first product is different**, because this pass starts from the stakeholders' requirements (`requirements.md`), not from the gateway.*

**Department:** Member Services, at a regional health insurer

**Working title:** Which fix keeps member chat up at peak, at the lowest cost?

---

## The problem

**Who has it?** A **member-service agent** working the AI-assisted chat queue during open enrollment.

**What are they trying to do?** Answer a member's coverage or claims question inside the chat SLA, using the assistant's draft.

**How do they handle it today?**

Three workloads share one provider account and its token limit:
- member chat (live);
- claims summaries (back office);
- a nightly policy refresh, which spills into the morning during open enrollment.

At peak, whichever caller arrives first wins, so member chats fail with 429s. The agent falls back to manual lookup. IT either asks for more quota or asks the batch owner, by hand, to pause.

**What does that cost?**

Measured in discovery with the client's numbers; no figures invented here:

> failed chats per peak hour × extra handle time × loaded agent cost per minute, plus SLA-penalty exposure, plus emergency quota spend.

There's also member experience at plan selection, and the cross-team escalations every open enrollment.

**The problem in one sentence. No solution in it.**

> During open enrollment, member-service agents lose their AI-assisted answers at the moment of highest member demand, because back-office work uses up the shared model capacity first, and nobody can say which department used it.

---

## Success

**What does the new world look like for that person?** At peak the assistant keeps answering. When capacity really is short, the work that waits is back-office work, not a member.

**How would the firm measure it?**

The pre-registered metrics in `cxo-story.md` §4, with thresholds in `evals/thresholds.json`:

| Metric | What it measures |
| --- | --- |
| M1 | Member-chat failure rate at peak, against the owner's target T_chat |
| M2 | Share of failures caused by back-office load |
| M3 | The gateway's benefit on top of the cheapest fix |
| M4 | What protecting chat costs Claims |
| M5 | The shortfall no policy can fix: the quota to buy |
| M6 | Added latency |
| M8 | Spoofed-tier admits |

**Success includes a "stop" verdict.** If the cheapest fix meets T_chat, the program stops, and that counts as success.

**Step 8 amendment:** success also means the sponsor can read failures, peak token share and estimate accuracy **by workload and department** (M9). Today's shared provider key gives none of these. In shadow mode, the gateway's first value is that visibility. Enforcement is a separate decision.

---

## The first product

**Your solution in one sentence.**

> A decision instrument: a replay and shadow-mode gateway that shows the sponsor, from peak traffic, which fix meets the member-chat target at the lowest cost, and enforces priority only if the evidence says it's worth it.

The options it compares, in cost order (`cxo-story.md` §2):

| # | Option |
| :---: | --- |
| 0 | Today |
| 1 | Move the refresh off the live limit |
| 2 | Separate limits per workload |
| 3 | Tiered gateway |
| 4 | Buy quota (sized, not guessed) |

**Input → Output.**

| | |
| --- | --- |
| **In** | Peak traffic: per call, the caller's **authenticated identity**, a request id, a token estimate, and later the actual tokens used. Plus `evals/thresholds.json`: the target and gate thresholds, each with an owner and a status (`proposed` or `signed`). |
| **Out** | *(Step 8 addition)* **Per workload, in shadow mode:** provider failures attributed to it, would-sheds by reason, spend on actual tokens by department, actual ÷ estimate. **Per call**, a decision record: allowed or not, enforced or shadow, workload and tier *from identity*, and a reason (`admitted`, `floor`, `too_large`). Metadata only, never content. **Per run**, for each option: M1–M6 and M8, then a **verdict at each gate**: PROCEED, NARROW, STOP, NOT REACHED or NOT DECIDABLE. Each verdict is labelled with whether its thresholds were signed or only proposed. |

You'd notice it was built wrong if:
- a request body could claim a tier;
- shadow mode ever blocked a call;
- a call that ran in shadow mode wasn't charged;
- a gate gave a verdict without a threshold;
- a "stop" result was presented as a failure.

---

## Decisions made later

See [`decisions.md`](./decisions.md). It's logged during the build, not after.
