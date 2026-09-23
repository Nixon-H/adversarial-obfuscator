"""Adversarial dead-code injection: never-crash property (fixed flaky NameError).

The func-body dead-code templates once emitted `[x for xs ...]` with an
unbound element name; func-body injection had no try/except guard (unlike
the module path), so a poisoned decoder crashed at import ~10-40% of
builds (seed-dependent). Fixed: element is `z` (bound), injection is
guarded. These tests lock the property across seeds.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.adversarial import inject_adversarial_code


def _run_seed(seed):
    src = "def _dec():\n    return 42\nprint(_dec())\n"
    out = inject_adversarial_code(
        src, {"seed": seed, "func_count": 2, "mod_count": 2})
    compile(out, "<adv>", "exec")
    proc = subprocess.run([sys.executable, "-c", out], capture_output=True,
                          text=True, timeout=60)
    return proc


def test_injected_artifacts_run_across_seeds():
    for seed in range(10):
        proc = _run_seed(seed)
        assert proc.returncode == 0, (seed, proc.stderr[-1000:])
        assert "42" in proc.stdout, seed


def test_no_unbound_comprehension_element():
    # The fixed template family: every comprehension binds its element.
    import obfuscator.adversarial as adv
    for tmpl in (adv._MODULE_DEAD_CODE + adv._FUNC_BODY_DEAD_CODE):
        if "for xs in" in tmpl:
            assert "[z for xs in" in tmpl, tmpl
            assert "[x for xs in" not in tmpl, tmpl
