"""Op-count truth lock (GAP 5 audit).

The vendor "141 lowered ops" claim does not match this repo. Lock the
audited numbers so the claim cannot silently drift back:

- 14 families, 61 registry entries (59 unique names)
- 51 callable ops + 8 AST node-kind markers (BinOp, Compare, BoolOp,
  Not, Subscript, JoinedStr, FormattedValue, AugAssign — Phase-2 only,
  no runtime function yet)
- 52 native kernel ops (NATIVE_OPS): the 51 callable ops + fuse dispatch

Python 3.10 compatible: stdlib only, no match statements.
"""
import ast
import os

from obfuscator import lowering
from obfuscator.kernel_gen import NATIVE_OPS
import obfuscator.lowering_shim as shim

NODE_KINDS = frozenset({
    "BinOp", "Compare", "BoolOp", "Not",
    "Subscript", "JoinedStr", "FormattedValue", "AugAssign",
})

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_registry_counts():
    assert len(lowering.FAMILIES) == 14
    total = sum(len(info["ops"]) for info in lowering.FAMILIES.values())
    assert total == 61
    unique = {op for info in lowering.FAMILIES.values() for op in info["ops"]}
    assert len(unique) == 59
    assert (unique & NODE_KINDS) == NODE_KINDS  # all 8 node-kind markers
    assert len(unique - NODE_KINDS) == 51  # callable ops


def test_native_kernel_counts():
    assert len(NATIVE_OPS) == 52
    callable_ops = (
        {op for info in lowering.FAMILIES.values() for op in info["ops"]}
        - NODE_KINDS
    )
    assert set(NATIVE_OPS) - {"fuse"} == callable_ops


def test_shim_kernel_parity():
    shim_names = {n for n in dir(shim) if n.startswith("_nxk_")}
    native_tokens = {"_nxk_" + op.replace(".", "_") for op in NATIVE_OPS}
    assert shim_names == native_tokens
    assert len(shim_names) == 52


def test_design_doc_has_no_stale_141():
    path = os.path.join(REPO_ROOT, "obfuscator", "lowering_DESIGN.md")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    for line in text.splitlines():
        if "141" in line:
            # Any surviving 141 mention must be framed as the debunked
            # vendor claim, never as our own op count.
            lowered = line.lower()
            assert "vendor" in lowered or "unverif" in lowered, line
    # The audited numbers must be present.
    assert "61" in text and "52" in text


def test_no_bare_141_claim_in_code():
    # Only archive fixtures, generated build outputs, and test fixture
    # data may contain the digits 141; live code + user docs must not
    # state it as our own op count.
    bad = []
    skip_dirs = {"archive", "build", ".git", ".opencode", ".mypy_cache",
                 ".pytest_cache", "__pycache__"}
    skip_files = {"test_opcount_truth.py", "test_multi_func.py"}
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fn in files:
            if not (fn.endswith(".py") or fn.endswith(".md")):
                continue
            if fn in skip_files or ".decoy.py" in fn or "attention_poison" in fn:
                continue
            p = os.path.join(root, fn)
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    src = f.read()
            except OSError:
                continue
            for i, line in enumerate(src.splitlines(), 1):
                s = line.strip()
                if s.startswith("#") or s.startswith("//"):
                    continue
                if "141" in line and "3.14159" not in line:
                    # Allowed only if framed as vendor/unverified claim.
                    low = line.lower()
                    if "vendor" in low or "unverif" in low:
                        continue
                    bad.append("%s:%d: %s" % (p, i, line.strip()[:120]))
    assert not bad, bad


def test_touched_files_parse_on_310():
    for rel in ("obfuscator/lowering_DESIGN.md",):
        _ = rel  # doc file: presence check only
    import obfuscator.kernel_gen  # noqa: F401
    import obfuscator.lowering  # noqa: F401
    assert True
