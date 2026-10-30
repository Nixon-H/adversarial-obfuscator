"""Op-count truth lock (verified-140 audit; was 141 before str.decode was
removed — Python 3 has no str.decode, only bytes.decode).

The "140 lowered operations" claim is now TRUE and enforced here:

- 20 families, 148 registry entries (147 unique names)
- 139 callable ops + 8 AST node-kind markers (BinOp, Compare, BoolOp,
  Not, Subscript, JoinedStr, FormattedValue, AugAssign — Phase-2 only,
  no runtime function yet)
- 140 native kernel ops (NATIVE_OPS): the 139 callable ops + fuse dispatch
- Every kernel op routes at least one real call site through the kernel
  (behavioral parity locked by tests/test_lowering_parity_141.py — file
  name kept for stable references; content asserts 140); the
  original 51 op names/shapes are untouched.

Python 3.10 compatible: stdlib only, no match statements.
"""
import ast
import os
import re
import subprocess

from obfuscator import lowering
from obfuscator.kernel_gen import NATIVE_OPS
import obfuscator.lowering_shim as shim

NODE_KINDS = frozenset({
    "BinOp", "Compare", "BoolOp", "Not",
    "Subscript", "JoinedStr", "FormattedValue", "AugAssign",
})

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The original 51 kernel entries (order-independent): additive growth
# must never rename, drop, or reshape these. ("str.decode" was removed
# outright per audit: Python 3 has no str.decode — only bytes.decode —
# so it was never a real op, just a misroute hazard.)
ORIGINAL_OPS = frozenset({
    "print", "input", "open",
    "int", "float", "str", "bool", "chr", "ord", "hex", "oct", "bin",
    "abs", "round", "len",
    "str.join", "str.split", "str.format", "str.encode",
    "str.upper", "str.lower",
    "list", "tuple", "dict", "set", "frozenset", "sorted", "reversed",
    "enumerate", "zip",
    "getattr", "setattr", "hasattr", "isinstance", "issubclass",
    "callable", "id", "hash",
    "iter", "next", "repr", "bytes",
    "map", "filter", "any", "all", "sum", "min", "max",
    "__import__", "fuse",
})


def test_registry_counts():
    assert len(lowering.FAMILIES) == 20
    total = sum(len(info["ops"]) for info in lowering.FAMILIES.values())
    assert total == 148
    unique = {op for info in lowering.FAMILIES.values() for op in info["ops"]}
    assert len(unique) == 147
    assert (unique & NODE_KINDS) == NODE_KINDS  # all 8 node-kind markers
    assert len(unique - NODE_KINDS) == 139  # callable ops


def test_native_kernel_counts():
    assert len(NATIVE_OPS) == 140
    assert len(set(NATIVE_OPS)) == 140  # no duplicate entries
    callable_ops = (
        {op for info in lowering.FAMILIES.values() for op in info["ops"]}
        - NODE_KINDS
    )
    assert set(NATIVE_OPS) - {"fuse"} == callable_ops


def test_original_51_untouched():
    assert ORIGINAL_OPS <= set(NATIVE_OPS)
    for op in ORIGINAL_OPS - {"fuse"}:
        fam_hit = [n for n, i in lowering.FAMILIES.items()
                   if op in i["ops"]]
        assert fam_hit, op
        assert hasattr(shim, "_nxk_" + op.replace(".", "_")), op


def test_shim_kernel_parity():
    shim_names = {n for n in dir(shim) if n.startswith("_nxk_")}
    native_tokens = {"_nxk_" + op.replace(".", "_") for op in NATIVE_OPS}
    assert shim_names == native_tokens
    assert len(shim_names) == 140


def test_design_doc_states_verified_140():
    path = os.path.join(REPO_ROOT, "obfuscator", "lowering_DESIGN.md")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    assert "verified-140" in text.lower() or "verified 140" in text.lower()
    assert "140" in text
    # No stale debunk framing may survive.
    for line in text.splitlines():
        low = line.lower()
        if "141" in line and ("debunk" in low or "does not match" in low
                              or "unverified" in low):
            raise AssertionError(line)


def _is_ignored(path):
    """True when git ignores *path* (a build leftover, not source)."""
    try:
        rel = os.path.relpath(path, REPO_ROOT)
    except ValueError:
        return False
    if rel.startswith(".."):
        return False
    try:
        out = subprocess.run(["git", "-C", REPO_ROOT, "check-ignore", "-q", rel],
                             capture_output=True, timeout=30)
        return out.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def test_no_bare_141_claim_in_code():
    # Only archive fixtures, generated build outputs, and test fixture
    # data may contain the digits 141; live code + user docs must frame
    # it as the verified count (or vendor/unverified for history).
    # File-path mentions (tests/...parity_141.py) are self-referential,
    # not claims, and are also allowed.
    # "h0h5-results" holds generated transfer-experiment artifacts: their
    # CFI constants are random integers, so the digits "141" appear by
    # coincidence (e.g. 314182922) — not as an op-count claim.
    bad = []
    skip_dirs = {"archive", "build", ".git", ".opencode", ".mypy_cache",
                 ".pytest_cache", "__pycache__", "h0h5-results",
                 # Vendored third-party code for the external corpus: its
                 # constants are not this project's claims. recipes.py's
                 # Miller-Rabin base 4759123141 contains the digits by accident.
                 }
    skip_files = {"test_opcount_truth.py", "test_multi_func.py",
                  "test_lowering_parity_141.py"}
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fn in files:
            if not (fn.endswith(".py") or fn.endswith(".md")):
                continue
            if fn in skip_files or ".decoy.py" in fn or "attention_poison" in fn:
                continue
            # Vendored third-party code for the external corpus: its constants
            # are not this project's claims. recipes.py's Miller-Rabin base
            # 4759123141 contains the digits by accident.
            _vendored = os.path.join(root, fn)
            if (os.sep + os.path.join("corpus", "external") in _vendored
                    or os.sep + os.path.join("corpus", "bulk") in _vendored):
                continue
            p = os.path.join(root, fn)
            # Git-ignored files are build leftovers, not source: a failed
            # build used to leave its staging file in the repository root,
            # and the check is about the SOURCE, not about whatever a
            # half-finished build left behind.
            if _is_ignored(p):
                continue
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    src = f.read()
            except OSError:
                continue
            for i, line in enumerate(src.splitlines(), 1):
                s = line.strip()
                if s.startswith("#") or s.startswith("//"):
                    continue
                # A DOI can contain the digits by accident: "141" appears
                # inside 10.3390/app14125056.  That is a citation, not an
                # op-count claim, so strip DOIs before looking.
                _nodoiline = re.sub(r"10\.\d{4,}/[^\s)\]}]*", "<DOI>", line)
                if "141" in _nodoiline and "3.14159" not in line:
                    # Allowed only if framed as vendor/unverified history,
                    # as the verified count, or as a file-path reference
                    # to the parity test module itself.
                    low = line.lower()
                    if ("vendor" in low or "unverif" in low
                            or "verified" in low or "verif" in low
                            or "test_lowering_parity_141" in line
                            or "test_opcount_truth" in line):
                        continue
                    bad.append("%s:%d: %s" % (p, i, line.strip()[:120]))
    assert not bad, bad


def test_touched_files_parse_on_310():
    for rel in ("obfuscator/lowering.py", "obfuscator/lowering_shim.py",
                "obfuscator/kernel_gen.py",
                "tests/test_lowering_parity_141.py"):
        path = os.path.join(REPO_ROOT, rel)
        with open(path, encoding="utf-8") as f:
            src = f.read()
        ast.parse(src, feature_version=(3, 10))
    import obfuscator.kernel_gen  # noqa: F401
    import obfuscator.lowering  # noqa: F401
    assert True
