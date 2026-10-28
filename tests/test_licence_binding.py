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
    _, path, _ = _token(tmp_path)
    src = tmp_path / "payload.py"
    src.write_text('print("BOUND_OK")\n', encoding="utf-8")
    build = subprocess.run(
        [sys.executable, "-m", "obfuscator.core.pipeline", "build", str(src),
         "--licence-token", str(path)],
        cwd=tmp_path, capture_output=True, text=True, timeout=300,
        env=dict(os.environ, PYTHONPATH=repo, NIXON_LOG_REDIRECT="0"))
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


def _find_artefact(tmp_path):
    """Where `pipeline build` puts its output (dist/ beside the source)."""
    for root, _dirs, files in os.walk(tmp_path):
        for name in files:
            if name.endswith("_protected.py"):
                return os.path.join(root, name)
    return None
