"""What a shadow-mode gateway would report about today's peaks: the metrics that don't exist yet (R15, R16).

Nothing is enforced. The provider fails calls exactly as it does today, and the
gateway attributes every outcome to a workload and department.

Run (from solution/):  uv run python -m fde_gateway.observe
"""

from fde_gateway.gateway import WORKLOADS
from fde_gateway.options import HELD_OUT_SEEDS, STARTER, shadow_replay
from fde_gateway.traffic import MIXES, open_enrollment_peak

SUMMED = ("calls", "floor", "too_large", "settled", "tokens_estimated", "tokens_actual", "overruns")


def observe(mix: str, seeds: range, reserves: dict[str, float] = STARTER) -> dict:
    """Shadow-replay totals over seeds: provider outcomes, gateway metrics and spend, per workload."""
    provider = {w: {"offered": 0, "failed": 0} for w in WORKLOADS}
    gateway = {w: dict.fromkeys(SUMMED, 0) for w in WORKLOADS}
    spend: dict[str, int] = {}
    for seed in seeds:
        report = shadow_replay(open_enrollment_peak(seed, mix), reserves)
        for w in WORKLOADS:
            for k in provider[w]:
                provider[w][k] += report["provider"][w][k]
            for k in SUMMED:
                gateway[w][k] += report["gateway"][w][k]
        for dept, tokens in report["spend"].items():
            spend[dept] = spend.get(dept, 0) + tokens
    return {"provider": provider, "gateway": gateway, "spend": spend}


def report(mix: str, obs: dict) -> str:
    total_spend = sum(obs["spend"].values())
    lines = [f"### Mix `{mix}`: shadow gateway (starter reserves) in front of today's limit", "",
             "| Workload (department, tier) | Failed at provider, attributed | Policy would have held back | Actual ÷ estimate (overruns) | Spend on actual tokens |",
             "|---|---|---|---|---|"]
    for w, spec in WORKLOADS.items():
        p, g = obs["provider"][w], obs["gateway"][w]
        held_back = g["floor"] + g["too_large"]
        accuracy = g["tokens_actual"] / g["tokens_estimated"] if g["tokens_estimated"] else 0.0
        dept_spend = obs["spend"].get(spec.department, 0)
        lines.append(
            f"| `{w}` ({spec.department}, {spec.priority}) | {p['failed']}/{p['offered']} = {p['failed'] / p['offered']:.1%} "
            f"| {held_back}/{g['calls']} = {held_back / g['calls']:.1%} "
            f"| {accuracy:.2f} ({g['overruns']}/{g['settled']}) "
            f"| {dept_spend:,} ({dept_spend / total_spend:.0%}) |")
    return "\n".join(lines)


def main() -> None:
    seeds = HELD_OUT_SEEDS
    print(f"Held-out seeds {seeds.start}-{seeds.stop - 1}. Nothing enforced; the provider behaves exactly as today.\n")
    for mix in MIXES:
        print(report(mix, observe(mix, seeds)) + "\n")


if __name__ == "__main__":
    main()
