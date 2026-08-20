"""LLM provider factory.

Deliberate choice: a mid-tier model (Groq-hosted Llama or Gemini Flash), not a
frontier model. A frontier model would solve most of this eval set zero-shot,
which would leave no measurable headroom -- the self-correction loop would have
nothing to correct and any "improvement" number would be noise. See README.md.

Providers are lazy-imported so that installing only one provider SDK is enough
to run the project.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache

from agent.usage import record

DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


class _TrackedLLM:
    """Proxies a chat model and records token usage on every invoke().

    Wrapping here rather than in each node means a new node cannot silently
    escape cost accounting -- every LLM call in the project goes through
    get_llm/get_cached_llm.
    """

    def __init__(self, inner):
        self._inner = inner

    def invoke(self, *args, **kwargs):
        response = self._inner.invoke(*args, **kwargs)
        record(response)
        return response

    def __getattr__(self, name):
        return getattr(self._inner, name)


def get_llm(temperature: float = 0.0, model: str | None = None, api_key: str | None = None):
    """Returns a LangChain chat model for the provider named in LLM_PROVIDER.

    temperature defaults to 0.0 for reproducibility of the self-correct and
    single-shot paths. best_of_n deliberately overrides this -- sampling N
    completions at temperature 0 would return N near-identical answers and
    make the pass@N ceiling meaningless.

    api_key, when supplied, is used for this client instead of the environment
    variable. It exists for the hosted demo's bring-your-own-key path, where a
    visitor's key must be used for exactly one request and never persisted.
    Such clients are deliberately NOT cached -- see get_cached_llm.
    """
    provider = os.environ.get("LLM_PROVIDER", "groq").lower()

    if provider == "groq":
        from langchain_groq import ChatGroq

        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        return _TrackedLLM(
            ChatGroq(
                model=model or os.environ.get("LLM_MODEL", DEFAULT_GROQ_MODEL),
                temperature=temperature,
                max_retries=2,
                **kwargs,
            )
        )

    if provider in ("gemini", "google"):
        from langchain_google_genai import ChatGoogleGenerativeAI

        kwargs = {}
        if api_key:
            kwargs["google_api_key"] = api_key
        return _TrackedLLM(
            ChatGoogleGenerativeAI(
                model=model or os.environ.get("LLM_MODEL", DEFAULT_GEMINI_MODEL),
                temperature=temperature,
                max_retries=2,
                **kwargs,
            )
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER={provider!r}. Supported: 'groq', 'gemini'."
    )


@lru_cache(maxsize=8)
def _cached_llm(temperature: float, model: str | None):
    return get_llm(temperature=temperature, model=model)


def get_cached_llm(temperature: float = 0.0, model: str | None = None, api_key: str | None = None):
    """Cached variant -- avoids rebuilding a client per node call in the eval loop.

    A caller-supplied api_key bypasses the cache entirely. Caching those would
    keep a visitor's credential alive in a process-wide LRU and risk handing it
    to the next request, so BYOK clients are always built fresh and discarded.
    """
    key = api_key or _request_api_key.get()
    if key:
        return get_llm(temperature=temperature, model=model, api_key=key)
    return _cached_llm(temperature, model)


def strip_code_fences(text: str) -> str:
    """Extracts code from a markdown-fenced LLM response.

    Mid-tier models wrap code in ```python fences inconsistently -- sometimes
    with prose before and after. Taking the largest fenced block is more robust
    than taking the first, since models often emit a short illustrative snippet
    before the real answer.
    """
    import re

    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, flags=re.DOTALL)
    if blocks:
        return max(blocks, key=len).strip()
    return text.strip()


class LLMUnavailableError(RuntimeError):
    """Raised when the configured model cannot be reached before a run starts."""


def verify_llm_available() -> str:
    """One cheap call to prove the configured model exists and is reachable.

    Why this exists: providers retire model IDs. When that happens every request
    404s, every problem records as a failure, and the run reports 0/N across all
    three methods -- which reads as a catastrophic model result rather than a
    dead endpoint. This turns that into a loud abort before the budget is spent,
    the same role verify_sandbox_health() plays for the sandbox.

    Learned the hard way: llama-3.3-70b-versatile was retired mid-project, and
    two full 30-problem runs recorded 0/30 before anyone looked at the errors.
    """
    provider = os.environ.get("LLM_PROVIDER", "groq")
    model = os.environ.get("LLM_MODEL", "(provider default)")
    try:
        get_llm(temperature=0.0).invoke("Reply with OK.")
    except Exception as exc:
        raise LLMUnavailableError(
            "Configured model is not reachable.\n"
            f"  provider: {provider}\n"
            f"  model:    {model}\n"
            f"  error:    {exc}\n"
            "This is a configuration or provider-availability problem, NOT a "
            "code-generation result. Providers retire model IDs, and a retired "
            "ID fails every call identically."
        ) from exc
    return model


# ---------------------------------------------------------------------------
# Per-request key scoping for the hosted demo.
#
# The visitor's key is carried in a ContextVar rather than in AgentState. That
# is deliberate: AgentState is serialised into history records and run files, so
# a credential placed there would leak into logs and saved output. A ContextVar
# is visible to the nodes that need it, invisible to everything that persists
# state, and is reset when the request ends.
# ---------------------------------------------------------------------------

_request_api_key: ContextVar[str | None] = ContextVar("request_api_key", default=None)


@contextmanager
def use_api_key(key: str | None):
    """Scopes an API key to one request. Restores the previous value on exit."""
    token = _request_api_key.set(key or None)
    try:
        yield
    finally:
        _request_api_key.reset(token)


def current_request_api_key() -> str | None:
    return _request_api_key.get()
