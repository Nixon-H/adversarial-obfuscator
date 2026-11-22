"""Coverage-guided fuzzing harness for the security-sensitive parsers.

Review register, seventh pass, §5: "Use coverage-guided fuzzing, retain
crash-inducing inputs as regression fixtures, and apply strict resource
limits. ... The goal is not simply zero crashes. It is proving that
malformed input cannot produce an unintended acceptance or bypass."

Targets (the register's list):
    pack     — the section_split pack parser / verifier
    manifest — the build manifest parser and signature verification
    elf      — the PE/ELF header reporting in native_harden
    pe       — PE extended DLL characteristics + CFG parsing
    macho    — Mach-O header parsing
    state    — the pack-state digest validation

The harness treats an UNINTENDED ACCEPTANCE as the bug: a parser that
returns a valid-looking result for hostile bytes is recorded as an ACCEPT
finding rather than only counting crashes.

Run (atheris is not vendored; install it separately):

    python3 -m venv /tmp/fuzzvenv && /tmp/fuzzvenv/bin/pip install atheris
    NX_FUZZ_TARGET=pack NX_FUZZ_SECONDS=120 \
        /tmp/fuzzvenv/bin/python scripts/fuzz/nx_fuzz.py

Without atheris the module imports cleanly and prints the instructions, so
it is safe to keep in the tree and in the shard lists.
"""
import base64
import json
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

# Strict resource limits (the register asks for them): the fuzz body must
# never allocate unbounded memory because a length field said so.
MAX_INPUT = 1 << 16          # 64 KiB of fuzz input is plenty for a header
MAX_PACK_SECTIONS = 64

TARGETS = ("pack", "manifest", "elf", "pe", "macho", "state")


def _refuse_if_accepted(cond, what):
    """An acceptance is the bug class this harness exists to find."""
    if cond:
        raise AssertionError("UNINTENDED ACCEPTANCE: %s" % (what,))


def fuzz_pack(data):
    from obfuscator.section_split import stream_join
    key = b"\x11" * 32
    if len(data) > MAX_INPUT:
        return
    candidates = [data]
    try:
        candidates.append(base64.b85decode(data))
    except Exception:
        pass
    for candidate in candidates:
        try:
            pack = json.loads(candidate.decode("utf-8", "strict"))
        except Exception:
            continue
        if not isinstance(pack, dict):
            continue
        secs = pack.get("sections")
        if isinstance(secs, list) and len(secs) > MAX_PACK_SECTIONS:
            continue
        try:
            out = stream_join(pack, key)
        except Exception:
            continue
        _refuse_if_accepted(out is not None, "stream_join returned data")


def fuzz_manifest(data):
    """Feed bytes to verify_manifest through a mkstemp pair."""
    from obfuscator.build_manifest import MANIFEST_SUFFIX, verify_manifest
    if len(data) > MAX_INPUT:
        return
    workdir = tempfile.mkdtemp(prefix="nx-fuzz-manifest-")
    try:
        art_fd, art = tempfile.mkstemp(suffix=".py", dir=workdir)
        with os.fdopen(art_fd, "w", encoding="utf-8") as fh:
            fh.write("print(1)\n")
        man_fd, man = tempfile.mkstemp(suffix=MANIFEST_SUFFIX, dir=workdir)
        with os.fdopen(man_fd, "wb") as fh:
            fh.write(data)
        # verify_manifest derives the manifest path from the artefact path,
        # so the artefact must sit beside it under the canonical name.
        canonical = os.path.join(workdir, "payload" + ".py")
        os.replace(art, canonical)
        os.replace(man, canonical + MANIFEST_SUFFIX)
        res = verify_manifest(canonical)
        _refuse_if_accepted(res.get("ok") is True,
                            "manifest of %d bytes verified" % len(data))
    finally:
        for name in os.listdir(workdir):
            try:
                os.unlink(os.path.join(workdir, name))
            except OSError:
                pass
        try:
            os.rmdir(workdir)
        except OSError:
            pass


def fuzz_elf(data):
    from obfuscator import native_harden as nh
    if len(data) > MAX_INPUT:
        return
    rep = nh.verify_pe_bytes(data)
    _refuse_if_accepted(rep.get("valid") is True and len(data) < 4,
                        "a <4-byte buffer reported valid")


def fuzz_pe(data):
    from obfuscator import native_harden as nh
    if len(data) > MAX_INPUT:
        return
    rep = nh.verify_pe_bytes(data)
    _refuse_if_accepted(
        rep.get("cfg_function_table") is True and rep.get("valid") is not True,
        "a CFG function table reported on an object the parser calls invalid")


def fuzz_macho(data):
    from obfuscator import native_harden as nh
    if len(data) > MAX_INPUT:
        return
    rep = nh.verify_macho_bytes(data)
    _refuse_if_accepted(rep.get("valid") is True and len(data) < 16,
                        "a <16-byte buffer reported as a valid Mach-O")


def fuzz_state(data):
    from obfuscator.pack_state import state_digest
    if len(data) > MAX_INPUT:
        return
    try:
        doc = json.loads(data.decode("utf-8", "strict"))
    except Exception:
        return
    if not isinstance(doc, dict):
        return
    try:
        digest = state_digest(doc.get("sections") or [], doc.get("count", 0),
                              doc.get("total", 0))
    except Exception:
        return
    _refuse_if_accepted(digest is None, "state_digest returned None")


BODIES = {
    "pack": fuzz_pack,
    "manifest": fuzz_manifest,
    "elf": fuzz_elf,
    "pe": fuzz_pe,
    "macho": fuzz_macho,
    "state": fuzz_state,
}


def main(argv):
    target = os.environ.get("NX_FUZZ_TARGET", "pack")
    if target not in BODIES:
        print("unknown target %r; choose one of %s" % (target, TARGETS))
        return 2
    body = BODIES[target]
    try:
        import atheris
    except ImportError:
        print("atheris is not installed, so coverage-guided fuzzing cannot "
              "run here.\nThis harness stays in the tree so the campaign is "
              "reproducible:\n\n"
              "  python3 -m venv /tmp/fuzzvenv\n"
              "  /tmp/fuzzvenv/bin/pip install atheris\n"
              "  NX_FUZZ_TARGET=%s NX_FUZZ_SECONDS=120 "
              "/tmp/fuzzvenv/bin/python scripts/fuzz/nx_fuzz.py\n\n"
              "The structured malformed-input matrix (tests/test_parser_fuzz"
              ".py) covers the same\nparsers without the tool and retains its "
              "fixtures as regressions." % target)
        return 0
    seconds = int(os.environ.get("NX_FUZZ_SECONDS", "60"))

    def _one(data):
        body(data)

    atheris.Setup(sys.argv, _one, enable_python_coverage=True)
    atheris.Fuzz()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
