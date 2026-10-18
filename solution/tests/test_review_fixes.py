"""Step 10: one test per pre-publication review finding (see PROCESS.md and use_case/decisions.md)."""

import json
import math
from pathlib import Path

import pytest

from fde_gateway.evaluate import evaluate_mix, recommendation, results_json
from fde_gateway.gates import Verdict, evaluate_gates, load_thresholds
from fde_gateway.gateway import WORKLOADS, Gateway
from fde_gateway.options import HELD_OUT_SEEDS, STARTER
from fde_gateway.shedder import LoadShedder, Request, ShedderConfig
from fde_gateway.traffic import CALLERS, MIXES

IDENTITIES = {caller: workload for workload, caller in CALLERS.items()}
RESULTS = Path(__file__).parents[2] / "use_case" / "evals" / "results" / "2026-10-18_heldout.json"
THRESHOLDS = Path(__file__).parents[2] / "use_case" / "evals" / "thresholds.json"


def make_gateway(enforce: bool = True) -> Gateway:
    shedder = LoadShedder(ShedderConfig(1000, 100, STARTER), clock=lambda: 0.0)
    return Gateway({w: shedder for w in WORKLOADS}, IDENTITIES, enforce=enforce)


# --- Critical 1: no recommendation for an option the gates never reached ---

def test_recommendation_is_none_when_g2_not_reached():
    gates = {"G0": Verdict("NARROW", "size quota"), "G1": Verdict("NOT REACHED", ""), "G2": Verdict("NOT REACHED", "")}
    assert recommendation(gates) is None


def test_recommendation_is_option1_only_when_g1_stops_on_it():
    gates = {"G0": Verdict("PROCEED", ""), "G1": Verdict("STOP", "option 1 meets target"), "G2": Verdict("NOT REACHED", "")}
    assert recommendation(gates) == "option1"


def test_recommendation_follows_g2_option():
    gates = {"G0": Verdict("PROCEED", ""), "G1": Verdict("PROCEED", ""), "G2": Verdict("PROCEED", "", option="option3a")}
    assert recommendation(gates) == "option3a"


def test_recommendation_is_none_when_g2_narrows_without_an_option():
    gates = {"G0": Verdict("PROCEED", ""), "G1": Verdict("PROCEED", ""), "G2": Verdict("NARROW", "Claims decides")}
    assert recommendation(gates) is None


# --- Critical 2: a missing t_chat is NOT DECIDABLE, not a crash ---

def test_missing_t_chat_does_not_crash_evaluate():
    values, _ = load_thresholds(THRESHOLDS)
    values.pop("t_chat")
    ev = evaluate_mix("baseline", range(300, 302), values)
    assert ev["gates"]["G0"].verdict == "NOT DECIDABLE"
    assert ev["quota_scale"] == {} and "t_chat" in ev["quota_note"]


# --- Important: the published numbers are pinned (catches e.g. dropping the x100 on M4) ---

@pytest.fixture(scope="module")
def published():
    return json.loads(RESULTS.read_text())


@pytest.mark.parametrize("mix", list(MIXES))
def test_published_results_reproduce(published, mix):
    values, _ = load_thresholds(THRESHOLDS)
    ev = evaluate_mix(mix, HELD_OUT_SEEDS, values)
    want = published[mix]
    assert ev["results"] == want["results"]
    got_metrics = {k: v for k, v in ev["metrics"].items() if k != "m6_p99_ms"}
    want_metrics = {k: v for k, v in want["metrics"].items() if k != "m6_p99_ms"}
    assert _close(got_metrics, want_metrics)
    assert {g: v.verdict for g, v in ev["gates"].items()} == {g: v["verdict"] for g, v in want["gates"].items()}
    assert ev["recommended"] == want["recommended"]
    assert ev["quota_scale"] == want["quota_scale"]


def _close(a, b) -> bool:
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k]) for k in a)
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)


def test_results_json_keeps_threshold_statuses():
    values, statuses = load_thresholds(THRESHOLDS)
    ev = {"baseline": evaluate_mix("baseline", range(300, 302), values)}
    out = results_json(ev, values, statuses)
    assert out["thresholds"]["t_chat"] == {"value": values["t_chat"], "status": statuses["t_chat"]}
    assert set(out["thresholds"]) == set(values)


# --- Important: request ids can't be reused while a hold is open ---

def test_gateway_rejects_a_request_id_that_is_still_running():
    g = make_gateway()
    g.submit("chat-frontend", "m1", 100)
    with pytest.raises(ValueError, match="already running"):
        g.submit("chat-frontend", "m1", 100)
    assert g.shedders["member_chat"].token_balance == 900
    assert len(g.log) == 1


def test_shedder_rejects_a_request_id_with_an_open_hold():
    s = LoadShedder(ShedderConfig(1000, 100, STARTER), clock=lambda: 0.0)
    s.admit(Request("a", "CRITICAL", 100))
    with pytest.raises(ValueError, match="open hold"):
        s.admit(Request("a", "CRITICAL", 100))
    assert s.token_balance == 900 and s.stats()["CRITICAL"] == {"admitted": 1, "shed": 0}


def test_a_settled_id_can_be_reused():
    g = make_gateway()
    g.submit("chat-frontend", "m1", 100)
    g.settle("m1", 80)
    assert g.submit("chat-frontend", "m1", 100).allowed


# --- Important: settle validates before it changes anything ---

@pytest.mark.parametrize("bad, error", [(None, TypeError), ("80", TypeError), (True, TypeError), (-5, ValueError)])
def test_settle_rejects_bad_token_actual_and_keeps_the_hold(bad, error):
    g = make_gateway()
    g.submit("chat-frontend", "m1", 100)
    with pytest.raises(error):
        g.settle("m1", bad)
    assert "m1" in g.running and g.showback() == {}
    g.settle("m1", 80)
    assert g.showback() == {"Member Services": 80}


@pytest.mark.parametrize("bad, error", [(None, TypeError), (-1, ValueError)])
def test_shedder_release_rejects_bad_token_actual_and_keeps_the_hold(bad, error):
    s = LoadShedder(ShedderConfig(1000, 100, STARTER), clock=lambda: 0.0)
    s.admit(Request("a", "CRITICAL", 100))
    with pytest.raises(error):
        s.release("a", bad)
    assert s.request_ledger == {"a": 100}


# --- Important: the kill switch takes a real boolean ---

@pytest.mark.parametrize("bad", ["false", 0, 1, None])
def test_set_enforce_rejects_non_bool(bad):
    g = make_gateway()
    with pytest.raises(TypeError):
        g.set_enforce(bad)
    assert g.enforce is True


def test_gateway_constructor_rejects_non_bool_enforce():
    with pytest.raises(TypeError):
        Gateway({w: LoadShedder(ShedderConfig(1000, 100, STARTER)) for w in WORKLOADS}, IDENTITIES, enforce="no")  # pyright: ignore[reportArgumentType]  (the wrong type is the point)


# --- Important: the threshold file can't silently disable a rule ---

def _write(tmp_path, text: str) -> Path:
    p = tmp_path / "t.json"
    p.write_text(text)
    return p


ENTRY = '"owner": "o", "status": "proposed", "reason": "r"'


@pytest.mark.parametrize("value", ["NaN", "Infinity", "null", '"0.05"', "true"])
def test_threshold_value_must_be_a_finite_number(tmp_path, value):
    with pytest.raises(ValueError):
        load_thresholds(_write(tmp_path, '{"m8_max": {"value": %s, %s}}' % (value, ENTRY)))


def test_threshold_key_must_be_known(tmp_path):
    with pytest.raises(ValueError, match="unknown threshold"):
        load_thresholds(_write(tmp_path, '{"t_chatt": {"value": 0.05, %s}}' % ENTRY))


def test_threshold_keys_must_not_repeat(tmp_path):
    text = '{"t_chat": {"value": 0.05, %s}, "t_chat": {"value": 0.5, %s}}' % (ENTRY, ENTRY)
    with pytest.raises(ValueError, match="duplicate"):
        load_thresholds(_write(tmp_path, text))


# --- Important: ShedderConfig validates and is really frozen ---

@pytest.mark.parametrize("kwargs", [
    {"token_capacity": 0, "token_refill_per_sec": 100, "reserves": STARTER},
    {"token_capacity": 1000.5, "token_refill_per_sec": 100, "reserves": STARTER},
    {"token_capacity": 1000, "token_refill_per_sec": -1, "reserves": STARTER},
    {"token_capacity": 1000, "token_refill_per_sec": float("nan"), "reserves": STARTER},
    {"token_capacity": 1000, "token_refill_per_sec": 100, "reserves": {"CRITICAL": -0.4}},
    {"token_capacity": 1000, "token_refill_per_sec": 100, "reserves": {"CRITICAL": 1.5}},
    {"token_capacity": 1000, "token_refill_per_sec": 100, "reserves": {}},
])
def test_shedder_config_rejects_bad_policy(kwargs):
    with pytest.raises(ValueError):
        ShedderConfig(**kwargs)


def test_shedder_config_reserves_are_a_private_read_only_copy():
    source = dict(STARTER)
    config = ShedderConfig(1000, 100, source)
    source["CRITICAL"] = 0.9
    assert config.reserves["CRITICAL"] == 0.0
    with pytest.raises(TypeError):
        config.reserves["CRITICAL"] = 0.9  # type: ignore[index]
    assert STARTER["CRITICAL"] == 0.0


# --- Important: every identity's workload has a shedder ---

def test_gateway_rejects_identity_without_a_shedder():
    shedder = LoadShedder(ShedderConfig(1000, 100, STARTER))
    with pytest.raises(ValueError, match="no shedder"):
        Gateway({"member_chat": shedder}, IDENTITIES)


# --- Suggestions: decided behaviour and gaps in coverage ---

def test_unknown_caller_is_rejected_in_shadow_mode_too():
    g = make_gateway(enforce=False)
    with pytest.raises(PermissionError):
        g.submit("laptop-script", "x1", 10)
    assert g.unknown_callers == 1 and g.log == []


def test_cancel_frees_the_hold_and_charges_nothing():
    g = make_gateway()
    g.submit("chat-frontend", "m1", 300)
    g.cancel("m1")
    assert g.shedders["member_chat"].token_balance == 1000
    assert g.showback() == {} and g.metrics()["member_chat"]["settled"] == 0
    with pytest.raises(KeyError):
        g.cancel("m1")


def test_g1_stops_exactly_at_the_target():
    t = {"t_chat": 0.05, "m2_min": 0.5}
    m = {"m1_today": 0.19, "m2_backoffice_share": 0.9, "m1_option1": 0.05}
    assert evaluate_gates(m, t)["G1"].verdict == "STOP"


def test_verdict_option_is_set_only_when_pointing_to_an_option():
    t = {"t_chat": 0.05, "m2_min": 0.5, "m3_min": 0.5, "m4_max_points": 15, "m6_p99_ms_max": 1.0, "m8_max": 0}
    base = {"m1_today": 0.19, "m2_backoffice_share": 0.9, "m1_option1": 0.08, "m6_p99_ms": 0.01, "m8_spoof_admits": 0}
    passing, failing = {"m3": 0.6, "m4_points": 5}, {"m3": 0.1, "m4_points": 1}
    g = evaluate_gates({**base, "candidates": {"option2": passing, "option3a": passing, "option3b": passing}}, t)
    assert g["G2"].option == "option2" and g["G0"].option is None
    g = evaluate_gates({**base, "candidates": {"option2": failing, "option3a": failing, "option3b": failing}}, t)
    assert g["G2"].verdict == "STOP" and g["G2"].option is None
