"""Token accounting, verified with a stub. No API key required.

Guards two things that would otherwise fail silently: that usage is actually
attributed to the scope it happened in, and that a provider which omits usage
metadata is reported as incomplete rather than as zero tokens.
"""

from __future__ import annotations

from agent.usage import Usage, record, track_usage


class _Resp:
    def __init__(self, meta):
        self.usage_metadata = meta
        self.content = "x"


def test_accumulates_tokens():
    with track_usage() as u:
        record(_Resp({"input_tokens": 100, "output_tokens": 20}))
        record(_Resp({"input_tokens": 50, "output_tokens": 10}))
    assert u.calls == 2
    assert u.input_tokens == 150
    assert u.output_tokens == 30
    assert u.total_tokens == 180
    assert u.is_complete


def test_missing_metadata_marks_incomplete():
    with track_usage() as u:
        record(_Resp({"input_tokens": 10, "output_tokens": 5}))
        record(_Resp(None))
    assert u.calls == 2
    assert u.calls_missing_usage == 1
    # Tokens are a lower bound, and the flag says so rather than implying zero.
    assert u.total_tokens == 15
    assert not u.is_complete


def test_scopes_are_isolated():
    with track_usage() as outer:
        record(_Resp({"input_tokens": 1, "output_tokens": 1}))
        with track_usage() as inner:
            record(_Resp({"input_tokens": 99, "output_tokens": 99}))
        assert inner.calls == 1
        assert inner.input_tokens == 99
    # The inner scope must not leak into the outer one.
    assert outer.calls == 1
    assert outer.input_tokens == 1


def test_record_outside_scope_is_a_noop():
    record(_Resp({"input_tokens": 5, "output_tokens": 5}))  # must not raise


def test_as_dict_is_json_serialisable():
    import json

    with track_usage() as u:
        record(_Resp({"input_tokens": 3, "output_tokens": 4}))
    d = u.as_dict()
    assert json.loads(json.dumps(d))["total_tokens"] == 7


def test_tracked_llm_records_through_the_factory():
    """A node using the factory cannot escape accounting."""
    from agent.llm import _TrackedLLM

    class _Inner:
        def invoke(self, messages):
            return _Resp({"input_tokens": 7, "output_tokens": 3})

    llm = _TrackedLLM(_Inner())
    with track_usage() as u:
        llm.invoke("hi")
    assert u.calls == 1
    assert u.total_tokens == 10
