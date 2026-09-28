"""Variant-matrix construction + semantic-equivalence gate (G2).

Builds, per corpus program:
- unprotected arm: the original source (control 1).
- seed_only arm: N variants, ONE frozen pass set, distinct seeds.
- hetero arm: N variants, heterogeneous frozen pass sets, distinct seeds.

Every variant passes the semantic gate (script-level behavior identical
to the original on fixed demo invocations) or it is excluded and
reported — transfer over non-equivalent builds is confounded.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

from scripts.transfer import corpus as corpus_mod
from scripts.transfer import protocol


# Fixed demo argv per corpus program (mirrors each _demo dispatcher).
DEMO_ARGV = {
    "calc": [["add", "2", "3"], ["mul", "6", "7"], ["fib", "10"], ["gcd", "48", "18"]],
    "parser": [["slugify", "Hello", "World!"], ["count_words", "one", "two"], ["shout", "hey"]],
    "auth": [["make_token", "alice", "s3cret"], ["check_password", "pw", "salt", "x"]],
    "store": [["store_get", "a", "dflt"], ["store_keys"], ["store_merge"]],
    "codec": [["rle_encode", "aaabbc"], ["rle_decode", "a3b2c1"], ["xor_bytes", "hi"]],
    "sched": [["priority_pick"], ["slot_hash", "hello", "64"], ["rotate_list", "a,b,c", "1"]],
}


def run_script(path, argv, timeout=60):
    try:
        proc = subprocess.run(
            [sys.executable, path] + argv,
            capture_output=True, text=True, timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return None, "", "timeout"


def semantic_gate(original_path, variant_path, prog_name):
    """True iff variant behaves identically to the original on demo argv.

    Returns (passed: bool, detail: str). Any crash, timeout, rc or
    stdout mismatch fails the variant (excluded + reported).
    """
    for argv in DEMO_ARGV.get(prog_name, []):
        rc0, out0, _ = run_script(original_path, argv)
        rc1, out1, err1 = run_script(variant_path, argv)
        if rc0 != 0:
            return False, "original nonzero rc on %r" % (argv,)
        if rc1 is None:
            return False, "variant timeout on %r" % (argv,)
        if rc1 != rc0 or out1 != out0:
            return False, "mismatch on %r rc=%r err=%s" % (argv, rc1, err1[-200:])
    return True, "ok"


def build_matrix(prog_entry, out_root, n_hetero=3, n_seed=3):
    """Build the full variant matrix for one corpus program.

    Returns dict with variant records + exclusions + config_freeze_hash.
    Layout: out_root/<prog>/unprotected.py, hetero_{i}.py, seed_{i}.py.
    """
    from scripts.diversity.generator import DiversityGenerator

    prog = corpus_mod.load_program(prog_entry["dir"])
    name = prog_entry["name"]
    cfg = prog["config"]
    freeze_hash = corpus_mod.config_freeze_hash(cfg)
    out_dir = os.path.join(out_root, name)
    os.makedirs(out_dir, exist_ok=True)

    orig_path = os.path.join(out_dir, "unprotected.py")
    with open(orig_path, "w", encoding="utf-8") as f:
        f.write(prog["source"])

    records, excluded = [], []

    def _add_variant(path, arm, pass_set, seed):
        ok, detail = semantic_gate(orig_path, path, name)
        rec = {"path": path, "arm": arm, "pass_set": list(pass_set),
               "seed": seed, "gate_passed": ok, "gate_detail": detail}
        (records if ok else excluded).append(rec)
        return rec

    # hetero arm: distinct pass set per build (cycled), distinct seeds.
    hetero_sets = cfg["hetero_pass_sets"]
    for i in range(n_hetero):
        pset = hetero_sets[i % len(hetero_sets)]
        seed = cfg["master_seed"] * 1000 + 11 + i
        gen = DiversityGenerator(config={"master_seed": seed, "pass_sets": [pset]})
        with tempfile.TemporaryDirectory(prefix="nxk_hetero_") as td:
            paths = gen.generate(orig_path, 1, td)
            with open(paths[0], encoding="utf-8") as f:
                code = f.read()
        dst = os.path.join(out_dir, "hetero_%d.py" % i)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(code)
        _add_variant(dst, protocol.ARM_HETERO, pset, seed)

    # seed-only arm: ONE pass set, distinct seeds (negative control).
    seed_sets = cfg["seed_only_pass_sets"]
    pset0 = seed_sets[0]
    for i in range(n_seed):
        seed = cfg["master_seed"] * 1000 + 101 + i
        gen = DiversityGenerator(config={"master_seed": seed, "pass_sets": [pset0]})
        with tempfile.TemporaryDirectory(prefix="nxk_seed_") as td:
            paths = gen.generate(orig_path, 1, td)
            with open(paths[0], encoding="utf-8") as f:
                code = f.read()
        dst = os.path.join(out_dir, "seed_%d.py" % i)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(code)
        _add_variant(dst, protocol.ARM_SEED_ONLY, pset0, seed)

    return {
        "program": name,
        "split": prog_entry["split"],
        "unprotected": orig_path,
        "original_source": prog["source"],
        "variants": records,
        "excluded": excluded,
        "config_freeze_hash": freeze_hash,
        "ground_truth": prog["ground_truth"],
        "vectors": prog["vectors"],
    }
