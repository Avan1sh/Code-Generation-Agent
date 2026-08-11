"""Eval-set loader.

Layout per problem directory:
    prompt.md     -- the task text handed to the model (the ONLY file it sees)
    tests.py      -- hand-written canonical tests, the ground-truth signal
    meta.json     -- id, category, difficulty, and the v1 trap being probed
    reference.py  -- a known-good v2 solution, used only to prove the problem is
                     solvable and the tests are not broken. Never shown to the
                     model; see tests/test_problem_set.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent.state import Problem

PROBLEMS_DIR = Path(__file__).parent


def load_problems() -> list[Problem]:
    problems: list[Problem] = []
    for directory in sorted(PROBLEMS_DIR.iterdir()):
        if not directory.is_dir() or directory.name.startswith("_"):
            continue
        meta_path = directory / "meta.json"
        prompt_path = directory / "prompt.md"
        tests_path = directory / "tests.py"
        if not (meta_path.exists() and prompt_path.exists() and tests_path.exists()):
            continue

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        problems.append(
            Problem(
                id=meta["id"],
                prompt=prompt_path.read_text(encoding="utf-8"),
                category=meta["category"],
                difficulty=meta.get("difficulty", "medium"),
                canonical_tests_path=str(tests_path),
            )
        )
    return problems


def problem_dir(problem_id: str) -> Path:
    return PROBLEMS_DIR / problem_id
