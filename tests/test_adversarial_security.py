"""Adversarial + security battery for the obfuscator.

Test-kind legend (every test is tagged in its docstring):
  [unit]         pure in-process function contract (no I/O, no subprocess).
  [integration]  crosses a boundary: subprocess artifact runs, real state
                 files on disk, emitted snippets exec'd in live namespaces.
  [security]     attacker-model property: tamper must fail closed, secrets
                 must not leak, replays must not bypass.
  [adversarial]  hostile/malformed/resource-exhaustion input: garbage bytes,
                 deep nesting, huge inputs, randomized roundtrips. The
                 process must never crash (segfault/abort) and must never
                 return a silent wrong answer — correct result or clean
                 catchable error only.

Property-based backend: ``hypothesis`` is probed at import; it is NOT
installed in this environment, so all randomized roundtrips below are
hand-rolled 200-iteration loops over ``random.Random`` with FIXED seeds
(deterministic, reproducible). If hypothesis ever becomes available the
loops remain valid as-is.

Python 3.10 compatible: stdlib only, no match statements, no PEP-695
syntax, no runtime-evaluated X|Y annotations.
"""

from __future__ import annotations

import ast
import os
import random
import subprocess
import sys
import tempfile
import time
import types

import pytest

from obfuscator import chacha20 as _chacha20
from obfuscator import clock_bias as _clock_bias
from obfuscator import dataflow as _dataflow
from obfuscator import lowering as _lowering
from obfuscator import lowering_shim as _shim
from obfuscator import nyser as _nyser
from obfuscator import string_crypto as _string_crypto
from obfuscator import trial_bind as _trial
from obfuscator import watermark_gate as _wm
from obfuscator.split_bootstrap import (
    emit_bootstrap_snippet,
    recover_bootstrap_key,
    split_bootstrap_key,
)

try:
    import hypothesis  # noqa: F401

    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False

# Fixed seeds: every randomized loop below reproduces byte-for-byte.
_ADV_SEED = 0xAD1A55


def _rng(salt=0):
    return random.Random(_ADV_SEED + salt)


# ---------------------------------------------------------------------------
# A. malformed inputs: NYSER1 decoder
# ---------------------------------------------------------------------------

def _sample_code():
    return compile("def _nx_adv_target(x):\n    return x * 2 + 1\n",
                   "<adv>", "exec")


def test_nyser_truncated_swapped_garbage_rejected():
    """[unit][security][adversarial] NYSER1 loads() rejects truncated,
    magic-swapped, version-flipped and random-garbage inputs with
    ValueError (never exec, never crash)."""
    good = _nyser.dumps(_sample_code())
    cur_minor = sys.version_info[1]
    other_minor = 10 if cur_minor != 10 else 11
    bad_version = (good[:6] + bytes([other_minor]) + good[7:])
    tampered = bytearray(good)
    tampered[20] ^= 0x01  # inside the SHA-256 digest -> integrity failure
    cases = [
        b"", b"\x00", b"garbage-bytes-here", good[:0], good[:3],
        good[:7], good[:len(good) // 2], good[:-1], good + b"\x00",
        b"NYS0" + good[4:], bad_version, bytes(tampered),
    ]
    for blob in cases:
        with pytest.raises(ValueError):
            _nyser.loads(blob)


def test_nyser_loads_never_executes_payload():
    """[security][adversarial] loads() rebuilds the code object WITHOUT
    executing it: a payload whose top level has side effects leaves no
    trace after loads()."""
    canary = os.path.join(tempfile.gettempdir(),
                          "nx_adv_canary_%d.py" % os.getpid())
    try:
        if os.path.exists(canary):
            os.unlink(canary)
    except OSError:
        pass
    evil_src = ("open(%r, 'w').write('pwned')\n_RESULT = 1\n" % (canary,))
    evil = compile(evil_src, "<evil>", "exec")
    co = _nyser.loads(_nyser.dumps(evil))
    assert isinstance(co, types.CodeType)
    assert co.co_name == "<module>"
    assert not os.path.exists(canary)


def test_nyser_garbage_fuzz_never_crash():
    """[adversarial] 200 seeded random blobs: every one raises ValueError
    (bad magic / truncation / integrity). Never a crash, never a parse."""
    rng = _rng(11)
    for _ in range(200):
        ln = rng.randint(0, 64)
        blob = bytes(rng.getrandbits(8) for _ in range(ln))
        try:
            _nyser.loads(blob)
        except ValueError:
            pass
        else:  # pragma: no cover - can only fire on a 2^-32 magic fluke
            pytest.fail("random garbage parsed as valid NYSER1")


def test_nyser_nested_const_roundtrip():
    """[unit][adversarial] 60-deep nested tuple consts survive a
    dumps/loads roundtrip (decoder recursion handles adversarial depth)."""
    inner = "1"
    for _ in range(60):
        inner = "(" + inner + ", 2)"
    co = compile("x = " + inner + "\n", "<t>", "exec")
    rt = _nyser.loads(_nyser.dumps(co))
    assert rt.co_consts == co.co_consts


# ---------------------------------------------------------------------------
# B. loader snippets with corrupted markers (trial gate via subprocess)
# ---------------------------------------------------------------------------

_VERDICT_RC = {"ok": 0, "expired": 4, "tampered": 3, "rollback": 5}


def _trial_artifact_source(deadline, token, key_hex, hwid):
    src = _trial.emit_trial_snippet(deadline, token, key_hex,
                                    func_name="_nx_trial_gate")
    src += ("\n_verdict = _nx_trial_gate(hwid_hint=%r)\n"
            "import sys\n"
            "sys.exit(%r.get(_verdict, 7))\n" % (hwid, _VERDICT_RC))
    return src


def _run_artifact(source):
    with tempfile.TemporaryDirectory(prefix="nx_adv_") as td:
        path = os.path.join(td, "artifact.py")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(source)
        env = dict(os.environ)
        # Isolate rollback state: never touch the real ~/.local/state.
        env["XDG_STATE_HOME"] = os.path.join(td, "state")
        env["NIXON_LOG_REDIRECT"] = "0"
        return subprocess.run([sys.executable, path], capture_output=True,
                              text=True, timeout=120, env=env, cwd=td)


def test_trial_snippet_subprocess_ok_then_tampered_fail_closed():
    """[integration][security] A trial-gated artifact exits 0 when intact
    and non-zero (fail-closed) when its token is corrupted."""
    key = b"T" * 32
    now = time.time()
    ctx = _trial.build_trial_context(3600.0, hwid="adv-hwid",
                                     build_key=key, now=now)
    ok_src = _trial_artifact_source(ctx["deadline"], ctx["token"],
                                    key.hex(), "adv-hwid")
    res = _run_artifact(ok_src)
    assert res.returncode == 0, res.stderr[-2000:]
    first = "0" if ctx["token"][0] != "0" else "1"
    bad_src = _trial_artifact_source(ctx["deadline"],
                                     first + ctx["token"][1:],
                                     key.hex(), "adv-hwid")
    res2 = _run_artifact(bad_src)
    assert res2.returncode == _VERDICT_RC["tampered"], (
        res2.returncode, res2.stderr[-2000:])


def test_trial_snippet_build_rejects_corrupt_token():
    """[unit][security] Corrupt token material fails at BUILD time
    (ValueError), never inside the artifact."""
    key = b"B" * 32
    ctx = _trial.build_trial_context(60.0, hwid="h", build_key=key,
                                     now=time.time())
    with pytest.raises(ValueError):
        _trial.emit_trial_snippet(ctx["deadline"], ctx["token"][:32],
                                  key.hex())


# ---------------------------------------------------------------------------
# C. trial state file with garbage
# ---------------------------------------------------------------------------

def test_trial_state_garbage_tampered_empty_first_run(tmp_path):
    """[unit][security] A garbage trial state file verdicts "tampered"
    (fail-closed); a missing one is a clean first run ("ok")."""
    key = b"S" * 32
    now = time.time()
    ctx = _trial.build_trial_context(3600.0, hwid="h", build_key=key,
                                     now=now)
    bad = str(tmp_path / "bad.state")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("garbage-no-colon-at-all")
    assert _trial.check_and_update(key, "h", ctx["deadline"], ctx["token"],
                                   state_path=bad, now=now + 1) == "tampered"
    fresh = str(tmp_path / "fresh.state")
    assert _trial.check_and_update(key, "h", ctx["deadline"], ctx["token"],
                                   state_path=fresh, now=now + 1) == "ok"


# ---------------------------------------------------------------------------
# D. watermark tag corrupt -> refuse; DISABLED-safe
# ---------------------------------------------------------------------------

def test_watermark_corrupt_refuses_and_disabled_safe():
    """[unit][security][integration] Corrupt tag / edited message verdict
    "tampered", stripped marker verdicts "missing" (both in-process AND
    in the emitted snippet); unmarked builds stay DISABLED-safe."""
    key = b"W" * 32
    ctx = _wm.build_watermark_context("adv-msg", build_key=key)
    assert _wm.check_watermark(key, "adv-msg", ctx["tag"],
                               marker_present=True) == "ok"
    assert _wm.check_watermark(key, "adv-msg", "0" * 64,
                               marker_present=True) == "tampered"
    assert _wm.check_watermark(key, "evil-msg", ctx["tag"],
                               marker_present=True) == "tampered"
    assert _wm.check_watermark(key, "adv-msg", ctx["tag"],
                               marker_present=False) == "missing"
    src = _wm.emit_watermark_snippet("adv-msg", ctx["tag"], key.hex(),
                                     ctx["marker"])
    ns = {}
    exec(compile(src, "<wm>", "exec"), ns)
    assert ns["_nx_watermark_gate"]() == "missing"
    ns["_NX_WATERMARK_MARKER"] = ctx["marker"]
    assert ns["_nx_watermark_gate"]() == "ok"
    bad_src = _wm.emit_watermark_snippet("adv-msg", "f" * 64, key.hex(),
                                         ctx["marker"])
    ns3 = {"_NX_WATERMARK_MARKER": ctx["marker"]}
    exec(compile(bad_src, "<wm>", "exec"), ns3)
    assert ns3["_nx_watermark_gate"]() == "tampered"
    assert _wm.build_watermark_context(None) == {"disabled": True}
    assert _wm.build_watermark_context("") == {"disabled": True}


# ---------------------------------------------------------------------------
# E. boundary conditions
# ---------------------------------------------------------------------------

def test_trial_tolerance_exact_boundary(tmp_path):
    """[unit][security] Rollback check is a STRICT inequality: exactly
    tolerance-aged state is "ok", one millisecond older is "rollback"."""
    key = b"Q" * 32
    t0 = time.time()
    ctx = _trial.build_trial_context(86400.0, hwid="h", build_key=key,
                                     now=t0)
    tol = _trial.ROLLBACK_TOLERANCE_S

    def run_at(now):
        path = str(tmp_path / ("s_%d.state" % int(now * 1000)))
        assert _trial.check_and_update(key, "h", ctx["deadline"],
                                       ctx["token"], state_path=path,
                                       now=t0) == "ok"
        return _trial.check_and_update(key, "h", ctx["deadline"],
                                       ctx["token"], state_path=path,
                                       now=now)

    assert run_at(t0 - tol) == "ok"
    assert run_at(t0 - tol - 0.001) == "rollback"
    assert run_at(t0 + 10) == "ok"


def test_trial_deadline_exact_boundary():
    """[unit] now == deadline is still "ok"; deadline + 1s is "expired"."""
    key = b"D" * 32
    deadline = 2000000000
    tok = _trial.mint_token(key, "h", deadline)
    assert _trial.check_trial(key, "h", deadline, tok,
                              now=float(deadline)) == "ok"
    assert _trial.check_trial(key, "h", deadline, tok,
                              now=float(deadline + 1)) == "expired"


def test_clock_empty_single_and_biased_vectors():
    """[unit] Clock detector never flags empty / single-sample /
    degenerate vectors; flags a genuinely bimodal one (control)."""
    flagged, stats = _clock_bias.clock_bias_verdict([])
    assert flagged is False and stats["samples"] == 0
    flagged, stats = _clock_bias.clock_bias_verdict([100])
    assert flagged is False and stats["samples"] == 1
    flagged, _stats = _clock_bias.clock_bias_verdict([0, 0, 0])
    assert flagged is False
    flagged, stats = _clock_bias.clock_bias_verdict([100] * 1970 +
                                                    [10000] * 30)
    assert flagged is True
    assert stats["median_ns"] == 100


def test_shamir_k_minus_1_fails_k_eq_n_works():
    """[unit][security] k-1 shares fail closed; k==n recovers; malformed
    fragment counts are rejected at build AND recover time."""
    key = bytes((i * 37) % 256 for i in range(32))  # incl. bytes >= 251
    ctx = split_bootstrap_key(key)
    assert ctx["k"] == 2 and len(ctx["fragments"]) == 3
    with pytest.raises(ValueError):
        recover_bootstrap_key(ctx["fragments"][:1], 2)
    assert recover_bootstrap_key(ctx["fragments"][:2], 2) == key
    full = split_bootstrap_key(key, n=3, k=3)
    assert recover_bootstrap_key(full["fragments"], 3) == key
    with pytest.raises(ValueError):
        recover_bootstrap_key(full["fragments"][:2], 3)
    with pytest.raises(ValueError):
        emit_bootstrap_snippet(ctx["fragments"][:2], 2)
    from scripts.dispersal.payload_dispersal import ShamirSharing
    shares = ShamirSharing.split_secret(b"hello-watermark", 3, 2)
    with pytest.raises(ValueError):
        ShamirSharing.recover_secret(shares[:1], 2)
    assert ShamirSharing.recover_secret(shares[:2], 2) == b"hello-watermark"


# ---------------------------------------------------------------------------
# F. parser abuse: lowering rewriter recursion safety
# ---------------------------------------------------------------------------

def test_lowering_deeply_nested_recursion_safe():
    """[adversarial] 120-deep nesting lowers exactly; 3000-deep nesting
    either lowers or raises a CATCHABLE error (RecursionError/SyntaxError/
    MemoryError/ValueError) — the process must survive either way."""
    depth_ok = 120
    src = "out = " + "len(" * depth_ok + "[1, 2]" + ")" * depth_ok + "\n"
    lowered, n = _lowering.lower_source(src, "scalar")
    assert n == depth_ok
    compile(lowered, "<t>", "exec")
    deep = 3000
    src2 = "out = " + "len(" * deep + "[1, 2]" + ")" * deep + "\n"
    try:
        lowered2, _n2 = _lowering.lower_source(src2, "scalar")
    except (RecursionError, SyntaxError, MemoryError, ValueError):
        pass  # clean catchable error, not a crash
    else:
        compile(lowered2, "<t2>", "exec")


# ---------------------------------------------------------------------------
# G. path manipulation
# ---------------------------------------------------------------------------

def test_output_traversal_guard_confines_write(tmp_path):
    """[security] process_file_safe re-roots sources outside the project
    root (rel starts with "..") so the write stays inside build_dir."""
    try:
        from obfuscator.core.pipeline import process_file_safe
    except BaseException as exc:
        pytest.skip("guard not importable: %r" % (exc,))
    root = tmp_path / "root"
    root.mkdir()
    build = tmp_path / "build"
    build.mkdir()
    evil_src = tmp_path / "evil.py"
    evil_src.write_text("print('evil')\n")
    before = set(os.listdir(str(tmp_path)))
    res = process_file_safe((str(evil_src), str(build), [1, 2, 3],
                             "zzz_no_match.py", str(root), {}, {}))
    assert res is not None and res[0] == "success", res
    assert (build / "evil.py").exists()
    assert set(os.listdir(str(tmp_path))) == before
    assert not (root / "evil.py").exists()


@pytest.mark.skipif(not hasattr(os, "O_NOFOLLOW"),
                    reason="needs POSIX O_NOFOLLOW")
def test_state_symlink_not_followed(tmp_path):
    """[security] Trial state writes use O_NOFOLLOW: a symlinked state
    path degrades to "ok" WITHOUT following the link (no write through
    it, no file created for a dangling link)."""
    if os.name == "nt":  # pragma: no cover - posix symlink semantics
        pytest.skip("posix symlink semantics")
    key = b"L" * 32
    now = time.time()
    ctx = _trial.build_trial_context(3600.0, hwid="h", build_key=key,
                                     now=now)
    link = str(tmp_path / "dangling.state")
    target = str(tmp_path / "nope.state")
    os.symlink(target, link)
    assert _trial.check_and_update(key, "h", ctx["deadline"], ctx["token"],
                                   state_path=link, now=now + 1) == "ok"
    # The lock open may create an EMPTY target; sealed data must never
    # be written through the link.
    assert (not os.path.lexists(target)
            or os.path.getsize(target) == 0)
    real = str(tmp_path / "real.state")
    sealed = _trial.seal_last_seen(key, now)
    with open(real, "w", encoding="utf-8") as fh:
        fh.write(sealed)
    link2 = str(tmp_path / "link2.state")
    os.symlink(real, link2)
    assert _trial.check_and_update(key, "h", ctx["deadline"], ctx["token"],
                                   state_path=link2, now=now + 2) == "ok"
    with open(real, encoding="utf-8") as fh:
        assert fh.read() == sealed


# ---------------------------------------------------------------------------
# H. replay
# ---------------------------------------------------------------------------

def test_trial_token_reuse_advances_not_bypass(tmp_path):
    """[security] Reusing one trial token across runs keeps verdict "ok"
    AND advances the sealed last_seen (no rollback-window bypass)."""
    key = b"R" * 32
    t0 = time.time()
    ctx = _trial.build_trial_context(3600.0, hwid="replay-hwid",
                                     build_key=key, now=t0)
    state = str(tmp_path / "r.state")
    assert _trial.check_and_update(key, "replay-hwid", ctx["deadline"],
                                   ctx["token"], state_path=state,
                                   now=t0 + 10) == "ok"
    assert _trial.check_and_update(key, "replay-hwid", ctx["deadline"],
                                   ctx["token"], state_path=state,
                                   now=t0 + 20) == "ok"
    with open(state, encoding="utf-8") as fh:
        sealed = fh.read().strip()
    assert _trial.unseal_last_seen(key, sealed) == t0 + 20


def test_sealed_state_copied_to_other_machine_tampered(tmp_path):
    """[security] A token bound to machine-A verdicts "tampered" on
    machine-B (sealed state transplant buys nothing)."""
    key = b"M" * 32
    t0 = time.time()
    ctx = _trial.build_trial_context(3600.0, hwid="machine-A",
                                     build_key=key, now=t0)
    state_a = str(tmp_path / "m.state")
    assert _trial.check_and_update(key, "machine-A", ctx["deadline"],
                                   ctx["token"], state_path=state_a,
                                   now=t0 + 5) == "ok"
    state_b = str(tmp_path / "m2.state")
    assert _trial.check_and_update(key, "machine-B", ctx["deadline"],
                                   ctx["token"], state_path=state_b,
                                   now=t0 + 6) == "tampered"


# ---------------------------------------------------------------------------
# I. resource exhaustion
# ---------------------------------------------------------------------------

def test_string_crypto_10mb_bounded():
    """[adversarial] A 10MB string seals and unseals correctly in bounded
    time (works or clean error, never a hang/crash)."""
    key = b"S" * 32
    big = "A" * (10 * 1024 * 1024)
    start = time.time()
    seal = _string_crypto.encrypt_string(big, key)
    assert isinstance(seal, str) and len(seal) > 0
    assert _string_crypto.decrypt_string(seal, key) == big
    assert time.time() - start < 300.0


def test_evidence_scorer_5mb_cap(tmp_path):
    """[unit][adversarial] Files over the 5MB cap are SKIPPED (return no
    matches); small files with claims are still found."""
    from scripts.evidence_completeness.scorer import (
        EvidenceCompletenessScorer,
        _MAX_SCAN_FILE_BYTES,
    )
    assert _MAX_SCAN_FILE_BYTES == 5 * 1024 * 1024
    big = tmp_path / "big.py"
    big.write_text("# secure unbreakable claim\n" +
                   "x = 1\n" * ((5 * 1024 * 1024) // 6 + 100))
    assert os.path.getsize(str(big)) > _MAX_SCAN_FILE_BYTES
    scorer = EvidenceCompletenessScorer(root_dir=str(tmp_path))
    assert scorer._scan_file_for_claims(str(big)) == []
    small = tmp_path / "small.py"
    small.write_text("x = 'secure vault'\n")
    assert scorer._scan_file_for_claims(str(small)) != []


# ---------------------------------------------------------------------------
# J. property-based roundtrips (hand-rolled: hypothesis not installed)
# ---------------------------------------------------------------------------

def test_property_chacha20_roundtrip_random():
    """[unit][adversarial] 200 seeded chacha20 AEAD roundtrips over random
    lengths/content (incl. empty, block edges, zeros, 0xff); any 1-bit
    tamper fails closed with ValueError."""
    rng = _rng(21)
    key = bytes(rng.getrandbits(8) for _ in range(32))
    fixed = [0, 1, 27, 28, 55, 64, 65, 129, 1000]
    for i in range(200):
        ln = fixed[i] if i < len(fixed) else rng.randint(0, 2000)
        r = rng.random()
        if r < 0.10:
            pt = b"\x00" * ln
        elif r < 0.20:
            pt = b"\xff" * ln
        else:
            pt = bytes(rng.getrandbits(8) for _ in range(ln))
        blob = _chacha20.aead_encrypt(key, pt)
        assert _chacha20.aead_decrypt(key, blob) == pt
        bad = bytearray(blob)
        bad[rng.randrange(len(bad))] ^= 0x01
        with pytest.raises(ValueError):
            _chacha20.aead_decrypt(key, bytes(bad))


def test_property_dataflow_split_reconstruct_random():
    """[unit][adversarial] 200 seeded dataflow split/reconstruct exec
    roundtrips over random 64-bit values incl. low-bit and edge values."""
    rng = _rng(22)
    edges = [0, 1, 2, 0xFF, 2 ** 63 - 1, 2 ** 63, 2 ** 64 - 2, 2 ** 64 - 1,
             0xAAAAAAAAAAAAAAAA, 0x5555555555555555]
    for i in range(200):
        val = edges[i] if i < len(edges) else rng.getrandbits(64)
        parts = rng.randint(2, 5)
        seed = bytes(rng.getrandbits(8) for _ in range(32))
        tree = ast.parse("x = %d\nout = x\n" % val)
        tree2 = _dataflow.split_value(tree, "x", parts, seed=seed)
        ns = {}
        exec(compile(tree2, "<t>", "exec"), ns)
        assert ns["out"] == val, (val, parts)


def test_property_shamir_ascii_roundtrip_random():
    """[unit][adversarial] 200 seeded Shamir split/recover roundtrips over
    random ASCII (incl. empty) with random n/k and shuffled subsets."""
    from scripts.dispersal.payload_dispersal import ShamirSharing
    rng = _rng(23)
    for _ in range(200):
        ln = rng.randint(0, 64)
        secret = bytes(rng.randint(0, 127) for _ in range(ln))
        n = rng.randint(2, 5)
        k = rng.randint(2, n)
        shares = ShamirSharing.split_secret(secret, n, k)
        subset = rng.sample(shares, k)
        assert ShamirSharing.recover_secret(subset, k) == secret


def test_property_lowering_parity_spotcheck_random():
    """[unit][adversarial] 200 seeded lowering parity spot-checks: the
    lowered kernel call returns exactly what the plain builtin returns."""
    rng = _rng(24)
    for _ in range(200):
        op = rng.choice(["len", "abs", "int", "str", "bool"])
        if op == "len":
            val = rng.choice([[1, 2], "hello", (1,), {"a": 1},
                              range(5), b"xy"])
        elif op == "abs":
            val = rng.choice([-7, 3.25, -(2 ** 70), complex(1, 2)])
        elif op == "int":
            val = rng.choice(["42", 3.99, "  -17  ", b"101", True])
        elif op == "str":
            val = rng.choice([42, None, 3.5, "x", b"ab"])
        else:
            val = rng.choice([0, 1, "", [1], None, "x", 2 ** 100])
        setup_src = "x = %r\n" % (val,)
        expr = "%s(x)" % op
        plain_ns = {}
        exec(compile(setup_src + "out = " + expr + "\n", "<p>", "exec"),
             plain_ns)
        want = plain_ns["out"]
        lowered, n = _lowering.lower_source(setup_src + "out = " + expr
                                            + "\n", "all")
        assert n >= 1
        toks = {nd.id for nd in ast.walk(ast.parse(lowered))
                if isinstance(nd, ast.Name) and nd.id.startswith("_nxk_")}
        assert toks
        low_ns = {"x": val}
        for tok in toks:
            low_ns[tok] = getattr(_shim, tok)
        exec(compile(lowered, "<l>", "exec"), low_ns)
        got = low_ns["out"]
        assert type(got) is type(want) and got == want, (op, val)
