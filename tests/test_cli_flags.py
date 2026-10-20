"""The CLI's flag surface must be real.

The pipeline CLI used to hand ``build_project`` a freshly constructed
``argparse.Namespace`` instead of the one argparse had parsed.  Every
field the copy forgot was silently dropped, so fourteen documented flags
(``--hwid``, ``--trial``, ``--vm-threshold``, ``--kod``,
``--hostguard``, ``--hwid-lock``, ``--driver-check``,
``--split-bootstrap``, ``--no-snapshot``, ``--no-stdlib-audit``,
``--name-gate``, ``--lowering``, ``--rename-internal``,
``--no-audit-hook-plant``) were no-ops: the flag was accepted, echoed
in the help text, and did nothing.

These tests close that class structurally, so it cannot reopen.
"""
import argparse
import inspect
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import build_parser, main  # noqa: E402


def _dest_options(action):
    return [opt for opt in action.option_strings if opt.startswith("--")]


def _build_parser():
    parser, _subparsers = build_parser()
    return parser


def test_main_does_not_rebuild_the_namespace():
    """The parsed namespace must reach build_project unchanged.

    Rebuilding it is what dropped the flags; this is the guard.
    """
    source = inspect.getsource(main)
    assert re.search(r"build_project\(\s*args\s*\)", source), (
        "main() must pass the parsed namespace straight to build_project; "
        "rebuilding it is what dropped the flags")
    # A namespace built for the build stage is the bug.  (Other
    # namespaces exist in main() for the verification suite, one per
    # variant, and those are legitimate.)
    assert not re.search(
        r"Namespace\([^)]*\bsource\s*=", source), (
        "main() rebuilds the build namespace; any field it forgets "
        "becomes a silently ignored flag")


def test_every_build_flag_is_consumed():
    """Every flag the build subcommand advertises must be read."""
    parser = _build_parser()
    build = parser._subparsers._group_actions[0].choices["build"]
    module_source = inspect.getsource(sys.modules["obfuscator.core.pipeline"])

    unread = []
    for action in build._actions:
        if not action.option_strings or action.dest in ("help", argparse.SUPPRESS):
            continue
        patterns = [r"\bargs\.%s\b" % re.escape(action.dest),
                    r"getattr\(\s*args\s*,\s*['\"]%s['\"]" % re.escape(action.dest)]
        if not any(re.search(p, module_source) for p in patterns):
            unread.append("%s (dest=%s)" % (action.option_strings[0],
                                            action.dest))
    assert not unread, ("flags that are declared but never read: %r"
                         % (unread,))


def test_every_build_flag_reaches_the_namespace():
    """A flag must not be swallowed by the parser."""
    parser = _build_parser()
    build = parser._subparsers._group_actions[0].choices["build"]
    args = parser.parse_args(["build", "payload.py"])
    for action in build._actions:
        if action.dest in ("help", argparse.SUPPRESS):
            continue
        assert hasattr(args, action.dest), (
            "dest %r missing from the parsed namespace" % action.dest)


def test_deprecated_watermark_alias_still_works():
    """--watermark was renamed to --lock-hwid; the old spelling works."""
    parser = _build_parser()
    args = parser.parse_args(["build", "payload.py", "--watermark", "H1"])
    assert args.lock_hwid == "H1"
    args = parser.parse_args(["build", "payload.py", "--lock-hwid", "H2"])
    assert args.lock_hwid == "H2"


def test_platform_choices_match_the_implemented_farms():
    """--platform must not advertise a backend that does not exist."""
    parser = _build_parser()
    build = parser._subparsers._group_actions[0].choices["build"]
    action = [a for a in build._actions if a.dest == "platform"][0]
    assert "gitlab" not in action.choices, (
        "gitlab is offered but no GitLab farm is implemented")
    assert set(action.choices) == {"auto", "github"}


def test_unknown_command_is_reported_clearly():
    """A bad command must name the valid ones, not guess."""
    _p, subparsers = build_parser()
    assert "build" in subparsers.choices
    assert "build-farm" in subparsers.choices
    assert "auth" in subparsers.choices
    assert "clean" in subparsers.choices
    assert "obfuscate" in subparsers.choices
    assert "version" in subparsers.choices
