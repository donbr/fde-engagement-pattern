"""Step 12: findings from the pre-publication re-run, plus the test gaps it rated highest."""

import copy
import math
import pickle
from pathlib import Path

import pytest

from fde_gateway.evaluate import evaluate_mix
from fde_gateway.gates import evaluate_gates, load_thresholds
from fde_gateway.gateway import WORKLOADS, Gateway
from fde_gateway.observe import observe, report
from fde_gateway.options import HELD_OUT_SEEDS, STARTER, shadow_replay
from fde_gateway.shedder import LoadShedder, Request, ShedderConfig
from fde_gateway.traffic import CALLERS, MIXES, open_enrollment_peak
from test_audit import section

IDENTITIES = {caller: workload for workload, caller in CALLERS.items()}
EVALS = Path(__file__).parents[2] / "use_case" / "evals"


def shared_gateway(enforce: bool = True, clock=lambda: 0.0) -> Gateway:
    shedder = LoadShedder(ShedderConfig(1000, 100, STARTER), clock=clock)
    return Gateway({w: shedder for w in WORKLOADS}, IDENTITIES, enforce=enforce)


# --- Important: a known caller can't hit a missing reserve (R7) ---

def test_gateway_rejects_a_shedder_without_a_reserve_for_the_workloads_tier():
    critical_only = LoadShedder(ShedderConfig(1000, 100, {"CRITICAL": 0.0}))
    with pytest.raises(ValueError, match="no reserve"):
        Gateway({w: critical_only for w in WORKLOADS}, IDENTITIES, enforce=False)


# --- Important: token_estimate is validated before anything is recorded ---

@pytest.mark.parametrize("bad, error", [
    (0, ValueError), (-1, ValueError), (float("nan"), TypeError), (10.5, TypeError), (True, TypeError), (None, TypeError),
])
@pytest.mark.parametrize("enforce", [True, False])
def test_submit_rejects_bad_token_estimate_before_recording(bad, error, enforce):
    g = shared_gateway(enforce)
    with pytest.raises(error):
        g.submit("chat-frontend", "m1", bad)
    assert g.log == [] and g.running == {}
    assert g.metrics()["member_chat"]["calls"] == 0
    assert g.shedders["member_chat"].stats()["CRITICAL"] == {"admitted": 0, "shed": 0}


def test_shedder_rejects_non_int_token_estimate():
    s = LoadShedder(ShedderConfig(1000, 100, STARTER), clock=lambda: 0.0)
    with pytest.raises(TypeError):
        s.admit(Request("a", "CRITICAL", float("nan")))  # pyright: ignore[reportArgumentType]
    assert s.token_balance == 1000


# --- Important: shadow_replay attributes provider failures by identity ---

def test_shadow_replay_attributes_by_caller_identity_not_ground_truth():
    # claims traffic arrives through the chat front end's identity, so it is attributed to member_chat
    callers = {"member_chat": "chat-frontend", "claims_summary": "chat-frontend", "policy_refresh": "refresh-job"}
    identities = {"chat-frontend": "member_chat", "refresh-job": "policy_refresh"}
    arrivals = open_enrollment_peak(300, "baseline")
    rep = shadow_replay(arrivals, STARTER, callers=callers, identities=identities)
    chat_and_claims = sum(a.workload in ("member_chat", "claims_summary") for a in arrivals)
    assert rep["provider"]["claims_summary"]["offered"] == 0
    assert rep["provider"]["member_chat"]["offered"] == chat_and_claims


# --- Important: thresholds in the wrong units or shape are rejected ---

ENTRY = '"owner": "o", "status": "proposed", "reason": "r"'


@pytest.mark.parametrize("key, value", [
    ("t_chat", 5), ("m2_min", 1.5), ("m3_min", -0.1), ("m4_max_points", 150), ("m6_p99_ms_max", -1), ("m8_max", -1), ("m8_max", 0.5),
])
def test_threshold_out_of_range_is_rejected(tmp_path, key, value):
    p = tmp_path / "t.json"
    p.write_text('{"%s": {"value": %s, %s}}' % (key, value, ENTRY))
    with pytest.raises(ValueError, match="range|whole"):
        load_thresholds(p)


def test_threshold_entry_must_be_an_object(tmp_path):
    p = tmp_path / "t.json"
    p.write_text('{"t_chat": 0.05}')
    with pytest.raises(ValueError, match="object"):
        load_thresholds(p)


# --- Suggestions rated highest by the re-run ---

def test_g2_proceed_carries_the_option():
    t = {"t_chat": 0.05, "m2_min": 0.5, "m3_min": 0.5, "m4_max_points": 15, "m6_p99_ms_max": 1.0, "m8_max": 0}
    m = {"m1_today": 0.19, "m2_backoffice_share": 0.9, "m1_option1": 0.08, "m6_p99_ms": 0.01, "m8_spoof_admits": 0,
         "candidates": {"option2": {"m3": 0.1, "m4_points": 1}, "option3a": {"m3": 0.1, "m4_points": 1},
                        "option3b": {"m3": 0.6, "m4_points": 5}}}
    g2 = evaluate_gates(m, t)["G2"]
    assert (g2.verdict, g2.option) == ("PROCEED", "option3b")


def test_refund_is_capped_at_capacity():
    now = [0.0]
    s = LoadShedder(ShedderConfig(1000, 100, STARTER), clock=lambda: now[0])
    s.admit(Request("a", "CRITICAL", 100))
    now[0] = 10.0  # refill back to capacity
    s.release("a", 0)
    assert s.token_balance == 1000


@pytest.mark.parametrize("mix", list(MIXES))
def test_published_observability_output_reproduces(mix):
    published = (EVALS / "results" / "2026-10-18_heldout_observability.md").read_text()
    assert report(mix, observe(mix, HELD_OUT_SEEDS)) == section(published, mix)


def test_end_to_end_g2_proceed_sizes_quota_for_the_recommended_option():
    # with the Claims limit raised to 25 points, 3b passes on baseline and becomes the recommendation
    values, _ = load_thresholds(EVALS / "thresholds.json")
    ev = evaluate_mix("baseline", HELD_OUT_SEEDS, {**values, "m4_max_points": 25})
    assert (ev["gates"]["G2"].verdict, ev["recommended"]) == ("PROCEED", "option3b")
    assert set(ev["quota_scale"]) == {"option1", "option3b"} and ev["quota_scale"]["option3b"] == 1.0


def test_shedder_config_survives_pickle_and_deepcopy():
    config = ShedderConfig(1000, 100, STARTER)
    # Safe: round-trips an object this test just built; nothing untrusted is unpickled.
    for clone in (pickle.loads(pickle.dumps(config)), copy.deepcopy(config)):
        assert clone == config and clone.reserves["DEFERRABLE"] == 0.4
        with pytest.raises(TypeError):
            clone.reserves["CRITICAL"] = 0.9  # type: ignore[index]


def test_formulas_independently_of_the_snapshot():
    # M3 and M4 by hand from the baseline counts: option1 sheds 36 chats and 49/221 claims; 3b sheds 16 and 98/221
    values, _ = load_thresholds(EVALS / "thresholds.json")
    m = evaluate_mix("baseline", HELD_OUT_SEEDS, values)["metrics"]
    assert math.isclose(m["candidates"]["option3b"]["m3"], (36 - 16) / 36)
    assert math.isclose(m["candidates"]["option3b"]["m4_points"], (98 - 49) / 221 * 100)
    assert math.isclose(m["m2_backoffice_share"], (113 - 6) / 113)
