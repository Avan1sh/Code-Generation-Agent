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


# ---------------------------------------------------------------------------
# Server endpoint shape
# ---------------------------------------------------------------------------


def test_solve_endpoint_is_not_a_generator():
    """A stray `yield` in the endpoint silently empties every response.

    FastAPI 0.141+ streams generator endpoints as application/jsonl. A `return
    JSONResponse(...)` inside a generator yields nothing, so the client gets
    HTTP 200, correct-looking headers, and a zero-byte body -- with no
    exception, no crash, and the worker still alive. Nothing in the logs says
    why. An orphan `yield` left by a line-based edit caused exactly that, and it
    survived a full test run because no test asserted on the response body.
    """
    import inspect

    from serve.app import solve, status

    assert not inspect.isgeneratorfunction(solve)
    assert not inspect.isgeneratorfunction(status)


def test_solve_returns_a_non_empty_json_body():
    """End-to-end shape check with a stubbed model -- no API key needed.

    Asserts on the body, which is the assertion that was missing when the bug
    shipped.
    """
    import json

    from fastapi.testclient import TestClient

    from agent.nodes import generator as gen_mod
    from agent.nodes import reflector as ref_mod
    from agent.nodes import test_generator as tg_mod
    import serve.app as app_mod

    class _Resp:
        def __init__(self, content):
            self.content = content
            self.usage_metadata = {"input_tokens": 5, "output_tokens": 5}

    class _Stub:
        payload = "```python\nfrom pydantic import BaseModel\n\n\nclass B(BaseModel):\n    w: int\n```"

        def invoke(self, _messages):
            return _Resp(self.payload)

    stub = _Stub()
    originals = {}
    for mod in (gen_mod, ref_mod, tg_mod):
        originals[mod] = mod.get_cached_llm
        mod.get_cached_llm = lambda *a, **k: stub
    try:
        with TestClient(app_mod.app) as client:
            resp = client.post("/api/solve", json={"prompt": "x" * 30})
    finally:
        for mod, fn in originals.items():
            mod.get_cached_llm = fn

    assert resp.status_code == 200
    assert len(resp.content) > 0, "empty body -- is the endpoint a generator again?"
    assert resp.headers["content-type"].startswith("application/json")
    body = json.loads(resp.content)
    assert "status" in body
    assert "attempts" in body
    assert body["tests_are_llm_written"] is True
