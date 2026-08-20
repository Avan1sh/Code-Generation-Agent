"""FastAPI wrapper that runs the agent live for the hosted demo.

This exists so the deterministic parts of the project can be seen working end to
end, on a machine where the sandbox's POSIX resource limits are actually active
-- which they are not on the Windows box this was developed on.

Three things about a public endpoint that runs LLM-generated code deserve to be
stated rather than assumed:

1. **Cost is capped, not trusted.** The owner's key is used until a daily call
   ceiling is reached, after which the demo asks visitors for their own key
   rather than continuing to spend. Per-IP rate limiting sits in front of that.
   `max_attempts` is fixed server-side; the client cannot raise it.

2. **Runs are serialised.** `agent/sandbox.py` uses `preexec_fn`, which is not
   thread-safe -- forking from a multi-threaded process to set rlimits is the
   classic deadlock. FastAPI runs sync endpoints in a threadpool, so a semaphore
   of one is held across each agent run. That also bounds concurrent LLM spend.

3. **A pass here is not a benchmark result.** Ad-hoc prompts have no canonical
   tests, so the tests are written by the same model being tested. The response
   carries `tests_are_llm_written: true` and the UI says so. Only
   `eval/run_eval.py`, which uses hand-written tests, backs any reported number.
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.graph import run_agent  # noqa: E402
from agent.llm import LLMUnavailableError, use_api_key, verify_llm_available  # noqa: E402
from agent.sandbox import DEFAULT_TIMEOUT_SEC, SandboxHealthError, verify_sandbox_health  # noqa: E402
from agent.state import Problem  # noqa: E402
from agent.usage import track_usage  # noqa: E402

# ---------------------------------------------------------------------------
# Limits. Every one of these is a cost or safety control, not a preference.
# ---------------------------------------------------------------------------
MAX_ATTEMPTS = 3                       # fixed server-side; clients cannot raise it
MAX_PROMPT_CHARS = 1200
DAILY_CALL_BUDGET = int(os.environ.get("DAILY_CALL_BUDGET", "400"))
RATE_LIMIT_REQUESTS = 4                # per IP
RATE_LIMIT_WINDOW_SEC = 600
QUEUE_WAIT_SEC = 45

# Measured at startup and surfaced in /api/status. A probe that eats most of
# the timeout budget means this hardware is about to start reporting valid
# solutions as "timed out" -- which reads as the model writing infinite loops.
# "not_run" is the honest default: a probe that failed and a probe that never
# executed must not look identical in /api/status. The first version recorded
# only success, so a blank reading had two possible causes and no way to tell
# them apart.
_probe = {"status": "not_run", "seconds": None, "marginal": None, "detail": None}

@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """Same guards the eval uses, for the same reason: fail loudly, not silently.

    Uses the lifespan API rather than the deprecated on_event hook so there is no
    ambiguity about whether it ran -- an earlier version recorded nothing and the
    cause could not be distinguished between "never fired" and "failed".
    """
    try:
        probe = verify_sandbox_health()
        # Known-good code needing more than half the budget means real solutions,
        # which do more work, will start timing out on this hardware.
        marginal = probe > DEFAULT_TIMEOUT_SEC * 0.5
        _probe.update(status="ok", seconds=round(probe, 1), marginal=marginal, detail=None)
        print(f"[startup] sandbox health OK (probe {probe:.1f}s, timeout {DEFAULT_TIMEOUT_SEC}s)", flush=True)
        if marginal:
            print(
                f"[startup] WARNING: probe used {probe:.1f}s of a {DEFAULT_TIMEOUT_SEC}s budget. "
                "Real solutions will report timed_out on this hardware, which looks like "
                "a model failure but is not. Raise SANDBOX_TIMEOUT_SEC.",
                file=sys.stderr, flush=True,
            )
    except SandboxHealthError as exc:
        _probe.update(status="failed", seconds=None, marginal=None, detail=str(exc)[:300])
        print("[startup] SANDBOX UNHEALTHY", file=sys.stderr, flush=True)
        print(str(exc), file=sys.stderr, flush=True)
    except Exception as exc:  # noqa: BLE001
        # Anything else is still recorded rather than leaving a blank reading.
        _probe.update(status="error", seconds=None, marginal=None,
                      detail=f"{type(exc).__name__}: {exc}"[:300])
        print(f"[startup] PROBE ERROR: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)

    print(f"[startup] POSIX resource limits active: {sys.platform != 'win32'}", flush=True)
    if os.environ.get("GROQ_API_KEY"):
        try:
            print(f"[startup] model reachable: {verify_llm_available()}", flush=True)
        except LLMUnavailableError as exc:
            print("[startup] LLM PREFLIGHT FAILED", file=sys.stderr, flush=True)
            print(str(exc), file=sys.stderr, flush=True)
    else:
        print("[startup] no shared key set -- bring-your-own-key mode only", flush=True)
    yield


app = FastAPI(title="selfcorrect-agent demo", docs_url=None, redoc_url=None, lifespan=_lifespan)


# Serialises agent runs: see point 2 in the module docstring.
_run_slot = threading.Semaphore(1)
_state_lock = threading.Lock()
_ip_hits: dict[str, deque] = {}
_budget = {"day": None, "calls_used": 0}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _budget_remaining() -> int:
    with _state_lock:
        if _budget["day"] != _today():
            _budget["day"] = _today()
            _budget["calls_used"] = 0
        return max(0, DAILY_CALL_BUDGET - _budget["calls_used"])


def _spend(calls: int) -> None:
    with _state_lock:
        _budget["calls_used"] += max(0, calls)


def _rate_limited(ip: str) -> bool:
    now = time.monotonic()
    with _state_lock:
        hits = _ip_hits.setdefault(ip, deque())
        while hits and now - hits[0] > RATE_LIMIT_WINDOW_SEC:
            hits.popleft()
        if len(hits) >= RATE_LIMIT_REQUESTS:
            return True
        hits.append(now)
        return False


class SolveRequest(BaseModel):
    prompt: str = Field(min_length=8, max_length=MAX_PROMPT_CHARS)
    # Used for this request only, never stored and never logged. See the
    # ContextVar rationale in agent/llm.py.
    api_key: str | None = Field(default=None, max_length=200)


@app.get("/api/status")
def status() -> dict:
    remaining = _budget_remaining()
    return {
        "ok": True,
        "shared_budget_remaining": remaining,
        "shared_budget_total": DAILY_CALL_BUDGET,
        "byok_required": remaining <= 0,
        "max_attempts": MAX_ATTEMPTS,
        "max_prompt_chars": MAX_PROMPT_CHARS,
        "model": os.environ.get("LLM_MODEL", "(provider default)"),
        "posix_resource_limits_active": sys.platform != "win32",
        "sandbox_timeout_sec": DEFAULT_TIMEOUT_SEC,
        "sandbox_probe_status": _probe["status"],
        "sandbox_probe_sec": _probe["seconds"],
        "sandbox_timeout_marginal": _probe["marginal"],
        "sandbox_probe_detail": _probe["detail"],
    }


@app.post("/api/solve")
def solve(req: SolveRequest, request: Request) -> JSONResponse:
    ip = (request.headers.get("x-forwarded-for") or request.client.host or "?").split(",")[0].strip()

    if _rate_limited(ip):
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limited",
                "message": f"Limit is {RATE_LIMIT_REQUESTS} runs per "
                           f"{RATE_LIMIT_WINDOW_SEC // 60} minutes. Supply your own Groq key to bypass it.",
            },
        )

    visitor_key = (req.api_key or "").strip() or None
    using_shared = visitor_key is None

    if using_shared and _budget_remaining() <= 0:
        return JSONResponse(
            status_code=429,
            content={
                "error": "budget_exhausted",
                "message": "The shared daily budget for this demo is spent. "
                           "Supply your own free Groq key to keep going -- it is used "
                           "for this request only and never stored.",
                "byok_required": True,
            },
        )

    if not _run_slot.acquire(timeout=QUEUE_WAIT_SEC):
        return JSONResponse(
            status_code=503,
            content={"error": "busy", "message": "Another run is in progress. Try again in a moment."},
        )

    try:
        problem = Problem(id="adhoc", prompt=req.prompt.strip(), category="adhoc")
        started = time.monotonic()

        with use_api_key(visitor_key), track_usage() as usage:
            final = run_agent(problem, max_attempts=MAX_ATTEMPTS)

        if using_shared:
            _spend(usage.calls)

        return JSONResponse(content={
            "status": final.status,
            "passed": final.status == "passed",
            "attempts_used": final.attempt_number,
            "max_attempts": final.max_attempts,
            "code": final.generated_code or "",
            "test_code": final.test_code or "",
            "duration_sec": round(time.monotonic() - started, 1),
            "usage": usage.as_dict(),
            "key_source": "visitor" if visitor_key else "shared",
            "shared_budget_remaining": _budget_remaining(),
            # Stated in the payload, not just the UI: a pass here means the model
            # passed tests it wrote for itself.
            "tests_are_llm_written": True,
            "attempts": [
                {
                    "attempt_number": a.attempt_number,
                    "static_passed": a.static_check.passed if a.static_check else None,
                    "static_issues": [
                        {"kind": i.kind, "message": i.message, "line": i.line}
                        for i in (a.static_check.issues if a.static_check else [])
                    ],
                    "execution_passed": a.execution.passed if a.execution else None,
                    "timed_out": a.execution.timed_out if a.execution else None,
                    "stdout_tail": (a.execution.stdout[-1400:] if a.execution else ""),
                    "reflection": a.reflection,
                    "code": a.code,
                }
                for a in final.history
            ],
        })

    except LLMUnavailableError as exc:
        return JSONResponse(status_code=503, content={"error": "llm_unavailable", "message": str(exc)[:400]})
    except Exception as exc:  # noqa: BLE001
        # Never echo the exception body: a provider error can contain the key.
        return JSONResponse(
            status_code=500,
            content={"error": type(exc).__name__,
                     "message": "The run failed. If you supplied a key, check that it is valid."},
        )
    finally:
        _run_slot.release()


    yield


_STATIC = Path(__file__).resolve().parent / "static"
if _STATIC.is_dir():
    app.mount("/", StaticFiles(directory=str(_STATIC), html=True), name="static")
