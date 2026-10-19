# Audit this repo in 10 minutes

The repo claims that the order of work is the evidence. Each claim below has a command or file that checks it. Commands run from the repo root and need Python 3.11+, [uv](https://docs.astral.sh/uv/) and a full clone (not `--depth 1`). What you **can't** verify here is listed at the end.

From step 16 on, [CI](./.github/workflows/ci.yml) runs checks 1–4, and 8 from step 17, on every push and pull request.

| # | Claim | Check | What you should see |
| :---: | --- | --- | --- |
| 1 | The code works, and the published results come from it | `cd solution && uv run pytest` | All pass. The `published` snapshot tests (`uv run pytest -k published`) regenerate `use_case/evals/results/` on the held-out seeds and compare them with the saved files. |
| 2 | The evidence files were committed in step order: acceptance cases, thresholds, failing tests, code, held-out results | `python3 scripts/check_history.py` | `PASS  order of evidence files` |
| 3 | The acceptance cases weren't edited to fit the code | Same script; then `git log --oneline -- use_case/evals/golden.jsonl` | `PASS  acceptance cases unchanged`. The log shows step 2, which added them, and step 12, which changed one `why` text and no input or expected output. |
| 4 | No threshold value changed after it was registered, and none is signed yet | Same script; then `grep -c '"proposed"' use_case/evals/thresholds.json` | `PASS  threshold values unchanged`, and `6` (all six still proposed) |
| 5 | The tests were written first, and failed | `git switch --detach "$(git log --format=%h --grep='^Step 4a' -1)"`, then `cd solution && uv run pytest`. Return with `cd .. && git switch -`. | Collection fails with `ModuleNotFoundError` (`fde_gateway.gates`, `fde_gateway.gateway`). The step 4b commit passes 35. |
| 6 | Stopping is a real outcome, not just a word | `cd solution && uv run pytest -k stop` | Six tests where a gate returns STOP, including the golden case `gate_stops_when_cheap_fix_suffices` |
| 7 | The tier comes from identity, and the gateway reads no content (CISO, R5 and R6) | `cd solution && uv run pytest -k "spoof or metadata_only"` | Three tests pass. M8 in the results is `0 / 221` spoofed admits. |
| 8 | Every role named anywhere traces to a planned conversation, starting with the person with the problem | `cd solution && uv run pytest -k stakeholder_trace` | Nine tests pass. They cover requirements, threshold and metric owners, golden cases, the ecosystem's asks and gates, the readout's ask, and the coverage checklist. `use_case/stakeholders.md` shows what each person still owes. |

Checks 2–4 are also a lock going forward: an edit to a case's input or expected output, or to a threshold value, fails CI. Such a change needs a row in [`use_case/decisions.md`](./use_case/decisions.md) and a matching update to `scripts/check_history.py`. Signing a threshold changes only its `status`, so it passes.

## What you can't verify here

- **When steps 0–9 happened.** Their git history was reconstructed after step 9 and rewritten in step 12 ([`PROCESS.md`, "Evidence of order"](./PROCESS.md#evidence-of-order)). Commit order is real; commit times are not the step times. The step times in `PROCESS.md` are self-reported, backed by file modification times listed there. Steps 10 onward are real commits.
- **That the thresholds were set blind.** They weren't fully: I had seen an earlier spike's results on other seeds when I proposed them. The held-out seeds and the `waves` mix were not run before step 5. Disclosed at the top of [`PROCESS.md`](./PROCESS.md).
- **Anything about a real client.** The client is hypothetical, the traffic is synthetic ([`DATASHEET.md`](./use_case/data/DATASHEET.md) says what that can't validate), and the thresholds are proposed, not signed.
- **M6 on your machine.** Decision latency is wall-clock, so it differs from the saved value. The snapshot tests leave it out.
