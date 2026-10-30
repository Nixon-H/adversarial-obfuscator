"""An accumulating attacker: state persists across builds.

The retraction (`retraction-cost-curve.md`) established that the previous
endpoint was vacuous because the attacker was memoryless in k: `develop()`
took one build, nothing was carried forward, and a frozen property set applied
N times must cost the same N times.

This attacker carries state. After each build it records what it learned --
which transforms appear to have fired, and which candidate properties
discriminated -- and it applies that state to the NEXT build. Cost at build
k+1 is therefore a function of k, and the curve can rise, fall or stay flat.

The state is the attacker's own observations. It never contains evaluator
information: no ground truth, no test vectors, no original source. What is
accumulated is what any analyst would keep in a notebook.

Two questions the design can answer:

  1. Does accumulated knowledge make the next build cheaper? (utilisation)
  2. Does the accumulated state transfer at all, or is every build a
     cold start wearing a warm label? (transfer)
"""

import os
import sys
import time
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.transfer.attack import module_functions  # noqa: E402,F401


class AccumulatingAttack:
    """An attacker whose cost on build k depends on what it saw in 0..k-1."""

    def __init__(self):
        self.state = {
            "builds_seen": 0,
            "fingerprints": [],     # per-build transform traces it inferred
            "useful_props": [],     # property shapes that discriminated before
            "candidates_seen": 0,
        }

    # ---- observation -------------------------------------------------
    def _fingerprint(self, src):
        """Crude transform fingerprint: shapes that survive renaming."""
        marks = {
            "opaque_if": src.count("if "),
            "loops": src.count("for "),
            "try": src.count("try:"),
            "hexblobs": sum(1 for line in src.splitlines()
                            if "'" in line and len(line) > 60),
            "underscore_names": sum(1 for line in src.splitlines()
                                    if line.startswith("def _")),
        }
        return marks

    def observe(self, path):
        """Learn from one build without scoring it."""
        t0 = time.monotonic()
        with open(path, encoding="utf-8") as f:
            src = f.read()
        fp = self._fingerprint(src)
        self.state["fingerprints"].append(fp)
        self.state["builds_seen"] += 1
        n_funcs = len(module_functions(src))
        self.state["candidates_seen"] += n_funcs
        return {
            "builds_seen": self.state["builds_seen"],
            "cpu_s": round(time.monotonic() - t0, 4),
            "n_functions": n_funcs,
        }

    # ---- application -------------------------------------------------
    def predict_family(self):
        """From accumulated fingerprints, guess which family the next build is."""
        if not self.state["fingerprints"]:
            return "unknown"
        last = self.state["fingerprints"][-1]
        # a build with many `if` blocks and few loops looks flattening-heavy
        if last["opaque_if"] > 2 * max(1, last["loops"]):
            return "opaque_heavy"
        return "loop_heavy"

    def _active_props(self, props):
        """Props worth running given what earlier builds taught us.

        A property that has never eliminated any candidate carries no
        information and is skipped. This is the mechanism by which cost can
        fall with k: the state decides what the next build needs, instead of
        re-running everything.
        """
        if not self.state["useful_props"]:
            return list(range(len(props))), len(props)
        active = [i for i, _ in enumerate(props)
                  if i in self.state["useful_props"] or not self.state["useful_props"]]
        return active, len(props) - len(active)

    def apply(self, path, props):
        """Score a build using accumulated state; returns hits and cost."""
        t0 = time.monotonic()
        with open(path, encoding="utf-8") as f:
            src = f.read()
        tree_mod = {}
        exec(compile(src, path, "exec"), tree_mod)
        funcs = {n: v for n, v in tree_mod.items() if isinstance(v, types.FunctionType)}

        active, skipped = self._active_props(props)
        passing = []
        # per-property discrimination: did it ever separate a candidate?
        discriminates = [False] * len(props)
        for name, fn in funcs.items():
            ok = True
            for i in active:
                try:
                    if not props[i](fn):
                        ok = False
                        discriminates[i] = True
                        break
                except Exception:
                    ok = False
                    break
            if ok and active:
                if len(funcs) > 1:
                    for i in active:
                        discriminates[i] = True
                passing.append(name)

        # remember which properties were informative
        for i, d in enumerate(discriminates):
            if d and i not in self.state["useful_props"]:
                self.state["useful_props"].append(i)

        cpu = round(time.monotonic() - t0, 4)
        return {"passing": passing, "cpu_s": cpu, "family_guess": self.predict_family(),
                "props_skipped": skipped, "props_active": len(active)}
