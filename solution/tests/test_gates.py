"""Gate rules from use_case/evals/PREREGISTRATION.md (repo root), one test per rule (R12)."""

import pytest

from fde_gateway.gates import evaluate_gates, load_thresholds

THRESHOLDS = {"t_chat": 0.05, "m2_min": 0.5, "m3_min": 0.5, "m4_max_points": 15, "m6_p99_ms_max": 1.0, "m8_max": 0}
PASS = {"m3": 0.6, "m4_points": 5}
CLAIMS_TOO_COSTLY = {"m3": 0.6, "m4_points": 25}
TOO_SMALL = {"m3": 0.2, "m4_points": 2}


def metrics(**overrides):
    m = {
        "m1_today": 0.19, "m2_backoffice_share": 0.8, "m1_option1": 0.08,
        "candidates": {"option2": TOO_SMALL, "option3a": TOO_SMALL, "option3b": TOO_SMALL},
        "m6_p99_ms": 0.05, "m8_spoof_admits": 0,
    }
    m.update(overrides)
    return m


def verdicts(m, t=THRESHOLDS):
    return {g: v.verdict for g, v in evaluate_gates(m, t).items()}


def test_g0_stops_when_today_already_meets_target():
    assert verdicts(metrics(m1_today=0.03)) == {"G0": "STOP", "G1": "NOT REACHED", "G2": "NOT REACHED"}


def test_g0_narrows_to_quota_when_back_office_is_not_the_cause():
    assert verdicts(metrics(m2_backoffice_share=0.3))["G0"] == "NARROW"


def test_g1_proceeds_when_cheap_fix_falls_short():
    assert verdicts(metrics())["G1"] == "PROCEED"


def test_g2_stops_on_any_spoofed_admit():
    m = metrics(m8_spoof_admits=1, candidates={"option2": TOO_SMALL, "option3a": PASS, "option3b": PASS})
    assert verdicts(m)["G2"] == "STOP"


def test_g2_prefers_option2_when_it_meets_the_same_bar():
    m = metrics(candidates={"option2": PASS, "option3a": PASS, "option3b": PASS})
    result = evaluate_gates(m, THRESHOLDS)["G2"]
    assert result.verdict == "NARROW" and "option2" in result.reason


def test_g2_narrows_when_latency_is_over_budget():
    m = metrics(m6_p99_ms=5.0, candidates={"option2": TOO_SMALL, "option3a": PASS, "option3b": PASS})
    assert verdicts(m)["G2"] == "NARROW"


def test_g2_proceeds_with_3a_before_3b():
    m = metrics(candidates={"option2": TOO_SMALL, "option3a": PASS, "option3b": PASS})
    result = evaluate_gates(m, THRESHOLDS)["G2"]
    assert result.verdict == "PROCEED" and "option3a" in result.reason


def test_g2_proceeds_with_3b_when_only_3b_passes():
    m = metrics(candidates={"option2": TOO_SMALL, "option3a": TOO_SMALL, "option3b": PASS})
    result = evaluate_gates(m, THRESHOLDS)["G2"]
    assert result.verdict == "PROCEED" and "option3b" in result.reason


def test_g2_narrows_when_benefit_is_real_but_claims_pays_too_much():
    m = metrics(candidates={"option2": TOO_SMALL, "option3a": TOO_SMALL, "option3b": CLAIMS_TOO_COSTLY})
    result = evaluate_gates(m, THRESHOLDS)["G2"]
    assert result.verdict == "NARROW" and "Claims" in result.reason


def test_g2_stops_when_benefit_is_too_small():
    assert verdicts(metrics())["G2"] == "STOP"


def test_missing_threshold_is_not_decidable_never_defaulted():
    t = {k: v for k, v in THRESHOLDS.items() if k != "t_chat"}
    assert verdicts(metrics(), t)["G0"] == "NOT DECIDABLE"


def test_missing_threshold_later_only_blocks_that_gate():
    t = {k: v for k, v in THRESHOLDS.items() if k != "m3_min"}
    assert verdicts(metrics(), t) == {"G0": "PROCEED", "G1": "PROCEED", "G2": "NOT DECIDABLE"}


def test_load_thresholds_keeps_owner_status(tmp_path):
    path = tmp_path / "t.json"
    path.write_text('{"t_chat": {"value": 0.05, "owner": "MS", "status": "proposed", "reason": "r"}}')
    values, statuses = load_thresholds(path)
    assert values == {"t_chat": 0.05} and statuses == {"t_chat": "proposed"}


@pytest.mark.parametrize("bad", ["draft", "", None])
def test_load_thresholds_rejects_unknown_status(tmp_path, bad):
    path = tmp_path / "t.json"
    path.write_text('{"t_chat": {"value": 0.05, "owner": "MS", "status": %s, "reason": "r"}}' % ('null' if bad is None else f'"{bad}"'))
    with pytest.raises(ValueError):
        load_thresholds(path)
