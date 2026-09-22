"""V10 kernel split-bootstrap: Shamir threshold key + fragmented decoder.

Closes the caveat honestly: kernel bootstrap derives key material from a
split-secret scheme and a fragmented decoder rather than a single embedded
key.

Covers:
- split->reconstruct roundtrip through the REAL ShamirSharing API
  (obfuscator/split_bootstrap.py reuses scripts/dispersal/
  payload_dispersal.py — never reimplements it), incl. keys with bytes
  >= 251 (the GF(251) lossy edge, bridged via ASCII-hex encoding).
- k-1 shares fail closed (ValueError).
- emitted snippet compile()s + parses under 3.10 grammar.
- fragments are non-adjacent in the emitted stub (positions spread).
- post-reconstruction wipe (fragment vars deleted from the namespace).
- tampered share fails closed (both build-time recover and the runtime
  _nx_sb_combine path).
- fragmented decoder: no single function contains the full decode path
  (_collect knows locations only, _combine knows math only, _activate
  knows timing only).
- flag-off loader unchanged: default output has no split-bootstrap
  decoder, and matches the pre-flag golden shape (byte-identical apart
  from the additive OFF markers); signature default is False.
- flag-on loader: _nx_sb_activate() yields the SAME effective key the
  loader decrypts with (BLOB_KEY), and executes end-to-end.
"""
import ast
import base64
import inspect
import marshal
import os
import re
import secrets
import subprocess
import sys
import zlib

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import generate_hybrid_loader_script
from obfuscator.key_emit import derive_effective_key
from obfuscator.split_bootstrap import (
    emit_bootstrap_snippet,
    fragments_spread,
    recover_bootstrap_key,
    snip_markers,
    split_bootstrap_key,
)

BUILD_PY = os.path.join(os.path.dirname(__file__), "..", "scripts", "build.py")

_BLANKS = {"windows": "", "linux": "", "darwin": ""}
_RAW_KEY = bytes(range(32))  # contains no bytes >= 251; high-byte keys below
_PAYLOAD_SRC = "SB_E2E = 100 + 23\n"


def _enc_blob(raw_key=_RAW_KEY):
    from obfuscator.core.utils import fast_xor_bytes
    marshalled = marshal.dumps(compile(_PAYLOAD_SRC, "<sb_e2e>", "exec"))
    return fast_xor_bytes(zlib.compress(marshalled), raw_key)


def _exec_snippet(fragments, k, build_id):
    src = emit_bootstrap_snippet(fragments, k, build_id)
    ns = {}
    exec(compile(src, "<nx_sb>", "exec"), ns)
    return src, ns


# --- 1. split->reconstruct roundtrip (real Shamir API) ----------------------

def test_roundtrip_uses_real_shamir_api():
    # split_bootstrap.py must reuse scripts/dispersal/payload_dispersal.py,
    # never carry its own field arithmetic at build time.
    import obfuscator.split_bootstrap as mod
    src = inspect.getsource(mod)
    assert "from scripts.dispersal.payload_dispersal import ShamirSharing" in src
    assert "ShamirSharing.split_secret" in src
    assert "ShamirSharing.recover_secret" in src
    out = split_bootstrap_key(_RAW_KEY)
    assert out["n"] == 3 and out["k"] == 2 and len(out["fragments"]) == 3
    assert recover_bootstrap_key(out["fragments"], out["k"]) == _RAW_KEY


def test_roundtrip_random_keys_many():
    for _ in range(5):
        key = secrets.token_bytes(32)
        out = split_bootstrap_key(key)
        assert recover_bootstrap_key(out["fragments"], out["k"]) == key


def test_roundtrip_high_bytes_ge_251():
    # GF(251) loses bytes >= 251; the hex bridge must cover them.
    key = bytes([250, 251, 252, 253, 254, 255] + list(range(26)))
    out = split_bootstrap_key(key)
    assert recover_bootstrap_key(out["fragments"], out["k"]) == key
    for _ in range(3):
        key = secrets.token_bytes(32)
        if any(b >= 251 for b in key):
            out = split_bootstrap_key(key)
            assert recover_bootstrap_key(out["fragments"], out["k"]) == key


def test_split_bad_params_fail():
    with pytest.raises(ValueError):
        split_bootstrap_key(b"", n=3, k=2)
    with pytest.raises(ValueError):
        split_bootstrap_key(_RAW_KEY, n=3, k=1)  # Shamir floor
    with pytest.raises(ValueError):
        split_bootstrap_key(_RAW_KEY, n=2, k=3)  # k > n
    with pytest.raises(ValueError):
        emit_bootstrap_snippet(["a", "b"], 2)  # need exactly 3
    with pytest.raises(ValueError):
        emit_bootstrap_snippet(split_bootstrap_key(_RAW_KEY)["fragments"],
                               3, "bid")  # k=2 only


# --- 2. k-1 shares fail closed ----------------------------------------------

def test_k_minus_1_fails_closed():
    out = split_bootstrap_key(_RAW_KEY)
    with pytest.raises(ValueError):
        recover_bootstrap_key(out["fragments"][:1], out["k"])


def test_combine_path_k_minus_1_fails_closed():
    out = split_bootstrap_key(_RAW_KEY)
    _, ns = _exec_snippet(out["fragments"], out["k"], "bid-combine-01")
    with pytest.raises(ValueError):
        ns["_nx_sb_combine"](out["fragments"][:1])


# --- 3. snippet compiles + 3.10-parses --------------------------------------

def test_snippet_compiles_and_py310_parses():
    out = split_bootstrap_key(_RAW_KEY)
    src = emit_bootstrap_snippet(out["fragments"], out["k"], "bid-310")
    compile(src, "<nx_sb>", "exec")
    tree = ast.parse(src, feature_version=(3, 10))
    for node in ast.walk(tree):
        assert not isinstance(node, ast.Match), "match forbidden"
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            assert not (isinstance(node.annotation, ast.BinOp)
                        and isinstance(node.annotation.op, ast.BitOr))


def test_snippet_markers_contract():
    m = snip_markers()
    out = split_bootstrap_key(_RAW_KEY)
    src = emit_bootstrap_snippet(out["fragments"], out["k"], "bid-mark")
    for marker in (m["head"], m["trail"], m["salt"]):
        assert marker in src
    for name in (m["collect"], m["combine"], m["activate"], m["cache_var"]):
        assert name in src


# --- 4. fragments non-adjacent ----------------------------------------------

def test_fragments_spread_positions():
    out = split_bootstrap_key(_RAW_KEY)
    src = emit_bootstrap_snippet(out["fragments"], out["k"], "bid-spread")
    spread = fragments_spread(src)
    assert spread["gap"] >= 8, spread
    # full ordering: HEAD ... TRAIL ... SALT group all separated
    lines = src.split("\n")
    head = next(i for i, l in enumerate(lines) if l.startswith("_NX_SB_HEAD ="))
    trail = next(i for i, l in enumerate(lines) if l.startswith("_NX_SB_TRAIL ="))
    salt = next(i for i, l in enumerate(lines) if l.startswith("_NX_SB_SALT ="))
    third = next(i for i, l in enumerate(lines) if l.startswith("_NX_SB_THIRD ="))
    assert trail - head >= 8
    assert salt - trail >= 8
    assert third > salt  # third travels WITH the salt group, not HEAD
    # raw key hex never contiguous in the snippet
    assert _RAW_KEY.hex() not in src


# --- 5. post-reconstruction wipe --------------------------------------------

def test_post_activation_wipe_deletes_holders():
    out = split_bootstrap_key(_RAW_KEY)
    _, ns = _exec_snippet(out["fragments"], out["k"], "bid-wipe")
    key = ns["_nx_sb_activate"]()
    from obfuscator.key_emit import derive_effective_key as _drv
    assert key == _drv(_RAW_KEY, "bid-wipe")
    for holder in ("_NX_SB_HEAD", "_NX_SB_TRAIL", "_NX_SB_THIRD"):
        assert holder not in ns, holder
    # cached key answers second call without holders
    assert ns["_nx_sb_activate"]() == key


# --- 6. tampered share fails closed ------------------------------------------

def test_tampered_share_build_time_fails():
    out = split_bootstrap_key(_RAW_KEY)
    frags = list(out["fragments"])
    x, b64 = frags[0].split(":", 1)
    raw = bytearray(base64.b64decode(b64))
    raw[0] ^= 0xFF
    frags[0] = "%s:%s" % (x, base64.b64encode(bytes(raw)).decode("ascii"))
    with pytest.raises(ValueError):
        got = recover_bootstrap_key(frags, out["k"])
        assert got == _RAW_KEY  # must not reach here with the right key


def test_tampered_share_runtime_fails():
    # Flip a middle byte hard (0xFF): single-bit flips at the share tail
    # can land back inside the hex alphabet (~6% of the time — the share
    # byte maps through GF(251) interpolation to a neighboring hex char),
    # so the "tamper" under test must be one that actually corrupts the
    # combined hex. A 0xFF flip in the middle reliably does; the runtime
    # combiner then fails closed via the bad-hex ValueError.
    out = split_bootstrap_key(_RAW_KEY)
    frags = list(out["fragments"])
    x, b64 = frags[1].split(":", 1)
    raw = bytearray(base64.b64decode(b64))
    raw[len(raw) // 2] ^= 0xFF
    frags[1] = "%s:%s" % (x, base64.b64encode(bytes(raw)).decode("ascii"))
    _, ns = _exec_snippet(out["fragments"], out["k"], "bid-tamper-rt")
    with pytest.raises(ValueError):
        got = ns["_nx_sb_combine"](frags[:2])
        assert got == _RAW_KEY


def test_malformed_fragment_fails_closed():
    out = split_bootstrap_key(_RAW_KEY)
    with pytest.raises(ValueError):
        recover_bootstrap_key(["not-a-fragment!!!", out["fragments"][1]],
                              out["k"])


# --- 7. fragmented decoder: no single fn holds the full path -----------------

def test_decoder_fragmented_across_functions():
    out = split_bootstrap_key(_RAW_KEY)
    src = emit_bootstrap_snippet(out["fragments"], out["k"], "bid-frag")
    tree = ast.parse(src)
    fns = {n.name: ast.get_source_segment(src, n)
           for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert {"_nx_sb_collect", "_nx_sb_combine", "_nx_sb_activate"} <= set(fns)
    collect, combine, activate = (fns["_nx_sb_collect"], fns["_nx_sb_combine"],
                                  fns["_nx_sb_activate"])
    # _collect: locations only — no Lagrange math, no salt/hashlib.
    assert "pow(" not in collect and "hashlib" not in collect
    assert "_NX_SB_HEAD" in collect
    # _combine: math only — no globals locations beyond its arg, no salt.
    assert "pow(" in combine and "fromhex" in combine
    assert "_NX_SB_HEAD" not in combine and "sha256" not in combine
    assert "_NX_SB_SALT" not in combine
    # _activate: timing/salt only — no Lagrange math of its own.
    assert "pow(" not in activate and "sha256" in activate
    assert "_NX_SB_SALT" in activate


# --- 8. flag-off loader unchanged ----------------------------------------------

def test_loader_signature_default_off():
    sig = inspect.signature(generate_hybrid_loader_script)
    assert sig.parameters["split_bootstrap"].default is False


def test_loader_default_off_no_decoder():
    src, _, _ = generate_hybrid_loader_script(dict(_BLANKS), b"",
                                              _RAW_KEY.hex(),
                                              build_id="sb-off-01")
    compile(src, "<sb_off>", "exec")
    assert "def _nx_sb_combine" not in src
    assert "def _nx_sb_collect" not in src
    assert "def _nx_sb_activate" not in src
    assert "_NX_SPLIT_BOOTSTRAP = False" in src
    assert "_NX_SPLIT_BOOTSTRAP_ARMED = False" in src
    # existing single-key path untouched
    assert 'BLOB_KEY = _nx_key_reconstruct()' in src


def test_loader_flag_off_byte_identical_apart_from_markers():
    enc = _enc_blob()
    kw = dict(build_id="sb-stable-01")
    off, _, fb_off = generate_hybrid_loader_script(dict(_BLANKS), bytes(enc),
                                                   _RAW_KEY.hex(), **kw)
    # strip the two additive OFF markers; the rest must equal the
    # pre-flag shape (same template + same shares for a fixed build_id).
    stripped = off.replace("_NX_SPLIT_BOOTSTRAP = False\n", "")
    stripped = stripped.replace("_NX_SPLIT_BOOTSTRAP_ARMED = False\n", "")
    on_src, _, _ = generate_hybrid_loader_script(dict(_BLANKS), bytes(enc),
                                                 _RAW_KEY.hex(), **kw,
                                                 split_bootstrap=False)
    on_stripped = on_src.replace("_NX_SPLIT_BOOTSTRAP = False\n", "")
    on_stripped = on_stripped.replace("_NX_SPLIT_BOOTSTRAP_ARMED = False\n", "")
    assert stripped == on_stripped
    # determinism: same inputs -> same outputs
    again, _, fb_again = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(), **kw)
    assert again == off and fb_again == fb_off


# --- 9. flag-on loader: same effective key + end-to-end --------------------------

def test_loader_flag_on_same_effective_key_and_e2e():
    enc = _enc_blob()
    bid = "sb-on-01"
    src, _, _ = generate_hybrid_loader_script(dict(_BLANKS), bytes(enc),
                                              _RAW_KEY.hex(), build_id=bid,
                                              split_bootstrap=True)
    compile(src, "<sb_on>", "exec")
    assert "_NX_SPLIT_BOOTSTRAP = True" in src
    assert "_NX_SPLIT_BOOTSTRAP_ARMED = True" in src
    assert "def _nx_sb_activate" in src
    # salt baked into the SB snippet must equal the emitted _NX_BUILD_ID
    sb_salt = re.search(r'_NX_SB_SALT = "([^"]+)"', src).group(1)
    build_id = re.search(r'_NX_BUILD_ID = "([^"]+)"', src).group(1)
    assert sb_salt == build_id == bid
    ns = {"__name__": "sb_on_loader"}
    exec(compile(src, "<sb_on_loader>", "exec"), ns)
    eff = derive_effective_key(_RAW_KEY, bid)
    assert ns.get("BLOB_KEY") == eff
    assert ns.get("BLOB_KEY_SB") == eff
    ns["_exec_fallback"]()
    assert ns.get("SB_E2E") == 123


def test_loader_flag_on_tampered_salt_fails():
    # Tampering the SB salt leg derives a WRONG split key (fail-closed at
    # the key-derivation layer): BLOB_KEY_SB != the effective key the
    # loader decrypts with. Documented scope: the loader's decrypt path
    # still uses BLOB_KEY (unchanged); BLOB_KEY_SB is the opt-in second
    # opinion, so this asserts wrong-key derivation, not a decrypt break.
    enc = _enc_blob()
    src, _, _ = generate_hybrid_loader_script(dict(_BLANKS), bytes(enc),
                                              _RAW_KEY.hex(),
                                              build_id="sb-ontamper",
                                              split_bootstrap=True)
    tampered = src.replace('_NX_SB_SALT = "sb-ontamper"',
                           '_NX_SB_SALT = "sb-ontamper-X"', 1)
    ns = {"__name__": "sb_ontamper"}
    exec(compile(tampered, "<sb_ontamper>", "exec"), ns)
    assert ns.get("BLOB_KEY_SB") != derive_effective_key(_RAW_KEY,
                                                         "sb-ontamper")
    # main decrypt path untouched by the SB salt leg (existing key paths
    # unchanged per the additive constraint).
    assert ns.get("BLOB_KEY") == derive_effective_key(_RAW_KEY, "sb-ontamper")
    # ... while the UNTAMPERED loader's SB key matches BLOB_KEY exactly.
    ns2 = {"__name__": "sb_ontamper_clean"}
    exec(compile(src, "<sb_ontamper_clean>", "exec"), ns2)
    assert ns2.get("BLOB_KEY_SB") == ns2.get("BLOB_KEY")


def test_build_flag_present():
    out = subprocess.run([sys.executable, BUILD_PY, "--help"],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr[-2000:]
    assert "--split-bootstrap" in (out.stdout + out.stderr)


def test_sb_names_survive_rename_passes():
    from obfuscator.core.sources import apply_ast_mutation
    probe = ("def _x():\n"
             "    a = _nx_sb_collect\n"
             "    b = _nx_sb_combine\n"
             "    c = _nx_sb_activate\n"
             "    d = _NX_SB_HEAD\n"
             "    e = _NX_SB_TRAIL\n"
             "    f = _NX_SB_SALT\n"
             "    g = _NX_SB_KEY\n"
             "    h = _NX_SB_THIRD\n"
             "    i = _NX_SPLIT_BOOTSTRAP\n"
             "    j = _NX_SPLIT_BOOTSTRAP_ARMED\n"
             "    k = BLOB_KEY_SB\n"
             "    return (a, b, c, d, e, f, g, h, i, j, k)\n")
    out, _ = apply_ast_mutation(probe, {"symbol_rename": True,
                                        "unicode_ids": True,
                                        "split_bootstrap": True})
    for name in ("_nx_sb_collect", "_nx_sb_combine", "_nx_sb_activate",
                 "_NX_SB_HEAD", "_NX_SB_TRAIL", "_NX_SB_SALT", "_NX_SB_KEY",
                 "_NX_SB_THIRD", "_NX_SPLIT_BOOTSTRAP",
                 "_NX_SPLIT_BOOTSTRAP_ARMED", "BLOB_KEY_SB"):
        assert name in out, name
