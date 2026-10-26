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
import tempfile
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.diversity.generator import generate_variant


def _run_variant(source, seed, args=()):
    code = generate_variant(
        source, 0,
        {"master_seed": seed,
         "pass_sets": [["rename", "dead_code", "mba", "cfg_flatten", "vm"]]})
    # The probe is written into a fresh temp dir: the old hardcoded
    # /tmp/opencode path was a scratch directory from one developer's
    # machine and did not exist on CI (or anywhere else).
    with tempfile.TemporaryDirectory(prefix="nixon_flat_") as tmp:
        probe = os.path.join(tmp, "flat_probe.py")
        with open(probe, "w") as f:
            f.write(code)
        return subprocess.run([sys.executable, probe] + list(args),
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


def test_flattened_three_block_order_across_seeds():
    # Regression: the flattener chained blocks in SHUFFLED order, so any
    # >=3-block function executed out of order whenever the shuffle moved
    # a later block ahead (codec rle_encode exclusions in H0/H1/H5).
    # Execution must follow original program order on every seed.
    src = textwrap.dedent("""\
        def rle_encode(text):
            if not text:
                return ""
            out = []
            run = text[0]
            count = 1
            for ch in text[1:]:
                if ch == run[-1] and count < 9:
                    count += 1
                else:
                    out.append(run[-1] + str(count))
                    run = ch
                    count = 1
            out.append(run[-1] + str(count))
            return "".join(out)
        print(rle_encode("aaabbc"))
        print(rle_encode(""))
        """)
    for seed in range(1, 13):
        r = _run_variant(src, seed)
        assert r.returncode == 0, (seed, r.stderr[-500:])
        assert r.stdout.splitlines() == ["a3b2c1", ""], seed


def test_flattened_block_order_observable():
    # Order-sensitive appends: any block permutation is observable.
    src = textwrap.dedent("""\
        def f(x):
            log = []
            log.append("first")
            if x:
                log.append("second")
            else:
                log.append("other")
            log.append("third")
            return "-".join(log)
        print(f(True))
        print(f(False))
        """)
    for seed in range(1, 9):
        r = _run_variant(src, seed)
        assert r.returncode == 0, (seed, r.stderr[-500:])
        assert r.stdout.strip().splitlines() == [
            "first-second-third", "first-other-third"], seed
