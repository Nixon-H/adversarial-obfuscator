"""AI-STRING-001: the string-seal shard must be required at LOAD, not first use.

Found by the A6 reverse-engineering benchmark. The agent recovered the entire
payload from a maximum-security artefact WITHOUT holding the seal shard, and
said exactly why:

    "the string-seal env-var requirement was NOT load-bearing -- this look-up
     happens in a try/except that degrades only if a caller actually invokes
     the decoder."

The emitted decoder did contain the shard check, but it ran INSIDE the decoder
function. An analyst who reads the payload's code-object constants and bytecode
never calls the decoder, so the check never ran and the missing shard was never
noticed. The feature's docstring claimed "the stub fails closed without it",
true only in the narrow sense of failing on first use.

These tests pin the emitted source. The BEHAVIOURAL proof was measured
separately and is recorded in docs/security/REVIEW_FINDINGS_FILED.md:
importing the emitted stub in a clean interpreter with no shard raises
"string KEK unavailable: this artefact requires the string-seal shard ...",
and importing it with a valid 32-byte shard succeeds. Both directions were
observed. Reproducing that here would need a subprocess with a controlled
environment, which the local write-time scanner refuses in a test file; the
source assertions below are what remain testable without it, and they cover
the property that actually regressed -- whether the gate is emitted at module
level at all.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _stub_source(kek_env="NX_SEAL_SHARD"):
    """Return the emitted decoder stub as source text."""
    from obfuscator.chacha20 import build_stub_decoder
    return build_stub_decoder("_nx_dec", "00" * 32, kek_env=kek_env)


def test_the_stub_emits_a_load_time_assertion():
    src = _stub_source()
    assert "_nx_assert_kek_present()" in src, (
        "the emitted stub has no load-time shard check, so an artefact can "
        "import and run its payload without the shard -- the exact gap the A6 "
        "benchmark agent reported")
    module_level = [ln.strip() for ln in src.splitlines()]
    assert "_nx_assert_kek_present()" in module_level, (
        "the assertion is defined but never called at module level, so it "
        "would not run on import")


def test_the_gate_is_a_module_level_statement_not_inside_the_decoder():
    """The call must sit after the decoder def, at column zero."""
    src = _stub_source()
    lines = src.splitlines()
    call_lines = [ln for ln in lines if ln.strip() == "_nx_assert_kek_present()"]
    assert call_lines, "no bare module-level call found"
    for ln in call_lines:
        assert ln == ln.lstrip(), (
            "the call is indented, so it sits inside a function and will not "
            "run at import")


def test_the_gate_refuses_a_missing_shard():
    """The emitted text must name the failure and refuse to continue."""
    src = _stub_source()
    assert "KEK unavailable" in src, (
        "no diagnostic for a missing shard")
    assert "raise ValueError" in src


def test_the_gate_validates_hex_and_length():
    src = _stub_source()
    assert "not valid hex" in src, "no hex validation in the emitted gate"
    assert "shorter than 16 bytes" in src, (
        "no minimum-length check in the emitted gate")


def test_the_stub_compiles():
    compile(_stub_source(), "<emitted-stub>", "exec")


def test_no_gate_is_emitted_when_kek_env_is_absent():
    """A build that did not ask for a shard must not require one."""
    src = _stub_source(kek_env=None)
    assert "_nx_assert_kek_present" not in src, (
        "a shard-free build emitted a shard requirement, which would break "
        "every artefact built without string-key-env")
