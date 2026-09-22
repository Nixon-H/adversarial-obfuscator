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
    check_current,
    check_names,
    emit_driver_snippet,
    enum_loaded_drivers,
    is_armed,
    normalize,
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
    assert "os._exit(1)" in src or "_os._exit(1)" in src
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
    monkeypatch.setitem(ns, "_os", _os)
    with pytest.raises(SystemExit):
        ns["driver_check"](["RTCore64.sys"])
    assert exited.get("code") == 1


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
    with pytest.raises(SystemExit):
        ns["driver_check"](["WinRing0x64.sys"])
    assert exited.get("code") == 1


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
