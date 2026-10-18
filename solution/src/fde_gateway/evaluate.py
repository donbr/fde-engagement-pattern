"""Run the pre-registered evaluation and print the evidence and the gate verdicts.

Run (from solution/):
    uv run python -m fde_gateway.evaluate                 # held-out seeds 200-219, both mixes
    uv run python -m fde_gateway.evaluate --out results.json
"""

import argparse
import json
import statistics
from pathlib import Path

from fde_gateway.gates import CANDIDATES, Verdict, evaluate_gates, load_thresholds
from fde_gateway.options import HELD_OUT_SEEDS, OPTIONS, pooled, quota_scale, replay
from fde_gateway.traffic import MIXES, open_enrollment_peak

THRESHOLDS = Path(__file__).parents[3] / "use_case" / "evals" / "thresholds.json"


def _rate(t: dict) -> float:
    return t["shed"] / t["offered"]


def evaluate_mix(mix: str, seeds: range, thresholds: dict[str, float]) -> dict:
    """All options, M1-M8 and the gate verdicts for one mix."""
    results = {name: pooled(opt, seeds, mix) for name, opt in OPTIONS.items()}
    chat = {name: r["member_chat"] for name, r in results.items()}
    claims_rate = {name: _rate(r["claims_summary"]) for name, r in results.items() if "claims_summary" in r}

    timings: list[float] = []
    spoof_critical = spoof_attempts = 0
    for seed in seeds:
        arrivals = open_enrollment_peak(seed, mix)
        for name in ("option3a", "option3b"):
            replay(arrivals, OPTIONS[name], timings_ms=timings)
        spoofed = replay(arrivals, OPTIONS["option3a"], spoof=True)
        spoof_critical += spoofed["spoof_critical"]
        spoof_attempts += spoofed["spoof_attempts"]

    fails_option1 = chat["option1"]["shed"]
    metrics = {
        "m1_today": _rate(chat["today"]),
        "m2_backoffice_share": (chat["today"]["shed"] - chat["chat_alone"]["shed"]) / chat["today"]["shed"],
        "m1_option1": _rate(chat["option1"]),
        "candidates": {
            n: {"m3": (fails_option1 - chat[n]["shed"]) / fails_option1 if fails_option1 else 0.0,
                "m4_points": (claims_rate[n] - claims_rate["option1"]) * 100}
            for n in CANDIDATES
        },
        "m5_chat_alone": _rate(chat["chat_alone"]),
        "m6_p99_ms": statistics.quantiles(timings, n=100)[98],
        "m8_spoof_admits": spoof_critical,
        "m8_spoof_attempts": spoof_attempts,
    }
    gates = evaluate_gates(metrics, thresholds)

    recommended = recommendation(gates)
    if "t_chat" in thresholds:
        sized = ("option1", recommended) if recommended else ("option1",)
        quota = {n: quota_scale(OPTIONS[n], seeds, mix, thresholds["t_chat"]) for n in dict.fromkeys(sized)}
        quota_note = ""
    else:
        quota, quota_note = {}, "NOT DECIDABLE: threshold t_chat not set"
    return {"results": results, "metrics": metrics, "gates": gates, "recommended": recommended,
            "quota_scale": quota, "quota_note": quota_note}


def recommendation(gates: dict[str, Verdict]) -> str | None:
    """The option the gates point to, or None when they don't point to one.

    G2's option when it names one; option1 when G1 stops on it (the cheap fix meets
    the target); otherwise None. There is no default: a gate that never ran
    recommends nothing (step 10).
    """
    if gates["G2"].option:
        return gates["G2"].option
    if gates["G1"].verdict == "STOP":
        return "option1"
    return None


def results_json(evaluations: dict[str, dict], values: dict[str, float], statuses: dict[str, str]) -> dict:
    """The saved results: thresholds with their status (PREREGISTRATION.md), then each mix."""
    return {
        "thresholds": {k: {"value": v, "status": statuses[k]} for k, v in values.items()},
        **{mix: {"metrics": ev["metrics"], "recommended": ev["recommended"], "quota_scale": ev["quota_scale"],
                 "quota_note": ev["quota_note"],
                 "gates": {g: {"verdict": v.verdict, "reason": v.reason} for g, v in ev["gates"].items()},
                 "results": ev["results"]}
           for mix, ev in evaluations.items()},
    }


def _cell(t: dict | None) -> str:
    return "—" if t is None else f"{t['shed']}/{t['offered']} = {_rate(t):.1%} (worst {t['worst']:.0%})"


def report(mix: str, ev: dict, statuses: dict[str, str]) -> str:
    lines = [f"### Mix `{mix}`", "", "| Option | Member chats shed | Claims shed |", "|---|---|---|"]
    for name, opt in OPTIONS.items():
        r = ev["results"][name]
        lines.append(f"| `{name}`: {opt.description} | {_cell(r.get('member_chat'))} | {_cell(r.get('claims_summary'))} |")
    m = ev["metrics"]
    lines += ["", "| Metric | Value |", "|---|---|",
              f"| M1 today / option 1 | {m['m1_today']:.1%} / {m['m1_option1']:.1%} |",
              f"| M2 back-office share of today's chat failures | {m['m2_backoffice_share']:.0%} |"]
    for n, c in m["candidates"].items():
        lines.append(f"| M3 / M4 `{n}` | {c['m3']:.0%} of option-1 failures removed / {c['m4_points']:+.1f} pts claims sheds |")
    q = ", ".join(f"`{n}` {s if s is not None else '> 2.0'}x" for n, s in ev["quota_scale"].items()) or ev["quota_note"]
    lines += [f"| M5 chat alone; quota scale to reach t_chat | {m['m5_chat_alone']:.1%}; {q} |",
              f"| M6 decision p99 | {m['m6_p99_ms'] * 1000:.1f} µs |",
              f"| M8 spoofed admits / attempts | {m['m8_spoof_admits']} / {m['m8_spoof_attempts']} |",
              "", "| Gate | Verdict | Why | Thresholds |", "|---|---|---|---|"]
    for gate, v in ev["gates"].items():
        used = ", ".join(f"{k} ({statuses.get(k, 'missing')})" for k in v.thresholds_used) or "—"
        lines.append(f"| {gate} | **{v.verdict}** | {v.reason} | {used} |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the pre-registered evaluation.")
    parser.add_argument("--thresholds", type=Path, default=THRESHOLDS)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    values, statuses = load_thresholds(args.thresholds)
    seeds = HELD_OUT_SEEDS
    print(f"Held-out seeds {seeds.start}-{seeds.stop - 1}. Thresholds: "
          + ", ".join(f"{k}={v} ({statuses[k]})" for k, v in values.items()) + "\n")
    evaluations = {mix: evaluate_mix(mix, seeds, values) for mix in MIXES}
    for mix, ev in evaluations.items():
        print(report(mix, ev, statuses) + "\n")

    if args.out:
        args.out.write_text(json.dumps(results_json(evaluations, values, statuses), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
