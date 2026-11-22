"""The fuzz harness must stay able to measure coverage.

The seventh pass recorded the §5 row as "mutation-driven, not truly
coverage-guided" and blamed the interpreter: "libFuzzer reports the
sanitizer coverage runtime is absent". Re-running the campaign showed that
explanation was wrong. Three defects in ``scripts/fuzz/nx_fuzz.py`` made the
campaign measure nothing while looking healthy:

  * ``REPO`` was one directory short, so every target died on
    ``ModuleNotFoundError`` -- which libFuzzer reports as "fuzz target
    exited", i.e. as a finding;
  * the parsers were imported INSIDE the fuzz body, after Atheris had
    stopped instrumenting, so coverage sat at ``cov: 1`` and libFuzzer
    printed "Is the code instrumented for coverage?";
  * there was no seed corpus, so random bytes never satisfied ``json.loads``
    and the pack/state targets never reached a single branch of the parser.

Worse, the pack oracle asserted that ``stream_join`` *never* returns data.
A legitimate pack decrypts, so the first real seed tripped it. Those checks
are pinned here as static invariants, because all three are silent -- the
campaign exits 0 and prints impressive execution counts either way.
"""
import ast
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HARNESS = os.path.join(REPO, "scripts", "fuzz", "nx_fuzz.py")


def _source():
    with open(HARNESS, encoding="utf-8") as fh:
        return fh.read()


def _tree():
    return ast.parse(_source())


def _load_harness():
    """Import the harness module (it imports cleanly without atheris)."""
    spec = importlib.util.spec_from_file_location("_nx_fuzz_harness", HARNESS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_harness_resolves_the_repository_root():
    """REPO must point at the repo root -- scripts/fuzz/x.py is three deep."""
    module = _load_harness()
    assert os.path.isdir(os.path.join(module.REPO, "obfuscator")), (
        "REPO resolved to %r, which does not contain the obfuscator package; "
        "every fuzz target will die on import and libFuzzer will report that "
        "as a target exit" % (module.REPO,))
    assert os.path.abspath(module.REPO) == os.path.abspath(REPO), (
        "REPO resolved to %r, expected %r" % (module.REPO, REPO))


def test_the_parsers_are_imported_under_instrumentation():
    """No fuzz body may import a parser itself.

    An import inside the body runs after Atheris has instrumented, so the
    module is never covered and the campaign silently degenerates to
    mutation testing.
    """
    offenders = []
    for node in ast.walk(_tree()):
        if not isinstance(node, ast.FunctionDef):
            continue
        if not node.name.startswith("fuzz_"):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, (ast.Import, ast.ImportFrom)):
                mods = ([a.name for a in sub.names]
                        if isinstance(sub, ast.Import)
                        else [sub.module or ""])
                if any((m or "").startswith("obfuscator") for m in mods):
                    offenders.append((node.name, mods))
    assert not offenders, (
        "these fuzz bodies import the parser themselves, so it is never "
        "instrumented and coverage stays at 1: %r" % (offenders,))


def test_the_harness_preloads_parsers_before_setup():
    """_load_parsers() must be called, and only under instrument_imports."""
    module = _load_harness()
    assert hasattr(module, "_load_parsers"), (
        "the harness must preload the parsers under an instrumentation "
        "context; without that the campaign cannot see coverage")
    src = _source()
    assert "instrument_imports" in src, (
        "the harness must enter atheris.instrument_imports() around the "
        "parser imports")
    # And the call must happen before Setup, or it is too late.
    assert src.index("_load_parsers()") < src.index("atheris.Setup"), (
        "_load_parsers() is called after atheris.Setup; instrumentation must "
        "be in place before the target starts running")
    assert "enable_python_coverage=True" in src, (
        "Setup must keep python coverage enabled, or Atheris only sees the "
        "native runtime and the Python parsers are invisible")


def test_a_seed_corpus_is_provided():
    """Coverage-guided fuzzing needs to start inside the parser."""
    module = _load_harness()
    assert hasattr(module, "_write_seed_corpus"), (
        "the campaign must be given a seed corpus; with an empty corpus the "
        "JSON targets never satisfy json.loads and coverage stays at 1")
    assert hasattr(module, "_seed_blobs"), "the seed generator is missing"
    seeds = module._seed_blobs("pack")
    assert seeds, "the pack target produced no seeds"
    assert all(isinstance(s, bytes) for s in seeds), (
        "seeds must be raw bytes")
    # A seed must be a REAL pack from the project's builder, not a
    # hand-typed approximation: a hand-typed one does not exercise the code
    # the loader actually runs.
    import json
    first = json.loads(seeds[0].decode("utf-8"))
    assert set(first) >= {"sections", "count", "total", "state", "v"}, (
        "the pack seed is not builder-shaped: %r" % (sorted(first),))


def test_the_pack_oracle_accepts_a_legitimate_pack():
    """The oracle must not fire on correct behaviour.

    This is the defect that made the first seeded run abort on unit 7: the
    oracle asserted stream_join never returns data, but a valid pack
    decrypts. An oracle that rejects correct output gets loosened until it
    detects nothing.
    """
    src = _source()
    assert "_KNOWN_GOOD_SKELETONS" in src, (
        "the pack oracle must be able to tell a builder-produced pack from a "
        "mutated one")
    assert "_check_accepted_pack" in src, (
        "an acceptance must be validated against the declared total and the "
        "known-good structure, not against 'it did not raise'")
    # The old, wrong oracle must be gone.
    assert 'out is not None, "stream_join returned data"' not in src, (
        "the old oracle (any successful join is a finding) is back; it "
        "rejects legitimate packs")


def test_the_linux_target_exercises_the_elf_classifier():
    """The elf row must not fuzz the PE parser.

    The first version routed ``elf`` to ``verify_pe_bytes``, so the ELF row
    fuzzed a parser it did not name and ``_object_kind`` -- the function that
    decides a blob may arm native mode -- was never fed a byte.
    """
    src = _source()
    body = None
    for node in ast.walk(_tree()):
        if isinstance(node, ast.FunctionDef) and node.name == "fuzz_elf":
            body = node
            break
    assert body is not None, "fuzz_elf is missing"
    text = ast.get_source_segment(src, body) or ""
    assert "object_kind" in text, (
        "the elf target must exercise _object_kind, the classifier that "
        "decides whether a blob is loadable")
    assert "verify_pe_bytes" in text, (
        "the elf target should assert the PE reader does not claim an ELF "
        "object (cross-format confusion)")
