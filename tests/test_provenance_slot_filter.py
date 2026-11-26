"""Regression: only the exact provenance slot assignment is excluded.

Measured bypass (2026-11-25): both the Ed25519 signed content and the
Merkle/HMAC self-check excluded every line CONTAINING `_NX_PROV_SIG` or
`_NX_PROV_PK`. Four live executable lines mention those names, so attacker
code appended to one of them ran while the signed and hashed bytes stayed
byte-identical.
"""

from obfuscator.attestation import signed_content
from obfuscator.core.pipeline import generate_hybrid_loader_script


def _artefact(*lines):
    return ("\n".join(lines) + "\n").encode()


def test_live_line_mentioning_slot_is_signed():
    data = _artefact(
        '_NX_PROV_SIG = "AAAA"',
        '_nx_prov_pk_s = bool(globals().get("_NX_PROV_PK", ""))',
        "print('payload')",
    )
    signed = signed_content(data)
    assert b"_nx_prov_pk_s" in signed
    assert b"print('payload')" in signed


def test_appended_code_on_slot_line_is_signed():
    data = _artefact('_NX_PROV_SIG = "AAAA"; import os; os.system("id")')
    assert b"os.system" in signed_content(data)


def test_exact_slot_assignment_is_excluded():
    data = _artefact('_NX_PROV_SIG = "AAAA"', '_NX_PROV_PK = "bbbb: cccc"',
                     "print('x')")
    signed = signed_content(data)
    assert b"_NX_PROV_SIG" not in signed
    assert b"_NX_PROV_PK" not in signed
    assert b"print('x')" in signed


def test_emitted_loader_uses_strict_slot_helper():
    script, _meta, _fb = generate_hybrid_loader_script(
        native_blobs={}, bytecode_fallback=b"print('x')",
        key_hex="11" * 32, build_id="test-build")
    assert "_nx_slot_line" in script
    assert 'b"_NX_PROV_SIG" + b" = "' in script


def test_unbound_provenance_check_runs_after_selfcheck():
    script, _meta, _fb = generate_hybrid_loader_script(
        native_blobs={}, bytecode_fallback=b"print('x')",
        key_hex="11" * 32, build_id="test-build", self_check=True)
    selfcheck = script.find("_NX_SELF_OK = _nx_self_check()")
    live_check = script.find("_nx_prov_sig_s = bool")
    assert selfcheck >= 0
    assert live_check > selfcheck
