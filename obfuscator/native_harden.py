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

#: IMAGE_LOAD_CONFIG_DIRECTORY64 GuardFlags bits that decide whether CFG is a
#: real control or a declaration. Measured 2026-11-19 (lld-link 19, real object
#: with a supplied `_load_config_used`): GuardFlags came out 0x100 — instrumented
#: but with NO function table, so indirect calls cannot be validated.
PE_GUARD_CF_INSTRUMENTED = 0x00000100
PE_GUARD_CFW_INSTRUMENTED = 0x00000200
PE_GUARD_CF_FUNCTION_TABLE_PRESENT = 0x00000400

#: CET (Control-flow Enforcement Technology) and shadow-stack bits, from the
#: same GuardFlags word. Windows 10 2004+ uses these to decide whether to enable
#: the hardware shadow stack for the image:
#:
#:   IMAGE_GUARD_XFG_ENABLED               0x00004000  eXtended Flow Guard
#:   IMAGE_GUARD_CET_SHADOW_STACK_PRESENT  0x00040000  shadow-stack metadata
#:   IMAGE_GUARD_CET_UserCETCompat         0x00100000  user-mode CET opt-in
#:
#: The /CETCOMPAT compiler flag alone does NOT set these. The linker must see
#: CET metadata from the objects, or the image is marked "CET compatible" with
#: nothing behind the claim — the same trap as the CFG bit. They are read and
#: reported separately from CFG so the two cannot be conflated.
PE_GUARD_XFG_ENABLED = 0x00004000
PE_GUARD_CET_SHADOW_STACK_PRESENT = 0x00040000
PE_GUARD_CET_USER_COMPAT = 0x00100000

#: Offset of GuardFlags inside IMAGE_LOAD_CONFIG_DIRECTORY64, computed from the
#: field layout rather than assumed: the naive 0x70 this module first used is
#: the CFCheckFunctionPointer, so it read zero and would have reported every
#: object's GuardFlags as 0. Verified against the windows-sys binding layout.
LOAD_CONFIG_GUARD_FLAGS_OFFSET = 0x90


def _read_guard_flags(data, num_sections, section_table, lc_va, lc_size):
    """GuardFlags from the load config, or 0 when it cannot be located.

    The data directory stores an RVA, so it must be translated through the
    section table before reading. Returning 0 on any failure is deliberate: an
    unreadable table is reported as "no guard flags", never as a pass.

    ``section_table`` is passed in rather than derived here: the first version
    re-derived it as ``opt - 16 + 2``, which reads the wrong offset and produced
    a garbage GuardFlags (0xE020B) that looked plausible.
    """
    if lc_size < LOAD_CONFIG_GUARD_FLAGS_OFFSET + 4:
        return 0
    try:
        for index in range(min(num_sections, 96)):
            entry = section_table + index * 40
            # Section header layout: name(8) vsize(4) vaddr(4) rawsize(4)
            # rawptr(4). So +8 gives (vsize, vaddr) and +16 gives
            # (raw_size, raw_ptr). Reading +20 returns (raw_ptr, 0) and made
            # every lookup land at file offset 0 — measured, and it produced a
            # garbage GuardFlags (0xE020B) that looked plausible enough to
            # nearly be reported as fact.
            vsize, vaddr = struct.unpack_from("<II", data, entry + 8)
            raw_size, raw_ptr = struct.unpack_from("<II", data, entry + 16)
            if vaddr <= lc_va < vaddr + max(vsize, raw_size):
                file_offset = raw_ptr + (lc_va - vaddr)
                return struct.unpack_from(
                    "<I", data, file_offset + LOAD_CONFIG_GUARD_FLAGS_OFFSET)[0]
    except (struct.error, IndexError):
        return 0
    return 0

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


def _rva_to_offset(data, num_sections, section_table, rva):
    """Translate an RVA to a file offset, or None.

    One helper for every enumeration below. The section header gives
    ``(vsize, vaddr)`` at +8 and ``(raw_size, raw_ptr)`` at +16 — reading +20
    returns ``(raw_ptr, 0)`` and lands every lookup at file offset 0, which is a
    mistake that was actually made in this module and is now pinned by a test.
    """
    try:
        for index in range(min(num_sections, 96)):
            entry = section_table + index * 40
            vsize, vaddr = struct.unpack_from("<II", data, entry + 8)
            raw_size, raw_ptr = struct.unpack_from("<II", data, entry + 16)
            if vaddr <= rva < vaddr + max(vsize, raw_size):
                return raw_ptr + (rva - vaddr)
    except (struct.error, IndexError):
        return None
    return None


def _read_cstring(data, offset, limit=256):
    if offset is None or offset < 0 or offset >= len(data):
        return ""
    end = data.find(b"\x00", offset, min(offset + limit, len(data)))
    if end < 0:
        end = min(offset + limit, len(data))
    return data[offset:end].decode("ascii", "replace")


def enumerate_pe_exports(data):
    """Names the object EXPORTS, read from the export directory (index 0).

    §3 asks for "PE import/export inspection", and on Windows the export table is
    the analogue of ``nm -D`` on ELF: it is what an analyst reads first, without
    reversing anything. For a Python extension the only export a correct build
    needs is ``PyInit_<module>``; anything more is a readable name surface.

    Returns ``{"present": bool, "names": [...], "dll_name": str}``. An
    unparseable table reports ``present: True, error: ...`` rather than an empty
    list, because "no exports" and "could not read the exports" are different
    findings and only one of them is good news.
    """
    out = {"present": False, "names": [], "dll_name": ""}
    try:
        if data[:2] != b"MZ":
            return out
        e = struct.unpack_from("<I", data, 0x3C)[0]
        if data[e:e + 4] != b"PE\0\0":
            return out
        coff = e + 4
        num_sections = struct.unpack_from("<H", data, coff + 2)[0]
        opt_size = struct.unpack_from("<H", data, coff + 16)[0]
        opt = coff + 20
        magic = struct.unpack_from("<H", data, opt)[0]
        dirs_off = opt + (112 if magic == 0x20B else 96)
        section_table = opt + opt_size
        exp_rva, exp_size = struct.unpack_from("<II", data, dirs_off)
        if not exp_rva or not exp_size:
            return out
        out["present"] = True
        base = _rva_to_offset(data, num_sections, section_table, exp_rva)
        if base is None:
            out["error"] = "export directory RVA not mapped by any section"
            return out
        # IMAGE_EXPORT_DIRECTORY: Name(4) Base(4) NumberOfFunctions(4)
        # NumberOfNames(4) AddressOfFunctions(4) AddressOfNames(4)
        # AddressOfNameOrdinals(4)
        name_rva = struct.unpack_from("<I", data, base + 12)[0]
        num_names = struct.unpack_from("<I", data, base + 24)[0]
        names_rva = struct.unpack_from("<I", data, base + 32)[0]
        out["dll_name"] = _read_cstring(
            data, _rva_to_offset(data, num_sections, section_table, name_rva))
        table = _rva_to_offset(data, num_sections, section_table, names_rva)
        if table is None:
            out["error"] = "export name table RVA not mapped"
            return out
        names = []
        for index in range(min(num_names, 4096)):
            rva = struct.unpack_from("<I", data, table + index * 4)[0]
            names.append(_read_cstring(
                data, _rva_to_offset(data, num_sections, section_table, rva)))
        out["names"] = [n for n in names if n]
    except (struct.error, IndexError) as exc:
        out["error"] = "export parse failed: %s" % (str(exc)[:80],)
    return out


def enumerate_pe_imports(data):
    """DLLs and symbols the object IMPORTS (import directory, index 1).

    The import surface is the other half of "PE import inspection": it names the
    libraries the artefact depends on, which is both a provenance signal (does a
    "self-contained" payload pull in unusual DLLs?) and an analysis aid (an
    analyst reads the import list to guess behaviour).

    Returns ``{"present": bool, "dlls": [...], "symbols": {dll: [...]}}``.
    """
    out = {"present": False, "dlls": [], "symbols": {}}
    try:
        if data[:2] != b"MZ":
            return out
        e = struct.unpack_from("<I", data, 0x3C)[0]
        if data[e:e + 4] != b"PE\0\0":
            return out
        coff = e + 4
        num_sections = struct.unpack_from("<H", data, coff + 2)[0]
        opt_size = struct.unpack_from("<H", data, coff + 16)[0]
        opt = coff + 20
        magic = struct.unpack_from("<H", data, opt)[0]
        dirs_off = opt + (112 if magic == 0x20B else 96)
        is64 = magic == 0x20B
        section_table = opt + opt_size
        imp_rva, imp_size = struct.unpack_from("<II", data, dirs_off + 8)
        if not imp_rva or not imp_size:
            return out
        out["present"] = True
        cursor = _rva_to_offset(data, num_sections, section_table, imp_rva)
        if cursor is None:
            out["error"] = "import directory RVA not mapped"
            return out
        # IMAGE_IMPORT_DESCRIPTOR: OriginalFirstThunk(4) TimeDateStamp(4)
        # ForwarderChain(4) Name(4) FirstThunk(4) -- terminated by an all-zero
        # entry. 20 bytes each.
        for index in range(min(512, imp_size // 20 or 512)):
            entry = cursor + index * 20
            if entry + 20 > len(data):
                break
            oft, _ts, _fwd, name_rva, ft = struct.unpack_from("<IIIII",
                                                              data, entry)
            if not (oft or name_rva or ft):
                break
            dll = _read_cstring(
                data, _rva_to_offset(data, num_sections, section_table,
                                     name_rva))
            if dll:
                out["dlls"].append(dll)
                out["symbols"].setdefault(dll, [])
            thunk = oft or ft
            thunk_off = _rva_to_offset(data, num_sections, section_table, thunk)
            if thunk_off is None:
                continue
            width = 8 if is64 else 4
            for slot in range(512):
                pos = thunk_off + slot * width
                if pos + width > len(data):
                    break
                value = (struct.unpack_from("<Q", data, pos)[0] if is64
                         else struct.unpack_from("<I", data, pos)[0])
                if not value:
                    break
                # High bit set = import by ordinal; the low bits are then an
                # ordinal, not a name offset. Record it so the surface is not
                # silently under-reported.
                if value & (1 << (63 if is64 else 31)):
                    if dll:
                        out["symbols"][dll].append(
                            "#%d" % (value & 0xFFFF,))
                    continue
                off = _rva_to_offset(data, num_sections, section_table,
                                     value & 0x7FFFFFFF)
                # IMAGE_IMPORT_BY_NAME: Hint(2) then the ASCII name.
                name = _read_cstring(data, (off + 2) if off is not None else None)
                if name and dll:
                    out["symbols"][dll].append(name)
    except (struct.error, IndexError) as exc:
        out["error"] = "import parse failed: %s" % (str(exc)[:80],)
    return out


def verify_pe_bytes(data):
    """Report the PE hardening the object ACTUALLY carries.

    Parses the DOS header, the PE signature, the COFF header and
    ``OptionalHeader.DllCharacteristics``. Returns a dict of booleans plus the
    raw value, and ``valid: False`` when the bytes are not a PE at all -- an
    unparseable object must never read as "hardened".

    **CFG needs more than its flag bit.** Measured 2026-11-19 on lld-link 19
    with ``-guard:cf``: the linker sets ``DllCharacteristics`` bit 0x4000 and
    prints

        warning: Control Flow Guard is enabled but '_load_config_used' is
        missing

    and the resulting object has an EMPTY load-config data directory, so no
    guard function table, no guard flags, nothing for the loader to enforce.
    The bit alone is a declaration. ``cfg_data`` therefore reports whether the
    load-config directory actually carries a payload, and ``check`` treats a
    declared-but-empty CFG as NOT satisfied. A verifier that accepted the bit
    would be reporting exactly the kind of reassurance this project keeps
    having to retract.
    """
    out = {"kind": "pe", "valid": False, "dll_characteristics": None,
           "aslr": False, "high_entropy_va": False, "dep": False,
           "cfg": False, "cfg_data": False, "authenticode": False,
           "debug_directory": False, "load_config_size": 0,
           # Load-config-derived keys are present from the start so the
           # report's SHAPE never depends on what the object turned out to
           # contain. A caller iterating the report must not get KeyError for
           # an object that happens to declare no load config.
           "cfg_guard_flags": 0, "cfg_instrumented": False,
           "cfg_function_table": False, "cet_xfg": False,
           "cet_shadow_stack": False, "cet_user_compat": False}
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
        # Security directory (index 4) = Authenticode; debug directory = 6;
        # load config = 10 (the one that makes CFG real).
        num_dirs = struct.unpack_from("<I", data, num_dirs_off)[0]
        if num_dirs > 4:
            sec_size = struct.unpack_from("<I", data, dirs_off + 4 * 8 + 4)[0]
            out["authenticode"] = sec_size > 0
        if num_dirs > 6:
            dbg_size = struct.unpack_from("<I", data, dirs_off + 6 * 8 + 4)[0]
            out["debug_directory"] = dbg_size > 0
        if num_dirs > 10:
            lc_va, lc_size = struct.unpack_from("<II", data,
                                                dirs_off + 10 * 8)
            out["load_config_size"] = lc_size
            # CFG metadata lives in the load config; an empty directory means
            # the flag is a declaration with nothing behind it.
            out["cfg_data"] = lc_size > 0
            if lc_size > 0:
                # Read GuardFlags from the load config itself. Being present is
                # NOT the same as being effective: measured 2026-11-19 on
                # lld-link 19 with a supplied `_load_config_used`, the table is
                # emitted with GuardFlags = 0x100 (IMAGE_GUARD_CF_INSTRUMENTED)
                # and no CF_FUNCTION_TABLE_PRESENT bit — CFG checks were
                # compiled in, but there is no function table for the loader to
                # validate indirect calls against. That is a weaker state than
                # full CFG, and reporting only "cfg_data present" would hide it.
                out["cfg_guard_flags"] = _read_guard_flags(
                    data, num_sections, opt + opt_size, lc_va, lc_size)
                flags = out["cfg_guard_flags"]
                out["cfg_instrumented"] = bool(flags & PE_GUARD_CF_INSTRUMENTED)
                out["cfg_function_table"] = bool(
                    flags & PE_GUARD_CF_FUNCTION_TABLE_PRESENT)
                # CET is read from the SAME word but reported separately: the
                # /CETCOMPAT flag does not set these bits, so conflating them
                # would repeat the CFG mistake one abstraction up.
                out["cet_xfg"] = bool(flags & PE_GUARD_XFG_ENABLED)
                out["cet_shadow_stack"] = bool(
                    flags & PE_GUARD_CET_SHADOW_STACK_PRESENT)
                out["cet_user_compat"] = bool(flags & PE_GUARD_CET_USER_COMPAT)
        # CET can ALSO be declared in DllCharacteristics (bit 0x8000 is
        # TERMINAL_SERVER_AWARE, so this is not it) -- Windows' CET opt-in for
        # an image is the GuardFlags bits above, not a DllCharacteristics bit.
        # Recorded here so a reader does not go looking for one.
        #
        # EVERY load-config-derived key is defaulted, not just the CET ones.
        # Measured 2026-11-19: an object with no load-config directory raised
        # KeyError on `cfg_function_table` in a consumer that iterated the
        # report, because that key was only created inside the `lc_size > 0`
        # branch. A report whose shape depends on the object is a trap for
        # every caller; the parser now always returns the same keys and lets
        # the VALUES say "absent".
        out.setdefault("cfg_guard_flags", 0)
        out.setdefault("cfg_instrumented", False)
        out.setdefault("cfg_function_table", False)
        out.setdefault("cet_xfg", False)
        out.setdefault("cet_shadow_stack", False)
        out.setdefault("cet_user_compat", False)
        out["sections"] = num_sections
        out["opt_size"] = opt_size
    except (struct.error, IndexError):
        return {"kind": "pe", "valid": False, "dll_characteristics": None,
                "aslr": False, "high_entropy_va": False, "dep": False,
                "cfg": False, "cfg_data": False, "authenticode": False,
                "debug_directory": False, "load_config_size": 0}
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


def signing_readiness(platform_name):
    """Can this HOST produce a *trusted* signature for the artefact?

    The review asks for Authenticode on Windows and Hardened Runtime / code
    signing on macOS. Both are properties of a SIGNATURE, not of a compiler
    flag, and a signature is only worth anything if the platform trusts its
    issuer.

    Measured on this host 2026-11-19:

      * Linux: no ``codesign``, no ``rcodesign``, no ``ldid``, no
        ``osslsigncode``. ``signtool`` exists but is the NSS build and fails
        with ``SEC_ERROR_BAD_DATABASE``. There is no Windows certificate store.
      * A self-signed certificate CAN be generated here (OpenSSL 3.5 is
        present) and PKCS#7 signing is available via ``cryptography``. But a
        self-signed Authenticode signature is not trusted by Windows and a
        self-signed Mach-O signature is not accepted by Gatekeeper, so
        producing one would make the artefact *look* signed while changing
        nothing an attacker or the OS cares about.

    This function returns what is actually possible, so the build reports the
    truth instead of either claiming a signature it does not have or silently
    skipping one it was asked for. It is a capability probe, not a policy
    decision: an operator with a real certificate and a real signing tool can
    sign out of band, and this module will verify the result from the bytes.

    Returns ``{"platform", "signing_tool", "trusted_issuer_possible",
    "reason"}``.
    """
    import shutil as _shutil

    canonical = canonical_platform(platform_name)
    out = {"platform": canonical, "signing_tool": None,
           "trusted_issuer_possible": False, "reason": ""}
    if canonical == "windows":
        # osslsigncode and a working signtool are the two ways to produce an
        # Authenticode signature on a non-Windows host.
        if _shutil.which("osslsigncode"):
            out["signing_tool"] = "osslsigncode"
            out["trusted_issuer_possible"] = True
            out["reason"] = ("osslsigncode present; supply a CA-issued "
                             "certificate to sign")
        elif _shutil.which("signtool"):
            out["signing_tool"] = "signtool"
            out["reason"] = ("signtool present but no certificate store on a "
                             "POSIX host; verify with `signtool verify` once a "
                             "certificate is installed")
        else:
            out["reason"] = ("no Authenticode signing tool on this host; "
                             "Authenticode is an OPERATOR step, not a build flag")
    elif canonical == "darwin":
        for tool in ("codesign", "rcodesign"):
            if _shutil.which(tool):
                out["signing_tool"] = tool
                out["trusted_issuer_possible"] = True
                out["reason"] = ("%s present; supply an Apple Developer ID to "
                                 "sign with Hardened Runtime" % (tool,))
                break
        else:
            out["reason"] = ("no codesign/rcodesign on this host; Hardened "
                             "Runtime and library validation are OPERATOR "
                             "steps, not compiler flags")
    else:
        out["reason"] = "ELF: code signing is not part of the platform model"
    return out


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

    Returns ``{"ok", "missing", "wrong", "unavailable", "inert", "report"}``.
    ``missing`` lists a required-True field that is not True; ``wrong`` lists a
    required-False field that IS set. Both fail. An unparseable object fails
    before either list is considered, because "the parser did not look" is not
    evidence of safety.

    ``inert`` lists flags that are SET but have nothing behind them — measured
    2026-11-19: lld-link sets the CFG bit while leaving the load-config
    directory empty, so no guard table exists and the loader has nothing to
    enforce. A flag with no data is the "blindly enable every flag" failure the
    review warns about, so it FAILS the check rather than passing it.

    ``unavailable`` lists flags this toolchain cannot emit (see
    :data:`TOOLCHAIN_UNAVAILABLE`). They are excluded from the verdict because
    no flag would change them, but they are named so the gap is recorded rather
    than silently treated as satisfied.
    """
    canonical = canonical_platform(platform_name)
    want = expected_for(platform_name, toolchain)
    missing = [field for field, value in want.items()
               if value is True and not object_report.get(field)]
    wrong = [field for field, value in want.items()
             if value is False and object_report.get(field)]
    unavailable = [field for field, _value in REQUIRED.get(canonical, ())
                   if field not in want]
    # SET but unsupported by metadata. Only CFG has a data directory today, so
    # the pairing is explicit rather than a general rule that could misfire.
    inert = []
    if object_report.get("cfg") and not object_report.get("cfg_data"):
        inert.append("cfg")
    # PARTIAL CFG, reported rather than hidden. Measured 2026-11-19: an object
    # with a supplied `_load_config_used` carries GuardFlags 0x100
    # (CF_INSTRUMENTED) but NOT 0x400 (CF_FUNCTION_TABLE_PRESENT). Checks were
    # compiled in, so indirect-call sites do verify against the guard check
    # pointer — that is real protection, and `ok` stays True. But there is no
    # function table, so calls to addresses that are not statically valid
    # targets cannot be rejected at load time. A reader deciding whether to
    # trust the object needs both facts, so the weaker one is named instead of
    # being collapsed into a boolean.
    partial = []
    if object_report.get("cfg") and object_report.get("cfg_data"):
        if not object_report.get("cfg_instrumented"):
            partial.append("cfg_not_instrumented")
        if not object_report.get("cfg_function_table"):
            partial.append("cfg_no_function_table")
    # CET: the /CETCOMPAT flag is a REQUEST, not a result. Measured 2026-11-19
    # on the MSVC-ABI object: GuardFlags carried 0x100 (CF_INSTRUMENTED) and
    # NONE of the CET bits, so the image declares CET compatibility with no
    # shadow-stack metadata behind it. That is the same inert-flag trap as the
    # CFG bit one level up, and it is reported rather than assumed.
    if object_report.get("cfg") and not (object_report.get("cet_xfg")
                                         or object_report.get("cet_shadow_stack")):
        partial.append("cet_not_instrumented")
    return {"ok": (not missing and not wrong and not inert
                   and bool(object_report.get("valid"))),
            "missing": missing, "wrong": wrong,
            "unavailable": unavailable, "inert": inert,
            "partial": partial,
            "report": object_report}
