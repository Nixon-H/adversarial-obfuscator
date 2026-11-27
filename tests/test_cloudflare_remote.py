"""Generated Cloudflare Worker behavior for remote split execution."""
import asyncio
import importlib.util
import json
import os
import stat
import sys
import time
import types

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from obfuscator.cloudflare_remote import (  # noqa: E402
    WORKER_MARKER, cloudflare_remote_implementation_source,
    cloudflare_worker_source, derive_customer_credentials,
    main as cloudflare_remote_main, write_cloudflare_worker,
    write_customer_provisioning, write_master_provisioning,
)
from obfuscator.remote_exec import split_module, sign_request  # noqa: E402
from obfuscator.totp import new_base32_secret, totp_code  # noqa: E402

MASTER_HEX = "aa" * 32
SHARED_SECRET_HEX = "22" * 32
CUSTOMER = "acme"
CUSTOMER_CREDS = derive_customer_credentials(MASTER_HEX, CUSTOMER)

SOURCE = '''\
from obfuscator.remote_exec import remote

@remote
def hidden_pricing(x, scale=2):
    coefficient = 991
    return coefficient + x * scale
'''


class _FakeResponse:
    @classmethod
    def json(cls, doc):
        return doc


class _FakeWorkerEntrypoint:
    pass


class _FakeDurableObject:
    def __init__(self, ctx=None, env=None):
        self.ctx = ctx
        self.env = env


class _FakeRequest:
    method = "POST"

    def __init__(self, doc):
        self._raw = json.dumps(doc, separators=(",", ":"))

    async def text(self):
        return self._raw


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def toArray(self):
        return list(self._rows)


class _FakeSQL:
    """SQLite-backed double matching Durable Object storage semantics.

    The real runtime is SQLite inside the Durable Object, so driving the same
    statements through sqlite3 exercises the actual schema, upserts, and
    transitions instead of reimplementing them in the test double.
    """

    def __init__(self):
        import sqlite3
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


def _load_worker(tmp_path, monkeypatch, source=SOURCE):
    _client, functions = split_module(source)
    target = tmp_path / "worker"
    write_cloudflare_worker(functions, str(target), worker_name="test-remote")

    workers = types.ModuleType("workers")
    workers.DurableObject = _FakeDurableObject
    workers.Response = _FakeResponse
    workers.WorkerEntrypoint = _FakeWorkerEntrypoint
    monkeypatch.setitem(sys.modules, "workers", workers)
    monkeypatch.delitem(sys.modules, "remote_impl", raising=False)

    monkeypatch.syspath_prepend(str(target / "src"))
    entry = target / "src" / "entry.py"
    spec = importlib.util.spec_from_file_location("generated_cf_worker", str(entry))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    sql = _FakeSQL()
    ctx = types.SimpleNamespace(storage=types.SimpleNamespace(sql=sql))
    registry = module.SecurityRegistry(ctx, None)
    env = types.SimpleNamespace(
        NIXON_REMOTE_MASTER_SECRET=MASTER_HEX,
        SECURITY=_FakeSecurityNamespace(registry),
    )
    worker = module.Default()
    worker.env = env
    return module, worker, sql, target


def _valid_payload(env=None, *, customer=CUSTOMER, function="hidden_pricing",
                   args=None, kwargs=None, nonce="nonce-1"):
    args = [7] if args is None else args
    kwargs = {"scale": 3} if kwargs is None else kwargs
    now = time.time()
    creds = derive_customer_credentials(MASTER_HEX, customer)
    secret = bytes.fromhex(creds["hmac_secret"])
    doc = {
        "version": 1,
        "function": function,
        "args": args,
        "kwargs": kwargs,
        "nonce": nonce,
        "timestamp": now,
        "signature": sign_request(secret, function, args, nonce, now, kwargs),
        "totp": totp_code(creds["totp_primary_secret"], at=now),
        "totp_secondary": totp_code(creds["totp_secondary_secret"], at=now),
    }
    if customer is not None:
        doc["customer"] = customer
    return doc


def _enable_shared_mode(worker):
    primary = new_base32_secret()
    secondary = new_base32_secret()
    while secondary == primary:
        secondary = new_base32_secret()
    worker.env.NIXON_REMOTE_MASTER_SECRET = ""
    worker.env.NIXON_REMOTE_ALLOW_SHARED = "1"
    worker.env.NIXON_REMOTE_SECRET = SHARED_SECRET_HEX
    worker.env.NIXON_REMOTE_TOTP_SECRET = primary
    worker.env.NIXON_REMOTE_TOTP2_SECRET = secondary
    return primary, secondary


def _shared_payload(primary, secondary, *, nonce="shared-1"):
    args = [7]
    kwargs = {"scale": 3}
    now = time.time()
    secret = bytes.fromhex(SHARED_SECRET_HEX)
    return {
        "version": 1,
        "function": "hidden_pricing",
        "args": args,
        "kwargs": kwargs,
        "nonce": nonce,
        "timestamp": now,
        "signature": sign_request(
            secret, "hidden_pricing", args, nonce, now, kwargs),
        "totp": totp_code(primary, at=now),
        "totp_secondary": totp_code(secondary, at=now),
    }


def _fetch(worker, doc):
    return asyncio.run(worker.fetch(_FakeRequest(doc)))


def test_generated_project_layout_permissions_and_worker_source(tmp_path):
    _client, functions = split_module(SOURCE)
    target = tmp_path / "worker"
    write_cloudflare_worker(functions, str(target), worker_name="test-remote")
    assert (target / WORKER_MARKER).exists()
    assert (target / "wrangler.jsonc").exists()
    assert (target / "pyproject.toml").exists()
    assert (target / ".gitignore").exists()
    assert (target / "DEPLOYMENT.md").exists()
    entry = (target / "src" / "entry.py").read_text()
    implementation = (target / "src" / "remote_impl.py").read_text()
    deployment = (target / "DEPLOYMENT.md").read_text()
    assert "coefficient = 991" not in entry
    assert "coefficient = 991" in implementation
    assert "class SecurityRegistry" in entry
    assert "NIXON_REMOTE_MASTER_SECRET" in entry
    assert "NIXON_REMOTE_RATE_LIMIT_PER_MINUTE" in entry
    assert "NIXON_REMOTE_TOTP_PAIR_MAX_USES" in entry
    assert "NIXON_REMOTE_DISABLED_CUSTOMERS" in deployment
    assert "Request-bound phone approval" in deployment
    assert stat.S_IMODE((target / "src" / "entry.py").stat().st_mode) & 0o077 == 0
    assert stat.S_IMODE((target / "src" / "remote_impl.py").stat().st_mode) & 0o077 == 0
    assert stat.S_IMODE(target.stat().st_mode) & 0o077 == 0
    config = json.loads((target / "wrangler.jsonc").read_text())
    assert config["compatibility_flags"] == ["python_workers"]
    assert config["durable_objects"]["bindings"][0]["name"] == "SECURITY"
    assert config["durable_objects"]["bindings"][0]["class_name"] == "SecurityRegistry"


def test_worker_generation_refuses_to_replace_existing_path(tmp_path):
    _client, functions = split_module(SOURCE)
    target = tmp_path / "worker"
    target.mkdir()
    with pytest.raises(FileExistsError):
        write_cloudflare_worker(functions, str(target))


def test_customer_credential_derivation_is_deterministic_and_independent():
    first = derive_customer_credentials(MASTER_HEX, "acme")
    second = derive_customer_credentials(MASTER_HEX, "acme")
    other = derive_customer_credentials(MASTER_HEX, "other-customer")
    assert first == second
    assert first["hmac_secret"] != other["hmac_secret"]
    assert first["totp_primary_secret"] != other["totp_primary_secret"]
    assert first["totp_primary_secret"] != first["totp_secondary_secret"]
    assert len(first["hmac_secret"]) == 64
    with pytest.raises(Exception, match="customer identity"):
        derive_customer_credentials(MASTER_HEX, "bad customer")
    with pytest.raises(ValueError, match="master secret"):
        derive_customer_credentials("aa", "acme")


def test_master_and_customer_provisioning_files_are_owner_only(tmp_path):
    master_path = tmp_path / "master-provisioning.json"
    customer_path = tmp_path / "customer-provisioning.json"
    master = write_master_provisioning(str(master_path))
    customer = write_customer_provisioning(
        str(customer_path), master_secret=master["master_secret"],
        customer_id="acme")
    assert stat.S_IMODE(master_path.stat().st_mode) & 0o077 == 0
    assert stat.S_IMODE(customer_path.stat().st_mode) & 0o077 == 0
    derived = derive_customer_credentials(master["master_secret"], "acme")
    assert customer["customer_id"] == "acme"
    assert customer["hmac_secret"] == derived["hmac_secret"]
    assert customer["primary"]["secret"] == derived["totp_primary_secret"]
    assert customer["secondary"]["secret"] == derived["totp_secondary_secret"]
    with pytest.raises(FileExistsError):
        write_master_provisioning(str(master_path))
    with pytest.raises(FileExistsError):
        write_customer_provisioning(
            str(customer_path), master_secret=master["master_secret"],
            customer_id="acme")


def test_customer_provisioning_cli_writes_file_without_printing_secrets(tmp_path, capsys):
    master_path = tmp_path / "master.json"
    customer_path = tmp_path / "customer.json"
    master = write_master_provisioning(str(master_path))
    rc = cloudflare_remote_main([
        "provision-customer", str(customer_path), "--customer-id", "acme",
        "--master-secret-file", str(master_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert customer_path.exists()
    assert master["master_secret"] not in out
    provisioned = json.loads(customer_path.read_text())
    assert provisioned["hmac_secret"] not in out
    assert provisioned["customer_id"] == "acme"


def test_generated_worker_signing_matches_protocol_vectors(tmp_path, monkeypatch):
    module, _worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    args = [1, -0.0, "é", True, None, {"b": 2, "a": 1.5}]
    kwargs = {"rate": 0.5, "label": "x"}
    vector_secret = bytes.fromhex("11" * 32)
    assert module._sign(vector_secret, "f", args, kwargs, "nonce", 1000.0) == (
        "b2adc43bf63eb2bfeb87e9b5b509f636b2de11ea36189d23893c7a1be44c030f")
    assert module._sign(bytes.fromhex(SHARED_SECRET_HEX), "f", [1], {}, "n", 1.0) != module._sign(
        bytes.fromhex(SHARED_SECRET_HEX), "f", [1.0], {}, "n", 1.0)


def test_generated_worker_customer_derivation_matches_reference(tmp_path, monkeypatch):
    module, _worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    secret, primary, secondary = module._derive_customer_credentials(
        bytes.fromhex(MASTER_HEX), CUSTOMER)
    assert secret.hex() == CUSTOMER_CREDS["hmac_secret"]
    assert primary == CUSTOMER_CREDS["totp_primary_secret"]
    assert secondary == CUSTOMER_CREDS["totp_secondary_secret"]


def test_generated_worker_totp_matches_reference_implementation(tmp_path, monkeypatch):
    module, _worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    secret = new_base32_secret()
    for when in (0, 29, 30, 59, 1200, 1700000000):
        assert module._totp(secret, when) == totp_code(secret, at=when)


def test_generated_worker_executes_after_hmac_dual_totp_and_security_registry(
        tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    out = _fetch(worker, _valid_payload())
    assert out == {"result": 1012}  # 991 + 7 * 3


def test_customer_bound_mode_requires_customer_identity(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    doc = _valid_payload()
    del doc["customer"]
    out = _fetch(worker, doc)
    assert "customer identity is required" in out["error"]


def test_customer_credential_cannot_be_used_for_another_customer(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    doc = _valid_payload(customer="acme")
    doc["customer"] = "other-customer"
    out = _fetch(worker, doc)
    assert "signature mismatch" in out["error"]


def test_generated_worker_rejects_bad_hmac_before_execution(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    doc = _valid_payload()
    doc["args"] = [8]
    out = _fetch(worker, doc)
    assert "signature mismatch" in out["error"]


def test_generated_worker_requires_both_totp_factors(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    doc = _valid_payload()
    del doc["totp"]
    assert "authentication failed" in _fetch(worker, doc)["error"]

    doc = _valid_payload(nonce="nonce-2")
    doc["totp_secondary"] = "000000"
    correct = totp_code(CUSTOMER_CREDS["totp_secondary_secret"], at=doc["timestamp"])
    if doc["totp_secondary"] == correct:
        doc["totp_secondary"] = "999999"
    assert "authentication failed" in _fetch(worker, doc)["error"]


def test_generated_worker_rejects_replayed_nonce(tmp_path, monkeypatch):
    _module, worker, sql, _target = _load_worker(tmp_path, monkeypatch)
    doc = _valid_payload()
    assert _fetch(worker, doc) == {"result": 1012}
    replayed = _fetch(worker, doc)
    assert "replayed" in replayed["error"]
    rows = sql.db.execute(
        "SELECT nonce FROM nonces WHERE nonce = ?", (doc["nonce"],)).fetchall()
    assert len(rows) == 1


def test_totp_pair_cannot_be_reused_with_a_different_nonce(tmp_path, monkeypatch):
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    fixed = 1700000000.0
    monkeypatch.setattr(module.time, "time", lambda: fixed)
    first = _valid_payload(nonce="totp-use-1")
    assert _fetch(worker, first) == {"result": 1012}
    second = _valid_payload(nonce="totp-use-2")
    assert second["totp"] == first["totp"]
    assert second["totp_secondary"] == first["totp_secondary"]
    out = _fetch(worker, second)
    assert "authenticator code replayed" in out["error"]


def test_security_registry_sql_behavior_expires_old_nonces(tmp_path, monkeypatch):
    module, _worker, sql, _target = _load_worker(tmp_path, monkeypatch)
    ctx = types.SimpleNamespace(storage=types.SimpleNamespace(sql=sql))
    registry = module.SecurityRegistry(ctx, None)
    assert asyncio.run(registry.check_and_store(
        "n", 1000.0, CUSTOMER, 60, 10000)) == "ok"
    assert asyncio.run(registry.check_and_store(
        "n", 1001.0, CUSTOMER, 60, 10000)) == "replayed"
    assert asyncio.run(registry.check_and_store(
        "n", 1701.0, CUSTOMER, 60, 10000)) == "ok"


def test_totp_failure_limit_throttles_hmac_valid_guessing(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    worker.env.NIXON_REMOTE_AUTH_FAILURE_LIMIT_PER_MINUTE = "2"
    for index in range(2):
        doc = _valid_payload(nonce="bad-totp-%d" % index)
        doc["totp"] = "000000"
        if doc["totp"] == totp_code(
                CUSTOMER_CREDS["totp_primary_secret"], at=doc["timestamp"]):
            doc["totp"] = "999999"
        assert "authentication failed" in _fetch(worker, doc)["error"]
    doc = _valid_payload(nonce="after-auth-limit")
    out = _fetch(worker, doc)
    assert "authentication failure limit" in out["error"]


def test_successful_totp_does_not_consume_failure_budget(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    worker.env.NIXON_REMOTE_AUTH_FAILURE_LIMIT_PER_MINUTE = "1"
    worker.env.NIXON_REMOTE_TOTP_PAIR_MAX_USES = "10"
    assert _fetch(worker, _valid_payload(nonce="success-a")) == {"result": 1012}
    assert _fetch(worker, _valid_payload(nonce="success-b")) == {"result": 1012}


def test_security_registry_enforces_minute_rate_limit(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    worker.env.NIXON_REMOTE_RATE_LIMIT_PER_MINUTE = "2"
    worker.env.NIXON_REMOTE_QUOTA_PER_DAY = "100"
    worker.env.NIXON_REMOTE_TOTP_PAIR_MAX_USES = "10"
    assert _fetch(worker, _valid_payload(nonce="rate-1")) == {"result": 1012}
    assert _fetch(worker, _valid_payload(nonce="rate-2")) == {"result": 1012}
    out = _fetch(worker, _valid_payload(nonce="rate-3"))
    assert "rate limit exceeded" in out["error"]


def test_security_registry_enforces_daily_quota(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    worker.env.NIXON_REMOTE_RATE_LIMIT_PER_MINUTE = "100"
    worker.env.NIXON_REMOTE_QUOTA_PER_DAY = "2"
    worker.env.NIXON_REMOTE_TOTP_PAIR_MAX_USES = "10"
    assert _fetch(worker, _valid_payload(nonce="quota-1")) == {"result": 1012}
    assert _fetch(worker, _valid_payload(nonce="quota-2")) == {"result": 1012}
    out = _fetch(worker, _valid_payload(nonce="quota-3"))
    assert "quota exceeded" in out["error"]


def test_usage_policy_misconfiguration_fails_closed(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    worker.env.NIXON_REMOTE_RATE_LIMIT_PER_MINUTE = "not-a-number"
    out = _fetch(worker, _valid_payload())
    assert "usage policy is not configured" in out["error"]


def test_revoked_customer_fails_before_signature_or_execution(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    worker.env.NIXON_REMOTE_DISABLED_CUSTOMERS = "other,acme"
    out = _fetch(worker, _valid_payload())
    assert "access revoked" in out["error"]


def test_generated_worker_requires_security_binding(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    worker.env.SECURITY = None
    out = _fetch(worker, _valid_payload())
    assert "replay protection" in out["error"]


def test_generated_worker_rejects_missing_or_malformed_requests(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    assert "unsupported" in _fetch(worker, {"version": 2})["error"]
    doc = _valid_payload()
    doc["kwargs"] = []
    assert "args must be" in _fetch(worker, doc)["error"]
    doc = _valid_payload()
    doc["timestamp"] = time.time() + 9999
    assert "expired" in _fetch(worker, doc)["error"]
    doc = _valid_payload()
    doc["customer"] = "bad customer"
    assert "malformed customer" in _fetch(worker, doc)["error"]


def test_shared_mode_requires_explicit_opt_in_and_still_executes(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    primary = new_base32_secret()
    secondary = new_base32_secret()
    worker.env.NIXON_REMOTE_MASTER_SECRET = ""
    worker.env.NIXON_REMOTE_SECRET = SHARED_SECRET_HEX
    worker.env.NIXON_REMOTE_TOTP_SECRET = primary
    worker.env.NIXON_REMOTE_TOTP2_SECRET = secondary
    out = _fetch(worker, _shared_payload(primary, secondary))
    assert "customer-bound remote credentials" in out["error"]

    primary, secondary = _enable_shared_mode(worker)
    out = _fetch(worker, _shared_payload(primary, secondary))
    assert out == {"result": 1012}


def test_shared_mode_rejects_identical_totp_seed_configuration(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    primary, _secondary = _enable_shared_mode(worker)
    worker.env.NIXON_REMOTE_TOTP2_SECRET = primary
    out = _fetch(worker, _shared_payload(primary, primary))
    assert "not independent" in out["error"]


def test_implementation_exception_details_do_not_leak_to_client(
        tmp_path, monkeypatch, capsys):
    source = '''\
from obfuscator.remote_exec import remote

@remote
def explosive():
    coefficient = 991
    raise RuntimeError("coefficient leaked 991")
'''
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch, source)
    doc = _valid_payload(function="explosive", args=[], kwargs={})
    out = _fetch(worker, doc)
    assert out == {"error": "remote function failed"}
    assert "991" not in json.dumps(out)
    captured = capsys.readouterr().out
    assert "coefficient leaked 991" not in captured
    assert '"outcome":"function-error"' in captured


def test_audit_events_do_not_contain_secrets_or_request_values(
        tmp_path, monkeypatch, capsys):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    doc = _valid_payload(nonce="audit-nonce-unique")
    assert _fetch(worker, doc) == {"result": 1012}
    captured = capsys.readouterr().out
    assert '"outcome":"success"' in captured
    forbidden = [
        MASTER_HEX, CUSTOMER_CREDS["hmac_secret"],
        CUSTOMER_CREDS["totp_primary_secret"],
        CUSTOMER_CREDS["totp_secondary_secret"],
        doc["nonce"], doc["totp"], doc["totp_secondary"],
    ]
    assert not any(value and value in captured for value in forbidden)


def test_worker_source_is_self_contained_except_workers_runtime():
    _client, functions = split_module(SOURCE)
    source = cloudflare_worker_source(functions)
    implementation = cloudflare_remote_implementation_source(functions)
    assert "obfuscator.remote_exec" not in source
    assert "coefficient = 991" not in source
    assert "_remote_impl.hidden_pricing" in source
    assert "coefficient = 991" in implementation
    compile(source, "<generated-worker>", "exec")
    compile(implementation, "<generated-remote-impl>", "exec")


def test_implementation_text_cannot_retrigger_template_substitution():
    src = (
        "from obfuscator.remote_exec import remote\n\n"
        "@remote\n"
        "def token_text():\n"
        "    return '__FUNCTION_MAP__'\n"
    )
    _client, functions = split_module(src)
    generated = cloudflare_worker_source(functions)
    implementation = cloudflare_remote_implementation_source(functions)
    assert "return '__FUNCTION_MAP__'" not in generated
    assert "return '__FUNCTION_MAP__'" in implementation
    assert "_FUNCTIONS = {\n    'token_text': _remote_impl.token_text,\n}" in generated
    compile(generated, "<generated-token-worker>", "exec")
    compile(implementation, "<generated-token-impl>", "exec")


# ── request-bound phone approval ─────────────────────────────────────────

def _b64url(raw):
    import base64 as _b64
    return _b64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


class _Phone:
    """Test double for the browser approval device using real ECDSA."""

    def __init__(self):
        from cryptography.hazmat.primitives.asymmetric import ec
        self._private = ec.generate_private_key(ec.SECP256R1())
        numbers = self._private.public_key().public_numbers()
        self.x = _b64url(numbers.x.to_bytes(32, "big"))
        self.y = _b64url(numbers.y.to_bytes(32, "big"))

    def sign(self, message):
        from cryptography.hazmat.primitives.asymmetric import ec, utils
        from cryptography.hazmat.primitives import hashes
        der = self._private.sign(message, ec.ECDSA(hashes.SHA256()))
        r, s = utils.decode_dss_signature(der)
        return (r.to_bytes(32, "big") + s.to_bytes(32, "big")).hex()

    def key_id(self):
        import hashlib as _hashlib
        return _hashlib.sha256((self.x + ":" + self.y).encode("utf-8")).hexdigest()[:24]


def _install_real_verify(module, monkeypatch):
    """Replace the worker FFI verifier with real ECDSA verification.

    The generated worker verifies through the WebCrypto FFI, which does not
    exist under CPython. This replacement implements the same P-256/SHA-256
    P1363 semantics, so tests exercise real signatures rather than a stub.
    """
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    from cryptography.hazmat.primitives import hashes
    import base64 as _b64

    def unb64url(text):
        return _b64.urlsafe_b64decode(text + "=" * ((4 - len(text) % 4) % 4))

    async def verify(x, y, signature_hex, message):
        try:
            numbers = ec.EllipticCurvePublicNumbers(
                int.from_bytes(unb64url(x), "big"),
                int.from_bytes(unb64url(y), "big"),
                ec.SECP256R1())
            public = numbers.public_key()
            raw = bytes.fromhex(signature_hex)
            if len(raw) != 64:
                return False
            der = utils.encode_dss_signature(
                int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
            public.verify(der, bytes(message), ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False

    monkeypatch.setattr(module, "_ecdsa_verify", verify)


def _enrol(worker, phone, customer=CUSTOMER, token_index=0, tamper=False):
    from obfuscator.cloudflare_remote import derive_enrol_tokens
    token = derive_enrol_tokens(MASTER_HEX, customer)[token_index]["token"]
    message = (b"nixon-remote-enrol-v1\x00" + customer.encode("utf-8")
               + b"\x00" + token.encode("ascii"))
    proof = phone.sign(message + (b"x" if tamper else b""))
    doc = {
        "type": "enrol", "version": 1, "customer": customer, "token": token,
        "x": phone.x, "y": phone.y, "proof": proof, "label": "test-phone",
    }
    return _fetch(worker, doc)


def _pending_items(worker, phone, customer=CUSTOMER):
    stamp = str(int(time.time()))
    message = (b"nixon-remote-pending-v1\x00" + customer.encode("utf-8")
               + b"\x00" + phone.key_id().encode("ascii")
               + b"\x00" + stamp.encode("ascii"))
    doc = {
        "type": "pending", "version": 1, "customer": customer,
        "key_id": phone.key_id(), "ts": stamp, "signature": phone.sign(message),
    }
    out = _fetch(worker, doc)
    assert "pending" in out, out
    return out["pending"]


def _decide(worker, phone, item, decision, customer=CUSTOMER, hash_override=None):
    stamp = str(int(time.time()))
    request_hash = hash_override or item["request_hash"]
    message = (b"nixon-remote-approval-v1\x00" + customer.encode("utf-8")
               + b"\x00" + item["approval_id"].encode("ascii")
               + b"\x00" + request_hash.encode("ascii")
               + b"\x00" + decision.encode("ascii")
               + b"\x00" + stamp.encode("ascii"))
    doc = {
        "type": "approve", "version": 1, "customer": customer,
        "key_id": phone.key_id(), "approval_id": item["approval_id"],
        "request_hash": request_hash, "decision": decision,
        "ts": stamp, "signature": phone.sign(message),
    }
    return _fetch(worker, doc)


def _poll(worker, approval_id, customer=CUSTOMER):
    return _fetch(worker, {
        "type": "poll", "version": 1, "customer": customer,
        "approval_id": approval_id,
    })


def _admin(worker, action, customer=CUSTOMER, key_id="", secret=None):
    from obfuscator.cloudflare_remote import derive_admin_secret
    doc = {
        "type": "admin", "version": 1, "action": action, "customer": customer,
        "secret": derive_admin_secret(MASTER_HEX) if secret is None else secret,
    }
    if key_id:
        doc["key_id"] = key_id
    return _fetch(worker, doc)


def _approval_payload(**overrides):
    doc = _valid_payload(**overrides)
    # Once enrolled, approval supersedes typed codes; clients need not send any.
    doc.pop("totp", None)
    doc.pop("totp_secondary", None)
    return doc


def test_enrol_happy_path_and_tokens_are_single_use(tmp_path, monkeypatch):
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    phone = _Phone()
    out = _enrol(worker, phone)
    assert out.get("enrolled") is True
    assert out["key_id"] == phone.key_id()
    reused = _enrol(worker, _Phone())
    assert "already used" in reused["error"]
    second = _enrol(worker, _Phone(), token_index=1)
    assert second.get("enrolled") is True


def test_enrol_rejects_invalid_token_and_bad_proof(tmp_path, monkeypatch):
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    phone = _Phone()
    out = _enrol(worker, phone, tamper=True)
    assert "proof invalid" in out["error"]
    from obfuscator.cloudflare_remote import derive_enrol_tokens
    doc_token = derive_enrol_tokens(MASTER_HEX, "other-customer")[0]["token"]
    message = (b"nixon-remote-enrol-v1\x00" + CUSTOMER.encode("utf-8")
               + b"\x00" + doc_token.encode("ascii"))
    doc = {
        "type": "enrol", "version": 1, "customer": CUSTOMER, "token": doc_token,
        "x": phone.x, "y": phone.y, "proof": phone.sign(message), "label": "x",
    }
    out = _fetch(worker, doc)
    assert "token invalid" in out["error"]


def test_enrolled_customer_rpc_pends_and_full_approval_executes(tmp_path, monkeypatch):
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True

    submitted = _fetch(worker, _approval_payload())
    assert submitted.get("approval_pending") is True
    assert len(submitted["approval_id"]) == 64

    items = _pending_items(worker, phone)
    assert len(items) == 1
    item = items[0]
    assert item["function"] == "hidden_pricing"
    assert item["approval_id"] == submitted["approval_id"]

    status = _poll(worker, submitted["approval_id"])
    assert status.get("approval_status") == "pending"

    decided = _decide(worker, phone, item, "approve")
    assert decided == {"approved": True}

    out = _poll(worker, submitted["approval_id"])
    assert out == {"result": 1012}


def test_approval_denied_is_terminal_for_the_client(tmp_path, monkeypatch):
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True
    submitted = _fetch(worker, _approval_payload())
    item = _pending_items(worker, phone)[0]
    assert _decide(worker, phone, item, "deny") == {"denied": True}
    out = _poll(worker, submitted["approval_id"])
    assert "denied" in out["error"]


def test_approval_binds_the_exact_stored_request(tmp_path, monkeypatch):
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True
    _fetch(worker, _approval_payload())
    item = _pending_items(worker, phone)[0]
    wrong_hash = "0" * 64 if item["request_hash"] != "0" * 64 else "1" * 64
    out = _decide(worker, phone, item, "approve", hash_override=wrong_hash)
    assert "does not match" in out["error"]
    # The request must still be pending: a mismatched approval records nothing.
    assert len(_pending_items(worker, phone)) == 1


def test_approval_requires_valid_signature_and_active_key(tmp_path, monkeypatch):
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True
    _fetch(worker, _approval_payload())
    item = _pending_items(worker, phone)[0]

    stamp = str(int(time.time()))
    doc = {
        "type": "approve", "version": 1, "customer": CUSTOMER,
        "key_id": phone.key_id(), "approval_id": item["approval_id"],
        "request_hash": item["request_hash"], "decision": "approve",
        "ts": stamp, "signature": "00" * 64,
    }
    out = _fetch(worker, doc)
    assert "signature invalid" in out["error"]

    assert _admin(worker, "revoke-key", key_id=phone.key_id()).get("revoked") is True
    out = _decide(worker, phone, item, "approve")
    assert "not active" in out["error"]


def test_admin_requires_secret_and_disable_blocks_requests(tmp_path, monkeypatch):
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True

    out = _admin(worker, "disable-customer", secret="00" * 32)
    assert "authentication failed" in out["error"]

    assert _admin(worker, "disable-customer").get("disabled") is True
    out = _fetch(worker, _approval_payload(nonce="admin-disabled"))
    assert "access revoked" in out["error"]

    assert _admin(worker, "enable-customer").get("disabled") is False
    submitted = _fetch(worker, _approval_payload(nonce="admin-enabled"))
    assert submitted.get("approval_pending") is True

    keys = _admin(worker, "list-keys")
    assert len(keys["keys"]) == 1
    assert keys["keys"][0]["key_id"] == phone.key_id()


def test_approval_mode_off_executes_directly_and_required_fails_closed(
        tmp_path, monkeypatch):
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True

    worker.env.NIXON_REMOTE_APPROVAL_MODE = "off"
    out = _fetch(worker, _valid_payload(nonce="mode-off"))
    assert out == {"result": 1012}

    worker.env.NIXON_REMOTE_APPROVAL_MODE = "required"
    out = _fetch(worker, _valid_payload(nonce="mode-required-enrolled"))
    assert out.get("approval_pending") is True


def test_approval_required_without_enrolment_fails_closed(tmp_path, monkeypatch):
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    worker.env.NIXON_REMOTE_APPROVAL_MODE = "required"
    out = _fetch(worker, _valid_payload())
    assert "approval enrolment is required" in out["error"]


def test_approval_backlog_is_capped_per_customer(tmp_path, monkeypatch):
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    worker.env.NIXON_REMOTE_MAX_PENDING = "1"
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True
    first = _fetch(worker, _approval_payload(nonce="backlog-1"))
    assert first.get("approval_pending") is True
    second = _fetch(worker, _approval_payload(nonce="backlog-2"))
    assert "backlog is full" in second["error"]


def test_expired_pending_cannot_be_approved(tmp_path, monkeypatch):
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    worker.env.NIXON_REMOTE_APPROVAL_EXPIRY_SECONDS = "30"
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True

    fixed = 1700000000.0
    monkeypatch.setattr(module.time, "time", lambda: fixed)
    submitted = _fetch(worker, _approval_payload())
    assert submitted.get("approval_pending") is True

    monkeypatch.setattr(module.time, "time", lambda: fixed + 31.0)
    # Phone signatures use fresh-ts semantics relative to worker time.
    items = _pending_items_at(worker, phone, fixed + 31.0)
    assert items == [] or all(
        item["approval_id"] != submitted["approval_id"] for item in items)


def _pending_items_at(worker, phone, at, customer=CUSTOMER):
    stamp = str(int(at))
    message = (b"nixon-remote-pending-v1\x00" + customer.encode("utf-8")
               + b"\x00" + phone.key_id().encode("ascii")
               + b"\x00" + stamp.encode("ascii"))
    doc = {
        "type": "pending", "version": 1, "customer": customer,
        "key_id": phone.key_id(), "ts": stamp, "signature": phone.sign(message),
    }
    out = _fetch(worker, doc)
    return out.get("pending", [])


def test_poll_requires_matching_customer(tmp_path, monkeypatch):
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True
    submitted = _fetch(worker, _approval_payload())
    out = _poll(worker, submitted["approval_id"], customer="other-customer")
    assert "unknown" in out["error"]


def test_enrolment_audit_does_not_leak_token(tmp_path, monkeypatch, capsys):
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    from obfuscator.cloudflare_remote import derive_enrol_tokens
    phone = _Phone()
    token = derive_enrol_tokens(MASTER_HEX, CUSTOMER)[0]["token"]
    assert _enrol(worker, phone).get("enrolled") is True
    captured = capsys.readouterr().out
    assert '"outcome":"enrolled"' in captured
    assert token not in captured
    assert phone.x not in captured and phone.y not in captured


def test_get_requests_serve_the_approval_page(tmp_path, monkeypatch):
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)

    class GetRequest:
        method = "GET"

    asyncio.run(worker.fetch(GetRequest()))
    # The fake Response constructor does not model the real runtime; check the
    # page constant directly for the enrolment/signing surface instead.
    page = module._APPROVAL_PAGE
    assert "nixon-remote-approval-v1" in page
    assert "nixon-remote-enrol-v1" in page
    assert "generateKey" in page
    assert "namedCurve" in page
    assert "indexedDB" in page
    assert "fetch" in page


# ── regression tests for defects fixed during approval development ────────

def test_enrolled_customer_valid_totp_does_not_bypass_approval(tmp_path, monkeypatch):
    """The core invariant of the approval design: once a customer holds an
    active approval key, valid typed TOTP codes must NOT execute the request
    directly. If they could, malware with captured/typed codes would bypass
    request-bound approval entirely — the exact weakness approval exists
    to close."""
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True

    # _valid_payload carries fully valid dual-TOTP codes, as malware using
    # captured codes would submit them.
    out = _fetch(worker, _valid_payload(nonce="totp-bypass-attempt"))
    assert out.get("approval_pending") is True
    assert "result" not in out


def test_malformed_master_secret_never_falls_through_to_shared(tmp_path, monkeypatch):
    """Regression: a configured-but-malformed master secret previously could
    fall through to shared-secret mode. It must fail closed instead."""
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    primary, secondary = _enable_shared_mode(worker)
    worker.env.NIXON_REMOTE_MASTER_SECRET = "not-valid-hex"
    out = _fetch(worker, _shared_payload(primary, secondary))
    assert "not configured" in out["error"]
    assert "result" not in out

    worker.env.NIXON_REMOTE_MASTER_SECRET = "abcd"  # well-formed but too short
    out = _fetch(worker, _shared_payload(primary, secondary, nonce="short"))
    assert "not configured" in out["error"]
    assert "result" not in out


def test_approved_result_is_delivered_exactly_once(tmp_path, monkeypatch):
    """Regression for exactly-once terminal delivery: the first poll collects
    the result and destroys the row, so a replayed poll cannot distinguish
    or re-collect anything."""
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True
    submitted = _fetch(worker, _approval_payload())
    item = _pending_items(worker, phone)[0]
    assert _decide(worker, phone, item, "approve").get("approved") is True

    first = _poll(worker, submitted["approval_id"])
    assert first == {"result": 1012}
    second = _poll(worker, submitted["approval_id"])
    assert "unknown or already delivered" in second["error"]
    assert "result" not in second


def test_denial_is_delivered_exactly_once(tmp_path, monkeypatch):
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True
    submitted = _fetch(worker, _approval_payload())
    item = _pending_items(worker, phone)[0]
    assert _decide(worker, phone, item, "deny").get("denied") is True

    first = _poll(worker, submitted["approval_id"])
    assert "denied" in first["error"]
    second = _poll(worker, submitted["approval_id"])
    assert "unknown or already delivered" in second["error"]


def test_correct_approval_after_hash_mismatch_still_executes(tmp_path, monkeypatch):
    """Regression for the atomic hash-binding fix: a mismatched approval must
    record nothing and must not burn the request — a later correct approval
    for the exact stored hash still executes."""
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True
    submitted = _fetch(worker, _approval_payload())
    item = _pending_items(worker, phone)[0]
    wrong_hash = "0" * 64 if item["request_hash"] != "0" * 64 else "1" * 64
    out = _decide(worker, phone, item, "approve", hash_override=wrong_hash)
    assert "does not match" in out["error"]

    # The genuine approval for the exact stored request must still work.
    out = _decide(worker, phone, item, "approve")
    assert out.get("approved") is True
    assert _poll(worker, submitted["approval_id"]) == {"result": 1012}


def test_expired_pending_approval_is_rejected_and_never_executes(tmp_path, monkeypatch):
    """Strengthens the expiry regression: after expiry, an actual approval
    attempt must be rejected and the function must never execute."""
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    worker.env.NIXON_REMOTE_APPROVAL_EXPIRY_SECONDS = "30"
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True

    fixed = 1700000000.0
    monkeypatch.setattr(module.time, "time", lambda: fixed)
    submitted = _fetch(worker, _approval_payload())
    assert submitted.get("approval_pending") is True
    items = _pending_items_at(worker, phone, fixed)
    assert len(items) == 1
    item = items[0]

    later = fixed + 31.0
    monkeypatch.setattr(module.time, "time", lambda: later)
    out = _decide(worker, phone, item, "approve")
    assert "approved" not in out or out.get("approved") is not True
    assert "error" in out
    poll = _poll(worker, submitted["approval_id"])
    assert "result" not in poll


def test_pending_list_rejects_invalid_signature_and_stale_timestamp(
        tmp_path, monkeypatch):
    """Negative regression for the phone pending endpoint: signatures are
    verified and phone timestamps must be fresh."""
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True

    stamp = str(int(time.time()))
    doc = {
        "type": "pending", "version": 1, "customer": CUSTOMER,
        "key_id": phone.key_id(), "ts": stamp, "signature": "00" * 64,
    }
    out = _fetch(worker, doc)
    assert "signature invalid" in out["error"]

    stale = str(int(time.time()) - 400)
    message = (b"nixon-remote-pending-v1\x00" + CUSTOMER.encode("utf-8")
               + b"\x00" + phone.key_id().encode("ascii")
               + b"\x00" + stale.encode("ascii"))
    doc = {
        "type": "pending", "version": 1, "customer": CUSTOMER,
        "key_id": phone.key_id(), "ts": stale, "signature": phone.sign(message),
    }
    out = _fetch(worker, doc)
    assert "expired" in out["error"]


def test_approve_rejects_stale_or_future_timestamp(tmp_path, monkeypatch):
    """Negative regression for decide freshness: validly-signed approvals
    with stale or far-future phone timestamps must be rejected."""
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True
    _fetch(worker, _approval_payload())
    item = _pending_items(worker, phone)[0]

    for label, offset in (("stale", -400), ("future", 400)):
        stamp = str(int(time.time()) + offset)
        message = (b"nixon-remote-approval-v1\x00" + CUSTOMER.encode("utf-8")
                   + b"\x00" + item["approval_id"].encode("ascii")
                   + b"\x00" + item["request_hash"].encode("ascii")
                   + b"\x00approve\x00" + stamp.encode("ascii"))
        doc = {
            "type": "approve", "version": 1, "customer": CUSTOMER,
            "key_id": phone.key_id(), "approval_id": item["approval_id"],
            "request_hash": item["request_hash"], "decision": "approve",
            "ts": stamp, "signature": phone.sign(message),
        }
        out = _fetch(worker, doc)
        assert "expired" in out["error"], label
    # Neither attempt counted as a decision: the request is still pending.
    assert len(_pending_items(worker, phone)) == 1


def test_disabled_customer_cannot_enrol_new_keys(tmp_path, monkeypatch):
    """Invariant: customer disable must block fresh enrolment too, otherwise
    revocation could be sidestepped by enrolling a replacement key with an
    unused token."""
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    phone = _Phone()
    assert _enrol(worker, phone).get("enrolled") is True
    assert _admin(worker, "disable-customer").get("disabled") is True

    second = _Phone()
    out = _enrol(worker, second, token_index=1)
    assert "revoked" in out["error"]
    assert out.get("enrolled") is not True


def test_revoked_key_cannot_list_pending_but_other_device_can(tmp_path, monkeypatch):
    """Per-key revocation granularity: the revoked device loses even read-only
    pending access, while a second enrolled device is unaffected."""
    module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    _install_real_verify(module, monkeypatch)
    first = _Phone()
    second = _Phone()
    assert _enrol(worker, first).get("enrolled") is True
    assert _enrol(worker, second, token_index=1).get("enrolled") is True
    submitted = _fetch(worker, _approval_payload())

    assert _admin(worker, "revoke-key", key_id=first.key_id()).get("revoked") is True
    stamp = str(int(time.time()))
    message = (b"nixon-remote-pending-v1\x00" + CUSTOMER.encode("utf-8")
               + b"\x00" + first.key_id().encode("ascii")
               + b"\x00" + stamp.encode("ascii"))
    out = _fetch(worker, {
        "type": "pending", "version": 1, "customer": CUSTOMER,
        "key_id": first.key_id(), "ts": stamp, "signature": first.sign(message),
    })
    assert "not active" in out["error"]

    # The surviving device can still see and approve the request.
    items = _pending_items(worker, second)
    assert len(items) == 1
    assert _decide(worker, second, items[0], "approve").get("approved") is True
    assert _poll(worker, submitted["approval_id"]) == {"result": 1012}


def test_deployment_template_renders_without_keyerror(tmp_path):
    """Regression: literal JSON braces in the deployment documentation once
    crashed .format() with KeyError. The template must always render."""
    from obfuscator.cloudflare_remote import (
        COMPATIBILITY_DATE, _DEPLOYMENT_TEMPLATE, _PYPROJECT_TEMPLATE,
        _WRANGLER_TEMPLATE)
    # Render each template exactly as write_cloudflare_worker does.
    deployment = _DEPLOYMENT_TEMPLATE.format(worker_name="my-worker")
    pyproject = _PYPROJECT_TEMPLATE.format(worker_name="my-worker")
    wrangler = _WRANGLER_TEMPLATE.format(
        worker_name="my-worker", compatibility_date=COMPATIBILITY_DATE)
    assert "my-worker" in deployment and "wrangler" in deployment
    assert "my-worker" in pyproject
    assert "my-worker" in wrangler and COMPATIBILITY_DATE in wrangler


def test_approval_page_uses_one_timestamp_for_sign_and_submit(tmp_path, monkeypatch):
    """Regression for the approval-page timestamp defect: the same `stamp`
    value must feed both the signed message parts and the submitted body —
    signing one timestamp while submitting another produces signatures the
    server always rejects."""
    module, _worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    page = module._APPROVAL_PAGE

    import re
    decide = re.search(
        r"const decide = async \(decision\) => \{(.*?)\n  \};", page, re.S)
    assert decide is not None, "decide handler missing from approval page"
    body = decide.group(1)
    # Exactly one timestamp sample inside the decision flow.
    assert body.count("ts()") == 1
    assert "const stamp = ts();" in body
    # The stamp is part of the signed message...
    sign_parts = re.search(r"signWith\(record, \[(.*?)\]\)", body, re.S)
    assert sign_parts is not None
    assert "stamp" in sign_parts.group(1)
    # ...and the identical variable is submitted, not a fresh sample.
    assert re.search(r"ts: stamp,", body) is not None

    # Same invariant in the pending-list flow.
    pending = re.search(r"async function pollOnce\(record\) \{(.*?)\n\}", page, re.S)
    assert pending is not None
    assert pending.group(1).count("ts()") == 1
    assert "ts: stamp" in pending.group(1)

    # Domain separators in the page must match the server verifier domains.
    for domain in ("nixon-remote-approval-v1", "nixon-remote-enrol-v1",
                   "nixon-remote-pending-v1"):
        assert domain in page


def test_approval_page_canonical_part_order_matches_server(tmp_path, monkeypatch):
    """Regression guard for browser/server canonicalization drift. Unit tests
    sign with the server's constructor order, so a reordered or restructured
    message in the page JavaScript would only surface with real browsers.
    Pin the exact construction here."""
    module, _worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    page = module._APPROVAL_PAGE

    import re
    # Approval decision: domain, customer, approval_id, request_hash,
    # decision, stamp — the exact order of _approval_message server-side.
    decide = re.search(
        r"const decide = async \(decision\) => \{(.*?)\n  \};", page, re.S).group(1)
    parts = re.search(r"signWith\(record, \[(.*?)\]\)", decide, re.S).group(1)
    order = [piece.strip() for piece in parts.split(",")]
    assert order == [
        '"nixon-remote-approval-v1"', "item.customer", "item.approval_id",
        "item.request_hash", "decision", "stamp"]

    # Pending list: domain, customer, keyId, stamp — _pending_message order.
    pending = re.search(
        r"async function pollOnce\(record\) \{(.*?)\n\}", page, re.S).group(1)
    parts = re.search(r"signWith\(record, \[(.*?)\]\)", pending, re.S).group(1)
    order = [piece.strip() for piece in parts.split(",")]
    assert order == [
        '"nixon-remote-pending-v1"', "record.customer", "record.keyId", "stamp"]

    # Enrolment: domain, customer, token — _enrol_proof_message order.
    enrol = re.search(
        r"async function enrolFromHash\(\) \{(.*?)\n\}", page, re.S).group(1)
    enc = re.search(r"enc\.encode\(\[(.*?)\]\.join", enrol, re.S)
    assert enc is not None
    order = [piece.strip() for piece in enc.group(1).split(",")]
    assert order == ['"nixon-remote-enrol-v1"', "customer", "token"]

    # All three flows must join with NUL separators, matching the server.
    # The page must carry the visible escape sequence, not a raw NUL byte:
    # the outer worker template is a raw string, so a single backslash in the
    # template would be converted to a raw control byte when the worker
    # parses its own page literal.
    assert 'join("\\x00")' in page
    assert "\x00" not in page
    for code in range(32):
        if code in (9, 10, 13):  # tab/newline/CR are ordinary whitespace
            continue
        assert chr(code) not in page, "raw control byte %d in page" % code
    assert '.join(" ")' not in page
