"""R15 and R16: the metrics the shadow-mode gateway produces that the provider's logs don't (step 8)."""

import pytest

from fde_gateway.gateway import WORKLOADS, Gateway
from fde_gateway.options import STARTER, shadow_replay
from fde_gateway.shedder import LoadShedder, ShedderConfig
from fde_gateway.traffic import CALLERS, open_enrollment_peak

IDENTITIES = {caller: workload for workload, caller in CALLERS.items()}


@pytest.fixture
def gateway() -> Gateway:
    shedder = LoadShedder(ShedderConfig(1000, 100, STARTER), clock=lambda: 0.0)
    return Gateway({w: shedder for w in WORKLOADS}, IDENTITIES, enforce=False)


def test_r15_metrics_by_workload_include_reasons_and_estimate_accuracy(gateway: Gateway):
    gateway.submit("refresh-job", "r1", 700)     # would-shed: floor
    gateway.submit("chat-frontend", "m1", 200)   # admitted
    gateway.submit("chat-frontend", "m2", 100)   # admitted
    gateway.settle("r1", 650)
    gateway.settle("m1", 240)                    # overrun of 40
    gateway.settle("m2", 80)

    m = gateway.metrics()
    assert m["policy_refresh"] == {
        "department": "Content Operations", "priority": "DEFERRABLE", "calls": 1, "allowed": 1,
        "admitted": 0, "floor": 1, "too_large": 0,
        "settled": 1, "tokens_estimated": 700, "tokens_actual": 650, "overruns": 0,
    }
    assert m["member_chat"]["tokens_estimated"] == 300
    assert m["member_chat"]["tokens_actual"] == 320
    assert m["member_chat"]["overruns"] == 1
    assert m["claims_summary"]["calls"] == 0


def test_r15_unsettled_calls_are_not_in_estimate_accuracy(gateway: Gateway):
    gateway.submit("chat-frontend", "m1", 200)
    assert gateway.metrics()["member_chat"]["settled"] == 0
    assert gateway.metrics()["member_chat"]["tokens_estimated"] == 0


def test_r16_shadow_replay_attributes_provider_failures_by_workload():
    report = shadow_replay(open_enrollment_peak(300, "baseline"), STARTER)
    for w in WORKLOADS:
        p = report["provider"][w]
        assert 0 <= p["failed"] <= p["offered"]
    assert sum(p["failed"] for p in report["provider"].values()) > 0


def test_r16_shadow_never_blocks_so_provider_failures_match_today():
    # in shadow mode the provider sees exactly today's traffic, so failures equal today's sheds
    from fde_gateway.options import OPTIONS, replay
    arrivals = open_enrollment_peak(301, "baseline")
    today = replay(arrivals, OPTIONS["today"])
    shadow = shadow_replay(arrivals, STARTER)
    assert {w: p["failed"] for w, p in shadow["provider"].items()} == today["shed"]


def test_r10_r16_calls_that_failed_at_the_provider_cost_nothing():
    arrivals = open_enrollment_peak(302, "baseline")
    report = shadow_replay(arrivals, STARTER)
    ran = {w: report["provider"][w]["offered"] - report["provider"][w]["failed"] for w in WORKLOADS}
    actual = {w: sum(a.token_actual for a in arrivals if a.workload == w) for w in WORKLOADS}
    assert sum(report["spend"].values()) < sum(actual.values())
    assert all(report["gateway"][w]["settled"] == ran[w] for w in WORKLOADS)
