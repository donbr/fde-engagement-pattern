"""Gate verdicts from pre-registered thresholds (use_case/evals/PREREGISTRATION.md at the repo root, R12).

A missing threshold gives NOT DECIDABLE, never a default. After a gate that
isn't PROCEED, later gates are NOT REACHED.
"""

import dataclasses
import json
import math
from dataclasses import dataclass
from pathlib import Path

STATUSES = ("proposed", "signed")
CANDIDATES = ("option2", "option3a", "option3b")
NEEDS = {
    "G0": ("t_chat", "m2_min"),
    "G1": ("t_chat",),
    "G2": ("m3_min", "m4_max_points", "m6_p99_ms_max", "m8_max"),
}


@dataclass(frozen=True)
class Verdict:
    """One gate's outcome: PROCEED, NARROW, STOP, NOT REACHED or NOT DECIDABLE, and why."""

    verdict: str
    reason: str
    thresholds_used: tuple[str, ...] = ()
    option: str | None = None  # the option a PROCEED or NARROW points to, if any


KNOWN = frozenset(k for keys in NEEDS.values() for k in keys)


def _no_duplicates(pairs: list[tuple[str, object]]) -> dict:
    keys = [k for k, _ in pairs]
    if dupes := sorted({k for k in keys if keys.count(k) > 1}):
        raise ValueError(f"duplicate threshold keys {dupes}")
    return dict(pairs)


def load_thresholds(path: Path) -> tuple[dict[str, float], dict[str, str]]:
    """Read thresholds.json into (values, statuses).

    A key may be absent (its gates report NOT DECIDABLE), but a key that is present
    must be valid: a bad value could otherwise disable a rule silently, e.g.
    ``m8_max: NaN`` makes the spoofing stop rule unable to fire.

    Raises:
        ValueError: A duplicate or unknown key, a value that isn't a finite number,
            or a status that isn't "proposed" or "signed".
    """
    raw = json.loads(Path(path).read_text(), object_pairs_hook=_no_duplicates)
    for key, entry in raw.items():
        if key not in KNOWN:
            raise ValueError(f"unknown threshold {key!r}; expected some of {sorted(KNOWN)}")
        value = entry.get("value")
        if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
            raise ValueError(f"threshold {key!r} must be a finite number, got {value!r}")
        if entry.get("status") not in STATUSES:
            raise ValueError(f"threshold {key!r} has status {entry.get('status')!r}; expected one of {STATUSES}")
    return {k: e["value"] for k, e in raw.items()}, {k: e["status"] for k, e in raw.items()}


def _g0(m: dict, t: dict) -> Verdict:
    if m["m1_today"] <= t["t_chat"]:
        return Verdict("STOP", f"today's chat failure rate {m['m1_today']:.1%} already meets t_chat {t['t_chat']:.0%}")
    if m["m2_backoffice_share"] >= t["m2_min"]:
        return Verdict("PROCEED", f"failures {m['m1_today']:.1%} > t_chat; back office causes {m['m2_backoffice_share']:.0%}")
    return Verdict("NARROW", f"back office causes only {m['m2_backoffice_share']:.0%} of failures: size quota instead")


def _g1(m: dict, t: dict) -> Verdict:
    if m["m1_option1"] <= t["t_chat"]:
        return Verdict("STOP", f"option 1 alone brings chat failures to {m['m1_option1']:.1%} <= t_chat {t['t_chat']:.0%}: stop the gateway program")
    return Verdict("PROCEED", f"option 1 leaves chat failures at {m['m1_option1']:.1%} > t_chat {t['t_chat']:.0%}")


def _g2(m: dict, t: dict) -> Verdict:
    cands = m["candidates"]

    def passes(name: str) -> bool:
        return cands[name]["m3"] >= t["m3_min"] and cands[name]["m4_points"] <= t["m4_max_points"]

    def show(name: str) -> str:
        return f"{name}: M3 {cands[name]['m3']:.0%}, M4 {cands[name]['m4_points']:+.1f} pts"

    if m["m8_spoof_admits"] > t["m8_max"]:
        return Verdict("STOP", f"{m['m8_spoof_admits']} calls were decided at a tier their identity doesn't hold")
    if passes("option2"):
        return Verdict("NARROW", f"option2 (separate limits, no gateway) meets the bar at lower cost; {show('option2')}", option="option2")
    if m["m6_p99_ms"] > t["m6_p99_ms_max"]:
        return Verdict("NARROW", f"decision p99 {m['m6_p99_ms']:.3f} ms over {t['m6_p99_ms_max']} ms: fix, or run as a policy on an existing gateway")
    for name in ("option3a", "option3b"):
        if passes(name):
            return Verdict("PROCEED", f"enforce {name}; {show(name)}", option=name)
    if real := [n for n in CANDIDATES if cands[n]["m3"] >= t["m3_min"]]:
        return Verdict("NARROW", f"benefit is real but Claims pays more than its limit ({'; '.join(show(n) for n in real)}): the Claims owner decides")
    return Verdict("STOP", "gateway benefit too small: " + "; ".join(show(n) for n in CANDIDATES))


RULES = {"G0": _g0, "G1": _g1, "G2": _g2}


def evaluate_gates(metrics: dict, thresholds: dict[str, float]) -> dict[str, Verdict]:
    """Evaluate G0-G2 in order. G3 needs a real enforcement period and isn't simulated."""
    out: dict[str, Verdict] = {}
    reached = True
    for gate, rule in RULES.items():
        if not reached:
            out[gate] = Verdict("NOT REACHED", "an earlier gate did not proceed")
            continue
        if missing := [k for k in NEEDS[gate] if k not in thresholds]:
            out[gate] = Verdict("NOT DECIDABLE", f"threshold(s) not set: {', '.join(missing)}")
        else:
            out[gate] = dataclasses.replace(rule(metrics, thresholds), thresholds_used=NEEDS[gate])
        reached = out[gate].verdict == "PROCEED"
    return out

