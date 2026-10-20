"""Concurrent writers must not clobber each other.

``scripts.common.atomic_write`` used a fixed ``path + ".tmp"`` name for
the temporary file.  Two builds writing the same target therefore wrote
to the SAME temporary file: one build's bytes could win the rename, and
a reader could observe the other build's content.  The rename itself is
atomic, so a reader never saw a partial file -- it saw the *wrong*
file's complete content.

Recorded in ``docs/failure-modes.md`` as #29 (``NEEDS-FIX``).
"""
import os
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.common import atomic_write  # noqa: E402


def test_atomic_write_uses_a_unique_temp_name(tmp_path):
    """The temp name must not be the fixed "path + .tmp"."""
    target = tmp_path / "out.bin"
    atomic_write(str(target), b"payload", mode="wb")
    assert target.read_bytes() == b"payload"
    # No leftover fixed-name temp file.
    assert not (tmp_path / "out.bin.tmp").exists()


def test_atomic_write_leaves_no_temp_files(tmp_path):
    target = tmp_path / "out.bin"
    atomic_write(str(target), b"payload", mode="wb")
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "out.bin"]
    assert not leftovers, "atomic_write left temp files behind: %r" % (leftovers,)


def test_concurrent_writers_do_not_clobber_each_other(tmp_path):
    """Two writers to the same target must not share a temp file."""
    target = str(tmp_path / "shared.bin")
    payload_a = b"A" * 200000
    payload_b = b"B" * 200000
    errors = []
    barrier = threading.Barrier(2)

    def _write(payload):
        barrier.wait()
        try:
            atomic_write(target, payload, mode="wb")
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=_write, args=(p,))
               for p in (payload_a, payload_b)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
        assert not t.is_alive(), "a writer hung"

    assert not errors, ("a concurrent writer failed: %r" % (errors,))
    final = open(target, "rb").read()
    # Whichever writer won the rename, the content must be ONE of the
    # two payloads, complete -- never a mix, never truncated.
    assert final in (payload_a, payload_b), (
        "the target holds a blend of two writers' content (%d bytes)"
        % len(final))


def test_atomic_write_cleans_up_on_failure(tmp_path):
    """A failed write must not leave a temp file behind."""
    target = tmp_path / "out.bin"
    target.write_bytes(b"original")
    try:
        atomic_write(str(target), object())     # not a str/bytes
    except Exception:
        pass
    assert target.read_bytes() == b"original"
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "out.bin"]
    assert not leftovers, "a failed write left temp files: %r" % (leftovers,)
