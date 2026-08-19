"""Recovers test-level resolution from an existing run. Zero API cost.

Why this exists: with n=12 and a binary pass/fail per problem, the smallest
difference the eval can express is one problem = 8.3 points. Every comparison in
the headline table is therefore within noise. But each problem carries 4-7
individual assertions, and every run file already stores the final `code` each
method produced -- so the finer-grained signal has already been paid for and
just needs to be read out.

This re-executes those stored solutions locally in the same sandbox and counts
individual tests passed. It turns ~12 binary outcomes into ~60 test-level ones,
which is a materially better resolution for the same API spend.

What this does NOT do: it does not make a small eval set statistically
sufficient. Test-level counts are correlated within a problem (one wrong API
call fails several assertions at once), so 60 tests are not 60 independent
samples. This sharpens a descriptive comparison; it does not license a
significance claim.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.sandbox import run_tests_in_sandbox  # noqa: E402
from problems import load_problems  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

_COUNT_RE = re.compile(r"(\d+)\s+(passed|failed|error|errors|skipped)")


def parse_pytest_counts(output: str) -> dict[str, int]:
    """Reads pytest's summary line. Returns {} when no summary is present."""
    counts: dict[str, int] = {}
    for line in reversed(output.strip().splitlines()):
        found = _COUNT_RE.findall(line)
        if found:
            for n, label in found:
                key = "error" if label.startswith("error") else label
                counts[key] = counts.get(key, 0) + int(n)
            break
    return counts


def count_test_functions(tests_path: Path) -> int:
    return len(re.findall(r"^def test_", tests_path.read_text(encoding="utf-8"), flags=re.M))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="Run file. Defaults to the newest.")
    args = parser.parse_args()

    if args.path:
        path = Path(args.path)
    else:
        candidates = sorted(RESULTS_DIR.glob("run_*.jsonl"))
        if not candidates:
            print("No run files in results/.", file=sys.stderr)
            return 1
        path = candidates[-1]

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    meta = next((r for r in rows if r.get("record_type") == "run_meta"), {})
    results = [r for r in rows if r.get("record_type") == "result"]
    if not results:
        print(f"{path} has no result rows.", file=sys.stderr)
        return 1

    problems = {p.id: p for p in load_problems()}
    totals: dict[str, dict[str, int]] = {}
    per_problem: list[tuple[str, str, int, int]] = []

    print(f"Re-running stored solutions from {path.name} (no API calls)...", flush=True)

    for row in results:
        problem = problems.get(row["problem_id"])
        if problem is None or not row.get("code"):
            continue
        tests_path = Path(problem.canonical_tests_path)
        n_tests = count_test_functions(tests_path)

        execution = run_tests_in_sandbox(
            solution_code=row["code"],
            test_code=tests_path.read_text(encoding="utf-8"),
            timeout_sec=30,
        )
        counts = parse_pytest_counts(execution.stdout + "\n" + execution.stderr)
        # A collection error (bad import, syntax error) means no test ran, so
        # passed=0 against the full denominator -- not an excluded row. Dropping
        # these would flatter whichever method crashes most.
        passed = counts.get("passed", 0)

        bucket = totals.setdefault(row["method"], {"passed": 0, "total": 0})
        bucket["passed"] += passed
        bucket["total"] += n_tests
        per_problem.append((row["problem_id"], row["method"], passed, n_tests))

    print("\n" + "=" * 72)
    print(f"TEST-LEVEL RESULTS  --  model: {meta.get('model', '?')}")
    print("=" * 72)
    print("\n--- assertions passed per method (raw counts) ---")
    for method in ("single_shot", "best_of_n", "self_correct"):
        if method in totals:
            b = totals[method]
            pct = 100 * b["passed"] / b["total"] if b["total"] else 0.0
            print(f"  {method:<14} {b['passed']:>3}/{b['total']:<3} assertions ({pct:.1f}%)")

    print("\n--- per problem: assertions passed (single_shot / best_of_n / self_correct) ---")
    by_problem: dict[str, dict[str, tuple[int, int]]] = {}
    for pid, method, passed, total in per_problem:
        by_problem.setdefault(pid, {})[method] = (passed, total)
    for pid in sorted(by_problem):
        cells = []
        for method in ("single_shot", "best_of_n", "self_correct"):
            if method in by_problem[pid]:
                p, t = by_problem[pid][method]
                cells.append(f"{p}/{t}")
            else:
                cells.append("  - ")
        print(f"  {pid:<30} {'  '.join(f'{c:>6}' for c in cells)}")

    # Counterfactual: how many problems would each method have solved if judged
    # ONLY by the tests, with the static gate advisory rather than blocking?
    # The gate can halt an attempt whose code would in fact have passed --
    # notably `class Config`, which Pydantic v2 still honours for backwards
    # compatibility, so it is simultaneously "v1 syntax" (gate says fail) and
    # "working code" (tests say pass). This measures the cost of that policy.
    print("\n--- counterfactual: final code judged by tests alone ---")
    print("    (i.e. if the static check were advisory instead of blocking)")
    for method in ("single_shot", "best_of_n", "self_correct"):
        rows_m = [(pid, v[method]) for pid, v in by_problem.items() if method in v]
        full = [pid for pid, (p, t) in rows_m if t and p == t]
        reported = sum(1 for r in results if r["method"] == method and r.get("passed"))
        print(f"  {method:<14} tests-only {len(full)}/{len(rows_m)}   vs reported {reported}/{len(rows_m)}")
        gap = sorted(set(full) - {r["problem_id"] for r in results if r["method"] == method and r.get("passed")})
        if gap:
            print(f"                 blocked by the gate despite passing: {gap}")

    print("\nTest-level counts are correlated within a problem -- one wrong API call")
    print("fails several assertions at once. This is finer description, not significance.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
