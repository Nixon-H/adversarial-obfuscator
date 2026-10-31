"""The emitted key fetch must verify the certificate chain AND the hostname.

Audit finding: the emitted loader built its TLS context with
``ssl._create_unverified_context()``, which accepts any certificate.  On
the key-exchange path the response *is* the session key, so a network
attacker could substitute their own key.

The loader now builds a verified context: the system trust store plus an
optional operator-owned CA embedded at build time (``--tls-ca-bundle``).
Embedding a CA ADDS trust for that endpoint; it never disables
verification.

These tests build the context the same way the builder does (apply_vars ->
brace unescape -> format), then exercise it against a real local TLS
server with a real certificate.
"""
import base64
import datetime
import http.server
import ipaddress
import os
import socket
import ssl
import sys
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.sources import TLS_CTX_SOURCE, apply_vars


# ---------------------------------------------------------------------------
# Certificate fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolate_vars():
    """Snapshot and restore the module-level VARS dict around every test here.

    `apply_vars` reads `obfuscator.core.sources.VARS`, and `pipeline.py` writes
    `VARS["FORCE_NATIVE_EXEC"]` in both branches of its native-compilation setup
    with no restore. Any earlier test that runs the pipeline therefore changes the
    values this file substitutes into TLS_CTX_SOURCE, which is why these tests
    pass alone and failed in a full run (round 231, diagnosed in round 232).

    Restoring here is the local half of the fix. The real fix is for pipeline.py
    to restore what it sets, which needs a round that can run the native-build
    tests.
    """
    from obfuscator.core import sources as _src
    saved = dict(_src.VARS)
    try:
        yield
    finally:
        _src.VARS.clear()
        _src.VARS.update(saved)


def _vars_snapshot():
    """Diagnostic: record what apply_vars would see (round 239)."""
    from obfuscator.core import sources as _src
    return dict(_src.VARS)


def test_vars_snapshot_is_stable():
    """If VARS changes between two reads with no build in between, something leaked."""
    first = _vars_snapshot()
    second = _vars_snapshot()
    assert first == second, (
        "VARS mutated between two reads with no intervening build: %r -> %r"
        % (first, second))


def _make_ca():
    """Create a test CA; returns (ca_cert_pem_bytes, ca_cert, ca_key)."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "nixon-test-ca")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None),
                       critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False,
                key_encipherment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=True, crl_sign=True,
                encipher_only=False, decipher_only=False),
            critical=True)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
            critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(
                key.public_key()), critical=False)
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM), cert, key


def _make_leaf(ca_cert, ca_key, tmpdir, names):
    """Create a server cert signed by the CA with the given SANs."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.datetime.now(datetime.timezone.utc)
    san = []
    for n in names:
        try:
            san.append(x509.IPAddress(ipaddress.ip_address(n)))
        except ValueError:
            san.append(x509.DNSName(n))
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, names[0])]))
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
            critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(
                ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    cert_path = os.path.join(str(tmpdir), "server.crt")
    key_path = os.path.join(str(tmpdir), "server.key")
    with open(cert_path, "wb") as fh:
        fh.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(key_path, "wb") as fh:
        fh.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()))
    return cert_path, key_path


# ---------------------------------------------------------------------------
# A local TLS server
# ---------------------------------------------------------------------------

class _QuietHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


class _QuietServer(http.server.ThreadingHTTPServer):
    """A server that stays quiet when the client rejects the handshake.

    The negative tests deliberately fail verification; the server side
    would otherwise print a traceback for each rejected handshake.
    """

    def handle_error(self, request, client_address):
        pass


def _start_server(cert_path, key_path):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_path, key_path)
    httpd = _QuietServer(("127.0.0.1", 0), _QuietHandler)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    host, port = httpd.socket.getsockname()[:2]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, host, port


@pytest.fixture
def tls_server(tmp_path):
    """Start a local HTTPS server; yields (host, port, ca_pem)."""
    ca_pem, ca_cert, ca_key = _make_ca()
    cert_path, key_path = _make_leaf(ca_cert, ca_key, tmp_path,
                                     ["127.0.0.1", "localhost"])
    httpd, host, port = _start_server(cert_path, key_path)
    try:
        yield host, port, ca_pem
    finally:
        httpd.shutdown()
        httpd.server_close()


# ---------------------------------------------------------------------------
# The context under test
# ---------------------------------------------------------------------------

def _build_context(ca_pem=b""):
    """Render the emitted TLS context exactly like the builder does.

    The decoder name is randomised per import, so the function is
    located structurally (the snippet defines exactly one) instead of by
    name — a test must not depend on a name another module may have
    regenerated.
    """
    src = apply_vars(TLS_CTX_SOURCE).replace("{{", "{").replace("}}", "}")
    literal = repr(base64.b64encode(ca_pem).decode("ascii")) if ca_pem else "''"
    src = src.format(tls_ca_b64=literal)
    namespace = {}
    exec(compile(src, "<tls_ctx>", "exec"), namespace)
    defined = [v for v in namespace.values()
               if callable(v)
               and getattr(v, "__module__", "") != "builtins"]
    if len(defined) != 1:
        raise AssertionError(
            "expected exactly one emitted function, found %d" % (len(defined),))
    return defined[0]()


def _connect(host, port, context):
    """Attempt one TLS handshake; returns the negotiated peer cert or raises."""
    with socket.create_connection((host, port), timeout=10) as sock:
        with context.wrap_socket(sock, server_hostname=host) as tls:
            return tls.getpeercert()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_emitted_snippet_never_disables_verification():
    src = apply_vars(TLS_CTX_SOURCE)
    assert "_create_unverified_context" not in src
    assert "create_default_context" in src
    assert "CERT_REQUIRED" in src
    assert "check_hostname" in src


def test_context_verifies_and_checks_hostname():
    ctx = _build_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_untrusted_certificate_is_rejected(tls_server):
    host, port, ca_pem = tls_server
    ctx = _build_context()  # no CA embedded -> system trust store only
    with pytest.raises(ssl.SSLError):
        _connect(host, port, ctx)


def test_embedded_ca_certificate_is_accepted(tls_server):
    host, port, ca_pem = tls_server
    ctx = _build_context(ca_pem)
    peer = _connect(host, port, ctx)
    assert peer, "handshake produced no peer certificate"


def test_embedded_context_fetches_over_https(tls_server):
    """The intended key-fetch path: an HTTPS request through the context."""
    import urllib.request

    host, port, ca_pem = tls_server
    ctx = _build_context(ca_pem)
    url = "https://%s:%d/" % (host, port)
    with urllib.request.urlopen(url, timeout=10, context=ctx) as resp:
        assert resp.read() == b"ok"


def test_hostname_mismatch_is_rejected(tmp_path):
    # A CA-signed certificate for a DIFFERENT host must still be refused:
    # the bundle adds trust, it does not disable the hostname check.
    ca_pem, ca_cert, ca_key = _make_ca()
    cert_path, key_path = _make_leaf(ca_cert, ca_key, tmp_path,
                                     ["wrong.example.com"])
    httpd, host, port = _start_server(cert_path, key_path)
    try:
        client_ctx = _build_context(ca_pem)
        with pytest.raises(ssl.SSLError):
            _connect(host, port, client_ctx)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_loader_body_uses_the_verified_context():
    """The key-fetch loader must call the verified context, both sites."""
    from obfuscator.core.sources import LOADER_BODY, LOADER_HEAD
    assert "_create_unverified_context" not in LOADER_BODY
    assert "_create_unverified_context" not in LOADER_HEAD
    # The context helper is emitted with the loader head, ahead of its use.
    assert "{tls_ca_source}" in LOADER_HEAD
    # One call for the auth probe, one for the NTRU key exchange.
    assert LOADER_BODY.count("{FUNC_TLS_CTX}()") == 2


def test_ca_bundle_helper_roundtrip(tmp_path):
    """The build-side helper embeds the PEM as a Python literal."""
    from obfuscator.core.pipeline import load_tls_ca_bundle

    assert load_tls_ca_bundle(None) == "''"
    assert load_tls_ca_bundle("") == "''"
    ca_pem, _, _ = _make_ca()
    path = os.path.join(str(tmp_path), "ca.pem")
    with open(path, "wb") as fh:
        fh.write(ca_pem)
    literal = load_tls_ca_bundle(path)
    assert literal.startswith("'") and literal.endswith("'")
    assert base64.b64decode(literal[1:-1]) == ca_pem
    # An unreadable or empty bundle must fail the build, not ship silently.
    with pytest.raises(ValueError):
        load_tls_ca_bundle(os.path.join(str(tmp_path), "missing.pem"))
    empty = os.path.join(str(tmp_path), "empty.pem")
    with open(empty, "wb") as fh:
        fh.write(b"   \n")
    with pytest.raises(ValueError):
        load_tls_ca_bundle(empty)
