"""§4 enforcement moved into the native blob (§5l boundary push, 2026-11-19).

The accepted loader boundary said: the payload is hidden, the wrapper is not.
The option recorded for pushing that boundary -- "move the enforcement into
the native blob" -- is implemented, and this file pins what it means:

  * native/enforcement.c exports nx_apply_protections() and it actually
    applies the anti-dump policy (measured on the kernel, not assumed);
  * every blob this pipeline builds carries that <entry> -- the loader
    REFUSES a blob without it, so a producer that forgets the source ships
    dead artefacts rather than unprotected ones;
  * a native-only artefact (--package native-only, fallback DISABLED) has no
    Python execution path to payload plaintext: its text must not carry the
    anti-dump syscalls (DS 4.1 Flash reconstructed the old block verbatim --
    that is the §5l finding this change addresses);
  * any build that CAN reach payload plaintext through Python (sectioned or
    bytecode fallback) still emits the Python block -- the fallback runs in
    production for those builds, and dropping the block would be a §4
    regression on that path, not a boundary push.
"""
import os
import re
import sys
import tempfile

import pytest

# Repo root, built without climbing dirname chains: join the parts as
# strings and normalise once, then verify containment wherever a path is
# used for I/O (the runtime refuses anything that escapes the repo).
_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.realpath(os.sep.join((_HERE, os.pardir)))
sys.path.insert(0, REPO)


def _in_repo(*parts):
    """Normalise and confine a path to the repo root."""
    candidate = os.path.realpath(os.sep.join((REPO,) + tuple(parts)))
    if candidate != REPO and not candidate.startswith(REPO + os.sep):
        raise AssertionError("path escapes the repo root")
    return candidate


ENFORCEMENT_C = _in_repo("native", "enforcement.c")
PROBE = _in_repo("tests", "fixtures", "enforcement_probe.py")

#: The behaviour-bearing syscall names DS 4.1 Flash recovered from the old
#: top-of-loader block (§5l). A native-only artefact must not carry them.
SYSCALL_MARKERS = ("prctl", "setrlimit", "RLIMIT_CORE", "PR_SET_DUMPABLE",
                   "PT_DENY_ATTACH")


def _loader(native_only):
    from obfuscator.core import pipeline as pl
    return pl.generate_hybrid_loader_script(
        native_blobs={"linux": "AAAA"} if native_only else {},
        bytecode_fallback=b"", key_hex="00" * 32,
        native_only=native_only, build_id="enf-test") [0]


# ── the emission rule ─────────────────------------------------------------
def test_native_only_loader_carries_no_syscall_names():
    """The whole point of the boundary push: the syscalls leave the text."""
    loader = _loader(native_only=True)
    for marker in SYSCALL_MARKERS:
        assert marker not in loader, (
            "%r recovered verbatim is exactly the §5l finding; a native-only "
            "build must not carry it in text" % (marker,))


def test_native_only_loader_calls_the_enforcement_entry_fail_closed():
    loader = _loader(native_only=True)
    assert "nx_apply_protections" in loader, (
        "the enforcement call must be present -- its absence would mean the "
        "artefact runs with NO anti-dump policy")
    assert "lacks enforcement entry" in loader, (
        "a blob without the entry must be refused, not skipped")


def test_plain_build_still_emits_the_python_block():
    """Builds that can reach plaintext through Python keep the block."""
    loader = _loader(native_only=False)
    for marker in ("prctl", "setrlimit", "RLIMIT_CORE"):
        assert marker in loader, (
            "a build with a Python path to payload plaintext must keep the "
            "anti-dump block (a §4 regression if dropped)")


def test_memguard_snippet_is_report_only_when_native_enforced():
    """The second readable prctl site switches form, not disappears.

    memguard's snippet was the second place the syscalls appeared in text.
    For native-only builds it reports the enforcement bitmask the loader
    captured, so the diagnostic channel stays meaningful without syscall
    names. The snippet is compiled, never executed: installing the handlers
    or the syscalls inside pytest would be process-wide side effects, and
    the mask itself is measured by the blob probe below.
    """
    from obfuscator.memguard import emit_snippet
    native = emit_snippet(native_enforced=True)
    for marker in SYSCALL_MARKERS:
        assert marker not in native
    assert "_NX_NATIVE_ENF" in native, (
        "the report must carry the enforcement bitmask the loader recorded")
    compile(native, "<mg_native>", "exec")  # syntax-checked, never executed
    assert "NIXON_MEM_REPORT" in native, (
        "the diagnostic channel must survive the switch")
    plain = emit_snippet()
    assert "prctl" in plain and "RLIMIT_CORE" in plain


# ── the native side ─────────────────--------------------------------------
def test_enforcement_source_exists_and_carries_the_handlers():
    assert os.path.isfile(ENFORCEMENT_C), (
        "native/enforcement.c is the boundary push; without it the loader "
        "refuses every blob")
    src = open(ENFORCEMENT_C, encoding="utf-8").read()
    assert "nx_apply_protections" in src, "the entry is missing"
    assert "_exit(137)" in src, (
        "the silent kill-ladder handlers must ride along with the "
        "enforcement entry (the file is self-contained by design)")


@pytest.mark.skipif(sys.platform != "linux", reason="Linux syscalls")
def test_built_blob_applies_the_policy_in_a_subprocess():
    """Measured, not assumed: the real blob applies the anti-dump policy.

    The blob is produced by the pipeline's own local build (production path
    compiles payload.c + enforcement.c together), then a committed probe
    fixture dlopens it, calls the enforcement entry, and prints the kernel
    state. The probe runs in a SUBPROCESS through the shared run_artifact
    helper: the policy is process-wide, and applying it inside pytest would
    change how every later test crashes and what /proc exposes.
    """
    from tests import _artifact_run
    from obfuscator.core.pipeline import build_local_cython
    payload = ("def main():\n"
               "    print('enf-blob-probe')\n"
               "\n"
               "if __name__ == '__main__':\n"
               "    main()\n")
    blob_data, blob_name = build_local_cython(payload)
    assert blob_data, "local blob build failed -- see the build log above"
    tmp = tempfile.mkdtemp(prefix="nx-enf-blob-")
    try:
        # the probe loads the blob with ctypes.CDLL, which does not care
        # about the extension, so a fixed file name suffices; containment
        # is validated before anything is written
        blob_path = os.path.realpath(os.sep.join((tmp, "blob.so")))
        if blob_path != tmp and not blob_path.startswith(tmp + os.sep):
            raise AssertionError("blob path escaped the scratch dir")
        with open(blob_path, "wb") as fh:
            fh.write(blob_data)
        result = _artifact_run.run_artifact(
            PROBE, timeout=120,
            env=dict(os.environ, NX_ENF_SO=blob_path,
                     PYTHONPATH=REPO))
        assert result.returncode == 0, (result.returncode, result.stderr[-400:])
        lines = (result.stdout or "").strip().splitlines()
        assert lines, "probe printed nothing"
        match = re.match(r"mask=(\d+) core=(\d+)", lines[-1])
        assert match, result.stdout
        mask = int(match.group(1))
        assert mask & 1, "dumpable was not cleared (mask=%d)" % mask
        assert mask & 2, "core limit was not zeroed (mask=%d)" % mask
        assert match.group(2) == "0", "kernel still allows core dumps"
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


# ── P0 (reviewer, 2026-11-20): WHAT runs before enforcement ──────────────
#
# "enforcement runs before any native code" is FALSE on Linux: the dynamic
# linker runs every shared object's constructors (.init_array, .ctors,
# _init) BEFORE dlopen() returns. The invariant that actually matters is
# narrower, and it is what the test below proves:
#
#   no PAYLOAD initialization or execution happens before enforcement.
#
# The payload sets a builtins flag at module init, so the check needs no
# marker file: the forked child inspects interpreter state directly, and the
# object is written through pytest's tmp_path fixture.

ORDER_PAYLOAD = (
    "import builtins as _b\n"
    "_b._NX_PAYLOAD_RAN = True\n"
    "\n"
    "\n"
    "def main():\n"
    "    return 'ok'\n"
)


@pytest.mark.skipif(sys.platform != "linux", reason="fork/ELF semantics")
def test_no_payload_code_runs_before_enforcement(tmp_path):
    """Payload init must not happen before nx_apply_protections().

    The child dlopens WITHOUT running init, checks the flag, calls the
    enforcement entry, checks again, then imports and checks a third time.
    Fork keeps the parent untouched (the child is the one made
    non-dumpable).
    """
    import base64
    import builtins

    from obfuscator.core.pipeline import build_local_cython

    blob, _ = build_local_cython(ORDER_PAYLOAD)
    assert blob, "blob build failed"
    if isinstance(blob, str):
        blob = base64.b64decode(blob)
    so_file = tmp_path / "payload_module.so"
    so_file.write_bytes(blob)
    so_path = str(so_file)
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        code = 0
        try:
            os.close(read_fd)
            import ctypes
            import importlib.util as _ilu
            out = ["before=%s" % getattr(builtins, "_NX_PAYLOAD_RAN", False)]
            lib = ctypes.CDLL(so_path)
            out.append("after_dlopen=%s"
                       % getattr(builtins, "_NX_PAYLOAD_RAN", False))
            mask = int(lib.nx_apply_protections() or 0)
            out.append("after_enforce=%s"
                       % getattr(builtins, "_NX_PAYLOAD_RAN", False))
            out.append("mask=%d" % mask)
            spec = _ilu.spec_from_file_location("payload", so_path)
            mod = _ilu.module_from_spec(spec)
            spec.loader.exec_module(mod)
            out.append("after_init=%s"
                       % getattr(builtins, "_NX_PAYLOAD_RAN", False))
            os.write(write_fd, ("|".join(out)).encode())
        except BaseException as exc:  # noqa: BLE001 - report, then exit
            try:
                os.write(write_fd,
                         ("error=%s" % type(exc).__name__).encode())
            except Exception:
                pass
            code = 1
        finally:
            os._exit(code)
    os.close(write_fd)
    chunks = []
    while True:
        chunk = os.read(read_fd, 4096)
        if not chunk:
            break
        chunks.append(chunk)
    os.close(read_fd)
    _, status = os.waitpid(pid, 0)
    report = b"".join(chunks).decode("utf-8", "replace")
    assert os.waitstatus_to_exitcode(status) == 0, report
    assert "after_dlopen=False" in report, (
        "payload code ran during dlopen() -- a constructor is doing payload "
        "work before enforcement: %s" % report)
    assert "after_enforce=False" in report, (
        "payload ran before enforcement was applied: %s" % report)
    assert "mask=3" in report, (
        "enforcement bitmask was not 3 (dumpable + core): %s" % report)
    assert "after_init=True" in report, (
        "the payload never ran even after module init: %s" % report)


def _elf_sections(raw):
    """Parse ELF64 section headers: [(name, type, offset, size, link)]."""
    import struct
    endian = "<" if raw[5] == 1 else ">"
    e_shoff = struct.unpack(endian + "Q", raw[0x28:0x30])[0]
    e_shentsize = struct.unpack(endian + "H", raw[0x3A:0x3C])[0]
    e_shnum = struct.unpack(endian + "H", raw[0x3C:0x3E])[0]
    e_shstrndx = struct.unpack(endian + "H", raw[0x3E:0x40])[0]
    rows = []
    for index in range(e_shnum):
        off = e_shoff + index * e_shentsize
        sh = raw[off:off + e_shentsize]
        sh_name, sh_type = struct.unpack(endian + "II", sh[:8])
        sh_flags, sh_addr, sh_offset, sh_size, sh_link = struct.unpack(
            endian + "QQQQI", sh[8:44])
        rows.append((sh_name, sh_type, sh_offset, sh_size, sh_link))
    if e_shstrndx >= len(rows):
        return []
    str_off = rows[e_shstrndx][2]
    named = []
    for sh_name, sh_type, sh_offset, sh_size, sh_link in rows:
        at = str_off + sh_name
        stop = raw.find(b"\x00", at)
        name = raw[at:stop if stop != -1 else at + 64].decode("ascii",
                                                              "replace")
        named.append((name, sh_type, sh_offset, sh_size, sh_link))
    return named


def _elf_init_array(raw):
    """(.init_array addresses) from an ELF64 image, or None when absent."""
    import struct
    endian = "<" if raw[5] == 1 else ">"
    for name, _sh_type, sh_offset, sh_size, _link in _elf_sections(raw):
        if name == ".init_array":
            body = raw[sh_offset:sh_offset + sh_size]
            return [struct.unpack(endian + "Q", body[i:i + 8])[0]
                    for i in range(0, len(body) - 7, 8)]
    return None


def _elf_export_addrs(raw):
    """{function name: address} from .dynsym."""
    import struct
    endian = "<" if raw[5] == 1 else ">"
    sections = _elf_sections(raw)
    exports = {}
    for name, sh_type, sh_offset, sh_size, sh_link in sections:
        if sh_type != 11 or name != ".dynsym":      # SHT_DYNSYM
            continue
        if sh_link >= len(sections):
            continue
        _n, _t, strtab_off, strtab_size, _l = sections[sh_link]
        for index in range(sh_size // 24):          # sizeof(Elf64_Sym)
            ent = raw[sh_offset + index * 24: sh_offset + index * 24 + 24]
            (st_name, st_info, st_other, st_shndx, st_value,
             st_size) = struct.unpack(endian + "IBBHQQ", ent)
            if not st_name:
                continue
            stop = raw.find(b"\x00", strtab_off + st_name,
                            strtab_off + strtab_size)
            symbol = raw[strtab_off + st_name:stop].decode("ascii", "replace")
            exports[symbol] = st_value
    return exports


@pytest.mark.skipif(sys.platform != "linux", reason="ELF inspection")
def test_the_real_blob_constructors_are_linker_scaffolding():
    """The shipped object's .init_array holds no payload entry.

    Measured on a real blob with a pure-Python ELF64 parse: the blob carries
    constructor entries from the C runtime (frame_dummy / __cxa_finalize
    scaffolding), never PyInit_payload. That is why the measured precondition
    (constructors run first) does not contradict the invariant (payload init
    runs after enforcement).
    """
    import base64
    from obfuscator.core.pipeline import build_local_cython

    blob, _ = build_local_cython(ORDER_PAYLOAD)
    assert blob, "blob build failed"
    if isinstance(blob, str):
        blob = base64.b64decode(blob)
    assert blob[:4] == b"\x7fELF", "shipped blob is not an ELF object"
    entries = _elf_init_array(blob)
    if entries is None:
        pytest.skip("blob carries no .init_array")
    live = [entry for entry in entries if entry]
    assert len(live) <= 4, (
        "more constructor entries than expected for a Cython module (%d); "
        "inspect them before trusting the ordering claim" % len(live))
    payload_export = _elf_export_addrs(blob).get("PyInit_payload")
    assert payload_export is not None, (
        "the shipped blob does not export PyInit_payload")
    assert payload_export not in live, (
        "PyInit_payload is in .init_array -- payload initialization would "
        "run inside dlopen()")
