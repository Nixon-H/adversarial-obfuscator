"""C transformation layer: each transform must be correct, safe, polymorphic.

The transforms run on Cython-generated C.  A wrong transform here means the
native build produces a binary that crashes or misbehaves, so every test
checks both correctness (the transformed code is still valid C with the same
semantics) and the security property.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.c_transform import (  # noqa: E402
    encrypt_strings, transform_c, _unescape_c, _c_escape,
)

# A minimal Cython-generated C file (the patterns this layer targets).
CYX_C = r'''
#include "Python.h"
typedef int __pyx_t_3;
static char __pyx_k_hello[] = "hello_world_secret_function";
static char __pyx_k_route[] = "/api/v2/decrypt";
static char __pyx_k_empty[] = "";
static char __pyx_k_msg[] = "Authorization: Bearer ";
static char __pyx_k_build[] = "b1a2c3d4e5";

static int __pyx_f_1f(__pyx_t_3 _x) {
  int locals_1 = 0;
  int __pyx_t_3 = (int)_x;
  if (__pyx_t_3) {
    locals_1 = 1;
  }
  return locals_1;
}

static void __Pyx_InitStrings(void) {
  /* ... */
}
'''

SEED = b"test-seed-1234"


def test_unescape_c_round_trips_octal_and_hex():
    for data in (b"hello\x00\x01\xff", b'quote " and backslash \\'):
        literal = _c_escape(data)
        # The unescaper receives the body BETWEEN the quotes.
        assert _unescape_c(literal[1:-1]) == data


def test_string_encryption_hides_all_literals():
    """After encryption, no plaintext string literal survives."""
    new, count = encrypt_strings(CYX_C, SEED, __import__("random").Random(42))
    assert count >= 4, "expected at least 4 strings encrypted, got %d" % count
    for plaintext in ("hello_world_secret_function", "/api/v2/decrypt",
                      "Authorization: Bearer ", "b1a2c3d4e5"):
        assert plaintext not in new, (
            "plaintext %r survived encryption" % plaintext)


def test_string_encryption_preserves_array_names():
    new, _ = encrypt_strings(CYX_C, SEED, __import__("random").Random(42))
    for name in ("__pyx_k_hello", "__pyx_k_route", "__pyx_k_empty",
                 "__pyx_k_msg", "__pyx_k_build"):
        assert ("static char %s[]" % name) in new, (
            "array definition for %s missing after encryption" % name)


def test_string_encryption_adds_decrypt_function():
    new, _ = encrypt_strings(CYX_C, SEED, __import__("random").Random(42))
    assert "__nx_decrypt_strings" in new
    assert "__nx_decrypt_strings();" in new, "decrypt call not emitted"
    # The call must be INSIDE __Pyx_InitStrings' body (at file scope it
    # would be parsed as a declaration, not a call).
    call_pos = new.find("__nx_decrypt_strings();")
    init_pos = new.find("__Pyx_InitStrings")
    assert call_pos > init_pos, (
        "the decrypt call is at file scope, where gcc parses it as a "
        "declaration instead of a call")


def test_string_encryption_is_polymorphic():
    """Different seeds produce different ciphertexts for the same input."""
    a, _ = encrypt_strings(CYX_C, b"seed-one", __import__("random").Random(1))
    b, _ = encrypt_strings(CYX_C, b"seed-two", __import__("random").Random(2))
    assert a != b, "different seeds produced the same encrypted output"


def test_empty_string_is_skipped():
    """The empty string has nothing to encrypt; it must not be corrupted."""
    new, _ = encrypt_strings(CYX_C, SEED, __import__("random").Random(42))
    # The array definition is still present.
    assert "static char __pyx_k_empty[]" in new


def test_non_cython_source_is_skipped():
    """A file without __pyx_k_* definitions is returned unchanged."""
    plain = 'int main() { return 0; }\n'
    new, count = encrypt_strings(plain, SEED, __import__("random").Random(42))
    assert count == 0
    assert new == plain


def test_full_transform_produces_valid_c(tmp_path):
    """The transformed source must be valid C (syntax-only check)."""
    result = transform_c(CYX_C, SEED)
    assert result.strings_encrypted > 0
    # Use the real Python include path so gcc can resolve Python.h.
    import sysconfig
    py_inc = sysconfig.get_paths().get("include", "")
    out = tmp_path / "test.c"
    out.write_text(result.source, encoding="utf-8")
    import subprocess
    proc = subprocess.run(
        ["gcc", "-fsyntax-only", "-std=c99", "-I", py_inc, str(out)],
        capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, (
        "transformed C does not pass syntax check:\n%s\n---\n%s"
        % (proc.stderr[:800], result.source[:600]))


def test_transform_is_polymorphic():
    """Same input, different seed -> different output."""
    a = transform_c(CYX_C, b"seed-a")
    b = transform_c(CYX_C, b"seed-b")
    assert a.source != b.source
    assert a.transforms_applied != b.transforms_applied or \
        a.strings_encrypted == b.strings_encrypted  # both encrypt


def test_transform_correctness_all_transforms():
    """All transforms together must not break the C structure."""
    result = transform_c(CYX_C, b"all-on")
    assert result.strings_encrypted > 0
    assert result.junk_injected > 0
    # The transformed source must still contain the function definition.
    assert "__pyx_f_1f" in result.source or "static int" in result.source


def test_transform_valid_c_across_seeded_fuzz(tmp_path):
    """Regression for the 2026-11-28 malformed-C class: the dead-block pass
    spliced blocks into Cython's metadata header comment because the line
    scan had no comment/string/initialiser awareness -- 34/60 seeds failed
    on real payload output.  This fuzz uses the same comment-heavy shapes:
    a header comment with bracey JSON-ish lines, bracey string literals,
    and a multi-line initialiser.  Every seed must yield valid C."""
    import subprocess, sysconfig
    bracey = (
        "/* BEGIN: metadata\n"
        "{\n"
        "    \"pkg\": {\n"
        "        \"src\": [\"x.py\"]\n"
        "    },\n"
        "}\n"
        "END: metadata */\n"
        "static const char *msg = \"brace } inside string {\";\n"
        "static int arr[3] = {\n"
        "    1,\n"
        "    2,\n"
        "    3,\n"
        "};\n"
    )
    src = bracey + CYX_C
    py_inc = sysconfig.get_paths().get("include", "")
    bad = []
    for i in range(12):
        seed = ("regression-%d" % i).encode()
        result = transform_c(src, seed)
        out = tmp_path / ("fuzz%d.c" % i)
        out.write_text(result.source, encoding="utf-8")
        proc = subprocess.run(
            ["gcc", "-fsyntax-only", "-std=c99", "-I", py_inc, str(out)],
            capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            bad.append((i, proc.stderr[:200]))
    assert not bad, "malformed C on seeds: %s" % bad


def test_scan_c_structure_ignores_comment_braces():
    """The metadata comment must yield no injectable positions even though
    it is full of lines ending in `{`."""
    from scripts.c_transform import scan_c_structure
    comment = (
        "/* BEGIN\n"
        "{\n"
        "    \"distutils\": {\n"
        "}\n"
        "END */\n"
    )
    recs = scan_c_structure(comment)
    assert not any(r["injectable"] for r in recs)


def test_scan_c_structure_ignores_string_braces():
    """A `}` inside a string literal must not desync depth."""
    from scripts.c_transform import scan_c_structure
    src = (
        "static int f(void) {\n"
        "    const char *s = \"}\";\n"
        "    if (1) {\n"
        "        return 1;\n"
        "    }\n"
        "    return 0;\n"
        "}\n"
    )
    recs = scan_c_structure(src)
    # line 2 (`if (1) {`) must be seen at depth 2, injectable -- if the
    # string's `}` desynced depth it would read depth 1 or negative.
    assert recs[2]["injectable"] is True
    assert recs[2]["depth"] == 2
