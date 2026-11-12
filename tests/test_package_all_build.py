"""`scripts/build.py --package all` = "package with everything else".

The one-flag maximum: every packaging option (pytoc, pyinstaller, all
cross targets) plus every opt-in --transforms pass and fail-strict
validation.  Anti-REA is already at maximum by default and the six AST
transforms are on unless excluded, so nothing else is needed.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts import build as build_mod  # noqa: E402


class _Opts:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def _namespaced(**kw):
    base = dict(skip=None, exclude=None, audit=None, research=None,
                package=None, transforms=None, validate=None, access=None)
    base.update(kw)
    return build_mod._apply_build_namespaces(_Opts(**base))


def test_package_all_pulls_in_everything():
    opts = _namespaced(package=["all"])
    assert opts.pytoc is True
    assert opts.pyinstaller_spec is True
    assert opts.cross == "win,linux,macos,linux-arm"
    assert opts.data_obfuscation is True
    assert opts.function_intent is True
    assert opts.speculation_obfuscation is True
    assert opts.struct_randomization is True
    assert opts.validate is True
    assert opts.validate_fail is True


def test_package_everything_is_an_alias():
    opts = _namespaced(package=["everything"])
    assert opts.pytoc is True and opts.validate_fail is True


def test_package_all_does_not_override_an_explicit_validate():
    opts = _namespaced(package=["all"], validate=None)
    assert opts.validate is True and opts.validate_fail is True


def test_unknown_package_option_is_still_refused():
    with pytest.raises(SystemExit, match="unknown option"):
        _namespaced(package=["everything-else"])


def test_default_build_has_no_packaging_and_no_extra_transforms():
    opts = _namespaced()
    assert opts.pytoc is False
    assert opts.pyinstaller_spec is False
    assert opts.cross is None
    assert opts.data_obfuscation is False
    assert opts.function_intent is False
    assert opts.speculation_obfuscation is False
    assert opts.struct_randomization is False
    assert opts.validate is False and opts.validate_fail is False
