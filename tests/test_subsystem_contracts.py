"""Subsystem contract tests: existence + genuine-overlap differentials.

Companion to docs/contracts.md. Existence is asserted for all eight
pairs/groups (file present + key symbol defined, via AST — no imports, no
side effects). Differential tests exist ONLY where semantics genuinely
overlap:

- poly engines: same host -> comparable profile fields (os/python/arch).
- fragment cryptos: same plaintext vectors -> each roundtrips byte-identical.

Every other pair is documented "no differential - different jobs" in
docs/contracts.md and gets existence-only coverage here.
"""
import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _path(*parts):
    return os.path.join(ROOT, *parts)


def _top_level_names(path):
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


# -- existence: all pairs/groups present with their key symbols -----------

PAIRS = [
    # (path, expected top-level symbol proving the contract side exists)
    ("scripts/poly/poly_engine.py", "PolyEngine"),
    ("scripts/environment/poly_engine.py", "EnvironmentalPolyEngine"),
    ("scripts/payload/dispersal.py", "PayloadDisperser"),
    ("scripts/dispersal/payload_dispersal.py", "PayloadDispersal"),
    ("scripts/optimizer/profiler.py", "FunctionProfiler"),
    ("scripts/classification/function_classifier.py", "FunctionClassifier"),
    ("scripts/classification/strategy_selector.py", "StrategySelector"),
    ("scripts/fragment/fragment_compiler.py", "FragmentCompiler"),
    ("scripts/fragment/micro_fragment.py", "MicroFragmentExecutor"),
    ("scripts/distributed/dist_attestation.py", "DistributedAttestation"),
    ("scripts/runtime/challenge_response.py", "ChallengeResponse"),
    ("runtime/src/sw_attestation.rs", None),  # Rust side: content check below
    ("scripts/evidence/ledger.py", "EvidenceLedger"),
    ("scripts/certificates/certificate.py", "Certificate"),
    ("scripts/verification_bundle/bundler.py", "VerificationBundler"),
    ("scripts/self_audit/auditor.py", "SelfAuditor"),
    ("scripts/independent_audit/auditor.py", "IndependentAuditor"),
    ("scripts/claim_auditor/auditor.py", "audit_source"),
    ("scripts/false_confidence/auditor.py", "audit_source"),
    ("obfuscator/string_crypto.py", "encrypt_string"),
    ("obfuscator/chacha20.py", "aead_encrypt"),
]


def test_all_contract_sides_exist():
    missing = [p for p, _ in PAIRS if not os.path.isfile(_path(p))]
    assert not missing, "missing contract files: %s" % (missing,)
    for rel, symbol in PAIRS:
        if symbol is None or rel.endswith(".rs"):
            continue
        assert symbol in _top_level_names(_path(rel)), (rel, symbol)


def test_rust_attestation_core_present():
    with open(_path("runtime/src/sw_attestation.rs"), encoding="utf-8") as fh:
        src = fh.read()
    assert "ChallengeHandler" in src
    assert not os.path.exists(_path("native/attestation.c")), (
        "deleted C sim must stay deleted; canonical is sw_attestation.rs")


def test_string_crypto_layers_point_one_way():
    # chacha20 owns the primitive; string_crypto owns policy and imports it.
    with open(_path("obfuscator/string_crypto.py"), encoding="utf-8") as fh:
        upper = fh.read()
    with open(_path("obfuscator/chacha20.py"), encoding="utf-8") as fh:
        lower = fh.read()
    assert "from obfuscator.chacha20 import" in upper
    # Lower layer never imports the upper one (a comment may name it, but
    # no import statement may reference it).
    import re
    assert not re.search(r"^\s*(from|import)\s+[\w.]*string_crypto",
                         lower, re.M)


# -- differential: poly engines agree on platform facts --------------------

def test_poly_engines_agree_on_platform_facts():
    from scripts.poly.poly_engine import PolyEngine
    from scripts.environment.poly_engine import EnvironmentalPolyEngine
    a = PolyEngine(seed=1234).get_environment_profile()
    b = EnvironmentalPolyEngine(seed=1234).get_environment_profile()
    # Same host, same inputs -> comparable outputs on the shared fields.
    assert a["os"] == b["os"] and isinstance(a["os"], str) and a["os"]
    assert a["python"] == b["python"] and len(a["python"].split(".")) == 3
    assert a["arch"] == b["arch"] and isinstance(a["arch"], str) and a["arch"]
    # Fingerprints are engine-specific by design (different composition and
    # width); only their SHAPE is asserted, never equality.
    assert len(a["fingerprint"]) == 32
    assert len(b["fingerprint"]) == 16


# -- differential: fragment cryptos roundtrip shared vectors ---------------

_ROUNDTRIP_VECTORS = [
    b"",
    b"a",
    b"hello world",
    bytes(range(256)),
    b"\x00" * 1024,
    bytes((i * 37 + 11) % 256 for i in range(4096)),
]


def test_fragment_cryptos_roundtrip_shared_vectors():
    from scripts.fragment.fragment_compiler import aes_ctr_encrypt_fragment
    from scripts.fragment.micro_fragment import (
        _derive_sequence_key,
        _xor_encrypt,
    )
    key = b"contract-test-key-32-bytes!!!!!!"
    assert len(key) == 32
    for i, vec in enumerate(_ROUNDTRIP_VECTORS):
        # Both ciphers are symmetric CTR/XOR streams: re-applying decrypts.
        assert aes_ctr_encrypt_fragment(
            aes_ctr_encrypt_fragment(vec, key), key) == vec, i
        seq_key = _derive_sequence_key(key, i)
        assert _xor_encrypt(_xor_encrypt(vec, seq_key), seq_key) == vec, i
