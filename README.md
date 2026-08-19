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

**That reasoning cuts both ways, and the first run proved it.** `llama-3.1-8b-instant`
turned out to be *too* weak: its oracle ceiling was 1/12, so the eval had no
discriminating power at all (see [Results](#results), Run 1). The model was moved
up to `llama-3.3-70b-versatile` — still not frontier — on that evidence. Both runs
are kept. The failed calibration is part of the record, not something to delete.

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

Two runs, both committed in `results/` as raw JSONL. Reproduce either with
`python eval/analyze.py results/<file>`.

### Run 2 — `llama-3.3-70b-versatile`, max_attempts=3, n=12

`results/run_20260816T212101Z.jsonl`

| Method | Solved | LLM calls |
|--------|--------|-----------|
| `single_shot` (pass@1 floor) | **3/12** | 12 |
| `best_of_n` (pass@3 oracle ceiling) | **4/12** | 36 |
| `self_correct` (agent) | **3/12** | 54 |

**The self-correction loop produced no net improvement: +0 problems out of 12.**
It fixed one problem the baseline failed (`pyd_005_model_validate`) and broke one
the baseline solved (`pyd_012_before_validator`), for 4.5× the API cost of the
baseline.

**The most informative number is the ceiling, not the agent's score.** The oracle
ceiling sits just **1 problem above the floor** (4/12 vs 3/12), and only 5 of 36
individual samples passed. If the model's failures were *stochastic*, drawing
three samples at temperature 0.8 would have recovered many more. It recovered
one. That means the failures are **systematic knowledge gaps, not sampling
variance** — this model tier does not know the v2 APIs for the 8 unsolved
problems, and it fails them the same way every time.

Neither intervention can fix that. Resampling re-draws from a distribution whose
mass is on the wrong answer; reflection names the correct API, and the model
still does not produce it. This is the honest explanation for +0, and it is a
statement about *where these methods stop working*, not evidence that
self-correction never helps.

#### Test-level resolution (same run, no additional API spend)

`python eval/partial_credit.py results/run_20260816T212101Z.jsonl` re-executes the
stored solutions locally and counts individual assertions. At n=12 a binary
outcome can only express differences of 8.3 points; the 64 assertions underneath
were already paid for and give a finer read.

| Method | Assertions passed |
|--------|-------------------|
| `single_shot` | **18/64** (28.1%) |
| `best_of_n` | **27/64** (42.2%) |
| `self_correct` | **30/64** (46.9%) |

**This is the one place the loop shows a measurable effect: +12 assertions over
the baseline, while scoring +0 problems.** The correction step moves solutions
substantially closer to correct without crossing the threshold — it takes
`pyd_007` from 0/5 to 4/5 and `pyd_008` from 0/5 to 3/5, and both still count as
failures.

Read this as a *descriptive* result and nothing stronger. Assertions within a
problem are correlated — one wrong API call fails several at once — so 64
assertions are not 64 independent samples, and none of this licenses a
significance claim. It is also the metric most flattering to the agent, which is
reason for more scepticism, not less.

#### A methodology bug this surfaced, and its resolution

The test-level pass revealed that `pyd_003`'s stored solution passed every
assertion while the pipeline recorded it as `failed_static` — the static gate and
the canonical tests disagreed about the same code.

Cause: the code used `class Config:`, which **Pydantic v2 still honours for
backwards compatibility**. It populates `model_config` exactly as `ConfigDict`
would, so a test asserting on `model_config` passes for v1-style and v2-style code
alike. The test named `test_config_is_v2_style` did not, in fact, test for v2
style.

The static gate was correct and the test was too weak. Both `pyd_003` and
`pyd_008` now additionally assert `not hasattr(Model, "Config")`, which is what
actually distinguishes the two. After the fix the two signals agree
(`self_correct` tests-only 3/12 = reported 3/12).

This fix changes no headline number — `pyd_003` was already recorded as a failure
for every method — so it corrects the measurement without retroactively reshaping
a reported result. Worth stating explicitly: had it changed the headline, the
honest move would have been to re-run and report both.

Observed failure modes:

- **Non-monotonic correction.** On `pyd_012`, attempt 2 passed the static check
  and failed only on test semantics; attempt 3 then *regressed* to v1 syntax
  (`@field.validator(..., pre=True)`, `class Config:`). The loop can move the
  model backwards, and the agent returns the **last** attempt rather than the
  **best** one — recorded here rather than quietly fixed before reporting.

  Checked against the data before proposing a fix: **no unsolved problem ever had
  an attempt that passed its tests** (a passing attempt terminates the graph
  immediately, so it is always the one returned). Best-attempt selection would
  therefore improve the quality of the returned artifact but could **not** recover
  a single pass. Worth doing on its merits; not worth claiming as a score
  improvement.
- **Where the loop does work.** All 3 of the agent's solves came on attempt 2,
  never attempt 3. Reflection reliably repairs *syntactic* v1→v2 errors on the
  first correction, and reliably fails to repair *semantic* ones thereafter.
- Terminal states for the 9 unsolved: 5 `failed_static`, 4 `failed_tests`.

### Run 1 — `llama-3.1-8b-instant`, max_attempts=3, n=12

`results/run_20260811T123858Z.jsonl`

| Method | Solved | LLM calls |
|--------|--------|-----------|
| `single_shot` | **1/12** | 12 |
| `best_of_n` (oracle) | **1/12** | 36 |
| `self_correct` | **0/12** | 60 |

**This run is reported because it is a real finding, not because it is
flattering: the 8B tier is below the floor at which this eval can measure
anything.** With the oracle ceiling itself at 1/12, no method could have scored
meaningfully higher, so the 0/12-vs-1/12 gap is a one-problem difference that
carries no signal. An eval whose ceiling is pinned near zero has no discriminating
power, and reporting only the headline would have invited the false reading
"self-correction makes things worse."

The model choice was then changed to a larger — but still non-frontier — model on
that basis. Keeping this run visible is the point: it is the evidence for why the
model was changed.

### Caveats that limit these numbers

- **n = 12.** One problem is 8.3 points. Every single-problem difference above,
  including the +0 and both the fix and the break, is within noise.
- **Temperature 0 is not deterministic.** `single_shot` and the agent's attempt 1
  use an identical prompt and temperature, but provider-side batching means they
  can still diverge — as they did on `pyd_012`. The "same first attempt"
  property is approximate, not exact.
- **Single run per configuration.** No seed variance, no repeated trials. These
  are point estimates.
- Windows sandbox: `posix_resource_limits_active: false` in both runs.

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
