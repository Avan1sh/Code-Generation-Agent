# Hosted demo

Runs the agent live: generate → static gate → sandboxed tests → reflect → retry,
bounded at 3 attempts.

Deploying this is not only about the demo. **The container runs Linux, so
`agent/sandbox.py`'s `RLIMIT_AS` / `RLIMIT_CPU` / `RLIMIT_NPROC` ceilings are
actually enforced** — on Windows they are inert and the project's README lists
them as an unverified design claim. Running `tests/test_sandbox_posix.py` in this
image is what retires that caveat.

---

## Deploy to Render (free, no card)

Hugging Face Spaces is **not** an option on a free account any more: as of July
2026 both the Gradio and Docker SDKs require a paid plan, and only Static Spaces
(which have no compute) stay free. Render's free tier still takes Docker, needs
no payment details, and does not expire.

1. Push this repo to GitHub (already done).

2. At <https://dashboard.render.com> choose **New → Blueprint**, point it at the
   repo, and Render reads [`render.yaml`](../render.yaml). It will prompt for the
   one value deliberately kept out of that file:

   | Name | Value |
   |------|-------|
   | `GROQ_API_KEY` | your Groq key |

   `render.yaml` sets `sync: false` for the key precisely so it is never
   committed to a public repo. The other variables (`LLM_PROVIDER`,
   `LLM_MODEL`, `DAILY_CALL_BUDGET`) are safe in the file and set automatically.

   Without a key the service still starts and runs in bring-your-own-key mode.

3. First build takes a few minutes. The health check is `/api/status`.

### The free-tier tradeoff, stated plainly

Free services **sleep after 15 minutes idle**, and the next request pays a
30&ndash;60 second cold start. The UI handles this rather than hiding it: the status
strip shows "waking the server" and retries for about 70 seconds, and the run
button warns that a sleeping server adds a minute.

For a portfolio link that is usually acceptable. If it is not, a paid instance
removes the sleep; nothing in the code changes.

## Other hosts

The image is a plain Dockerfile listening on `$PORT` (falling back to 7860), so
anything that runs a container works: Koyeb, Fly.io, Google Cloud Run, or your
own box. Only Render is scripted here.

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
