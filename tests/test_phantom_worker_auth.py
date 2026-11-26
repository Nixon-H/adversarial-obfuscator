"""The Cloudflare worker must never downgrade AES-GCM failures to XOR."""
import subprocess

from obfuscator.core.pipeline import PHANTOM_NODE_JS


def test_gcm_authentication_failure_cannot_use_fallback(tmp_path):
    try:
        node_missing = subprocess.run(
            ["node", "--version"], capture_output=True).returncode != 0
    except FileNotFoundError:
        node_missing = True
    if node_missing:
        import pytest
        pytest.skip("node is not installed")
    worker = tmp_path / "worker.mjs"
    worker.write_text(PHANTOM_NODE_JS, encoding="utf-8")
    probe = tmp_path / "probe.mjs"
    probe.write_text(r'''
import { webcrypto } from "node:crypto";
if (!globalThis.crypto || !globalThis.crypto.subtle || !globalThis.crypto.getRandomValues) {
  Object.defineProperty(globalThis, "crypto", {
    value: webcrypto, configurable: true, writable: true,
  });
}
const { default: worker } = await import("./worker.mjs");
const enc = new TextEncoder();
const N = 509;
const plain = enc.encode(JSON.stringify({hw: "probe"}));
const ntru = new Uint8Array(2 + N * 2 + 12 + plain.length);
ntru[0] = (N * 2) >> 8;
ntru[1] = (N * 2) & 255;
const iv = ntru.subarray(2 + N * 2, 2 + N * 2 + 12);
for (let i = 0; i < iv.length; i++) iv[i] = i;
const sessionToken = new Uint8Array(32);
const seedInput = new Uint8Array(sessionToken.length + iv.length);
seedInput.set(sessionToken);
seedInput.set(iv, sessionToken.length);
let k_h = new Uint8Array(await crypto.subtle.digest("SHA-256", seedInput));
const payload = new Uint8Array(plain.length);
for (let i = 0; i < plain.length; i++) {
  if (i > 0 && i % 32 === 0) {
    const rekeyInput = new Uint8Array(k_h.length + i.toString().length);
    rekeyInput.set(k_h);
    rekeyInput.set(enc.encode(i.toString()), k_h.length);
    k_h = new Uint8Array(await crypto.subtle.digest("SHA-256", rekeyInput));
  }
  payload[i] = plain[i] ^ k_h[i % 32];
}
ntru.set(payload, 2 + N * 2 + 12);
const env = {
  NTRU_PRIV: JSON.stringify(new Array(N).fill(0)),
  LICENSES: {get: async () => "FINALKEY"},
};
const response = await worker.fetch(new Request("https://worker.test", {
  method: "POST", body: ntru,
}), env);
console.log(response.status);
if (response.status !== 403) process.exit(1);
''', encoding="utf-8")
    result = subprocess.run(["node", str(probe)], cwd=tmp_path,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert result.stdout.strip() == "403", (result.stdout, result.stderr)


def test_cloudflare_worker_bindings_use_secret_text(monkeypatch):
    """Private worker key material must not be deployed as visible plain_text."""
    import json
    import re
    import obfuscator.core.pipeline as pipeline

    captured = {}

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"{}"

    def fake_checked_urlopen(*args, **kwargs):
        captured["data"] = kwargs.get("data", b"")
        return DummyResponse()

    deployer = pipeline.CloudflareDeployer("token", "account")
    deployer.get_kv_id = lambda: "kv-id"
    deployer._req = lambda method, endpoint, data=None: {
        "result": {"subdomain": "example"}, "success": True}
    monkeypatch.setattr(pipeline, "checked_urlopen", fake_checked_urlopen)

    url = deployer.deploy_master("x" * 64, ntru_priv=[1, -1, 0])
    assert url == "https://nixon-master-node.example.workers.dev"
    match = re.search(rb'\r\n\r\n(\{.*?\})\r\n--', captured["data"], re.S)
    assert match, "multipart metadata not found in worker upload"
    metadata = json.loads(match.group(1).decode("utf-8"))
    bindings = {item["name"]: item for item in metadata["bindings"]}
    assert bindings["SECRET_KEY"]["type"] == "secret_text"
    assert bindings["NTRU_PRIV"]["type"] == "secret_text"
    assert all(item["type"] != "plain_text"
               for item in bindings.values() if item["name"] != "LICENSES")


def test_cloud_licence_private_key_generation_is_not_seed_reduced():
    """The cloud licence key sampler must not collapse to a 32-bit seed."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source = open(os.path.join(root, "obfuscator", "core", "pipeline.py"),
                  encoding="utf-8").read()
    start = source.find("ntru_priv_key = None")
    end = source.find("if auto_cf:", start)
    assert start >= 0 and end > start
    block = source[start:end]
    assert "secrets.SystemRandom()" in block
    assert "secrets.randbits(32)" not in block
    assert "random.Random(s_s)" not in block


def test_local_master_key_write_is_atomic_private_and_symlink_safe(tmp_path):
    import os
    import stat
    from obfuscator.core.pipeline import _write_private_key_file

    victim = tmp_path / "victim"
    victim.write_text("keep", encoding="utf-8")
    target = tmp_path / ".nixon_key_test"
    target.symlink_to(victim)
    _write_private_key_file(str(target), "test-secret")
    assert victim.read_text(encoding="utf-8") == "keep"
    assert not target.is_symlink()
    assert target.read_text(encoding="utf-8") == "test-secret"
    mode = stat.S_IMODE(os.stat(str(target)).st_mode)
    assert mode & 0o077 == 0, oct(mode)
