# fde-engagement-pattern: a forward-deployed engagement pattern, with one worked example

**Forward Deployed Engineering (FDE)** is a consultative practice. A small group of engineers, either inside an organization or serving its clients, embeds with a business owner. Together they define the problem, prove a fix against numbers agreed in advance, and hand it over so it runs without them. The practice is older than AI engineering: it grew out of field engineering, solutions engineering and internal consulting groups. AI workloads raise the cost of building before measuring, but the discipline is the same.

This repo packages that practice as a reusable pattern: **define → accept → pre-register → build (tests first) → measure → decide → report.** The worked example is a load-shedding gateway, which does priority-based admission control in front of a shared LLM rate limit. The pattern is the files and the order they were written in, not the gateway. See [`PROCESS.md`](./PROCESS.md) for the timestamped order of work, and [Reusing this pattern](#reusing-this-pattern) to apply it to your own use case.

An earlier solution-first spike (not included in this repo) is the comparison point; see [What changed from the first pass](#what-changed-from-the-first-pass).

The client is **hypothetical** (a regional health insurer) and the traffic is **synthetic**. Thresholds are **proposed**, for owners to sign.

## Layout

| Path | What |
| --- | --- |
| [`use_case/cxo-story.md`](./use_case/cxo-story.md) | The pitch, hypotheses, pre-registered metrics, gates with stop rules, and the **results log** |
| [`use_case/CHARTER.md`](./use_case/CHARTER.md) | Problem, success, first product: **a decision instrument** |
| [`use_case/requirements.md`](./use_case/requirements.md) | R1–R16 traced to stakeholder roles (R15 and R16 added in step 8), plus non-goals and anti-goals |
| [`use_case/stakeholders.md`](./use_case/stakeholders.md), [`ecosystem.md`](./use_case/ecosystem.md) | Carried over from the first pass, with changes |
| [`use_case/evals/`](./use_case/evals/) | Five acceptance cases, `PREREGISTRATION.md`, `thresholds.json`, `results/` |
| [`use_case/data/DATASHEET.md`](./use_case/data/DATASHEET.md) | Traffic spec, held-out seeds, what it can't validate |
| [`use_case/decisions.md`](./use_case/decisions.md) | 27 decisions by step, including what was **not** changed after the results, and the step 8 amendment |
| [`use_case/readout.md`](./use_case/readout.md) | The report: headline, what it does, numbers, cost, running it for real, risks, recommendation, handover, and the ask |
| [`solution/`](./solution/) | `fde_gateway`: shedder core, identity-aware shadow-mode gateway, options replay, gates, evaluation |

Needs Python 3.11+ and [uv](https://docs.astral.sh/uv/). From the repo root:

```bash
cd solution
uv run pytest                                # 82 checks
uv run python -m fde_gateway.evaluate        # prints options and gates (saved copy: use_case/evals/results/2026-10-18_heldout.md)
uv run python -m fde_gateway.observe         # prints shadow metrics (saved copy: use_case/evals/results/2026-10-18_heldout_observability.md)
```

## What changed from the first pass

| | First pass (earlier spike, not included) | This pass |
| --- | --- | --- |
| **Order** | Build, run, tune, then write the charter and decisions | Charter → requirements → acceptance cases → pre-registration → failing tests → build → one held-out run → decisions → readout |
| **Nature of the product** | A tiered gateway | A **decision instrument** that compares five fixes in cost order, plus a gateway whose **first value is visibility** (shadow mode) and whose second, optional value is enforcement |
| **Complexity** | Shedder + department tags + replay | Adds identity-derived tiers, shadow mode, a kill switch, reason codes, provider failures attributed by workload, estimate accuracy, separate-limits and batch-lane options, quota sizing, and gate rules that give NOT DECIDABLE without a threshold |
| **Golden cases** | Read off the implementation | Worked out by hand from stakeholder requirements before code; passed on the first implementation, unedited |
| **Thresholds** | "< 5%" written after seeing 4.3% | Written before the held-out run; labelled *proposed*; none changed afterward |
| **Headline** | "Tiering cut member-chat failures from 19% to 4%" | "Moving one job cuts them from 18.3% to 5.8% with no new software. An observe-only gateway gives you numbers you don't have today, and those decide whether enforcing priority is ever worth it." |
| **Recommendation** | Proceed, narrowed (build and shadow-run the gateway) | Option 1 **plus the shadow gateway** for visibility; **defer enforcement** until real token shares and signed thresholds exist (step 8; step 7 had said "don't fund the gateway yet") |
| **Value** | Shows the mechanism works | Shows which fix is worth paying for, when to stop, and why the CxO can trust the answer. And it creates the metrics (attributed failures, peak share, estimate accuracy) that make those decisions possible on real traffic. |

## For the CxO conversation

Lead with `use_case/cxo-story.md` §1 and §2, then the results in §8. **The line to repeat:**

> "The cheapest fix gets most of the way. The gateway's first job is to show you numbers you don't have today: whose calls fail, who uses the peak, how far off the estimates are. Those numbers decide whether it should ever enforce anything, and I'll show you the answer either way."

## Reusing this pattern

Replace the example in the order it was written. Each file feeds the next one.

| Order | Stage | Replace | What it must say before you move on |
| :---: | --- | --- | --- |
| 0 | Pitch | `use_case/cxo-story.md` §1–§7 | The outcome, the options in cost order, hypotheses that can come out false, metrics, and gates with stop rules. Written before any implementation. |
| 1 | Define | `use_case/CHARTER.md`, `stakeholders.md`, `requirements.md` | The problem in one sentence with no solution in it, who owns each number, and requirements traced to roles |
| 2 | Accept | `use_case/evals/golden.jsonl` | A handful of acceptance cases, with expected values worked out by hand from the requirements |
| 3 | Pre-register | `use_case/evals/PREREGISTRATION.md`, `thresholds.json`, `use_case/data/DATASHEET.md` | Metrics with denominators, gate rules and held-out data. Thresholds stay marked *proposed* until an owner signs them. |
| 4 | Build | `solution/tests/`, then `solution/src/` | Tests fail before the code exists and pass after it. Golden cases are not edited to fit the code. |
| 5 | Measure | `use_case/evals/results/` | One held-out run; regenerated in steps 9–10 with identical counts and verdicts |
| 6 | Decide | `use_case/decisions.md`, `cxo-story.md` §8 | A verdict at each gate, and what was *not* changed after the results |
| 7 | Report | `use_case/readout.md` | The eight-part readout and the ask |

Log each step with a timestamp in `PROCESS.md`. The order is the evidence.

- Reuse the shape, not these numbers: cheapest fix first, thresholds set before the data, gates with stop rules, and whatever is left over sizes the spend.
- A stop verdict is a deliverable. Tell the sponsor that in the first meeting.

## License

MIT. See [`LICENSE`](./LICENSE).
