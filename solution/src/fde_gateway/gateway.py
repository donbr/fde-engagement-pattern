"""The gateway: identity in, a metadata-only decision record out, spend charged on what ran.

Requirements it implements (use_case/requirements.md at the repo root):
    R5  the tier comes from the caller's identity; a claimed tier is ignored and flagged.
    R6  decision records carry metadata only.
    R7  shadow mode never blocks a known caller; ``set_enforce`` is the kill switch.
        Unknown callers are rejected in both modes (R5; decisions.md, step 10).
    R8  counts by tier and reason.
    R10 showback on actual tokens for every call that ran, including shadow-allowed would-sheds.
    R15 per-workload metrics that don't exist today: calls, reasons, estimate accuracy.
    R16 ``cancel`` frees a call that failed downstream (e.g. a provider 429), so it costs
        nothing. Attribution of that failure comes from the caller's identity: see
        ``options.shadow_replay``, which counts it under ``Decision.workload``.

In shadow mode the shedder still decides, and only its would-admits draw on its
bucket. So the shadow records what the policy *would* have done with its own
accounting, not what the provider saw. See decisions.md.

Example
    >>> from fde_gateway.shedder import LoadShedder, ShedderConfig
    >>> shedder = LoadShedder(ShedderConfig(1000, 100, {"CRITICAL": 0.0, "STANDARD": 0.1, "DEFERRABLE": 0.4}),
    ...                       clock=lambda: 0.0)
    >>> gateway = Gateway({w: shedder for w in WORKLOADS}, {"refresh-job": "policy_refresh"}, enforce=False)
    >>> d = gateway.submit("refresh-job", "r1", 700)   # 1000 - 700 < 400 floor
    >>> d.allowed, d.reason, d.enforced
    (True, 'floor', False)
"""

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from fde_gateway.shedder import LoadShedder, Request, _check_token_actual, _check_token_estimate

REASONS = ("admitted", "floor", "too_large")


@dataclass(frozen=True)
class Workload:
    """One kind of traffic, as the business owner names it."""

    name: str
    department: str
    priority: str


# The tier table the business owners sign (R1).
WORKLOADS: dict[str, Workload] = {
    w.name: w
    for w in (
        Workload("member_chat", "Member Services", "CRITICAL"),
        Workload("claims_summary", "Claims", "STANDARD"),
        Workload("policy_refresh", "Content Operations", "DEFERRABLE"),
    )
}


@dataclass(frozen=True)
class Decision:
    """What the gateway decided for one call. Metadata only: no prompt or response content (R6).

    Attributes:
        allowed: Whether the call may run. In shadow mode this is always True.
        enforced: Whether the policy was enforcing when this was decided.
        reason: The policy's own decision: "admitted", "floor" or "too_large",
            recorded even when shadow mode let the call through.
        spoof_attempt: The request claimed a workload its identity doesn't hold.
    """

    request_id: str
    caller: str
    workload: str
    priority: str
    token_estimate: int
    allowed: bool
    enforced: bool
    reason: str
    spoof_attempt: bool


class Gateway:
    """Map caller identity to a workload, ask that workload's shedder, record and charge.

    Attributes:
        shedders: Workload name -> the shedder that decides it. One shared instance
            for a single limit; separate instances for separate limits (option 2).
        identities: Authenticated caller identity -> workload name.
        enforce: False is shadow mode: decide and record, never block a known caller.
        log: Every decision, in order.
        running: Calls that are allowed and not yet settled: request id ->
            (workload name, whether the shedder holds tokens for it, token estimate).
        unknown_callers: Rejected calls from identities not in ``identities``.
    """

    def __init__(self, shedders: Mapping[str, LoadShedder], identities: Mapping[str, str],
                 enforce: bool = True, workloads: Mapping[str, Workload] = WORKLOADS):
        if unknown := set(identities.values()) - set(workloads):
            raise ValueError(f"identities map to unknown workloads {sorted(unknown)}")
        if unserved := set(identities.values()) - set(shedders):
            raise ValueError(f"no shedder for workloads {sorted(unserved)}")
        if untiered := sorted(w for w in set(identities.values())
                              if workloads[w].priority not in shedders[w].config.reserves):
            raise ValueError(f"no reserve for the tier of workloads {untiered}")
        _check_bool(enforce)
        self.shedders = dict(shedders)
        self.identities = dict(identities)
        self.workloads = dict(workloads)
        self.enforce = enforce
        self.log: list[Decision] = []
        self.running: dict[str, tuple[str, bool, int]] = {}
        self.unknown_callers = 0
        self._spend: dict[str, int] = defaultdict(int)
        self._counts = {w.priority: {r: 0 for r in REASONS} for w in self.workloads.values()}
        self._by_workload = {
            name: {"calls": 0, "allowed": 0, **{r: 0 for r in REASONS},
                   "settled": 0, "tokens_estimated": 0, "tokens_actual": 0, "overruns": 0}
            for name in self.workloads
        }

    def submit(self, caller: str, request_id: str, token_estimate: int,
               claimed_workload: str | None = None) -> Decision:
        """Decide one call. The tier comes from ``caller``; ``claimed_workload`` is only checked, never used.

        Raises:
            PermissionError: Unknown caller, in either mode. Nothing is recorded but
                the rejection count.
            TypeError: ``token_estimate`` isn't an int.
            ValueError: ``token_estimate`` isn't positive, or ``request_id`` is still
                running (reusing it would lose its hold).

            Every check runs before anything is recorded, in both modes.
        """
        if caller not in self.identities:
            self.unknown_callers += 1
            raise PermissionError(f"unknown caller {caller!r}")
        _check_token_estimate(token_estimate)
        if request_id in self.running:
            raise ValueError(f"request id {request_id!r} is already running")
        workload = self.workloads[self.identities[caller]]
        shedder = self.shedders[workload.name]

        held = shedder.admit(Request(request_id, workload.priority, token_estimate))
        if held:
            reason = "admitted"
        elif token_estimate > shedder.config.token_capacity:
            reason = "too_large"
        else:
            reason = "floor"
        allowed = held or not self.enforce
        if allowed:
            self.running[request_id] = (workload.name, held, token_estimate)

        decision = Decision(
            request_id=request_id, caller=caller, workload=workload.name, priority=workload.priority,
            token_estimate=token_estimate, allowed=allowed, enforced=self.enforce, reason=reason,
            spoof_attempt=claimed_workload is not None and claimed_workload != workload.name,
        )
        self.log.append(decision)
        self._counts[workload.priority][reason] += 1
        tally = self._by_workload[workload.name]
        tally["calls"] += 1
        tally["allowed"] += allowed
        tally[reason] += 1
        return decision

    def settle(self, request_id: str, token_actual: int) -> None:
        """Charge a call that ran, and settle the shedder's hold if it has one.

        Raises:
            TypeError: ``token_actual`` isn't an int.
            ValueError: ``token_actual`` is negative.
            KeyError: The call never ran (blocked or unknown) or was already settled.

            The value checks run first, so a bad value leaves the call running.
        """
        _check_token_actual(token_actual)
        workload_name, held, token_estimate = self.running[request_id]
        if held:
            self.shedders[workload_name].release(request_id, token_actual)
        del self.running[request_id]  # after the shedder settles, so a failure there leaves the call running
        self._spend[self.workloads[workload_name].department] += token_actual
        tally = self._by_workload[workload_name]
        tally["settled"] += 1
        tally["tokens_estimated"] += token_estimate
        tally["tokens_actual"] += token_actual
        tally["overruns"] += token_actual > token_estimate

    def cancel(self, request_id: str) -> None:
        """An allowed call failed downstream (e.g. a provider 429) and never ran: free its hold, charge nothing.

        Raises:
            KeyError: The call isn't running.
        """
        workload_name, held, _ = self.running[request_id]
        if held:
            self.shedders[workload_name].release(request_id, 0)
        del self.running[request_id]

    def set_enforce(self, value: bool) -> None:
        """The kill switch. False returns to today's behaviour: every known caller's call runs.

        Raises:
            TypeError: ``value`` isn't a bool (``"false"`` would otherwise turn enforcement on).
        """
        _check_bool(value)
        self.enforce = value

    def showback(self) -> dict[str, int]:
        """Actual tokens by department, as a copy."""
        return dict(self._spend)

    def counts(self) -> dict[str, dict[str, int]]:
        """Decisions by tier and reason, as a copy."""
        return {p: dict(c) for p, c in self._counts.items()}

    def metrics(self) -> dict[str, dict]:
        """Per workload: department, tier, calls, allowed, decisions by reason, and estimate accuracy on settled calls (R15)."""
        return {name: {"department": self.workloads[name].department, "priority": self.workloads[name].priority, **tally}
                for name, tally in self._by_workload.items()}


def _check_bool(value: object) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"enforce must be a bool, got {value!r}")
