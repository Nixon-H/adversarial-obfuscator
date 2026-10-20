"""The single source of truth for the project's version.

The version used to live in three places that could disagree:
``obfuscator/core/pipeline.py`` (3.0.0), ``scripts/build.py`` (a
hard-coded "shadow-compiler 2.0.0" string) and ``config/default.json``
(2.0.0).  They are now one constant, read by all three.

``config/default.json`` still carries ``shadow_compiler.version``
because the config schema requires the key, but the value there is
checked against :data:`VERSION` by ``tests/test_version_consistency.py``.
"""
VERSION = "2.0.0"

#: The name the CLI reports.
PROGRAM_NAME = "shadow-compiler"


def version_string():
    """The version the CLI reports, e.g. ``"shadow-compiler 2.0.0"``."""
    return "%s %s" % (PROGRAM_NAME, VERSION)


__all__ = ["VERSION", "PROGRAM_NAME", "version_string"]
