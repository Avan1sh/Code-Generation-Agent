"""Runs all three methods over the problem set and writes raw per-problem records.

Methodology notes that the results depend on:

  - All three methods run in the SAME process against the SAME problem set with
    the SAME model in a single invocation. A baseline measured in a different
    run, against a different model snapshot, is not a baseline -- provider-side
    model updates alone can move the number.
  - Nothing is aggregated here. This script emits one JSON line per
    (problem, method) with the raw outcome; eval/analyze.py does the counting.
    Keeping measurement and analysis separate means the raw record survives even
    if the analysis is wrong, and lets the numbers be recomputed without
    re-spending API budget.
  - Failures are recorded, not skipped. A crashed run writes `error` and
    `passed: false` rather than vanishing, so the denominator stays honest.

Retry note: the `max_retries` on the LLM clients (agent/llm.py) handles
transient API errors. That is a DIFFERENT mechanism from the self-correction
loop -- it has no feedback signal and exists only for network flakiness. Do not
conflate the two when reading the results.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Running this as a script path (`python eval/run_eval.py`, as documented in the
# README) puts eval/ on sys.path rather than the repo root, so `import agent`
# fails. Prepending the repo root makes both that form and `python -m
# eval.run_eval` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.graph import run_agent  # noqa: E402
from agent.llm import LLMUnavailableError, verify_llm_available  # noqa: E402
from agent.sandbox import SandboxHealthError, verify_sandbox_health  # noqa: E402
from agent.state import Problem  # noqa: E402
from agent.usage import track_usage  # noqa: E402
from baselines.best_of_n import run_best_of_n  # noqa: E402
from baselines.single_shot import run_single_shot  # noqa: E402
from problems import load_problems  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


def _run_self_correct(problem: Problem, max_attempts: int) -> dict:
    final = run_agent(problem, max_attempts=max_attempts)

    # LLM calls: one generate per attempt, plus one reflect per failed attempt
    # that was followed by another attempt. Counted from history rather than
    # assumed, so the cost column reflects what actually happened.
    generate_calls = len(final.history)
    reflect_calls = max(0, len(final.history) - 1)

    return {
        "passed": final.status == "passed",
        "status": final.status,
        "attempts_used": final.attempt_number,
        "llm_calls": generate_calls + reflect_calls,
        "code": final.generated_code or "",
        "attempts": [
            {
                "attempt_number": r.attempt_number,
                "static_passed": r.static_check.passed if r.static_check else None,
                "static_issues": [
                    {"kind": i.kind, "message": i.message} for i in (r.static_check.issues if r.static_check else [])
                ],
                "execution_passed": r.execution.passed if r.execution else None,
                "timed_out": r.execution.timed_out if r.execution else None,
                "reflection": r.reflection,
            }
            for r in final.history
        ],
    }


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument(
        "--methods",
        nargs="+",
        default=["single_shot", "best_of_n", "self_correct"],
        choices=["single_shot", "best_of_n", "self_correct"],
    )
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N problems.")
    parser.add_argument(
        "--only",
        nargs="+",
        default=None,
        help="Run only problems whose id contains any of these substrings.",
    )
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    if args.max_attempts < 1:
        parser.error("--max-attempts must be >= 1")

    # Checked BEFORE any API call. A sandbox that cannot run known-good code
    # would report every method as 0 passes, which reads as a model failure
    # rather than a configuration one -- and would burn the whole API budget
    # producing a meaningless result file.
    try:
        verify_sandbox_health()
    except SandboxHealthError as exc:
        print(f"Sandbox health check FAILED -- aborting before spending API budget.\n\n{exc}", file=sys.stderr)
        return 2

    # Same rationale as the sandbox check, one call instead of the whole run: a
    # retired model ID fails every request identically and would otherwise
    # produce a 0/N result file that looks like a measurement rather than an
    # outage. This is not hypothetical -- it happened, twice, on 2026-08-20.
    try:
        verify_llm_available()
    except LLMUnavailableError as exc:
        print(f"LLM preflight FAILED -- aborting before spending API budget.\n\n{exc}", file=sys.stderr)
        return 3


    problems = load_problems()
    if args.only:
        problems = [p for p in problems if any(frag in p.id for frag in args.only)]
    if args.limit is not None:
        problems = problems[: args.limit]
    if not problems:
        print("No problems found.", file=sys.stderr)
        return 1

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = Path(args.out) if args.out else RESULTS_DIR / f"run_{stamp}.jsonl"

    run_meta = {
        "record_type": "run_meta",
        "timestamp_utc": stamp,
        "provider": os.environ.get("LLM_PROVIDER", "groq"),
        "model": os.environ.get("LLM_MODEL", "(provider default)"),
        "max_attempts": args.max_attempts,
        "best_of_n_n": args.max_attempts,
        "methods": args.methods,
        "n_problems": len(problems),
        # Recorded so a filtered run cannot be read as a full-set result.
        "problem_ids": [p.id for p in problems],
        "subset_filter": args.only,
        "python": platform.python_version(),
        "platform": platform.platform(),
        # Recorded because the sandbox enforces different guarantees per OS
        # (see agent/sandbox.py) -- results are not fully comparable across them.
        "posix_resource_limits_active": sys.platform != "win32",
    }

    with out_path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(run_meta) + "\n")

        total = len(problems) * len(args.methods)
        done = 0

        for problem in problems:
            test_code = Path(problem.canonical_tests_path).read_text(encoding="utf-8")

            for method in args.methods:
                done += 1
                print(f"[{done}/{total}] {problem.id} :: {method}", flush=True)

                record = {
                    "record_type": "result",
                    "problem_id": problem.id,
                    "category": problem.category,
                    "difficulty": problem.difficulty,
                    "method": method,
                }
                start = time.monotonic()

                # Token accounting is scoped per (problem, method) so cost can
                # be attributed, not just totalled. See agent/usage.py.
                with track_usage() as usage:
                    try:
                        if method == "single_shot":
                            r = run_single_shot(problem, test_code)
                            record.update(passed=r.passed, llm_calls=r.llm_calls, code=r.code, attempts_used=1)
                        elif method == "best_of_n":
                            r = run_best_of_n(problem, test_code, n=args.max_attempts)
                            record.update(
                                passed=r.passed,
                                llm_calls=r.llm_calls,
                                code=r.code,
                                samples_passed=r.samples_passed,
                                attempts_used=r.llm_calls,
                            )
                        else:
                            record.update(_run_self_correct(problem, args.max_attempts))
                    except Exception:
                        # Recorded, not skipped -- a dropped row would silently
                        # shrink the denominator and inflate every rate.
                        record.update(passed=False, error=traceback.format_exc(limit=5), llm_calls=None)

                record["usage"] = usage.as_dict()
                record["duration_sec"] = round(time.monotonic() - start, 2)
                handle.write(json.dumps(record) + "\n")
                handle.flush()

    print(f"\nRaw records written to: {out_path}")
    print(f"Now run: python eval/analyze.py {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
