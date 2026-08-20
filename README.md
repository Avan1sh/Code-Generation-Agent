# selfcorrect-agent

[![tests](https://github.com/Avan1sh/Code-Generation-Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Avan1sh/Code-Generation-Agent/actions/workflows/ci.yml)

**[Results and methodology](https://avan1sh.github.io/Code-Generation-Agent/)** · **[Try the static gate](https://avan1sh.github.io/Code-Generation-Agent/try.html)** · **[Run the agent live](https://selfcorrect-agent-demo.onrender.com)**

A LangGraph agent that generates Pydantic v2 code, detects its own failures, and
retries with a diagnosis — evaluated against two baselines under a fixed compute
budget.

**Headline result: the correction loop scored 30/30 against a 26/30 baseline —
but only +1 of that gap is attributable to the correction step.** The rest is
temperature-0 sampling variance and one rate-limited baseline call. The
decomposition, and the measured ~3-problem noise floor that makes the +1
uninterpretable, are in [Results](#results). Every number here comes from a
committed run file; none is estimated. See [Reporting rules](#reporting-rules).

---

## Why these choices

### Why a mid-tier model, not a frontier model

The LLM is a mid-tier open-weights model (currently `openai/gpt-oss-120b` on
Groq) — chosen deliberately, not to save money.

A frontier model would solve most of this eval set zero-shot. The single-shot
baseline would sit near ceiling, the correction loop would have almost nothing to
correct, and any measured "improvement" would be indistinguishable from run-to-run
noise. Deliberately using a weaker model leaves measurable headroom between the
floor and the ceiling — which is the only condition under which the central
question (*does directed self-correction beat undirected resampling at equal
compute?*) has an answerable form.

**Calibrating that is harder than it sounds, and this project missed in both
directions.** `llama-3.1-8b-instant` was *too weak*: its oracle ceiling was 1/12,
so the eval had no discriminating power at all (Run 1). `openai/gpt-oss-120b` is
*too strong*: it solves 26/30 zero-shot, leaving only 4 problems of headroom
(Run 3). Only `llama-3.3-70b-versatile` landed in a measurable band — and Groq
retired it mid-project, so that band is no longer reachable.

Every run is kept, including the unflattering ones. The mis-calibrations are the
record of how the measurable band was located, and deleting them would leave the
model choice looking arbitrary.

**The honest current status: the eval set needs harder problems to regain
headroom at this model tier.** That is a property of the eval, not a result about
self-correction.

### Why Pydantic v2 as the target domain

Pydantic's v1→v2 migration is an unusually clean failure mode to study. Enormous
amounts of v1 code exist in training data, the v1 API is still the model's
statistical default, and v1 constructs fail in v2 in a *diagnosable* way:
`@validator` is not registered, `.dict()` does not exist, `class Config` is
silently ignored. That gives a genuine, reproducible, root-causable error class —
rather than the diffuse "sometimes the model is just wrong" failures of a generic
benchmark.

The eval set probes 40 specific v1 habits and v2 semantics — 7 easy, 12 medium,
21 hard, 185 assertions total. Problems 031–040 were added after Run 3 showed the
set was ceiling-limited; see [Run 4](#run-4--hard-problem-calibration-check-openaigpt-oss-120b-n11)
for how well that worked. Each problem ships a hand-written `reference.py`
proving it is solvable (see [The eval set validates itself](#the-eval-set-validates-itself)).

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
| 013 | `optional_default` | v1 made `Optional[X]` implicitly default to `None` |
| 014 | `validation_info` | validator `values` dict to `ValidationInfo.data` |
| 015 | `root_model` | `__root__` field to `RootModel` base class |
| 016 | `copy` | `.copy(update=...)` to `.model_copy(update=...)` |
| 017 | `json_schema` | `.schema()` to `.model_json_schema()` |
| 018 | `construct` | `.construct()` to `.model_construct()` |
| 019 | `sequence_length` | `min_items`/`max_items` to `min_length`/`max_length` |
| 020 | `validate_default` | `@validator(always=True)` to `Field(validate_default=True)` |
| 021 | `self_reference` | `update_forward_refs()` to `model_rebuild()` |
| 022 | `literal_const` | `Field(const=True)`, removed in v2, to `Literal` |
| 023 | `enum_values` | `use_enum_values` via `class Config` |
| 024 | `serialization_alias` | v1 had one alias; v2 splits validation/serialization |
| 025 | `default_factory` | mutable default shared across instances |
| 026 | `exclude_none` | `.dict(exclude_none=True)` |
| 027 | `strict` | v1 coerced `"5"` to `5`; v2 strictness is opt-in |
| 028 | `nested_update` | `.copy(update=...)` on nested models |
| 029 | `model_validator_before` | `@root_validator(pre=True)` |
| 030 | `alias_choices` | v1 allowed one alias per field; v2 needs `AliasChoices` |

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

**These ceilings are verified, not assumed.** They were a design claim for most of
this project's life, because development happened on Windows where
`resource.setrlimit` does not exist and
[tests/test_sandbox_posix.py](tests/test_sandbox_posix.py) was permanently
skipped. CI now runs on `ubuntu-latest`, where those tests execute for real —
proving the ceilings both *permit* valid code and *stop* a runaway allocation
without falling back on the wall clock. The workflow **fails the build if those
tests skip**, since a skipped test still exits 0 and a green run would otherwise
prove nothing.

The hosted demo is the second confirmation: it reports
`posix_resource_limits_active: true` and a measured startup probe of **17.1s**
against its 45s budget.

See [Limitations](#limitations) — the Windows gap is still real for local runs and
is recorded in every run's metadata.

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
  than `single_shot` by construction. Cost is measured in **actual input/output
  tokens**, not just call counts: a reflection call carries the failing code plus
  a pytest traceback, so it is far more expensive than a first-attempt
  generation, and "54 calls" hides that. The headline cost figure is **tokens per
  solved problem** — a method can look cheap in total while being expensive per
  unit of work delivered. If any call returns no usage metadata, the totals are
  labelled a lower bound rather than reported as if complete.

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

Runs are committed in `results/` as raw JSONL. Reproduce with
`python eval/analyze.py results/<file>`.

### Run 3 — `openai/gpt-oss-120b`, max_attempts=3, n=30 (current)

`results/run_20260820T054643Z.jsonl`

| Method | Solved | Calls | Total tokens | Tokens / solve |
|--------|--------|-------|--------------|----------------|
| `single_shot` (pass@1 floor) | **26/30** | 29 | 20,955 | 805 |
| `best_of_n` (pass@3 oracle) | **28/30** | 90 | 65,732 | 2,347 |
| `self_correct` (agent) | **30/30** | 32 | 24,365 | 812 |

**Do not read the headline as "+4 problems, 100%".** Decomposing where those 4
came from is the whole result, and it does not survive the obvious question
*"how many did the correction step actually fix?"*

| Problem `single_shot` missed | How `self_correct` got it | Attributable to the loop? |
|------------------------------|---------------------------|---------------------------|
| `pyd_011_type_adapter` | attempt 1 — baseline had hit a **429 rate limit** | **No** — infrastructure |
| `pyd_014_validation_info` | attempt 1, no correction run | **No** — sampling variance |
| `pyd_015_root_model` | attempt 1, no correction run | **No** — sampling variance |
| `pyd_020_validate_default` | **attempt 2, after reflection** | **Yes** |

**The correction loop's genuine contribution is +1 problem out of 30, not +4.**
29 of the agent's 30 solves came on attempt 1, which is prompt-identical to
`single_shot` and involves no reflection at all. Only `pyd_020` was actually
repaired by the loop.

#### The confound this quantifies

`single_shot` and the agent's attempt 1 use the same prompt, same model, and
temperature 0 — yet they diverged on **3 of 30 problems**. Provider-side
batching makes temperature 0 non-deterministic, and this run puts a number on
it: roughly a 10% per-problem disagreement rate between calls that should be
identical.

That matters beyond this project. **Any A/B result smaller than ~3 problems at
this n is inside the noise floor of the harness itself**, regardless of how
carefully the two arms are matched. The measured +1 from the loop is well inside
it. The honest conclusion is that this run does not establish that the loop
helps, only that it did not hurt (0 problems broken).

#### The eval set is now ceiling-limited

At 26/30 the baseline sits near ceiling, leaving 4 problems of headroom. This is
the *opposite* failure of Run 1, where the ceiling was pinned at the floor — but
it damages measurement the same way: with almost nothing left to fix, the
correction loop has almost nothing to demonstrate. `best_of_n` passed 80 of 90
individual samples, confirming the model finds these problems easy rather than
the eval being noisy.

**This eval set no longer discriminates at this model tier.** Recovering
headroom needs harder problems, not more of the same difficulty.

#### Cost

`self_correct` costs essentially the same as `single_shot` per solved problem
(812 vs 805 tokens) because 29/30 needed no correction — the loop only spends
when it fails. `best_of_n` costs **2.9×** per solve, since it always draws all
three samples whether or not the first worked. That is the clearest cost result
here: **undirected resampling is the expensive strategy, and it scored lower
than the agent.**

### Run 4 — hard-problem calibration check, `openai/gpt-oss-120b`, n=11

`results/run_20260820T061750Z.jsonl` (problems 030–040 only, via `--only`)

Ten new problems were written specifically to defeat this model, after Run 3
showed the eval was ceiling-limited. **The attempt largely failed, and that is
the result:**

| Method | Solved | Tokens / solve |
|--------|--------|----------------|
| `single_shot` | **9/11** (81.8%) | 1,188 |
| `best_of_n` (oracle) | **10/11** (90.9%) | 3,180 |
| `self_correct` | **9/11** (81.8%) | 2,819 |

Baseline moved from 86.7% (Run 3) to 81.8% — **barely harder**. The model
comfortably handles wrap validators, `model_post_init` with private attributes,
`model_fields_set`/`exclude_unset`, plain `Generic[T]` models, `alias_generator`,
wrap serializers, and `extra="allow"` with `__pydantic_extra__`. The loop again
netted +0.

**This is the third calibration miss**: too weak (Run 1), too strong (Run 3),
still too easy (Run 4). Recorded rather than quietly re-tuned, because the
pattern is the finding — writing problems this model fails in this domain is
genuinely difficult.

#### The two that did work, and why

Only `pyd_032` and `pyd_037` defeated the baseline; `pyd_037` defeated **every
method including the oracle**. Both share one property, and it is the generative
principle worth reusing:

> **The obvious answer looks correct, is silently accepted, and silently does
> nothing.**

- `pyd_032_serialize_as_any` — the model wrote
  `model_config = ConfigDict(serialize_as_any=True)`. `serialize_as_any` is *not*
  a `ConfigDict` key, but `ConfigDict` is a `TypedDict`, so the key is accepted
  at runtime, stored in `model_config`, and has **no effect**. No error, no
  warning; the subclass field is just missing from the output. The working
  answers are `SerializeAsAny[Animal]` on the field or the runtime
  `model_dump(serialize_as_any=True)` flag.
- `pyd_037_custom_error` — the model reached for `PydanticErrorMixin` from
  `pydantic.errors`, a real but internal API, rather than `PydanticCustomError`
  from `pydantic_core`. Plausible, importable, wrong.

Problems that merely ask *"which v2 name replaced this v1 name?"* are a lookup
this model performs reliably. Problems where a plausible construct is accepted
and silently misbehaves are the ones with discriminating power.

#### Honest status of the eval set

**Pydantic v2 is close to exhausted as a discriminating domain at this model
tier.** Forty problems now yield roughly 4–6 failures, which is not enough
headroom to measure a correction loop against. Restoring measurement needs one
of:

1. more problems built on the silent-failure principle above (the only approach
   shown to work here, at roughly a 2-in-11 hit rate);
2. a weaker model — but Groq has retired both Llama tiers, so the previously
   measurable band is no longer reachable;
3. a different, harder domain.

None of these is a result about self-correction. Stating that plainly is more
useful than continuing to tune until a favourable number appears.

### Runs 1 and 2 — Llama models, n=12 (historical, NOT reproducible)

`results/run_20260811T123858Z.jsonl` (`llama-3.1-8b-instant`) and
`results/run_20260816T212101Z.jsonl` (`llama-3.3-70b-versatile`).

| Run | Model | single_shot | best_of_n | self_correct |
|-----|-------|-------------|-----------|--------------|
| 1 | llama-3.1-8b-instant | 1/12 | 1/12 | 0/12 |
| 2 | llama-3.3-70b-versatile | 3/12 | 4/12 | 3/12 |

**Groq retired both model IDs on 2026-08-20, mid-project.** These runs can never
be reproduced or extended. They are kept because they are evidence, and because
the retirement is itself the clearest possible demonstration of the caveat in
`run_eval.py`: provider-side changes alone can move a number, which is why all
three methods must run in one process against one model snapshot.

Run 1 is reported despite being unflattering: with the oracle ceiling itself at
1/12, no method could have scored meaningfully higher, so it measured nothing.
Run 2's finding — the loop nets +0, fixing one problem and breaking another —
stands as recorded.

Two `FAILED_*_model_404.jsonl` files are also kept. Those are the 30-problem runs
that hit the retirement: 90/90 rows errored and `analyze.py` printed `0/30`
across all three methods, which reads exactly like a catastrophic model result.
They are named so the analysis glob cannot mistake them for measurements, and
they are why `verify_llm_available()` now runs before any budget is spent.

### Caveats that limit these numbers

- **n = 30, and the harness noise floor is ~3 problems** (measured above). Only
  differences larger than that are interpretable. The loop's +1 is not.
- **Ceiling-limited.** At 86.7% baseline there is little room to improve, so this
  run cannot strongly support or refute the hypothesis either way.
- **Single run per configuration.** No seed variance, no repeated trials. Point
  estimates only.
- **One row hit a 429 rate limit** and is counted as a failure, which is correct
  for an honest denominator but understates `single_shot` by one problem. On the
  model's own merits the baseline is arguably 27/30.
- **Model changed mid-project under duress**, not by choice. Results are not
  comparable across runs 1–2 and run 3.
- Windows sandbox: `posix_resource_limits_active: false` in every run.
- **Runs 1 and 2 have no token data**; they predate the usage instrumentation and
  `analyze.py` says so rather than printing zeros.

## Limitations

- **The Windows sandbox is weaker than the POSIX one.** `resource.setrlimit` does
  not exist on Windows, so on Windows there is *no* memory ceiling, *no* CPU
  ceiling, and *no* process-count ceiling — only a wall-clock timeout. Generated
  code can still open sockets and touch the filesystem on any platform. Each run
  records `posix_resource_limits_active` in its metadata, because results are not
  fully comparable across operating systems. For a stronger guarantee, run under
  WSL/Linux or in a container.
- **The sandbox does not isolate the network.** It bounds CPU, memory, process
  count, and wall-clock time — all now verified on Linux — but generated code
  could still open a socket. Container isolation is the outer boundary. This is
  the one sandbox guarantee that remains unproven, and it is unproven because it
  does not exist, not because it is untested.
- **Local Windows runs still have no memory or CPU ceiling**, only a wall-clock
  timeout, since `resource.setrlimit` is POSIX-only. Every run file records
  `posix_resource_limits_active` for this reason, and results are not strictly
  comparable across operating systems.
- **The sandbox timeout is hardware-dependent.** The 10s default suits a
  developer machine; on constrained shared hosting it is far too short, and a
  valid solution then reports `timed_out` — which reads as the model writing an
  infinite loop. `SANDBOX_TIMEOUT_SEC` makes it configurable and
  `/api/status` reports the measured probe duration so the value can be set from
  data. This was found the hard way on the live demo, where the probe takes
  **17.1s** against the 1.7s measured locally.
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
