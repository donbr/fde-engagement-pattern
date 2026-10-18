"""Requirements not covered by a golden case (R4, R6, R8, R11, R13), plus replay invariants."""

import dataclasses

import pytest

from fde_gateway.gateway import WORKLOADS, Decision, Gateway
from fde_gateway.options import OPTIONS, pooled, quota_scale, replay
from fde_gateway.shedder import LoadShedder, ShedderConfig
from fde_gateway.traffic import CALLERS, MIXES, open_enrollment_peak

RESERVES = {"CRITICAL": 0.0, "STANDARD": 0.1, "DEFERRABLE": 0.4}


@pytest.fixture
def gateway() -> Gateway:
    shedder = LoadShedder(ShedderConfig(1000, 100, RESERVES), clock=lambda: 0.0)
    return Gateway({w: shedder for w in WORKLOADS}, CALLERS_BY_ID, enforce=True)


CALLERS_BY_ID = {caller: workload for workload, caller in CALLERS.items()}


def test_r6_decision_record_is_metadata_only():
    fields = {f.name for f in dataclasses.fields(Decision)}
    assert fields == {"request_id", "caller", "workload", "priority", "token_estimate",
                      "allowed", "enforced", "reason", "spoof_attempt"}


def test_r8_counts_by_tier_and_reason(gateway: Gateway):
    gateway.submit("refresh-job", "r1", 700)     # floor
    gateway.submit("chat-frontend", "m1", 1001)  # too_large
    gateway.submit("chat-frontend", "m2", 100)   # admitted
    assert gateway.counts() == {
        "CRITICAL": {"admitted": 1, "floor": 0, "too_large": 1},
        "STANDARD": {"admitted": 0, "floor": 0, "too_large": 0},
        "DEFERRABLE": {"admitted": 0, "floor": 1, "too_large": 0},
    }


def test_unknown_caller_changes_nothing(gateway: Gateway):
    with pytest.raises(PermissionError):
        gateway.submit("laptop-script", "x1", 10)
    assert gateway.log == [] and gateway.unknown_callers == 1


def test_mixes_are_the_preregistered_ones():
    assert set(MIXES) == {"baseline", "waves"}
    assert set(CALLERS) == set(WORKLOADS)


def test_r13_replay_is_deterministic():
    arrivals = open_enrollment_peak(300, "baseline")
    assert replay(arrivals, OPTIONS["option3a"]) == replay(arrivals, OPTIONS["option3a"])
    assert open_enrollment_peak(300, "waves") == open_enrollment_peak(300, "waves")


def test_r4_option1_takes_the_refresh_off_the_live_limit():
    report = replay(open_enrollment_peak(300, "baseline"), OPTIONS["option1"])
    assert report["offered"]["policy_refresh"] == 0
    assert report["batch_lane"]["policy_refresh"] > 0


def test_every_option_sees_the_same_live_chat_and_claims_traffic():
    arrivals = open_enrollment_peak(301, "baseline")
    reports = {name: replay(arrivals, opt) for name, opt in OPTIONS.items() if name != "chat_alone"}
    for w in ("member_chat", "claims_summary"):
        assert len({r["offered"][w] for r in reports.values()}) == 1


def test_option2_partitions_isolate_chat_from_claims():
    # same chat traffic, claims traffic doubled: chat outcome under separate limits must not change
    arrivals = open_enrollment_peak(302, "baseline")
    extra = [dataclasses.replace(a, request_id=a.request_id + "-dup") for a in arrivals if a.workload == "claims_summary"]
    alone = replay(arrivals, OPTIONS["option2"])["shed"]["member_chat"]
    flooded = replay(sorted(arrivals + extra, key=lambda a: a.t), OPTIONS["option2"])["shed"]["member_chat"]
    assert alone == flooded


def test_spoofing_replay_never_decides_a_claims_call_at_critical():
    report = replay(open_enrollment_peak(303, "baseline"), OPTIONS["option3a"], spoof=True)
    assert report["spoof_attempts"] > 0 and report["spoof_critical"] == 0


def test_pooled_rates_have_denominators():
    p = pooled(OPTIONS["today"], range(300, 302), "baseline")
    t = p["member_chat"]
    assert set(t) == {"shed", "offered", "worst"} and t["offered"] > 0


def test_r11_quota_scale_is_the_smallest_that_meets_target():
    scale = quota_scale(OPTIONS["option1"], range(300, 305), "baseline", t_chat=0.05)
    assert scale is None or 1.0 <= scale <= 2.0
    if scale is not None and scale > 1.0:
        below = pooled(OPTIONS["option1"], range(300, 305), "baseline", scale=round(scale - 0.1, 1))["member_chat"]
        assert below["shed"] / below["offered"] > 0.05
