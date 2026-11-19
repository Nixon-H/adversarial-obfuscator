"""§6 adversarial solver validation — the review's actual bar.

The review is blunt about the standard:

    "I would not count a transform as a successful security mechanism until it
     survives automated simplification and adversarial recovery attempts."

    "NP-hardness of a general problem does not automatically make an individual
     generated instance difficult."

This module is the adversarial side of that: it takes the instances the C
transform actually emits and tries to crush them with the tools an analyst has.
It is deliberately NOT part of the emitter — a transform that grades itself is
the self-judging failure §10 names.

Three claims are under test, exactly as the review lists them:

  1. the fixed-even opaque predicate   -> `probe_opaque_predicate`
  2. subset-sum with a 4096-entry DP   -> `probe_subset_sum`
  3. multi-round MBA "exponential"     -> `probe_mba`

Each probe returns a MEASURED result with a verdict, and the verdict is allowed
to be "this claim does not hold". That is the point: a benchmark that can only
report success is not a benchmark.
"""
from __future__ import annotations

import itertools
import random
import statistics
import time

#: The bar the review sets. A transform that an automated solver dispatches in
#: under this budget is not a security mechanism, whatever it costs in bytes.
CHEAP_SECONDS = 1.0

#: A fixed-even predicate written the way the C transform emits them: true for
#: every input, but not obviously so. The audit compiles this and counts the
#: conditional branches that survive -O3. It lives here rather than in a script
#: so the fixture and the probe cannot drift apart.
#:
#: ``%%`` and ``\\n`` are escaped because the text is %-formatted at use.
FOLD_PROBE_SOURCE = """\
#include <stdio.h>
int main(void) {
    volatile int sink = 0;
    for (int x = 0; x < 4; x++) {
        if (((x * x - x) %% 2) == 0) { sink += 1; }
    }
    printf("%%d\\n", sink);
    return 0;
}
"""


def sample_mba_expressions(value=12345, rounds_list=(1, 3, 5),
                           seed=b"nx-mba-adversarial"):
    """MBA expressions as the transform emits them, at growing depth.

    The emitter is imported lazily so this module carries no build dependency
    at import time. The RNG is a DETERMINISTIC TEST FIXTURE: the same seed must
    produce the same expression, or the audit's numbers would move between runs
    for reasons unrelated to the transform. It generates no key and no nonce.
    """
    import random as _fixture

    from scripts.c_transform import _mba_substitute_constant
    out = []
    for rounds in rounds_list:
        fixture = _fixture.Random(int.from_bytes(bytes(seed), "big") ^ rounds)
        out.append(_mba_substitute_constant(value, fixture, rounds=rounds))
    return out



def _solve_seconds(fn, repeats=5):
    """Fastest wall-clock over a few runs, in seconds.

    Fastest, not mean: a solver's cost is the cost of the run that succeeded,
    and a reader wants the number an attacker would actually experience. Timing
    noise only ever makes a solver look SLOWER, so taking the minimum is the
    conservative choice against our own claim.
    """
    best = None
    for _ in range(max(1, repeats)):
        started = time.perf_counter()
        fn()
        elapsed = time.perf_counter() - started
        best = elapsed if best is None else min(best, elapsed)
    return best


def _verdict(seconds):
    """Map a measured solve time onto the review's acceptance bar."""
    if seconds <= CHEAP_SECONDS:
        return "NOT A PROTECTION: solved automatically in under %.1fs" % (
            CHEAP_SECONDS,)
    return "costs the analyst more than %.1fs" % (CHEAP_SECONDS,)


# ── claim 2: subset-sum with a 4096-entry DP table ────────────────────────

def probe_subset_sum(instances, limit=None):
    """How hard is a GENERATED instance to solve, measured, not inferred?

    The review's argument: the 4096-entry DP table describes the run-time
    verifier, not the attack. An analyst is not obliged to reproduce the DP —
    they can enumerate subsets, use a meet-in-the-middle split, or just read the
    constants and check which subset hits the target.

    Measured here: exhaustive subset enumeration, which is what a human or a
    small script does first. The number that matters is the SEARCH SPACE
    (2**n), because that is what sets the cost of every method above.
    """
    rows = []
    for index, instance in enumerate(instances):
        if limit is not None and index >= limit:
            break
        values = list(instance["set"])
        target = int(instance["target"])
        width = len(values)
        space = 2 ** width

        def _brute(values=values, target=target):
            # Enumerate by increasing cardinality: an analyst wants a solution,
            # not all of them, so stopping at the first hit is realistic.
            for size in range(len(values) + 1):
                for combo in itertools.combinations(range(len(values)), size):
                    if sum(values[i] for i in combo) == target:
                        return combo
            return None

        solution = _brute()
        seconds = _solve_seconds(_brute)
        rows.append({
            "n": width,
            "search_space": space,
            "target": target,
            "solved": solution is not None,
            "solve_seconds": round(seconds, 6),
            "dp_table_entries": max(4096, target + 1),
        })

    if not rows:
        return {"probe": "subset_sum", "applicable": True, "measured": False,
                "reason": "no instances supplied"}
    spaces = {row["search_space"] for row in rows}
    worst = max(row["solve_seconds"] for row in rows)
    return {
        "probe": "subset_sum",
        "applicable": True,
        "measured": True,
        "instances": len(rows),
        "n": rows[0]["n"],
        # The single number that decides the claim: 2**n is the whole story.
        "search_space": sorted(spaces)[-1] if len(spaces) > 1 else spaces.pop(),
        "solve_seconds_max": worst,
        "solve_seconds_median": round(
            statistics.median([r["solve_seconds"] for r in rows]), 6),
        "all_solved": all(row["solved"] for row in rows),
        "dp_table_entries": rows[0]["dp_table_entries"],
        "verdict": _verdict(worst),
        "note": ("The DP table sizes the RUN-TIME check. It does not size the "
                 "attack: the instance is 2**n subsets, and the table adds "
                 "nothing an enumerator must pay."),
        "sample": rows[0],
    }


# ── claim 3: multi-round MBA described as exponential ─────────────────────

def probe_mba(expressions, expected_value, simplifier=None):
    """Can an automated simplifier recover the constant, and how fast?

    The review: "MBA expressions can often be simplified using algebraic
    solvers, symbolic execution and bit-vector reasoning." If a symbolic
    simplifier reproduces the literal in milliseconds, the transform cost the
    attacker nothing — the added bytes are decoration.

    ``simplifier`` is injected so the probe stays pure and testable: it maps
    expression text to (recovered_value, seconds). Production callers pass the
    sympy-backed simplifier in `scripts/adversarial_transforms.py`.
    """
    rows = []
    for expression in expressions:
        if simplifier is None:
            rows.append({"expression_length": len(expression),
                         "measured": False,
                         "reason": "no simplifier supplied"})
            continue
        recovered, seconds = simplifier(expression)
        rows.append({
            "expression_length": len(expression),
            "recovered": recovered,
            "expected": expected_value,
            "correct": recovered == expected_value,
            "simplify_seconds": round(seconds, 6),
            "measured": True,
        })
    measured = [row for row in rows if row.get("measured")]
    if not measured:
        return {"probe": "mba", "applicable": True, "measured": False,
                "reason": "no simplifier supplied", "rows": rows}
    worst = max(row["simplify_seconds"] for row in measured)
    recovered_all = all(row["correct"] for row in measured)
    return {
        "probe": "mba",
        "applicable": True,
        "measured": True,
        "expressions": len(measured),
        "max_length": max(row["expression_length"] for row in measured),
        # The finding: if a symbolic solver gets the constant back, the
        # expression protected nothing. Recorded as a fact, not a claim.
        "constant_recovered": recovered_all,
        "simplify_seconds_max": round(worst, 6),
        "verdict": (("WHOLLY INEFFECTIVE: constant recovered automatically in "
                     "%.3fs" % worst) if recovered_all else _verdict(worst)),
        "note": ("volatile slots stop the C COMPILER folding the expression; "
                 "they do not stop a reader or a symbolic solver, which see "
                 "the same arithmetic. Length is not difficulty."),
        "rows": rows,
    }


# ── claim 1: the opaque predicate under constant folding ──────────────────

def count_main_branches(disassembly):
    """Conditional branches inside ``main`` of an objdump listing.

    The mnemonic is matched in the middle of the line, not at the start:
    ``objdump -d`` puts an address and a hex column before it, so a
    ``line.startswith("j")`` test returns 0 for every function and would make
    the compiler probe report "folded" for everything. That bug was caught by
    running it — -O0 and -O3 both read as 0 branches.
    """
    import re as _re

    body = disassembly.split("<main>:", 1)[-1]
    pattern = _re.compile(r"\t(j[a-z]+|cmov[a-z]*)\s")
    return sum(1 for line in body.splitlines() if pattern.search(line))


def evaluate_integer_expression(expression):
    """Evaluate an MBA expression of CONSTANTS, without ``eval``.

    The emitted text is arithmetic over integer literals and parentheses only
    (the emitter guarantees "pure constants, no C identifiers"), so a tiny AST
    walk covers the whole grammar it can produce. This exists because the
    obvious implementation is ``eval``, and running the scanner taught us that
    is a code-execution sink regardless of what the caller believes about the
    input — the audit should not need an exemption to be written.

    Raises ``ValueError`` for anything outside the allowed node set, so an
    expression that ever gained a name or a call fails loudly instead of being
    silently evaluated.
    """
    import ast

    _BINOPS = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.BitXor: lambda a, b: a ^ b,
        ast.BitAnd: lambda a, b: a & b,
        ast.BitOr: lambda a, b: a | b,
        ast.FloorDiv: lambda a, b: a // b,
    }
    _UNARY = {ast.USub: lambda a: -a, ast.UAdd: lambda a: a}

    def _walk(node):
        if isinstance(node, ast.Expression):
            return _walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            return _BINOPS[type(node.op)](_walk(node.left), _walk(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](_walk(node.operand))
        raise ValueError("disallowed node %s in %r"
                         % (type(node).__name__, expression[:60]))

    return _walk(ast.parse(str(expression), mode="eval"))


def probe_opaque_predicate(compiler, expressions, build_dir=None):
    """Does the predicate survive `-O3`, measured on real emitted code?

    ``compiler`` is a callable ``(source_text) -> (kept: bool, detail: str)``
    supplied by the caller, so this probe stays pure. The production wiring
    compiles with gcc and counts `count_main_branches` at -O0 and -O3.
    """
    rows = []
    for expression in expressions:
        kept, detail = compiler(expression)
        rows.append({"expression": expression, "survived": kept,
                     "detail": str(detail)[:200]})
    if not rows:
        return {"probe": "opaque_predicate", "measured": False,
                "reason": "no expressions supplied"}
    survived = sum(1 for row in rows if row["survived"])
    return {
        "probe": "opaque_predicate",
        "applicable": True,
        "measured": True,
        "expressions": len(rows),
        "survived": survived,
        "folded": len(rows) - survived,
        "verdict": ("survived %d/%d at -O3" % (survived, len(rows))
                    if survived == len(rows) else
                    "FOLDED AWAY: %d/%d predicates removed by the compiler"
                    % (len(rows) - survived, len(rows))),
        "rows": rows,
    }


# ── the summary the report quotes ─────────────────────────────────────────

def summarise(results):
    """One block stating, per claim, whether it survived the review's bar.

    A claim is only "holds" when it was MEASURED and the measurement supports
    it. Anything unmeasured is reported as unmeasured rather than counted as a
    pass — the same rule the rest of the harness follows.
    """
    lines = []
    for result in results:
        name = result.get("probe", "?")
        if not result.get("measured"):
            lines.append((name, "UNMEASURED", result.get("reason", "")))
            continue
        verdict = result.get("verdict", "")
        if name == "subset_sum":
            holds = result.get("solve_seconds_max", 0) > CHEAP_SECONDS
        elif name == "mba":
            holds = not result.get("constant_recovered", False)
        elif name == "opaque_predicate":
            holds = result.get("folded", 1) == 0
        else:
            holds = False
        lines.append((name, "HOLDS" if holds else "DOES NOT HOLD", verdict))
    return {"claims": [{"claim": c, "status": s, "evidence": e}
                       for c, s, e in lines],
            "holds": sum(1 for _c, s, _e in lines if s == "HOLDS"),
            "total": len(lines)}
