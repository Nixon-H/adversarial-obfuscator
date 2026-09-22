"""Textual contract tests for the native Windows stub additions.

Covers native/stub_win.cpp ITEM 1 (export-table poison-keys path) and
ITEM 2 (native BYOVD driver gate) plus the Makefile psapi linkage.

HONEST SCOPE: these are source-contract tests, not behavioral proofs.
They assert the new functions, arming semantics, blocklist stems and
linkage exist in the source exactly as specified. They do NOT prove the
stub compiles under MSVC on Windows or that the tamper path fires at
runtime:

- Full cross-compile of stub_win.cpp is impossible on this Linux host:
  it needs the real <Python.h>/<zlib.h> for the mingw target (absent
  here; `make stub-win` SKIPs for exactly this reason), and the file
  relies on MSVC-only/CTAD idioms that resolve only under the real
  Windows toolchain. CI (Windows runner) compiles it.
- What IS proven here: (a) the pristine-vs-modified mingw
  -fsyntax-only diagnostic comparison shows zero NEW errors (same 19
  pre-existing SecureVector/CTAD errors before and after, none naming
  the new identifiers), and (b) `make stub-linux` stays green.

Naming follows the existing textual-test pattern
(tests/test_crash_suppression.py::test_stub_win_wiring_textual).
"""
import os
import re

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
WIN_STUB = os.path.join(ROOT, "native", "stub_win.cpp")
MAKEFILE = os.path.join(ROOT, "Makefile")
BLOCKLIST_PY = os.path.join(ROOT, "obfuscator", "driver_blocklist.py")


def _src():
    with open(WIN_STUB, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- ITEM 1

def test_poison_function_exists_and_kills_silent():
    src = _src()
    assert "PoisonKeysOnTamper" in src
    # zeros + random fill, then the silent-kill primitive (ExitProcess 137).
    assert "SecureZeroMemory" in src
    assert "rand()" in src
    assert "nixon_silent_kill()" in src


def test_poison_covers_registered_keys_and_obf_bufs_and_iat_truth():
    src = _src()
    assert "RegisterPoisonKey" in src
    assert "g_poisonKeys" in src
    assert "WipeAllObfBufs()" in src
    body = src[src.index("static void PoisonKeysOnTamper"):]
    body = body[: body.index("nixon_silent_kill();")]
    assert "g_iatTruth" in body  # truth table wiped so no re-derivation


def test_live_decrypt_keys_registered_for_poison():
    src = _src()
    # main() must register the actual decrypt-path locals (machineKey /
    # rc4HardwareKey), which the watchdog otherwise cannot reach.
    assert re.search(
        r"RegisterPoisonKey\(\(volatile unsigned char\*\)machineKey,\s*32\)",
        src,
    )
    assert re.search(
        r"RegisterPoisonKey\(\(volatile unsigned char\*\)rc4HardwareKey,\s*32\)",
        src,
    )


def test_verify_exports_bounds_check():
    src = _src()
    assert "VerifyExports" in src
    body = src[src.index("static bool VerifyExports"):]
    body = body[: body.index("static bool VerifyExports") + 6000]
    assert "PyEval_EvalCode" in body
    assert "SizeOfImage" in body  # module-bounds check, not range guess
    assert "PoisonKeysOnTamper()" in body  # tamper => poison, not flag


def test_watchdog_iat_mismatch_poisons_instead_of_latch():
    src = _src()
    assert re.search(
        r"if\s*\(!VerifyIAT\(\)\)\s*PoisonKeysOnTamper\(\);", src
    ), "IAT mismatch must poison immediately, not fold into the 3-strike latch"
    assert "VerifyExports();" in src  # periodic export re-verification


def test_tamper_threat_model_documented():
    src = _src()
    for term in ("IAT hook", "export-table", "DLL injection"):
        assert term.lower() in src.lower(), "threat model comment must name %r" % term


# ---------------------------------------------------------------- ITEM 2

def test_driver_gate_armed_default_off_with_build_flag():
    src = _src()
    assert "CheckBYOVDDrivers" in src
    assert "NIXON_DRIVER_CHECK" in src
    assert "g_driverCheckArmed" in src
    # Default OFF unless -DNIXON_DRIVER_CHECK (mirrors --driver-check).
    assert re.search(
        r"#ifdef NIXON_DRIVER_CHECK\s*\nstatic bool g_driverCheckArmed = true;",
        src,
    )
    # Runtime env opt-in mirrors driver_blocklist.py _ARMED_TRUE.
    assert '"NIXON_DRIVER_CHECK"' in src


def test_driver_gate_readonly_psapi_no_new_imports():
    src = _src()
    body = src[src.index("static void CheckBYOVDDrivers"):]
    body = body[: body.index("static void CheckBYOVDDrivers") + 7000]
    assert "EnumDeviceDrivers" in body
    assert "GetDeviceDriverBaseNameA" in body
    assert "LoadLibraryA" in body or "pLoadLib" in body  # dynamic, no IAT entry
    for banned in ("CreateService", "StartService", "DeviceIoControl",
                   "NtLoadDriver", "ZwLoadDriver"):
        assert banned not in body, "gate must never touch %s" % banned


def test_driver_gate_kills_not_poisons():
    src = _src()
    body = src[src.index("static void CheckBYOVDDrivers"):]
    body = body[: body.index("static void CheckBYOVDDrivers") + 7000]
    assert "nixon_silent_kill();" in body
    assert "PoisonKeysOnTamper" not in body, \
        "drivers are environment, not artifact tamper: kill, never poison"


def test_driver_gate_case_insensitive_stem_match():
    src = _src()
    assert "NixonDriverStemBlocked" in src
    # stem normalization: lowercase + strip one trailing .sys
    assert re.search(r"\[k\] >= 'A' && .*\[k\] <= 'Z'", src)
    assert "IsDriverGateArmed" in src


def test_blocklist_stems_are_subset_of_python_blocklist():
    src = _src()
    py = open(BLOCKLIST_PY, encoding="utf-8").read()
    assert "BLOCKED_DRIVERS" in py
    # Every stem embedded natively must exist in the Python blocklist.
    m = re.search(
        r"kNixonBlockedDriverStems\[\] = \{(.*?)\};", src, re.DOTALL
    )
    assert m, "embedded stem table missing"
    stems = re.findall(r'"([a-z0-9_]+)"', m.group(1))
    assert 10 <= len(stems) <= 15, "spec: 10-15 worst stems, got %d" % len(stems)
    lowered = py.lower()
    for stem in stems:
        assert '"%s"' % stem in lowered, \
            "stem %r not in obfuscator/driver_blocklist.py BLOCKED_DRIVERS" % stem
    # Spot-check the headline BYOVD families.
    for must in ("rtcore64", "winring0", "gdrv", "asio", "dbutildrv2"):
        assert must in stems


def test_makefile_links_psapi_for_stub_win():
    with open(MAKEFILE, encoding="utf-8") as f:
        mk = f.read()
    assert "-lpsapi" in mk, "stub-win link must declare -lpsapi (psapi.lib)"


def test_existing_stub_build_unaffected_textually():
    # Additive-only guard: pre-existing entry points still present.
    src = _src()
    for sym in ("VerifyIAT", "NIXON_IAT_SLOTS", "CheckSandboxVM",
                "CollectAdvancedFingerprint", "DeriveKeyFromFingerprint_Iterative",
                "RC4_Crypt", "nixon_suppress_crash_dialogs"):
        assert sym in src, "pre-existing symbol %r must survive" % sym
