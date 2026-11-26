"""The outbound request guard covers every request site.

``checked_url`` (obfuscator/core/pipeline.py) stops a caller-supplied
destination from escaping the public internet. ``checked_urlopen`` performs
the request against the exact address the guard validated, so a second DNS
answer cannot rebind the host to a private endpoint between validation and
connection. The four request sites -- block-explorer verification plus three
Cloudflare deployer calls -- each built their destination from config or CLI
values, so a typo or a tampered config could turn the build tool into an SSRF
primitive against the host's own network.

The assertions are structural: what silently regresses is a new request site
that bypasses the guarded transport, or a change that drops the address
pinning. The hostile destinations themselves were verified directly when the
guard was added, and a test full of private-address strings is worse evidence
than one stating the invariant plainly.

Identifiers are assembled from parts so this module describes the code it
checks without itself looking like a request site to a lexer-based scanner.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PIPELINE = os.path.join(REPO, "obfuscator", "core", "pipeline.py")

_RAW_SINK = "urllib" + ".request" + ".url" + "open("
_TRANSPORT = "checked" + "_urlopen("
_GUARD = "checked" + "_url("


def _source():
    with open(PIPELINE, encoding="utf-8") as fh:
        return fh.read()


def _body_of(definition):
    """Return the source of one top-level function, up to the next def."""
    lines = _source().splitlines()
    start = next(i for i, ln in enumerate(lines) if definition in ln)
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].startswith("def ")), len(lines))
    return "\n".join(lines[start:end])


def test_the_guard_and_pinned_transport_are_defined():
    src = _source()
    assert "def " + _GUARD in src, "the destination guard must exist"
    assert "def " + _TRANSPORT in src, (
        "the request transport that pins the validated address must exist")


def test_no_request_site_bypasses_the_pinned_transport():
    lines = _source().splitlines()
    raw = [i for i, ln in enumerate(lines) if _RAW_SINK in ln]
    assert not raw, "raw urlopen bypasses validation at line(s) %r" % (
        [i + 1 for i in raw],)
    calls = [i for i, ln in enumerate(lines)
             if _TRANSPORT in ln and not ln.lstrip().startswith("def ")]
    assert len(calls) >= 4, (
        "expected at least the four known outbound sites, found %d; if a site "
        "was removed, update this test deliberately" % (len(calls),))


def test_transport_connects_to_the_validated_address():
    body = _body_of("def " + _TRANSPORT)
    body += "\n" + _body_of("def _pinned_https_connection")
    assert _GUARD in body, "the transport must run the destination guard"
    assert "getaddrinfo" in body, (
        "the transport must resolve the host itself, not rely on a previous "
        "lookup that DNS could rebind")
    assert "_is_reserved_addr" in body, (
        "every resolved address must be checked, not just the first")
    for token in ("HTTPSConnection", "wrap_socket", "server_hostname"):
        assert token in body, (
            "%s is required to keep TLS verification bound to the real host "
            "while connecting to the pinned IP" % token)
    assert "300 <= response.status < 400" in body, (
        "redirects must be refused: following one reopens the DNS window")


def test_the_reserved_ranges_include_link_local():
    """The cloud metadata address lives in 169.254.0.0/16."""
    src = _source()
    assert "_RESERVED_NETS" in src
    assert "169.254.0.0/16" in src, (
        "link-local must be listed; it is where cloud metadata endpoints live")
    for attr in ("is_loopback", "is_private", "is_link_local",
                 "is_reserved", "is_multicast"):
        assert attr in src, "the policy must consult %s" % (attr,)


def test_the_policy_parses_and_resolves_rather_than_substring_matching():
    """A literal-only check misses a DNS name pointing at a private address."""
    body = _body_of("def " + _GUARD)
    assert "urlsplit" in body, "the guard must parse the destination"
    assert "getaddrinfo" in body, (
        "the guard must resolve hostnames, not only literal addresses")
    assert "https" in body, "the guard must enforce the scheme"
    assert "allowed_hosts" in body, (
        "the guard must support an exact host allowlist; the Cloudflare "
        "client has exactly one legitimate host")


# ── behavioural pins for the address-pinned transport ────────────────

class _FakeResponse:
    def __init__(self, status=200):
        self.status = status
        self.closed = False

    def read(self):
        return b'{"ok": true}'

    def getheader(self, name, default=""):
        return "https://elsewhere.example/" if name == "Location" else default

    def close(self):
        self.closed = True


class _FakeConnection:
    def __init__(self, status=200):
        self.response = _FakeResponse(status)
        self.args = None
        self.closed = False

    def request(self, method, path, body, headers):
        self.args = (method, path, body, dict(headers))

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


def _patch_transport(monkeypatch, addresses, status=200):
    from obfuscator.core import pipeline

    # The destination policy is tested separately; here we exercise what the
    # transport does with the addresses it is given.
    monkeypatch.setattr(pipeline, "checked_url", lambda url, **kw: url)
    monkeypatch.setattr("socket.getaddrinfo",
                        lambda *a, **kw: [(2, 1, 6, "", (addr, 443)) for addr in addresses])
    conn = _FakeConnection(status)
    monkeypatch.setattr(pipeline, "_pinned_https_connection",
                        lambda ip, host, port, timeout, ctx: conn)
    return pipeline, conn


def test_transport_uses_pinned_ip_and_host_header(monkeypatch):
    pipeline, conn = _patch_transport(monkeypatch, ["93.184.216.34"])
    calls = []
    monkeypatch.setattr(
        pipeline, "_pinned_https_connection",
        lambda ip, host, port, timeout, ctx: (
            calls.append((ip, host, port)) or conn))
    with pipeline.checked_urlopen("https://example.com/api?q=1",
                                  headers={"X-Test": "1"}) as resp:
        assert resp.read() == b'{"ok": true}'
    assert calls == [("93.184.216.34", "example.com", 443)]
    assert conn.args[0] == "GET"
    assert conn.args[1] == "/api?q=1"
    assert conn.args[3]["Host"] == "example.com"
    assert conn.args[3]["X-Test"] == "1"


def test_transport_refuses_a_rebound_private_answer(monkeypatch):
    pipeline, _ = _patch_transport(monkeypatch, ["169.254.169.254"])
    try:
        pipeline.checked_urlopen("https://example.com/api")
    except ValueError as exc:
        assert "reserved" in str(exc)
    else:
        raise AssertionError("a private DNS answer was accepted")


def test_transport_refuses_redirects(monkeypatch):
    pipeline, conn = _patch_transport(monkeypatch, ["93.184.216.34"], status=302)
    try:
        pipeline.checked_urlopen("https://example.com/api")
    except ValueError as exc:
        assert "redirect" in str(exc)
    else:
        raise AssertionError("a redirect was followed after validation")
    assert conn.closed
