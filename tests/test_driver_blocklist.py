"""V10 Kernel Driver Detection: SAFE read-only defensive gate.

- Blocklist hits on known-bad stems (case variants, with/without .sys).
- Legit driver names pass (ntoskrnl, win32k, tcpip, dxgkrnl, ...).
- Gate disarmed NEVER exits, even with a fake bad driver present
  (monkeypatched enumeration).
- Gate armed + bad driver -> fail-closed (os._exit path).
- enum_loaded_drivers() never raises on this Linux host.
- Snippet compile()s and 3.10-parses; loader wiring defaults OFF and
  --driver-check bakes the gate in.
"""
import ast
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.driver_blocklist import (
    ARM_VAR,
    BLOCKED_DRIVERS,
    CONF_BAD_SIGNATURE,
    CONF_STEM_ONLY,
    CONF_SUSPICIOUS_PATH,
    CONF_VULN_VERSION,
    KILL_THRESHOLD,
    LIMITATION_HIDDEN,
    check_current,
    check_current_evidence,
    check_names,
    check_names_evidence,
    emit_driver_snippet,
    enum_loaded_drivers,
    enum_loaded_drivers_with_paths,
    get_file_version,
    is_armed,
    normalize,
    should_kill,
    signature_status,
)

BUILD_PY = os.path.join(os.path.dirname(__file__), "..", "scripts", "build.py")

_LEGIT = [
    "ntoskrnl.sys",
    "NTOSKRNL",
    "win32k.sys",
    "tcpip.sys",
    "dxgkrnl.sys",
    "storport.sys",
    "ndis.sys",
    "acpi.sys",
    "ntfs.sys",
    "hal.dll",
    "nvlddmkm.sys",  # NVIDIA display driver: legit, must NOT be blocked
]


def _exec_snippet(armed=False, **env):
    """Exec the emitted snippet in a fresh namespace with env applied."""
    src = emit_driver_snippet(armed=armed)
    ns = {}
    old = {}
    for k, v in env.items():
        old[k] = os.environ.get(k)
        os.environ[k] = v
    try:
        exec(compile(src, "<nx_driver_gate>", "exec"), ns)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return src, ns


def test_blocklist_nonempty_and_commented():
    assert len(BLOCKED_DRIVERS) >= 15
    src = open(os.path.join(os.path.dirname(__file__), "..",
                            "obfuscator", "driver_blocklist.py")).read()
    # Every stem should have an explanatory comment nearby (vendor/purpose).
    assert "LOLDrivers" in src
    assert "BYOVD" in src
    # Spot-check confident entries exist.
    for stem in ("rtcore64", "winring0x64", "gdrv", "dbutildrv2",
                 "kprocesshacker", "biontdrv", "rzpnk", "truesight"):
        assert stem in BLOCKED_DRIVERS, stem


def test_no_legit_drivers_blocked():
    assert check_names(_LEGIT) == []
    # VirtualBox guest / AV-style names must not be in the blocklist.
    for legit in ("vboxguest", "vboxsf", "vmw_vmci", "wdf01000",
                  "wdFilter", "WdNisDrv", "norton", "mcafee"):
        assert legit not in BLOCKED_DRIVERS, legit


def test_known_bad_hit_case_variants():
    assert check_names(["RTCore64.sys"]) == ["rtcore64"]
    assert check_names(["rtcore64"]) == ["rtcore64"]
    assert check_names(["RTCORE64.SYS"]) == ["rtcore64"]
    assert check_names(["WinRing0x64.sys"]) == ["winring0x64"]
    assert check_names(["winring0"]) == ["winring0"]
    assert check_names(["GDRV.SYS"]) == ["gdrv"]
    assert check_names(["DBUtilDrv2.sys"]) == ["dbutildrv2"]
    assert check_names(["C:\\Windows\\System32\\drivers\\RTCore64.sys"]) == ["rtcore64"]


def test_normalize_strips_sys_and_case():
    assert normalize("RTCore64.sys") == "rtcore64"
    assert normalize("RTCORE64.SYS") == "rtcore64"
    assert normalize("WinRing0x64") == "winring0x64"
    assert normalize("  GDRV.sys  ") == "gdrv"
    assert normalize(None) == ""
    assert normalize("") == ""


def test_check_names_bad_input_never_raises():
    assert check_names(None) == []
    assert check_names([]) == []
    assert check_names([None, "", 123]) == []
    assert check_names("not-a-list-but-string") == [] or isinstance(
        check_names("not-a-list-but-string"), list)


def test_check_names_sorted_dedup():
    hits = check_names(["GDRV.sys", "gdrv", "RTCore64.sys", "ntoskrnl.sys"])
    assert hits == sorted(hits)
    assert hits == ["gdrv", "rtcore64"]


def test_enum_loaded_drivers_never_raises_linux(monkeypatch):
    # Real host call: must return a list, never raise.
    names = enum_loaded_drivers()
    assert isinstance(names, list)
    # Every entry a non-empty string.
    assert all(isinstance(n, str) and n for n in names)
    # Missing file -> [] (never raises).
    assert enum_loaded_drivers("/nonexistent-nx-modules") == []


def test_enum_linux_parses_first_column(tmp_path):
    f = tmp_path / "modules"
    f.write_text("tun 77824 0 - Live 0x0\nnft_reject 12288 1 x, Live 0x0\n",
                 encoding="utf-8")
    names = enum_loaded_drivers(str(f))
    assert names == ["tun", "nft_reject"]


def test_enum_windows_guarded(monkeypatch):
    # Force the windows branch on this Linux host; ctypes.WinDLL must fail
    # safely -> [].
    import obfuscator.driver_blocklist as mod
    monkeypatch.setattr(mod.platform, "system", lambda: "Windows")
    assert mod.enum_loaded_drivers() == []


def test_is_armed_defaults_off(monkeypatch):
    monkeypatch.delenv(ARM_VAR, raising=False)
    assert is_armed() is False
    for val in ("1", "true", "True", "TRUE", "yes", "Yes", "YES"):
        assert is_armed({ARM_VAR: val}) is True
    for val in ("", "0", "false", "no", "2"):
        assert is_armed({ARM_VAR: val}) is False


def test_snippet_compiles_py310():
    for armed in (False, True):
        src = emit_driver_snippet(armed=armed)
        compile(src, "<nx_driver_gate>", "exec")
        ast.parse(src, feature_version=(3, 10))


def test_snippet_no_py310_banned_syntax():
    src = emit_driver_snippet(armed=False)
    tree = ast.parse(src, feature_version=(3, 10))
    for node in ast.walk(tree):
        assert not isinstance(node, ast.Match), "match statement forbidden"
    # No X|Y annotations: no BinOp-BitOr annotations anywhere.
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            assert not (isinstance(node.annotation, ast.BinOp)
                        and isinstance(node.annotation.op, ast.BitOr))


def test_snippet_mentions_gate_and_exit():
    src = emit_driver_snippet(armed=False)
    assert ARM_VAR in src
    assert "NIXON_DRIVER_CHECK" in src
    assert "driver_check" in src
    # Kill ladder: single failure path via _nx_kill (exit 137), not raw _exit.
    assert "_nx_kill(" in src
    assert "/proc/modules" in src
    assert "EnumDeviceDrivers" in src
    assert "daemon=True" in src  # continuous background re-check
    # No driver LOADING / ring-0 behavior: read-only enumeration only.
    for banned in ("CreateService", "StartService", "NtLoadDriver",
                   "ZwLoadDriver", "DeviceIoControl", "WriteProcessMemory"):
        assert banned not in src, banned


def test_gate_disarmed_never_exits_with_bad_driver(monkeypatch):
    monkeypatch.delenv(ARM_VAR, raising=False)
    _, ns = _exec_snippet(armed=False)
    # Fake a bad driver present via injected names (no real drivers needed).
    hits = ns["driver_check"](["RTCore64.sys", "ntoskrnl.sys"])
    assert hits == ["rtcore64"]  # reported, but no exit


def test_gate_disarmed_snippet_import_never_exits(monkeypatch):
    # Even when the HOST has (or fakes) a bad driver, import-time
    # driver_check() must not exit while disarmed.
    monkeypatch.delenv(ARM_VAR, raising=False)
    import obfuscator.driver_blocklist as mod
    monkeypatch.setattr(mod, "enum_loaded_drivers",
                        lambda *a, **k: ["RTCore64.sys"])
    src = emit_driver_snippet(armed=False)
    ns = {}
    exec(compile(src, "<nx_driver_gate>", "exec"), ns)  # must not raise
    assert ns["driver_check"](["RTCore64.sys"]) == ["rtcore64"]


def test_gate_armed_exits_on_bad_driver(monkeypatch):
    import os as _os
    monkeypatch.delenv(ARM_VAR, raising=False)
    _, ns = _exec_snippet(armed=True)
    exited = {}

    def fake_exit(code):
        exited["code"] = code
        raise SystemExit(code)

    monkeypatch.setattr(_os, "_exit", fake_exit)
    # The snippet did "import os as _os": patch its reference too.
    # NOTE: the kill ladder embeds its own "import os as _nx_os" INSIDE
    # _nx_kill, so patch _nx_os as well.
    monkeypatch.setitem(ns, "_os", _os)
    monkeypatch.setitem(ns, "_nx_os", _os)
    with pytest.raises(SystemExit):
        ns["driver_check"](["RTCore64.sys"])
    assert exited.get("code") == 137


def test_gate_armed_subprocess_137():
    # Real end-to-end kill chain in a child process: armed emitted
    # snippet + REAL kill ladder, bad driver present -> silent 137.
    from obfuscator.kill_ladder import emit_kill_snippet
    src = emit_kill_snippet() + "\n" + emit_driver_snippet(armed=True)
    code = (src + "\n_hits = driver_check(['RTCore64.sys'])\n"
            "print('SHOULD-NOT-REACH')\n")
    env = dict(os.environ)
    env.pop(ARM_VAR, None)
    env.setdefault("NIXON_LOG_REDIRECT", "0")
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, timeout=60, env=env)
    assert proc.returncode == 137, (proc.returncode, proc.stdout, proc.stderr)
    assert proc.stdout == ""
    assert proc.stderr == ""
    assert "SHOULD-NOT-REACH" not in proc.stdout


def test_gate_armed_env_only_exits(monkeypatch):
    import os as _os
    # Env arming is read LIVE at check time: exec disarmed, then arm.
    _, ns = _exec_snippet(armed=False)
    monkeypatch.setenv(ARM_VAR, "1")
    exited = {}

    def fake_exit(code):
        exited["code"] = code
        raise SystemExit(code)

    monkeypatch.setattr(_os, "_exit", fake_exit)
    monkeypatch.setitem(ns, "_os", _os)
    monkeypatch.setitem(ns, "_nx_os", _os)
    with pytest.raises(SystemExit):
        ns["driver_check"](["WinRing0x64.sys"])
    assert exited.get("code") == 137


def test_gate_armed_clean_names_no_exit(monkeypatch):
    monkeypatch.setenv(ARM_VAR, "1")
    _, ns = _exec_snippet(armed=True)
    try:
        assert ns["driver_check"](["ntoskrnl.sys", "win32k.sys"]) == []
    finally:
        monkeypatch.delenv(ARM_VAR, raising=False)


def test_check_current_pure_helper(monkeypatch):
    import obfuscator.driver_blocklist as mod
    monkeypatch.setattr(mod, "enum_loaded_drivers",
                        lambda *a, **k: ["gdrv.sys"])
    assert check_current(names=None) == ["gdrv"]
    assert check_current(names=["ntoskrnl.sys"]) == []


def test_loader_default_off_no_armed_gate():
    from obfuscator.core.pipeline import generate_hybrid_loader_script
    blanks = {"windows": "", "linux": "", "darwin": ""}
    src, _, _ = generate_hybrid_loader_script(blanks, b"", "00" * 32)
    compile(src, "<t>", "exec")
    # Gate snippet always present (report-only), but NOT build-armed.
    assert "def driver_check" in src
    assert "_NX_DRIVER_CHECK_ARMED = False" in src
    assert "_NX_DRIVER_ARMED_BUILD = False" in src


def test_loader_driver_check_true_arms_gate():
    from obfuscator.core.pipeline import generate_hybrid_loader_script
    blanks = {"windows": "", "linux": "", "darwin": ""}
    src, _, _ = generate_hybrid_loader_script(blanks, b"", "00" * 32,
                                              driver_check=True)
    compile(src, "<t>", "exec")
    assert "_NX_DRIVER_CHECK_ARMED = True" in src
    assert "_NX_DRIVER_ARMED_BUILD = True" in src


def test_loader_signature_default_off():
    import inspect
    from obfuscator.core.pipeline import generate_hybrid_loader_script
    assert inspect.signature(
        generate_hybrid_loader_script).parameters["driver_check"].default is False


def test_build_flag_present():
    out = subprocess.run(
        [sys.executable, BUILD_PY, "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert out.returncode == 0, out.stderr[-2000:]
    assert "--driver-check" in (out.stdout + out.stderr)


def test_driver_names_survive_rename_passes():
    # Gate helper/marker names must be reserved against symbol renames and
    # unicode encoding, or an armed gate breaks at runtime.
    from obfuscator.core.sources import apply_ast_mutation
    probe = ("def _x():\n"
             "    a = driver_check\n"
             "    b = _nx_driver_hits\n"
             "    c = _nx_enum_drivers\n"
             "    d = _nx_driver_armed\n"
             "    e = _nx_driver_stem\n"
             "    f = _nx_driver_watch\n"
             "    g = _NX_DRIVER_BLOCKED\n"
             "    h = _NX_DRIVER_ARMED_BUILD\n"
             "    i = _NX_DRIVER_CHECK_ARMED\n"
             "    return (a, b, c, d, e, f, g, h, i)\n")
    out, _ = apply_ast_mutation(
        probe, {"symbol_rename": True, "unicode_ids": True,
                "driver_check": True})
    for name in ("driver_check", "_nx_driver_hits", "_nx_enum_drivers",
                 "_nx_driver_armed", "_nx_driver_stem", "_nx_driver_watch",
                 "_NX_DRIVER_BLOCKED", "_NX_DRIVER_ARMED_BUILD",
                 "_NX_DRIVER_CHECK_ARMED"):
        assert name in out, name


# ---------------------------------------------------------------------------
# Hardening additions: evidence records, path signal, version fingerprints,
# confidence tiers. All additive; existing bare-string/snippet behavior above
# is untouched.
# ---------------------------------------------------------------------------

def test_check_names_still_bare_strings_contract():
    # check_names return type is load-bearing (snippet parity): bare stems.
    assert check_names(["RTCore64.sys"]) == ["rtcore64"]
    recs = check_names_evidence(["RTCore64.sys"])
    assert len(recs) == 1
    assert recs[0]["stem"] == "rtcore64"
    assert check_names(["ntoskrnl.sys"]) == []
    assert check_names_evidence(["ntoskrnl.sys"]) == []


def test_evidence_shape_keys():
    recs = check_names_evidence(["RTCore64.sys"])
    assert len(recs) == 1
    rec = recs[0]
    for key in ("stem", "raw", "rule", "confidence"):
        assert key in rec, key
    assert rec["stem"] == "rtcore64"
    assert rec["raw"] == "RTCore64.sys"
    assert isinstance(rec["confidence"], float)
    # Explainable verdict: limitation strings always present.
    assert "limitation" in rec
    assert "rootkit" in rec["limitation"] or "hidden" in rec["limitation"]
    assert LIMITATION_HIDDEN in rec["limitation"]


def test_evidence_stem_only_confidence_06():
    recs = check_names_evidence(["WinRing0x64.sys"])
    assert len(recs) == 1
    assert recs[0]["confidence"] == CONF_STEM_ONLY == 0.6
    assert recs[0]["rule"] == "stem_match"
    # Kill gate preserved: stem-only still meets threshold.
    assert should_kill(recs) is True
    assert KILL_THRESHOLD == 0.6


def test_evidence_known_dir_path_stays_06():
    recs = check_names_evidence(
        ["C:\\Windows\\System32\\drivers\\RTCore64.sys"])
    assert len(recs) == 1
    assert recs[0]["confidence"] == 0.6
    assert "location_suspicious" not in recs[0]["rules"]
    assert recs[0]["path"] != ""


def test_evidence_suspicious_path_confidence_08():
    recs = check_names_evidence(["C:\\Users\\evil\\Temp\\RTCore64.sys"])
    assert len(recs) == 1
    assert recs[0]["confidence"] == CONF_SUSPICIOUS_PATH == 0.8
    assert recs[0]["rule"] == "location_suspicious"
    assert "location_suspicious" in recs[0]["rules"]
    assert should_kill(recs) is True


def test_evidence_tuple_and_paths_map_inputs():
    recs = check_names_evidence([("gdrv.sys", "C:\\Temp\\gdrv.sys")])
    assert len(recs) == 1 and recs[0]["confidence"] == 0.8
    recs = check_names_evidence(["gdrv.sys"],
                                paths={"gdrv": "C:\\Temp\\gdrv.sys"})
    assert len(recs) == 1 and recs[0]["confidence"] == 0.8
    recs = check_names_evidence(
        ["gdrv.sys"], paths={"gdrv": "C:\\Windows\\System32\\drivers\\gdrv.sys"})
    assert len(recs) == 1 and recs[0]["confidence"] == 0.6


def test_evidence_vulnerable_version_confidence_095():
    # DBUtilDrv2 2.3.0.0 is a known-vulnerable build (CVE-2021-21551).
    recs = check_names_evidence(["DBUtilDrv2.sys"],
                                versions={"dbutildrv2": "2.3.0.0"})
    assert len(recs) == 1
    assert recs[0]["confidence"] == CONF_VULN_VERSION == 0.95
    assert recs[0]["rule"] == "vulnerable_version"
    assert recs[0]["version"] == "2.3.0.0"
    assert should_kill(recs) is True


def test_evidence_version_mismatch_falls_back_to_stem():
    # Far-future version: not vulnerable per fingerprint, but the stem hit
    # still reports at 0.6 (version data must never fail-open).
    recs = check_names_evidence(["DBUtilDrv2.sys"],
                                versions={"dbutildrv2": "9.9.9.9"})
    assert len(recs) == 1
    assert recs[0]["confidence"] == 0.6
    assert recs[0]["rule"] == "fixed_version_stem_only"
    assert should_kill(recs) is True


def test_evidence_unknown_version_falls_back_to_stem():
    recs = check_names_evidence(["DBUtilDrv2.sys"])
    assert len(recs) == 1
    assert recs[0]["confidence"] == 0.6
    assert recs[0]["version"] == ""
    assert should_kill(recs) is True
    # Garbage version strings never raise, never inflate.
    recs = check_names_evidence(["DBUtilDrv2.sys"],
                                versions={"dbutildrv2": "not-a-version!!!"})
    assert recs[0]["confidence"] == 0.6


def test_evidence_signature_invalid_09_via_override():
    recs = check_names_evidence(["gdrv.sys"],
                                signatures={"gdrv": False})
    assert len(recs) == 1
    assert recs[0]["confidence"] == CONF_BAD_SIGNATURE == 0.9
    assert recs[0]["rule"] == "signature_invalid"
    recs = check_names_evidence(["gdrv.sys"], signatures={"gdrv": True})
    assert recs[0]["confidence"] == 0.6  # valid: no boost


def test_signature_helper_skipped_gracefully():
    # Live validation intentionally unimplemented: always unknown, never raises.
    assert signature_status("C:\\Windows\\System32\\drivers\\gdrv.sys") is None
    assert signature_status(None) is None
    assert signature_status("") is None


def test_get_file_version_failsoft_nonwindows():
    # On this Linux host: always None, never raises.
    assert get_file_version("/proc/modules") is None
    assert get_file_version(None) is None
    assert get_file_version("") is None


def test_evidence_renamed_copy_stem_still_hits():
    # Rename that keeps the stem (new dir, same basename) still hits.
    recs = check_names_evidence(["C:\\evil-drop\\RTCore64.sys"])
    assert [r["stem"] for r in recs] == ["rtcore64"]
    # A copy renamed to a fully different stem is invisible: documented
    # limitation, must NOT false-positive.
    assert check_names_evidence(["totally_legit.sys"]) == []
    assert check_names_evidence(["totally_legit.sys"]) == check_names(
        ["totally_legit.sys"])


def test_evidence_never_raises_bad_input():
    assert check_names_evidence(None) == []
    assert check_names_evidence([]) == []
    assert check_names_evidence([None, "", 123]) == []
    assert check_names_evidence("not-a-list-but-string") == [] or isinstance(
        check_names_evidence("not-a-list-but-string"), list)
    assert check_names_evidence([("gdrv.sys", None, "extra")]) == [] or \
        isinstance(check_names_evidence([("gdrv.sys", None, "extra")]), list)
    assert should_kill(None) is False
    assert should_kill([]) is False
    assert should_kill([{"confidence": 0.1}]) is False
    assert should_kill([{"confidence": 0.6}]) is True


def test_evidence_sorted_dedup():
    recs = check_names_evidence(["GDRV.sys", "gdrv",
                                 "C:\\T\\RTCore64.sys", "ntoskrnl.sys"])
    assert [r["stem"] for r in recs] == ["gdrv", "rtcore64"]


def test_check_current_evidence_pure_helper(monkeypatch):
    import obfuscator.driver_blocklist as mod
    monkeypatch.setattr(mod, "enum_loaded_drivers",
                        lambda *a, **k: ["gdrv.sys"])
    recs = check_current_evidence(names=None)
    assert [r["stem"] for r in recs] == ["gdrv"]
    assert check_current_evidence(names=["ntoskrnl.sys"]) == []
    recs = check_current_evidence(names=["WinRing0x64.sys"])
    assert recs[0]["confidence"] == 0.6


def test_enum_with_paths_linux_no_paths(tmp_path):
    f = tmp_path / "modules"
    f.write_text("tun 77824 0 - Live 0x0\n", encoding="utf-8")
    pairs = enum_loaded_drivers_with_paths(str(f))
    assert pairs == [("tun", None)]  # /proc/modules has no path column
    assert enum_loaded_drivers_with_paths("/nonexistent-nx-modules") == []


def test_version_fingerprints_small_curated_subset():
    import json as _json
    fp_path = os.path.join(os.path.dirname(__file__), "..", "obfuscator",
                           "driver_versions.json")
    data = _json.load(open(fp_path, encoding="utf-8"))
    assert "_meta" in data  # staleness warning + refresh pointer documented
    meta = _json.dumps(data["_meta"]).lower()
    assert "stale" in meta and "lol" in meta
    stems = [k for k in data if not k.startswith("_")]
    assert 1 <= len(stems) <= 10, len(stems)
    for stem in stems:
        assert stem in BLOCKED_DRIVERS, stem


def test_module_no_driver_loading_apis():
    src = open(os.path.join(os.path.dirname(__file__), "..", "obfuscator",
                            "driver_blocklist.py")).read()
    for banned in ("CreateService", "StartService", "NtLoadDriver",
                   "ZwLoadDriver", "DeviceIoControl", "WriteProcessMemory",
                   "NtDeviceIoControlFile", "IoCreateDevice"):
        assert banned not in src, banned


def test_module_compiles_py310():
    src = open(os.path.join(os.path.dirname(__file__), "..", "obfuscator",
                            "driver_blocklist.py")).read()
    compile(src, "<nx_driver_blocklist>", "exec")
    ast.parse(src, feature_version=(3, 10))
