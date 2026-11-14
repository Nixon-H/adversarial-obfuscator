"""The artefact must never destroy itself unless the operator asked for it.

The temporal-redundancy wrapper originally called a function three times and, if
the results differed, treated it as a hardware fault attack: delete the artefact
and exit 666.

Both halves were unsafe as a DEFAULT. Re-running an arbitrary callable re-runs
its side effects, so a counter closure always produced three different results,
the self-destruct fired on a false positive, and the operator's file was
destroyed -- leaving a 0-byte artefact that ran silently forever after
(reproduced: four concurrent runs left the file empty).

The protection is real, so it was not deleted: --strict-detections restores the
three-call comparison and the self-destruct. These tests pin both halves.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from obfuscator.core.sources import TRIPLE_REDUNDANCY_SOURCE as REDUNDANCY


def _default_branch():
    """The code that runs when strict detections are off."""
    start = REDUNDANCY.index("if not {VAR_STRICT_DETECTIONS}:")
    return REDUNDANCY[start:REDUNDANCY.index("return func(*args)", start) + len("return func(*args)")]


def _strict_branch():
    start = REDUNDANCY.index("# --strict-detections")
    return REDUNDANCY[start:]


def test_default_path_calls_the_callable_once():
    branch = _default_branch()
    assert branch.count("func(*args)") == 1, (
        "the default path must call user code exactly once: re-running it "
        "re-runs its side effects and makes the fault check fire falsely")


def test_default_path_does_not_delete_anything():
    assert "os.remove" not in _default_branch()
    assert "sys.argv[0]" not in _default_branch()


def test_strict_mode_restores_the_redundancy_check():
    branch = _strict_branch()
    assert branch.count("func(*args)") == 3, (
        "--strict-detections must compare three independent calls")
    assert "__r1 == __r2 == __r3" in branch, "the three results must be compared"


def test_strict_mode_restores_the_fault_response():
    branch = _strict_branch()
    assert "__ro.remove(__rs.argv[0])" in branch, (
        "--strict-detections must still delete the artefact on a fault")
    assert "__rs.exit(666)" in branch


def test_the_destructive_path_is_reachable_only_in_strict_mode():
    # The guard must come BEFORE the destructive code in the source, so that
    # an operator who did not opt in can never reach it.
    guard = REDUNDANCY.index("if not {VAR_STRICT_DETECTIONS}:")
    destructive = REDUNDANCY.index("__ro.remove")
    assert guard < destructive, "the strict guard must precede the self-destruct"


def test_the_redundancy_wrapper_is_wired_only_for_pure_functions():
    """The wrapper is live now -- but only where re-invocation is sound.

    It previously had no call sites at all, because re-running arbitrary user code
    re-runs its side effects: a counter closure always returns three different
    values, so the check fired on correct code and the self-destruct destroyed the
    artefact. The fix is not to remove the check but to apply it only to functions
    that cannot have side effects.
    """
    from obfuscator.core.sources import apply_ast_mutation
    from obfuscator.core.transforms import is_pure_function
    import ast

    # Parameterless: a parameter could be an iterator the first call consumes,
    # which is how `all_equal(iterable)` destroyed a correct artefact.
    pure = "def total():\n    x = 2\n    return x + 3\nprint(total())\n"
    impure = ("def bump(c):\n    c.append(1)\n    return len(c)\n"
              "print(bump([1]))\n")

    out, _ = apply_ast_mutation(pure, {"opt_level": 0, "temporal_redundancy": True})
    assert "total_impl" in out, "a pure function must be wrapped"

    out2, _ = apply_ast_mutation(impure, {"opt_level": 0, "temporal_redundancy": True})
    assert "bump_impl" not in out2, (
        "an impure function must NOT be wrapped: re-invoking it re-runs its side "
        "effects, which is what made the self-destruct fire on correct code")

    # The purity test itself, directly.
    assert is_pure_function(ast.parse(pure).body[0]) is True
    assert is_pure_function(ast.parse(impure).body[0]) is False


def test_the_wrapper_reaches_the_full_pipeline_output():
    """End to end, not just the mutation step.

    An earlier attempt to verify this grepped a BUILT ARTEFACT for the wrapper
    and found none -- but the payload is packed inside the artefact, so its text
    is not greppable at all. The wrapper was there the whole time. This test
    looks at the assembler's output, which is where the payload still exists as
    source.
    """
    import re
    from obfuscator.core.pipeline import build_pipeline

    src = ("def total():\n"
           "    x = 2\n"
           "    return x + 3\n"
           "RESULT = total()\n")
    out = build_pipeline(src, extra_options={"opt_level": 0})

    # The checksum guard is injected as the first statement of every
    # module-level function, so it sits between the signature and the
    # first assignment.  Its presence is not what this test is about.
    wrappers = re.findall(
        r"\*args, \*\*kwargs\):\s*\n(?:\s*_nx_verify\(\)\s*\n)?\s*\S+ = ", out)
    assert wrappers, (
        "no purity-gated redundancy wrapper in the assembled payload; the "
        "protection would be dead code again")
    # And the destructive response is reachable from it.
    assert "argv[0]" in out, "the wrapper has no fault response"


def test_a_pure_function_returning_nan_does_not_self_destruct():
    """NaN != NaN, so a naive equality check would look like tampering.

    A pure function may legitimately return nan. Comparing the three results with
    == alone would report three different values, and the fault response would
    destroy the artefact on completely correct code -- exactly the class of false
    positive that made this protection unusable before.
    """
    import ast
    from obfuscator.core.transforms import TemporalRedundancyWrapper

    src = 'def f():\n    return float("nan")\nRESULT = f()\n'
    tree = TemporalRedundancyWrapper().visit(ast.parse(src))
    ns = {"float": float}
    exec(compile(ast.unparse(tree), "<nan-test>", "exec"), ns)  # SystemExit 666 if wrong
    value = ns["RESULT"]
    assert value != value, "the payload should have returned nan"


def test_an_inconclusive_comparison_never_destroys_the_artefact():
    """Inconclusive is not tampering.

    If comparing the three results raises -- an exotic __eq__, an array-like
    result whose truth value is ambiguous, a repr that fails -- the artefact must
    return the value it would have returned without the check, not destroy
    itself. A protection that kills correct code is a hazard, not a protection.
    """
    import ast
    from obfuscator.core.transforms import TemporalRedundancyWrapper

    src = (
        "class Bad:\n"
        "    def __eq__(self, other):\n"
        "        raise RuntimeError('cannot compare')\n"
        "def f():\n"
        "    return Bad()\n"
        "RESULT = f()\n"
    )
    tree = TemporalRedundancyWrapper().visit(ast.parse(src))
    ns = {}
    exec(compile(ast.unparse(tree), "<inconclusive-test>", "exec"), ns)
    assert type(ns["RESULT"]).__name__ == "Bad"
