"""Level-5 split execution: the implementation must not ship.

The whole point of this layer is that reversing the artefact does not yield
the algorithm, so the tests check the artefact itself -- not just that the
helpers work.
"""
import ast
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from obfuscator.remote_exec import (  # noqa: E402
    RemoteError, RemoteRegistry, SECRET_ENV, URL_ENV, call_remote,
    extract_remote_functions, sign_request, split_module, stub_source,
    verify_request, write_remote_bundle,
)

SECRET = bytes.fromhex("11" * 32)

SOURCE = '''\
from obfuscator.remote_exec import remote


@remote
def pricing_engine(units, tier):
    """The algorithm that must never ship."""
    SECRET_COEFFICIENT = 0x5EC12E7
    base = units * SECRET_COEFFICIENT
    if tier == "gold":
        return base * 87 // 100
    return base


def main():
    print(pricing_engine(10, "gold"))
'''


def test_remote_function_is_extracted():
    tree = ast.parse(SOURCE)
    found = extract_remote_functions(tree, SOURCE)
    assert [f.name for f in found] == ["pricing_engine"]


def test_implementation_does_not_ship_in_the_client_source():
    """The decisive property: the constants are gone from the client build."""
    client, remote = split_module(SOURCE)
    assert len(remote) == 1
    assert "SECRET_COEFFICIENT" not in client
    assert "0x5EC12E7" not in client
    assert "base * 87" not in client
    # The stub is still callable and still named the same.
    assert "def pricing_engine(" in client
    compile(client, "<client>", "exec")


def test_unmarked_functions_are_untouched():
    client, remote = split_module(SOURCE)
    assert "def main():" in client
    assert "print(pricing_engine" in client
    assert [f.name for f in remote] == ["pricing_engine"]


def test_no_marker_means_no_change():
    plain = "def f():\n    return 1\n"
    client, remote = split_module(plain)
    assert client == plain
    assert remote == []


def test_stub_fails_closed_without_configuration(monkeypatch):
    monkeypatch.delenv(URL_ENV, raising=False)
    monkeypatch.delenv(SECRET_ENV, raising=False)
    with pytest_raises(RemoteError):
        call_remote("pricing_engine", [10, "gold"])


def pytest_raises(exc_type):
    """Tiny local context manager so this file needs no pytest import."""
    class _Ctx:
        def __enter__(self):
            return self

        def __exit__(self, exc_type_, exc, tb):
            if exc_type_ is None:
                raise AssertionError("expected %s, nothing raised" % exc_type)
            return issubclass(exc_type_, exc_type)
    return _Ctx()


def test_plain_http_endpoint_is_refused(monkeypatch):
    monkeypatch.setenv(URL_ENV, "http://example.invalid/rpc")
    monkeypatch.setenv(SECRET_ENV, "11" * 32)
    with pytest_raises(RemoteError):
        call_remote("pricing_engine", [1, "gold"])


def test_signature_round_trip():
    sig = sign_request(SECRET, "f", [1, "x"], "nonce1", 1000.0)
    verify_request(SECRET, "f", [1, "x"], "nonce1", 1000.0, sig, now=1000.0)


def test_tampered_args_are_rejected():
    sig = sign_request(SECRET, "f", [1], "n", 1000.0)
    with pytest_raises(RemoteError):
        verify_request(SECRET, "f", [2], "n", 1000.0, sig, now=1000.0)


def test_stale_request_is_rejected():
    sig = sign_request(SECRET, "f", [1], "n", 1000.0)
    with pytest_raises(RemoteError):
        verify_request(SECRET, "f", [1], "n", 1000.0, sig, now=1000.0 + 9999)


def test_replay_is_rejected():
    registry = RemoteRegistry(SECRET)
    registry.register("f", lambda x: x + 1)
    nonce = "abc"
    body = json.dumps({
        "function": "f", "args": [1], "nonce": nonce, "timestamp": 1000.0,
        "signature": sign_request(SECRET, "f", [1], nonce, 1000.0),
    }).encode()
    first = json.loads(registry.handle(body, now=1000.0))
    assert first.get("result") == 2
    second = json.loads(registry.handle(body, now=1000.0))
    assert "replayed" in second.get("error", "")


def test_server_executes_the_implementation():
    registry = RemoteRegistry(SECRET)
    registry.register("pricing_engine", lambda units, tier: units * 3)
    nonce = "n2"
    body = json.dumps({
        "function": "pricing_engine", "args": [10, "gold"], "nonce": nonce,
        "timestamp": 1000.0,
        "signature": sign_request(SECRET, "pricing_engine", [10, "gold"],
                                  nonce, 1000.0),
    }).encode()
    out = json.loads(registry.handle(body, now=1000.0))
    assert out["result"] == 30


def test_client_and_server_agree_end_to_end():
    """A stub built from the client source reaches the real implementation.

    The transport is injected by replacing the module-level ``urlopen`` the
    client uses, so this exercises the real signing/verification path with no
    network.
    """
    client, remote = split_module(SOURCE)
    ns = {}
    exec(compile(client, "<client>", "exec"), ns)

    registry = RemoteRegistry(SECRET)
    registry.register("pricing_engine",
                      lambda units, tier: units * 0x5EC12E7 * 87 // 100)

    import obfuscator.remote_exec as rx

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    real_urlopen = rx.urllib.request.urlopen

    def fake_urlopen(request, timeout=None):
        body = request.data
        return _Resp(registry.handle(body, now=json.loads(body)["timestamp"]))

    monkeypatch_env = {
        URL_ENV: "https://relay.invalid/rpc",
        SECRET_ENV: SECRET.hex(),
    }
    saved = {k: os.environ.get(k) for k in monkeypatch_env}
    os.environ.update(monkeypatch_env)
    rx.urllib.request.urlopen = fake_urlopen
    try:
        result = ns["pricing_engine"](10, "gold")
    finally:
        rx.urllib.request.urlopen = real_urlopen
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    expected = 10 * 0x5EC12E7 * 87 // 100
    assert result == expected


def test_operator_bundle_contains_the_implementation(tmp_path):
    _client, remote = split_module(SOURCE)
    path = tmp_path / "remote_bundle.py"
    write_remote_bundle(remote, str(path))
    text = path.read_text()
    assert "SECRET_COEFFICIENT" in text
    assert "def build_registry" in text
    compile(text, "<bundle>", "exec")


def test_stub_source_has_no_body_leak():
    _client, remote = split_module(SOURCE)
    stub = stub_source(remote[0])
    assert "SECRET_COEFFICIENT" not in stub
    assert "call_remote" in stub
    compile(stub, "<stub>", "exec")
