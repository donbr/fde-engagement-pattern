"""Synthetic open-enrollment peaks, exactly as specified in use_case/data/DATASHEET.md (repo root).

One generator draws every stream from a single seeded RNG in a fixed order.
Options never change the generator: they filter its output (``replay`` skips
dropped and off-live workloads). So every option sees identical arrivals for the
workloads it keeps.
"""

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Arrival:
    """One call arriving at the gateway."""

    t: float
    workload: str
    request_id: str
    token_estimate: int
    token_actual: int


@dataclass(frozen=True)
class Stream:
    """Poisson arrivals of one workload over part of the window."""

    workload: str
    rate_per_sec: float
    token_estimate_min: int
    token_estimate_max: int
    start_sec: float
    end_sec: float


WINDOW_SEC = 120.0
ACTUAL_TO_ESTIMATE = (0.70, 1.05)

BASELINE = (
    Stream("member_chat", 0.25, 150, 350, 0.0, WINDOW_SEC),
    Stream("claims_summary", 0.10, 300, 600, 0.0, WINDOW_SEC),
    Stream("policy_refresh", 1.00, 400, 800, 0.0, 60.0),
)
WAVES = BASELINE + tuple(Stream("member_chat", 1.00, 150, 350, s, s + 10.0) for s in (20.0, 60.0, 100.0))
MIXES: dict[str, tuple[Stream, ...]] = {"baseline": BASELINE, "waves": WAVES}

# The authenticated identity each workload calls from (R5).
CALLERS: dict[str, str] = {
    "member_chat": "chat-frontend",
    "claims_summary": "claims-worker",
    "policy_refresh": "refresh-job",
}


def open_enrollment_peak(seed: int, mix: str = "baseline") -> list[Arrival]:
    """Return one seeded peak window of the named mix, sorted by arrival time."""
    rng = random.Random(seed)
    arrivals = []
    for i, s in enumerate(MIXES[mix]):
        t, n = s.start_sec, 0
        while (t := t + rng.expovariate(s.rate_per_sec)) < s.end_sec:
            estimate = rng.randint(s.token_estimate_min, s.token_estimate_max)
            actual = max(1, round(estimate * rng.uniform(*ACTUAL_TO_ESTIMATE)))
            arrivals.append(Arrival(t, s.workload, f"{s.workload}-{i}-{n}", estimate, actual))
            n += 1
    return sorted(arrivals, key=lambda a: a.t)
