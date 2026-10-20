"""Optional import of the z3 SMT solver.

z3 is needed only by the proof / verification paths.  It used to be a
hard module-level import in every module that touches it, which made
the WHOLE build CLI unimportable without it: a proof-only dependency
load-bearing for every build.

The pattern here is a lazy stand-in.  When z3 is installed it is the
real module.  When it is not, the stand-in raises a clear RuntimeError
the moment anything actually uses it, so the build works and the proof
path fails with a message that says what to install.

Usage::

    from scripts.z3_optional import z3

    def prove_something():
        solver = z3.Solver()      # raises a clear error if z3 is absent
"""
try:
    import z3
except ImportError:  # pragma: no cover - exercised by the absence test
    class _MissingZ3:
        """Stand-in for z3 when the optional dependency is absent."""

        def __getattr__(self, name):
            raise RuntimeError(
                "z3-solver is required for the SMT proof paths. "
                "Install it with: pip install z3-solver")

        def __bool__(self):
            return False

    z3 = _MissingZ3()

__all__ = ["z3"]
