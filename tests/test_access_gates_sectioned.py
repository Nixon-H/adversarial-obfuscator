"""Access gates must actually reach the SECTIONED loader.

Benchmark 2026-11-17, access-gate matrix: three gates were wired only into
the packed loader's build context, so on the sectioned path (the default)
they were silently ignored — an operator setting an expiry, a geo block or
one-shot got an artefact with none of them:

* ``--access expire=YYYY-MM-DD``  -> no ``_NX_EXP_DATE``, ran past its date
* ``--access block-countries=…``  -> no geo gate, ran from a blocked region
* ``--access one-shot``           -> artefact survived every run

Each is asserted here at the emitter level (the value reaches the emitted
loader and is enforced before the entry point), plus the trial gate's
enforcement shape, which was correct but untested end to end.
"""
from obfuscator.core.pipeline import generate_hybrid_loader_script

_BLANKS = {"native_blobs": "", "fallback_blob": ""}


def _emit(**kw):
    kw.setdefault("identity_gate", False)
    kw.setdefault("self_check", False)
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANKS), b"", "11" * 32, section_split=True, **kw)
    return src


def _entry_at(src):
    at = src.rfind('if __name__ in ("__main__", "__mp_main__"):')
    return at if at >= 0 else src.rfind('if __name__ == "__main__":')


# --- expire -----------------------------------------------------------------

def test_expire_gate_is_emitted_before_the_entry():
    src = _emit(expire_ts=1000000000.0)
    assert "_NX_EXP_DATE = 1000000000.0" in src
    pos = src.find("_NX_EXP_DATE")
    assert 0 <= pos < _entry_at(src), "expiry must gate the payload"


def test_expire_gate_kills_on_a_past_date():
    """The emitted gate must reach a kill on an expired build.

    Run in a CHILD process: the emitted kill ladder calls os._exit(137),
    which would take the pytest runner with it (that is exactly how
    _nx_strict_fail broke a full suite once).
    """
    import subprocess
    import sys
    src = _emit(expire_ts=1.0)  # 1970: always past
    head = src.split('if __name__ in ("__main__", "__mp_main__"):')[0]
    child = ("import sys\n"
             "sys.argv[0] = '<t>'\n"
             "ns = {'__name__': '__main__', '__file__': '<t>'}\n"
             "exec(compile(%r, '<loader>', 'exec'), ns)\n"
             "print('SURVIVED')\n" % (head,))
    p = subprocess.run([sys.executable, "-c", child], capture_output=True,
                       text=True, timeout=120)
    assert p.returncode == 137, (p.returncode, p.stdout[-200:], p.stderr[-200:])
    assert "SURVIVED" not in p.stdout


def test_expire_gate_absent_when_not_configured():
    src = _emit()
    assert "_NX_EXP_DATE" not in src


# --- geo --------------------------------------------------------------------

def test_geo_gate_is_emitted_before_the_entry():
    src = _emit(blocked_countries=["RU"])
    assert "_NX_GEO" in src
    assert "'b_c': ['RU']" in src
    pos = src.find("_NX_GEO")
    assert 0 <= pos < _entry_at(src)


def test_geo_gate_carries_all_four_lists():
    src = _emit(allowed_countries=["US"], blocked_countries=["RU"],
                allowed_regions=["R1"], blocked_regions=["R2"])
    assert "'a_c': ['US']" in src
    assert "'b_c': ['RU']" in src
    assert "'a_r': ['R1']" in src
    assert "'b_r': ['R2']" in src


def test_geo_gate_absent_when_not_configured():
    assert "_NX_GEO" not in _emit()


def test_geo_gate_fails_closed_without_a_location():
    """No location resolvable -> not ok -> kill (fail closed)."""
    src = _emit(blocked_countries=["RU"])
    assert "_nx_geo_ok = False" in src
    assert "if not _nx_geo_ok:" in src
    assert "_nx_kill('geo-blocked')" in src


# --- one-shot ---------------------------------------------------------------

def test_one_shot_is_emitted():
    src = _emit(one_shot=True)
    assert "_NX_ONE_SHOT = True" in src
    assert "_nx_one_shot_cleanup" in src
    assert "atexit" in src
    # it must overwrite before unlinking (a plain unlink leaves the bytes
    # recoverable on the filesystem)
    assert "urandom(_sz)" in src or "urandom" in src


def test_one_shot_absent_when_not_configured():
    assert "_NX_ONE_SHOT" not in _emit()


def test_one_shot_cleanup_deletes_the_target(tmp_path):
    """Execute the emitted cleanup against a real file."""
    src = _emit(one_shot=True)
    # Pull out the whole one-shot block: from its `try:` through the
    # `except Exception: pass` that closes it.  A non-greedy match to the
    # first newline cut the try in half (SyntaxError in the extracted text).
    start = src.find("try:\n    import atexit as _nx_os_atexit")
    assert start >= 0, "one-shot block not found"
    end = src.find("    pass\n", src.find("_nx_os_atexit.register", start))
    assert end > start
    block = src[start:end + len("    pass\n")]
    target = tmp_path / "artifact.py"
    target.write_text("secret-bytes\n", encoding="utf-8")
    ns = {"__name__": "__main__"}
    import sys
    old_argv = sys.argv[:]
    sys.argv = [str(target)]
    try:
        exec(compile(block, "<oneshot>", "exec"), ns)
        token = ns["_NX_ONE_SHOT_TOK"].decode("ascii")
        target.write_text("prefix\n" + token + "\nsuffix\n", encoding="utf-8")
        ns["_nx_one_shot_cleanup"]()
    finally:
        sys.argv = old_argv
    assert not target.exists(), "one-shot did not delete the artefact"


def test_one_shot_refuses_env_controlled_victim_without_artifact_marker(tmp_path):
    """NX_ORIGIN must not become an arbitrary file-deletion primitive."""
    src = _emit(one_shot=True)
    start = src.find("try:\n    import atexit as _nx_os_atexit")
    end = src.find("    pass\n", src.find("_nx_os_atexit.register", start))
    block = src[start:end + len("    pass\n")]
    artifact = tmp_path / "artifact.py"
    victim = tmp_path / "victim.txt"
    victim.write_text("do-not-delete\n", encoding="utf-8")
    ns = {"__name__": "__main__"}
    import os
    import sys
    old_argv = sys.argv[:]
    old_origin = os.environ.get("NX_ORIGIN")
    sys.argv = [str(artifact)]
    os.environ["NX_ORIGIN"] = str(victim)
    try:
        exec(compile(block, "<oneshot>", "exec"), ns)
        token = ns["_NX_ONE_SHOT_TOK"].decode("ascii")
        artifact.write_text("artifact\n" + token + "\n", encoding="utf-8")
        ns["_nx_one_shot_cleanup"]()
    finally:
        sys.argv = old_argv
        if old_origin is None:
            os.environ.pop("NX_ORIGIN", None)
        else:
            os.environ["NX_ORIGIN"] = old_origin
    assert not artifact.exists(), "marked artefact was not removed"
    assert victim.read_text(encoding="utf-8") == "do-not-delete\n"


def test_one_shot_refuses_symlink_target(tmp_path):
    """A symlink must not redirect the overwrite into another file."""
    src = _emit(one_shot=True)
    start = src.find("try:\n    import atexit as _nx_os_atexit")
    end = src.find("    pass\n", src.find("_nx_os_atexit.register", start))
    block = src[start:end + len("    pass\n")]
    real = tmp_path / "real.py"
    link = tmp_path / "link.py"
    ns = {"__name__": "__main__"}
    import sys
    old_argv = sys.argv[:]
    sys.argv = [str(link)]
    try:
        exec(compile(block, "<oneshot>", "exec"), ns)
        token = ns["_NX_ONE_SHOT_TOK"].decode("ascii")
        real.write_text("artifact\n" + token + "\n", encoding="utf-8")
        link.symlink_to(real)
        ns["_nx_one_shot_cleanup"]()
    finally:
        sys.argv = old_argv
    assert real.exists(), "symlink redirection erased the underlying file"
    assert link.exists(), "the symlink itself should not be unlinked as an artefact"


# --- trial (shape) ----------------------------------------------------------

def test_trial_gate_result_is_enforced():
    src = _emit(trial_seconds=60)
    assert "_NX_TRIAL_GATE" in src
    assert 'if _NX_TRIAL_GATE != "ok":' in src
    assert '_nx_kill("trial-" + str(_NX_TRIAL_GATE))' in src


def test_packed_one_shot_paths_require_the_build_identity_marker():
    """The packed loader family must enforce the same victim-file constraint."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source = open(os.path.join(root, "obfuscator", "core", "sources.py"),
                  encoding="utf-8").read()
    assert source.count('_BUILD_ID.encode("ascii")') >= 2
    assert source.count('O_NOFOLLOW') >= 2
    assert 'if origin: targets.add(origin)\n                for t in targets:\n                    if _nixon_オペレーション운영.path.exists(t)' not in source
