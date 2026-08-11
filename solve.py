"""CLI: run the self-correcting agent on a single ad-hoc prompt.

Note the honesty caveat that applies to this entry point specifically: with no
canonical tests on disk, the test suite is LLM-written (see
agent/nodes/test_generator.py). A "passed" here means "passed tests the model
wrote for itself" -- useful for iterating, NOT a benchmark result. Numbers
reported in the README come from eval/run_eval.py, which uses hand-written
tests only.
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from agent.graph import run_agent
from agent.state import Problem


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", help="The coding task, in quotes.")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--show-history", action="store_true", help="Print every attempt.")
    args = parser.parse_args()

    if args.max_attempts < 1:
        parser.error("--max-attempts must be >= 1")

    problem = Problem(id="adhoc", prompt=args.prompt, category="adhoc")
    final = run_agent(problem, max_attempts=args.max_attempts)

    print("=" * 70)
    print(f"status:   {final.status}")
    print(f"attempts: {final.attempt_number}/{final.max_attempts}")
    print("=" * 70)

    if args.show_history:
        for record in final.history:
            print(f"\n--- attempt {record.attempt_number} ---")
            if record.reflection:
                print(f"[diagnosis that guided this attempt]\n{record.reflection}\n")
            print(record.code)
            if record.static_check and not record.static_check.passed:
                print("[static check failed]")
                for issue in record.static_check.issues:
                    print(f"  {issue.kind}: {issue.message}")
            if record.execution and not record.execution.passed:
                print("[tests failed]")
                print(record.execution.stdout[-1000:])
        print("\n" + "=" * 70)
        print("FINAL CODE")
        print("=" * 70)

    print(final.generated_code or "(no code produced)")

    if final.status == "passed":
        print("\nNOTE: tests were LLM-generated for this ad-hoc prompt. Not a benchmark result.")

    return 0 if final.status == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
