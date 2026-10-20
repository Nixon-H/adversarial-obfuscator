"""Failure-mode proofs for docs/failure-modes.md.

Each test forces the failure and asserts the documented behavior.
Python 3.10 compatible: no match statements, no X | Y annotations.
"""
import argparse
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# --- D3: z3 absence must NOT break the build import closure -----------------

def test_z3_absence_does_not_break_the_build_import_closure():
    """Without z3, the build CLI must still import.

    z3 is a proof-only dependency.  It used to be a hard module-level
    import in scripts/validation/*, which made the WHOLE build CLI
    unimportable without it -- a proof-only dependency load-bearing for
    every build.  The import is now guarded and the proof entry points
    raise a clear error when they are actually reached.
    """
    import importlib
    purged = {}
    for name in list(sys.modules):
        # scripts.z3_optional caches the real z3 the first time it is
        # imported, so it has to be purged too -- otherwise the result
        # depends on what ran before this test.
        if (name == "z3" or name.startswith("scripts.validation")
                or name == "scripts.z3_optional"):
            purged[name] = sys.modules.pop(name)
    sys.modules["z3"] = None  # 'import z3' now raises ImportError
    try:
        smt = importlib.import_module("scripts.validation.smt_validator")
        assert smt is not None
        build = importlib.import_module("scripts.build")
        assert build is not None
    finally:
        sys.modules.pop("z3", None)
        for name, mod in purged.items():
            if name != "z3":
                sys.modules[name] = mod


def test_z3_absence_raises_a_clear_error_at_the_proof_entry_point():
    """The proof path must fail with a message, not an AttributeError."""
    import importlib
    purged = {}
    for name in list(sys.modules):
        # scripts.z3_optional caches the real z3 the first time it is
        # imported, so it has to be purged too -- otherwise the result
        # depends on what ran before this test.
        if (name == "z3" or name.startswith("scripts.validation")
                or name == "scripts.z3_optional"):
            purged[name] = sys.modules.pop(name)
    sys.modules["z3"] = None
    try:
        ir_to_smt = importlib.import_module("scripts.validation.ir_to_smt")
        # The stand-in raises when z3 is actually used, not when the
        # module is imported: importing must stay cheap, using must
        # fail with a message.
        with pytest.raises(RuntimeError) as exc:
            ir_to_smt.IRToSMT()._bv("x")
        assert "z3" in str(exc.value).lower()
    finally:
        sys.modules.pop("z3", None)
        for name, mod in purged.items():
            if name != "z3":
                sys.modules[name] = mod


# --- D7: corrupted config fails closed ---------------------------------------
# (behavior changed DEGRADE -> FAIL-CLOSED by config schema validation;
# see scripts/config_schema.py and tests/test_config_schema.py)

def test_corrupted_config_fails_closed(tmp_path):
    """Malformed default.json -> ConfigError (fail-closed, aborts build).

    Previously degraded to {'features': {}} silently (docs/failure-modes.md
    D7); schema validation now refuses to build with an unreadable
    protection posture instead of emitting an unprotected artifact.
    """
    import scripts.phases.phase02_config as p2
    from scripts.config_schema import ConfigError
    bad = tmp_path / "default.json"
    bad.write_text("{not valid json,,,", encoding="utf-8")
    old = p2.DEFAULT_CONFIG
    p2.DEFAULT_CONFIG = str(bad)
    try:
        opts = argparse.Namespace(
            advanced_protection=False, phase2=False,
            advanced_protection_only=None, phase2_only=None,
            phase2_extras=False, adversarial_injection=False,
            ephemeral_isa=False, microjit=False, oram=False, rop=False,
        )
        with pytest.raises(ConfigError):
            p2.load_advanced_protection_config(opts)
    finally:
        p2.DEFAULT_CONFIG = old


# --- D8: missing driver metadata -> no hits, no kill -------------------------

def test_missing_driver_metadata_yields_no_kill():
    """Empty/unreadable enumeration -> [] hits; gate cannot fire."""
    from obfuscator import driver_blocklist as db
    assert db.enum_loaded_drivers(modules_path="/nonexistent-proc-modules") == []
    assert db.check_current(names=[]) == []
    assert db.check_names([]) == []
    assert db.should_kill([]) is False
    assert db.should_kill(None) is False


# --- D4/D9: contradictory evidence still kills when armed --------------------

def test_contradictory_driver_evidence_still_kills():
    """Stem hit + fixed version -> 'fixed_version_stem_only' @ 0.6, still kills."""
    from obfuscator import driver_blocklist as db
    fp = db._load_version_fingerprints()
    assert "_meta" not in fp  # malformed top-level keys skipped
    ev = db.check_names_evidence(["dbutildrv2"],
                                 versions={"dbutildrv2": "9.9.9.9"})
    assert len(ev) == 1
    assert ev[0]["rule"] == "fixed_version_stem_only"
    assert ev[0]["confidence"] == db.CONF_STEM_ONLY == 0.6
    assert db.should_kill(ev) is True
    ev_vuln = db.check_names_evidence(["dbutildrv2"],
                                      versions={"dbutildrv2": "2.3.0.0"})
    assert ev_vuln[0]["rule"] == "vulnerable_version"
    assert ev_vuln[0]["confidence"] == db.CONF_VULN_VERSION == 0.95


# --- D19: half-written trial state -> tampered --------------------------------

def test_half_written_trial_state_is_tampered(tmp_path):
    """Torn/corrupt state file fails closed as 'tampered'."""
    from obfuscator import trial_bind as tb
    key = os.urandom(32)
    ctx = tb.build_trial_context(3600.0, hwid="halfwrite", build_key=key)
    state = str(tmp_path / "trial.state")
    with open(state, "w", encoding="utf-8") as fh:
        fh.write("half-written{{{no-colon-no-mac")
    assert tb.check_and_update(key, "halfwrite", ctx["deadline"],
                               ctx["token"], state_path=state,
                               now=1700000000.0) == "tampered"


# --- D17: clock jumps backwards -> rollback -----------------------------------

def test_clock_rollback_detected(tmp_path):
    """now < last_seen - tolerance -> 'rollback' (fail-closed)."""
    from obfuscator import trial_bind as tb
    key = os.urandom(32)
    ctx = tb.build_trial_context(86400.0, hwid="rollback", build_key=key)
    state = str(tmp_path / "trial.state")
    t0 = 1700000000.0
    assert tb.check_and_update(key, "rollback", ctx["deadline"],
                               ctx["token"], state_path=state,
                               now=t0) == "ok"
    assert tb.check_and_update(key, "rollback", ctx["deadline"],
                               ctx["token"], state_path=state,
                               now=t0 - 1000.0) == "rollback"
    # Within tolerance is still ok.
    assert tb.check_and_update(key, "rollback", ctx["deadline"],
                               ctx["token"], state_path=state,
                               now=t0 - 10.0) == "ok"


# --- D30: token reuse advances state, no bypass -------------------------------

def test_trial_token_reuse_advances(tmp_path):
    """Same token twice -> ok/ok and last_seen moves forward."""
    from obfuscator import trial_bind as tb
    key = os.urandom(32)
    ctx = tb.build_trial_context(3600.0, hwid="replay-hwid", build_key=key)
    state = str(tmp_path / "trial.state")
    t0 = 1700000000.0
    assert tb.check_and_update(key, "replay-hwid", ctx["deadline"],
                               ctx["token"], state_path=state,
                               now=t0) == "ok"
    assert tb.check_and_update(key, "replay-hwid", ctx["deadline"],
                               ctx["token"], state_path=state,
                               now=t0 + 60.0) == "ok"
    with open(state, encoding="utf-8") as fh:
        sealed = fh.read().strip()
    assert tb.unseal_last_seen(key, sealed) == t0 + 60.0


# --- D18: 2**63 timestamps ----------------------------------------------------

def test_huge_timestamps_no_overflow():
    """2**63 deadlines/timestamps give correct verdicts, no exception."""
    from obfuscator import trial_bind as tb
    key = os.urandom(32)
    fp = "bigclock"
    dl = 2 ** 63
    token = tb.mint_token(key, fp, dl)
    assert tb.check_trial(key, fp, dl, token, now=float(2 ** 63 - 10)) == "ok"
    # NOTE: ulp at 2**63 is 1024, so the post-deadline probe must exceed it.
    assert tb.check_trial(key, fp, dl, token, now=float(2 ** 63) + 4096.0) == "expired"
    sealed = tb.seal_last_seen(key, float(2 ** 63))
    assert tb.unseal_last_seen(key, sealed) == float(2 ** 63)


# --- D31: env defaults are fail-safe ------------------------------------------

def test_env_defaults_fail_safe():
    """Empty env: gates armed/off in the safe direction; disarmed snippet
    enumerates but never exits; armed snippet kills via os._exit(137)
    (uncatchable in-process, so probed in a subprocess)."""
    import subprocess
    from obfuscator import driver_blocklist as db
    from obfuscator import frozen_snapshot as fs
    assert db.is_armed({}) is False
    assert fs.is_opted_out({}) is False
    ns = {}
    exec(db.emit_driver_snippet(armed=False), ns)
    assert ns["driver_check"](["rtcore64"]) == ["rtcore64"]  # no exit
    assert ns["driver_check"]([]) == []
    probe = (
        "import sys; sys.path.insert(0, %r)\n"
        "from obfuscator.driver_blocklist import emit_driver_snippet\n"
        "ns = {}\n"
        "exec(emit_driver_snippet(armed=True), ns)\n"
        "ns['driver_check'](['rtcore64'])\n"
        "print('SURVIVED')\n" % (ROOT,)
    )
    env = {k: v for k, v in os.environ.items()
           if k != "NIXON_DRIVER_CHECK"}
    env["NIXON_LOG_REDIRECT"] = "0"
    proc = subprocess.run([sys.executable, "-c", probe],
                          capture_output=True, text=True, env=env,
                          timeout=120)
    assert proc.returncode == 137, proc.stderr[-2000:]
    assert "SURVIVED" not in proc.stdout


# --- D10: staleness flag (proves the applied fix) ------------------------------

def test_fingerprint_staleness_flag():
    """Evaluable staleness flag: huge max-age fresh, zero max-age stale."""
    from obfuscator import driver_blocklist as db
    assert db.version_fingerprints_mtime() is not None  # file ships
    assert db.version_fingerprints_stale(max_age_s=10 ** 9) is False
    assert db.version_fingerprints_stale(max_age_s=0) is True
    # Gate data still loads regardless (warn-not-gate contract).
    assert isinstance(db._load_version_fingerprints(), dict)


# --- D4: missing Cython degrades gracefully ------------------------------------

def test_pytoc_missing_cython_graceful_skip(tmp_path, monkeypatch):
    """Cython absent -> (None, reason), never raises."""
    import importlib
    pp = importlib.import_module("scripts.phases.phase_pytoc")
    src = tmp_path / "obf.py"
    src.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setitem(sys.modules, "Cython", None)
    monkeypatch.setitem(sys.modules, "Cython.Build", None)
    built, msg = pp.cythonize_obfuscated(str(src),
                                         str(tmp_path / "o_pytoc.so"))
    assert built is None
    assert "Cython not installed" in msg
    built2, msg2 = pp.phase_pytoc(str(tmp_path / "missing.py"))
    assert built2 is None
    assert "skip" in msg2


# --- D11/D22: malformed + huge driver inputs never raise -----------------------

def test_malformed_driver_paths_never_raise():
    """None/empty/non-str entries are skipped; 10MB strings don't hang/crash."""
    from obfuscator import driver_blocklist as db
    big = "A" * (10 * 1024 * 1024)
    out = db.check_names([None, "", 12345, b"\x00", [], {}, 3.14,
                          "RTCORE64.SYS", big])
    assert out == ["rtcore64"]
    ev = db.check_names_evidence([None, "", big])
    assert ev == []
    assert db._path_suspicious(None) is None
    assert db._path_suspicious("") is None
    assert db._path_suspicious("C:\\Temp\\evil\\rtcore64.sys") is True
    assert db._path_suspicious("C:\\Windows\\System32\\drivers\\x.sys") is False
