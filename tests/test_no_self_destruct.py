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


def test_the_redundancy_wrapper_is_not_wired_into_any_artefact():
    """Documents a fact that was misread as a security regression.

    An audit of this project once ranked "removal of the redundancy
    self-destruct" as the most severe change of a session. It was not: the class
    is injected into every artefact and `execute_redundant` has no call sites --
    before that change or after it. The three-call comparison never ran, so the
    self-destruct never fired, in either mode.

    This test fails if someone wires it up, which is the moment the self-destruct
    becomes reachable and must be reconsidered (re-running arbitrary user code is
    unsound; a closure always produces three different results).
    """
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    callers = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "archive", "__pycache__"}]
        for name in filenames:
            if not name.endswith(".py") or name.startswith("test_"):
                continue
            path = os.path.join(dirpath, name)
            try:
                text = open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for line in text.splitlines():
                stripped = line.strip()
                if "execute_redundant" in stripped and not stripped.startswith("def "):
                    callers.append((os.path.relpath(path, root), stripped[:80]))
    assert not callers, (
        "execute_redundant is now invoked; the self-destruct is reachable and "
        "must be re-evaluated before shipping: %r" % (callers[:3],))
