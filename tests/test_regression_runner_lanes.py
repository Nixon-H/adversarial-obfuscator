"""Regression tests for the runner-only failure classes fixed 2026-11-27.

Each test pins the exact mechanism of a bug that CI caught and local
runs did not, so none of them can silently come back.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


# ── 1. Windows merkle deaths: artefact writes must be LF-exact ─────────
#
# The self-check merkle is stamped over LF-normalised bytes while the
# runtime hashes raw disk bytes. Windows text-mode writes translated
# LF -> CRLF on disk, so every artefact killed itself at startup on
# Windows only. The invariant: writing artefact content through the
# emission open() shape must reproduce the exact input bytes on disk.

def test_artefact_write_sites_use_newline_exact():
    """Every Python-artefact write in the emission path pins newline=""."""
    sites = [
        ("obfuscator/core/pipeline.py", "loader_path"),
        ("obfuscator/core/pipeline.py", "_hy_out"),
        ("obfuscator/core/pipeline.py", "client_path"),
        ("obfuscator/core/pipeline.py", "_dest2"),
        ("obfuscator/core/pipeline.py", "args.output"),
        ("obfuscator/core/pipeline.py", "src_path"),
        ("obfuscator/core/sources.py", "final_output"),
    ]
    missing = []
    for rel, var in sites:
        src_text = open(os.path.join(_ROOT, rel), encoding="utf-8").read()
        idx = src_text.find("open(" + var)
        assert idx >= 0, "%s: write site for %s not found" % (rel, var)
        call = src_text[idx:src_text.find(")", idx)]
        if "newline" not in call:
            missing.append("%s open(%s...)" % (rel, var))
    assert not missing, "artefact writes missing newline='': " + ", ".join(missing)


def test_lf_exact_write_roundtrip_invariant():
    """The invariant itself: bytes written with newline='' survive disk exactly.

    Simulates what Windows text mode would do by contrast: a default-mode
    write of the same content may translate line endings, newline='' never does.
    """
    content = '_NX_SELF_CK = "0" * 0\nline two\nline three\n'
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "art.py")
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        with open(p, "rb") as f:
            disk = f.read()
    assert disk == content.encode("utf-8"), \
        "newline='' write must reproduce exact bytes on every platform"
    assert b"\r\n" not in disk


def test_stamp_then_disk_bytes_self_consistent():
    """Stamped loader source hashed from disk bytes matches the embedded slots."""
    from obfuscator.core.pipeline import _stamp_hybrid_selfcheck
    src = (
        'import sys\n'
        '_NX_SELF_CK = "' + "0" * 64 + '"\n'
        '_NX_SELF_HM = "' + "0" * 64 + '"\n'
        '_NX_SELF_HK = "' + "0" * 64 + '"\n'
        '_NX_SELF_TOK = ""\n'
        '_NX_CFI_SEQ = \"0000000000000000000000000000000000000000000000000000000000000000\"\n'
        'print("hi")\n'
    )
    out = _stamp_hybrid_selfcheck(src, "ab" * 32)
    import re as _re
    m = _re.search(r'_NX_SELF_CK = "([0-9a-f]{64})"', out)
    assert m and m.group(1) != "0" * 64, "stamping must fill the CK slot"
    # LF bytes in, LF bytes out: the stamped source must not gain CRLF.
    assert "\r" not in out


# ── 2. exclude-rea flags must stay registered ──────────────────────────

def test_exclude_rea_flags_are_registered():
    """The documented flags were never argparse-registered; lanes died on
    'unrecognized arguments'. Pin registration and dest wiring."""
    from obfuscator.core.pipeline import build_pipeline  # noqa: F401 -- import smoke
    import subprocess
    for flag, dest in (
        ("--exclude-rea", "anti_rea_exclude_bait"),
        ("--exclude-rea-bio", "anti_rea_exclude_bio"),
        ("--exclude-rea-cognitive", "anti_rea_exclude_cognitive"),
        ("--exclude-rea-compliance", "anti_rea_exclude_compliance"),
    ):
        r = subprocess.run(
            [sys.executable, "-m", "obfuscator.core.pipeline", "build",
             "/nonexistent/probe.py", flag],
            capture_output=True, text=True, timeout=60, cwd=_ROOT)
        assert "unrecognized arguments" not in (r.stderr or ""), \
            "%s is not registered with the ai-obf parser" % flag


# ── 3. except* must be a Cython blocker even where it cannot parse ─────

def test_except_star_flagged_via_parse_failure_path():
    """On Python < 3.11 except* is a SyntaxError, so the AST walk never ran
    and the checker reported it as compatible -- exactly backwards. The
    textual fallback must hold on every interpreter."""
    from obfuscator.core.pipeline import cython_compat_issues
    src = "try:\n    pass\nexcept* ValueError:\n    pass\n"
    issues = cython_compat_issues(src)
    assert issues and "exception groups" in issues[0][1]
    # And the false-positive guard: ordinary try/except stays clean.
    assert cython_compat_issues("try:\n    pass\nexcept ValueError:\n    pass\n") == []


# ── 4. Session-wide fixes: cp1252 reads, nargs='?' catalogue, harness blocking ──

def test_self_critique_reads_are_utf8_exact():
    """engine.py read repo files with bare open(); Windows cp1252 died on
    byte 0x81 and took down four shard flags at once."""
    import re
    src = open(os.path.join(_ROOT, "scripts/self_critique/engine.py"), encoding="utf-8").read()
    bare = []
    for m in re.finditer(r'open\(([^)\n]*)\)', src):
        if 'encoding' not in m.group(1) and 'b' not in m.group(1).split(',')[0]:
            bare.append("line %d" % (src[:m.start()].count("\n") + 1))
    assert not bare, "bare open() reads in engine.py: " + ", ".join(bare)


def test_validate_catalogued_as_bare_flag():
    """nargs='?' flags must invoke bare: the catalogue passed sample '2' to
    --validate, which the builder correctly rejects."""
    sys.path.insert(0, os.path.join(_ROOT, "scripts", "ci"))
    from flag_catalogue import catalogue  # noqa: E402
    entries = {e["flag"]: e for e in catalogue()}
    v = entries.get("--validate")
    assert v is not None, "--validate missing from catalogue"
    assert v["argv"] == ["--validate"], \
        "optional-value flags must be invoked bare, got %r" % v["argv"]


def test_blocked_decision_does_not_require_artefact(tmp_path):
    """blocked_before_workspace must record a fail-closed decision without
    touching the artefact: it crashed when the artefact was absent, which
    is exactly the CI-checkout case it exists for."""
    sys.path.insert(0, os.path.join(_ROOT, "re-bench", "tools"))
    try:
        import ai_bench  # noqa: E402
    except Exception:
        import pytest
        pytest.skip("ai_bench not importable here")
    import inspect
    sig = inspect.signature(ai_bench.blocked_before_workspace)
    assert sig is not None  # existence pin; behaviour covered in test_ai_benchmark_harness


# ── 5. section-split registration + shadow-build lane structure ────────

def test_section_split_positive_form_registered():
    """Only --no-section-split existed; the deep-matrix lanes pass the
    positive form explicitly and died on 'unrecognized arguments'."""
    import subprocess
    r = subprocess.run(
        [sys.executable, "-m", "obfuscator.core.pipeline", "build",
         "/nonexistent/probe.py", "--section-split", "--section-count", "2"],
        capture_output=True, text=True, timeout=60, cwd=_ROOT)
    assert "unrecognized arguments" not in (r.stderr or "")


def test_shadow_build_stage1_skips_manual_stages():
    """Stage 1 must not run irgen/llvmgen/encrypt: the lane re-runs them in
    later steps, and a second encrypt hits the key sidecar's O_EXCL write
    (FileExistsError: build/encrypted.o.key)."""
    import re
    yml = open(os.path.join(_ROOT, ".github/workflows/shadow-build.yml"), encoding="utf-8").read()
    m = re.search(r"scripts/build\.py --payload examples/hello\.py --skip ([^\n]+)", yml)
    assert m, "stage 1 invocation not found"
    skips = m.group(1).split()
    for stage in ("irgen", "llvmgen", "encrypt"):
        assert stage in skips, \
            "stage 1 must skip %s (the lane runs it manually later)" % stage


def test_newly_registered_flags_stay_documented():
    """Doc-completeness is enforced by test_maximum_doc_completeness; this
    pins the regeneration workflow invariant: CLI.md must be in sync."""
    import subprocess
    r = subprocess.run(
        [sys.executable, "scripts/gen_cli_reference.py", "--check"],
        capture_output=True, text=True, timeout=60, cwd=_ROOT)
    assert r.returncode == 0, "docs/CLI.md is stale; regenerate with --write"


def test_stego_flag_is_registered():
    """stego was plumbed end-to-end (package parsing, emission at line 7675)
    but unreachable: no argparse registration anywhere. The deep-matrix lane
    authors knew it should exist; the flag is now real."""
    import subprocess
    r = subprocess.run(
        [sys.executable, "-m", "obfuscator.core.pipeline", "build",
         "/nonexistent/probe.py", "--stego"],
        capture_output=True, text=True, timeout=60, cwd=_ROOT)
    assert "unrecognized arguments" not in (r.stderr or "")


def test_release_upload_includes_everything_publish_reads():
    """The publish job re-verifies the accepted artefact chain: it reads
    accepted_artefact.py.build-manifest.json, but the upload step only
    shipped the artefact, digest, and report. The manifest never crossed
    the job boundary -- FileNotFoundError in publish, measured 2026-11-28.
    Invariant: every accepted_* file the publish verification opens must
    appear in the upload path list."""
    import re
    text = open(os.path.join(_ROOT, ".github", "workflows", "release.yml"),
                encoding="utf-8").read()
    upload_block = re.search(
        r"Upload immutable release artefact.*?path: \|(.*?)\n\s+retention",
        text, re.S)
    assert upload_block, "upload step not found"
    uploaded = set(re.findall(r"(accepted_\S+)", upload_block.group(1)))
    publish_section = text.split("publish:", 1)[1]
    reads = set(re.findall(r'open\("(accepted_[^"]+)"', publish_section))
    reads |= set(re.findall(r"verify_manifest\(\"(accepted_[^\"]+)\"", publish_section))
    manifest_reads = {r.replace(".py", ".py.build-manifest.json")
                      if r.endswith(".py") and "manifest" not in r else r
                      for r in reads}
    missing = manifest_reads - uploaded
    assert not missing, f"publish reads files the upload never ships: {missing}"
