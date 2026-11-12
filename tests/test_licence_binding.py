"""Licence-bound payload keys (--licence-token).

The binding is a capability, not a claim: the payload key is derived from
the token's ``key_material`` at pack time, and the loader re-derives it
from the token at run time.  A forged token carries other material and
therefore derives a key that does not match the ciphertext, which is why
nothing in the artefact verifies the Ed25519 signature: the signature
protects issuance, the material protects decryption.
"""

import json
import os

import pytest

from obfuscator.core.pipeline import generate_hybrid_loader_script
from obfuscator.key_emit import derive_effective_key
from obfuscator.licensing import (
    Licence,
    issue,
    private_key_from_hex,
    public_key_from_hex,
    public_key_hex,
    verify,
)

_KEY = bytes(range(32))
_BLANKS = {"windows": "", "linux": "", "darwin": ""}


def _token(tmp_path, name="acme.licence"):
    seed = "22" * 32
    lic = Licence(
        licence_id="L-1", customer="acme", issued_at=0, expires_at=2**31,
        features=("pro",))
    token = issue(lic, private_key_from_hex(seed))
    path = tmp_path / name
    path.write_text(token, encoding="utf-8")
    return token, path, seed


def test_issue_always_carries_key_material(tmp_path):
    token, _, seed = _token(tmp_path)
    payload = json.loads(token)["payload"]
    material = payload["key_material"]
    assert isinstance(material, str) and len(material) == 64
    # The signature covers the material, and verify() round-trips it.
    verified = verify(token, public_key_from_hex(public_key_hex(
        private_key_from_hex(seed))))
    assert verified.customer == "acme"
    assert verified.key_material == material


def test_key_material_changes_the_derived_key(tmp_path):
    token, _, _ = _token(tmp_path)
    material = json.loads(token)["payload"]["key_material"]
    plain = derive_effective_key(_KEY, "bid-1")
    bound = derive_effective_key(_KEY, "bid-1", material)
    assert bound != plain
    # Different licences never share a key for the same build id.
    other = derive_effective_key(_KEY, "bid-1", "ff" * 32)
    assert other not in (plain, bound)


def test_loader_emits_the_bound_plumbing(tmp_path):
    token, _, _ = _token(tmp_path)
    material = json.loads(token)["payload"]["key_material"]
    src, _, _ = generate_hybrid_loader_script(
        _BLANKS, b"", _KEY.hex(), build_id="bid-l1",
        customer_salt=material, licence_bound=True)
    assert '_NX_LICENCE_BOUND = "1" == "1"' in src
    assert "_nx_licence_key" in src
    # Unbound builds keep the old shape (flag false, literal salt empty).
    plain, _, _ = generate_hybrid_loader_script(
        _BLANKS, b"", _KEY.hex(), build_id="bid-l1")
    assert '_NX_LICENCE_BOUND = "0" == "1"' in plain


def test_env_only_helper_does_not_search_local_files():
    from obfuscator.core.pipeline import _licence_runtime_helpers
    src = _licence_runtime_helpers("a" * 64, False, True)
    assert "NIXON_LICENCE" in src
    assert '"__ENV_ONLY__"' not in src
    compile(src, "<env_only_helper>", "exec")


def test_hybrid_env_only_binding_does_not_search_local_files():
    src, _, _ = generate_hybrid_loader_script(
        _BLANKS, b"", _KEY.hex(), build_id="bid-env-only",
        customer_salt="ab" * 32, licence_bound=True, licence_env_only=True)
    start = src.index("def _nx_licence_key(")
    end = src.index("_BLOB_S0 =", start)
    helper = src[start:end]
    assert "NIXON_LICENCE" in helper
    assert "licence.json" not in helper
    assert "no local token search" in helper
    compile(helper, "<env_only_hybrid>", "exec")


def _load_lookup(src):
    """Exec just the emitted _nx_licence_key() helper."""
    start = src.index("def _nx_licence_key(")
    end = src.index("_BLOB_S0 =", start)
    ns = {}
    exec(compile(src[start:end], "<licence_lookup>", "exec"), ns)
    return ns["_nx_licence_key"]


def test_loader_reads_the_material_from_the_token(tmp_path, monkeypatch):
    token, path, _ = _token(tmp_path)
    material = json.loads(token)["payload"]["key_material"]
    src, _, _ = generate_hybrid_loader_script(
        _BLANKS, b"", _KEY.hex(), build_id="bid-l2",
        customer_salt=material, licence_bound=True)
    lookup = _load_lookup(src)

    monkeypatch.setenv("NIXON_LICENCE", str(path))
    assert lookup() == material

    # No token anywhere: the mask is absent, so the derived key differs and
    # the payload decrypts to garbage -- the intended "inert without a
    # licence" behaviour.
    monkeypatch.delenv("NIXON_LICENCE", raising=False)
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)
    assert lookup() is None


def test_loader_head_has_bootstrap_token_helper():
    from obfuscator.core.sources import LOADER_HEAD
    assert "def _nx_bootstrap_token_key():" in LOADER_HEAD
    assert "{licence_bootstrap_encrypted}" in LOADER_HEAD
    assert "{licence_helpers}" in LOADER_HEAD


def test_licence_bootstrap_encrypted_via_unified_flag_is_parsed():
    from obfuscator.core.pipeline import apply_unified_specs, build_parser
    parser, _subparsers = build_parser()
    args = parser.parse_args(["build", "src.py"])
    assert not hasattr(args, "licence_bootstrap_encrypted")
    args = parser.parse_args(
        ["build", "src.py", "--licence", "bootstrap-encrypted"])
    args = apply_unified_specs(args)
    assert args.licence_bootstrap_encrypted is True


def test_licence_helper_pins_token_hash():
    from obfuscator.core.pipeline import _licence_runtime_helpers
    src = _licence_runtime_helpers("a" * 64, False, False)
    assert "_nx_licence_payload" in src
    assert "__TOKEN_HASH__" not in src
    assert "licence token does not match the pinned token" in src


def test_parse_chain_spec_accepts_required_fields():
    from obfuscator.licensing import parse_chain_spec
    chain = parse_chain_spec([
        "contract=0x" + "a" * 40,
        "token-id=1",
        "owner=0x" + "b" * 40,
        "rpc=https://example.invalid/v1",
        "chain-id=1",
    ])
    assert chain["contract"] == "0x" + "a" * 40
    assert chain["token_id"] == "1"
    assert chain["owner"] == "0x" + "b" * 40
    assert chain["rpc"] == "https://example.invalid/v1"
    assert chain["chain_id"] == "1"


def test_licence_helper_can_enable_chain_gate():
    from obfuscator.core.pipeline import _licence_runtime_helpers
    src = _licence_runtime_helpers("a" * 64, True, True)
    assert "chain_owner_of" in src
    assert '"__CHAIN_ENABLED__"' not in src


def _chain_payload(chain):
    return {
        "licence_id": "L-chain", "customer": "acme", "issued_at": 0,
        "expires_at": 2**31, "features": ["pro"],
        "key_material": "ab" * 32, "chain": chain,
    }


def _exec_chain_helpers(payload, fake_owner_of):
    """Exec the emitted helpers with ownerOf stubbed out (no network).

    Returns the namespace so the test can call _nx_licence_payload() the
    way the loader does: the chain gate either returns the payload or exits.
    """
    import hashlib

    from obfuscator.core.pipeline import _licence_runtime_helpers
    from obfuscator.licensing import canonical
    token_hash = hashlib.sha256(canonical(payload)).hexdigest()
    src = _licence_runtime_helpers(token_hash, True, True)
    # The emitted helper hashes with the loader's aliased hashlib module
    # (same identifier sources.py uses throughout the loader).
    ns = {"_nixon_ハッシュ해시": hashlib}
    exec(compile(src, "<chain_helpers>", "exec"), ns)
    ns["chain_owner_of"] = fake_owner_of
    return ns


def _chain_token(tmp_path, payload):
    token = tmp_path / "acme.licence"
    token.write_text(json.dumps({"payload": payload, "sig": "00"}),
                     encoding="utf-8")
    return token


def test_chain_gate_owner_mismatch_stops_the_loader(tmp_path, monkeypatch,
                                                    capsys):
    payload = _chain_payload({
        "rpc": "https://example.invalid/v1",
        "contract": "0x" + "a" * 40,
        "token_id": "1",
        "owner": "0x" + "b" * 40,
        "chain_id": "1",
    })
    seen = {}

    def fake_owner_of(rpc, contract, token_id, expected_chain_id=None):
        seen.update(rpc=rpc, contract=contract, token_id=token_id,
                    chain_id=expected_chain_id)
        return "0x" + "c" * 40  # the NFT moved on chain

    ns = _exec_chain_helpers(payload, fake_owner_of)
    monkeypatch.setenv("NIXON_LICENCE", str(_chain_token(tmp_path, payload)))
    with pytest.raises(SystemExit):
        ns["_nx_licence_payload"]()
    assert "licence chain owner mismatch" in capsys.readouterr().err
    # The check used the RPC, contract, and id signed into the token.
    assert seen == {"rpc": "https://example.invalid/v1",
                    "contract": "0x" + "a" * 40,
                    "token_id": 1, "chain_id": 1}


def test_chain_gate_success_returns_the_payload(tmp_path, monkeypatch):
    payload = _chain_payload({
        "rpc": "https://example.invalid/v1",
        "contract": "0x" + "a" * 40,
        "token_id": "7",
        "owner": "0x" + "b" * 40,
    })

    def fake_owner_of(rpc, contract, token_id, expected_chain_id=None):
        assert rpc.startswith("https://")
        return "0x" + "B" * 40  # case-insensitive match

    ns = _exec_chain_helpers(payload, fake_owner_of)
    monkeypatch.setenv("NIXON_LICENCE", str(_chain_token(tmp_path, payload)))
    assert ns["_nx_licence_payload"]() == payload


def test_chain_gate_failure_names_the_cause(tmp_path, monkeypatch, capsys):
    payload = _chain_payload({
        "rpc": "https://example.invalid/v1",
        "contract": "0x" + "a" * 40,
        "token_id": "1",
        "owner": "0x" + "b" * 40,
    })

    def fake_owner_of(rpc, contract, token_id, expected_chain_id=None):
        raise RuntimeError("rpc down")

    ns = _exec_chain_helpers(payload, fake_owner_of)
    monkeypatch.setenv("NIXON_LICENCE", str(_chain_token(tmp_path, payload)))
    with pytest.raises(SystemExit):
        ns["_nx_licence_payload"]()
    err = capsys.readouterr().err
    # A chain failure is not "no token": it names the cause and stops.
    assert "licence chain verification failed: rpc down" in err
    assert "licence token required" not in err


def test_chain_gate_missing_signed_fields(tmp_path, monkeypatch, capsys):
    payload = _chain_payload({})

    def fake_owner_of(rpc, contract, token_id, expected_chain_id=None):
        raise AssertionError("ownerOf must not run without signed fields")

    ns = _exec_chain_helpers(payload, fake_owner_of)
    monkeypatch.setenv("NIXON_LICENCE", str(_chain_token(tmp_path, payload)))
    with pytest.raises(SystemExit):
        ns["_nx_licence_payload"]()
    err = capsys.readouterr().err
    assert "missing signed chain fields" in err
    assert set(part.strip() for part in err.split(":")[-1].split(",")) == {
        "rpc", "contract", "token_id", "owner"}


def test_bound_build_marks_the_artefact_and_demands_the_token(tmp_path):
    """The source path applies the binding now, so this is the real check.

    It used to refuse the flag without --native. That was true when only
    the hybrid loader carried the mask; the source emitter now carries it
    too, so the property to test is the one that matters: the artefact
    runs with its token and refuses without it.
    """
    import subprocess
    import sys

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _, path, issuer_seed = _token(tmp_path)
    from obfuscator.licensing import private_key_from_hex, public_key_hex
    public_key = public_key_hex(private_key_from_hex(issuer_seed))
    src = tmp_path / "payload.py"
    src.write_text('print("BOUND_OK")\n', encoding="utf-8")
    build = subprocess.run(
        [sys.executable, "-m", "obfuscator.core.pipeline", "build", str(src),
         "--licence", "token=" + str(path)],
        # 1800s, not 900s. Licence-bound builds have grown heavier with
        # signature pinning and bootstrap encryption; the leash was catching
        # a slow build, not a hang.
        cwd=tmp_path, capture_output=True, text=True, timeout=1800,
        env=dict(os.environ, PYTHONPATH=repo, NIXON_LOG_REDIRECT="0",
                 NIXON_LICENCE_PUBLIC_KEY=public_key))
    assert build.returncode == 0, build.stderr[-800:]

    artefact = _find_artefact(tmp_path)
    assert artefact is not None, "no artefact produced"

    without = subprocess.run(
        [sys.executable, str(artefact)],
        cwd=tmp_path, capture_output=True, text=True, timeout=120,
        env={k: v for k, v in os.environ.items() if k != "NIXON_LICENCE"})
    assert without.returncode != 0, "a bound artefact ran without its licence"
    assert "licence token required" in (without.stdout + without.stderr)

    with_token = subprocess.run(
        [sys.executable, str(artefact)],
        cwd=tmp_path, capture_output=True, text=True, timeout=120,
        env=dict(os.environ, NIXON_LICENCE=str(path)))
    assert with_token.returncode == 0, with_token.stderr[-800:]
    assert "BOUND_OK" in with_token.stdout

    forged = tmp_path / "forged.licence"
    forged.write_text(json.dumps({"payload": {"key_material": "00" * 32}}),
                      encoding="utf-8")
    with_forged = subprocess.run(
        [sys.executable, str(artefact)],
        cwd=tmp_path, capture_output=True, text=True, timeout=120,
        env=dict(os.environ, NIXON_LICENCE=str(forged)))
    assert with_forged.returncode != 0, (
        "a forged token decrypted the payload; the token is only a presence gate")
    forged_output = with_forged.stdout + with_forged.stderr
    assert (
        "Magic Mismatch" in forged_output
        or "licence token does not match the pinned token" in forged_output
    ), forged_output


def test_verification_harness_presents_the_token(tmp_path):
    """The variant table must run a bound artefact the way the operator does.

    A bound loader refuses without NIXON_LICENCE, so a harness that omits the
    token reads every correctly bound build as MISMATCH -- which, since the
    verification gate now fails the build, meant bound artefacts could never
    ship. test_protected_file must present the token when given one and still
    fail the un-tokened run, exactly like the real loader.
    """
    from obfuscator.core.pipeline import test_protected_file

    original = tmp_path / "orig.py"
    original.write_text('print("OK")\n', encoding="utf-8")
    bound = tmp_path / "bound.py"
    bound.write_text(
        "import os, sys\n"
        "if not os.environ.get('NIXON_LICENCE'):\n"
        "    sys.stderr.write('licence token required\\n'); sys.exit(1)\n"
        "print('OK')\n",
        encoding="utf-8")

    harness_fail = test_protected_file(str(bound), str(original))
    assert harness_fail['obfuscated']['status'] == 'FAIL', (
        "the harness must not silently hand the token to an un-tokened run")

    harness_pass = test_protected_file(
        str(bound), str(original),
        licence_path=str(tmp_path / "acme.licence"))
    assert harness_pass['obfuscated']['status'] == 'PASS'
    assert harness_pass['comparison']['outputs_match'] is True


def _find_artefact(tmp_path):
    """Where `pipeline build` puts its output (dist/ beside the source)."""
    for root, _dirs, files in os.walk(tmp_path):
        for name in files:
            if name.endswith("_protected.py"):
                return os.path.join(root, name)
    return None
