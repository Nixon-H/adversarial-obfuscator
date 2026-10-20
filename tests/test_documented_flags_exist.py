"""Every flag the docs tell a user to run must exist.

A flag that is documented but does not exist is worse than one that is
not documented: the user types it, gets "unrecognized arguments", and
has no reason to suspect the documentation.  That is exactly the class
of defect this repository's audits have been finding -- flags that are
accepted and do nothing, and flags that are documented and do not
exist at all.

This test collects the long flags the CLIs actually accept and checks
the user-facing documentation against them.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from obfuscator.core.pipeline import build_parser as pipeline_parser  # noqa: E402

#: The documents that tell a USER what to type.  The audit reports are
#: dated snapshots and legitimately mention flags that have since been
#: removed, so they are checked separately (they carry RESOLVED notes).
USER_DOCS = ("README.md", "docs/USER_GUIDE.md", "docs/DEVELOPER.md",
             "docs/CHANGELOG.md", "SECURITY.md", "THREAT_MODEL.md",
             "docs/PLATFORMS.md")

#: Flags that belong to OTHER tools and are quoted in the docs.  They
#: are not project flags and must not be checked against ours.
FOREIGN_FLAGS = frozenset({
    # ruff
    "--fix", "--no-cache", "--select", "--ignore-glob", "--include",
    "--target-version",
    # pip
    "--require-hashes",
    # cargo
    "--target",
    # the repo's own tooling (scripts/lint/*.py)
    "--apply", "--calls-only", "--range", "--only",
})

#: Prose fragments, not flags: the docs write "--no-" and "--skip-" when
#: talking about a family of switches.
FRAGMENTS = frozenset({"--no-", "--skip-"})


def _pipeline_flags():
    flags = set()
    parser, _subparsers = pipeline_parser()
    for sub in parser._subparsers._group_actions[0].choices.values():
        for action in sub._actions:
            flags.update(o for o in action.option_strings if o.startswith("--"))
    return flags


def _build_py_flags():
    src = open(os.path.join(ROOT, "scripts", "build.py"), encoding="utf-8").read()
    return set(re.findall(r'add_argument\(\s*"(--[a-z0-9][a-z0-9\-]*)"', src))


def _other_tool_flags():
    """Flags of the smaller tools the docs also mention."""
    flags = set()
    for rel in ("scripts/artifact_sign.py", "llvmgen/codegen.py",
                "irgen/chaff_circuits.py", "irgen/fragmentation.py",
                "irgen/variant_pool.py", "irgen/watermark.py",
                "scripts/sbom.py", "scripts/secure_cleanup.py"):
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        src = open(path, encoding="utf-8").read()
        flags.update(re.findall(
            r'add_argument\(\s*["\'](--[a-z0-9][a-z0-9\-]*)', src))
    return flags


def _documented_flags():
    found = {}
    for rel in USER_DOCS:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        for match in re.finditer(r"(?<![\w-])(--[a-z0-9][a-z0-9\-]*)", text):
            found.setdefault(match.group(1), set()).add(rel)
    return found


def test_every_documented_flag_exists():
    known = (_pipeline_flags() | _build_py_flags() | _other_tool_flags()
             | FOREIGN_FLAGS | FRAGMENTS)
    unknown = {}
    for flag, docs in _documented_flags().items():
        if flag not in known:
            unknown[flag] = sorted(docs)
    assert not unknown, (
        "the documentation mentions flags that no CLI accepts: %r" % (unknown,))


def test_the_pipeline_and_build_clis_share_no_ambiguous_flags():
    """A flag with a different meaning in the two CLIs is a trap.

    ``--watermark`` used to mean "license target" in the loader CLI and
    "semantic watermark in the IR" in the native pipeline.  The loader
    CLI's flag is now ``--lock-hwid``, and the old spelling survives
    there only as an ALIAS for it -- so it must resolve to the same
    dest, and it must not be a separate flag with its own meaning.
    """
    parser, subparsers = pipeline_parser()
    build_sub = subparsers.choices["build"]
    dests = {}
    for action in build_sub._actions:
        for opt in action.option_strings:
            if opt.startswith("--"):
                dests[opt] = action.dest
    assert "--lock-hwid" in dests, "the loader CLI must offer --lock-hwid"
    assert "--watermark" in dests, (
        "the deprecated --watermark spelling should remain as an alias")
    assert dests["--watermark"] == dests["--lock-hwid"], (
        "--watermark must be an alias of --lock-hwid, not its own flag")

    # --rename-internal is genuinely on both CLIs, with the same meaning.
    assert "--rename-internal" in _build_py_flags()


def test_the_audit_reports_flag_removals_are_annotated():
    """A historical report may mention a removed flag, but must say so."""
    for rel in ("docs/AUDIT-2026-10-19.md",
                "docs/AUDIT-2026-10-19-followup.md",
                "docs/AUDIT-2026-10-20.md"):
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        if "--no-section-split" in text:
            assert "RESOLVED" in text, (
                "%s mentions --no-section-split without a RESOLVED note; "
                "that switch never existed" % rel)
