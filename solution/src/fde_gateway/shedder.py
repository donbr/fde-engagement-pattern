"""Priority-aware load shedder for LLM API calls.

Copied unchanged from the reference implementation in an earlier solution-first
spike (not included in this repo) on 2026-10-18. The core decision rule did not change between passes; what changed
is everything around it (gateway.py, options.py, gates.py).

Purpose
    Decide, immediately and without queueing, whether an LLM request may run
    under a shared token budget. Each request is either admitted or shed.

Where it sits
    Caller -> gateway -> LoadShedder -> LLM API. The gateway resolves the
    business questions first: a policy layer maps request metadata (business
    unit, interactive vs. batch, ...) to a priority, and a tokenizer turns the
    payload into an estimate. The shedder only sees ``priority`` and
    ``token_estimate``; it never sees who the caller is or what the prompt says.

Workflow (like a credit-card pre-authorization)
    1. ``admit(request)``                      -> place a hold for the *estimated* tokens.
    2. caller invokes the LLM                  (only if admitted).
    3. ``release(request_id, token_actual)``  -> settle the hold with the *actual* usage:
                                                  refund ``token_estimate - token_actual``,
                                                  or charge an overrun.

Decision rule
    Admit iff  ``token_balance - token_estimate >= reserves[priority] * token_capacity``.
    A reserve is the share of capacity a tier must leave behind for more
    important traffic, so lower tiers are shed first.

Invariants
    - Refill and refund never raise ``token_balance`` above ``token_capacity``.
    - ``token_balance`` may go negative, but only through an overrun on ``release``.
    - Priority decision counts change only in ``admit``; invalid requests are not counted.
    - Each admitted request is settled at most once (``request_ledger`` tracks it).

Naming
    Parameters and locals are named after the field they carry: ``request`` is a
    ``Request``, ``request_id`` is ``Request.id``, ``token_estimate`` is
    ``Request.token_estimate``, and ``reserve_floor`` comes from
    ``ShedderConfig.reserves``.

    Budget names follow ``<resource>_<role>``: ``capacity`` is the fixed limit
    (config) and ``balance`` is what's left now (state). This module has one
    budget, tokens: ``token_capacity``, ``token_refill_per_sec``,
    ``token_balance``. A request-rate (RPM) limit would be a second budget named
    the same way: ``rate_capacity``, ``rate_refill_per_sec``, ``rate_balance``.
    Per-request amounts follow the same prefix: ``token_estimate`` at admit,
    ``token_actual`` at release.

Example
    >>> s = LoadShedder(ShedderConfig(1000, 100, {"CRITICAL": 0.0, "DEFERRABLE": 0.4}),
    ...                 clock=lambda: 0.0)
    >>> s.admit(Request("a", "DEFERRABLE", 700))   # 1000 - 700 = 300 < floor 400
    False
    >>> s.admit(Request("b", "CRITICAL", 700))     # 1000 - 700 = 300 >= floor 0
    True
    >>> s.release("b", 500)                        # refund 200 -> 500
    >>> s.token_balance
    500.0
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ShedderConfig:
    """Deploy-time policy. Frozen so the policy can't change under a running shedder.

    Attributes:
        token_capacity: Maximum tokens the bucket can hold; also the starting balance.
        token_refill_per_sec: Tokens added back per second of elapsed clock time.
        reserves: Priority name -> fraction of capacity (0.0-1.0) that must remain
            after admitting a request of that priority. The keys are also the set of
            valid priorities.
    """

    token_capacity: int
    token_refill_per_sec: float
    reserves: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class Request:
    """One LLM call, after the gateway has resolved priority and size.

    Attributes:
        id: Correlation id; ``release`` uses it to find this request's hold.
        priority: A key of ``ShedderConfig.reserves`` (e.g. "CRITICAL").
        token_estimate: Estimated token cost; must be positive.
    """

    id: str
    priority: str
    token_estimate: int


class LoadShedder:
    """Token-bucket admission controller with per-priority reserve floors.

    Attributes:
        config: The policy this shedder enforces.
        clock: Returns the current time in seconds. Injectable so tests can freeze
            or move time by hand.
        token_balance: Tokens currently available. Float because refill is fractional.
        last_refill_time: Clock reading at the most recent refill.
        request_ledger: Admitted, not-yet-released requests: request id -> token_estimate.
        priority_decision_counts: Priority -> {"admitted": n, "shed": m}; every configured priority
            is present from the start.
    """

    def __init__(self, config: ShedderConfig, clock: Callable[[], float] = time.monotonic):
        self.config = config
        self.clock = clock
        self.token_balance = float(config.token_capacity)  # start full
        self.last_refill_time = clock()
        self.request_ledger: dict[str, int] = {}
        self.priority_decision_counts = {priority: {"admitted": 0, "shed": 0} for priority in config.reserves}

    def _refill(self) -> None:
        """Add tokens for the time elapsed since the last refill, capped at capacity.

        Called at the start of every ``admit`` and ``release`` so the balance is
        current before it is read or changed.
        """
        current_time = self.clock()
        elapsed_sec = max(0.0, current_time - self.last_refill_time)  # backwards clock adds nothing
        self.token_balance = min(self.config.token_capacity, self.token_balance + elapsed_sec * self.config.token_refill_per_sec)
        self.last_refill_time = current_time  # reset even if the clock went backwards

    def admit(self, request: Request) -> bool:
        """Decide now whether ``request`` may run; on admit, place a hold for its estimate.

        Args:
            request: The request to decide on.

        Returns:
            True if admitted (tokens deducted, hold recorded in ``request_ledger``);
            False if shed (balance unchanged).

        Raises:
            ValueError: If the priority isn't configured or ``token_estimate <= 0``.
                Raised before any state changes, so invalid requests aren't counted.
        """
        # Validate before touching state.
        if request.priority not in self.config.reserves:
            raise ValueError(f"unknown priority {request.priority!r}")
        if request.token_estimate <= 0:
            raise ValueError("token_estimate must be positive")

        self._refill()

        # The floor is what this tier must leave behind for more important traffic.
        reserve_floor = self.config.reserves[request.priority] * self.config.token_capacity
        # The capacity check is implied by the floor check (token_balance <= capacity and
        # reserve_floor >= 0), but it reads as an explicit "too big, ever" guard.
        # The floor boundary is inclusive: landing exactly on it is admitted.
        admitted = (request.token_estimate <= self.config.token_capacity
                    and self.token_balance - request.token_estimate >= reserve_floor)
        if admitted:
            self.token_balance -= request.token_estimate
            self.request_ledger[request.id] = request.token_estimate  # hold, settled later by release()
        self.priority_decision_counts[request.priority]["admitted" if admitted else "shed"] += 1
        return admitted

    def release(self, request_id: str, token_actual: int) -> None:
        """Settle an admitted request's hold with its actual usage.

        Refunds ``token_estimate - token_actual`` when the call used less than
        estimated, and deducts the difference when it used more. Counts are not
        changed.

        Args:
            request_id: The ``Request.id`` passed to ``admit``.
            token_actual: Tokens the LLM call really consumed.

        Raises:
            KeyError: If ``request_id`` has no open hold: never admitted, shed, or
                already released. ``pop`` removes the hold, so a second release
                can't refund twice.
        """
        token_estimate = self.request_ledger.pop(request_id)
        self._refill()
        # Cap at capacity so a refund can't overfill; an overrun may go negative.
        self.token_balance = min(self.config.token_capacity, self.token_balance + token_estimate - token_actual)

    def stats(self) -> dict[str, dict[str, int]]:
        """Return admitted/shed counts per priority.

        Returns:
            A copy, so callers can't modify the shedder's counters.
        """
        return {priority: dict(tally) for priority, tally in self.priority_decision_counts.items()}
