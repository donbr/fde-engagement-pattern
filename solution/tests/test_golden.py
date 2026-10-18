"""Replay the five stakeholder acceptance cases in use_case/evals/golden.jsonl (repo root).

Gateway cases check each step's listed keys, the exception name, or None; then
the final showback. The gate case checks the verdict per gate.
"""

import json
from pathlib import Path

import pytest

from fde_gateway.gates import evaluate_gates
from fde_gateway.gateway import WORKLOADS, Gateway
from fde_gateway.shedder import LoadShedder, ShedderConfig

GOLDEN = Path(__file__).parents[2] / "use_case" / "evals" / "golden.jsonl"
CASES = [json.loads(line) for line in GOLDEN.read_text().splitlines() if line.strip()]
GATEWAY_CASES = [c for c in CASES if c["input"].get("op") != "gates"]
GATE_CASES = [c for c in CASES if c["input"].get("op") == "gates"]
EXCEPTIONS = {"PermissionError": PermissionError, "KeyError": KeyError}


def test_five_cases_each_with_a_stakeholder_and_a_why():
    assert len(CASES) == 5
    assert all(c["input"]["stakeholder"] and c["why"] for c in CASES)


@pytest.mark.parametrize("case", GATEWAY_CASES, ids=[c["input"]["name"] for c in GATEWAY_CASES])
def test_gateway_case(case):
    spec = case["input"]
    now = [0.0]
    shedder = LoadShedder(ShedderConfig(**spec["config"]), clock=lambda: now[0])
    gateway = Gateway({w: shedder for w in WORKLOADS}, spec["identities"], enforce=spec["enforce"])
    assert len(spec["steps"]) == len(case["output"]["results"])

    for step, want in zip(spec["steps"], case["output"]["results"]):
        now[0] = step["t"]
        if step["op"] == "submit":
            call = lambda: gateway.submit(step["caller"], step["id"], step["token_estimate"], step.get("claimed_workload"))  # noqa: E731
        elif step["op"] == "settle":
            call = lambda: gateway.settle(step["id"], step["token_actual"])  # noqa: E731
        else:
            call = lambda: gateway.set_enforce(step["value"])  # noqa: E731

        if isinstance(want, str):
            with pytest.raises(EXCEPTIONS[want]):
                call()
        elif want is None:
            assert call() is None, step
        else:
            decision = call()
            assert {k: getattr(decision, k) for k in want} == want, step

    assert gateway.showback() == case["output"]["showback"]


@pytest.mark.parametrize("case", GATE_CASES, ids=[c["input"]["name"] for c in GATE_CASES])
def test_gate_case(case):
    verdicts = evaluate_gates(case["input"]["metrics"], case["input"]["thresholds"])
    assert {g: v.verdict for g, v in verdicts.items()} == case["output"]["gates"]
