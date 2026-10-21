"""process_ctx.py

Purpose:
    The multiprocessing context the distributed package spawns workers
    with.

Architectural Role:
    A module of its own, so that the worker modules can import it
    without importing the package (which imports them).

Security Relevance:
    "spawn", not the platform default: forking a multi-threaded
    process is deprecated (Python 3.12+ warns) and may deadlock in the
    child, and Python 3.14 changes the default on Linux.  "spawn" also
    gives the worker a clean interpreter, so it inherits none of this
    process's state -- the workers here communicate through shared
    memory and queues, not through inherited globals.
"""

from __future__ import annotations

import multiprocessing


def process_context():
    """The context to spawn workers with (see the module docstring)."""
    return multiprocessing.get_context("spawn")
