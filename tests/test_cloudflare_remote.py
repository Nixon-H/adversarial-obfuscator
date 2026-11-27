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
    cloudflare_worker_source, write_cloudflare_worker,
)
from obfuscator.remote_exec import split_module, sign_request  # noqa: E402
from obfuscator.totp import new_base32_secret, totp_code  # noqa: E402

SECRET_HEX = "22" * 32
SECRET = bytes.fromhex(SECRET_HEX)

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
    """Tiny behavioral SQL double for the generated nonce statements."""

    def __init__(self):
        self.rows = {}
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
        if compact.startswith("SELECT NONCE FROM NONCES"):
            nonce = bindings[0]
            return _Cursor([{"nonce": nonce}] if nonce in self.rows else [])
        if compact.startswith("INSERT INTO NONCES"):
            nonce, expires = bindings
            self.rows[nonce] = expires
            return _Cursor([])
        raise AssertionError("unexpected SQL: %s" % compact)


class _FakeReplayNamespace:
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
    write_cloudflare_worker(functions, str(target), worker_name="test-remote")

    workers = types.ModuleType("workers")
    workers.DurableObject = _FakeDurableObject
    workers.Response = _FakeResponse
    workers.WorkerEntrypoint = _FakeWorkerEntrypoint
    monkeypatch.setitem(sys.modules, "workers", workers)

    monkeypatch.syspath_prepend(str(target / "src"))
    entry = target / "src" / "entry.py"
    spec = importlib.util.spec_from_file_location("generated_cf_worker", str(entry))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    sql = _FakeSQL()
    ctx = types.SimpleNamespace(storage=types.SimpleNamespace(sql=sql))
    registry = module.ReplayRegistry(ctx, None)
    env = types.SimpleNamespace(
        NIXON_REMOTE_SECRET=SECRET_HEX,
        NIXON_REMOTE_TOTP_SECRET=new_base32_secret(),
        NIXON_REMOTE_TOTP2_SECRET=new_base32_secret(),
        REPLAY=_FakeReplayNamespace(registry),
    )
    while env.NIXON_REMOTE_TOTP2_SECRET == env.NIXON_REMOTE_TOTP_SECRET:
        env.NIXON_REMOTE_TOTP2_SECRET = new_base32_secret()
    worker = module.Default()
    worker.env = env
    return module, worker, sql, target


def _valid_payload(env, *, function="hidden_pricing", args=None,
                   kwargs=None, nonce="nonce-1"):
    args = [7] if args is None else args
    kwargs = {"scale": 3} if kwargs is None else kwargs
    now = time.time()
    doc = {
        "version": 1,
        "function": function,
        "args": args,
        "kwargs": kwargs,
        "nonce": nonce,
        "timestamp": now,
        "signature": sign_request(
            SECRET, function, args, nonce, now, kwargs),
        "totp": totp_code(env.NIXON_REMOTE_TOTP_SECRET, at=now),
        "totp_secondary": totp_code(env.NIXON_REMOTE_TOTP2_SECRET, at=now),
    }
    return doc


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
    assert "coefficient = 991" not in entry
    assert "coefficient = 991" in implementation
    assert "class ReplayRegistry" in entry
    assert "NIXON_REMOTE_TOTP_SECRET" in entry
    assert "NIXON_REMOTE_TOTP2_SECRET" in entry
    assert stat.S_IMODE((target / "src" / "entry.py").stat().st_mode) & 0o077 == 0
    assert stat.S_IMODE((target / "src" / "remote_impl.py").stat().st_mode) & 0o077 == 0
    assert stat.S_IMODE(target.stat().st_mode) & 0o077 == 0
    config = json.loads((target / "wrangler.jsonc").read_text())
    assert config["compatibility_flags"] == ["python_workers"]
    assert config["durable_objects"]["bindings"][0]["name"] == "REPLAY"


def test_worker_generation_refuses_to_replace_existing_path(tmp_path):
    _client, functions = split_module(SOURCE)
    target = tmp_path / "worker"
    target.mkdir()
    with pytest.raises(FileExistsError):
        write_cloudflare_worker(functions, str(target))


def test_generated_worker_signing_matches_protocol_vectors(tmp_path, monkeypatch):
    module, _worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    args = [1, -0.0, "é", True, None, {"b": 2, "a": 1.5}]
    kwargs = {"rate": 0.5, "label": "x"}
    vector_secret = bytes.fromhex("11" * 32)
    assert module._sign(vector_secret, "f", args, kwargs, "nonce", 1000.0) == (
        "b2adc43bf63eb2bfeb87e9b5b509f636b2de11ea36189d23893c7a1be44c030f")
    assert module._sign(SECRET, "f", [1], {}, "n", 1.0) != module._sign(
        SECRET, "f", [1.0], {}, "n", 1.0)


def test_generated_worker_totp_matches_reference_implementation(tmp_path, monkeypatch):
    module, _worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    secret = new_base32_secret()
    for when in (0, 29, 30, 59, 1200, 1700000000):
        assert module._totp(secret, when) == totp_code(secret, at=when)


def test_generated_worker_executes_after_hmac_dual_totp_and_replay(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    out = _fetch(worker, _valid_payload(worker.env))
    assert out == {"result": 1012}  # 991 + 7 * 3


def test_generated_worker_rejects_bad_hmac_before_execution(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    doc = _valid_payload(worker.env)
    doc["args"] = [8]
    out = _fetch(worker, doc)
    assert "signature mismatch" in out["error"]


def test_generated_worker_requires_both_totp_factors(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    doc = _valid_payload(worker.env)
    del doc["totp"]
    assert "authentication failed" in _fetch(worker, doc)["error"]

    doc = _valid_payload(worker.env, nonce="nonce-2")
    doc["totp_secondary"] = "000000"
    if doc["totp_secondary"] == totp_code(
            worker.env.NIXON_REMOTE_TOTP2_SECRET, at=doc["timestamp"]):
        doc["totp_secondary"] = "999999"
    assert "authentication failed" in _fetch(worker, doc)["error"]


def test_generated_worker_rejects_identical_totp_seed_configuration(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    worker.env.NIXON_REMOTE_TOTP2_SECRET = worker.env.NIXON_REMOTE_TOTP_SECRET
    out = _fetch(worker, _valid_payload(worker.env))
    assert "not independent" in out["error"]


def test_generated_worker_rejects_replayed_nonce(tmp_path, monkeypatch):
    _module, worker, sql, _target = _load_worker(tmp_path, monkeypatch)
    doc = _valid_payload(worker.env)
    assert _fetch(worker, doc) == {"result": 1012}
    replayed = _fetch(worker, doc)
    assert "replayed" in replayed["error"]
    assert doc["nonce"] in sql.rows


def test_replay_registry_sql_behavior_expires_old_nonces(tmp_path, monkeypatch):
    module, _worker, sql, _target = _load_worker(tmp_path, monkeypatch)
    ctx = types.SimpleNamespace(storage=types.SimpleNamespace(sql=sql))
    registry = module.ReplayRegistry(ctx, None)
    assert asyncio.run(registry.check_and_store("n", 1000.0)) is True
    assert asyncio.run(registry.check_and_store("n", 1001.0)) is False
    assert asyncio.run(registry.check_and_store("n", 1701.0)) is True


def test_generated_worker_requires_replay_binding(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    worker.env.REPLAY = None
    out = _fetch(worker, _valid_payload(worker.env))
    assert "replay protection" in out["error"]


def test_generated_worker_rejects_missing_or_malformed_requests(tmp_path, monkeypatch):
    _module, worker, _sql, _target = _load_worker(tmp_path, monkeypatch)
    assert "unsupported" in _fetch(worker, {"version": 2})["error"]
    doc = _valid_payload(worker.env)
    doc["kwargs"] = []
    assert "args must be" in _fetch(worker, doc)["error"]
    doc = _valid_payload(worker.env)
    doc["timestamp"] = time.time() + 9999
    assert "expired" in _fetch(worker, doc)["error"]


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
