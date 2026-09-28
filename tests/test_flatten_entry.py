"""ControlFlowFlattener entry-state regression tests.

Bug: the flattened dispatcher initialized _nx_state to the first block
in SHUFFLED order instead of the entry block (original_idx 0), so any
function whose entry block didn't sort first executed mid-function
code with unbound locals (UnboundLocalError). Fix: rotate the shuffled
order so original_idx 0 leads; pairwise chain links preserved.
"""
import os
import subprocess
import sys
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.diversity.generator import generate_variant


def _run_variant(source, seed, args=()):
    code = generate_variant(
        source, 0,
        {"master_seed": seed,
         "pass_sets": [["rename", "dead_code", "mba", "cfg_flatten", "vm"]]})
    with open("/tmp/opencode/flat_probe.py", "w") as f:
        f.write(code)
    return subprocess.run([sys.executable, "/tmp/opencode/flat_probe.py"] + list(args),
                          capture_output=True, text=True, timeout=120)


def test_flattened_fib_across_seeds():
    src = textwrap.dedent("""\
        def fib(n):
            a, b = 0, 1
            for _ in range(n):
                a, b = b, a + b
            return a
        print(fib(10))
        """)
    for seed in (1, 2, 3, 7, 11, 42, 99, 1234):
        r = _run_variant(src, seed)
        assert r.returncode == 0, (seed, r.stderr[-500:])
        assert r.stdout.strip() == "55", seed


def test_flattened_multi_block_across_seeds():
    # Entry block must run first regardless of shuffle: three blocks
    # where later blocks depend on earlier bindings.
    src = textwrap.dedent("""\
        def f(x):
            a = x + 1
            if a > 2:
                b = a * 10
            else:
                b = a * 100
            return b - a
        print(f(5))
        print(f(0))
        """)
    for seed in (3, 7, 21, 77):
        r = _run_variant(src, seed)
        assert r.returncode == 0, (seed, r.stderr[-500:])
        assert r.stdout.strip().splitlines() == ["54", "99"], seed
