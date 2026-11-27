"""End-to-end chain gate verification against a local HTTPS mock RPC.

Proves the chain gate pipeline — TLS handshake → JSON-RPC eth_call →
ownerOf → owner comparison — works against a real HTTPS endpoint without
any gas, testnet, or real chain. Uses a self-signed cert trusted via the
SSL_CERT_FILE env var (urllib's default context reads it).

These tests verify `chain_owner_of` (the function the emitted loader
calls) against the mock, plus the alert relay wiring. Full-pipeline
integration is covered by the offline-max build test.
"""
import http.server
import json
import os
import ssl
import sys
import tempfile
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from obfuscator.core.sources import VARS
from obfuscator.licensing import chain_owner_of

_OWNER = "0x" + "ab" * 20
_CONTRACT = "0x" + "cd" * 20
_CHAIN_ID = 31337
_TOKEN_ID = 1


class _MockRPCHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n))
        method = req.get("method", "")
        if method == "eth_chainId":
            result = hex(_CHAIN_ID)
        elif method == "eth_call":
            data = req["params"][0].get("data", "")
            if data.startswith("0x6352211e"):  # ownerOf(uint256)
                owner = getattr(self.server, "mock_owner", _OWNER)
                result = "0x" + "0" * 24 + owner[2:].rjust(40, "0")
            else:
                result = "0x" + "0" * 64
        else:
            result = "0x" + "0" * 64
        resp = json.dumps({"jsonrpc": "2.0", "id": req.get("id", 1),
                           "result": result}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp)))
        self.end_headers()
        self.wfile.write(resp)

    def log_message(self, *a): pass


@pytest.fixture(scope="module")
def mock_rpc():
    """Self-signed HTTPS mock JSON-RPC server; yields (rpc_url, server)."""
    work = tempfile.mkdtemp()
    cert = os.path.join(work, "cert.pem")
    key = os.path.join(work, "key.pem")
    import subprocess
    r = subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048",
                        "-keyout", key, "-out", cert, "-days", "1",
                        "-nodes", "-subj", "/CN=localhost"],
                       capture_output=True)
    assert r.returncode == 0, r.stderr.decode()

    srv = http.server.HTTPServer(("127.0.0.1", 0), _MockRPCHandler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(cert, key)
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()

    old_cert = os.environ.get("SSL_CERT_FILE")
    os.environ["SSL_CERT_FILE"] = cert
    yield f"https://localhost:{port}", srv
    srv.shutdown()
    if old_cert is not None:
        os.environ["SSL_CERT_FILE"] = old_cert
    else:
        os.environ.pop("SSL_CERT_FILE", None)


def test_chain_owner_of_returns_correct_owner(mock_rpc):
    rpc_url, _srv = mock_rpc
    owner = chain_owner_of(rpc_url, _CONTRACT, _TOKEN_ID, _CHAIN_ID)
    assert owner == _OWNER


def test_chain_owner_of_detects_wrong_owner(mock_rpc):
    rpc_url, srv = mock_rpc
    srv.mock_owner = "0x" + "ee" * 20
    owner = chain_owner_of(rpc_url, _CONTRACT, _TOKEN_ID, _CHAIN_ID)
    assert owner != _OWNER
    srv.mock_owner = _OWNER  # restore


def test_chain_owner_of_enforces_https():
    with pytest.raises(ValueError, match="HTTPS"):
        chain_owner_of("http://localhost:8545", _CONTRACT, _TOKEN_ID)


def test_chain_owner_of_validates_contract_address():
    with pytest.raises(ValueError, match="20-byte"):
        chain_owner_of("https://localhost:8545", "not-an-address", 1)


def test_kill_ladder_reports_to_alert_before_wipe(tmp_path):
    """_nx_kill wipes keys and _exit(137)s — the alert must fire BEFORE
    that, in a child process (os._exit cannot be caught in-process)."""
    import subprocess
    import obfuscator.kill_ladder as kl
    alert_name = VARS["FUNC_TRIGGER_ALERT"]
    snippet = kl.emit_kill_snippet(alert_fn=alert_name)
    compile(snippet, "<kill>", "exec")
    evidence = tmp_path / "kill_evidence.txt"
    child = (
        "import os\n"
        "def " + alert_name + "(reason):\n"
        "    open(" + repr(str(evidence)) + ", 'w').write(reason)\n"
        + snippet +
        "\nBLOB_KEY = bytearray(b'SECRET' * 100)\n"
        "_nx_kill('trial-expired', [BLOB_KEY])\n"
    )
    p = subprocess.run([sys.executable, "-c", child],
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 137, (p.returncode, p.stderr[-300:])
    # The relay prefixes the reason with "kill:" for the server.
    assert evidence.read_text() == "kill:trial-expired"


def test_kill_snippet_without_alert_name_still_kills():
    import subprocess
    import obfuscator.kill_ladder as kl
    snippet = kl.emit_kill_snippet()
    compile(snippet, "<kill>", "exec")
    child = snippet + "\nimport os\nBLOB_KEY = bytearray(b'SECRET' * 100)\n" \
        "_nx_kill('trial-expired', [BLOB_KEY])\n"
    p = subprocess.run([sys.executable, "-c", child],
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 137


def test_strict_fail_reports_to_alert(monkeypatch):
    """The emitted _nx_strict_fail alerts BEFORE os._exit(137)."""
    s = open("obfuscator/core/sources.py").read()
    i = s.find("def _nx_strict_fail(reason):")
    j = s.find("def _nx_self_fail(reason):", i)
    strict_src = s[i:j]
    for k, v in VARS.items():
        if isinstance(v, bytes):
            v = v.decode("latin-1")
        strict_src = strict_src.replace("{%s}" % k, str(v))

    fired = []
    relay = VARS["FUNC_TRIGGER_ALERT"]

    class FakeOs:
        @staticmethod
        def _exit(code):
            fired.append(("exit", code))

    ns = {"__name__": "t", "_NX_STRICT_DETECTIONS": True,
          relay: lambda reason: fired.append(("relay", reason)),
          "_nx_st_os": FakeOs}
    exec(compile(strict_src, "<sf>", "exec"), ns)
    ns["_nx_strict_fail"]("geo-block")
    assert ("relay", "strict:geo-block") in fired
    assert ("exit", 137) in fired
    assert fired.index(("relay", "strict:geo-block")) < fired.index(("exit", 137))
