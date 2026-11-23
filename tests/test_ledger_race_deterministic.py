"""Deterministic regression test for AI-PROTO-007 (ledger check-and-record race).

The register originally recorded no test for this finding, on the argument that
a race is timing-dependent and a passing test would prove scheduler luck. That
argument was half right: relying on natural timing IS flaky. But the interleaving
itself can be forced, and once forced the test is entirely deterministic.

How the interleaving is forced, without patching the code under test:

  * ``ReplayLedger._load`` and ``ReplayLedger._store`` are wrapped on the
    INSTANCE with functions that rendezvous on a ``multiprocessing.Barrier``.
  * ``_load`` is the READ half of check-and-record, ``_store`` is the WRITE
    half. Making every reader wait until all workers have read, and only then
    letting any writer proceed, reproduces exactly the window the defect is
    about: all N processes observe the identity absent, then all N write.
  * Nothing about the ledger's own logic is altered -- the wrappers only add a
    barrier around the real methods, so the test would still fail if the
    implementation were correct (a correct implementation using O_EXCL or a
    lock would never let all N reach the write with a stale read).

This is a strict-xfail test: the defect is open, so it fails today, and the
strict marker demands the marker be removed when a real atomic primitive lands.

Finding: docs/security/REVIEW_FINDINGS_FILED.md — AI-PROTO-007.
"""
import multiprocessing as mp
import sys

import pytest

sys.path.insert(0, __file__.rsplit("/tests/", 1)[0])

WORKERS = 6


def _worker(ledger_path, barrier, results, ok_flag):
    """One presentation, with reads and writes forced to interleave."""
    from obfuscator.licence_replay import ReplayLedger

    ledger = ReplayLedger(path=ledger_path, window_s=300)
    real_load = ledger._load
    real_store = ledger._store

    def load():
        data = real_load()
        # Every worker reaches this point before ANY worker writes.
        try:
            barrier.wait(timeout=20)
        except Exception:                       # noqa: BLE001
            ok_flag.value = 0
        return data

    def store(data):
        return real_store(data)

    ledger._load = load
    ledger._store = store
    try:
        results.put(bool(ledger.check_and_record("race-identity")))
    except Exception:                           # noqa: BLE001
        results.put(False)


@pytest.mark.xfail(
    strict=True,
    reason="AI-PROTO-007 open: check_and_record is load-modify-store with no "
           "lock, so the interleaving where every presenter reads before any "
           "writes yields N acceptances instead of 1")
def test_concurrent_presentations_accept_exactly_once(tmp_path):
    ledger_path = str(tmp_path / "seen.json")
    ctx = mp.get_context("fork") if hasattr(mp, "get_context") else mp
    barrier = ctx.Barrier(WORKERS)
    results = ctx.Queue()
    ok_flag = ctx.Value("i", 1)

    procs = [ctx.Process(target=_worker,
                         args=(ledger_path, barrier, results, ok_flag))
             for _ in range(WORKERS)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(40)
    assert ok_flag.value == 1, (
        "the barrier never released -- the interleaving was not forced, so this "
        "run proves nothing and must not be read as a pass")

    outcomes = [results.get(timeout=5) for _ in range(WORKERS)]
    accepted = sum(1 for o in outcomes if o)

    assert accepted == 1, (
        "check_and_record accepted the same token %d times out of %d when every "
        "presenter read before any wrote; replay protection does not hold under "
        "concurrency. Outcomes: %r" % (accepted, WORKERS, outcomes))
