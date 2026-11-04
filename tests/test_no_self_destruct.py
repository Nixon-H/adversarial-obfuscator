"""The artefact must never delete itself.

The temporal-redundancy wrapper used to call a function three times and, if the
results differed, treat that as a hardware fault attack: `os.remove(sys.argv[0])`
then `sys.exit(666)`.

Both halves were wrong. Re-running an arbitrary callable re-runs its side
effects, so a counter closure (or anything non-deterministic) always produced
three different results, the self-destruct fired on a false positive, and the
operator's file was destroyed. The 0-byte artefact that remained then ran
silently on every later attempt -- the intermittent "exited 1, no output" that
cost several rounds of diagnosis.

Reproduced: four concurrent runs left the artefact at 0 bytes
(md5 d41d8cd98f00b204e9800998ecf8427e) and every subsequent run was silent.
"""
from obfuscator.core.sources import TRIPLE_REDUNDANCY_SOURCE as REDUNDANCY


def test_no_self_deletion_anywhere_in_the_wrapper():
    assert "os.remove" not in REDUNDANCY, (
        "the redundancy wrapper deletes the artefact again; a false positive "
        "destroys the operator's file and leaves a silent 0-byte artefact")
    assert "sys.argv[0]" not in REDUNDANCY, (
        "the wrapper still targets its own file")


def test_no_fault_self_destruct_exit():
    # Check for the CALL, not the digits: the explanatory comment legitimately
    # mentions the old exit code, and a guard that cannot tell code from prose
    # is the mistake this project has recorded before.
    assert "sys.exit(666)" not in REDUNDANCY.replace(" ", ""), (
        "the wrapper still exits on a redundancy mismatch")


def test_the_wrapped_callable_is_invoked_once():
    calls = REDUNDANCY.count("func(*args)")
    assert calls == 1, (
        "the wrapper calls the callable %d times; re-running user code re-runs "
        "its side effects" % calls)


def test_wrapper_still_returns_something():
    assert "return func(*args)" in REDUNDANCY
