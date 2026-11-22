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

# scripts/fuzz/nx_fuzz.py -> fuzz -> scripts -> repository root. The first
# version of this line stopped one level short (at ``scripts``), so every
# target raised ModuleNotFoundError: obfuscator before it fuzzed a single
# byte -- and libFuzzer reports that as "fuzz target exited", which reads
# like a finding. Caught only by actually running the campaign.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, REPO)

# Strict resource limits (the register asks for them): the fuzz body must
# never allocate unbounded memory because a length field said so.
MAX_INPUT = 1 << 16          # 64 KiB of fuzz input is plenty for a header
MAX_PACK_SECTIONS = 64

TARGETS = ("pack", "manifest", "elf", "pe", "macho", "state")

#: Parser handles, populated by :func:`_load_parsers` INSIDE an Atheris
#: instrumentation context. Importing them inside each fuzz body (the first
#: version of this file did) means the module is imported once, un-instrumented,
#: and libFuzzer then reports "no interesting inputs were found so far" while
#: still burning 200k exec/s: a campaign that measures nothing and looks like
#: coverage.
_PARSERS = {}


def _load_parsers():
    """Import the parsers under instrumentation; return the handle map."""
    try:
        import atheris
    except ImportError:
        atheris = None
    ctx = atheris.instrument_imports() if atheris is not None else None
    if ctx is not None:
        ctx.__enter__()
    try:
        from obfuscator import native_harden as _nh
        from obfuscator.build_manifest import MANIFEST_SUFFIX, verify_manifest
        from obfuscator.core.pipeline import _object_kind
        from obfuscator.pack_state import state_digest
        from obfuscator.section_split import stream_join
    finally:
        if ctx is not None:
            ctx.__exit__(None, None, None)
    _PARSERS.update({
        "nh": _nh,
        "MANIFEST_SUFFIX": MANIFEST_SUFFIX,
        "verify_manifest": verify_manifest,
        "object_kind": _object_kind,
        "state_digest": state_digest,
        "stream_join": stream_join,
    })
    return _PARSERS


def _refuse_if_accepted(cond, what):
    """An acceptance is the bug class this harness exists to find."""
    if cond:
        raise AssertionError("UNINTENDED ACCEPTANCE: %s" % (what,))


def fuzz_pack(data):
    """The invariant: stream_join may only succeed on an UNMUTATED pack.

    The first version asserted that ``stream_join`` never returns data at
    all, which is wrong: a legitimate pack decrypts, so the very seed corpus
    that makes coverage possible tripped it on the first unit. An oracle
    that fires on correct behaviour is worse than no oracle -- it would have
    been "fixed" by loosening it until it detected nothing.

    The real security property is narrower and checkable: given the key,
    ``stream_join`` may accept ONLY a pack whose sections, count, total and
    version are the ones the builder produced. Any other pack must raise.
    A successful join of a mutated pack means the metadata binding (v2 MAC
    context, per-section index/total, state digest) failed to catch an edit
    -- which is exactly the bypass this fuzzer is for.
    """
    stream_join = _PARSERS["stream_join"]
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
        # Accepted. That is legitimate ONLY if this is a pack the builder
        # itself produced for this key -- identified by the keyed hint, the
        # declared structure and the plaintext, not by "it did not raise".
        _check_accepted_pack(pack, out)


#: Packs the seed builder actually produced, keyed by their JSON skeleton.
_KNOWN_GOOD_SKELETONS = set()


def _skeleton(pack):
    """Structure-only fingerprint: no ciphertext, no state digest."""
    secs = pack.get("sections")
    if not isinstance(secs, list):
        return None
    try:
        return (int(pack.get("v", 0)), int(pack.get("count", -1)),
                int(pack.get("total", -1)),
                tuple(sorted(int(s.get("i", -1)) for s in secs
                             if isinstance(s, dict))))
    except (TypeError, ValueError):
        return None


def _check_accepted_pack(pack, out):
    """An acceptance is legitimate only for an unmutated builder pack."""
    skel = _skeleton(pack)
    if skel is None:
        _refuse_if_accepted(True, "a pack with no usable structure decrypted")
    try:
        declared_total = int(pack["total"])
    except Exception:
        _refuse_if_accepted(True, "a pack with no readable total decrypted")
    _refuse_if_accepted(
        len(out) != declared_total,
        "stream_join returned %d bytes for a pack declaring %d"
        % (len(out), declared_total))
    _refuse_if_accepted(
        skel not in _KNOWN_GOOD_SKELETONS,
        "a pack whose structure %r was never built by the seed generator "
        "decrypted under the key" % (skel,))


def fuzz_manifest(data):
    """Feed bytes to verify_manifest through a mkstemp pair."""
    MANIFEST_SUFFIX = _PARSERS["MANIFEST_SUFFIX"]
    verify_manifest = _PARSERS["verify_manifest"]
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
    """ELF magic routing plus the shared object-kind classifier.

    The first version of this target called ``verify_pe_bytes`` -- the PE
    parser -- so the ELF row fuzzed a parser it did not name, and the ELF
    entry point (`_object_kind`, which decides whether a blob may arm native
    mode) was never fed a byte. The classifier is the security-relevant ELF
    surface in this tree: it is what decides a blob is loadable, and a
    false positive there arms FORCE_NATIVE_MODE on a file that cannot load.
    """
    nh = _PARSERS["nh"]
    object_kind = _PARSERS["object_kind"]
    if len(data) > MAX_INPUT:
        return
    kind = object_kind(data)
    _refuse_if_accepted(kind is not None and len(data) < 8,
                        "a <%d-byte buffer classified as %r" % (8, kind))
    if data[:4] == b"\x7fELF":
        # The PE reader must not claim an ELF object. This is the cross-format
        # confusion bug class: a verifier that identifies by "not MZ" and
        # returns a report full of False reads as "PE, unhardened".
        rep = nh.verify_pe_bytes(data)
        _refuse_if_accepted(rep.get("valid") is True,
                            "an ELF object reported as a valid PE")
        _refuse_if_accepted(rep.get("kind") != "pe",
                            "PE reader mislabelled an ELF object")


def fuzz_pe(data):
    nh = _PARSERS["nh"]
    if len(data) > MAX_INPUT:
        return
    rep = nh.verify_pe_bytes(data)
    _refuse_if_accepted(
        rep.get("cfg_function_table") is True and rep.get("valid") is not True,
        "a CFG function table reported on an object the parser calls invalid")
    # A CFG *function table* is the only thing a loader can enforce. The
    # declaration bit alone (dll_characteristics 0x4000) must never be
    # reported as an enforced CFG -- that distinction is the whole reason
    # `cfg_data` exists.
    _refuse_if_accepted(
        rep.get("cfg_function_table") is True
        and rep.get("load_config_size", 0) == 0,
        "CFG function table reported with an empty load config")


def fuzz_macho(data):
    nh = _PARSERS["nh"]
    if len(data) > MAX_INPUT:
        return
    rep = nh.verify_macho_bytes(data)
    _refuse_if_accepted(rep.get("valid") is True and len(data) < 16,
                        "a <16-byte buffer reported as a valid Mach-O")


def fuzz_state(data):
    state_digest = _PARSERS["state_digest"]
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


def _seed_blobs(target):
    """Return structurally VALID inputs the fuzzer can start from.

    Coverage-guided fuzzing needs to start inside the parser. The first
    campaign ran with an empty corpus, and measured exactly what that
    produces: ``cov: 1 ft: 1``, 8.5 million executions in 46 s and ONE new
    unit -- a campaign that is fast and useless. Random bytes never satisfy
    ``json.loads``, so the pack/state targets never reached a single branch
    of the code they exist to test. Seeding with a real pack makes every
    mutation land inside the parser instead of against its front door.
    """
    seeds = []
    if target in ("pack", "state"):
        from obfuscator.section_split import split_sealed
        key = b"\x11" * 32
        for n_sec in (1, 2, 4):
            try:
                pack = split_sealed(b"payload-bytes" * n_sec, sections=n_sec,
                                    key=key,
                                    nonce_seed=b"seed" + bytes([n_sec]))
            except Exception:
                continue
            _KNOWN_GOOD_SKELETONS.add(_skeleton(pack))
            seeds.append(json.dumps(pack).encode("utf-8"))
        if seeds:
            base = json.loads(seeds[0].decode("utf-8"))
            for field, value in (("count", 0), ("count", 99), ("total", -1),
                                 ("total", 0), ("v", 1), ("v", 3),
                                 ("state", "00" * 32), ("state", None)):
                variant = dict(base)
                variant[field] = value
                seeds.append(json.dumps(variant).encode("utf-8"))
    elif target == "manifest":
        seeds = [b'{"version": 1}', b"null", b"[]",
                 b'{"version":"1","build":{}}']
    elif target == "elf":
        seeds = [b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 56, b"\x7fELF"]
    elif target == "pe":
        seeds = [b"MZ" + b"\x00" * 62 + b"\x40\x00\x00\x00" + b"PE\x00\x00",
                 b"MZ"]
    elif target == "macho":
        seeds = [b"\xcf\xfa\xed\xfe" + b"\x00" * 28,
                 b"\xca\xfe\xba\xbe" + b"\x00" * 12]
    return seeds


def _write_seed_corpus(target):
    """Materialise the seed corpus in a private temp dir; return its path."""
    seeds = _seed_blobs(target)
    if not seeds:
        return None
    corpus = tempfile.mkdtemp(prefix="nx-fuzz-corpus-")
    for blob in seeds:
        fd, path = tempfile.mkstemp(prefix="seed-", dir=corpus)
        with os.fdopen(fd, "wb") as fh:
            fh.write(blob)
    return corpus


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
    _load_parsers()
    corpus = _write_seed_corpus(target)
    # libFuzzer's own time budget. Passed through argv because Atheris forwards
    # unknown libFuzzer flags verbatim; the first campaign passed an int where
    # a flag list was expected and libFuzzer aborted before fuzzing.
    sys.argv = [sys.argv[0], "-max_total_time=%d" % seconds,
                "-max_len=%d" % MAX_INPUT, "-print_final_stats=1"]
    if corpus is not None:
        sys.argv.append(corpus)

    def _one(data):
        body(data)

    atheris.Setup(sys.argv, _one, enable_python_coverage=True)
    atheris.Fuzz()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
