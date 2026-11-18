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

def _pe(dll_characteristics, security_size=0, debug_size=0, pe32plus=True):
    """A minimal PE image: DOS header, PE signature, COFF, optional header."""
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
        # The MSVC branch builds these as "/" + name, so the literal string
        # "/NXCOMPAT" does not appear in the source. Accept either form, but
        # require that the name is present exactly once inside a "/"-prefixed
        # construction and never with a leading dash.
        assert ('"/" +' in code and name in code), (
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
        capture_output=True, text=True)
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
        capture_output=True, text=True)
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
