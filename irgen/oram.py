"""
oram.py

Purpose:
ORAM compiler hint generator. Marks variables for Path-ORAM allocation in
the protection pipeline. Produces annotations in Python source and generates
ORAM controller configuration dicts for the runtime.

Architectural Role:
Pre-compilation hinting pass. Annotates specific variables with # oram:
comments that are consumed by the downstream ORAM instrumentation pass.
Also generates configuration for the runtime OramController.

Security Relevance:
ORAM (Oblivious RAM) obscures which memory locations are accessed by
transforming every access into a deterministic path read/write. This
module identifies which variables should be ORAM-protected and produces
the metadata needed by the runtime controller.

Key design decisions:
- Leaf assignment is deterministic from variable name and seed:
  SHA-256(varname || seed) % num_blocks. This ensures consistent
  mapping across runs.
- Variables are annotated with # oram: comments at the source level,
  making the ORAM intent visible to the compilation pipeline.
- The config dict includes a leaf_mapping that maps each variable
  to its initial tree leaf.
"""

import ast
import hashlib

_ORAM_ANNOTATION_PREFIX = "# oram:"


def _leaf_for_variable(varname: str, num_blocks: int, seed: bytes) -> int:
    """
    Deterministically compute a leaf index for a variable.

    Uses SHA-256(varname || seed), truncated to first 8 bytes as
    a little-endian integer, modulo num_blocks.
    """
    h = hashlib.sha256(varname.encode("utf-8") + seed).digest()
    return int.from_bytes(h[:8], "little") % num_blocks


def annotate_oram_variables(source: str, variables: list[str]) -> str:
    """
    Add ``# oram: <varname>`` annotations to Python source.

    Walks the AST to find assignment targets, annotated assignments,
    and function parameters matching the given variable names. Adds
    a trailing comment to the first occurrence line.

    Security note: The annotations are source-level comments and are
    visible to anyone with access to the source. For obfuscated
    distributions, these should be stripped or the ORAM mapping
    should be embedded in the binary.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source

    var_set = set(variables)
    lines = source.splitlines(keepends=True)
    modified_lines = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in var_set:
                    lineno = target.lineno
                    if lineno is not None and lineno not in modified_lines:
                        idx = lineno - 1
                        if idx < len(lines):
                            stripped = lines[idx].rstrip("\n")
                            if _ORAM_ANNOTATION_PREFIX not in stripped:
                                lines[idx] = stripped + f"  {_ORAM_ANNOTATION_PREFIX} {target.id}\n"
                                modified_lines.add(lineno)

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id in var_set:
                lineno = node.target.lineno
                if lineno is not None and lineno not in modified_lines:
                    idx = lineno - 1
                    if idx < len(lines):
                        stripped = lines[idx].rstrip("\n")
                        if _ORAM_ANNOTATION_PREFIX not in stripped:
                            lines[idx] = stripped + f"  {_ORAM_ANNOTATION_PREFIX} {node.target.id}\n"
                            modified_lines.add(lineno)

        elif isinstance(node, ast.FunctionDef):
            for arg in node.args.args:
                if arg.arg in var_set:
                    lineno = arg.lineno
                    if lineno is not None and lineno not in modified_lines:
                        idx = lineno - 1
                        if idx < len(lines):
                            stripped = lines[idx].rstrip("\n")
                            if _ORAM_ANNOTATION_PREFIX not in stripped:
                                lines[idx] = stripped + f"  {_ORAM_ANNOTATION_PREFIX} {arg.arg}\n"
                                modified_lines.add(lineno)

    return "".join(lines)


def generate_oram_config(variables: list[str], num_blocks: int) -> dict:
    """
    Generate ORAM controller configuration dict.

    Returns a JSON-serializable dict suitable for runtime
    OramController initialization. Includes the leaf mapping
    for each variable.
    """
    seed = b"shadow-compiler-oram-seed"
    mapping = {}
    for v in variables:
        leaf = _leaf_for_variable(v, num_blocks, seed)
        mapping[v] = leaf

    return {
        "enabled": True,
        "variables": variables,
        "num_blocks": num_blocks,
        "tree_height": 8,
        "block_size": 64,
        "leaf_mapping": mapping,
    }


def detect_oram_annotations(source: str) -> list[str]:
    """
    Extract variable names annotated with ``# oram:`` from source.

    Scans each line for the prefix and extracts the variable name
    that follows.
    """
    variables: list[str] = []
    prefix = _ORAM_ANNOTATION_PREFIX
    for line in source.splitlines():
        stripped = line.strip()
        if prefix in stripped:
            idx = stripped.index(prefix) + len(prefix)
            varname = stripped[idx:].strip()
            if varname:
                variables.append(varname)
    return variables
