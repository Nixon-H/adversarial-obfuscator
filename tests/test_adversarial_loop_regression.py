"""Regression tests for adversarial_loop.py (HIGH: rebuild_payload passed
--skip-irgen-style dash flags that scripts/build.py no longer defines, so
every rebuild failed with argparse exit 2 and the loop could never progress;
the benchmark-failure path decremented round_num, looping forever)."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _build_argparse_flags():
    """All option strings scripts/build.py's parser actually defines."""
    src = (ROOT / "scripts" / "build.py").read_text()
    return set(re.findall(r'add_argument\(\s*"(--[a-z0-9-]+)"', src))


def test_rebuild_payload_uses_only_real_build_flags():
    import adversarial_loop as al
    src = Path(al.__file__).read_text()
    m = re.search(r'def rebuild_payload.*?cmd = \[(.*?)\]', src, re.S)
    assert m, "rebuild_payload cmd list not found"
    cmd_block = m.group(1)
    flags = re.findall(r'"(--[a-z0-9-]+)', cmd_block)
    known = _build_argparse_flags()
    for f in flags:
        assert f in known, f"rebuild_payload passes {f}, not defined by scripts/build.py"
    # --skip takes stage names as separate args, not --skip-<stage>
    assert '"--skip"' in cmd_block


def test_build_py_accepts_the_loop_skip_invocation():
    # argparse-level check: the exact flags rebuild_payload emits must parse
    proc = subprocess.run(
        [sys.executable, "scripts/build.py", "--payload", "/nonexistent.py",
         "--skip", "irgen", "llvmgen", "encrypt", "relay"],
        capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert "unrecognized arguments" not in proc.stderr, proc.stderr[-500:]


def test_main_loop_has_no_round_decrement():
    src = Path(ROOT / "adversarial_loop.py").read_text()
    main_body = src[src.index("def main()"):]
    assert "round_num -= 1" not in main_body, "round_num -= 1 makes the loop infinite on persistent benchmark failure"
    assert 'cfg["max_bench_failures"]' in main_body
    assert "consecutive_failures >= max_bench_failures" in main_body


def test_check_regressions_points_at_tests_dir():
    import adversarial_loop as al
    src = Path(al.__file__).read_text()
    body = src[src.index("def check_regressions"):src.index("# ─── Main Loop")]
    assert 'ROOT / "tests" / test_file' in body
    # every candidate must exist now (silently skipping missing ones hid drift)
    for name in re.findall(r'"(test_[a-z_0-9]+\.py)"', body):
        assert (ROOT / "tests" / name).exists(), f"check_regressions candidate missing: {name}"
