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
    RemoteError, RemoteRegistry, SECRET_ENV, TOTP_ENV, TOTP_KWARG,
    TOTP_SECONDARY_ENV, TOTP_SECONDARY_KWARG, URL_ENV, call_remote,
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


def test_loopback_http_endpoint_is_allowed_for_the_reference_relay():
    out = call_remote(
        "pricing_engine", [1, "gold"], url="http://127.0.0.1:8787/rpc",
        secret=SECRET, opener=lambda _url, _body: b'{"result": 3}')
    assert out == 3


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
        "version": 1,
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
        "version": 1,
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


def test_stub_forwards_kwargs_to_call_remote():
    """Regression: the emitted stub accepted **kwargs but dropped them."""
    _client, remote = split_module(SOURCE)
    stub = stub_source(remote[0])
    assert "kwargs=kwargs" in stub, stub
    compile(stub, "<stub>", "exec")


def test_sign_request_binds_kwargs():
    """Altering kwargs must invalidate the signature."""
    sig = sign_request(SECRET, "f", [1], "n", 1000.0, {"rate": 0.5})
    verify_request(SECRET, "f", [1], "n", 1000.0, sig, {"rate": 0.5}, now=1000.0)
    with pytest_raises(RemoteError):
        verify_request(SECRET, "f", [1], "n", 1000.0, sig, {"rate": 0.9}, now=1000.0)
    # Omitting kwargs signs the canonical empty object.
    sig2 = sign_request(SECRET, "f", [1], "n", 1000.0)
    verify_request(SECRET, "f", [1], "n", 1000.0, sig2, now=1000.0)


def test_protocol_v1_cross_language_vectors():
    """Fixed vectors also appear in relay/src/remote.rs's Rust tests."""
    vectors = [
        (
            [1, -0.0, "é", True, None, {"b": 2, "a": 1.5}],
            {"rate": 0.5, "label": "x"},
            "nonce",
            1000.0,
            "b2adc43bf63eb2bfeb87e9b5b509f636b2de11ea36189d23893c7a1be44c030f",
        ),
        (
            [],
            {},
            "n",
            0.0,
            "382e67120a57399c948f27624de9082070d2b80b3e847fcfa421b5b26fb2a396",
        ),
        (
            [-9223372036854775808, 18446744073709551615],
            {"z": 1},
            "abc",
            1.25,
            "0297cce9a44e6d8da81abbed561dc5ae941c1da98a6b0148df740ec2aa2d59fe",
        ),
    ]
    for args, kwargs, nonce, timestamp, expected in vectors:
        assert sign_request(SECRET, "f", args, nonce, timestamp, kwargs) == expected


def test_protocol_distinguishes_integer_and_float_and_rejects_nonfinite():
    assert sign_request(SECRET, "f", [1], "n", 1.0) != sign_request(
        SECRET, "f", [1.0], "n", 1.0)
    with pytest_raises(RemoteError):
        sign_request(SECRET, "f", [float("nan")], "n", 1.0)
    with pytest_raises(RemoteError):
        sign_request(SECRET, "f", [1], "n", float("inf"))


def test_registry_verifies_and_dispatches_kwargs():
    registry = RemoteRegistry(SECRET)
    registry.register("add_tax", lambda amount, rate=0.2: amount * (1 + rate))
    kwargs = {"rate": 0.5}
    body = json.dumps({
        "version": 1,
        "function": "add_tax",
        "args": [100],
        "kwargs": kwargs,
        "nonce": "kwargs-nonce",
        "timestamp": 1000.0,
        "signature": sign_request(
            SECRET, "add_tax", [100], "kwargs-nonce", 1000.0, kwargs),
    }).encode()
    assert json.loads(registry.handle(body, now=1000.0)) == {"result": 150.0}

    tampered = json.loads(body)
    tampered["kwargs"] = {"rate": 0.9}
    out = json.loads(registry.handle(json.dumps(tampered).encode(), now=1000.0))
    assert "signature" in out.get("error", "")


def test_bundle_main_invokes_impl_with_kwargs(tmp_path):
    """The operator bundle's __main__ must pass kwargs to the implementation."""
    import json as _json
    import subprocess as _sp
    import sys as _sys
    import time as _time
    src = (
        "from obfuscator.remote_exec import remote\n\n"
        "@remote\n"
        "def add_tax(amount, rate=0.2):\n"
        "    return amount * (1 + rate)\n"
    )
    _client, funcs = split_module(src)
    bundle = tmp_path / "bundle.py"
    write_remote_bundle(funcs, str(bundle))
    env = dict(os.environ, PYTHONPATH=os.getcwd(), **{SECRET_ENV: SECRET.hex()})
    req = {
        "version": 1,
        "function": "add_tax",
        "args": [100],
        "kwargs": {"rate": 0.5},
        "nonce": "bundle-nonce",
        "timestamp": _time.time(),
    }
    req["signature"] = sign_request(
        SECRET, "add_tax", [100], "bundle-nonce", req["timestamp"], req["kwargs"])
    out = _sp.run([_sys.executable, str(bundle)], input=_json.dumps(req),
                  capture_output=True, text=True, env=env, timeout=10)
    assert _json.loads(out.stdout) == {"result": 150.0}, out.stderr

    req["kwargs"] = {"rate": 0.9}
    out = _sp.run([_sys.executable, str(bundle)], input=_json.dumps(req),
                  capture_output=True, text=True, env=env, timeout=10)
    assert "signature" in _json.loads(out.stdout).get("error", ""), out.stderr


def test_split_client_is_standalone_and_removes_the_marker_dependency():
    client, _remote = split_module(SOURCE)
    assert "obfuscator" not in client
    assert "@remote" not in client
    assert "from obfuscator.remote_exec" not in client
    assert "_nx_call_remote" in client


def test_operator_bundle_is_owner_readable_only(tmp_path):
    import stat

    _client, remote = split_module(SOURCE)
    path = tmp_path / "remote_bundle.py"
    write_remote_bundle(remote, str(path))
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode & 0o077 == 0, oct(mode)


def test_nested_remote_function_is_refused_instead_of_half_split():
    src = (
        "from obfuscator.remote_exec import remote\n\n"
        "def outer():\n"
        "    @remote\n"
        "    def hidden():\n"
        "        return 1\n"
        "    return hidden()\n"
    )
    with pytest_raises(RemoteError):
        split_module(src)


def test_non_marker_remote_exec_import_is_refused():
    src = (
        "from obfuscator.remote_exec import remote, call_remote\n\n"
        "@remote\n"
        "def hidden():\n"
        "    return 1\n"
    )
    with pytest_raises(RemoteError):
        split_module(src)


def test_combined_decorators_are_refused_instead_of_shipping_wrong_semantics():
    src = (
        "from obfuscator.remote_exec import remote\n\n"
        "def wrap(fn):\n"
        "    return fn\n\n"
        "@wrap\n"
        "@remote\n"
        "def hidden():\n"
        "    return 1\n"
    )
    with pytest_raises(RemoteError):
        split_module(src)


def test_unimported_remote_name_is_not_treated_as_the_marker():
    src = (
        "def remote(fn):\n"
        "    return fn\n\n"
        "@remote\n"
        "def hidden():\n"
        "    return 1\n"
    )
    with pytest_raises(RemoteError):
        split_module(src)


def test_module_global_dependency_is_refused_because_it_would_not_be_bundled():
    src = (
        "from obfuscator.remote_exec import remote\n\n"
        "SECRET = 3\n\n"
        "@remote\n"
        "def hidden():\n"
        "    return SECRET\n"
    )
    with pytest_raises(RemoteError):
        split_module(src)


def test_function_local_import_is_self_contained():
    src = (
        "from obfuscator.remote_exec import remote\n\n"
        "@remote\n"
        "def hidden(value):\n"
        "    import math\n"
        "    return int(math.sqrt(value))\n"
    )
    client, remote = split_module(src)
    assert len(remote) == 1
    assert "import math" in remote[0].source
    assert "def hidden(*args, **kwargs):" in client


def test_module_global_default_value_is_refused_because_it_would_not_be_bundled():
    src = (
        "from obfuscator.remote_exec import remote\n\n"
        "SECRET = 3\n\n"
        "@remote\n"
        "def hidden(value=SECRET):\n"
        "    return value\n"
    )
    with pytest_raises(RemoteError):
        split_module(src)


def test_shadowed_builtin_is_an_unbundled_global_dependency():
    src = (
        "from obfuscator.remote_exec import remote\n\n"
        "def len(_value):\n"
        "    return 99\n\n"
        "@remote\n"
        "def hidden(value):\n"
        "    return len(value)\n"
    )
    with pytest_raises(RemoteError):
        split_module(src)



def test_totp_reserved_kwargs_become_top_level_transport_fields(monkeypatch):
    captured = {}

    def opener(_url, body):
        captured["body"] = json.loads(body.decode("utf-8"))
        return b'{"result": 1}'

    monkeypatch.setenv(TOTP_ENV, "111111")
    monkeypatch.setenv(TOTP_SECONDARY_ENV, "222222")
    out = call_remote(
        "pricing_engine", [1], {
            "tier": "gold",
            TOTP_KWARG: "333333",
            TOTP_SECONDARY_KWARG: "444444",
        }, url="http://127.0.0.1:8787/rpc", secret=SECRET, opener=opener)
    assert out == 1
    body = captured["body"]
    assert body["totp"] == "333333"
    assert body["totp_secondary"] == "444444"
    assert body["kwargs"] == {"tier": "gold"}
    expected = sign_request(
        SECRET, "pricing_engine", [1], body["nonce"], body["timestamp"],
        {"tier": "gold"})
    assert body["signature"] == expected


def test_totp_environment_fallback_is_used_when_per_call_kwargs_are_absent(monkeypatch):
    captured = {}

    def opener(_url, body):
        captured["body"] = json.loads(body.decode("utf-8"))
        return b'{"result": 1}'

    monkeypatch.setenv(TOTP_ENV, "111111")
    monkeypatch.setenv(TOTP_SECONDARY_ENV, "222222")
    call_remote("pricing_engine", [1], url="http://127.0.0.1:8787/rpc",
                secret=SECRET, opener=opener)
    assert captured["body"]["totp"] == "111111"
    assert captured["body"]["totp_secondary"] == "222222"


def test_malformed_totp_fails_before_network(monkeypatch):
    called = []

    def opener(_url, body):
        called.append(body)
        return b'{"result": 1}'

    monkeypatch.delenv(TOTP_ENV, raising=False)
    monkeypatch.delenv(TOTP_SECONDARY_ENV, raising=False)
    with pytest_raises(RemoteError):
        call_remote("pricing_engine", [1], {TOTP_KWARG: "12345"},
                    url="http://127.0.0.1:8787/rpc", secret=SECRET,
                    opener=opener)
    assert called == []


def test_embedded_client_totp_kwargs_are_not_signed_as_function_kwargs(monkeypatch):
    client, _remote = split_module(SOURCE)
    ns = {}
    exec(compile(client, "<client>", "exec"), ns)
    captured = {}

    import obfuscator.remote_exec as rx

    class _Resp:
        def read(self):
            return b'{"result": 5}'

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    real_urlopen = rx.urllib.request.urlopen

    def fake_urlopen(request, timeout=None):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Resp()

    monkeypatch.setenv(URL_ENV, "https://relay.invalid/rpc")
    monkeypatch.setenv(SECRET_ENV, SECRET.hex())
    rx.urllib.request.urlopen = fake_urlopen
    try:
        assert ns["pricing_engine"](
            10, "gold", _nx_totp="123456", _nx_totp_secondary="654321") == 5
    finally:
        rx.urllib.request.urlopen = real_urlopen
    body = captured["body"]
    assert body["totp"] == "123456"
    assert body["totp_secondary"] == "654321"
    assert body["kwargs"] == {}
    expected = sign_request(
        SECRET, "pricing_engine", [10, "gold"], body["nonce"],
        body["timestamp"], {})
    assert body["signature"] == expected


def test_totp_prompt_opt_in_collects_two_fresh_codes(monkeypatch):
    import getpass as _getpass

    captured = {}

    def opener(_url, body):
        captured["body"] = json.loads(body.decode("utf-8"))
        return b'{"result": 1}'

    class _TTY:
        @staticmethod
        def isatty():
            return True

    answers = iter(["123456", "654321"])
    prompts = []
    monkeypatch.setattr(sys, "stdin", _TTY())
    monkeypatch.setattr(_getpass, "getpass",
                        lambda prompt: prompts.append(prompt) or next(answers))
    monkeypatch.setenv("NIXON_REMOTE_TOTP_PROMPT", "1")
    monkeypatch.delenv(TOTP_ENV, raising=False)
    monkeypatch.delenv(TOTP_SECONDARY_ENV, raising=False)
    call_remote("pricing_engine", [1], url="http://127.0.0.1:8787/rpc",
                secret=SECRET, opener=opener)
    assert captured["body"]["totp"] == "123456"
    assert captured["body"]["totp_secondary"] == "654321"
    assert prompts == [
        "Google Authenticator code: ", "Microsoft Authenticator code: "]


def test_totp_prompt_opt_in_fails_closed_when_not_interactive(monkeypatch):
    class _NoTTY:
        @staticmethod
        def isatty():
            return False

    monkeypatch.setattr(sys, "stdin", _NoTTY())
    monkeypatch.setenv("NIXON_REMOTE_TOTP_PROMPT", "1")
    monkeypatch.delenv(TOTP_ENV, raising=False)
    monkeypatch.delenv(TOTP_SECONDARY_ENV, raising=False)
    with pytest_raises(RemoteError):
        call_remote("pricing_engine", [1], url="http://127.0.0.1:8787/rpc",
                    secret=SECRET, opener=lambda _u, _b: b'{"result": 1}')


def test_embedded_client_totp_prompt_opt_in(monkeypatch):
    import getpass as _getpass

    client, _remote = split_module(SOURCE)
    ns = {}
    exec(compile(client, "<client>", "exec"), ns)
    captured = {}

    import obfuscator.remote_exec as rx

    class _Resp:
        def read(self):
            return b'{"result": 5}'

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class _TTY:
        @staticmethod
        def isatty():
            return True

    answers = iter(["123456", "654321"])
    real_urlopen = rx.urllib.request.urlopen

    def fake_urlopen(request, timeout=None):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Resp()

    monkeypatch.setattr(sys, "stdin", _TTY())
    monkeypatch.setattr(_getpass, "getpass", lambda prompt: next(answers))
    monkeypatch.setenv("NIXON_REMOTE_TOTP_PROMPT", "1")
    monkeypatch.delenv(TOTP_ENV, raising=False)
    monkeypatch.delenv(TOTP_SECONDARY_ENV, raising=False)
    monkeypatch.setenv(URL_ENV, "https://relay.invalid/rpc")
    monkeypatch.setenv(SECRET_ENV, SECRET.hex())
    rx.urllib.request.urlopen = fake_urlopen
    try:
        assert ns["pricing_engine"](10, "gold") == 5
    finally:
        rx.urllib.request.urlopen = real_urlopen
    assert captured["body"]["totp"] == "123456"
    assert captured["body"]["totp_secondary"] == "654321"
    assert captured["body"]["kwargs"] == {}
