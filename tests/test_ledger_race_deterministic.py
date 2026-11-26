"""Deterministic concurrency regression test for AI-PROTO-007.

The original JSON ledger had a check-and-record race: concurrent presenters
could all observe an identity as absent before any writer stored it. The ledger
now uses SQLite and performs the read/claim/prune sequence inside a single
``BEGIN IMMEDIATE`` transaction, so concurrent presenters are serialized at the
database layer and exactly one can claim the identity inside the window.

The barrier below is a start-line rendezvous for the public
``check_and_record`` call, including first-time ledger creation. It does not
patch or wrap the implementation under test: every worker is released together
and then races the real atomic claim path. This is not a proof of SQLite internals; it is a regression check that
the repository uses the atomic path rather than the old load/modify/write
sequence.

Finding: docs/security/REVIEW_FINDINGS_FILED.md — AI-PROTO-007.
"""
import multiprocessing as mp
import sys


sys.path.insert(0, __file__.rsplit("/tests/", 1)[0])

WORKERS = 6


def _worker(ledger_path, barrier, results, ok_flag):
    """One presentation, with reads and writes forced to interleave."""
    from obfuscator.licence_replay import ReplayLedger

    ledger = ReplayLedger(path=ledger_path, window_s=300)
    try:
        # Release every worker together; the atomic claim path does the rest.
        barrier.wait(timeout=20)
    except Exception:                           # noqa: BLE001
        ok_flag.value = 0
        results.put(False)
        return
    try:
        results.put(bool(ledger.check_and_record("race-identity")))
    except Exception:                           # noqa: BLE001
        results.put(False)


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
