"""AUDIT GAPS #52/#75: trial deadline MAC-bound + clock-rollback detection.

Unit + end-to-end coverage for obfuscator/trial_bind.py and its wiring
into generate_hybrid_loader_script:

- parse_trial units still work (macros contract unchanged);
- token verifies on the same fingerprint, fails on a different one;
- tampered deadline fails;
- rollback (now < last_seen - tolerance) detected; small skew tolerated;
- loader markers: no --trial -> DISABLED gate; with trial -> gate that
  refuses expired/tampered payloads;
- end-to-end: obfuscate a snippet with a trial -> run -> works; expired
  trial -> non-zero exit.
"""
import marshal
import os
import re
import subprocess
import sys
import time
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import generate_hybrid_loader_script
from obfuscator.core.utils import fast_xor_bytes
from obfuscator.macros import parse_trial
from obfuscator.trial_bind import (
    ROLLBACK_TOLERANCE_S,
    build_trial_context,
    check_and_update,
    check_trial,
    compute_deadline,
    emit_trial_snippet,
    fallback_fingerprint,
    mint_token,
    resolve_fingerprint,
    seal_last_seen,
    unseal_last_seen,
    verify_token,
)

_BLANKS = {"windows": "", "linux": "", "darwin": ""}
_RAW_KEY = bytes(range(32))


# -- parse_trial units (contract must keep working) -----------------------

def test_trial_units_still_work():
    assert parse_trial("90s") == 90
    assert parse_trial("1w2d") == 7 * 86400 + 2 * 86400
    assert parse_trial("1mo1hr") == 30 * 86400 + 3600
    assert parse_trial("") is None
    assert parse_trial(None) is None


# -- token binding ---------------------------------------------------------

def test_token_verifies_same_fp():
    key = b"k" * 32
    fp = "HOST-1"
    deadline = compute_deadline(86400, now=1_700_000_000.0)
    token = mint_token(key, fp, deadline)
    assert verify_token(key, fp, deadline, token) is True
    assert check_trial(key, fp, deadline, token,
                       now=1_700_000_000.0 + 10) == "ok"


def test_token_fails_different_fp():
    key = b"k" * 32
    deadline = compute_deadline(86400, now=1_700_000_000.0)
    token = mint_token(key, "HOST-1", deadline)
    assert verify_token(key, "HOST-2", deadline, token) is False
    assert check_trial(key, "HOST-2", deadline, token,
                       now=1_700_000_000.0 + 10) == "tampered"


def test_tampered_deadline_fails():
    key = b"k" * 32
    fp = "HOST-1"
    deadline = compute_deadline(86400, now=1_700_000_000.0)
    token = mint_token(key, fp, deadline)
    # Attacker extends the deadline by a week without the key.
    assert verify_token(key, fp, deadline + 7 * 86400, token) is False
    assert check_trial(key, fp, deadline + 7 * 86400, token,
                       now=1_700_000_000.0 + 10) == "tampered"


def test_wrong_key_fails():
    fp = "HOST-1"
    deadline = compute_deadline(86400, now=1_700_000_000.0)
    token = mint_token(b"a" * 32, fp, deadline)
    assert check_trial(b"b" * 32, fp, deadline, token,
                       now=1_700_000_000.0) == "tampered"


def test_absolute_deadline_expired():
    key = b"k" * 32
    fp = "HOST-1"
    deadline = compute_deadline(60, now=1_700_000_000.0)
    token = mint_token(key, fp, deadline)
    assert check_trial(key, fp, deadline, token,
                       now=1_700_000_000.0 + 30) == "ok"
    assert check_trial(key, fp, deadline, token,
                       now=float(deadline) + 1) == "expired"


def test_resolve_fingerprint_prefers_hwid():
    assert resolve_fingerprint("EXPLICIT") == "EXPLICIT"
    fb = resolve_fingerprint("")
    assert fb == fallback_fingerprint()
    assert "|" in fb


def test_build_context_disabled_without_trial():
    assert build_trial_context(None) == {"disabled": True}


def test_build_context_roundtrip():
    ctx = build_trial_context(3600, hwid="H-9", now=1_700_000_000.0)
    assert ctx["fingerprint"] == "H-9"
    assert ctx["deadline"] == 1_700_000_000 + 3600
    assert check_trial(ctx["build_key"], "H-9", ctx["deadline"], ctx["token"],
                       now=1_700_000_000.0 + 5) == "ok"


# -- sealed last-seen + rollback -------------------------------------------

def test_seal_roundtrip_and_tamper():
    key = b"s" * 32
    sealed = seal_last_seen(key, 1_700_000_100.0)
    assert unseal_last_seen(key, sealed) == 1_700_000_100.0
    body, mac = sealed.rsplit(":", 1)
    bad = "%s:%s" % (repr(1_700_000_999.0), mac)
    try:
        unseal_last_seen(key, bad)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for tampered seal")
    try:
        unseal_last_seen(b"other" + b"\x00" * 27, sealed)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for wrong key")


def test_rollback_detected(tmp_path):
    key = b"r" * 32
    fp = "H"
    t0 = 1_700_000_000.0
    deadline = compute_deadline(86400, now=t0)
    token = mint_token(key, fp, deadline)
    state = str(tmp_path / "trial.state")
    assert check_and_update(key, fp, deadline, token, state_path=state,
                            now=t0) == "ok"
    # Forward progress is fine.
    assert check_and_update(key, fp, deadline, token, state_path=state,
                            now=t0 + 60) == "ok"
    # Rewinding the clock past tolerance -> rollback.
    assert check_and_update(key, fp, deadline, token, state_path=state,
                            now=t0 + 60 - ROLLBACK_TOLERANCE_S - 60) == "rollback"


def test_small_skew_tolerated(tmp_path):
    key = b"r" * 32
    fp = "H"
    t0 = 1_700_000_000.0
    deadline = compute_deadline(86400, now=t0)
    token = mint_token(key, fp, deadline)
    state = str(tmp_path / "trial2.state")
    assert check_and_update(key, fp, deadline, token, state_path=state,
                            now=t0) == "ok"
    # 60s backwards (NTP wobble) is within the 300s tolerance.
    assert check_and_update(key, fp, deadline, token, state_path=state,
                            now=t0 - 60) == "ok"


def test_tampered_state_file_fails_closed(tmp_path):
    key = b"r" * 32
    fp = "H"
    t0 = 1_700_000_000.0
    deadline = compute_deadline(86400, now=t0)
    token = mint_token(key, fp, deadline)
    state = str(tmp_path / "trial3.state")
    assert check_and_update(key, fp, deadline, token, state_path=state,
                            now=t0) == "ok"
    with open(state, "w", encoding="utf-8") as fh:
        fh.write("%s:%s" % (repr(t0 + 99999.0), "00" * 32))
    assert check_and_update(key, fp, deadline, token, state_path=state,
                            now=t0 + 10) == "tampered"


# -- emit snippet ----------------------------------------------------------

def test_emit_snippet_compiles_and_enforces(tmp_path, monkeypatch):
    key = b"e" * 32
    fp = "SNIPPET-HOST"
    deadline = compute_deadline(3600, now=time.time())
    token = mint_token(key, fp, deadline)
    src = emit_trial_snippet(deadline, token, key.hex())
    compile(src, "<trial_snippet>", "exec")
    # Point runtime state at a sandbox dir so tests never touch real
    # ~/.local/state.
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    ns = {"__name__": "trial_snippet_test", "sys": sys}
    exec(compile(src, "<trial_snippet>", "exec"), ns)
    gate = ns["_nx_trial_gate"]
    assert gate(fp) == "ok"
    assert gate("OTHER-HOST") == "tampered"
    assert gate(fp + "-x") == "tampered"


def test_emit_snippet_expired(monkeypatch, tmp_path):
    key = b"e" * 32
    fp = "SNIPPET-HOST"
    past = time.time() - 7200
    deadline = compute_deadline(3600, now=past)  # expired an hour ago
    token = mint_token(key, fp, deadline)
    src = emit_trial_snippet(deadline, token, key.hex())
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    ns = {"__name__": "trial_snippet_exp"}
    exec(compile(src, "<trial_snippet>", "exec"), ns)
    assert ns["_nx_trial_gate"](fp) == "expired"


def test_emit_snippet_rollback(monkeypatch, tmp_path):
    import time as _time
    key = b"e" * 32
    fp = "SNIPPET-HOST"
    deadline = compute_deadline(86400, now=_time.time())
    token = mint_token(key, fp, deadline)
    src = emit_trial_snippet(deadline, token, key.hex())
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    ns = {"__name__": "trial_snippet_rb"}
    exec(compile(src, "<trial_snippet>", "exec"), ns)
    gate = ns["_nx_trial_gate"]
    assert gate(fp) == "ok"
    # Simulate clock rewound by a day: monkeypatch time seen by snippet.
    real_time = _time.time
    monkeypatch.setattr("time.time", lambda: real_time() - 86400)
    # Re-exec snippet so its `import time` picks the patched module attr.
    ns2 = {"__name__": "trial_snippet_rb2"}
    exec(compile(src, "<trial_snippet>", "exec"), ns2)
    # First call after rewind reads the sealed future stamp -> rollback.
    assert ns2["_nx_trial_gate"](fp) == "rollback"


# -- loader wiring ----------------------------------------------------------

def test_loader_no_trial_disabled():
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANKS), b"", _RAW_KEY.hex(), build_id="trial-dis-01")
    compile(src, "<trial_dis>", "exec")
    assert "_NX_TRIAL_GATE = \"DISABLED\"" in src
    assert "_NX_TRIAL_SECONDS = None" in src


def test_loader_with_trial_has_gate(tmp_path, monkeypatch):
    enc = fast_xor_bytes(
        zlib.compress(marshal.dumps(
            compile("TRIAL_E2E = 6 * 7\n", "<trial_e2e>", "exec"))),
        _RAW_KEY)
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(),
        trial_seconds=86400, build_id="trial-on-01")
    compile(src, "<trial_on>", "exec")
    assert "_NX_TRIAL_SECONDS = 86400" in src or \
        "_NX_TRIAL_SECONDS = 86400.0" in src
    assert "def _nx_trial_gate" in src
    assert "_NX_TRIAL_DEADLINE" in src
    assert "_NX_TRIAL_TOKEN" in src
    m = re.search(r"_NX_TRIAL_TOKEN = '([0-9a-f]{64})'", src)
    assert m, "token literal missing"
    # Gate runs at import: sandbox state, then exec the loader module top.
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    ns = {"__name__": "trial_on_loader"}
    exec(compile(src, "<trial_on_loader>", "exec"), ns)
    assert ns.get("_NX_TRIAL_GATE") == "ok"
    ns["_exec_fallback"]()
    assert ns.get("TRIAL_E2E") == 42


def test_loader_expired_trial_refuses_import(tmp_path, monkeypatch):
    enc = fast_xor_bytes(
        zlib.compress(marshal.dumps(
            compile("SHOULD_NOT_RUN = 1\n", "<trial_exp>", "exec"))),
        _RAW_KEY)
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(),
        trial_seconds=86400, build_id="trial-exp-01")
    # Forge an already-expired deadline but keep a VALID token: recompute
    # the token for the past deadline with the embedded key.
    m_dead = re.search(r"_NX_TRIAL_DEADLINE = (\d+)", src)
    m_key = re.search(r"_NX_TRIAL_KEY = '([0-9a-f]+)'", src)
    assert m_dead and m_key
    key = bytes.fromhex(m_key.group(1))
    hint_m = re.search(r"_NX_TRIAL_HWID_HINT = '(.*?)'", src)
    fp = hint_m.group(1) if hint_m else ""
    if not fp:
        fp = fallback_fingerprint()
    past_deadline = int(time.time()) - 3600
    past_token = mint_token(key, fp, past_deadline)
    old_dead = m_dead.group(0)
    src = src.replace(old_dead,
                      "_NX_TRIAL_DEADLINE = %d" % (past_deadline,), 1)
    # The emitted gate snippet inlines the same literals at def time
    # (_tb_deadline = <int>, _tb_token = '<hex>'): patch those too.
    old_deadline_reprs = sorted(
        set(re.findall(r"%d" % (int(m_dead.group(1))), src)), key=len)
    src = src.replace("_tb_deadline = %s" % (m_dead.group(1),),
                      "_tb_deadline = %d" % (past_deadline,), 1)
    old_tok = re.search(r"_NX_TRIAL_TOKEN = '([0-9a-f]{64})'", src)
    old_tok_hex = old_tok.group(1)
    src = src.replace(old_tok.group(0),
                      "_NX_TRIAL_TOKEN = '%s'" % (past_token,), 1)
    src = src.replace("_tb_token = '%s'" % (old_tok_hex,),
                      "_tb_token = '%s'" % (past_token,), 1)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    import os as _os
    exited = {}

    def _fake_exit(code):
        exited["code"] = code
        raise SystemExit(code)

    monkeypatch.setattr(_os, "_exit", _fake_exit)
    ns = {"__name__": "trial_exp_loader"}
    try:
        exec(compile(src, "<trial_exp_loader>", "exec"), ns)
    except SystemExit as e:
        # Kill ladder: expired trial funnels through _nx_kill (silent,
        # exit 137 — os._exit patched in-process; SystemExit surfaces).
        assert exited.get("code") == 137, exited
        assert e.code == 137, e.code
        return
    raise AssertionError("expired trial should SystemExit at import")


# -- end-to-end: obfuscate snippet with trial -> run -> works ---------------
# NOTE: forging an "already expired" artifact in-test is brittle (it
# requires rewriting embedded literals); the expired path is instead
# covered non-zero-exit end-to-end by building a SHORT-lived trial
# artifact and running it with a faked future clock.  We do that by
# pre-seeding XDG_STATE_HOME (no-op) and monkeypatching time only in
# the PARENT for deadline computation... simpler: emit with a 1-second
# trial, sleep past it, then run -> artifact must exit non-zero with
# "expired" on stderr/stdout.

def _write_and_run_loader(payload_src, trial_seconds, workdir,
                          expect_ok=True):
    enc = fast_xor_bytes(
        zlib.compress(marshal.dumps(
            compile(payload_src, "<e2e>", "exec"))),
        _RAW_KEY)
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(),
        trial_seconds=trial_seconds, build_id="e2e-%d" % (trial_seconds or 0,))
    # The loader template only runs the payload via _load_native() under
    # __main__; call _exec_fallback() directly at the end (same pattern as
    # tests/test_build_id.py::_run_loader).
    src += "\n_ns_e2e_out = _exec_fallback()\n"
    target = os.path.join(str(workdir), "trial_artifact.py")
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(src)
    env = dict(os.environ)
    env["XDG_STATE_HOME"] = str(workdir)
    # NIXON CI bypass gate reads env live: ensure it cannot mask failures.
    env.pop("NIXON_VERIFY_SKIP_VERSION_CHECK", None)
    env.pop("NIXON_CI", None)
    env.pop("NIXON_ALLOW_SKIP", None)
    proc = subprocess.run([sys.executable, target],
                          capture_output=True, text=True, timeout=60,
                          cwd=str(workdir), env=env)
    return proc


def test_e2e_trial_run_works(tmp_path):
    proc = _write_and_run_loader(
        "print('TRIAL_OK_MARKER')\n", 86400, tmp_path)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "TRIAL_OK_MARKER" in proc.stdout


def test_e2e_no_trial_run_works(tmp_path):
    proc = _write_and_run_loader(
        "print('NOTRIAL_OK_MARKER')\n", None, tmp_path)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "NOTRIAL_OK_MARKER" in proc.stdout


def test_e2e_expired_trial_nonzero_exit(tmp_path):
    import time as _time
    enc = fast_xor_bytes(
        zlib.compress(marshal.dumps(
            compile("print('SHOULD_NOT_PRINT')\n", "<e2e_exp>", "exec"))),
        _RAW_KEY)
    # 1-second trial minted ~2s in the past -> already expired at runtime.
    past_base = _time.time() - 2.0
    ctx = build_trial_context(1, hwid="", now=past_base)
    from obfuscator import trial_bind as _tb
    src_snippet = _tb.emit_trial_snippet(
        int(ctx["deadline"]), str(ctx["token"]), bytes(ctx["build_key"]).hex())
    # Reuse the loader generator for the decrypt path, then swap its
    # trial block for our pre-expired one: simplest is to generate with
    # trial_seconds=1 and then replace the three literals + snippet defs.
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(),
        trial_seconds=1, build_id="e2e-exp-01")
    m_dead = re.search(r"_NX_TRIAL_DEADLINE = (\d+)", src)
    m_key = re.search(r"_NX_TRIAL_KEY = '([0-9a-f]+)'", src)
    m_tok = re.search(r"_NX_TRIAL_TOKEN = '([0-9a-f]{64})'", src)
    assert m_dead and m_key and m_tok
    src = src.replace(m_dead.group(0),
                      "_NX_TRIAL_DEADLINE = %d" % (int(ctx["deadline"]),), 1)
    src = src.replace(m_key.group(0),
                      "_NX_TRIAL_KEY = '%s'" % (
                          bytes(ctx["build_key"]).hex(),), 1)
    src = src.replace(m_tok.group(0),
                      "_NX_TRIAL_TOKEN = '%s'" % (str(ctx["token"]),), 1)
    src = src.replace("_tb_deadline = %s" % (m_dead.group(1),),
                      "_tb_deadline = %d" % (int(ctx["deadline"]),), 1)
    src = src.replace("_tb_token = '%s'" % (m_tok.group(1),),
                      "_tb_token = '%s'" % (str(ctx["token"]),), 1)
    src = src.replace("_tb_key = bytes.fromhex('%s')" % (m_key.group(1),),
                      "_tb_key = bytes.fromhex('%s')" % (
                          bytes(ctx["build_key"]).hex(),), 1)
    src += "\n_ns_e2e_out = _exec_fallback()\n"
    target = os.path.join(str(tmp_path), "trial_expired.py")
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(src)
    env = dict(os.environ)
    env["XDG_STATE_HOME"] = str(tmp_path)
    env.pop("NIXON_VERIFY_SKIP_VERSION_CHECK", None)
    env.pop("NIXON_CI", None)
    env.pop("NIXON_ALLOW_SKIP", None)
    proc = subprocess.run([sys.executable, target],
                          capture_output=True, text=True, timeout=60,
                          cwd=str(tmp_path), env=env)
    # Kill ladder: expired trial funnels through _nx_kill (silent,
    # exit 137, no output) — same shape as the migrated audit-hook and
    # watermark gates.
    assert proc.returncode == 137, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert "SHOULD_NOT_PRINT" not in proc.stdout
