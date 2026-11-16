"""The Cython (native) path must produce an artifact that still runs.

Regression for the 2026-11-15 bench finding. Recipe C (absolute maximum) is a
Python artifact; compiling it with Cython hit three separate walls:

1. ``_g = globals`` -- aliasing the ``globals`` builtin as a *value* makes
   Cython emit a reference to its internal ``__Pyx_Globals`` helper as a
   Python name, and the module dies at import with
   ``NameError: name '__Pyx_Globals' is not defined``. The loader's builtin
   alias table did exactly that. ``lambda: globals()`` compiles and behaves
   identically.

2. ``cdivision=True`` in the generated ``.pyx`` header makes ``1 / 0``
   return 0 instead of raising, so every ``ZeroDivisionError`` guard in the
   payload silently stops firing -- a behaviour change, not an optimisation.
   ``infer_types=True`` segfaulted this payload at import. Only
   ``language_level`` is safe here.

3. The loader's self-integrity check hashes its own ``.py`` source against a
   Merkle root and HMAC the build computed, and feeds ``sha256(content)``
   into the key chain. A compiled extension ships no ``.py``, so
   ``open(__file__)`` reads the ``.so`` and the check can only fail -- and
   it cannot simply be dropped, because the digest is part of the key. The
   digest is now computed at build time from the same bytes the ``.py``
   artifact would have hashed and baked into the native module.

These tests pin all three without needing a compiler.
"""
import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core import pipeline, sources


def _fake_loader(checksum="a" * 64, hmac_val="b" * 64, extra=""):
    return (
        "import os\n"
        '_ck = "%s"; _SIG_ANCHOR_ = "__SIG_ANCHOR__"\n'
        '_hm = "%s"; _HMAC_ANCHOR_ = "__HMAC_ANCHOR__"\n'
        "def self_check():\n"
        "    try:\n"
        "        with open(__file__, 'rb') as f: lines = f.readlines()\n"
        "        return b''\n"
        "    except Exception:\n"
        "        pass\n"
        "%s" % (checksum, hmac_val, extra)
    )


def test_native_self_digest_matches_the_runtime_filter():
    source = _fake_loader()
    digest = pipeline._native_self_digest(source)
    assert digest is not None
    raw = source.encode("utf-8")
    content = b"".join(
        line for line in raw.splitlines(keepends=True)
        if b"a" * 64 not in line and b"b" * 64 not in line)
    assert digest == hashlib.sha256(content).digest()


def test_native_self_digest_is_none_without_anchors():
    assert pipeline._native_self_digest("print('no self check here')\n") is None


def test_native_self_digest_excludes_only_the_two_anchor_lines():
    source = _fake_loader(extra="payload_line = 1\n")
    digest = pipeline._native_self_digest(source)
    raw = source.encode("utf-8")
    kept = [line for line in raw.splitlines(keepends=True)
            if b"a" * 64 not in line and b"b" * 64 not in line]
    assert b"payload_line = 1\n" in kept
    assert digest == hashlib.sha256(b"".join(kept)).digest()


def test_cython_header_does_not_change_division_semantics():
    # cdivision=True turns `1 / 0` into 0, which disarms every
    # ZeroDivisionError guard in the payload.
    src = open(pipeline.__file__, encoding="utf-8").read()
    header = re.search(r"cython_code = f'''(.*?)'''", src, re.S)
    assert header is not None
    assert "cdivision" not in header.group(1)
    assert "infer_types" not in header.group(1)
    assert "language_level=3" in header.group(1)


def test_globals_alias_is_a_lambda_not_a_bare_builtin():
    # `_g = globals` is a Cython compile-time trap; `lambda: globals()` is not.
    src = open(sources.__file__, encoding="utf-8").read()
    assert "_全域變數ตัวแป=globals;" not in src
    assert "_全域變數ตัวแป=(lambda: globals());" in src
