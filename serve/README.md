# Hosted demo

Runs the agent live: generate → static gate → sandboxed tests → reflect → retry,
bounded at 3 attempts.

Deploying this is not only about the demo. **The container runs Linux, so
`agent/sandbox.py`'s `RLIMIT_AS` / `RLIMIT_CPU` / `RLIMIT_NPROC` ceilings are
actually enforced** — on Windows they are inert and the project's README lists
them as an unverified design claim. Running `tests/test_sandbox_posix.py` in this
image is what retires that caveat.

---

## Deploy to Hugging Face Spaces

1. Create a Space at <https://huggingface.co/new-space> — **SDK: Docker**, blank
   template. Any visibility.

2. Point it at this repo, or push these files to the Space's own git remote. The
   Space needs `serve/`, `agent/`, and `problems/`, plus a `Dockerfile` at the
   repo root. The simplest route is a root `Dockerfile` that just delegates:

   ```dockerfile
   # Dockerfile at repo root
   FROM python:3.13-slim
   # ... or simply copy serve/Dockerfile to the root, unchanged.
   ```

   `serve/Dockerfile` already builds from the repo root, so copying it to
   `./Dockerfile` works as-is.

3. In the Space: **Settings → Variables and secrets**, add

   | Kind | Name | Value |
   |------|------|-------|
   | Secret | `GROQ_API_KEY` | your Groq key |
   | Variable | `LLM_PROVIDER` | `groq` |
   | Variable | `LLM_MODEL` | `openai/gpt-oss-120b` |
   | Variable | `DAILY_CALL_BUDGET` | `400` (optional) |

   A **Secret**, not a Variable, for the key — Variables are visible in the Space
   UI. If you set no key at all the demo still works: it runs in
   bring-your-own-key mode only.

4. The Space builds and serves on port 7860, which the Dockerfile already
   exposes. First build takes a few minutes.

## Run locally

```bash
pip install -r serve/requirements.txt
uvicorn serve.app:app --host 127.0.0.1 --port 7860
```

Or in Docker, which is the only way to exercise the POSIX sandbox path:

```bash
docker build -f serve/Dockerfile -t selfcorrect-demo .
docker run --rm -p 7860:7860 -e GROQ_API_KEY=... -e LLM_MODEL=openai/gpt-oss-120b selfcorrect-demo
```

---

## What protects the endpoint

This is a public URL that spends money and executes model-written code, so the
controls are deliberate rather than incidental.

| Control | Value | Why |
|---|---|---|
| Per-IP rate limit | 4 runs / 10 min | Blunts casual abuse |
| Shared daily budget | 400 LLM calls | When spent, the demo asks for a visitor key instead of continuing to spend yours |
| Prompt length | 1200 chars | Caps input tokens per request |
| `max_attempts` | 3, server-side | The client cannot raise it |
| Concurrency | 1 run at a time | See below |
| Queue wait | 45 s, then 503 | Requests fail fast rather than piling up |

**Concurrency is capped at one for a specific reason, not for simplicity.**
`agent/sandbox.py` sets rlimits through `preexec_fn`, which runs between `fork`
and `exec`. Forking from a multi-threaded process to do that is the classic
deadlock, and FastAPI runs sync endpoints in a threadpool. A semaphore of one is
held across each agent run so the fork always happens from a quiet process. It
also bounds concurrent LLM spend, but that is the secondary benefit.

### Visitor keys

A key supplied by a visitor is used for exactly one request and never persisted.
It travels in a `ContextVar`, **not** in `AgentState` — state is serialised into
history records and run files, so a credential placed there would leak into logs
and saved output. BYOK clients also bypass the LLM client cache, so one visitor's
key can never be handed to the next request. Provider errors are caught and
replaced with a generic message, because an upstream error body can echo the key.

Verified locally: an invalid key returns a generic 500 with the key absent from
both the response and the server log.

### Residual risk, stated plainly

The sandbox bounds CPU, memory, process count, and wall-clock time. It does
**not** isolate the network — generated code could open a socket. Container
isolation is the outer boundary. For a demo running short Pydantic snippets this
is a reasonable trade; for anything higher-stakes, add network egress rules.

---

## Honesty constraint the demo carries

Ad-hoc prompts have no hand-written tests, so the agent writes its own — the model
is partly grading itself. The API response sets `tests_are_llm_written: true` and
the UI says so on the page and again on the result.

**Nothing from this demo backs any number in the project's README.** Those come
from `eval/run_eval.py`, which uses hand-written tests exclusively.
