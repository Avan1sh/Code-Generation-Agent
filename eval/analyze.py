"""Turns a raw run file into counts.

Every rate printed here is accompanied by the raw counts it came from
(`9/12`, not `75%`). A bare percentage hides the denominator, and with a
12-problem eval set the denominator is the most important part -- one problem
is 8.3 points.

This script refuses to print anything if the results file is missing or has no
result rows, rather than emitting an empty table that could be mistaken for a
real measurement.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

METHOD_LABELS = {
    "single_shot": "single_shot (pass@1 floor)",
    "best_of_n": "best_of_n (pass@N ORACLE ceiling)",
    "self_correct": "self_correct (agent)",
}


def _fmt(passed: int, total: int) -> str:
    if total == 0:
        return "n/a (0 problems)"
    return f"{passed}/{total} ({100 * passed / total:.1f}%)"


def load_run(path: Path) -> tuple[dict, pd.DataFrame]:
    meta: dict = {}
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("record_type") == "run_meta":
                meta = obj
            elif obj.get("record_type") == "result":
                rows.append(obj)
    return meta, pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="Path to a run_*.jsonl. Defaults to the newest.")
    args = parser.parse_args()

    if args.path:
        path = Path(args.path)
    else:
        candidates = sorted(RESULTS_DIR.glob("run_*.jsonl"))
        if not candidates:
            print(
                "No run files in results/. Run `python eval/run_eval.py` first.\n"
                "Refusing to print a summary with no data behind it.",
                file=sys.stderr,
            )
            return 1
        path = candidates[-1]

    if not path.exists():
        print(f"No such file: {path}", file=sys.stderr)
        return 1

    meta, df = load_run(path)
    if df.empty:
        print(f"{path} contains no result rows. Nothing to report.", file=sys.stderr)
        return 1

    print("=" * 72)
    print(f"RUN: {path.name}")
    for key in ("timestamp_utc", "provider", "model", "max_attempts", "n_problems", "posix_resource_limits_active"):
        if key in meta:
            print(f"  {key}: {meta[key]}")
    print("=" * 72)

    errors = df[df.get("error").notna()] if "error" in df.columns else df.iloc[0:0]
    if not errors.empty:
        print(f"\n!! {len(errors)} row(s) errored and are counted as failures:")
        for _, row in errors.iterrows():
            print(f"   {row['problem_id']} :: {row['method']}")

    print("\n--- HEADLINE: solved per method (raw counts) ---")
    for method in ("single_shot", "best_of_n", "self_correct"):
        sub = df[df["method"] == method]
        if sub.empty:
            continue
        print(f"  {METHOD_LABELS[method]:<38} {_fmt(int(sub['passed'].sum()), len(sub))}")

    ss = df[df["method"] == "single_shot"]
    sc = df[df["method"] == "self_correct"]
    if not ss.empty and not sc.empty:
        ss_n, sc_n = int(ss["passed"].sum()), int(sc["passed"].sum())
        n = len(sc)
        delta = sc_n - ss_n
        print(f"\n  self_correct - single_shot = {delta:+d} problems out of {n}")
        if delta == 0:
            print("  -> No measured improvement over the baseline in this run.")

        # Paired, per-problem: the aggregate delta can hide the loop fixing one
        # problem while breaking another. With n=12 that distinction matters.
        merged = ss[["problem_id", "passed"]].merge(
            sc[["problem_id", "passed"]], on="problem_id", suffixes=("_ss", "_sc")
        )
        fixed = merged[(~merged["passed_ss"]) & (merged["passed_sc"])]
        broke = merged[(merged["passed_ss"]) & (~merged["passed_sc"])]
        print(f"  fixed by the loop:   {len(fixed)}/{len(merged)}  {sorted(fixed['problem_id'])}")
        print(f"  broken by the loop:  {len(broke)}/{len(merged)}  {sorted(broke['problem_id'])}")

    if not sc.empty and "attempts_used" in sc.columns:
        print("\n--- self_correct: attempts used ---")
        solved = sc[sc["passed"]]
        for attempt in sorted(sc["attempts_used"].dropna().unique()):
            n_solved = int((solved["attempts_used"] == attempt).sum())
            print(f"  solved on attempt {int(attempt)}: {n_solved}/{len(sc)}")
        unsolved = sc[~sc["passed"]]
        if not unsolved.empty and "status" in unsolved.columns:
            print("  unsolved terminal states:")
            for status, count in unsolved["status"].value_counts().items():
                print(f"    {status}: {count}/{len(sc)}")

    if "samples_passed" in df.columns:
        bon = df[(df["method"] == "best_of_n") & df["samples_passed"].notna()]
        if not bon.empty:
            n = meta.get("best_of_n_n", meta.get("max_attempts", "?"))
            total_samples = bon["samples_passed"].sum()
            print(f"\n--- best_of_n: sample-level ---")
            print(f"  individual samples passing: {int(total_samples)}/{len(bon) * n if isinstance(n, int) else '?'}")

    print("\n--- per category: solved / attempted ---")
    for category, group in df.groupby("category"):
        parts = []
        for method in ("single_shot", "best_of_n", "self_correct"):
            sub = group[group["method"] == method]
            if not sub.empty:
                parts.append(f"{method}={int(sub['passed'].sum())}/{len(sub)}")
        print(f"  {category:<24} {'  '.join(parts)}")

    if "llm_calls" in df.columns:
        print("\n--- cost: total LLM calls ---")
        for method in ("single_shot", "best_of_n", "self_correct"):
            sub = df[(df["method"] == method) & df["llm_calls"].notna()]
            if not sub.empty:
                print(f"  {method:<14} {int(sub['llm_calls'].sum())} calls over {len(sub)} problems")

    print("\nNote: n is small. Treat single-problem differences as noise, not signal.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
