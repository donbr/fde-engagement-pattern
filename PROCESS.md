# Process log

> [!NOTE]
> **Why this log exists:**
> In Forward Deployed Engineering, **order is the evidence**. A system evaluated after the code is written invites post-hoc rationalization and overfitting.
> 
> This log proves that:
> 1. **Charter & Requirements** were defined before acceptance tests (Steps 0–1).
> 2. **Golden Acceptance Tests & Gate Thresholds** were frozen before any implementation (Steps 2–3).
> 3. **TDD suite failed red** before gateway code existed (Step 4a $\to$ 4b).
> 4. **Held-out counts and verdicts** have remained unchanged since step 5.
> 5. **Filesystem timestamps and git commits** anchor this sequence in verifiable history ([§ Evidence of order](#evidence-of-order)).

The order this work was done in, timestamped when each step finished. The point of the pattern is that definition comes before build, so the order is the evidence.

**Disclosure:** before this redo, a solution-first spike (not included in this repo) had already run on synthetic seeds 0–19 and 100–119. I had seen those results when I proposed the thresholds in step 3. The held-out seeds for this run (200–219) and the burstier "waves" mix were never run by `evaluate` or inspected before step 5. **Correction:** the step 4 tests ran seeds 200–204 to check invariants (determinism, identical traffic, partition isolation, spoofing), and one of them computed option 1's quota scale (the G1 quantity) on seeds 200–204. Those tests only asserted invariants; their values were not printed or read. The invariant tests now use seeds 300+. The snapshot tests run the held-out seeds 200–219 only to pin the saved results; they can't influence them.

## The engagement (steps 0–8)

| Step | Stage | What was done | Finished |
| --- | --- | --- | --- |
| 0 | — | Started the log. `use_case/cxo-story.md` (pitch, hypotheses, metrics, gates) was already written before any implementation. | 2026-10-18T09:39:44-07:00 |
| 1 | Define | `CHARTER.md` (first product: a decision instrument, not the gateway), `requirements.md` (R1–R14, non-goals, anti-goals), `stakeholders.md` and `ecosystem.md` carried over with changes | 2026-10-18T09:40:27-07:00 |
| 2 | Accept | `evals/golden.jsonl`: five stakeholder acceptance cases, expected values worked out by hand from R1, R5, R7, R10 and R12 | 2026-10-18T09:41:58-07:00 |
| 3 | Pre-register | `data/DATASHEET.md` (traffic spec, held-out seeds 200–219, new `waves` mix), `evals/PREREGISTRATION.md` (options, metrics, gate rules), `evals/thresholds.json` (proposed, unsigned) | 2026-10-18T09:41:58-07:00 |
| 4a | TDD red | `solution/tests/`: 33 tests (6 golden, 16 gate-rule, 11 requirement) written against an empty package. Collection fails with `ModuleNotFoundError`, as expected. | 2026-10-18T09:43:01-07:00 |
| 4b | TDD green | `solution/src/fde_gateway/`: `gateway.py` (identity, shadow, kill switch, reasons, showback), `traffic.py`, `options.py`, `gates.py`, `evaluate.py`; `shedder.py` copied unchanged. 35 passed (33 tests and 2 doctests). The golden expectations from step 2 passed on the first implementation, unedited. | 2026-10-18T09:45:19-07:00 |
| 5 | Measure | First run of `evaluate` on held-out seeds 200–219, both mixes. Output saved unedited to `use_case/evals/results/2026-10-18_heldout.{md,json}` | 2026-10-18T09:45:34-07:00 |
| 6 | Decide | `use_case/decisions.md`: 13 decisions, by step, including what was **not** changed after the results | 2026-10-18T09:46:24-07:00 |
| 7 | Report | `use_case/cxo-story.md` §8 results log filled in (SIM rows) with "What the first results changed"; `use_case/readout.md`; `README.md` | 2026-10-18T09:47:29-07:00 |
| 8a | Amendment: requirement + TDD red | Reviewer feedback: *the gateway earns its place by providing metrics that didn't exist before.* Added R15 and R16 to `requirements.md`, then `tests/test_observability.py` (5 tests); red, because `shadow_replay` doesn't exist yet. The first run raced the file write ("file not found"); a rerun confirmed the real red: `ImportError: cannot import name 'shadow_replay'`. | 2026-10-18T09:54:04-07:00 |
| 8b | Amendment: TDD green | `Gateway.metrics()` and `Gateway.cancel()`, `options.shadow_replay()` (shadow gateway in front of today's provider limit), `observe.py`. 40 passed (38 tests and 2 doctests). | 2026-10-18T09:55:12-07:00 |
| 8c | Amendment: run | `observe` on held-out seeds 200–219, both mixes. Descriptive, so no gate or threshold uses it. Saved unedited to `use_case/evals/results/2026-10-18_heldout_observability.md`. The step 5 results are unchanged. | 2026-10-18T09:55:12-07:00 |
| 8d | Amendment: documents | `cxo-story.md` (two values, H9, M9, step 8 results block, CFO line), `readout.md` (rewritten: option 1 + shadow gateway, defer enforcement), `decisions.md` (4 rows), `CHARTER.md`, `README.md`. The step 5 verdicts and results files are unchanged. | 2026-10-18T09:56:54-07:00 |
| 8e | Check | After step 8, a rerun of `evaluate` matches the step 5 output except M6, a wall-clock timing on a laptop: 4.0 → 5.2 µs (`baseline`) and 3.7 → 4.1 µs (`waves`). Every count, metric and verdict is identical. 40 passed. | 2026-10-18T09:57:10-07:00 |

## Evidence of order

**Git history:** the step commits were made after the engagement, from this log. There is one commit per step, in the order above, and each adds the files *created* in that step. Each file is committed as it stood at publication, not as it was at its own step; for example, the step 4b commit already contains step 8 code (`cancel`, `metrics`). Steps 8d and 8e have no commits, because they only edited files committed earlier. Commit times are not the step times; the timing evidence is the file modification times below. Two consequences: the step 4a commit is genuinely red (the tests import modules that don't exist yet), but the step 8a commit is not, because the final `options.py` it builds on already contains `shadow_replay`.

File modification times, oldest first. Regenerated after step 8. The test files predate every module except the copied `shedder.py` and the one-line `__init__.py`. `evaluate.py` and `gates.py` were edited after step 4b (a refactor, plus `Verdict.option`) but before the step 5 run. `use_case/cxo-story.md` was created at 09:34, before step 0; its listed time is the step 8 amendment edit (§8 was first filled in during step 7). The step 8 files (`test_observability.py` before `observe.py`; the edits to `gateway.py` and `options.py` came after the test) appear at the end.

```
2026-10-18 09:40:27  use_case/ecosystem.md
2026-10-18 09:40:27  use_case/stakeholders.md
2026-10-18 09:41:04  use_case/evals/README.md
2026-10-18 09:41:04  use_case/evals/golden.jsonl
2026-10-18 09:41:57  use_case/data/DATASHEET.md
2026-10-18 09:41:58  use_case/evals/PREREGISTRATION.md
2026-10-18 09:41:58  use_case/evals/thresholds.json
2026-10-18 09:42:59  solution/pyproject.toml
2026-10-18 09:42:59  solution/pyrightconfig.json
2026-10-18 09:42:59  solution/src/fde_gateway/__init__.py
2026-10-18 09:42:59  solution/tests/test_gates.py
2026-10-18 09:42:59  solution/tests/test_golden.py
2026-10-18 09:43:00  solution/tests/test_requirements.py
2026-10-18 09:44:44  solution/src/fde_gateway/shedder.py
2026-10-18 09:44:44  solution/src/fde_gateway/traffic.py
2026-10-18 09:45:28  solution/src/fde_gateway/evaluate.py
2026-10-18 09:45:28  solution/src/fde_gateway/gates.py
2026-10-18 09:45:34  use_case/evals/results/2026-10-18_heldout.json
2026-10-18 09:45:34  use_case/evals/results/2026-10-18_heldout.md
2026-10-18 09:54:02  solution/tests/test_observability.py
2026-10-18 09:54:02  use_case/requirements.md
2026-10-18 09:54:45  solution/src/fde_gateway/gateway.py
2026-10-18 09:54:45  solution/src/fde_gateway/options.py
2026-10-18 09:55:03  solution/src/fde_gateway/observe.py
2026-10-18 09:55:12  use_case/evals/results/2026-10-18_heldout_observability.md
2026-10-18 09:55:57  use_case/cxo-story.md
2026-10-18 09:56:54  use_case/CHARTER.md
2026-10-18 09:56:54  use_case/decisions.md
2026-10-18 09:56:54  use_case/readout.md
```
