"""Holdout-corpus loader (G2). Splits: calibration / development / held_out.

Each program dir holds prog.py, vectors.json, ground_truth.json,
config.json (frozen pass sets + master seed). held_out/ programs must
not inform planner calibration or pass-set choice (protocol.py).
"""
import hashlib
import json
import os

SPLITS = ("calibration", "development", "held_out")

_CORPUS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus")


def list_programs(split=None):
    splits = [split] if split else list(SPLITS)
    out = []
    for sp in splits:
        d = os.path.join(_CORPUS_DIR, sp)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            pdir = os.path.join(d, name)
            if os.path.isdir(pdir) and os.path.isfile(os.path.join(pdir, "prog.py")):
                out.append({"split": sp, "name": name, "dir": pdir})
    return out


def load_program(prog_dir):
    def _load(fn):
        with open(os.path.join(prog_dir, fn), encoding="utf-8") as f:
            return json.load(f)

    with open(os.path.join(prog_dir, "prog.py"), encoding="utf-8") as f:
        source = f.read()
    return {
        "dir": prog_dir,
        "source": source,
        "vectors": _load("vectors.json"),
        "ground_truth": _load("ground_truth.json"),
        "config": _load("config.json"),
    }


def config_freeze_hash(config):
    """sha256 over canonical pass-set config (anti-tuning rule)."""
    canonical = json.dumps(
        {
            "hetero_pass_sets": config["hetero_pass_sets"],
            "seed_only_pass_sets": config["seed_only_pass_sets"],
            "master_seed": config["master_seed"],
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
