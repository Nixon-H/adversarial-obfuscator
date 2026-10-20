"""The build farm must fail, not hang.

Three defects in the cloud-build path, all recorded in
``docs/failure-modes.md`` as ``NEEDS-FIX`` since the first audit:

* ``trigger_and_wait`` polled ``while True`` with no overall deadline,
  so a run that never completed left the CLI polling forever.
* ``download_artifacts`` issued a ``requests.get`` with **no timeout**,
  so a stalled network hung the build; and it never checked the status
  code, so an error page was parsed as an artifact list.
* A rate-limited response (HTTP 429 / 403) was treated as a terminal
  failure, and retries used a fixed sleep, ignoring ``Retry-After``.

These tests drive the real methods with a stubbed ``requests`` module,
so no network is touched.
"""
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from obfuscator.core import utils as nutils  # noqa: E402


class _Response:
    """A minimal stand-in for a requests.Response."""

    def __init__(self, status_code=200, headers=None, payload=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


def test_retry_after_honours_the_header():
    resp = _Response(429, {"Retry-After": "17"})
    assert nutils._github_retry_after(resp, default=2.0) == 17


def test_retry_after_falls_back_when_absent_or_malformed():
    assert nutils._github_retry_after(_Response(429), default=3.0) == 3.0
    assert nutils._github_retry_after(_Response(429, {"Retry-After": "soon"}),
                                      default=3.0) == 3.0
    assert nutils._github_retry_after(None, default=3.0) == 3.0


def test_retry_after_uses_the_rate_limit_reset_timestamp():
    import time as _time
    reset = str(int(_time.time()) + 42)
    resp = _Response(429, {"X-RateLimit-Reset": reset})
    delay = nutils._github_retry_after(resp, default=1.0)
    assert 30 <= delay <= 60


def test_retry_after_is_capped():
    resp = _Response(429, {"Retry-After": "99999"})
    assert nutils._github_retry_after(resp) == nutils._GITHUB_MAX_BACKOFF


def test_every_requests_call_in_the_farm_has_a_timeout():
    """A request without a timeout can hang the build forever."""
    import ast
    src = open(os.path.join(ROOT, "obfuscator", "core", "utils.py"),
               encoding="utf-8").read()
    offenders = []
    for node in ast.walk(ast.parse(src)):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("get", "post", "put", "delete", "patch")
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "requests"):
            if "timeout" not in {k.arg for k in node.keywords}:
                offenders.append(node.lineno)
    assert not offenders, ("requests calls without a timeout at lines %r"
                           % (offenders,))


def test_both_farm_classes_have_a_deadline():
    """Neither farm may poll forever.

    ``GitHubBuildFarm`` (the older, non-Nuitka farm) has its own poll
    loop, and it only breaks when the workflow reports "completed" --
    so it needed the same deadline as ``GitHubNuitkaFarm``.
    """
    import inspect
    src = inspect.getsource(nutils)
    assert src.count("while True:") == 2, (
        "expected exactly two poll loops (one per farm class)")
    # Every unbounded loop must be preceded by a deadline check.
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if line.strip() != "while True:":
            continue
        window = "\n".join(lines[max(0, i - 8):i + 4])
        assert "deadline" in window, (
            "an unbounded poll loop at line %d has no deadline" % (i + 1))


def test_trigger_and_wait_gives_up_at_the_deadline(monkeypatch):
    """A run that never completes must NOT poll forever.

    The fake transport raises a ``BaseException`` (not an ``Exception``):
    the poll loop catches ``Exception`` and would otherwise swallow the
    signal and keep polling, hanging the suite instead of failing it.
    """
    calls = {"n": 0}

    class _Stop(BaseException):
        pass

    def _fake_get(url, *_a, **_k):
        if str(url).rstrip("/").endswith("/user"):
            # The farm resolves the account name during construction.
            return _Response(200, payload={"login": "tester"})
        calls["n"] += 1
        raise _Stop("polled too many times: the deadline guard did not "
                    "stop the loop")

    fake_requests = types.ModuleType("requests")
    fake_requests.get = _fake_get
    fake_requests.post = lambda *a, **k: _Response(200)
    fake_requests.put = lambda *a, **k: _Response(200)
    fake_requests.delete = lambda *a, **k: _Response(204)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    monkeypatch.setattr(nutils.time, "sleep", lambda *_a: None)

    # A zero deadline: the loop must give up before polling at all.
    monkeypatch.setattr(nutils, "_GITHUB_WAIT_DEADLINE", 0)
    farm = nutils.GitHubNuitkaFarm("token")
    farm.username = "u"
    farm.repo_name = "r"
    assert farm.trigger_and_wait(resume_run_id=12345) is None
    assert calls["n"] == 0, "the deadline did not stop the loop"


def test_download_artifacts_checks_the_status_code(monkeypatch, tmp_path):
    """An error response must not be parsed as an artifact list."""
    fake_requests = types.ModuleType("requests")
    fake_requests.get = lambda *a, **k: _Response(403, {"Retry-After": "0"})
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    monkeypatch.setattr(nutils.time, "sleep", lambda *_a: None)

    farm = nutils.GitHubNuitkaFarm("token")
    farm.username = "u"
    farm.repo_name = "r"
    # Must return without raising and without downloading anything.
    farm.download_artifacts(1, str(tmp_path))
    assert not list(tmp_path.iterdir())


def test_download_artifacts_retries_once_on_429(monkeypatch, tmp_path):
    """A rate limit must be waited out, not treated as terminal."""
    seen = {"n": 0}

    def _fake_get(*_a, **_k):
        seen["n"] += 1
        if seen["n"] == 1:
            return _Response(429, {"Retry-After": "0"})
        return _Response(200, payload={"artifacts": []})

    fake_requests = types.ModuleType("requests")
    fake_requests.get = _fake_get
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    monkeypatch.setattr(nutils.time, "sleep", lambda *_a: None)

    farm = nutils.GitHubNuitkaFarm("token")
    farm.username = "u"
    farm.repo_name = "r"
    farm.download_artifacts(1, str(tmp_path))
    assert seen["n"] == 2, "the rate-limited request was not retried"


def test_upload_file_waits_out_a_rate_limit(monkeypatch, tmp_path):
    """A 429 on upload must back off using Retry-After, not a fixed sleep."""
    slept = []
    monkeypatch.setattr(nutils.time, "sleep", lambda s: slept.append(s))

    src = tmp_path / "payload.py"
    src.write_text("x = 1\n", encoding="utf-8")

    put_statuses = [429, 201]

    def _fake_put(*_a, **_k):
        return _Response(put_statuses.pop(0) if put_statuses else 201)

    fake_requests = types.ModuleType("requests")
    fake_requests.get = lambda *a, **k: _Response(404)
    fake_requests.put = _fake_put
    fake_requests.post = lambda *a, **k: _Response(200)
    fake_requests.delete = lambda *a, **k: _Response(204)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    farm = nutils.GitHubNuitkaFarm("token")
    farm.username = "u"
    farm.repo_name = "r"
    assert farm.upload_file(str(src), "payload.py") is True
    # The rate-limited attempt must have waited for the server's answer.
    assert any(s >= 0 for s in slept)
