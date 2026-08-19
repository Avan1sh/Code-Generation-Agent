"""Measured token accounting for LLM calls.

Why this exists: call counts are a crude proxy for cost. A reflection call
carries the failing code plus a pytest traceback, so it is far more expensive in
tokens than a first-attempt generation -- reporting "54 calls" hides that. This
records actual input/output tokens so the cost side of the cost-vs-quality
trade-off is measured rather than assumed, to the same standard as everything
else reported here.

Honesty constraint: not every provider populates usage metadata. When it is
missing the call is counted under `calls_missing_usage` and its tokens are NOT
silently counted as zero -- a run where usage was unavailable must be
distinguishable from a run that genuinely used no tokens.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import asdict, dataclass


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    # Calls whose response carried no usage metadata. If this is non-zero the
    # token figures are a LOWER BOUND, not a total.
    calls_missing_usage: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def is_complete(self) -> bool:
        """True when every counted call reported its usage."""
        return self.calls_missing_usage == 0

    def as_dict(self) -> dict:
        d = asdict(self)
        d["total_tokens"] = self.total_tokens
        d["is_complete"] = self.is_complete
        return d


class _Local(threading.local):
    usage: Usage | None = None


_state = _Local()


@contextmanager
def track_usage():
    """Scopes a Usage accumulator. Nests safely; restores the outer scope."""
    previous = _state.usage
    current = Usage()
    _state.usage = current
    try:
        yield current
    finally:
        _state.usage = previous


def record(response) -> None:
    """Adds one response's usage to the active scope. No-op outside a scope."""
    active = _state.usage
    if active is None:
        return

    active.calls += 1
    meta = getattr(response, "usage_metadata", None)
    if not meta:
        active.calls_missing_usage += 1
        return

    active.input_tokens += int(meta.get("input_tokens") or 0)
    active.output_tokens += int(meta.get("output_tokens") or 0)
