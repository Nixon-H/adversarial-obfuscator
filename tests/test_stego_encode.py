"""Coverage for the zero-width-steganography encoder.

The deep-matrix stego lane was removed because scripts/build.py has no
stego support and the lane could never pass; the feature itself lives in
the obfuscator pipeline and had NO coverage anywhere. These tests pin
the round-trip including the two bugs the lane comments mention: a
double-escaped ZWS character and a Latin-1/UTF-8 mix-up that corrupted
every non-ASCII byte.
"""
import subprocess
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from obfuscator.core.transforms import stego_encode  # noqa: E402


def _run_stego(artifact_source, tmp_path, extra_args=()):
    art = tmp_path / "art.py"
    art.write_text(artifact_source, encoding="utf-8")
    return subprocess.run([sys.executable, str(art), *extra_args],
                          capture_output=True, text=True, timeout=60)


def test_roundtrip_executes_original_source(tmp_path):
    src = "print('hello stego')\n"
    r = _run_stego(stego_encode(src), tmp_path)
    assert r.returncode == 0, r.stderr[-300:]
    assert r.stdout.strip() == "hello stego"


def test_roundtrip_preserves_non_ascii_bytes(tmp_path):
    """The Latin-1/UTF-8 mix-up: non-ASCII payloads must survive byte-exactly."""
    src = "print('héllo wörld — ünïcodé')\n"
    r = _run_stego(stego_encode(src), tmp_path)
    assert r.returncode == 0, r.stderr[-300:]
    assert r.stdout.strip() == "héllo wörld — ünïcodé"


def test_roundtrip_preserves_unicode_identifiers(tmp_path):
    """The artefact pipeline generates Unicode identifiers; the original bug
    corrupted them ('invalid non-printable character U+0090')."""
    src = "αβγ = 41\nprint(αβγ + 1)\n"
    r = _run_stego(stego_encode(src), tmp_path)
    assert r.returncode == 0, r.stderr[-300:]
    assert r.stdout.strip() == "42"


def test_foreign_exec_is_refused(tmp_path):
    """The identity gate: exec'd with a non-main __name__ must exit 2."""
    src = "print('should never print')\n"
    art = tmp_path / "art.py"
    art.write_text(stego_encode(src), encoding="utf-8")
    driver = tmp_path / "driver.py"
    driver.write_text(
        "src = open(%r, encoding='utf-8').read()\n"
        "exec(compile(src, 'art', 'exec'), {'__name__': 'not_main'})\n" % str(art),
        encoding="utf-8")
    r = subprocess.run([sys.executable, str(driver)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 2
    assert "should never print" not in r.stdout


def test_bootstrap_decodes_bytes_not_codepoints():
    """Structural pin on the Latin-1 fix: the bootstrap must decode bytes
    then UTF-8, never chr() per byte group."""
    out = stego_encode("print(1)\n")
    assert "bytes(" in out and '.decode("utf-8")' in out
    assert "chr(" not in out
