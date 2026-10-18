# Process log

The order this work was done in, timestamped when each step finished. The point of the pattern is that definition comes before build, so the order is the evidence. The *Stage* column uses generic stage names, adapted from FDE training material.

**Disclosure:** before this redo, a solution-first spike (not included in this repo) had already run on synthetic seeds 0–19 and 100–119. I had seen those results when I proposed the thresholds in step 3. The held-out seeds for this run (200–219) and the burstier "waves" mix were never run by `evaluate` or inspected before step 5. **Correction (step 10):** the step 4 tests ran seeds 200–204 to check invariants (determinism, identical traffic, partition isolation, spoofing), and one of them computed option 1's quota scale (the G1 quantity) on seeds 200–204. Those tests only asserted invariants; their values were not printed or read. Step 10 moved the invariant tests to seeds 300+. The snapshot tests added in steps 10 and 12 deliberately run the held-out seeds 200–219, after step 5, to pin the published results; they can't influence them.

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
| 9 | Publish | Made a standalone public copy with tactical edits for portability, renamed the "Q1" reserve label to "starter", and regenerated the results files with identical counts and verdicts (only the labels and the M6 timing differ: 4.0 → 4.2 µs `baseline`, 3.7 → 7.6 µs `waves`). `evals/PREREGISTRATION.md` and `data/DATASHEET.md` were also edited in this step, for wording only (the "Q1" label, and paths to the earlier spike); no option, metric, rule, seed or threshold changed. 40 passed. | 2026-10-18 |
| 10 | Review fixes | A pre-publication review (five agents) found five critical and nine important issues. Fixed test-first in `tests/test_review_fixes.py` (42 new checks; red at collection before the fixes): no default recommendation, `t_chat` NOT DECIDABLE, input guards, a threshold loader that rejects bad values, threshold statuses in the saved JSON, test seeds moved to 300+, and a snapshot test of the published results. Results regenerated: identical counts, metrics and verdicts; `recommended` changed from the `option1` fallback to `None` in both mixes; new `thresholds` and `quota_note` fields; M6 timing 4.2 → 4.6 µs and 7.6 → 4.8 µs. Factual and wording fixes in the docs; 5 rows in `decisions.md`. 82 passed. | 2026-10-18 |
| 11 | Publish prep | Removed the training-material code snippet from `use_case/ecosystem.md`; the two mentions now read "adapted from FDE training material". Commit messages rewritten to drop the session URL trailer. File contents of earlier commits were unchanged at this point, which left the training material in commits 0–10; step 12 removed it from the whole history. | 2026-10-18 |
| 12 | Re-run fixes | A re-run of the review found 2 blockers and 6 important issues. Fixed test-first in `tests/test_rerun_fixes.py` (30 new checks; 18 red before the fixes): tier-reserve check, `token_estimate` validation, attribution by identity in `shadow_replay`, threshold units, pickling of `ShedderConfig`, settle-after-release ordering, `allow_nan=False`, plus the rated test gaps (G2 option, refund cap, observability snapshot, end-to-end G2 PROCEED, formulas). Corrected the step 10 claims about seeds, mutation counts (33 of 38) and the evidence of order; "never blocks" now says "a known caller" in 8 places (one is the `why` text of a golden case; its expected values are unchanged). Results unchanged (observe byte-identical; evaluate differs only in M6). Then rewrote the whole history with `git filter-repo --replace-text` to remove the training material from commits 0–10 (the snippet, the course wording, the stub paragraph) and fix the "final published form" note in commit messages. 112 passed. | 2026-10-18 |
| 13 | Publish | Renamed the repo from `fde-mindset` to `fde-engagement-pattern` (`README.md` title, `cxo-story.md` byline); the Python package stays `fde-gateway`. Published to GitHub as a public repository. | 2026-10-18 |

## Evidence of order

**Git history** was reconstructed on 2026-10-18, after step 9, from this log. There is one commit per step, in the order above, and each adds the files *created* in that step. There were no snapshots of intermediate versions, so commits 0–9 hold each file **as it stood at step 9**, not as it was at its own step. For example, the step 4b commit already contains step 8 code (`cancel`, `metrics`). Steps 8d and 8e have no commits, because they only edited files committed earlier. Steps 10–12 are real commits of their own changes. Commit times are when the history was made, not the step times logged above. In step 12 the whole history was rewritten with `git filter-repo` to remove training material from every commit (row 12), so commits 0–10 differ from their step 9 text in exactly those places. Two consequences: the step 4a commit is genuinely red (the tests import modules that don't exist yet), but the step 8a commit is not, because the final `options.py` it builds on already contains `shadow_replay`.

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
