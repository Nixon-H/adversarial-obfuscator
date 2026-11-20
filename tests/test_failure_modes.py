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


# --- P1 (reviewer, 2026-11-20): native-only negative matrix -------------------
#
# The absolute-native-only profile has NO Python payload fallback, so every
# failure path must terminate WITHOUT executing payload code. These pin the
# emitted loader contract for each one; the runtime behaviour of the same
# paths is covered by test_artifact_tamper and by the ordering test in
# test_native_enforcement.

def _native_only_loader():
    from obfuscator.core import pipeline as pl
    return pl.generate_hybrid_loader_script(
        native_blobs={"linux": "QUJD"}, bytecode_fallback=b"",
        key_hex="00" * 32, native_only=True, build_id="negative-matrix")[0]


def test_native_only_has_no_python_payload_fallback():
    """FALLBACK_BLOB is DISABLED: there is nothing to decrypt in Python."""
    loader = _native_only_loader()
    assert 'FALLBACK_BLOB = "DISABLED"' in loader


def test_native_only_failure_path_exits_non_zero():
    """A fail-closed artefact must REPORT the failure, not exit 0.

    Measured 2026-11-21 on a real `--package native-only` build: with a wrong
    or missing seal shard the artefact printed nothing and exited **0**. Every
    failure path in _load_native() returns None, and the entrypoint ignored
    that return, so to systemd, CI, a supervisor or a benchmark the run was
    indistinguishable from success. Nothing had executed.

    The contract for this profile is "if the blob cannot load, the loader runs
    nothing (fail-closed by construction)", which is only meaningful if the
    failure is observable. Pinned at the source level here; the end-to-end
    non-zero exit is exercised by the build-level test in
    tests/test_native_enforcement.py.
    """
    loader = _native_only_loader()
    # The verdict is captured, not discarded.
    assert "_nx_native_verdict = _load_native()" in loader, \
        "the entrypoint still ignores what _load_native() returns"
    # ... and a None verdict is fatal for this profile.
    assert "_nx_native_verdict is None" in loader
    assert "exit 78" in loader
    assert "no Python fallback exists" in loader


def test_fallback_build_does_not_gain_the_native_only_exit():
    """The non-zero exit is compiled out for every profile with a fallback."""
    from obfuscator.core import pipeline as pl
    with_fallback = pl.generate_hybrid_loader_script(
        native_blobs={"linux": "QUJD"}, bytecode_fallback=b"PK\x03\x04junk",
        key_hex="00" * 32, native_only=False, build_id="fallback-profile")[0]
    assert "if False and _nx_native_verdict is None:" in with_fallback, \
        "a fallback build must keep the old entrypoint behaviour"


def test_missing_blob_is_refused_not_fallback_executed():
    """No blob for the platform: the loader returns without running."""
    loader = _native_only_loader()
    assert "if not blob_key or" in loader
    assert "_NX_SECTION_PACK or _nx_ci_bypass_ok()" in loader


def test_corrupt_blob_is_refused():
    """A blob that is not an object file is refused, never dlopen'd."""
    loader = _native_only_loader()
    assert "_nx_magics" in loader
    assert "\\\\x7fELF" in loader or "\\x7fELF" in loader


def test_missing_enforcement_export_is_fatal():
    """A blob without nx_apply_protections is refused (fail closed)."""
    loader = _native_only_loader()
    assert "lacks enforcement entry" in loader
    assert "nx_apply_protections" in loader


def test_native_enforcement_failure_is_fatal():
    loader = _native_only_loader()
    assert "native enforcement failed to apply" in loader


def test_signed_artefact_carries_provenance_material():
    """Provenance slots and the stdlib verifier ship in every loader.

    The CHECK block is stamped in by the build (that is what makes the
    signature cover the final bytes); this asserts the material a signed
    artefact is built from, and that the loader text compiles.
    """
    loader = _native_only_loader()
    assert "_NX_PROV_SIG" in loader and "_NX_PROV_PK" in loader
    assert "_nx_prov_verify" in loader
    compile(loader, "<native-only-loader>", "exec")


def test_native_only_bypass_is_disabled():
    """The CI bypass must answer False even with the env pair set.

    Reviewer P1: a native-only artefact promises no Python payload path. The
    bypass used to answer "yes" whenever the CI env pair was present, and
    four failure sites then reached `_exec_fallback()`. It is now compiled
    shut for this profile: the helper returns False before it ever reads the
    environment.
    """
    loader = _native_only_loader()
    marker = "def _nx_ci_bypass_ok():"
    body = loader.split(marker, 1)[1][:400]
    assert "if True:" in body, (
        "the native-only loader does not hard-disable the CI bypass; its "
        "failure paths would still reach the Python payload")
    # the guard must precede the environment read
    assert body.index("if True:") < body.index("NIXON_VERIFY_SKIP_VERSION_CHECK")


def test_failed_native_import_has_no_python_path_left():
    """Every _exec_fallback call site is gated, and the gate is compiled shut.

    Two properties together, since either alone is a layered assumption:
      1. every call site after the definition is guarded by
         `_nx_ci_bypass_ok()` -- no path reaches the Python payload around
         the gate;
      2. in this profile that helper returns False before it reads the
         environment -- the gate is shut by construction, not by config.
    """
    import re as _re

    loader = _native_only_loader()
    body = loader.split("def _exec_fallback", 1)[1]
    calls = [match.start() for match in _re.finditer(r"_exec_fallback\(\)",
                                                     body)]
    assert calls, "expected the loader to retain its fallback function"
    guarded = [pos for pos in calls
               if "_nx_ci_bypass_ok()" in body[max(0, pos - 200):pos]]
    # the definition's own name and any comment references are not calls
    live = [pos for pos in calls
            if not body[max(0, pos - 12):pos].rstrip().endswith("#")]
    assert len(guarded) >= len(live) - 1, (
        "a _exec_fallback call site is not gated by _nx_ci_bypass_ok: "
        "%d guarded of %d call sites" % (len(guarded), len(calls)))
    helper = loader.split("def _nx_ci_bypass_ok():", 1)[1][:300]
    assert "if True:" in helper, (
        "the native-only profile does not compile the bypass shut")
    assert helper.index("if True:") < helper.index(
        "NIXON_VERIFY_SKIP_VERSION_CHECK"), (
        "the compiled-shut guard must precede the environment read, or an "
        "env pair would still open the gate")


# --- platform=github without a token must FAIL, not degrade ----------------

def test_platform_github_without_a_token_refuses_to_build():
    """Measured 2026-11-20: this used to print ONE warning and ship a
    single-OS artefact under a "platform=github" request, ending with
    "ALL OPERATIONS COMPLETE". The windows and darwin blobs were empty and the
    warning was lost in the progress output, so the operator had every reason
    to believe they held a 3-OS build.

    A build that cannot do what it was asked must fail. This pins the refusal
    in source: the branch must raise, and the deliberate local path
    (--skip-cloud) must remain a separate, explicit choice.
    """
    src = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "obfuscator", "core", "pipeline.py"),
        encoding="utf-8").read()
    marker = "if _farm_platform == 'github' and not getattr(args, 'skip_cloud', False):"
    assert marker in src, "the farm gate moved; re-check this test"
    body = src[src.find(marker):src.find(marker) + 2200]
    assert "raise SystemExit(" in body, (
        "platform=github without a token no longer refuses: a single-OS "
        "artefact could ship as a 3-OS build again")
    # the message is split across literals, so match the pieces
    assert "no GitHub token is" in body and "GITHUB_TOKEN, GH_TOKEN" in body
    assert "single-OS" in body, (
        "the refusal must say the artefact would be single-OS, or the "
        "operator cannot tell what they almost shipped")
    # and it must NOT still be a warn-and-continue
    assert "fall back to bytecode (local blob still embedded)" not in body, (
        "the warn-and-continue path is back; that is what shipped a "
        "single-OS artefact under a platform=github request")
