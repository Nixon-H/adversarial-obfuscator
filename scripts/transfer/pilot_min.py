"""Minimal calibration pilot: does the oracle-free attacker rank at all?

STATUS (2026-10-30): runs. The attacker ranks 3/3 top-1 on both the
unprotected and the obfuscated artefacts.

Reaching that number required fixing FOUR harness defects, each of which
produced a plausible-looking result first: an underscore filter that
excluded every renamed candidate; a first-callable reference pick that
chose the wrong function; a name-based scoring path; and -- the one that
survived three fixes -- passing the PLAIN path to the obfuscated scoring
call, so it loaded unrenamed functions against renamed candidates and
could never match. Every one of those defects made the protection look
better than it is.

n is three fixtures with two unrelated decoys: this is a calibration run,
not evidence about the corpus. The result is that structural ranking
survives this obfuscation at this size, which is a negative result for the
protection and the reason the real study needs harder candidates.


This is not the study. It is the Phase-2 calibration step, cut to what one
session can run honestly: a handful of real functions, an unprotected
baseline and one obfuscated build, ranked by the artifact-only attacker and
scored by the evaluator.

It answers three questions the protocol needs answered before a confirmatory
run:

  1. Does the artifact-only attacker rank the target above chance on an
     UNPROTECTED artefact?  If not, the attacker is too weak and no
     protection result from it would mean anything (gate G5).
  2. How far does that ranking fall on an obfuscated artefact?  A drop is
     the only thing that could justify a larger study.
  3. How long does a build and a ranking take?  That is the cost model the
     plan is missing.

Scoring uses ground truth, and only the scoring does: the attacker never
sees it. That separation is the whole point of the previous round's guard.
"""

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.diversity.generator import generate_variant  # noqa: E402
from scripts.transfer.attack import ArtifactOnlyAttack  # noqa: E402

FIXTURES = {
    "accumulate": (
        "def accumulate(values, lo, hi):\n"
        "    total = 0\n"
        "    for v in values:\n"
        "        if lo <= v < hi:\n"
        "            total += v * 2 + 1\n"
        "    return total\n"
    ),
    "count_words": (
        "def count_words(text):\n"
        "    seen = {}\n"
        "    for w in text.split():\n"
        "        seen[w] = seen.get(w, 0) + 1\n"
        "    return seen\n"
    ),
    "clamp": (
        "def clamp(x, lo, hi):\n"
        "    if x < lo:\n"
        "        return lo\n"
        "    if x > hi:\n"
        "        return hi\n"
        "    return x\n"
    ),
}

# A second, unrelated function in each fixture so ranking is not trivial.
DECOYS = (
    "def helper_alpha(a, b, c):\n"
    "    return (a + b) * c\n"
    "\n"
    "def helper_beta(items):\n"
    "    return [i for i in items if i]\n"
)


INPUTS = {
    "accumulate": [([1, 2, 3, 4, 5], 2, 5), ([0, 10], 0, 1)],
    "count_words": [("a b a",), ("",), ("x",)],
    "clamp": [(5, 0, 3), (-1, 0, 3), (2, 0, 3)],
}


# Hard fixtures: the target sits among SIBLING functions with the same arity
# and near-identical shape. This is the condition the pilot's own document
# said was missing -- unrelated decoys are trivially separable, siblings are
# not, and siblings are what real modules contain.
FIXTURES_HARD = {
    "sumselected": (
        "def sumselected(values, lo, hi):\n"
        "    total = 0\n"
        "    for v in values:\n"
        "        if lo <= v < hi:\n"
        "            total += v\n"
        "    return total\n"
    ),
    "sibling_a": (
        "def sibling_a(values, lo, hi):\n"
        "    total = 0\n"
        "    for v in values:\n"
        "        if lo <= v < hi:\n"
        "            total += v * 2\n"
        "    return total\n"
    ),
    "sibling_b": (
        "def sibling_b(values, lo, hi):\n"
        "    total = 0\n"
        "    for v in values:\n"
        "        if lo < v <= hi:\n"
        "            total += v\n"
        "    return total\n"
    ),
    "sibling_c": (
        "def sibling_c(values, lo, hi):\n"
        "    total = 1\n"
        "    for v in values:\n"
        "        if lo <= v < hi:\n"
        "            total += v\n"
        "    return total\n"
    ),
    "sibling_d": (
        "def sibling_d(values, lo, hi):\n"
        "    out = []\n"
        "    for v in values:\n"
        "        if lo <= v < hi:\n"
        "            out.append(v)\n"
        "    return out\n"
    ),
}

INPUTS_HARD = {
    "sumselected": [([1, 2, 3, 4, 5], 2, 5), ([0, 10], 0, 1)],
}

def _rank(attack, path):
    art = attack.develop({"path": path}, tempfile.mkdtemp())
    out = attack.apply(art, {"path": path}, tempfile.mkdtemp())
    return out["ranking"]


def _behavioural_match(artefact_path, original_fn, target_name, candidates, inputs):
    """Find which candidate behaves like the original on fixed inputs.

    Names are renamed by the obfuscation, so name-based scoring is invalid:
    the first version of this pilot scored 0/3 for that reason alone. The
    evaluator may legitimately compare behaviour; the attacker may not.
    """
    import importlib.util

    def load(path, ns):
        spec = importlib.util.spec_from_file_location(ns, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    ref_mod = load(original_fn, "nxk_ref_%d" % abs(hash(original_fn)))
    # The reference is the function by its ORIGINAL name (the plain source
    # is unrenamed). Picking "the first callable in dir()" selected
    # helper_alpha alphabetically and made the pilot score 0/3 for that
    # reason alone -- twice over, in fact, before the underscore filter was
    # also removed.
    ref_name = target_name
    ref = getattr(ref_mod, ref_name)
    expected = [ref(*a) for a in inputs]

    tgt_mod = load(artefact_path, "nxk_tgt_%d" % abs(hash(artefact_path)))
    hits = []
    for name in candidates:
        fn = getattr(tgt_mod, name, None)
        if not callable(fn):
            continue
        try:
            got = [fn(*a) for a in inputs]
        except Exception:
            continue
        if got == expected:
            hits.append(name)
    return hits


def _topk_behaviour(ranking, hits, k):
    for i, name in enumerate(ranking[:k]):
        if name in hits:
            return i + 1
    return None


def run(hard=False):
    attack = ArtifactOnlyAttack()
    fixtures = FIXTURES_HARD if hard else FIXTURES
    inputs_map = INPUTS_HARD if hard else INPUTS
    rows = []
    # Only functions present in the inputs map are TARGETS; the rest are
    # decoys/siblings. Iterating over every fixture made sibling fixtures
    # raise KeyError.
    for name in [k for k in fixtures if k in inputs_map]:
        with tempfile.TemporaryDirectory(prefix="nxk_pilot_") as td:
            # Target plus decoys: unrelated helpers in the easy condition,
            # true sibling functions in the hard one.
            others = "".join(f for k, f in fixtures.items() if k != name)
            src = fixtures[name] + "\n" + (others if hard else DECOYS)
            plain = os.path.join(td, "plain.py")
            with open(plain, "w", encoding="utf-8") as f:
                f.write(src)
            t0 = time.monotonic()
            obf = generate_variant(src, 0, {"master_seed": 424242})
            build_s = round(time.monotonic() - t0, 2)
            obf_path = os.path.join(td, "obf.py")
            with open(obf_path, "w", encoding="utf-8") as f:
                f.write(obf)

            t1 = time.monotonic()
            r_plain = _rank(attack, plain)
            r_obf = _rank(attack, obf_path)
            rank_s = round(time.monotonic() - t1, 2)

            # Behavioural identity: the evaluator may compare outputs, the
            # attacker may not. Names are useless here (they are renamed).
            inputs = inputs_map[name]
            plain_hits = _behavioural_match(plain, plain, name, r_plain, inputs)
            # The artefact path must be the OBFUSCATED file: passing the
            # plain one loaded unrenamed functions while the ranking held
            # renamed candidates, so nothing could ever match and the
            # pilot reported 0/3 for obfuscated artefacts.
            obf_hits = _behavioural_match(obf_path, plain, name, r_obf, inputs)

            rows.append({
                "function": name,
                "candidates": len(r_plain),
                "plain_top1": _topk_behaviour(r_plain, plain_hits, 1),
                "obf_top1": _topk_behaviour(r_obf, obf_hits, 1),
                "obf_top3": _topk_behaviour(r_obf, obf_hits, 3),
                "build_s": build_s,
                "rank_both_s": rank_s,
            })
    return rows


if __name__ == "__main__":
    hard = "--hard" in sys.argv
    rows = run(hard=hard)
    print("condition: %s" % ("siblings" if hard else "unrelated decoys"))
    print(json.dumps(rows, indent=2))
    plain_hits = sum(1 for r in rows if r["plain_top1"] == 1)
    obf_hits = sum(1 for r in rows if r["obf_top1"] == 1)
    print("\nplain top-1: %d/%d   obf top-1: %d/%d   obf top-3: %d/%d"
          % (plain_hits, len(rows), obf_hits, len(rows),
             sum(1 for r in rows if r["obf_top3"] is not None), len(rows)))
