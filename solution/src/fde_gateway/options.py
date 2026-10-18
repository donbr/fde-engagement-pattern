"""The options from use_case/evals/PREREGISTRATION.md (repo root), and the replay that runs them.

Every option runs through the same Gateway and LoadShedder. Options differ only
in what is configured:
- which workloads leave the live limit (option 1's batch lane);
- whether limits are shared or separate (option 2);
- the reserves (options 3a and 3b).

``shadow_replay`` (step 8) runs today's traffic through a shadow-mode gateway in
front of today's shared provider limit, to produce the metrics in R15 and R16.
"""

import heapq
import itertools
import time
from dataclasses import dataclass, field

from fde_gateway.gateway import WORKLOADS, Gateway
from fde_gateway.shedder import LoadShedder, Request, ShedderConfig
from fde_gateway.traffic import CALLERS, Arrival, open_enrollment_peak

TOKEN_CAPACITY = 1000
TOKEN_REFILL_PER_SEC = 100
CALL_LATENCY_SEC = 2.0
HELD_OUT_SEEDS = range(200, 220)
QUOTA_SCALES = tuple(round(1.0 + 0.1 * i, 1) for i in range(11))  # 1.0 ... 2.0

ZERO = {"CRITICAL": 0.0, "STANDARD": 0.0, "DEFERRABLE": 0.0}
STARTER = {"CRITICAL": 0.0, "STANDARD": 0.10, "DEFERRABLE": 0.40}
SIZED = {"CRITICAL": 0.0, "STANDARD": 0.35, "DEFERRABLE": 0.40}
REFRESH = frozenset({"policy_refresh"})


@dataclass(frozen=True)
class Option:
    """One way to run the peak.

    Attributes:
        reserves: Floors per tier, as in ShedderConfig.
        off_live: Workloads moved to the batch lane, off the live limit.
        dropped: Workloads left out of the run entirely (only for chat_alone).
        partitions: Workload -> (capacity, refill per sec) for separate limits;
            None means one shared limit.
    """

    description: str
    reserves: dict[str, float]
    off_live: frozenset[str] = frozenset()
    dropped: frozenset[str] = frozenset()
    partitions: dict[str, tuple[int, float]] | None = field(default=None)


OPTIONS: dict[str, Option] = {
    "today": Option("one shared limit, first come first served", ZERO),
    "option1": Option("refresh moved to the batch lane", ZERO, off_live=REFRESH),
    "option2": Option("option 1 + separate limits (chat 60%, claims 40%)", ZERO, off_live=REFRESH,
                      partitions={"member_chat": (600, 60.0), "claims_summary": (400, 40.0)}),
    "option3a": Option("option 1 + tiered gateway, starter reserves", STARTER, off_live=REFRESH),
    "option3b": Option("option 1 + tiered gateway, claims floor = one chat", SIZED, off_live=REFRESH),
    "chat_alone": Option("member chat only", ZERO, dropped=frozenset({"claims_summary", "policy_refresh"})),
}


def _shedders(option: Option, scale: float, clock) -> dict[str, LoadShedder]:
    def make(capacity: float, refill: float) -> LoadShedder:
        return LoadShedder(ShedderConfig(round(capacity * scale), refill * scale, option.reserves), clock=clock)

    if option.partitions:
        return {w: make(c, r) for w, (c, r) in option.partitions.items()}
    shared = make(TOKEN_CAPACITY, TOKEN_REFILL_PER_SEC)
    return {w: shared for w in WORKLOADS}


def replay(arrivals: list[Arrival], option: Option, scale: float = 1.0, spoof: bool = False,
           timings_ms: list[float] | None = None) -> dict:
    """Run one window through an enforcing gateway on a simulated clock.

    Args:
        scale: Multiplier on capacity and refill (quota sizing, M5).
        spoof: Every claims call also claims ``member_chat`` (M8).
        timings_ms: If given, each submit's wall time is appended (M6). Kept out of
            the return value so replays stay deterministic.

    Returns:
        offered, shed and batch_lane per workload; spend per department; counts by
        tier and reason; spoof_attempts and spoof_critical.
    """
    now = [0.0]
    live = {c: w for w, c in CALLERS.items() if w not in option.off_live | option.dropped}  # only callers that reach the live gateway
    gateway = Gateway(_shedders(option, scale, lambda: now[0]), live)
    offered = {w: 0 for w in WORKLOADS}
    shed = {w: 0 for w in WORKLOADS}
    batch_lane = {w: 0 for w in WORKLOADS}
    spoof_attempts = spoof_critical = 0

    seq = itertools.count()
    events = [(a.t, next(seq), "arrive", a) for a in arrivals if a.workload not in option.dropped]
    heapq.heapify(events)
    while events:
        now[0], _, kind, a = heapq.heappop(events)
        if kind == "settle":
            gateway.settle(a.request_id, a.token_actual)
            continue
        if a.workload in option.off_live:
            batch_lane[a.workload] += 1
            continue
        offered[a.workload] += 1
        claimed = "member_chat" if spoof and a.workload == "claims_summary" else None
        start = time.perf_counter()
        decision = gateway.submit(CALLERS[a.workload], a.request_id, a.token_estimate, claimed)
        if timings_ms is not None:
            timings_ms.append((time.perf_counter() - start) * 1000)
        if decision.spoof_attempt:
            spoof_attempts += 1
            spoof_critical += decision.priority == "CRITICAL"
        if decision.allowed:
            heapq.heappush(events, (now[0] + CALL_LATENCY_SEC, next(seq), "settle", a))
        else:
            shed[a.workload] += 1

    return {"offered": offered, "shed": shed, "batch_lane": batch_lane, "spend": gateway.showback(),
            "counts": gateway.counts(), "spoof_attempts": spoof_attempts, "spoof_critical": spoof_critical}


def pooled(option: Option, seeds: range, mix: str, scale: float = 1.0) -> dict[str, dict[str, float]]:
    """Shed and offered counts pooled over seeds, plus the worst window, for each workload that ran live."""
    totals = {w: {"shed": 0, "offered": 0, "worst": 0.0} for w in WORKLOADS}
    for seed in seeds:
        report = replay(open_enrollment_peak(seed, mix), option, scale)
        for w, t in totals.items():
            if report["offered"][w]:
                t["shed"] += report["shed"][w]
                t["offered"] += report["offered"][w]
                t["worst"] = max(t["worst"], report["shed"][w] / report["offered"][w])
    return {w: t for w, t in totals.items() if t["offered"]}


def quota_scale(option: Option, seeds: range, mix: str, t_chat: float) -> float | None:
    """Smallest quota multiplier (1.0-2.0 in steps of 0.1) at which pooled M1 <= t_chat; None if none does."""
    for scale in QUOTA_SCALES:
        chat = pooled(option, seeds, mix, scale)["member_chat"]
        if chat["shed"] / chat["offered"] <= t_chat:
            return scale
    return None


def shadow_replay(arrivals: list[Arrival], reserves: dict[str, float]) -> dict:
    """Today's traffic with a shadow-mode gateway in front of today's shared provider limit (R15, R16).

    The provider decides as it does today (first come, first served). The gateway
    blocks nothing: it records what the policy would have done and, because it
    knows each caller's identity, attributes every provider failure to a workload.
    That attribution is what a shared provider key can't give.

    Returns:
        provider: {workload: {"offered": n, "failed": m}}; gateway: Gateway.metrics();
        spend: actual tokens by department for calls that ran.
    """
    now = [0.0]
    clock = lambda: now[0]  # noqa: E731
    policy = LoadShedder(ShedderConfig(TOKEN_CAPACITY, TOKEN_REFILL_PER_SEC, reserves), clock=clock)
    provider = LoadShedder(ShedderConfig(TOKEN_CAPACITY, TOKEN_REFILL_PER_SEC, ZERO), clock=clock)
    gateway = Gateway({w: policy for w in WORKLOADS}, {c: w for w, c in CALLERS.items()}, enforce=False)
    seen = {w: {"offered": 0, "failed": 0} for w in WORKLOADS}

    seq = itertools.count()
    events = [(a.t, next(seq), "arrive", a) for a in arrivals]
    heapq.heapify(events)
    while events:
        now[0], _, kind, a = heapq.heappop(events)
        if kind == "settle":
            gateway.settle(a.request_id, a.token_actual)
            provider.release(a.request_id, a.token_actual)
            continue
        decision = gateway.submit(CALLERS[a.workload], a.request_id, a.token_estimate)
        seen[a.workload]["offered"] += 1
        if provider.admit(Request(a.request_id, decision.priority, a.token_estimate)):
            heapq.heappush(events, (now[0] + CALL_LATENCY_SEC, next(seq), "settle", a))
        else:
            seen[a.workload]["failed"] += 1
            gateway.cancel(a.request_id)
    return {"provider": seen, "gateway": gateway.metrics(), "spend": gateway.showback()}
