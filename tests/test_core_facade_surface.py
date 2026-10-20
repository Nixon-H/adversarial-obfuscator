"""The package facade must expose exactly what it used to.

``obfuscator/core/__init__.py`` used to be four star imports.  It now
spells out 297 names, and F403/F405 are enforced because of it.  The
risk in that change is the compatibility surface: a name that used to
resolve to one object now resolving to another, or disappearing.

This test compares the facade against the surface the star imports
produced -- the four modules, in order, with the later ones shadowing
the earlier ones -- and asserts the facade matches it name for name
and object for object.

Names bound only inside a ``try: ... except ImportError`` are
conditional and are NOT part of the surface: ``np`` exists in
``utils`` only when numpy is installed, and re-exporting it
unconditionally would make the package unimportable without numpy.
That is not a theoretical concern -- it broke the 3.10, 3.11, 3.12 and
3.14 builds until it was found.
"""
import importlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import obfuscator.core as facade  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "scripts", "lint"))
import generate_core_facade as generator  # noqa: E402

#: The order the star imports ran in.  Later modules shadow earlier
#: ones, so this order defines the surface.
ORDER = ("utils", "transforms", "sources", "pipeline")


def _star_import_surface():
    """What `from .mod import *` produced, reconstructed."""
    namespace = {}
    for name in ORDER:
        module = importlib.import_module("obfuscator.core.%s" % name)
        exported = generator.public_names(module.__file__)
        for attr in exported:
            namespace[attr] = getattr(module, attr)
    return namespace


def test_the_facade_exposes_the_same_names():
    expected = set(_star_import_surface())
    actual = set(facade.__all__)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    assert not missing, "the facade dropped these names: %r" % (missing,)
    assert not extra, "the facade added these names: %r" % (extra,)


def test_the_facade_resolves_each_name_to_the_same_object():
    """A rename must not silently change what a name refers to."""
    expected = _star_import_surface()
    mismatched = []
    for name, value in sorted(expected.items()):
        if not hasattr(facade, name):
            mismatched.append("%s: missing" % name)
            continue
        if getattr(facade, name) is not value:
            mismatched.append("%s: different object" % name)
    assert not mismatched, (
        "the facade no longer matches the star-import surface: %r"
        % (mismatched,))


def test_the_submodules_are_still_reachable():
    for name in ORDER:
        assert hasattr(facade, name), (
            "obfuscator.core.%s must stay importable as an attribute" % name)


def test_no_star_imports_remain_in_the_core_package():
    """F403/F405 are enforced, so a star import would fail the gate.

    This is the direct guard for the conversion: the lint gate catches
    the class, and this test says what the class is.
    """
    import ast
    core = os.path.join(ROOT, "obfuscator", "core")
    offenders = []
    for fn in sorted(os.listdir(core)):
        if not fn.endswith(".py"):
            continue
        path = os.path.join(core, fn)
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and any(
                    n == "*" for n in node.names):
                offenders.append("%s:%d" % (fn, node.lineno))
    assert not offenders, ("star imports remain in the core package: %r"
                           % (offenders,))


def test_the_facade_file_is_generated_and_up_to_date():
    """The facade is generated; a hand edit would be lost."""
    proc = subprocess.run(
        [sys.executable,
         os.path.join(ROOT, "scripts", "lint", "generate_core_facade.py"),
         "--check"],
        capture_output=True, text=True, timeout=300, cwd=ROOT)
    assert proc.returncode == 0, (
        "obfuscator/core/__init__.py is out of date:\n%s%s"
        % (proc.stdout, proc.stderr))


def test_the_package_imports_without_numpy():
    """numpy is optional; the package must not need it.

    ``utils`` binds ``np`` only when numpy is installed.  Re-exporting
    that name made the whole package unimportable on an interpreter
    without numpy -- which broke the 3.10, 3.11, 3.12 and 3.14 builds
    until it was found.
    """
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.modules['numpy'] = None; "
         "import obfuscator.core, obfuscator.core.pipeline; "
         "print('OK')"],
        capture_output=True, text=True, timeout=300, cwd=ROOT,
        env=dict(os.environ, NIXON_LOG_REDIRECT="0",
                 PYTHONPATH=ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")))
    assert proc.returncode == 0, (
        "the package does not import without numpy:\n%s%s"
        % (proc.stdout[-2000:], proc.stderr[-2000:]))
