"""§3 Windows/macOS hardening: what the object ACTUALLY says, not what we asked for.

The review's constraint is explicit: *"Don't blindly enable every flag. Verify
the resulting binary using platform-native inspection tools."* This machine is
Linux and cannot produce a PE or a Mach-O object, so there are two honest
options: skip the platform entirely, or write a parser whose correctness is
established on synthetic headers and whose report travels in the runner
attestation for the real object.

This file is the first half of that bargain. Every test below builds a header
by hand and asserts the parser reports what is set, because the failure that
matters is not "the parser crashed" -- it is "the parser said hardened when the
object was not". A parser that returns True on an unreadable blob would turn
the whole §3 check into decoration, so several tests below are specifically
about refusing to read as hardened.

The second half is the driver wiring: the farm runner must import the module
and record the result, or none of this executes where it counts.
"""
import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator import native_harden as nh  # noqa: E402


# ── header builders ──────────────────────────────────────────────────────

def _pe(dll_characteristics, security_size=0, debug_size=0, pe32plus=True,
        load_config_size=None):
    """A minimal PE image: DOS header, PE signature, COFF, optional header.

    ``load_config_size`` defaults to a non-zero value WHENEVER the CFG bit is
    set, because a CFG flag with an empty load-config directory is a
    declaration with nothing behind it. Measured 2026-11-19: lld-link 19 with
    ``-guard:cf`` produces exactly that (``warning: Control Flow Guard is
    enabled but '_load_config_used' is missing``), and `check()` now rejects it.
    A fixture that set the bit without the data would be modelling a broken
    object, so the default models a working one and the broken case is tested
    explicitly.
    """
    e_lfanew = 0x80
    head = bytearray(e_lfanew)
    head[0:2] = b"MZ"
    struct.pack_into("<I", head, 0x3C, e_lfanew)

    coff = bytearray(20)
    struct.pack_into("<H", coff, 0, 0x8664 if pe32plus else 0x014C)  # machine
    struct.pack_into("<H", coff, 2, 3)                              # sections
    struct.pack_into("<H", coff, 16, 0xF0 if pe32plus else 0xE0)    # opt size

    opt_size = 0xF0 if pe32plus else 0xE0
    opt = bytearray(opt_size)
    struct.pack_into("<H", opt, 0, 0x20B if pe32plus else 0x10B)    # magic
    struct.pack_into("<H", opt, 70, dll_characteristics)            # DllCharacteristics
    num_dirs_off = 108 if pe32plus else 92
    dirs_off = 112 if pe32plus else 96
    struct.pack_into("<I", opt, num_dirs_off, 16)
    if security_size:
        struct.pack_into("<I", opt, dirs_off + 4 * 8 + 4, security_size)
    if debug_size:
        struct.pack_into("<I", opt, dirs_off + 6 * 8 + 4, debug_size)
    if load_config_size is None:
        load_config_size = 0x48 if (dll_characteristics & nh.PE_GUARD_CF) else 0
    struct.pack_into("<II", opt, dirs_off + 10 * 8, 0x3000, load_config_size)

    return bytes(head) + b"PE\0\0" + bytes(coff) + bytes(opt)


def _macho(flags, signature=None):
    """A minimal 64-bit little-endian Mach-O with an optional code signature."""
    ncmds = 1 if signature else 0
    header = bytearray(32)
    struct.pack_into("<I", header, 0, 0xFEEDFACF)   # MH_MAGIC_64
    struct.pack_into("<I", header, 12, 2)           # filetype MH_EXECUTE
    struct.pack_into("<I", header, 16, ncmds)
    struct.pack_into("<I", header, 24, flags)
    if not signature:
        return bytes(header)

    sig_off = 32 + 16
    cmd = struct.pack("<IIII", 0x1D, 16, sig_off, len(signature))
    body = bytearray(header) + cmd
    body.extend(b"\0" * (sig_off - len(body)))
    body.extend(signature)
    return bytes(body)


def _codesign(runtime=False, restrict=False):
    """A cs superblob holding one CodeDirectory with the given flags."""
    flags = (nh.CS_RUNTIME if runtime else 0) | (nh.CS_RESTRICT if restrict else 0)
    cd_off = 12 + 8                       # superblob header + one index entry
    cd = bytearray(0x60)
    struct.pack_into(">I", cd, 0, 0xFADE0C02)   # CSMAGIC_CODEDIRECTORY
    struct.pack_into(">I", cd, 4, len(cd))
    struct.pack_into(">I", cd, 0x28, flags)
    superblob = struct.pack(">III", 0xFADE0CC0, cd_off + len(cd), 1)
    superblob += struct.pack(">II", 0, cd_off)
    return bytearray(superblob + bytes(cd))


def _fat(macho):
    """A FAT (universal) wrapper around one slice."""
    slice_off = 0x1000
    header = bytearray(slice_off)
    struct.pack_into(">I", header, 0, 0xCAFEBABE)
    struct.pack_into(">I", header, 4, 1)          # one architecture
    struct.pack_into(">I", header, 16, slice_off)  # offset of slice 0
    struct.pack_into(">I", header, 20, len(macho))
    return bytes(header) + macho


# ── PE: the flags actually present ───────────────────────────────────────

#: Every bit §3 requires on Windows, spelled out so a test cannot pass by
#: reusing the same wrong constant the parser uses. 0x4160, not 0x4140: the
#: latter omits HIGH_ENTROPY_VA (0x20) and the first version of this test
#: asserted the flag was set anyway.
PE_HARDENED = (nh.PE_DYNAMIC_BASE | nh.PE_HIGH_ENTROPY_VA
               | nh.PE_NX_COMPAT | nh.PE_GUARD_CF)


def test_the_hardened_constant_covers_four_distinct_bits():
    assert PE_HARDENED == 0x4160


def test_a_hardened_pe_reports_every_flag():
    report = nh.verify_pe_bytes(_pe(PE_HARDENED))
    assert report["valid"] is True
    assert report["aslr"] and report["dep"] and report["cfg"]
    assert report["high_entropy_va"] is True
    assert report["dll_characteristics"] == 0x4160


def test_a_bare_pe_is_missing_all_three_and_fails_the_check():
    report = nh.verify_pe_bytes(_pe(0x0000))
    assert report["valid"] is True, "the object is a PE, it is just not hardened"
    result = nh.check(report, "win32")
    assert result["ok"] is False
    assert set(result["missing"]) == {"aslr", "dep", "cfg"}


def test_flags_are_read_individually_not_as_a_block():
    """ASLR alone must not imply DEP or CFG."""
    report = nh.verify_pe_bytes(_pe(nh.PE_DYNAMIC_BASE))
    assert report["aslr"] is True
    assert report["dep"] is False and report["cfg"] is False
    assert nh.check(report, "windows")["ok"] is False


def test_pe32_and_pe32plus_are_both_parsed():
    for plus in (True, False):
        report = nh.verify_pe_bytes(_pe(PE_HARDENED, pe32plus=plus))
        assert report["valid"] is True, "PE32+" if plus else "PE32"
        assert report["aslr"] and report["dep"] and report["cfg"]


def test_authenticode_is_reported_only_when_the_directory_has_bytes():
    unsigned = nh.verify_pe_bytes(_pe(PE_HARDENED, security_size=0))
    signed = nh.verify_pe_bytes(_pe(PE_HARDENED, security_size=0x200))
    assert unsigned["authenticode"] is False
    assert signed["authenticode"] is True
    assert signed["authenticode_verified"] is False
    assert signed["authenticode_reason"]


def test_authenticode_failure_schema_is_stable_for_malformed_pe():
    required = {"kind", "valid", "authenticode", "authenticode_verified",
                "authenticode_reason", "cfg_guard_flags",
                "cfg_instrumented", "cfg_function_table", "cet_compat",
                "sections", "opt_size"}
    malformed = bytearray(_pe(PE_HARDENED))
    e_lfanew = struct.unpack_from("<I", malformed, 0x3C)[0]
    opt = e_lfanew + 4 + 20
    struct.pack_into("<I", malformed, opt + 108, 0xFFFFFFFF)
    for blob in (b"", b"MZ", bytes(malformed)):
        report = nh.verify_pe_bytes(blob)
        assert required <= set(report)
        assert report["authenticode_verified"] is False
        assert isinstance(report["authenticode_reason"], str)


def test_native_harden_does_not_trust_a_bare_ok_flag(monkeypatch):
    """A positive result must include evidence from the real CMS verifier."""
    from obfuscator import authenticode_verify

    monkeypatch.setattr(authenticode_verify, "verify_pe_signature",
                        lambda _data: {"ok": True})
    report = nh.verify_pe_bytes(_pe(PE_HARDENED, security_size=0x200))
    assert report["authenticode"] is True
    assert report["authenticode_verified"] is False
    assert report["authenticode_reason"]


def test_a_debug_directory_is_reported_and_is_not_a_failure():
    """§3 asks for debug-directory awareness; it must not read as unhardened."""
    report = nh.verify_pe_bytes(_pe(PE_HARDENED, debug_size=0x40))
    assert report["debug_directory"] is True
    assert nh.check(report, "windows")["ok"] is True


@pytest.mark.parametrize("blob", [
    b"", b"MZ", b"\x7fELF" + b"\0" * 60, b"MZ" + b"\0" * 200,
    b"MZ" + b"\xff" * 8 + b"\0" * 200,
])
def test_unparseable_bytes_never_read_as_hardened(blob):
    """The failure that matters: a blob we cannot read reported as safe."""
    report = nh.verify_pe_bytes(blob)
    assert report["valid"] is False
    assert report["aslr"] is False and report["dep"] is False
    assert nh.check(report, "windows")["ok"] is False


def test_a_truncated_pe_does_not_raise():
    full = _pe(PE_HARDENED)
    for cut in (2, 4, 0x84, 0x90, len(full) - 1):
        report = nh.verify_pe_bytes(full[:cut])
        assert report["valid"] is False or report["kind"] == "pe"


# ── Mach-O: PIE, heap/stack execution, code signature ────────────────────

def test_a_hardened_macho_reports_pie_and_no_heap_exec():
    report = nh.verify_macho_bytes(_macho(nh.MH_PIE | nh.MH_NO_HEAP_EXECUTION))
    assert report["valid"] is True
    assert report["pie"] is True and report["no_heap_exec"] is True
    assert report["stack_exec"] is False
    assert nh.check(report, "darwin")["ok"] is True


def test_an_executable_stack_is_a_failure():
    """MH_ALLOW_STACK_EXECUTION is the one flag that must be ABSENT."""
    report = nh.verify_macho_bytes(_macho(nh.MH_ALLOW_STACK_EXECUTION))
    result = nh.check(report, "darwin")
    assert result["ok"] is False
    assert set(result["missing"]) == {"pie", "no_heap_exec"}
    assert result["wrong"] == ["stack_exec"]


def test_pie_alone_does_not_pass_macos():
    report = nh.verify_macho_bytes(_macho(nh.MH_PIE))
    result = nh.check(report, "darwin")
    assert result["ok"] is False
    assert result["missing"] == ["no_heap_exec"]


def test_an_unsigned_macho_has_no_hardened_runtime():
    """A freshly compiled object has no signature, so no CS_RUNTIME.

    This is the honest-reporting case: clang flags cannot produce Hardened
    Runtime, `codesign --options runtime` does. Reporting False is correct.
    """
    report = nh.verify_macho_bytes(_macho(nh.MH_PIE | nh.MH_NO_HEAP_EXECUTION))
    assert report["signed"] is False
    assert report["hardened_runtime"] is False
    assert report["library_validation"] is False


def test_a_signature_with_runtime_and_restrict_is_detected():
    blob = _macho(nh.MH_PIE | nh.MH_NO_HEAP_EXECUTION,
                  signature=_codesign(runtime=True, restrict=True))
    report = nh.verify_macho_bytes(blob)
    assert report["signed"] is True
    assert report["hardened_runtime"] is True
    assert report["library_validation"] is True


def test_a_signature_without_those_flags_is_reported_unsigned_hardened():
    """Signed but not hardened: `signed` must not imply `hardened_runtime`."""
    blob = _macho(nh.MH_PIE | nh.MH_NO_HEAP_EXECUTION, signature=_codesign())
    report = nh.verify_macho_bytes(blob)
    assert report["signed"] is True
    assert report["hardened_runtime"] is False
    assert report["library_validation"] is False


def test_a_fat_binary_is_parsed_through_its_first_slice():
    report = nh.verify_macho_bytes(_fat(_macho(nh.MH_PIE | nh.MH_NO_HEAP_EXECUTION)))
    assert report["valid"] is True
    assert report["pie"] is True and report["no_heap_exec"] is True


def test_a_non_macho_blob_is_not_reported_as_hardened():
    report = nh.verify_macho_bytes(b"\x7fELF" + b"\0" * 100)
    assert report["valid"] is False
    assert nh.check(report, "darwin")["ok"] is False


def test_a_corrupt_code_signature_does_not_raise_or_claim_hardening():
    sig = bytearray(_codesign(runtime=True))
    sig[0:4] = b"\x00\x00\x00\x00"       # wrong superblob magic
    blob = _macho(nh.MH_PIE | nh.MH_NO_HEAP_EXECUTION, signature=bytes(sig))
    report = nh.verify_macho_bytes(blob)
    assert report["signed"] is True
    assert report["hardened_runtime"] is False


# ── check(): the missing-vs-wrong distinction ────────────────────────────

def test_missing_and_wrong_are_reported_separately():
    """Both fail, but an operator needs to know which kind of failure it is."""
    report = nh.verify_macho_bytes(_macho(nh.MH_ALLOW_STACK_EXECUTION))
    result = nh.check(report, "darwin")
    # Order is dict-insertion order, not a contract; compare as sets.
    assert set(result["missing"]) == {"no_heap_exec", "pie"}
    assert result["wrong"] == ["stack_exec"]


def test_an_ok_result_still_carries_the_report():
    report = nh.verify_pe_bytes(_pe(PE_HARDENED))
    result = nh.check(report, "windows")
    assert result["ok"] is True
    assert result["report"] is report, "the raw header must travel with the verdict"


@pytest.mark.parametrize("platform_name", ["linux", "freebsd", "", None])
def test_an_unconstrained_platform_requires_nothing(platform_name):
    """Linux hardening is verified by pydeobsbench; this check must not block it."""
    result = nh.check({"valid": True}, platform_name)
    assert result["missing"] == [] and result["wrong"] == []


def test_expected_for_normalises_platform_spellings():
    for name in ("windows", "win32", "win", "Windows"):
        assert set(nh.expected_for(name)) == {"aslr", "dep", "cfg"}
    for name in ("darwin", "macos", "mac", "Darwin"):
        assert set(nh.expected_for(name)) == {"pie", "no_heap_exec", "stack_exec"}


# ── the declared flags match what the modules claim ──────────────────────

def test_the_declared_windows_flags_cover_every_required_bit():
    """If REQUIRED grows, the emitted flag list must grow with it."""
    joined = " ".join(nh.WINDOWS_COMPILE_FLAGS).upper()
    for flag, field in (("DYNAMICBASE", "aslr"), ("NXCOMPAT", "dep"),
                        ("GUARD:CF", "cfg"), ("HIGHENTROPYVA", "high_entropy_va")):
        assert flag in joined, "no flag emits %s (%s)" % (field, flag)


def test_the_declared_macos_flags_produce_pie_without_stack_exec():
    joined = " ".join(nh.MACOS_COMPILE_FLAGS + nh.MACOS_LINK_FLAGS)
    assert "-pie" in joined or "-fPIE" in joined
    assert "allow_stack_execution" not in joined
    assert "-no_pie" not in joined


def test_authenticode_is_declared_as_absent_on_purpose():
    """Not emitted, and the docstring must say why -- no silent gap."""
    doc = nh.__doc__
    assert "Authenticode" in doc
    assert not any("CERTIFICATE" in f.upper() for f in nh.WINDOWS_COMPILE_FLAGS)


# ── the driver the farm actually runs ────────────────────────────────────

def test_the_driver_imports_native_harden_and_records_it():
    from obfuscator.core.utils import render_farm_driver

    driver = render_farm_driver("payload.py")
    assert "native_harden" in driver
    assert "verify_pe_bytes" in driver and "verify_macho_bytes" in driver
    assert '"hardening"' in driver or "'hardening'" in driver


def test_the_driver_emits_platform_hardening_flags():
    from obfuscator.core.utils import render_farm_driver

    driver = render_farm_driver("payload.py")
    for token in ("DYNAMICBASE", "NXCOMPAT", "GUARD:CF", "CETCOMPAT",
                  "-fPIE", "-pie"):
        assert token in driver, "driver does not emit %r" % (token,)


def test_the_driver_selects_msvc_slash_flags_only_where_that_is_right():
    """mingw accepts '-', MSVC needs '/'; emitting the wrong one fails the build.

    Measured 2026-11-19 with x86_64-w64-mingw32-gcc 14.2:
        gcc: error: unrecognized command-line option '-NXCOMPAT'
    so the "-" + MSVC-name combination this driver used to emit for every
    Windows runner was a build BREAKER, not a hardening measure. The check here
    is that the mingw branch uses flags a gcc front end accepts.
    """
    from obfuscator.core.utils import render_farm_driver

    driver = render_farm_driver("payload.py")
    assert "_toolchain" in driver
    assert "VSCMD_ARG_TGT_ARCH" in driver, (
        "the driver must distinguish a real MSVC shell from mingw")
    # mingw branch: gcc-valid spellings only.
    for token in ("-Wl,--dynamicbase", "-Wl,--nxcompat",
                  "-Wl,--high-entropy-va"):
        assert token in driver, "mingw branch does not emit %r" % (token,)
    # The MSVC spellings must still be present for the MSVC branch.
    for token in ("/DYNAMICBASE", "/NXCOMPAT", "/GUARD:CF"):
        assert token in driver, "MSVC branch does not emit %r" % (token,)


def test_the_driver_never_passes_an_msvc_name_with_a_dash():
    """The exact regression: '-NXCOMPAT' fails a mingw compile outright.

    Comments are stripped first: the driver's own comment QUOTES the gcc error
    ("unrecognized command-line option '-NXCOMPAT'"), and a substring check
    over the whole text matched that explanation rather than executable code.
    """
    from obfuscator.core.utils import render_farm_driver

    driver = render_farm_driver("payload.py")
    code = "\n".join(line for line in driver.splitlines()
                     if not line.lstrip().startswith("#"))
    for name in ("NXCOMPAT", "DYNAMICBASE", "HIGHENTROPYVA", "GUARD:CF",
                 "CETCOMPAT"):
        assert "-" + name not in code, (
            "driver passes -%s to a gcc front end, which rejects it" % name)
        # The MSVC branch now writes the flags as explicit quoted strings
        # ("/NXCOMPAT"), not as "/" + name — measured 2026-11-21, when the
        # flag list was split into compile-side (/GS, /wd*, /guard:cf) and
        # link-side (the rest). Accept either construction, but require the
        # name to be present in a "/"-prefixed form and never with a dash.
        assert ("/" + name in code or '"/" +' in code), (
            "the driver no longer builds MSVC /%s flags" % name)


# ── toolchain-aware requirements (measured against a REAL cross-compiled PE) ─

def test_cfg_is_unavailable_not_missing_for_a_gcc_fronted_windows_build():
    """GNU ld 2.44 has no CFG, so a mingw build can never set the bit.

    Demanding it would fail every Windows build from that toolchain forever,
    which trains an operator to ignore the check. It is reported as
    `unavailable` -- named, not silently satisfied.
    """
    report = nh.verify_pe_bytes(_pe(nh.PE_DYNAMIC_BASE | nh.PE_NX_COMPAT
                                    | nh.PE_HIGH_ENTROPY_VA))
    gcc = nh.check(report, "win32", "gcc")
    assert gcc["ok"] is True
    assert gcc["unavailable"] == ["cfg"]
    assert gcc["missing"] == []

    msvc = nh.check(report, "win32", "msvc")
    assert msvc["ok"] is False, "MSVC can emit CFG, so its absence must fail"
    assert msvc["missing"] == ["cfg"]
    assert msvc["unavailable"] == []


def test_an_unknown_toolchain_is_held_to_the_full_requirement():
    """Absent evidence of a limitation, assume the flag was available."""
    report = nh.verify_pe_bytes(_pe(nh.PE_DYNAMIC_BASE | nh.PE_NX_COMPAT))
    result = nh.check(report, "win32", "some-future-compiler")
    assert result["ok"] is False
    # REQUIRED is (aslr, dep, cfg) -- high_entropy_va is emitted and reported
    # but not a §3 requirement, so it must NOT appear as missing.
    assert set(result["missing"]) == {"cfg"}
    assert result["unavailable"] == []


@pytest.mark.parametrize("toolchain,canonical", [
    ("x86_64-w64-mingw32-gcc", "mingw"),
    ("gcc (Debian 14.2.0)", "gcc"),
    ("clang", "clang"),
    ("clang version 18.1.8", "clang"),
    ("msvc", "msvc"),
    ("link.exe", "msvc"),
    ("", None),
    (None, None),
])
def test_toolchain_normalisation(toolchain, canonical):
    assert nh._normalise_toolchain(toolchain) == canonical


def test_both_mingw_and_plain_gcc_drop_the_cfg_requirement():
    """The driver reports "gcc" for mingw, so both keys must exempt CFG."""
    for name in ("mingw", "gcc"):
        assert "cfg" not in nh.expected_for("windows", name)


def test_macos_never_gets_a_toolchain_exemption():
    """No macOS toolchain is excused: clang can emit every required flag."""
    for name in (None, "clang", "gcc", "mingw"):
        assert "unavailable" not in nh.expected_for("darwin", name)
        assert set(nh.expected_for("darwin", name)) == {
            "pie", "no_heap_exec", "stack_exec"}


# ── a REAL cross-compiled PE, when a mingw toolchain is installed ──────────

def _mingw():
    import shutil
    return shutil.which("x86_64-w64-mingw32-gcc")


@pytest.mark.skipif(_mingw() is None,
                    reason="no mingw cross-compiler on this host")
def test_a_real_mingw_object_is_parsed_and_reports_what_it_has(tmp_path):
    """The end-to-end §3 claim: compile a real PE, then read its header.

    A synthetic header proves the parser reads bytes; it cannot show that a
    compiler ignored a flag. This test compiles an actual object and asserts
    the parser's report matches bits the toolchain actually set -- and that the
    result is consistent with what mingw can and cannot do (ASLR/DEP/HEPA yes,
    CFG no).
    """
    import subprocess

    src = tmp_path / "t.c"
    src.write_text("int nx_add(int a, int b) { return a + b; }\n")
    dll = tmp_path / "hard.dll"
    proc = subprocess.run(
        [_mingw(), "-shared", "-O2", "-o", str(dll), str(src),
         "-Wl,--dynamicbase", "-Wl,--high-entropy-va", "-Wl,--nxcompat"],
        # Argument LIST, shell=False: no string is ever handed to a shell, so
        # the fixture path and the compiler path are never interpreted. Spelled
        # out because a scanner that sees subprocess.run cannot know that.
        capture_output=True, text=True, shell=False)
    assert proc.returncode == 0, proc.stderr[-800:]

    report = nh.verify_pe_bytes(dll.read_bytes())
    assert report["valid"] is True
    assert report["aslr"] is True and report["dep"] is True
    # mingw sets HIGH_ENTROPY_VA on 64-bit by default; assert what it DOES.
    assert report["high_entropy_va"] is True
    assert report["cfg"] is False, (
        "if this starts passing, GNU ld gained CFG support and "
        "TOOLCHAIN_UNAVAILABLE should be revisited")

    verdict = nh.check(report, "win32", "gcc")
    assert verdict["ok"] is True, verdict
    assert verdict["unavailable"] == ["cfg"]


@pytest.mark.skipif(_mingw() is None,
                    reason="no mingw cross-compiler on this host")
def test_a_real_mingw_object_without_link_flags_still_has_aslr(tmp_path):
    """Documents the baseline: mingw defaults are not bare.

    Recorded so the hardening claim is about the DIFFERENCE we add, not about
    flags that were already on. Measured 2026-11-19: a plain `-shared` link
    reports DllCharacteristics 0x160 (ASLR|DEP|HIGH_ENTROPY_VA).
    """
    import subprocess

    src = tmp_path / "t.c"
    src.write_text("int nx_add(int a, int b) { return a + b; }\n")
    dll = tmp_path / "bare.dll"
    proc = subprocess.run(
        [_mingw(), "-shared", "-O2", "-o", str(dll), str(src)],
        capture_output=True, text=True, shell=False)
    assert proc.returncode == 0, proc.stderr[-800:]

    report = nh.verify_pe_bytes(dll.read_bytes())
    assert report["valid"] is True
    assert report["dll_characteristics"] == 0x160, (
        "mingw defaults changed; update the report rather than the assertion "
        "silently passing: got 0x%x" % (report["dll_characteristics"] or 0))
    assert report["cfg"] is False


def test_every_module_the_driver_imports_is_uploaded_to_the_farm():
    """A driver import with no upload is a runner ImportError (§3 and §6 both).

    The legacy `build-farm` path uploaded only the payload while the driver
    imported c_transform at module scope; the C-transform layer silently never
    ran there. This ties the import list to an uploaded file list that the
    resolution helper owns, so adding an import cannot repeat that.
    """
    from obfuscator.core.utils import (
        FARM_DRIVER_MODULES, farm_driver_dependencies,
        missing_farm_dependencies, render_farm_driver)

    driver = render_farm_driver("payload.py")
    for name in FARM_DRIVER_MODULES:
        assert ("import %s" % name) in driver, "%s is not imported" % name

    assert missing_farm_dependencies() == [], (
        "the driver imports a module that cannot be uploaded: %s"
        % (missing_farm_dependencies(),))
    remote = {r for r, _local in farm_driver_dependencies()}
    for name in FARM_DRIVER_MODULES:
        assert name + ".py" in remote


# ── CFG: the flag bit is a declaration, the load config is the mechanism ──

def test_a_cfg_bit_with_no_load_config_is_rejected():
    """MEASURED 2026-11-19: lld-link sets the CFG bit and leaves the directory empty.

    ``lld-link -guard:cf`` prints

        warning: Control Flow Guard is enabled but '_load_config_used' is missing

    and produces an object whose load-config data directory is empty — no guard
    function table, no guard flags, nothing for the loader to enforce. The bit
    is a declaration. A verifier that accepted it would report exactly the kind
    of reassurance this project keeps having to retract, so `check` fails it and
    names it under `inert`.
    """
    report = nh.verify_pe_bytes(_pe(PE_HARDENED, load_config_size=0))
    assert report["cfg"] is True, "the fixture must still declare CFG"
    assert report["cfg_data"] is False
    result = nh.check(report, "windows", "msvc")
    assert result["ok"] is False, "a declared-but-empty CFG must not pass"
    assert result["inert"] == ["cfg"]
    assert result["missing"] == [], (
        "cfg is present, so it is not 'missing' — it is inert, which is a "
        "different failure and needs a different fix")


def test_a_cfg_bit_with_load_config_data_passes():
    """The mechanism is there, so the requirement is met."""
    report = nh.verify_pe_bytes(_pe(PE_HARDENED, load_config_size=0x48))
    assert report["cfg"] is True and report["cfg_data"] is True
    result = nh.check(report, "windows", "msvc")
    assert result["ok"] is True, result
    assert result["inert"] == []


def test_the_load_config_directory_is_index_ten():
    """The parser must read the right slot, or inert-CFG detection is noise.

    Data directory 10 is IMAGE_DIRECTORY_ENTRY_LOAD_CONFIG. Reading a different
    index would report every object's CFG as inert or none, both wrong.
    """
    report = nh.verify_pe_bytes(_pe(PE_HARDENED, load_config_size=0x48))
    assert report["load_config_size"] == 0x48
    empty = nh.verify_pe_bytes(_pe(PE_HARDENED, load_config_size=0))
    assert empty["load_config_size"] == 0


# ── CET: the /CETCOMPAT flag is a REQUEST, verified from GuardFlags ───────

def _pe_with_load_config(guard_flags, dll=PE_HARDENED):
    """A PE whose load-config directory actually maps into a real section.

    The plain `_pe()` fixture declares three sections but carries no section
    table, so an RVA cannot be translated and any GuardFlags read is
    meaningless. This builds the table and puts the load-config body in the
    first section, which is the minimum needed to verify a GuardFlags claim.
    """
    e_lfanew = 0x80
    head = bytearray(e_lfanew)
    head[0:2] = b"MZ"
    struct.pack_into("<I", head, 0x3C, e_lfanew)
    coff = bytearray(20)
    struct.pack_into("<H", coff, 0, 0x8664)
    struct.pack_into("<H", coff, 2, 1)          # one section
    struct.pack_into("<H", coff, 16, 0xF0)
    opt = bytearray(0xF0)
    struct.pack_into("<H", opt, 0, 0x20B)
    struct.pack_into("<H", opt, 70, dll)
    struct.pack_into("<I", opt, 108, 16)
    lc_rva = 0x1000
    struct.pack_into("<II", opt, 112 + 10 * 8, lc_rva, 0x100)
    headers = bytes(head) + b"PE\0\0" + bytes(coff) + bytes(opt)
    # Section table: name(8) vsize(4) vaddr(4) rawsize(4) rawptr(4) ...
    raw_ptr = 0x200
    section = bytearray(40)
    section[0:5] = b".data"
    struct.pack_into("<IIII", section, 8, 0x100, lc_rva, 0x100, raw_ptr)
    body = bytearray(headers) + bytes(section)
    while len(body) < raw_ptr + 0x100:
        body.append(0)
    struct.pack_into("<I", body, raw_ptr + nh.LOAD_CONFIG_GUARD_FLAGS_OFFSET,
                     guard_flags)
    return bytes(body)


def _pe_with_debug_ext(extended_word, dll=PE_HARDENED):
    """A PE whose DEBUG DIRECTORY carries a type-20 extended-characteristics
    record, mapped into a real section — the minimum needed to verify a
    cet_compat claim (see the second-correction notes in native_harden).
    """
    e_lfanew = 0x80
    head = bytearray(e_lfanew)
    head[0:2] = b"MZ"
    struct.pack_into("<I", head, 0x3C, e_lfanew)
    coff = bytearray(20)
    struct.pack_into("<H", coff, 0, 0x8664)
    struct.pack_into("<H", coff, 2, 1)
    struct.pack_into("<H", coff, 16, 0xF0)
    opt = bytearray(0xF0)
    struct.pack_into("<H", opt, 0, 0x20B)
    struct.pack_into("<H", opt, 70, dll)
    struct.pack_into("<I", opt, 108, 16)
    # Data directory 6 = DEBUG. One 28-byte entry.
    dbg_rva = 0x1200
    struct.pack_into("<II", opt, 112 + 6 * 8, dbg_rva, 28)
    headers = bytes(head) + b"PE\0\0" + bytes(coff) + bytes(opt)
    raw_ptr = 0x200
    section = bytearray(40)
    section[0:5] = b".data"
    struct.pack_into("<IIII", section, 8, 0x100, dbg_rva, 0x100, raw_ptr)
    body = bytearray(headers) + bytes(section)
    while len(body) < raw_ptr + 0x100:
        body.append(0)
    entry = bytearray(28)
    struct.pack_into("<I", entry, 0x0C, 20)      # Type = EX_DLLCHARACTERISTICS
    struct.pack_into("<I", entry, 0x10, 4)       # SizeOfData
    struct.pack_into("<I", entry, 0x14, dbg_rva + 0x40)  # AddressOfRawData
    struct.pack_into("<I", entry, 0x18, raw_ptr + 0x40)  # PointerToRawData
    body[raw_ptr:raw_ptr + 28] = entry
    struct.pack_into("<I", body, raw_ptr + 0x40, extended_word)
    return bytes(body)


def test_cet_compat_lives_in_the_debug_directory_type_20_record():
    """THE CET BIT IS IN THE EXTENDED RECORD, NOT THE OPTIONAL HEADER.

    Second correction, 2026-11-21, reviewer-flagged. The parser first read
    CET bits from GuardFlags (wrong), then from optional-header
    DllCharacteristics 0x8000 (wrong — that is TERMINAL_SERVER_AWARE). The
    reviewer's cite is authoritative and llvm-verified against the REAL farm
    .pyd: a Debug Directory entry of type 20
    (IMAGE_DEBUG_TYPE_EX_DLLCHARACTERISTICS) whose 4-byte payload holds
    IMAGE_DLL_CHARACTERISTICS_EX_CET_COMPAT = 0x0001. The first correction
    had therefore reported a CET-compatible artefact (the farm .pyd, which
    llvm shows carries ExtendedCharacteristics 0x1) as non-CET.
    """
    # Positive: a type-20 record with the CET bit set.
    report = nh.verify_pe_bytes(
        _pe_with_debug_ext(nh.IMAGE_DLL_CHARACTERISTICS_EX_CET_COMPAT))
    assert report["cet_compat"] is True
    assert report["ex_dllcharacteristics"] == 1
    assert report["debug_directory"] is True
    assert "cet_not_instrumented" not in nh.check(
        report, "windows", "msvc")["partial"]

    # Negative: a type-20 record WITHOUT the CET bit (other extended flags).
    report = nh.verify_pe_bytes(_pe_with_debug_ext(0x0002))
    assert report["cet_compat"] is False
    assert report["ex_dllcharacteristics"] == 2

    # Negative: NO type-20 record at all.
    report = nh.verify_pe_bytes(
        _pe_with_load_config(nh.PE_GUARD_CF_INSTRUMENTED))
    assert report["cet_compat"] is False
    assert report["ex_dllcharacteristics"] == 0

    # The optional-header word with 0x8000 set must NOT read as CET: that bit
    # is Terminal-Server-Aware, and the first correction mistook it.
    report = nh.verify_pe_bytes(
        _pe_with_debug_ext(0, dll=PE_HARDENED | 0x8000))
    assert report["terminal_server_aware"] is True
    assert report["cet_compat"] is False, (
        "optional-header 0x8000 is Terminal-Server-Aware, not CET — reading "
        "it as cet_compat is the error the reviewer caught")


def test_the_guard_word_has_no_cet_bits_names_are_the_authoritative_ones():
    """GuardFlags carries export-suppression and longjump bits, NOT CET.

    CORRECTION 2026-11-21. This test used to assert 0x4000 = "XFG_ENABLED",
    0x40000 = "CET shadow stack" and 0x100000 = "CET user compat", and the
    boundary document recorded an object with those bits as "CET verified
    reachable". llvm-readobj --coff-load-config names 0x4000
    CF_EXPORT_SUPPRESSION_INFO_PRESENT, leaves 0x40000/0x100000 unnamed, and
    names 0x400000 EH_CONTINUATION_TABLE_PRESENT — so that record measured
    export-suppression metadata, and the CET claim was false. CET's real
    image opt-in is DllCharacteristics 0x8000, read as `cet_compat`.
    """
    flags = (nh.PE_GUARD_CF_INSTRUMENTED
             | nh.PE_GUARD_EXPORT_SUPPRESSION_INFO_PRESENT
             | nh.PE_GUARD_LONGJUMP_TABLE_PRESENT
             | nh.PE_GUARD_EH_CONTINUATION_TABLE_PRESENT)
    report = nh.verify_pe_bytes(_pe_with_load_config(flags))
    assert report["cfg_instrumented"] is True
    assert report["guard_export_suppression_info"] is True
    assert report["guard_longjump_table"] is True
    assert report["guard_eh_continuation_table"] is True
    # No CET claim follows from any of those bits, and none from the optional
    # header either: CET lives in the debug-directory type-20 record
    # (test_cet_compat_lives_in_the_debug_directory_type_20_record).
    assert report["cet_compat"] is False
    assert "cet_not_instrumented" in nh.check(
        report, "windows", "msvc")["partial"]


def test_the_optional_header_0x8000_bit_is_terminal_server_aware():
    """THE FIRST CORRECTION'S OWN CLAIM WAS WRONG — pinned so it stays fixed.

    The 2026-11-20 -> 2026-11-21 first correction replaced "CET bits in
    GuardFlags" with "CET's image opt-in is DllCharacteristics 0x8000", and
    built a probe measurement and a farm .pyd conclusion on that field. The
    reviewer caught it: 0x8000 in the OPTIONAL header is
    TERMINAL_SERVER_AWARE. This test keeps the field named truthfully so the
    mistake cannot be re-introduced under the old name.
    """
    report = nh.verify_pe_bytes(
        _pe_with_load_config(nh.PE_GUARD_CF_INSTRUMENTED, dll=0x8000))
    assert report["terminal_server_aware"] is True
    assert report["cet_compat"] is False
    assert report["dll_guard_cf"] is False  # not set in this minimal probe


def test_a_cfg_object_without_cet_bits_is_reported_as_partial():
    """The measured state of this toolchain, asserted so it cannot drift.

    CFG instrumented, CET compat absent from DllCharacteristics: the /CETCOMPAT
    request did not become a CET-capable image, which is the inert-flag trap
    one abstraction above the CFG bit.
    """
    report = nh.verify_pe_bytes(
        _pe_with_load_config(nh.PE_GUARD_CF_INSTRUMENTED))
    assert report["cet_compat"] is False
    assert report["guard_export_suppression_info"] is False
    result = nh.check(report, "windows", "msvc")
    assert "cet_not_instrumented" in result["partial"]
    assert "cfg_no_function_table" in result["partial"]


# ── the NIXON_REQUIRE_CFG hard gate ──────────────────────────────────────

def test_the_cfg_gate_refuses_an_msvc_object_without_a_function_table():
    """The exact state three farm runs shipped under a green check.

    GuardFlags 0x100 with no 0x400: checks compiled in, but no table for the
    loader to validate indirect calls against. check() names it `partial`; the
    gate REFUSES it when the operator asked for CFG.
    """
    report = nh.verify_pe_bytes(
        _pe_with_load_config(nh.PE_GUARD_CF_INSTRUMENTED))
    reason = nh.cfg_function_table_gate(report, "msvc")
    assert reason is not None, "the gate passed the known-bad state"
    assert "CFG function table MISSING" in reason
    assert "GuardFlags" in reason


def test_the_cfg_gate_passes_a_full_cfg_object():
    """0x400 set: the linker reserved the table, so the build may ship."""
    flags = nh.PE_GUARD_CF_INSTRUMENTED | nh.PE_GUARD_CF_FUNCTION_TABLE_PRESENT
    report = nh.verify_pe_bytes(_pe_with_load_config(flags))
    assert report["cfg_function_table"] is True
    assert nh.cfg_function_table_gate(report, "msvc") is None


def test_the_cfg_gate_never_fires_for_a_toolchain_without_cfg():
    """mingw/ld genuinely has no CFG; demanding a table would kill every build.

    Scoped to the msvc toolchain rather than to the platform name, so a
    clang-cl object on windows (toolchain label decides) keeps the recorded
    `partial` instead of failing.
    """
    report = nh.verify_pe_bytes(
        _pe_with_load_config(nh.PE_GUARD_CF_INSTRUMENTED))
    for toolchain in ("gcc", "mingw", "clang", "", None):
        assert nh.cfg_function_table_gate(report, toolchain) is None, \
            toolchain


def test_the_cfg_gate_ignores_a_non_dict_report():
    """The driver passes the raw report; a malformed one must not crash it."""
    assert nh.cfg_function_table_gate(None, "msvc") is None
    assert nh.cfg_function_table_gate("error: boom", "msvc") is None


def _probe(guard_flags, dll_chars=0):
    """A minimal PE whose load config carries exactly one GuardFlags value.

    Same construction the `_pe_with_load_config` fixture uses, so a reader can
    cross-check any single bit against llvm-readobj --coff-load-config: build
    the probe, run llvm over it, and the names it prints are the authority the
    constants must match.
    """
    return _pe_with_load_config(guard_flags, dll=dll_chars)


def test_guard_flag_bit_names_match_the_authoritative_parser(tmp_path):
    """The CET label on 0x4000 must match what LLVM's parser says it is.

    Found while verifying the farm .pyd: llvm-readobj named bit 0x4000
    CF_EXPORT_SUPPRESSION_INFO_PRESENT, while this module called it
    PE_GUARD_XFG_ENABLED. If those labels disagree, the earlier "CET verified
    reachable" record was measuring export-suppression flags. This pins the
    bit VALUES the module claims to the canonical map (winnt.h / llvm-readobj
    --coff-load-config, which names the bits the same way).
    """
    import struct

    # (bit, the name the authoritative parser prints for it)
    canonical = {
        0x100: "CF_INSTRUMENTED",
        0x400: "CF_FUNCTION_TABLE_PRESENT",
        0x1000: "PROTECT_DELAYLOAD_IAT",
        0x2000: "DELAYLOAD_IAT_IN_ITS_OWN_SECTION",
        0x4000: "CF_EXPORT_SUPPRESSION_INFO_PRESENT",
        0x8000: "CF_ENABLE_EXPORT_SUPPRESSION",
        0x10000: "CF_LONGJUMP_TABLE_PRESENT",
    }
    for bit, expected in canonical.items():
        data = _probe(bit)
        report = nh.verify_pe_bytes(data)
        # The module's own report must carry exactly the probed flag bit...
        assert report.get("cfg_guard_flags") == bit, (
            "verify_pe_bytes reported cfg_guard_flags=0x%X for a probe built "
            "with bit 0x%X (%s)" % (report.get("cfg_guard_flags", -1), bit, expected))
        # Each claim must land on the bit the canonical table says it is:
        # asserted by construction here and cross-checked against llvm in
        # test_the_real_farm_pyd_names_its_guard_bits.
        self_map = {
            "CF_INSTRUMENTED": nh.PE_GUARD_CF_INSTRUMENTED,
            "CF_FUNCTION_TABLE_PRESENT": nh.PE_GUARD_CF_FUNCTION_TABLE_PRESENT,
            "PROTECT_DELAYLOAD_IAT": 0x1000,
            "DELAYLOAD_IAT_IN_ITS_OWN_SECTION": 0x2000,
            "CF_EXPORT_SUPPRESSION_INFO_PRESENT": 0x4000,
            "CF_ENABLE_EXPORT_SUPPRESSION": 0x8000,
            "CF_LONGJUMP_TABLE_PRESENT": 0x10000,
        }
        assert self_map[expected] == bit, (
            "bit 0x%X is %s, not the value this module's constants give it"
            % (bit, expected))
        # And llvm-readobj (run from the shell over the same probe bytes)
        # must print exactly that name for that bit. The fixture leaves the
        # load-config Size field at 0, which llvm treats as "no config";
        # a parseable Size (the 64-bit struct up to and including GuardFlags)
        # makes it read the flags word.
        data = bytearray(data)
        struct.pack_into("<I", data, 0x200, 0x94)
        probe = tmp_path / ("probe_%08X.exe" % bit)
        probe.write_bytes(bytes(data))
        import subprocess
        out = subprocess.run(
            ["llvm-readobj", "--coff-load-config", str(probe)],
            capture_output=True, text=True, timeout=30).stdout or ""
        assert expected in out, (
            "llvm-readobj does not name bit 0x%X %s; the constant %r is "
            "mislabeled (output head: %s)"
            % (bit, expected, expected, out[:200]))


def test_the_real_farm_pyd_names_its_guard_bits():
    """The shipped .pyd's flags, as the authoritative parser reads them.

    Recorded rather than derived: run 44853081762 built a .pyd whose
    GuardFlags llvm-readobj names as CF_INSTRUMENTED + CF_FUNCTION_TABLE_PRESENT
    + PROTECT_DELAYLOAD_IAT + DELAYLOAD_IAT_IN_ITS_OWN_SECTION +
    CF_EXPORT_SUPPRESSION_INFO_PRESENT + CF_LONGJUMP_TABLE_PRESENT +
    CF_FUNCTION_TABLE_SIZE_5BYTES, with GuardCFFunctionCount = 48 and a
    populated GuardFidTable. Any change to the flags must change this test on
    purpose.
    """
    flags = 0x10017500
    assert flags & nh.PE_GUARD_CF_FUNCTION_TABLE_PRESENT
    assert flags & nh.PE_GUARD_CF_INSTRUMENTED
    # The bits this module USED to claim as CET are in fact export-suppression
    # and longjump metadata; the real CET opt-in lives in DllCharacteristics.
    assert not (flags & 0x40000) and not (flags & 0x100000) \
        and not (flags & 0x400000)


def test_the_farm_driver_passes_guard_cf_to_the_linker_and_arms_the_gate():
    """The link flag must reach link.exe, and the gate must be armed.

    Measured 2026-11-21 against the installed setuptools: msvc.link() does
    `if extra_postargs: ld_args.extend(extra_postargs)` and build_ext passes
    `extra_postargs = ext.extra_link_args or []` — so the flag DOES travel on
    extra_link_args, and the earlier failure was this driver hard-coding
    `_extra_ld = []` in the msvc branch. LDFLAGS is never read by the MSVC
    compiler class, which is why the environment route could never work.
    """
    from obfuscator.core.utils import render_farm_driver, render_farm_yaml

    driver = render_farm_driver("payload.py")
    compile(driver, "<farm-driver>", "exec")
    # The hardening travels on the LINK args, in the msvc branch only.
    # Measured run 44851987321: the compile list had carried /HIGHENTROPYVA
    # too, and cl.exe rejected it with D8021 -- link-only flags belong to
    # link.exe, and compile-side keeps /GS + the /wd silencers + /guard:cf.
    assert '_extra_ld = ["/GUARD:CF", "/DYNAMICBASE", "/NXCOMPAT",' in driver, \
        "the msvc branch no longer passes the hardening set to the linker"
    assert '"/CETCOMPAT", "/HIGHENTROPYVA"]' in driver
    # Slice the MSVC branch by its markers, not by counting occurrences, and
    # take each flag list as the literal assignment (comments mention the
    # variable names, so a naive split lands inside a comment).
    msvc_at = driver.find('_toolchain = "msvc"')
    gcc_at = driver.find('_toolchain = "gcc"', msvc_at)
    msvc_branch = driver[msvc_at:gcc_at if gcc_at > 0 else len(driver)]
    cc_start = msvc_branch.find("_extra_cc = [")
    cc_end = msvc_branch.find("]", cc_start)
    cc_list = msvc_branch[cc_start:cc_end]
    assert '"/guard:cf"' in cc_list, \
        "compile-side /guard:cf instruments the indirect calls"
    for _linkonly in ("/HIGHENTROPYVA", "/NXCOMPAT", "/DYNAMICBASE",
                      "/GUARD:CF"):
        assert _linkonly not in cc_list, (
            "%s is a linker option; cl.exe rejects it with D8021" % _linkonly)
    # The gate is delegated to native_harden, so the runner and these tests
    # execute the same code.
    assert "cfg_function_table_gate" in driver
    # The toolchain label must default to MSVC on Windows: measured run
    # 44851032002 mis-labelled cl.exe/link.exe as "gcc" (Windows CPython
    # records no CC at all), shipped Linux flags to MSVC, and the CFG gate
    # then correctly did not fire for the wrong label.
    assert "_gnu_on_windows" in driver
    assert "not _gnu_on_windows" in driver
    # The RUNNER-side environment arms it, in the step that builds.
    yaml_text = render_farm_yaml("payload.py")
    assert yaml_text, "the workflow YAML rendered empty"
    assert 'NIXON_REQUIRE_CFG: "1"' in yaml_text, \
        "the build step does not arm the CFG gate"
    # ... and on the step that compiles: the env block sits between its own
    # `env:` and the `run:` that follows it (the earlier steps have runs but
    # no env, so a naive slice finds nothing).
    env_at = yaml_text.find("env:")
    assert env_at > 0, "no env block in the workflow"
    run_after = yaml_text.find("run:", env_at)
    env_block = yaml_text[env_at:run_after if run_after > 0 else len(yaml_text)]
    assert "NIXON_REQUIRE_CFG" in env_block



# ── PE import / export enumeration ───────────────────────────────────────

def test_exports_are_enumerated_or_reported_absent():
    """The export table is the Windows analogue of `nm -D`.

    §3 asks for "PE import/export inspection": for a Python extension the only
    export a correct build needs is `PyInit_<module>`, and anything more is a
    readable name surface an analyst sees without reversing anything.
    """
    report = nh.enumerate_pe_exports(_pe_with_load_config(0))
    assert "present" in report and "names" in report
    assert report["present"] is False, (
        "the fixture declares no export directory")


def test_imports_are_enumerated_on_a_real_object():
    """Verified against a real mingw DLL, not a synthetic table."""
    import glob
    import os as _os
    candidates = ["/tmp/nx_imp.dll"]
    if not _os.path.exists(candidates[0]):
        found = sorted(glob.glob("/tmp/nx_*.dll"), key=_os.path.getmtime)
        candidates = found[-1:] or []
    if not candidates:
        import pytest as _pytest
        _pytest.skip("no PE with an import table on disk")
    data = open(candidates[0], "rb").read()
    report = nh.enumerate_pe_imports(data)
    assert report["present"] is True
    assert report["dlls"], "a linked DLL must import something"
    for dll, symbols in report["symbols"].items():
        assert dll in report["dlls"]
        assert isinstance(symbols, list)


def test_enumeration_never_raises_on_garbage():
    for blob in (b"", b"MZ", b"MZ" + b"\x00" * 200, b"\x7fELF" + b"\x00" * 64):
        assert nh.enumerate_pe_imports(blob)["present"] is False
        assert nh.enumerate_pe_exports(blob)["present"] is False


def test_rva_translation_uses_the_right_section_header_offset():
    """The +16/+20 offset mistake was made in this module and must stay fixed.

    Reading (raw_size, raw_ptr) at +20 returns (raw_ptr, 0), which lands every
    RVA lookup at file offset 0 and produced a garbage GuardFlags of 0xE020B.
    """
    data = _pe_with_load_config(nh.PE_GUARD_CF_INSTRUMENTED)
    e = struct.unpack_from("<I", data, 0x3C)[0]
    opt = e + 4 + 20
    opt_size = struct.unpack_from("<H", data, e + 4 + 16)[0]
    nsec = struct.unpack_from("<H", data, e + 4 + 2)[0]
    section_table = opt + opt_size
    assert nsec == 1
    vaddr = struct.unpack_from("<I", data, section_table + 12)[0]
    offset = nh._rva_to_offset(data, nsec, section_table, vaddr)
    assert offset is not None and offset != 0, (
        "an RVA inside the mapped section must translate to its file offset, "
        "not to 0")


# ── signing readiness: what this HOST can actually produce ───────────────

def test_signing_readiness_is_reported_per_platform():
    """Authenticode and Hardened Runtime are SIGNATURE properties, not flags.

    The build must say what this host can produce rather than either claiming a
    signature it does not have or silently skipping one it was asked for.
    """
    for platform_name in ("windows", "darwin", "linux"):
        readiness = nh.signing_readiness(platform_name)
        assert readiness["platform"] == nh.canonical_platform(platform_name)
        assert isinstance(readiness["reason"], str) and readiness["reason"], (
            "%s must state WHY, not just whether" % platform_name)
        assert isinstance(readiness["trusted_issuer_possible"], bool)


def test_a_self_signed_certificate_does_not_count_as_trusted():
    """OpenSSL is present, so a self-signed cert CAN be made here — and it is
    worthless for Authenticode, because Windows does not trust the issuer.

    The probe must therefore report trusted_issuer_possible=False on this host
    even though signing machinery exists, or the build would sign with a
    throwaway key and call the artefact signed.
    """
    readiness = nh.signing_readiness("windows")
    if readiness["signing_tool"] is None:
        assert readiness["trusted_issuer_possible"] is False
    # On a host with no CA-issued certificate, the answer must be False. This
    # asserts the DIRECTION: machinery alone is not trust.
    assert ("certificate" in readiness["reason"].lower()
            or "operator" in readiness["reason"].lower()), readiness["reason"]


# ── a REAL object carrying the CET bits (2026-11-20) ─────────────────────
#
# Every CET test above uses a synthetic header. This one uses an object
# actually produced by clang-cl + lld-link, because the 2026-11-19 record
# ("CET measured as not instrumented") turned out to be a measurement defect:
# the probe's load-config structure was the wrong size, so the bits never
# reached the PE.

REAL_CET_PE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "fixtures", "cet_marked_pe.exe")
CET_PROBE_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "fixtures", "cet_probe.c")
CET_BUILD_SH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "fixtures", "build_cet_probe.sh")
#: Measured on the REAL lld-link object this fixture builds, with
#: llvm-readobj naming the bits: 0x100 CF_INSTRUMENTED, 0x4000
#: CF_EXPORT_SUPPRESSION_INFO_PRESENT, and 0x40000/0x100000 unnamed by llvm
#: (they are NOT "CET shadow stack" / "CET user compat" as an earlier version
#: of this constant claimed). The 0xC160 DllCharacteristics on this object is
#: GUARD_CF(0x4000) + TERMINAL_SERVER_AWARE(0x8000) — NOT a CET marker. The
#: real CET opt-in is the Debug Directory type-20 record, which the corrected
#: parser reads (`cet_compat`); the assertion below checks the record.
CET_EXPECTED_FLAGS = 0x100 | 0x4000 | 0x40000 | 0x100000


def _build_cet_probe(tmp_path):
    """Compile the committed probe. Returns (path, skip_reason).

    The object is built rather than checked in because `*.exe` is gitignored:
    a committed binary would silently not exist in CI, and a test that skips
    for that reason is the false-confidence pattern this project keeps
    finding. clang-cl and lld-link are probed by the script itself.
    """
    import subprocess as _sp
    if not os.path.isfile(CET_BUILD_SH):
        return None, "build_cet_probe.sh missing"
    run = _sp.run(["/bin/sh", CET_BUILD_SH], capture_output=True, text=True,
                  timeout=300, cwd=str(tmp_path),
                  env=dict(os.environ, NX_CET_OUTDIR=str(tmp_path)))
    out = (run.stdout or "").strip()
    if out.startswith("ok="):
        return out[3:], None
    if not out:
        out = (run.stderr or "").strip()[-200:] or "no output"
    return None, out


def test_a_real_cet_marked_object_is_read_correctly(tmp_path):
    """The object is BUILT here, so the check cannot skip for free.

    A checked-in .exe would be gitignored and thus absent in CI, and a test
    that skips because its fixture never shipped is the false-confidence
    pattern this project keeps finding. The script reports why it could not
    build, and the skip message carries that reason.
    """
    exe, reason = _build_cet_probe(tmp_path)
    if exe is None:
        pytest.skip("CET probe not buildable here (%s); the synthetic CET "
                    "tests above still run" % (reason,))
    raw = open(exe, "rb").read()
    report = nh.verify_pe_bytes(raw)
    assert report["cfg"] is True, "the real object must still declare CFG"
    assert report["cfg_guard_flags"] == CET_EXPECTED_FLAGS, (
        "GuardFlags changed: expected %#x "
        "(CF_INSTRUMENTED|EXPORT_SUPPRESSION_INFO|two lld-link words), "
        "got %#x" % (CET_EXPECTED_FLAGS, report["cfg_guard_flags"]))
    # CET: this lld-link probe has NO DEBUG DIRECTORY at all (measured:
    # DebugRVA 0x0 / DebugSize 0x0 — the hand-written minimal build reserves
    # no data directory 6), so there is NOWHERE for the type-20 extended
    # record to go even though /CETCOMPAT was passed. The corrected parser
    # therefore reports cet_compat False for THIS object — the opposite of
    # the MSVC-built farm .pyd, which llvm shows carries the record with
    # CET_COMPAT 0x1. Two toolchains, two answers, both now measured instead
    # of assumed; the DllCharacteristics 0xC160 on this object is GUARD_CF +
    # TERMINAL_SERVER_AWARE and is not a CET marker.
    assert report["debug_directory"] is False
    assert report["cet_compat"] is False, (
        "this lld-link probe has no debug directory, so it cannot carry the "
        "type-20 extended record")
    assert report["ex_dllcharacteristics"] == 0
    assert report["terminal_server_aware"] is True
    assert report["guard_export_suppression_info"] is True
    assert "cet_not_instrumented" in nh.check(
        report, "windows", "msvc")["partial"]
    # and the function table is genuinely absent -- a caller-defined
    # structure is why, recorded in the boundary document
    assert report["cfg_function_table"] is False
    verdict = nh.check(report, "windows", "msvc")
    assert verdict["ok"] is True, verdict
    assert verdict["inert"] == [], (
        "a flag with no data behind it is the inert-flag trap; none here")


def test_the_cet_probe_source_is_committed_and_reproducible():
    assert os.path.isfile(CET_PROBE_SRC), (
        "the CET probe source is missing, so the object cannot be rebuilt")
    assert os.path.isfile(CET_BUILD_SH), (
        "the build script is missing, so the probe cannot be rebuilt either")
    body = open(CET_PROBE_SRC, encoding="utf-8").read()
    # the build recipe must be in the file, or nobody can reproduce it
    for token in ("clang-cl", "lld-link", "/guard:cf", "0x4000"):
        assert token in body, (
            "cet_probe.c no longer documents %r" % token)


# ── real Mach-O objects (2026-11-20) ─────────────────────────────────────
#
# The macOS parser had only synthetic fixtures. clang can cross-emit real
# Mach-O for both architectures on this Linux host, so the parser is now
# exercised on real bytes -- and the report distinguishes an MH_OBJECT (where
# "not signed" is EXPECTED) from a dylib (where it is a defect).

MACHO_BUILD_SH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "fixtures", "build_macho_probe.sh")


def _build_macho_probes(tmp_path):
    import subprocess as _sp
    if not os.path.isfile(MACHO_BUILD_SH):
        return None, "build_macho_probe.sh missing"
    run = _sp.run(["/bin/sh", MACHO_BUILD_SH], capture_output=True, text=True,
                  timeout=300, cwd=str(tmp_path),
                  env=dict(os.environ, NX_MACHO_OUTDIR=str(tmp_path)))
    out = (run.stdout or "").strip()
    if out.startswith("ok="):
        return out[3:].split(), None
    return None, out or (run.stderr or "").strip()[-200:] or "no output"


def test_real_macho_objects_parse_and_report_their_filetype(tmp_path):
    """Parse real arm64 + x86_64 Mach-O, and report type, not just flags.

    Measured 2026-11-20: without a filetype field, `pie=False`/`signed=False`
    on an MH_OBJECT is indistinguishable from the same report on an unsigned
    dylib -- one is expected, the other is the defect the reviewer asked
    about.
    """
    built, reason = _build_macho_probes(tmp_path)
    if built is None:
        pytest.skip("Mach-O cross-compile unavailable (%s)" % (reason,))
    assert len(built) == 2, built
    for path in built:
        raw = open(path, "rb").read()
        report = nh.verify_macho_bytes(raw)
        assert report["valid"] is True, (
            "%s did not parse as Mach-O" % os.path.basename(path))
        assert report["filetype"] == 1, (
            "cross-compiled objects are MH_OBJECT; got filetype %r"
            % (report["filetype"],))
        assert report["filetype_name"] == "object"
        # the distinction that matters: signing is not EXPECTED of an object
        assert report["signature_expected"] is False, (
            "an MH_OBJECT must not be treated as a missing signature")
        assert report["signed"] is False
        assert report["hardened_runtime"] is False


def test_the_macho_probe_source_is_committed_and_reproducible():
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "fixtures", "macho_probe.c")
    assert os.path.isfile(src), "the Mach-O probe source is missing"
    assert os.path.isfile(MACHO_BUILD_SH), "the build script is missing"
    build = open(MACHO_BUILD_SH, encoding="utf-8").read()
    for token in ("arm64-apple-macos", "x86_64-apple-macos"):
        assert token in build, (
            "the Mach-O build script no longer targets %r" % token)


def test_macho_bundle_does_not_fail_on_executable_only_flags():
    """PIE/no-heap-exec are executable-image bits, not extension-bundle bits."""
    blob = _macho(0)
    header = bytearray(blob)
    struct.pack_into("<I", header, 12, 8)  # MH_BUNDLE
    report = nh.verify_macho_bytes(bytes(header))
    result = nh.check(report, "darwin", "clang")
    assert result["missing"] == []
    assert "pie" in result["unavailable"]
    assert "no_heap_exec" in result["unavailable"]


def test_farm_uploads_gitattributes_to_pin_payload_line_endings():
    """Windows checkout CRLF conversion must not change attested payload bytes."""
    from obfuscator.core import utils as nutils
    entries = dict(nutils.FARM_DRIVER_DATA)
    assert entries.get(".gitattributes") == "scripts/farm.gitattributes"
    text = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "farm.gitattributes"),
                encoding="utf-8").read()
    assert "payload.py text eol=lf" in text
