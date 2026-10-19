"""Step 17: every requirement, threshold owner, golden case and readout ask traces to a row in stakeholders.md."""

import json
import re
from pathlib import Path

import pytest

USE_CASE = Path(__file__).parents[2] / "use_case"
BOLD = re.compile(r"\*\*(.+?)\*\*")
CHECKLIST = {"The person with the problem", "Whoever owns the data", "Whoever runs the platform",
             "Whoever approves", "My own manager"}


def table(path: Path, first_header: str) -> list[dict[str, str]]:
    """The markdown table whose header row starts with ``first_header``, as one dict per body row."""
    lines = path.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"| {first_header} |"))
    cells = lambda line: [c.strip() for c in line.strip().strip("|").split("|")]  # noqa: E731
    header = cells(lines[start])
    rows = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        rows.append(dict(zip(header, cells(line))))
    return rows


def names(cell: str) -> list[str]:
    return [n.strip() for n in cell.split(",") if n.strip()]


@pytest.fixture(scope="module")
def rows() -> dict[str, dict[str, str]]:
    """stakeholders.md rows keyed by the role's canonical name (the bold text in the Who column)."""
    found = {}
    for row in table(USE_CASE / "stakeholders.md", "Stage"):
        role = BOLD.search(row["Who (role)"])
        assert role, f"no bold role name in {row['Who (role)']!r}"
        assert role.group(1) not in found, f"{role.group(1)!r} has two rows"
        found[role.group(1)] = row
    return found


@pytest.fixture(scope="module")
def requirements() -> dict[str, list[str]]:
    return {r["#"]: names(r["Stakeholder (role)"]) for r in table(USE_CASE / "requirements.md", "#")}


def test_every_requirement_traces_to_a_row(rows, requirements):
    missing = {req: role for req, roles in requirements.items() for role in roles if role not in rows}
    assert not missing


def test_every_threshold_owner_is_a_row_that_owes_it(rows):
    thresholds = json.loads((USE_CASE / "evals" / "thresholds.json").read_text())
    for key, entry in thresholds.items():
        assert entry["owner"] in rows, f"{key}: owner {entry['owner']!r} has no row"
        assert f"`{key}`" in rows[entry["owner"]]["What they owe"], f"{key} isn't in its owner's What they owe"


def test_every_golden_case_belongs_to_a_requirement(requirements):
    for line in (USE_CASE / "evals" / "golden.jsonl").read_text().splitlines():
        case = json.loads(line)["input"]
        req = re.search(r"\((R\d+)\)", case["stakeholder"])
        assert req and req.group(1) in requirements, case["name"]


def test_every_metric_owner_is_a_row(rows):
    for metric in table(USE_CASE / "cxo-story.md", "Metric"):
        assert names(metric["Owner"]) and all(o in rows for o in names(metric["Owner"])), metric["Metric"]


def test_every_golden_case_stakeholder_in_the_evals_readme_is_a_row(rows):
    for case in table(USE_CASE / "evals" / "README.md", "Case"):
        assert case["Stakeholder"] in rows, case["Case"]


def test_everyone_the_ecosystem_asks_is_a_row_or_reached_through_one(rows):
    through = {r["Team"]: r["Reached through"] for r in table(USE_CASE / "stakeholders.md", "Team")}
    assert all(row in rows for row in through.values())
    asked = [n for r in table(USE_CASE / "ecosystem.md", "Area") if r["Ask"] != "—" for n in names(r["Ask"])]
    asked += [n for r in table(USE_CASE / "ecosystem.md", "What (gate)") for n in names(r["Who"])]
    assert asked
    assert not {n for n in asked if n not in rows and n not in through}


def test_every_role_in_the_readout_ask_is_a_row(rows):
    readout = (USE_CASE / "readout.md").read_text()
    ask = readout[readout.index("**The ask:**") + len("**The ask:**"):]
    asked = BOLD.findall(ask)
    assert asked
    assert set(asked) <= set(rows), set(asked) - set(rows)


def test_every_row_has_a_requirement_a_threshold_or_a_reason_for_neither(rows, requirements):
    sourced = {role for roles in requirements.values() for role in roles}
    owners = {e["owner"] for e in json.loads((USE_CASE / "evals" / "thresholds.json").read_text()).values()}
    reasons = {r["Role"]: r["Why there is no requirement"]
               for r in table(USE_CASE / "stakeholders.md", "Role")}
    for role in rows:
        has_work = role in sourced or role in owners
        assert has_work != (role in reasons), f"{role!r}: needs a requirement, a threshold or a reason (not both)"
    assert all(reasons.values())


def test_the_coverage_checklist_is_complete(rows):
    checklist = {r["Checklist"]: names(r["Rows"]) for r in table(USE_CASE / "stakeholders.md", "Checklist")}
    assert set(checklist) == CHECKLIST
    for item, roles in checklist.items():
        assert roles and all(role in rows for role in roles), item
