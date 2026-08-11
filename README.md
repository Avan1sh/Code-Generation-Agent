# selfcorrect-agent

A LangGraph agent that generates Pydantic v2 code, detects its own failures, and
retries with a diagnosis — evaluated against two baselines under a fixed compute
budget.

**The Results section below is empty on purpose.** No numbers are written here
until `eval/run_eval.py` has actually been run and `eval/analyze.py` has produced
them. See [Reporting rules](#reporting-rules).

---

## Why these choices

### Why a mid-tier model, not a frontier model

The LLM is a mid-tier model (Groq-hosted Llama 3.1 8B, or Gemini Flash) — chosen
deliberately, not to save money.

A frontier model would solve most of this eval set zero-shot. The single-shot
baseline would sit near ceiling, the correction loop would have almost nothing to
correct, and any measured "improvement" would be indistinguishable from run-to-run
noise. Deliberately using a weaker model leaves measurable headroom between the
floor and the ceiling — which is the only condition under which the central
question (*does directed self-correction beat undirected resampling at equal
compute?*) has an answerable form.

### Why Pydantic v2 as the target domain

Pydantic's v1→v2 migration is an unusually clean failure mode to study. Enormous
amounts of v1 code exist in training data, the v1 API is still the model's
statistical default, and v1 constructs fail in v2 in a *diagnosable* way:
`@validator` is not registered, `.dict()` does not exist, `class Config` is
silently ignored. That gives a genuine, reproducible, root-causable error class —
rather than the diffuse "sometimes the model is just wrong" failures of a generic
benchmark.

The eval set probes twelve specific traps:

| # | Problem | v1 trap being probed |
|---|---------|----------------------|
| 001 | `field_validator` | `@validator` instead of `@field_validator` |
| 002 | `model_dump` | `.dict()` / `.json()` |
| 003 | `config_dict` | `class Config:` instead of `ConfigDict` |
| 004 | `model_validator` | `@root_validator` |
| 005 | `model_validate` | `.parse_obj()` / `.parse_raw()` |
| 006 | `computed_field` | plain `@property`, excluded from output |
| 007 | `field_serializer` | `json_encoders` in `Config` |
| 008 | `alias` | `allow_population_by_field_name` |
| 009 | `discriminated_union` | plain `Union` without a discriminator |
| 010 | `constraints` | `regex=` instead of `pattern=`; `conint`/`constr` |
| 011 | `type_adapter` | `parse_obj_as()`, removed in v2 |
| 012 | `before_validator` | `@validator(pre=True)` |

---

## Architecture

```
test_gen ──> generate ──> static_check ──pass──> execute ──pass──> END
                 ^              │                     │
                 │           fail│                fail │
                 │              ▼                     ▼
                 └────────── reflect <────────────────┘
                        (only while attempts remain)
```

| Node | File | Does |
|------|------|------|
| `test_gen` | [test_generator.py](agent/nodes/test_generator.py) | Loads hand-written tests from disk (or LLM-writes them for ad-hoc prompts) |
| `generate` | [generator.py](agent/nodes/generator.py) | Produces code; on retry, carries prior code + failure evidence + diagnosis |
| `static_check` | [static_check.py](agent/nodes/static_check.py) | `ast` + `pyflakes` + v1 anti-pattern scan. No LLM, no cost |
| `execute` | [executor.py](agent/nodes/executor.py) | Runs the tests in a sandboxed subprocess |
| `reflect` | [reflector.py](agent/nodes/reflector.py) | One LLM call: root cause + fix direction, **not** code |

State is a Pydantic v2 model ([state.py](agent/state.py)) — not a dict with string
keys — so every node transition is runtime-validated.

`test_gen` runs **once**, before the loop. Regenerating tests per attempt would let
the success criterion drift under a failing solution.

The `reflect` node is prompted to diagnose and explicitly forbidden from emitting
code. If it wrote code it would just be a second generator, and the eval would no
longer isolate whether the reflection step contributes anything.

### Termination

The "no unbounded loops" claim rests on three things, in order of importance:

1. **Node-level guards.** `static_check_node` and `executor_node` each compare
   `attempt_number >= max_attempts` themselves and write a terminal status. The
   conditional edges only *read* that status — routers never decide termination.
2. **A monotonic counter.** `attempt_number` is incremented by `generate` on every
   pass and never decremented anywhere, so (1) is guaranteed to fire within
   `max_attempts` generations regardless of model output.
3. **`recursion_limit` as a backstop only.** Set above the worst-case node count,
   so hitting it means a wiring bug. It is *not* the guarantee: it raises
   `GraphRecursionError` (a crash) rather than producing a clean terminal state.

This is tested, not asserted: [tests/test_graph_termination.py](tests/test_graph_termination.py)
runs the graph with a stub LLM that **always** emits broken code — the worst case,
a model that never self-corrects — and checks the bound holds at
`max_attempts` 1, 2, and 3, on both the static-failure and test-failure paths.

### Sandboxing

Generated code is **never** passed to `exec()` or `eval()`. It is written to a
temporary directory and run under `pytest` in a subprocess
([sandbox.py](agent/sandbox.py)), with:

- a wall-clock timeout (all platforms), and
- `RLIMIT_AS` / `RLIMIT_CPU` / `RLIMIT_NPROC` via `resource.setrlimit` (**POSIX only**).

See [Limitations](#limitations) — the Windows gap is real and is recorded in every
run's metadata.

**The sandbox proves itself healthy before the eval spends anything.**
`verify_sandbox_health()` runs known-good Pydantic code through the sandbox under
the configured limits, and `run_eval.py` calls it before the first API call.

This guards a failure mode that would otherwise be invisible and badly
misattributed: `RLIMIT_AS` caps *virtual address space*, which CPython plus
`pydantic-core` reserve far more of than they make resident. A ceiling that looks
reasonable ("a solution shouldn't need 256 MB") can be too small for the
interpreter itself — in which case **every** problem fails, the eval reports 0
passes across all three methods, and it reads as a model failure rather than a
misconfigured sandbox. The check turns that into a loud, self-describing error
before any budget is spent. `DEFAULT_MEMORY_MB` is deliberately generous for the
same reason: it exists to stop unbounded allocation, not to enforce a tight
budget.

---

## Evaluation design

Three methods, run in the **same process, same invocation, same model snapshot**:

| Method | What it is | Role |
|--------|-----------|------|
| `single_shot` | One generation, one test run, no correction | **Floor.** The number to beat |
| `best_of_n` | N independent samples at temp 0.8, passes if *any* sample passes | **Oracle ceiling.** Not deployable |
| `self_correct` | The agent above | The thing being measured |

**`single_shot` uses the same system prompt and temperature as the agent's attempt
1.** If it didn't, a measured gap would confound "the loop helped" with "the retry
prompt was just better."

**`best_of_n` is an oracle, and is labelled as one everywhere.** Reporting pass@N
requires knowing which sample passed, which at inference time means already having
the tests. It is included because it is *compute-matched* — N is set to
`max_attempts`, so both spend a comparable generation budget. That makes the real
question answerable: at equal cost, does **directed** correction (reflect on the
actual error) beat **undirected** resampling (roll again)? If `self_correct` lands
near pass@N, the loop is extracting most of the available headroom. If it lands
near `single_shot`, the reflection step is not earning its cost.

### The eval set validates itself

If a problem's tests were broken or the task impossible as written, every method
would score 0 on it and it would look like model failure rather than an authoring
bug. [tests/test_problem_set.py](tests/test_problem_set.py) rules this out, with no
API key required:

- every problem has a hand-written `reference.py` that **passes its own tests** in
  the same sandbox the agent uses;
- every reference solution **passes the static check** — proving the v1 detector
  has no false positives that would reject correct answers;
- no `prompt.md` **leaks a v2 API name** (`field_validator`, `ConfigDict`, …),
  which would turn the eval into an instruction-following test instead of a test
  of v2 knowledge.

`reference.py` is never shown to the model — only `prompt.md` is.

### Reporting rules

These are enforced by [analyze.py](eval/analyze.py), not just by intent:

- **Raw counts always accompany rates.** `9/12 (75.0%)`, never `75%`. With n=12,
  one problem is 8.3 points.
- **Paired per-problem deltas**, not just aggregates. A net +0 can hide the loop
  fixing one problem and breaking another; `analyze.py` prints `fixed by the loop`
  and `broken by the loop` separately.
- **Errored runs count as failures**, never dropped — a dropped row silently
  shrinks the denominator and inflates every rate.
- **It refuses to print** a summary when the results file is missing or empty,
  rather than emitting an empty table that could be mistaken for a measurement.
- **Cost is reported alongside quality**, since `self_correct` spends more calls
  than `single_shot` by construction.

---

## Setup

```bash
python -m venv .venv && ./.venv/Scripts/activate  # Windows
pip install -r requirements.txt
```

Requires Python 3.11+. Set your provider in a `.env`:

```bash
LLM_PROVIDER=groq          # or: gemini
GROQ_API_KEY=...           # or: GOOGLE_API_KEY=...
LLM_MODEL=llama-3.1-8b-instant   # optional override
```

Optional LangSmith tracing (activates via env vars alone, no code change):

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=...
LANGCHAIN_PROJECT=selfcorrect-agent
```

## Running

Tests that need **no API key** — the sandbox, the static checker, the termination
proof, the sandbox health guard, and the eval-set validation:

```bash
pytest -q
```

On Windows, the POSIX resource-limit tests report as skipped; that is expected and
is the limitation described below, not a passing result.

Run the agent on one ad-hoc prompt:

```bash
python solve.py "Write a Pydantic model Config with a validated port field" --show-history
```

Run the full evaluation, then analyse it:

```bash
python eval/run_eval.py --max-attempts 3
```

```bash
python eval/analyze.py
```

`run_eval.py` writes one JSON line per (problem, method) to `results/run_<ts>.jsonl`
and aggregates nothing. Measurement and analysis are separate so the raw record
survives a wrong analysis, and so numbers can be recomputed without re-spending API
budget.

---

## Results

*Not yet run.* This section will be populated from an actual
`eval/run_eval.py` + `eval/analyze.py` run — headline counts, paired
fixed/broken breakdown, per-category results, attempt distribution, and LLM-call
cost per method. No numbers appear here before that run exists.

---

## Limitations

- **The Windows sandbox is weaker than the POSIX one.** `resource.setrlimit` does
  not exist on Windows, so on Windows there is *no* memory ceiling, *no* CPU
  ceiling, and *no* process-count ceiling — only a wall-clock timeout. Generated
  code can still open sockets and touch the filesystem on any platform. Each run
  records `posix_resource_limits_active` in its metadata, because results are not
  fully comparable across operating systems. For a stronger guarantee, run under
  WSL/Linux or in a container.
- **The POSIX resource-limit path has not been executed on the machine this was
  built on** (Windows only, no Linux runtime available). Its tests exist and are
  correct, but they are `skipif`-ed on Windows and have therefore never run — so
  "the memory and CPU ceilings work" is currently a *design* claim, not a measured
  one. [tests/test_sandbox_posix.py](tests/test_sandbox_posix.py) will exercise it
  on any Linux CI runner or container; until that has run, treat the POSIX limits
  as unverified. `verify_sandbox_health()` is the mitigation: even unverified, a
  ceiling too tight to run valid code fails loudly at startup instead of silently
  zeroing the eval.
- **n = 12.** Single-problem differences are noise. `analyze.py` says so on every
  report.
- **The eval set is hand-authored by one person** and probes traps chosen in
  advance. It measures what it was built to measure — v1-vs-v2 API knowledge — not
  general code generation ability.
- **`solve.py` results are not benchmark results.** Ad-hoc prompts have no
  canonical tests, so the tests are LLM-written and the model is partly grading
  itself. Only `eval/run_eval.py`, which uses hand-written tests exclusively, backs
  any reported number.
- **The v1 anti-pattern detector is regex-based** and line-oriented. It will flag
  `.dict(` inside a string literal or comment. This is a deliberate
  precision-vs-simplicity trade-off: a false positive costs one wasted retry, while
  a false negative lets the exact failure mode under study slip through to the
  sandbox undiagnosed.
- **`best_of_n` is an oracle** and is not achievable at inference time. It bounds
  the headroom; it is not a competitor the agent is expected to match.
