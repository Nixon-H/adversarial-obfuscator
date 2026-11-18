"""§3 native hardening for Windows and macOS: emit, then VERIFY on the runner.

The review is explicit: *"Don't blindly enable every flag. Verify the resulting
binary using platform-native inspection tools"*. That constraint shapes this
module. This machine is Linux, so it cannot compile or inspect a PE or a Mach-O
object; therefore the only honest design is:

  1. the build emits the platform hardening flags (done in the drivers), and
  2. the RUNNER proves, with platform-native tools, what actually landed, and
     that proof travels in the run attestation (§7.9).

Nothing here claims a flag was applied. ``verify_pe_bytes`` and
``verify_macho_bytes`` parse the produced object and report what the header
ACTUALLY says, so a compiler that ignored a flag shows up as ``applied: False``
rather than as a reassuring log line.

Flags emitted
-------------
Windows (MSVC ``/`` and mingw ``-`` spellings both listed because the farm's
windows runner may be either):

    /DYNAMICBASE      ASLR
    /NXCOMPAT         DEP
    /GUARD:CF         Control Flow Guard
    /CETCOMPAT        CET shadow stack (where the toolchain knows it)
    /HIGHENTROPYVA    64-bit ASLR entropy
    /GS               stack canaries
    /guard:ehcont     EH continuation metadata (CFG for EH)
    Authenticode: NOT emitted -- it needs a code-signing certificate, and
    signing with a throwaway key would be worse than not signing. Recorded as
    a required operator step instead of a fake pass.

macOS (clang):

    -fPIE -pie                MH_PIE
    -Wl,-no_pie  is NOT used; -pie is
    -Wl,-dead_strip
    -fstack-protector-strong
    -mmacosx-version-min=...  required for Hardened Runtime
    Hardened Runtime / library validation / code signing: these are applied by
    ``codesign``, not by the compiler, so they are checked from the signature
    rather than assumed. ``codesign --options runtime`` is the operator step;
    this module verifies the resulting CodeDirectory flags when a signature
    exists.

Honest limits, stated once and not softened below: an unsigned Mach-O has no
Hardened Runtime regardless of the compiler flags, and a PE without a
certificate has no Authenticode. Both are reported as "not present", never as
"enabled".
"""
from __future__ import annotations

import struct

#: PE DllCharacteristics bits that matter here.
PE_DYNAMIC_BASE = 0x0040      # ASLR
PE_HIGH_ENTROPY_VA = 0x0020   # 64-bit ASLR entropy
PE_NX_COMPAT = 0x0100         # DEP
PE_GUARD_CF = 0x4000          # Control Flow Guard
PE_NO_ISOLATION = 0x0200
PE_NO_SEH = 0x0400
PE_TERMINAL_SERVER_AWARE = 0x8000

#: Mach-O header flags.
MH_PIE = 0x200000
MH_NO_HEAP_EXECUTION = 0x01000000
MH_ALLOW_STACK_EXECUTION = 0x00020000

#: CodeDirectory / cs_blob flags relevant to Hardened Runtime.
CS_RESTRICT = 0x00000800
CS_RUNTIME = 0x00010000

#: The flags the drivers pass, per platform, for the record and for tests.
#:
#: These are NOT interchangeable with the mingw spellings, and getting this
#: wrong is worse than not emitting the flag at all -- measured 2026-11-19 on
#: x86_64-w64-mingw32-gcc 14.2:
#:
#:     $ x86_64-w64-mingw32-gcc -shared -o x.dll t.c -NXCOMPAT
#:     gcc: error: unrecognized command-line option '-NXCOMPAT'
#:
#: The build FAILS. An earlier version of the driver emitted ``-`` + the MSVC
#: name for every Windows runner, which would have turned "harden the Windows
#: build" into "the Windows build does not compile". The ``/`` names are MSVC
#: only; ``MINGW_*`` below are what a gcc front end accepts.
WINDOWS_COMPILE_FLAGS = (
    "/DYNAMICBASE", "/NXCOMPAT", "/GUARD:CF", "/CETCOMPAT",
    "/HIGHENTROPYVA", "/GS", "/guard:ehcont",
)
WINDOWS_LINK_FLAGS = ("/DYNAMICBASE", "/NXCOMPAT", "/GUARD:CF", "/CETCOMPAT")

#: mingw (gcc front end). GNU ld 2.44 has NO Control Flow Guard support --
#: ``--guard:cf`` is an lld-link option and ``/guard:cf`` passed through
#: ``-Wl,`` is read as a file name ("cannot find /guard:cf"). So CFG is simply
#: not reachable from a mingw toolchain, and claiming it would be a lie. The
#: three that ARE reachable are emitted here.
MINGW_LINK_FLAGS = (
    "-Wl,--dynamicbase", "-Wl,--high-entropy-va", "-Wl,--nxcompat",
)
MINGW_COMPILE_FLAGS = ("-fstack-protector-strong",)

MACOS_COMPILE_FLAGS = (
    "-fPIE", "-fstack-protector-strong", "-mmacosx-version-min=10.15",
)
MACOS_LINK_FLAGS = ("-pie", "-Wl,-dead_strip")


def elf_note():
    """Placeholder report for an ELF object on a non-Linux runner.

    ELF hardening (RELRO/NX/canaries/stripped/single export) is verified by
    pydeobsbench on Linux, where the platform tools exist. Recorded here so an
    attestation always carries a hardening entry rather than an absent field,
    which would read as "not checked".
    """
    return {"kind": "elf", "valid": True,
            "note": "ELF hardening verified on the linux runner by pydeobsbench"}


def unknown_note():
    """Report for an object whose magic is not recognised."""
    return {"kind": "unknown", "valid": False,
            "note": "object magic not recognised; hardening not verifiable"}


def verify_pe_bytes(data):
    """Report the PE hardening the object ACTUALLY carries.

    Parses the DOS header, the PE signature, the COFF header and
    ``OptionalHeader.DllCharacteristics``. Returns a dict of booleans plus the
    raw value, and ``valid: False`` when the bytes are not a PE at all -- an
    unparseable object must never read as "hardened".
    """
    out = {"kind": "pe", "valid": False, "dll_characteristics": None,
           "aslr": False, "high_entropy_va": False, "dep": False,
           "cfg": False, "authenticode": False, "debug_directory": False}
    if not data or data[:2] != b"MZ":
        return out
    try:
        e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
        if data[e_lfanew:e_lfanew + 4] != b"PE\0\0":
            return out
        coff = e_lfanew + 4
        num_sections = struct.unpack_from("<H", data, coff + 2)[0]
        opt_size = struct.unpack_from("<H", data, coff + 16)[0]
        opt = coff + 20
        magic = struct.unpack_from("<H", data, opt)[0]
        if magic == 0x20B:      # PE32+
            dll_off = opt + 70
            num_dirs_off = opt + 108
            dirs_off = opt + 112
        elif magic == 0x10B:    # PE32
            dll_off = opt + 70
            num_dirs_off = opt + 92
            dirs_off = opt + 96
        else:
            return out
        dll = struct.unpack_from("<H", data, dll_off)[0]
        out.update({
            "valid": True,
            "dll_characteristics": dll,
            "aslr": bool(dll & PE_DYNAMIC_BASE),
            "high_entropy_va": bool(dll & PE_HIGH_ENTROPY_VA),
            "dep": bool(dll & PE_NX_COMPAT),
            "cfg": bool(dll & PE_GUARD_CF),
        })
        # Security directory (index 4) = Authenticode; debug directory = 6.
        num_dirs = struct.unpack_from("<I", data, num_dirs_off)[0]
        if num_dirs > 4:
            sec_size = struct.unpack_from("<I", data, dirs_off + 4 * 8 + 4)[0]
            out["authenticode"] = sec_size > 0
        if num_dirs > 6:
            dbg_size = struct.unpack_from("<I", data, dirs_off + 6 * 8 + 4)[0]
            out["debug_directory"] = dbg_size > 0
        out["sections"] = num_sections
        out["opt_size"] = opt_size
    except (struct.error, IndexError):
        return {"kind": "pe", "valid": False, "dll_characteristics": None,
                "aslr": False, "high_entropy_va": False, "dep": False,
                "cfg": False, "authenticode": False, "debug_directory": False}
    return out


def verify_macho_bytes(data):
    """Report the Mach-O hardening the object ACTUALLY carries.

    Handles 64-bit little-endian Mach-O (what clang emits on x86_64/arm64) and
    FAT binaries (first slice). ``hardened_runtime`` and ``library_validation``
    come from a code signature, which a freshly compiled object does NOT have:
    they are reported False and the caller must treat that as "not enabled",
    not as unknown.
    """
    out = {"kind": "macho", "valid": False, "flags": None, "pie": False,
           "no_heap_exec": False, "stack_exec": False,
           "hardened_runtime": False, "library_validation": False,
           "signed": False}
    if not data or len(data) < 32:
        return out
    try:
        # FAT headers are BIG-endian (the magic reads 0xCAFEBABE, not
        # 0xBEB0FECA), so the magic must be compared in ">I". The first version
        # of this function unpacked it little-endian and therefore never
        # recognised a universal binary: `clang -arch arm64 -arch x86_64`
        # output reported valid=False and failed its own §3 check. Caught by
        # tests/test_native_harden.py.
        magic_be = struct.unpack_from(">I", data, 0)[0]
        if magic_be == 0xCAFEBABE:   # FAT
            nfat = struct.unpack_from(">I", data, 4)[0]
            if nfat < 1:
                return out
            offset = struct.unpack_from(">I", data, 16)[0]
            data = data[offset:]
            magic = struct.unpack_from("<I", data, 0)[0]
        else:
            magic = struct.unpack_from("<I", data, 0)[0]
        if magic != 0xFEEDFACF:       # MH_MAGIC_64
            return out
        flags = struct.unpack_from("<I", data, 24)[0]
        out.update({
            "valid": True,
            "flags": flags,
            "pie": bool(flags & MH_PIE),
            "no_heap_exec": bool(flags & MH_NO_HEAP_EXECUTION),
            "stack_exec": bool(flags & MH_ALLOW_STACK_EXECUTION),
        })
        # A code signature is an LC_CODE_SIGNATURE (0x1D) load command. The
        # CodeDirectory's flags then say whether Hardened Runtime (CS_RUNTIME)
        # and library validation (CS_RESTRICT) are set.
        ncmds = struct.unpack_from("<I", data, 16)[0]
        off = 32
        for _ in range(min(ncmds, 256)):
            if off + 8 > len(data):
                break
            cmd, cmdsize = struct.unpack_from("<II", data, off)
            if cmdsize < 8:
                break
            if cmd == 0x1D:           # LC_CODE_SIGNATURE
                out["signed"] = True
                if off + 16 <= len(data):
                    dataoff, datasize = struct.unpack_from("<II", data, off + 8)
                    blob = data[dataoff:dataoff + datasize]
                    out["hardened_runtime"], out["library_validation"] = \
                        _codesign_flags(blob)
                break
            off += cmdsize
    except (struct.error, IndexError):
        return {"kind": "macho", "valid": False, "flags": None, "pie": False,
                "no_heap_exec": False, "stack_exec": False,
                "hardened_runtime": False, "library_validation": False,
                "signed": False}
    return out


def _codesign_flags(superblob):
    """Return (hardened_runtime, library_validation) from a cs superblob.

    The superblob is big-endian: magic|length|count, then
    (type|offset) pairs. Type 0 is the CodeDirectory, whose `flags` field sits
    0x28 bytes in for version >= 0x20100.
    """
    try:
        if len(superblob) < 12:
            return False, False
        magic, _length, count = struct.unpack_from(">III", superblob, 0)
        if magic != 0xFADE0CC0:       # CSMAGIC_EMBEDDED_SIGNATURE
            return False, False
        for i in range(min(count, 32)):
            base = 12 + i * 8
            if base + 8 > len(superblob):
                break
            ctype, coff = struct.unpack_from(">II", superblob, base)
            if ctype != 0:            # 0 = CodeDirectory
                continue
            if coff + 0x30 > len(superblob):
                break
            cd_magic = struct.unpack_from(">I", superblob, coff)[0]
            if cd_magic != 0xFADE0C02:   # CSMAGIC_CODEDIRECTORY
                break
            flags = struct.unpack_from(">I", superblob, coff + 0x28)[0]
            return bool(flags & CS_RUNTIME), bool(flags & CS_RESTRICT)
    except (struct.error, IndexError):
        pass
    return False, False


#: What each platform MUST report, as (field, required_value) pairs.
#: A False requirement is as important as a True one: stack_exec must be ABSENT,
#: and expressing that as `stack_exec: False` in the same mapping as
#: `pie: True` is how the first version of this module got it backwards -- it
#: demanded stack execution on macOS. Tests caught it because a genuinely
#: hardened object then failed its own check.
REQUIRED = {
    "windows": (("aslr", True), ("dep", True), ("cfg", True)),
    "darwin": (("pie", True), ("no_heap_exec", True), ("stack_exec", False)),
}

#: Flags a toolchain physically cannot emit. Demanding them would make every
#: build from that toolchain fail forever, which trains an operator to ignore
#: the check -- the opposite of what §3 asks for. Reported as ``unavailable``
#: so the gap is visible rather than dropped.
#:
#: Measured 2026-11-19: GNU ld 2.44 (mingw) has no CFG option; CFG needs
#: MSVC's link.exe or lld-link. A real mingw PE reports 0x160
#: (ASLR|DEP|HIGH_ENTROPY_VA) and no CFG bit, whatever we pass.
TOOLCHAIN_UNAVAILABLE = {
    ("windows", "mingw"): ("cfg",),
    ("windows", "gcc"): ("cfg",),
}


def _normalise_toolchain(toolchain):
    """Map a compiler string to the key used in :data:`TOOLCHAIN_UNAVAILABLE`."""
    name = (toolchain or "").lower()
    if not name:
        return None
    if "mingw" in name:
        return "mingw"
    if "clang" in name or "lld" in name:
        return "clang"
    if "gcc" in name or name in ("cc", "g++"):
        return "gcc"
    if "msvc" in name or "cl.exe" in name or "link.exe" in name:
        return "msvc"
    return name


#: Canonical platform names, so the normalisation happens in ONE place instead
#: of being re-derived in every function (an earlier draft re-derived it three
#: times with three different spellings).
PLATFORM_ALIASES = {
    "windows": "windows", "win32": "windows", "win": "windows", "win64": "windows",
    "darwin": "darwin", "macos": "darwin", "mac": "darwin", "osx": "darwin",
}


def canonical_platform(platform_name):
    """"windows" / "darwin" / the lowercased input / ""."""
    name = (platform_name or "").lower()
    return PLATFORM_ALIASES.get(name, name)


def expected_for(platform_name, toolchain=None):
    """The hardening this project requires, as ``{field: required_value}``.

    With ``toolchain`` given, flags that toolchain cannot emit are removed from
    the requirement set; :func:`check` reports them under ``unavailable``.
    """
    canonical = canonical_platform(platform_name)
    if canonical not in REQUIRED:
        return {}
    want = dict(REQUIRED[canonical])
    for field in TOOLCHAIN_UNAVAILABLE.get(
            (canonical, _normalise_toolchain(toolchain)), ()):
        want.pop(field, None)
    return want


def check(object_report, platform_name, toolchain=None):
    """Compare what the object carries against what the build requires.

    Returns ``{"ok", "missing", "wrong", "unavailable", "report"}``.
    ``missing`` lists a required-True field that is not True; ``wrong`` lists a
    required-False field that IS set. Both fail. An unparseable object fails
    before either list is considered, because "the parser did not look" is not
    evidence of safety.

    ``unavailable`` lists flags this toolchain cannot emit (see
    :data:`TOOLCHAIN_UNAVAILABLE`). They are excluded from the verdict because
    no flag would change them, but they are named in the result so the gap is
    recorded rather than silently treated as satisfied.
    """
    canonical = canonical_platform(platform_name)
    want = expected_for(platform_name, toolchain)
    missing = [field for field, value in want.items()
               if value is True and not object_report.get(field)]
    wrong = [field for field, value in want.items()
             if value is False and object_report.get(field)]
    unavailable = [field for field, _value in REQUIRED.get(canonical, ())
                   if field not in want]
    return {"ok": (not missing and not wrong
                   and bool(object_report.get("valid"))),
            "missing": missing, "wrong": wrong,
            "unavailable": unavailable,
            "report": object_report}
