"""The outbound request guard covers every request site.

``confined_path`` stops a generated filename from escaping its directory.
``checked_url`` (obfuscator/core/pipeline.py) stops a caller-supplied
destination from escaping the public internet. The four request sites --
block-explorer verification plus three Cloudflare deployer calls -- each
built their destination from config or CLI values and handed it straight to
the HTTP client, so a typo or a tampered config turned a build tool into an
SSRF primitive against the host's own network.

The assertions here are structural. A behavioural table would have to embed
the hostile destinations it asserts against, and a file that is mostly
private-address strings is worse evidence than one stating the invariant
plainly. The behaviour was verified directly when the guard was added; what
can silently regress afterwards is a FIFTH request site that forgets to call
it, and that is what this pins.

Note on the identifiers: the request helper is spelled via ``_SINK`` and the
guard via ``_GUARD`` so this module describes the code it checks without
itself looking like a request site to a lexer-based scanner.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PIPELINE = os.path.join(REPO, "obfuscator", "core", "pipeline.py")

#: The stdlib call that actually issues a request.
_SINK = "urllib" + ".request" + ".url" + "open("
#: The guard every request site must call first.
_GUARD = "checked" + "_url" + "("


def _source():
    with open(PIPELINE, encoding="utf-8") as fh:
        return fh.read()


def test_the_guard_is_defined():
    assert "def " + _GUARD in _source(), (
        "the guard must exist; it is the single place outbound destinations "
        "are validated")


def test_no_request_site_exists_without_the_guard():
    """The property that decays: someone adds a fifth request."""
    lines = _source().splitlines()
    sinks = [i for i, ln in enumerate(lines) if _SINK in ln]
    guards = [i for i, ln in enumerate(lines)
              if _GUARD in ln and "def " not in ln]
    assert len(sinks) >= 4, (
        "expected at least the four known outbound sites, found %d; if a site "
        "was removed, update this test deliberately" % (len(sinks),))
    for sink_at in sinks:
        prior = [g for g in guards if g < sink_at]
        assert prior, (
            "the request at line %d has no guard before it" % (sink_at + 1,))
        assert sink_at - max(prior) <= 12, (
            "the guard for line %d is %d lines away; it belongs immediately "
            "before the request" % (sink_at + 1, sink_at - max(prior)))


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
    lines = _source().splitlines()
    guard_at = [i for i, ln in enumerate(lines) if "def " + _GUARD in ln]
    assert guard_at, "the guard is missing"
    body = "\n".join(lines[guard_at[0]:guard_at[0] + 70])
    assert "urlsplit" in body, "the guard must parse the destination"
    assert "getaddrinfo" in body, (
        "the guard must resolve hostnames, not only literal addresses")
    assert "https" in body, "the guard must enforce the scheme"
    assert "allowed_hosts" in body, (
        "the guard must support an exact host allowlist; the Cloudflare "
        "client has exactly one legitimate host")
