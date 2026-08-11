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
from functools import lru_cache

DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


def get_llm(temperature: float = 0.0, model: str | None = None):
    """Returns a LangChain chat model for the provider named in LLM_PROVIDER.

    temperature defaults to 0.0 for reproducibility of the self-correct and
    single-shot paths. best_of_n deliberately overrides this -- sampling N
    completions at temperature 0 would return N near-identical answers and
    make the pass@N ceiling meaningless.
    """
    provider = os.environ.get("LLM_PROVIDER", "groq").lower()

    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=model or os.environ.get("LLM_MODEL", DEFAULT_GROQ_MODEL),
            temperature=temperature,
            max_retries=2,
        )

    if provider in ("gemini", "google"):
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model or os.environ.get("LLM_MODEL", DEFAULT_GEMINI_MODEL),
            temperature=temperature,
            max_retries=2,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER={provider!r}. Supported: 'groq', 'gemini'."
    )


@lru_cache(maxsize=8)
def get_cached_llm(temperature: float = 0.0, model: str | None = None):
    """Cached variant -- avoids rebuilding a client per node call in the eval loop."""
    return get_llm(temperature=temperature, model=model)


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
