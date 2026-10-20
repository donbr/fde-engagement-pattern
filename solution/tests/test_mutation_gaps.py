"""Boundary, edge-case and sensor tests. Each one names the code mutation it catches.

Boundary cases cite use_case/evals/PREREGISTRATION.md.
"""

import dataclasses
import json
import math
from pathlib import Path

import pytest

import fde_gateway.options as options
from fde_gateway.evaluate import evaluate_mix
from fde_gateway.gates import evaluate_gates, load_thresholds
from fde_gateway.gateway import WORKLOADS, Gateway
from fde_gateway.options import OPTIONS, STARTER, quota_scale, replay
from fde_gateway.shedder import LoadShedder, Request, ShedderConfig
from fde_gateway.traffic import CALLERS, open_enrollment_peak

IDENTITIES = {caller: workload for workload, caller in CALLERS.items()}
EVALS = Path(__file__).parents[2] / "use_case" / "evals"
THRESHOLDS = {"t_chat": 0.05, "m2_min": 0.5, "m3_min": 0.5, "m4_max_points": 15, "m6_p99_ms_max": 1.0, "m8_max": 0}
SMALL = {"m3": 0.1, "m4_points": 1}


def metrics(**overrides):
    m = {"m1_today": 0.19, "m2_backoffice_share": 0.9, "m1_option1": 0.08,
         "candidates": {"option2": SMALL, "option3a": SMALL, "option3b": SMALL},
         "m6_p99_ms": 0.01, "m8_spoof_admits": 0}
    m.update(overrides)
    return m


def g2_with_3a(m3, m4, **overrides):
    return metrics(candidates={"option2": SMALL, "option3a": {"m3": m3, "m4_points": m4}, "option3b": SMALL}, **overrides)


def shedder_at(now: list[float], reserves=STARTER) -> LoadShedder:
    return LoadShedder(ShedderConfig(1000, 100, reserves), clock=lambda: now[0])


# --- Gate boundaries: each rule exactly at its threshold and one step past it ---

STEP = 1e-4


@pytest.mark.parametrize("m, gate, want", [
    # PREREGISTRATION G0: STOP if M1 today <= T_chat
    pytest.param(metrics(m1_today=0.05), "G0", "STOP", id="G0-M1-at-T_chat"),
    pytest.param(metrics(m1_today=0.05 + STEP), "G0", "PROCEED", id="G0-M1-over-T_chat"),
    # G0: PROCEED if M2 >= 0.5, else NARROW
    pytest.param(metrics(m2_backoffice_share=0.5), "G0", "PROCEED", id="G0-M2-at-min"),
    pytest.param(metrics(m2_backoffice_share=0.5 - STEP), "G0", "NARROW", id="G0-M2-under-min"),
    # G1: STOP if M1 option 1 <= T_chat
    pytest.param(metrics(m1_option1=0.05), "G1", "STOP", id="G1-M1-at-T_chat"),
    pytest.param(metrics(m1_option1=0.05 + STEP), "G1", "PROCEED", id="G1-M1-over-T_chat"),
    # G2: STOP if M8 > 0
    pytest.param(g2_with_3a(0.6, 5, m8_spoof_admits=0), "G2", "PROCEED", id="G2-M8-at-max"),
    pytest.param(g2_with_3a(0.6, 5, m8_spoof_admits=1), "G2", "STOP", id="G2-M8-over-max"),
    # G2: an option passes if M3 >= 0.5 and M4 <= 15 points
    pytest.param(g2_with_3a(0.5, 15), "G2", "PROCEED", id="G2-M3-M4-at-limits"),
    pytest.param(g2_with_3a(0.5 - STEP, 5), "G2", "STOP", id="G2-M3-under-min"),
    pytest.param(g2_with_3a(0.6, 15 + STEP), "G2", "NARROW", id="G2-M4-over-max"),
    # G2: the benefit is "real" (NARROW, Claims decides) if M3 >= 0.5 even when M4 is over
    pytest.param(g2_with_3a(0.5, 25), "G2", "NARROW", id="G2-real-benefit-at-M3-min"),
    # G2: NARROW if M6 p99 > 1 ms
    pytest.param(g2_with_3a(0.6, 5, m6_p99_ms=1.0), "G2", "PROCEED", id="G2-M6-at-max"),
    pytest.param(g2_with_3a(0.6, 5, m6_p99_ms=1.0 + STEP), "G2", "NARROW", id="G2-M6-over-max"),
])
def test_gate_rule_boundaries_match_the_preregistration(m, gate, want):
    # kills gates.py <=/>= flips on M1, M2, M3, M4, M6 and M8
    assert evaluate_gates(m, THRESHOLDS)[gate].verdict == want


def test_g0_narrow_ends_the_chain():
    # kills gates.py `reached = verdict == "PROCEED"` -> `in ("PROCEED", "NARROW")`
    g = evaluate_gates(metrics(m2_backoffice_share=0.3), THRESHOLDS)
    assert [g[k].verdict for k in ("G0", "G1", "G2")] == ["NARROW", "NOT REACHED", "NOT REACHED"]


def test_quota_scale_accepts_a_rate_exactly_at_target(monkeypatch):
    # kills options.py quota_scale `<= t_chat` -> `< t_chat`
    monkeypatch.setattr(options, "pooled", lambda *a, **k: {"member_chat": {"shed": 5, "offered": 100}})
    assert quota_scale(OPTIONS["option1"], range(1), "baseline", t_chat=0.05) == 1.0


# --- Metrics ---

def test_p99_is_the_99th_percentile():
    # kills evaluate.py `quantiles(...)[98]` -> `[94]`; exclusive method: 101 * 0.99 = 99.99
    from fde_gateway.evaluate import p99

    assert math.isclose(p99([float(x) for x in range(1, 101)]), 99.99)


def test_window_with_no_chat_failures_today_stops_at_g0_instead_of_crashing():
    # seed 109 has no member-chat sheds today, so M2's denominator is zero
    values, _ = load_thresholds(EVALS / "thresholds.json")
    ev = evaluate_mix("baseline", range(109, 110), values)
    assert ev["metrics"]["m1_today"] == 0.0 and ev["metrics"]["m2_backoffice_share"] == 0.0
    assert ev["gates"]["G0"].verdict == "STOP"


def test_m8_sensor_fires_when_a_gateway_trusts_the_claim(monkeypatch):
    # positive control for M8: kills options.py `spoof_critical += ...` -> `+= 0`
    class TrustsTheClaim(Gateway):
        def submit(self, caller, request_id, token_estimate, claimed_workload=None):
            if claimed_workload is None:
                return super().submit(caller, request_id, token_estimate)
            decision = super().submit(CALLERS[claimed_workload], request_id, token_estimate)
            return dataclasses.replace(decision, caller=caller, spoof_attempt=True)

    monkeypatch.setattr(options, "Gateway", TrustsTheClaim)
    report = replay(open_enrollment_peak(303, "baseline"), OPTIONS["option3a"], spoof=True)
    assert report["spoof_critical"] == report["spoof_attempts"] > 0


# --- Shedder edges ---

def test_backwards_clock_adds_nothing():
    # kills shedder.py `max(0.0, now - last)` -> `now - last`
    now = [10.0]
    s = shedder_at(now)
    s.admit(Request("a", "CRITICAL", 500))
    now[0] = 5.0
    s.admit(Request("b", "CRITICAL", 1))
    assert s.token_balance == 499


def test_partial_refill_then_cap():
    now = [0.0]
    s = shedder_at(now)
    s.admit(Request("a", "CRITICAL", 600))
    now[0] = 2.0  # +200
    s.admit(Request("b", "CRITICAL", 1))
    assert s.token_balance == 599
    now[0] = 100.0  # far more than enough to refill
    s.admit(Request("c", "CRITICAL", 1))
    assert s.token_balance == 999


def test_stats_count_a_shed():
    # kills shedder.py `["admitted" if admitted else "shed"]` -> `["admitted"]`
    s = shedder_at([0.0])
    assert s.admit(Request("a", "DEFERRABLE", 700)) is False  # 300 left < floor 400
    assert s.stats()["DEFERRABLE"] == {"admitted": 0, "shed": 1}


def test_overrun_is_charged_and_can_go_negative():
    s = shedder_at([0.0])
    s.admit(Request("a", "CRITICAL", 1000))
    s.release("a", 1100)
    assert s.token_balance == -100


@pytest.mark.parametrize("estimate, reason", [(1000, "floor"), (1001, "too_large")])
def test_estimate_at_capacity_is_a_floor_shed_not_too_large(estimate, reason):
    # kills gateway.py `token_estimate > capacity` -> `>=`; claims (STANDARD) keeps a 10% floor
    shedder = shedder_at([0.0])
    g = Gateway({w: shedder for w in WORKLOADS}, IDENTITIES)
    assert g.submit(CALLERS["claims_summary"], "c1", estimate).reason == reason


# --- Gateway settlement (step 12 fixes that had no test) ---

def test_settle_leaves_the_call_running_when_the_shedder_has_no_hold():
    # kills moving `del self.running[...]` above `shedder.release(...)` in Gateway.settle
    shedder = shedder_at([0.0])
    g = Gateway({w: shedder for w in WORKLOADS}, IDENTITIES)
    g.submit(CALLERS["member_chat"], "m1", 200)
    shedder.release("m1", 0)  # the shedder's hold is gone; the gateway still has the call running
    with pytest.raises(KeyError):
        g.settle("m1", 100)
    assert "m1" in g.running and g.showback() == {}


@pytest.mark.parametrize("actual, overruns", [(100, 0), (101, 1)])
def test_overrun_counts_only_calls_over_the_estimate(actual, overruns):
    # kills gateway.py overruns `>` -> `>=`
    shedder = shedder_at([0.0])
    g = Gateway({w: shedder for w in WORKLOADS}, IDENTITIES)
    g.submit(CALLERS["member_chat"], "m1", 100)
    g.settle("m1", actual)
    assert g.metrics()["member_chat"]["overruns"] == overruns


def test_saved_results_reject_nan(tmp_path):
    # kills dropping allow_nan=False: a NaN would be written as the non-JSON token NaN
    from fde_gateway.evaluate import write_results

    values, statuses = load_thresholds(EVALS / "thresholds.json")
    ev = evaluate_mix("baseline", range(300, 301), values)
    ev["metrics"]["m1_today"] = float("nan")
    out = tmp_path / "r.json"
    with pytest.raises(ValueError):
        write_results(out, {"baseline": ev}, values, statuses)
    assert not out.exists()
    del ev["metrics"]["m1_today"]
    write_results(out, {"baseline": ev}, values, statuses)
    assert "m1_today" not in json.loads(out.read_text())["baseline"]["metrics"]


# --- Threshold file shape ---

def test_threshold_file_must_be_an_object(tmp_path):
    p = tmp_path / "t.json"
    p.write_text("[]")
    with pytest.raises(ValueError, match="object"):
        load_thresholds(p)
