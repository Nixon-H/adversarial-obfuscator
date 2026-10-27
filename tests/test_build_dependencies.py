"""Dependency validation must not require tools the build will not use.

`validate_dependencies()` ran before argparse and demanded llc
unconditionally, so `--skip-llvmgen` failed on a machine without LLVM --
and `--help` did too. That is what broke the security-artifact CI job:
it builds with `--skip-irgen --skip-llvmgen --skip-encrypt --skip-relay
--skip-extras` and got "ERROR: Missing dependency: llc".
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts import build as build_mod  # noqa: E402


class _Opts:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def _capture_checks(monkeypatch):
    checked = []

    def fake_check_exe(name, hint=""):
        checked.append(name)
        return True

    monkeypatch.setattr(build_mod, "_check_exe", fake_check_exe)
    return checked


class TestDependencyValidation:
    def test_skip_llvmgen_does_not_require_llc(self, monkeypatch):
        checked = _capture_checks(monkeypatch)
        ok = build_mod.validate_dependencies(_Opts(skip_llvmgen=True))
        assert ok is True
        assert "llc" not in checked, \
            "llc was required even though the LLVM stage is skipped"

    def test_without_the_skip_llc_is_required(self, monkeypatch):
        checked = _capture_checks(monkeypatch)
        build_mod.validate_dependencies(_Opts(skip_llvmgen=False))
        assert "llc" in checked

    def test_default_opts_requires_llc(self, monkeypatch):
        """No opts at all (the old call shape) must still check llc."""
        checked = _capture_checks(monkeypatch)
        build_mod.validate_dependencies()
        assert "llc" in checked

    def test_help_does_not_validate_dependencies(self):
        """--help must work on a box with no toolchain: the check now runs
        after argparse."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/build.py", "--help"],
            capture_output=True, text=True, timeout=60,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
        )
        assert result.returncode == 0, result.stderr[-800:]
        assert "usage:" in result.stdout.lower()


class TestLoaderOnlyFlags:
    """Flags this pipeline cannot honour must be refused, not ignored.

    --customer-salt binds the payload key to a customer in the HYBRID
    LOADER path (`python3 -m obfuscator.core.pipeline build`). The
    scripts/build.py pipeline emits no hybrid loader, so accepting the
    flag there and doing nothing would leave an operator believing the
    build was customer-bound when it was not.
    """

    def test_customer_salt_is_refused_here(self):
        import subprocess
        root = os.path.join(os.path.dirname(__file__), "..")
        result = subprocess.run(
            [sys.executable, "scripts/build.py", "--payload",
             os.path.join(root, "tests", "fixtures", "test_payload.py"),
             "--customer-salt", "acme"],
            capture_output=True, text=True, timeout=120, cwd=root,
        )
        # The exact code is the refusal path's business (2 locally, 1 when
        # UI.fatal is the one that exits); what must hold is that the build
        # does not silently proceed.  The message is the real assertion.
        assert result.returncode != 0, (
            "expected the loader-only refusal, got 0\n%s"
            % (result.stderr[-500:],)
        )
        assert "--customer-salt" in result.stderr or "--customer-salt" in result.stdout
        assert "pipeline build" in result.stderr or "pipeline build" in result.stdout
