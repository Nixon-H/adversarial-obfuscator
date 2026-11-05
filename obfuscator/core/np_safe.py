"""Import numpy only where it is safe to import.

On Windows with CPython 3.14 numpy faults NATIVELY while importing
(ACCESS_VIOLATION, 0xC0000005) and prints "CRASHES ARE TO BE EXPECTED". A native
crash is not an ImportError, so `try: import numpy / except ImportError` does not
protect anything -- the process is gone before the except runs.

Four modules import numpy at module scope, which means merely importing them
killed the builder on that pairing. Those modules now import `np` from here.

Where numpy is unavailable, this returns a stub whose attribute access raises a
clear error. Importing the module still succeeds, so every non-numpy code path
keeps working; only code that actually reaches for numpy fails, and it says why.
"""
import platform
import sys


class _Unavailable:
    """Stands in for numpy where importing it would crash the interpreter."""

    def __init__(self, reason):
        self._reason = reason

    def __getattr__(self, name):
        raise RuntimeError(
            "numpy is unavailable here (%s). Code that needs it cannot run on "
            "this platform, but importing the module is safe." % self._reason)

    def __bool__(self):
        return False


def load():
    """Return the numpy module, or a stub explaining why it is unavailable."""
    if platform.system() == "Windows" and sys.version_info[:2] >= (3, 14):
        return _Unavailable(
            "CPython %d.%d on Windows faults natively inside numpy"
            % sys.version_info[:2])
    try:
        import numpy as _np
        return _np
    except Exception as exc:            # ImportError, OSError, anything catchable
        return _Unavailable(str(exc))


np = load()
HAS_NUMPY = not isinstance(np, _Unavailable)
