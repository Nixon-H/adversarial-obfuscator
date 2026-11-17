"""The identity gate: a foreign exec must not initialise ANY loader state.

Benchmark 2026-11-17, position A, attack 3 (GLM 5.3 Flash): exec'ing the
sectioned artifact with ``__name__="not_main_loader"`` skipped the entry
point, survived every gate, exposed the reconstructed payload key and the
loader's own HMAC-verified section join in the namespace, and recovered
all three payload secrets in two peeled layers.  The fix refuses to
initialise at all unless the artifact IS the script the interpreter was
pointed at.

* TOP gate (shipped artifact loaders): ``__name__`` must be main-ish AND
  ``__file__`` must match ``sys.argv[0]`` -- a foreign exec has neither.
* STAGE gate (interior packaging layers: EXEC_TEMPLATE, ZIP_LOADER_TEMPLATE,
  stego bootstrap): those run exec'd/runpy'd inside the artifact's own
  globals, so a name check is the strongest available; it still kills the
  foreign exec at every layer.
"""
import pytest

from obfuscator.core.sources import (
    EXEC_TEMPLATE,
    IDENTITY_GATE_STAGE,
    IDENTITY_GATE_TOP,
    ZIP_LOADER_TEMPLATE,
)
from obfuscator.core.transforms import stego_encode
from obfuscator.core.pipeline import generate_hybrid_loader_script

_BLANK_BLOBS = {"native_blobs": "", "fallback_blob": ""}


def test_top_gate_kills_foreign_exec_before_any_state():
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANK_BLOBS), b"x", "11" * 32, identity_gate=True)
    ns = {"__name__": "not_main_loader"}
    with pytest.raises(SystemExit) as exc:
        exec(compile(src, "<loader>", "exec"), ns)
    assert exc.value.code == 2
    # the point: NOTHING was initialised -- no key material, no pack,
    # no helpers the attacker could drive afterwards
    assert "BLOB_KEY" not in ns
    assert "_NX_EFF_KEY" not in ns
    assert "_nx_section_join" not in ns


def test_top_gate_kills_fake_main_without_file_context():
    """__name__="__main__" alone is not enough: an exec'd module has no
    __file__, and a foreign __file__ does not match argv[0]."""
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANK_BLOBS), b"x", "11" * 32, identity_gate=True)
    ns = {"__name__": "__main__"}
    with pytest.raises(SystemExit) as exc:
        exec(compile(src, "<loader>", "exec"), ns)
    assert exc.value.code == 2


def test_gate_is_default_on_for_shipped_builds(monkeypatch):
    # conftest flips the session default off (in-process tests exec the
    # loader); the SHIPPED default is ON -- prove it by clearing the test
    # flag and generating without an explicit kwarg.
    import obfuscator.core.pipeline as pl
    monkeypatch.setattr(pl, "_NX_TEST_LOADER_GATES_OFF", False)
    src, _, _ = pl.generate_hybrid_loader_script(dict(_BLANK_BLOBS), b"x", "11" * 32)
    assert "[BLOCKED] identity" in src
    assert "_nx_self_check()" in src
    src2, _, _ = pl.generate_hybrid_loader_script(
        dict(_BLANK_BLOBS), b"x", "11" * 32, identity_gate=True)
    assert "[BLOCKED] identity" in src2
    # the gate text: main required, mp_main allowed with a file context
    assert '__name__ != "__main__"' in src2
    assert 'not in ("__main__", "__mp_main__")' in IDENTITY_GATE_STAGE


def _stage_exec(template):
    ns = {"__name__": "not_main_loader"}
    try:
        exec(compile(template, "<stage>", "exec"), ns)
    except SystemExit as e:
        return e.code
    return None


def test_exec_template_stage_gate_kills_foreign_exec():
    code = EXEC_TEMPLATE % {"VAR_PAYLOAD": "p", "PAYLOAD_STR": "AAAA",
                            "VAR_CODE": "c", "DECODE_FUNC": "base64.b64decode"}
    assert _stage_exec(code) == 2


def test_zip_template_stage_gate_kills_foreign_exec():
    code = ZIP_LOADER_TEMPLATE % {"VAR_PAYLOAD": "p", "PAYLOAD_STR": "AAAA",
                                  "VAR_BOOTSTRAP": "b", "VAR_DATA": "d",
                                  "DECODE_FUNC": "base64.b64decode",
                                  "VAR_TEMP": "t", "VAR_CLEAN": "cl",
                                  "VAR_MAIN": "m"}
    assert _stage_exec(code) == 2


def test_stego_bootstrap_gate_kills_foreign_exec():
    assert _stage_exec(stego_encode("print(1)")) == 2


def test_stage_gate_compiles_for_all_templates():
    # the gates ride through %-format and .format() templates: a stray
    # brace or % would break the build, not just the gate
    compile(IDENTITY_GATE_STAGE, "<stage>", "exec")
    compile(IDENTITY_GATE_TOP, "<top>", "exec")
    assert "{" not in IDENTITY_GATE_STAGE and "{" not in IDENTITY_GATE_TOP
    assert "%" not in IDENTITY_GATE_STAGE and "%" not in IDENTITY_GATE_TOP
