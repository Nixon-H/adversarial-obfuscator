"""Offline licence tokens: sign, verify, and every way one must be refused.

The point of the asymmetric token is that a customer who extracts the
public key can *check* a licence but cannot *mint* one. Most of these
tests are about the refusal paths, because a licence check that accepts
anything is worse than no check.
"""
import json
import os
import subprocess
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator import licensing as lic  # noqa: E402


def _keypair():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    private = Ed25519PrivateKey.generate()
    return private, private.public_key()


def _licence(**kw):
    now = time.time()
    base = dict(
        licence_id="L-1",
        customer="acme",
        issued_at=now,
        expires_at=now + 86400,
        features=("pro",),
    )
    base.update(kw)
    return lic.Licence(**base)


class TestRoundTrip:
    def test_issue_then_verify(self):
        private, public = _keypair()
        token = lic.issue(_licence(), private)
        got = lic.verify(token, public)
        assert got.licence_id == "L-1"
        assert got.customer == "acme"
        assert got.features == ("pro",)

    def test_signature_is_deterministic(self):
        """Ed25519 is deterministic (RFC 8032) — same input, same token."""
        private, _ = _keypair()
        assert lic.issue(_licence(), private) == lic.issue(_licence(), private)

    def test_canonical_is_key_order_independent(self):
        a = lic.canonical({"b": 2, "a": 1})
        b = lic.canonical({"a": 1, "b": 2})
        assert a == b


class TestRefusals:
    def test_a_tampered_payload_is_refused(self):
        private, public = _keypair()
        token = json.loads(lic.issue(_licence(), private))
        token["payload"]["customer"] = "someone-else"
        with pytest.raises(lic.LicenceError, match="signature"):
            lic.verify(json.dumps(token), public)

    def test_another_issuer_is_refused(self):
        private, _ = _keypair()
        _, other_public = _keypair()
        with pytest.raises(lic.LicenceError, match="signature"):
            lic.verify(lic.issue(_licence(), private), other_public)

    def test_expired_is_refused(self):
        private, public = _keypair()
        old = _licence(issued_at=time.time() - 10 * 86400,
                       expires_at=time.time() - 86400)
        with pytest.raises(lic.LicenceError, match="expired"):
            lic.verify(lic.issue(old, private), public)

    def test_not_yet_valid_is_refused(self):
        private, public = _keypair()
        future = _licence(issued_at=time.time() + 86400,
                          expires_at=time.time() + 2 * 86400)
        with pytest.raises(lic.LicenceError, match="not valid yet"):
            lic.verify(lic.issue(future, private), public)

    def test_hwid_mismatch_is_refused(self):
        private, public = _keypair()
        token = lic.issue(_licence(hwid="machine-a"), private)
        with pytest.raises(lic.LicenceError, match="different machine"):
            lic.verify(token, public, hwid="machine-b")

    def test_hwid_match_is_accepted(self):
        private, public = _keypair()
        token = lic.issue(_licence(hwid="machine-a"), private)
        assert lic.verify(token, public, hwid="machine-a").hwid == "machine-a"

    def test_missing_feature_is_refused(self):
        private, public = _keypair()
        token = lic.issue(_licence(features=("basic",)), private)
        with pytest.raises(lic.LicenceError, match="does not grant"):
            lic.verify(token, public, required_features=("pro",))

    def test_wrong_schema_is_refused(self):
        private, public = _keypair()
        doc = json.loads(lic.issue(_licence(), private))
        doc["payload"]["schema"] = "something-else/9"
        with pytest.raises(lic.LicenceError, match="schema"):
            lic.verify(json.dumps(doc), public)

    def test_junk_is_refused(self):
        _, public = _keypair()
        with pytest.raises(lic.LicenceError, match="not a licence token"):
            lic.verify("not json", public)

    def test_truncated_signature_is_refused(self):
        private, public = _keypair()
        doc = json.loads(lic.issue(_licence(), private))
        doc["sig"] = doc["sig"][:-4]
        with pytest.raises(lic.LicenceError):
            lic.verify(json.dumps(doc), public)


class TestCli:
    def _run(self, *args, env=None):
        merged = dict(os.environ)
        merged.update(env or {})
        return subprocess.run(
            [sys.executable, "-m", "obfuscator.licensing", *args],
            capture_output=True, text=True, timeout=60,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
            env=merged,
        )

    def test_issue_then_verify(self, tmp_path):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        private = Ed25519PrivateKey.generate()
        seed = private.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        ).hex()
        pub = lic.public_key_hex(private)

        out = tmp_path / "licence.json"
        issued = self._run("issue", "--key-hex", seed, "--customer", "acme",
                           "--days", "7", "--features", "pro,beta", "--out", str(out))
        assert issued.returncode == 0, issued.stderr
        assert out.exists()

        ok = self._run("verify", str(out), "--pubkey-hex", pub, "--require", "pro")
        assert ok.returncode == 0, ok.stderr
        assert "OK" in ok.stdout

        refused = self._run("verify", str(out), "--pubkey-hex", pub, "--require", "enterprise")
        assert refused.returncode == 1
        assert "does not grant" in refused.stderr

    def test_pubkey_subcommand_matches(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        private = Ed25519PrivateKey.generate()
        seed = private.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        ).hex()
        result = self._run("pubkey", "--key-hex", seed)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == lic.public_key_hex(private)
