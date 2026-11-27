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
    """Behavioral SQL double for the generated security-registry statements."""

    def __init__(self):
        self.rows = {}
        self.usage = {}
        self.statements = []

    def exec(self, query, *bindings):
        compact = " ".join(query.split()).upper()
        self.statements.append((compact, bindings))
        if compact.startswith("CREATE TABLE"):
            return _Cursor([])
        if compact.startswith("DELETE FROM NONCES"):
            now = bindings[0]
            for nonce, expires in list(self.rows.items()):
                if expires < now:
                    del self.rows[nonce]
            return _Cursor([])
        if compact.startswith("DELETE FROM USAGE_WINDOWS"):
            now = bindings[0]
            for key, (_expires, _hits) in list(self.usage.items()):
                if _expires < now:
                    del self.usage[key]
            return _Cursor([])
        if compact.startswith("SELECT NONCE FROM NONCES"):
            nonce = bindings[0]
            return _Cursor([{"nonce": nonce}] if nonce in self.rows else [])
        if compact.startswith("SELECT HITS FROM USAGE_WINDOWS"):
            key = bindings[0]
            if key not in self.usage:
                return _Cursor([])
            return _Cursor([{"hits": self.usage[key][1]}])
        if compact.startswith("INSERT INTO NONCES"):
            nonce, expires = bindings
            self.rows[nonce] = expires
            return _Cursor([])
        if compact.startswith("INSERT INTO USAGE_WINDOWS"):
            key, expires = bindings
            if key in self.usage:
                _old_expires, hits = self.usage[key]
                self.usage[key] = (expires, hits + 1)
            else:
                self.usage[key] = (expires, 1)
            return _Cursor([])
        if compact.startswith("UPDATE USAGE_WINDOWS SET HITS = HITS - 1"):
            key = bindings[0]
            if key in self.usage and self.usage[key][1] > 0:
                expires, hits = self.usage[key]
                self.usage[key] = (expires, hits - 1)
            return _Cursor([])
        raise AssertionError("unexpected SQL: %s" % compact)


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
    assert "FIDO2/passkey" in deployment
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
    assert doc["nonce"] in sql.rows


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
