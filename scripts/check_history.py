"""Check the pre-registration against git history. Run from anywhere inside the repo: python3 scripts/check_history.py

Three checks, each printed PASS or FAIL:
  1. Order: the evidence files were first committed in step order
     (acceptance cases, thresholds, failing tests, code, held-out results).
  2. Acceptance cases: every case's input and expected output is unchanged since
     the commit that added golden.jsonl. Only the ``why`` text may change.
  3. Thresholds: every value is unchanged since the commit that added
     thresholds.json. ``status`` may change, because signing is how an owner
     turns ``proposed`` into ``signed``.

Commits 0-9 were reconstructed after the fact (PROCESS.md, "Evidence of order"),
so for those steps check 1 shows the commit order, not when the work happened.
Checks 2 and 3 are a lock from here on: any later edit to a case or a threshold
value fails CI, and must come with a row in use_case/decisions.md.

Needs the full history (in CI: actions/checkout with fetch-depth: 0). Stdlib only.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GOLDEN = "use_case/evals/golden.jsonl"
THRESHOLDS = "use_case/evals/thresholds.json"
# Evidence files in the order the pattern says they must be written.
ORDER = [
    ("acceptance cases", GOLDEN),
    ("thresholds", THRESHOLDS),
    ("failing tests", "solution/tests/test_golden.py"),
    ("code", "solution/src/fde_gateway/gates.py"),
    ("held-out results", "use_case/evals/results/2026-10-18_heldout.json"),
]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def added_in(path: str) -> str:
    """The commit that first added ``path``, following renames."""
    commits = git("log", "--follow", "--diff-filter=A", "--format=%H", "--", path).split()
    if not commits:
        raise SystemExit(f"FAIL  {path} is not in the git history (shallow clone?)")
    return commits[-1]


def is_ancestor(older: str, newer: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", older, newer], cwd=ROOT).returncode == 0


def check_order() -> list[str]:
    added = [(label, path, added_in(path)) for label, path in ORDER]
    problems = []
    for (label_a, _, a), (label_b, _, b) in zip(added, added[1:]):
        if a == b or not is_ancestor(a, b):
            problems.append(f"{label_a} ({a[:7]}) was not committed before {label_b} ({b[:7]})")
    return problems


def check_golden() -> list[str]:
    def cases(rev: str) -> list[dict]:
        return [json.loads(line) for line in git("show", f"{rev}:{GOLDEN}").splitlines() if line.strip()]

    first, now = cases(added_in(GOLDEN)), cases("HEAD")
    if len(first) != len(now):
        return [f"{len(first)} cases when added, {len(now)} now"]
    return [f"case {old['input'].get('name', i)!r}: input or expected output changed"
            for i, (old, new) in enumerate(zip(first, now))
            if (old["input"], old["output"]) != (new["input"], new["output"])]


def check_thresholds() -> list[str]:
    first = json.loads(git("show", f"{added_in(THRESHOLDS)}:{THRESHOLDS}"))
    now = json.loads(git("show", f"HEAD:{THRESHOLDS}"))
    if first.keys() != now.keys():
        return [f"keys changed: {sorted(first)} -> {sorted(now)}"]
    return [f"{key}: {first[key]['value']} -> {now[key]['value']}"
            for key in first if first[key]["value"] != now[key]["value"]]


def main() -> int:
    failed = False
    for name, check in [("order of evidence files", check_order),
                        ("acceptance cases unchanged", check_golden),
                        ("threshold values unchanged", check_thresholds)]:
        problems = check()
        print(f"{'FAIL' if problems else 'PASS'}  {name}")
        for problem in problems:
            print(f"      {problem}")
        failed = failed or bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
