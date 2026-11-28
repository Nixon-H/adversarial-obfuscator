"""Regression tests for the adversarial audit of remote-execution networking."""
import asyncio
import base64
import hashlib
import importlib.util
import json
import os
import sqlite3
import sys
import time
import types
import urllib.error
import urllib.request

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from obfuscator import webpush  # noqa: E402
from obfuscator.cloudflare_remote import (  # noqa: E402
    derive_customer_credentials, write_cloudflare_worker,
)
from obfuscator.remote_exec import (  # noqa: E402
    RemoteError, RemoteRegistry, call_remote, sign_request, split_module,
)
import obfuscator.remote_exec as remote_exec_module  # noqa: E402
from obfuscator.totp import totp_code  # noqa: E402


MASTER_HEX = "aa" * 32
CUSTOMER = "acme"
KEY_ID = "ab" * 12
RP_ID = "approval.example.test"

SOURCE = '''\
from obfuscator.remote_exec import remote

@remote
def hidden_pricing(x, scale=2):
    coefficient = 991
    return coefficient + x * scale
'''


class _FakeResponse(dict):
    def __init__(self, body=None, headers=None):
        self.headers = dict(headers or {})
        self.body = body
        if isinstance(body, str):
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = None
            if isinstance(parsed, dict):
                super().__init__(parsed)


class _FakeDurableObject:
    def __init__(self, ctx=None, env=None):
        self.ctx = ctx
        self.env = env


class _FakeWorkerEntrypoint:
    pass


class _FakeRequest:
    method = "POST"

    def __init__(self, doc):
        self._raw = json.dumps(doc, separators=(",", ":"))
        self.headers = {"host": RP_ID}
        self.url = "https://" + RP_ID + "/"

    async def text(self):
        return self._raw


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def toArray(self):
        return list(self._rows)


class _FakeSQL:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")

    def exec(self, query, *bindings):
        cursor = self.db.execute(query, bindings)
        self.db.commit()
        return _Cursor(cursor.fetchall())


class _FakeSecurityNamespace:
    def __init__(self, registry):
        self._registry = registry

    def idFromName(self, name):
        assert name == "global"
        return name

    def get(self, object_id):
        assert object_id == "global"
        return self._registry


def _load_worker(tmp_path, monkeypatch):
    _client, functions = split_module(SOURCE)
    target = tmp_path / "worker"
    write_cloudflare_worker(functions, str(target), worker_name="audit-remote")

    workers = types.ModuleType("workers")
    workers.DurableObject = _FakeDurableObject
    workers.Response = _FakeResponse
    workers.WorkerEntrypoint = _FakeWorkerEntrypoint
    monkeypatch.setitem(sys.modules, "workers", workers)
    monkeypatch.delitem(sys.modules, "remote_impl", raising=False)
    monkeypatch.syspath_prepend(str(target / "src"))

    entry = target / "src" / "entry.py"
    spec = importlib.util.spec_from_file_location("generated_audit_worker", str(entry))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    sql = _FakeSQL()
    ctx = types.SimpleNamespace(storage=types.SimpleNamespace(sql=sql))
    registry = module.SecurityRegistry(ctx, None)
    env = types.SimpleNamespace(
        NIXON_REMOTE_MASTER_SECRET=MASTER_HEX,
        NIXON_REMOTE_RP_ID=RP_ID,
        SECURITY=_FakeSecurityNamespace(registry),
    )
    worker = module.Default()
    worker.env = env
    return module, worker, registry


def _fetch(worker, doc):
    return asyncio.run(worker.fetch(_FakeRequest(doc)))


def _approval_payload(nonce="approval-nonce", at=None, include_totp=False):
    args = [7]
    kwargs = {"scale": 3}
    now = time.time() if at is None else float(at)
    creds = derive_customer_credentials(MASTER_HEX, CUSTOMER)
    secret = bytes.fromhex(creds["hmac_secret"])
    doc = {
        "version": 1,
        "function": "hidden_pricing",
        "args": args,
        "kwargs": kwargs,
        "nonce": nonce,
        "timestamp": now,
        "signature": sign_request(
            secret, "hidden_pricing", args, nonce, now, kwargs),
        "customer": CUSTOMER,
    }
    if include_totp:
        doc["totp"] = totp_code(creds["totp_primary_secret"], at=now)
        doc["totp_secondary"] = totp_code(creds["totp_secondary_secret"], at=now)
    return doc


def _install_approval_key(registry):
    return asyncio.run(registry.enrol_key(
        CUSTOMER, KEY_ID, "x", "y", "audit-phone", "token-hash",
        time.time(), "credential-id"))


async def _accepting_webauthn(_key_doc, _doc, _message, _rp_id):
    return True, "ok"


def test_disabled_customer_cannot_list_approve_or_collect_inflight_request(
        tmp_path, monkeypatch):
    """Customer disable must be effective for approval flow, not only new RPCs."""
    module, worker, registry = _load_worker(tmp_path, monkeypatch)
    assert _install_approval_key(registry) == "ok"
    monkeypatch.setattr(module, "_webauthn_verify", _accepting_webauthn)

    request_doc = _approval_payload()
    submitted = _fetch(worker, request_doc)
    assert submitted.get("approval_pending") is True

    assert asyncio.run(registry.set_customer_disabled(CUSTOMER, True)) == "ok"
    stamp = str(int(time.time()))
    pending = _fetch(worker, {
        "type": "pending", "version": 1, "customer": CUSTOMER,
        "key_id": KEY_ID, "ts": stamp,
    })
    assert "access revoked" in pending["error"]

    decision = _fetch(worker, {
        "type": "approve", "version": 1, "customer": CUSTOMER,
        "key_id": KEY_ID, "approval_id": submitted["approval_id"],
        "request_hash": request_doc["signature"], "decision": "approve",
        "ts": stamp,
    })
    assert "access revoked" in decision["error"]
    assert decision.get("approved") is not True

    poll = _fetch(worker, {
        "type": "poll", "version": 1, "customer": CUSTOMER,
        "approval_id": submitted["approval_id"],
    })
    assert "access revoked" in poll["error"]
    assert "result" not in poll


def test_totp_pair_with_approval_cannot_execute_two_requests(
        tmp_path, monkeypatch):
    """Defense-in-depth TOTP replay limits must still bind in approval mode."""
    module, worker, registry = _load_worker(tmp_path, monkeypatch)
    assert _install_approval_key(registry) == "ok"
    monkeypatch.setattr(module, "_webauthn_verify", _accepting_webauthn)
    worker.env.NIXON_REMOTE_TOTP_WITH_APPROVAL = "1"

    fixed = 1700000000.0
    monkeypatch.setattr(module.time, "time", lambda: fixed)
    first = _approval_payload("pair-replay-1", at=fixed, include_totp=True)
    second = _approval_payload("pair-replay-2", at=fixed, include_totp=True)
    assert first["totp"] == second["totp"]
    first_submission = _fetch(worker, first)
    second_submission = _fetch(worker, second)
    assert first_submission.get("approval_pending") is True
    assert second_submission.get("approval_pending") is True

    stamp = str(int(fixed))
    for submission, request_doc in (
            (first_submission, first), (second_submission, second)):
        out = _fetch(worker, {
            "type": "approve", "version": 1, "customer": CUSTOMER,
            "key_id": KEY_ID, "approval_id": submission["approval_id"],
            "request_hash": request_doc["signature"], "decision": "approve",
            "ts": stamp,
        })
        assert out.get("approved") is True

    first_poll = _fetch(worker, {
        "type": "poll", "version": 1, "customer": CUSTOMER,
        "approval_id": first_submission["approval_id"],
    })
    second_poll = _fetch(worker, {
        "type": "poll", "version": 1, "customer": CUSTOMER,
        "approval_id": second_submission["approval_id"],
    })
    assert first_poll == {"result": 1012}
    assert "authenticator code replayed" in second_poll.get("error", "")
    assert "result" not in second_poll


def _assertion_parts(module, message, rp_id, origin):
    auth_data = (
        hashlib.sha256(rp_id.encode("utf-8")).digest()
        + b"\x05" + b"\x00\x00\x00\x01")
    client = json.dumps({
        "type": "webauthn.get",
        "challenge": module._webauthn_challenge(message),
        "origin": origin,
    }, separators=(",", ":")).encode("utf-8")
    # Minimal well-formed DER sequence; the WebCrypto boundary is replaced in
    # this unit test, so only the parser shape matters here.
    signature_der = bytes.fromhex("3006020101020101")
    return {
        "authenticatorData": base64.urlsafe_b64encode(auth_data).decode().rstrip("="),
        "clientDataJSON": base64.urlsafe_b64encode(client).decode().rstrip("="),
        "signature": base64.urlsafe_b64encode(signature_der).decode().rstrip("="),
    }


def test_webauthn_assertion_rejects_unexpected_origin(tmp_path, monkeypatch):
    """A validly-signed assertion for another origin must not authorise execution."""
    module, _worker, _registry = _load_worker(tmp_path, monkeypatch)

    async def valid_ecdsa(_x, _y, _signature_hex, _message):
        return True

    monkeypatch.setattr(module, "_ecdsa_verify", valid_ecdsa)
    message = b"audit\x00message"
    key_doc = {"x": "x", "y": "y"}
    good = _assertion_parts(module, message, RP_ID, "https://" + RP_ID)
    ok, _detail = asyncio.run(module._webauthn_verify(
        key_doc, good, message, RP_ID))
    assert ok is True

    evil = _assertion_parts(
        module, message, RP_ID, "https://evil." + RP_ID)
    ok, detail = asyncio.run(module._webauthn_verify(
        key_doc, evil, message, RP_ID))
    assert ok is False
    assert detail == "challenge"

    insecure = _assertion_parts(module, message, RP_ID, "http://" + RP_ID)
    ok, _detail = asyncio.run(module._webauthn_verify(
        key_doc, insecure, message, RP_ID))
    assert ok is False


def test_webauthn_enrolment_client_data_rejects_unexpected_origin(tmp_path, monkeypatch):
    module, _worker, _registry = _load_worker(tmp_path, monkeypatch)
    message = b"enrolment-message"
    client = json.dumps({
        "type": "webauthn.create",
        "challenge": module._webauthn_challenge(message),
        "origin": "https://evil." + RP_ID,
    }, separators=(",", ":")).encode("utf-8")
    assert module._check_client_data(client, "webauthn.create", message, RP_ID) is False


def _fixture_private_key_b64u():
    scalar = 1 + 2 + 4  # small, publicly obvious test scalar; not deployment key material
    return base64.urlsafe_b64encode(scalar.to_bytes(32, "big")).decode().rstrip("=")


def test_worker_webpush_jwt_matches_reference_and_failure_is_contained(
        tmp_path, monkeypatch):
    module, _worker, _registry = _load_worker(tmp_path, monkeypatch)
    private = _fixture_private_key_b64u()
    message = b"audit signing input"
    assert module._wp_es256_sign(private, message) == webpush.es256_sign(private, message)

    token = module._wp_vapid_jwt(private, "https://push.example", "mailto:ops@example.test")
    parts = token.split(".")
    assert len(parts) == 3
    claims = json.loads(base64.urlsafe_b64decode(parts[1] + "==").decode())
    assert claims["aud"] == "https://push.example"

    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    public_key = ec.derive_private_key(7, ec.SECP256R1()).public_key()
    raw_sig = base64.urlsafe_b64decode(parts[2] + "==")
    der_sig = utils.encode_dss_signature(
        int.from_bytes(raw_sig[:32], "big"), int.from_bytes(raw_sig[32:], "big"))
    public_key.verify(
        der_sig, (parts[0] + "." + parts[1]).encode("ascii"),
        ec.ECDSA(hashes.SHA256()))

    workers_module = sys.modules["workers"]
    seen = {}

    async def successful_fetch(endpoint, **kwargs):
        seen["endpoint"] = endpoint
        seen["kwargs"] = kwargs
        return types.SimpleNamespace(status=201)

    monkeypatch.setattr(workers_module, "fetch", successful_fetch, raising=False)
    assert asyncio.run(module._webpush_tickle(
        "https://push.example/subscription", private, "public",
        "mailto:ops@example.test")) == 201
    headers = seen["kwargs"]["headers"]
    assert headers["TTL"] == "900"
    assert headers["Authorization"].startswith("vapid t=")
    assert "Content-Length" not in headers

    async def broken_fetch(*_args, **_kwargs):
        raise OSError("push service unreachable")

    monkeypatch.setattr(workers_module, "fetch", broken_fetch, raising=False)
    assert asyncio.run(module._webpush_tickle(
        "https://push.example/subscription", private, "public",
        "mailto:ops@example.test")) == 0


def test_webpush_send_tickle_never_raises_on_transport_failure(monkeypatch):
    def broken_urlopen(_request, timeout=0):
        raise urllib.error.URLError("push service unreachable")

    monkeypatch.setattr(urllib.request, "urlopen", broken_urlopen)
    assert webpush.send_tickle(
        "https://push.example/subscription", _fixture_private_key_b64u(),
        "public", "mailto:ops@example.test") == 0


def test_reference_registry_does_not_leak_implementation_exception_details():
    secret = bytes([17]) * 32
    registry = RemoteRegistry(secret)

    def explosive():
        raise RuntimeError("confidential coefficient 991")

    registry.register("explosive", explosive)
    nonce = "registry-nonce"
    body = json.dumps({
        "version": 1,
        "function": "explosive",
        "args": [],
        "kwargs": {},
        "nonce": nonce,
        "timestamp": 1000.0,
        "signature": sign_request(secret, "explosive", [], nonce, 1000.0, {}),
    }).encode("utf-8")
    out = json.loads(registry.handle(body, now=1000.0))
    assert out == {"error": "remote function failed"}
    assert "confidential coefficient" not in json.dumps(out)
    assert "991" not in json.dumps(out)


def _fake_clock(monkeypatch):
    now = [1000.0]

    def fake_time():
        return now[0]

    def fake_sleep(seconds):
        now[0] += seconds

    monkeypatch.setattr(remote_exec_module.time, "time", fake_time)
    monkeypatch.setattr(remote_exec_module.time, "sleep", fake_sleep)
    return now


@pytest.mark.parametrize("bad_timeout", ["inf", "+inf", "1e999"])
def test_call_remote_nonfinite_approval_timeout_still_times_out(
        monkeypatch, bad_timeout):
    monkeypatch.setenv(remote_exec_module.APPROVAL_TIMEOUT_ENV, bad_timeout)
    now = _fake_clock(monkeypatch)

    def pending_opener(_url, body):
        request = json.loads(body.decode("utf-8"))
        if request.get("type") == "poll":
            return json.dumps({"approval_status": "pending"}).encode("utf-8")
        return json.dumps({
            "approval_pending": True,
            "approval_id": "a" * 64,
        }).encode("utf-8")

    with pytest.raises(RemoteError, match="approval was not completed"):
        call_remote(
            "hidden_pricing", [], url="https://service.invalid/rpc",
            secret=bytes([17]) * 32, opener=pending_opener)
    assert now[0] >= 1150.0


class _MemoryResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def test_embedded_client_nonfinite_approval_timeout_still_times_out(monkeypatch):
    monkeypatch.setenv("NIXON_REMOTE_URL", "https://service.invalid/rpc")
    monkeypatch.setenv("NIXON_REMOTE_SECRET", (bytes([17]) * 32).hex())
    monkeypatch.setenv("NIXON_REMOTE_APPROVAL_TIMEOUT", "nan")
    now = _fake_clock(monkeypatch)

    initial = json.dumps({
        "approval_pending": True,
        "approval_id": "b" * 64,
    }).encode("utf-8")
    pending = json.dumps({"approval_status": "pending"}).encode("utf-8")

    def fake_urlopen(request, timeout=0):
        body = json.loads(request.data.decode("utf-8"))
        return _MemoryResponse(pending if body.get("type") == "poll" else initial)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    namespace = {}
    exec(remote_exec_module.EMBEDDED_CLIENT_SOURCE, namespace)
    with pytest.raises(RuntimeError, match="approval was not completed"):
        namespace["_nx_call_remote"]("hidden_pricing", [], {})
    assert now[0] >= 1150.0

