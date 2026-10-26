# -*- coding: utf-8 -*-
"""Hardening A2.2/A2.3: the fixed runtime vocabulary must not ship.

The loader used to name the same things in every build -- the kill ladder
entry point and the audit-hook state.  These tests pin the properties that
make a single rename pass safe:

* total: no fixed marker survives;
* consistent: a quoted ``globals().get("<name>")`` lookup is renamed with
  the same spelling as the ``def``, so the runtime lookup still resolves;
* per-build: two builds never share a name;
* functional: the *renamed* kill ladder still exits 137, and the renamed
  audit snippet still compiles;
* fail-loud: a loader that calls the ladder without defining it fails the
  build instead of raising ``NameError`` at run time.
"""
import ast
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from obfuscator import marker_names as mn


def _sample(token="deadbeef00"):
    """A miniature loader covering every renamed marker, all three forms."""
    return (
        "def _nx_kill(_reason=''):\n"
        "    import os as _nx_os\n"
        "    _nx_os._exit(137)\n"
        "\n"
        "_NX_AUDIT_OPT_OUT = False\n"
        "_NX_AUDIT_WRAPPED = False\n"
        "_NX_AUDIT_ADDED = 0\n"
        "_NX_AUDIT_WRAPPER_ID = 0\n"
        "_NX_AUDIT_SEEN = 0\n"
        "_NX_AUDIT_T0 = 0\n"
        "_NX_AUDIT_BASE_MEAN = 0\n"
        "_nx_entry_file = None\n"
        "\n"
        "_NX_ATTR_MAP = {}\n"
        "_NX_SENTINEL = object()\n"
        "_NX_SKIP_ON = False\n"
        "_NX_CI_ON = False\n"
        "if _NX_SKIP_ON and _NX_CI_ON:\n"
        "    pass\n"
        "_NX_POISON_KEY = 'poison-slot'\n"
        "globals()[_NX_POISON_KEY] = 0\n"
        "\n"
        "def _nx_is_site_path(_p):\n"
        "    return False\n"
        "\n"
        "def _nx_addaudithook(_hook, *args, **kwargs):\n"
        "    globals()['_NX_AUDIT_ADDED'] = 1\n"
        "    return 0\n"
        "\n"
        "def _nx_audit_canary(_ev, _args):\n"
        "    globals()['_NX_AUDIT_SEEN'] = 2\n"
        "\n"
        "def _nx_audit_baseline():\n"
        "    return 1\n"
        "\n"
        "def _nx_audit_verify():\n"
        "    _mine = globals().get('_nx_addaudithook', None)\n"
        "    _orig = globals().get('_nx_orig_addaudithook', None)\n"
        "    if _mine is None and _orig is None:\n"
        "        _nx_kill('audit-plant')\n"
        "    return 'ok'\n"
        "\n"
        "_nx_orig_addaudithook = None\n"
    )


def test_rename_is_total():
    tok = "aabbccddee"
    out = mn.rename_markers(_sample(tok), tok)
    assert mn.leftover_markers(out, tok) == []
    # Every build name is present, and the module's own map agrees.
    for fixed, build in mn.marker_map(tok).items():
        if fixed == mn.KILL_MARKER:
            assert "def %s(" % build in out
        else:
            assert build in out, (fixed, build)


def test_rename_is_per_build():
    a = mn.marker_map("1111111111")
    b = mn.marker_map("2222222222")
    assert set(a.values()).isdisjoint(set(b.values()))
    assert a[mn.KILL_MARKER] != b[mn.KILL_MARKER]
    assert mn.new_token() != mn.new_token()


def test_quoted_globals_lookup_uses_the_same_spelling():
    """The audit re-check resolves its wrapper through globals() *by name*.

    If the quoted form were left untouched, ``_mine`` would be ``None`` on
    every build and the "hook was replaced" branch would fire spuriously
    (or, worse, never fire at all once the definition is renamed).
    """
    tok = "0f0f0f0f0f"
    out = mn.rename_markers(_sample(tok), tok)
    wrapper = mn.marker_map(tok)["_nx_addaudithook"]
    orig = mn.marker_map(tok)["_nx_orig_addaudithook"]
    assert "def %s(" % wrapper in out
    assert "globals().get('%s', None)" % wrapper in out
    assert "globals().get('%s', None)" % orig in out
    assert "'_nx_addaudithook'" not in out


def test_renamed_snippet_compiles_and_parses():
    tok = "1234567890"
    out = mn.rename_markers(_sample(tok), tok)
    compile(out, "<renamed>", "exec")
    ast.parse(out, feature_version=(3, 10))


def test_renamed_kill_ladder_still_exits_137():
    """The rename must not change behaviour: same silent 137."""
    from obfuscator.kill_ladder import emit_kill_snippet

    tok = mn.new_token()
    src = mn.rename_markers(emit_kill_snippet(), tok)
    name = mn.kill_name(tok)
    assert "_nx_kill" not in src
    code = src + "\n%s('vm-detect')\n" % (name,)
    proc = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 137, (proc.returncode, proc.stdout, proc.stderr)
    assert proc.stdout == ""


def test_renamed_audit_snippet_compiles():
    from obfuscator.audit_hook import emit_snippet

    tok = mn.new_token()
    src = mn.rename_markers(emit_snippet(), tok)
    assert mn.leftover_markers(src, tok) == []
    compile(src, "<renamed_audit>", "exec")
    ast.parse(src, feature_version=(3, 10))


def test_assert_kill_wired_rejects_call_without_definition():
    tok = "abcabcabca"
    name = mn.kill_name(tok)
    broken = "def gate():\n    %s('vm-detect')\n" % (name,)
    with pytest.raises(RuntimeError) as exc:
        mn.assert_kill_wired(broken, tok)
    assert name in str(exc.value)


def test_assert_kill_wired_accepts_wired_and_absent_ladders():
    tok = "abcabcabcb"
    name = mn.kill_name(tok)
    ok = ("def %s(_reason=''):\n    pass\ndef gate():\n    %s('x')\n"
          % (name, name))
    mn.assert_kill_wired(ok, tok)          # no raise
    mn.assert_kill_wired("def gate():\n    return 1\n", tok)  # no raise
    mn.assert_kill_wired("", tok)


def test_assert_markers_renamed_catches_partial_rename():
    tok = "abcabcabcc"
    partial = "def %s(_reason=''):\n    pass\n_NX_AUDIT_SEEN = 0\n" % (
        mn.kill_name(tok),)
    with pytest.raises(RuntimeError) as exc:
        mn.assert_markers_renamed(partial, tok)
    assert "_NX_AUDIT_SEEN" in str(exc.value)


def test_marker_names_do_not_collide_with_each_other():
    tok = "abcabcabcd"
    values = list(mn.marker_map(tok).values())
    assert len(values) == len(set(values))
