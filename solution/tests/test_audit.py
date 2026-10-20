"""The saved evaluate report reproduces, so CI checks the published tables on every push."""

import re
from pathlib import Path

import pytest

from fde_gateway.evaluate import evaluate_mix, report
from fde_gateway.gates import load_thresholds
from fde_gateway.options import HELD_OUT_SEEDS
from fde_gateway.traffic import MIXES

EVALS = Path(__file__).parents[2] / "use_case" / "evals"
# M6 is wall-clock latency, so it differs on every machine; everything else must match exactly.
M6_ROW = re.compile(r"^\| M6 decision p99 \| [0-9.]+ µs \|$", re.MULTILINE)


def section(published: str, mix: str) -> str:
    """The saved report for one mix: from its "### Mix" heading up to the next heading or the end of the file."""
    return re.search(rf"^### Mix `{mix}`.*?(?=^### |\Z)", published, re.MULTILINE | re.DOTALL).group().rstrip()  # pyright: ignore[reportOptionalMemberAccess]


@pytest.mark.parametrize("mix", list(MIXES))
def test_published_report_reproduces_except_m6_timing(mix):
    values, statuses = load_thresholds(EVALS / "thresholds.json")
    got = report(mix, evaluate_mix(mix, HELD_OUT_SEEDS, values), statuses)
    published = (EVALS / "results" / "2026-10-18_heldout.md").read_text()
    assert len(M6_ROW.findall(got)) == 1
    # equality, not `in`: a report with a row missing must fail
    assert M6_ROW.sub("| M6 |", got) == M6_ROW.sub("| M6 |", section(published, mix))
