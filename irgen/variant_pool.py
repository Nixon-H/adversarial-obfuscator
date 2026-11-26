"""
variant_pool.py

Purpose:
Advanced Protection — Function Diversity: Polymorphic Implementation Pool.
Each sensitive function is compiled from N semantically equivalent but
structurally different implementations. Only one is selected per build.

Architectural Role:
Pre-build diversity pass. Generates multiple variants of each target
function. One variant is selected per build based on the build seed.

Security Relevance:
- Each build gets a differently named/scrambled copy of the same function.
- The selection is deterministic per build seed but unpredictable
  across builds.
- Variants use scrambled variable names (BLAKE2b-derived).
- The four strategy slots currently emit semantic-preserving renamed copies:
  the previous rewrites (recursion-to-loop, memoization, table lookup, loop
  unrolling) were not semantics-preserving and have been disabled rather
  than shipped as "equivalent" variants.

Threat model: Binary diffing, cross-build comparison, signature detection.

Dependencies:
    - irgen.compile (compile_py_to_ir, ir_module_to_text)
"""

from __future__ import annotations
import argparse
import ast
import builtins
import hashlib
import json
import os
import sys
import copy
import symtable
from typing import Optional


def _load_config() -> dict:
    """Load the project config for phase2 gating."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", "default.json"
    )
    try:
        with open(config_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _phase2_enabled() -> bool:
    """Check if phase2 (advanced protection) is enabled in config."""
    cfg = _load_config()
    return cfg.get("shadow_compiler", {}).get("advanced_protection", cfg.get("shadow_compiler", {}).get("phase2", {})).get("enabled", False)


def _blake2b(data: bytes, size: int = 32) -> bytes:
    """BLAKE2b hash for seeded deterministic derivation."""
    return hashlib.blake2b(data, digest_size=size).digest()


def _derive_constant(seed: bytes, label: str, num_bytes: int = 8) -> int:
    """Derive a deterministic constant from a seed and label."""
    h = _blake2b(seed + label.encode(), num_bytes)
    return int.from_bytes(h, "little")


def _modinv(a: int, m: int) -> int:
    """Modular inverse for affine encoding."""
    return pow(a, -1, m)


_AFFINE_A = None
_AFFINE_B = None


def affine_encode(x: int, A: int, b: int) -> int:
    """Affine encode: A*x + b mod 2^64."""
    return (A * x + b) & 0xFFFFFFFFFFFFFFFF


def affine_decode(x: int, A: int, b: int) -> int:
    """Affine decode: (x - b) * A^{-1} mod 2^64."""
    return ((x - b) * _modinv(A, 0xFFFFFFFFFFFFFFFF + 1)) & 0xFFFFFFFFFFFFFFFF


# ---- Variant Strategies ----

def _identifier_names(tree: ast.AST) -> set[str]:
    """Collect every identifier spelling that a generated name must avoid."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Name, ast.arg, ast.FunctionDef,
                             ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.id if isinstance(node, ast.Name) else
                      node.arg if isinstance(node, ast.arg) else node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add((alias.asname or alias.name).split('.')[0])
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            names.update(node.names)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            names.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            names.add(node.rest)
    return names


def _fresh_identifier(base: str, reserved: set[str]) -> str:
    """Return ``base`` or a deterministic unused suffix, never a collision."""
    candidate = base
    index = 1
    while candidate in reserved:
        candidate = f"{base}_{index}"
        index += 1
    reserved.add(candidate)
    return candidate


def _renamed_copy(source: str, func_name: str, suffix: str) -> str:
    """Return a semantic-preserving copy of ``func_name`` under a new name.

    The old per-strategy rewrites claimed semantic equivalence while emitting
    undefined variables, empty stacks and changed signatures. Until a rewrite
    can be verified against the original for arbitrary Python, the safe
    variant is an exact copy whose definition and references are renamed
    consistently.
    """
    tree = ast.parse(source)
    if _find_func(tree, func_name) is None:
        return source
    new_tree = copy.deepcopy(tree)
    new_name = _fresh_identifier(
        f"{func_name}_{suffix}", _identifier_names(new_tree))
    module_table = symtable.symtable(source, "<variant>", "exec")
    scope_tables: dict[tuple[str, str, int], list[symtable.SymbolTable]] = {}

    def collect_tables(table):
        for child in table.get_children():
            # Python 3.13 returns an enum for get_type(); 3.12 returns a str.
            scope_type = child.get_type()
            scope_value = getattr(scope_type, "value", scope_type)
            key = (scope_value, child.get_name(), child.get_lineno())
            scope_tables.setdefault(key, []).append(child)
            collect_tables(child)

    collect_tables(module_table)

    class _RenameReferences(ast.NodeTransformer):
        def __init__(self):
            self.table = module_table

        def visit_Name(self, node):
            if node.id != func_name:
                return node
            is_module_reference = self.table is module_table
            is_global_reference = (
                func_name in self.table.get_identifiers()
                and self.table.lookup(func_name).is_global()
            )
            if is_module_reference or is_global_reference:
                node.id = new_name
            return node

        def _visit_scope(self, key, body):
            candidates = scope_tables.get(key, [])
            previous = self.table
            if candidates:
                self.table = candidates.pop(0)
            for node in body:
                self.visit(node)
            self.table = previous

        def visit_FunctionDef(self, node):
            for decorator in node.decorator_list:
                self.visit(decorator)
            self.visit(node.args)
            if node.returns is not None:
                self.visit(node.returns)
            self._visit_scope(("function", node.name, node.lineno), node.body)
            return node

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ClassDef(self, node):
            for decorator in node.decorator_list:
                self.visit(decorator)
            for base in node.bases:
                self.visit(base)
            for keyword in node.keywords:
                self.visit(keyword)
            self._visit_scope(("class", node.name, node.lineno), node.body)
            return node

        def visit_Lambda(self, node):
            self.visit(node.args)
            self._visit_scope(("function", "lambda", node.lineno), (node.body,))
            return node

    new_tree = _RenameReferences().visit(new_tree)
    for node in new_tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            node.name = new_name
            break
    return ast.unparse(new_tree)


def _strategy_loop_bottomup(source: str, func_name: str, seed: bytes) -> str:
    """Loop-based variant slot: currently a semantic-preserving renamed copy."""
    return _renamed_copy(source, func_name, "loop")


def _strategy_recursive_topdown(source: str, func_name: str, seed: bytes) -> str:
    """Recursive/memoized variant slot: semantic-preserving renamed copy."""
    return _renamed_copy(source, func_name, "rec")


def _strategy_table_driven(source: str, func_name: str, seed: bytes) -> str:
    """Table-driven variant slot: semantic-preserving renamed copy."""
    return _renamed_copy(source, func_name, "table")


def _strategy_unrolled(source: str, func_name: str, seed: bytes) -> str:
    """Unrolled variant slot: semantic-preserving renamed copy."""
    return _renamed_copy(source, func_name, "unrolled")


# ---- Helper Functions ----

def _find_func(tree: ast.Module, name: str) -> Optional[ast.FunctionDef]:
    """Find a function definition by name in an AST module."""
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _has_while_recursion(node: ast.AST, func_name: str) -> bool:
    """Check if a node contains a recursive call to func_name."""
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == func_name:
            return True
    return False


def _is_recursive_call(node: ast.AST, func_name: str) -> bool:
    """Check if a node is a recursive call to func_name."""
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == func_name


def _recursion_to_loop(node: ast.AST, func_name: str, new_name: str, seed: bytes) -> list[ast.stmt]:
    """
    Generate stack-based loop body to replace recursion.

    Creates an explicit stack structure and iterative loop that
    emulates the original recursive computation.
    """
    stack_name = f"__stack_{func_name}_{hex(_derive_constant(seed, 'stack') & 0xFFFF)[2:]}"
    result_name = f"__res_{func_name}_{hex(_derive_constant(seed, 'res') & 0xFFFF)[2:]}"

    stmts = ast.parse(
        f"{stack_name} = []\n"
        f"{result_name} = 0\n"
        f"while True:\n"
        f"    if not {stack_name}:\n"
        f"        break\n"
        f"    {result_name} = {stack_name}.pop()\n"
    ).body

    return stmts


def _replace_calls_with_table_lookup(node: ast.AST, table_name: str, seed: bytes) -> ast.AST:
    """Replace binop calls with table lookups (stub transformer)."""
    transformer = _TableLookupTransformer(table_name, seed)
    return transformer.visit(node)


class _TableLookupTransformer(ast.NodeTransformer):
    """AST transformer that replaces binops with table lookups."""

    def __init__(self, table_name: str, seed: bytes):
        self.table_name = table_name
        self.seed = seed

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        return node


def _unroll_loop(node: ast.AST, seed: bytes) -> list[ast.stmt]:
    """
    Unroll a for loop over range(N) with small constant N.

    Duplicates the loop body N times to produce straight-line code.
    """
    if isinstance(node, ast.For) and isinstance(node.iter, ast.Call):
        if isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
            try:
                if node.iter.args and isinstance(node.iter.args[0], ast.Constant):
                    count = node.iter.args[0].value
                    if isinstance(count, int) and count <= 32:
                        body = node.body
                        return body * count
            except (IndexError, TypeError):
                pass
    return [node]


def _inline_expressions(node: ast.AST, seed: bytes) -> ast.AST:
    """Inline expression transformations (stub)."""
    return node


def _scramble_variable_names(source: str, seed: bytes) -> str:
    """
    Rename user-defined variables with deterministic BLAKE2b-derived names.

    Only assignment targets and loop variables are renamed. Parameters keep
    their spelling because keyword call labels are part of the callable API.
    Builtins, imported names and function names also keep their spelling.
    """
    tree = ast.parse(source)
    builtin_names = set(dir(builtins))

    class _ClassBodyBindings(ast.NodeVisitor):
        """Collect class attributes without descending into nested scopes."""

        def __init__(self):
            self.names: set[str] = set()

        def visit_Name(self, node):
            if isinstance(node.ctx, (ast.Store, ast.Del)):
                self.names.add(node.id)

        def visit_FunctionDef(self, node):
            for decorator in node.decorator_list:
                self.visit(decorator)
            self.visit(node.args)
            if node.returns is not None:
                self.visit(node.returns)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ClassDef(self, node):
            for decorator in node.decorator_list:
                self.visit(decorator)
            for base in node.bases:
                self.visit(base)
            for keyword in node.keywords:
                self.visit(keyword)

        def visit_Lambda(self, node):
            self.visit(node.args)

        def visit_comprehension(self, node):
            self.visit(node.iter)
            for condition in node.ifs:
                self.visit(condition)

    # Keep API-visible names and bindings whose string fields are not
    # rewritten by VarRenamer: parameters, imports, callable/attribute bases,
    # class attributes, exception targets and pattern captures.
    fixed: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            fixed.add(node.name)
            class_bindings = _ClassBodyBindings()
            for statement in node.body:
                class_bindings.visit(statement)
            fixed.update(class_bindings.names)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fixed.add(node.name)
        elif isinstance(node, ast.arg):
            fixed.add(node.arg)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                fixed.add((alias.asname or alias.name).split('.')[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fixed.add(node.func.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            fixed.add(node.value.id)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            fixed.update(node.names)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            fixed.add(node.name)
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            fixed.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            fixed.add(node.rest)

    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)

    var_map: dict[str, str] = {}
    reserved = _identifier_names(tree) | builtin_names
    for name in sorted(bound - builtin_names - fixed):
        if name.startswith("__"):
            continue
        h = _blake2b(seed + name.encode(), 4)
        base = f"v_{int.from_bytes(h, 'little'):08x}"
        var_map[name] = _fresh_identifier(base, reserved)

    class VarRenamer(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name) -> ast.Name:
            if node.id in var_map:
                node.id = var_map[node.id]
            return node

        def visit_arg(self, node: ast.arg) -> ast.arg:
            self.generic_visit(node)
            return node

    tree = VarRenamer().visit(tree)
    return ast.unparse(tree)


# ---- Public API ----

VARIANT_GENERATORS = {
    "A": _strategy_loop_bottomup,
    "B": _strategy_recursive_topdown,
    "C": _strategy_table_driven,
    "D": _strategy_unrolled,
}


def generate_variants(
    python_source: str,
    function_name: str,
    num_variants: int = 4,
    seed: bytes = None,
) -> list[str]:
    """
    Generate N semantically equivalent variants of a function.

    Each variant uses a different strategy from the VARIANT_GENERATORS
    dict. Variable names in each variant are scrambled with a
    variant-specific seed.

    Args:
        python_source: Source code containing the function.
        function_name: Name of the target function.
        num_variants: Number of variants to produce.
        seed: Build seed for deterministic generation.

    Returns:
        List of variant source code strings.
    """
    if not _phase2_enabled():
        raise RuntimeError("Advanced Protection must be enabled for variant generation")

    if seed is None:
        seed = os.urandom(32)

    strategies = list(VARIANT_GENERATORS.keys())
    selected = strategies[:num_variants]

    variants = []
    for i, strat_key in enumerate(selected):
        gen = VARIANT_GENERATORS[strat_key]
        variant_seed = _blake2b(seed + f"variant_{i}".encode())
        variant_source = gen(python_source, function_name, variant_seed)
        scrambled = _scramble_variable_names(variant_source, variant_seed)
        variants.append(scrambled)

    while len(variants) < num_variants:
        variants.append(python_source)

    return variants[:num_variants]


def select_variant(
    variants: list[str],
    build_seed: bytes,
    function_index: int,
) -> str:
    """
    Select one variant for a given build seed and function index.

    The selection is deterministic: same seed + index always produces
    the same variant.
    """
    if not _phase2_enabled():
        return variants[0] if variants else ""

    h = _blake2b(build_seed + f"variant_{function_index}".encode())
    idx = int.from_bytes(h, "little") % max(len(variants), 1)
    return variants[idx]


class VariantPool:
    """
    Manages a pool of function variants for a build.

    Each function can have N variants. When compiled, one is selected
    per build based on the build seed.
    """

    def __init__(self, build_seed: bytes):
        """Initialize with a build seed for deterministic selection."""
        self.build_seed = build_seed
        self.pool: dict[str, list[str]] = {}

    def add_function(self, name: str, source: str, num_variants: int = 4):
        """Generate and store variants for a function."""
        variants = generate_variants(source, name, num_variants, self.build_seed)
        self.pool[name] = variants

    def get_selected(self, name: str, index: int) -> str:
        """Get the selected variant for a function."""
        variants = self.pool.get(name, [])
        if not _phase2_enabled():
            return variants[0] if variants else ""
        return select_variant(variants, self.build_seed, index)

    def compile_all_variants(self, output_dir: str):
        """
        Compile all variants to Python and IR files.

        Writes each variant as both .py and .ir files.
        """
        os.makedirs(output_dir, exist_ok=True)
        for func_name, variants in self.pool.items():
            for i, variant_src in enumerate(variants):
                path = os.path.join(output_dir, f"{func_name}_variant_{i}.py")
                with open(path, "w") as f:
                    f.write(variant_src)

                ir_path = os.path.join(output_dir, f"{func_name}_variant_{i}.ir")
                try:
                    from irgen.compile import compile_py_to_ir, ir_module_to_text
                    module = compile_py_to_ir(variant_src)
                    ir_text = ir_module_to_text(module)
                    with open(ir_path, "w") as f:
                        f.write(ir_text)
                except ImportError:
                    pass


def select_variant_runtime(
    master_key: bytes,
    execution_count: int,
    timestamp_bucket: int,
    num_variants: int,
) -> int:
    """
    Determine which variant index to use at runtime.

    Uses master key, execution count, and timestamp bucket for
    hash-based selection. This enables runtime variant switching.
    """
    if not _phase2_enabled():
        return 0

    data = master_key + str(execution_count).encode() + str(timestamp_bucket).encode()
    h = _blake2b(data)
    return int.from_bytes(h, "little") % max(num_variants, 1)


# ---- CLI ----

def _cli_generate(args: list[str]):
    """CLI handler for variant generation."""
    parser = argparse.ArgumentParser(description="Generate function variants")
    parser.add_argument("source", help="Source Python file")
    parser.add_argument("--functions", required=True, help="Comma-separated function names")
    parser.add_argument("--num-variants", type=int, default=4)
    parser.add_argument("--seed", type=lambda s: bytes.fromhex(s), default=None)
    parser.add_argument("--output-dir", default=None)
    pargs = parser.parse_args(args)

    with open(pargs.source) as f:
        source = f.read()

    seed = pargs.seed or os.urandom(32)
    func_names = [f.strip() for f in pargs.functions.split(",")]
    pool = VariantPool(seed)

    for name in func_names:
        pool.add_function(name, source, pargs.num_variants)
        print(f"Generated {pargs.num_variants} variants for '{name}'")

    if pargs.output_dir:
        pool.compile_all_variants(pargs.output_dir)
        print(f"All variants compiled to {pargs.output_dir}/")

    print(f"Build seed: {seed.hex()}")


def _cli_select(args: list[str]):
    """CLI handler for variant selection."""
    parser = argparse.ArgumentParser(description="Select variants for build")
    parser.add_argument("--seed", required=True, type=lambda s: bytes.fromhex(s))
    parser.add_argument("variants_json", help="JSON file: {fn_name: [variant_sources]}")
    pargs = parser.parse_args(args)

    with open(pargs.variants_json) as f:
        pool_data = json.load(f)

    selected = {}
    for idx, (func_name, variants) in enumerate(pool_data.items()):
        chosen = select_variant(variants, pargs.seed, idx)
        selected[func_name] = chosen
        print(f"{func_name} -> variant {variants.index(chosen)} (of {len(variants)})")

    output_path = pargs.variants_json.replace(".json", "_selected.json")
    with open(output_path, "w") as f:
        json.dump(selected, f, indent=2)
    print(f"Selected variants written to {output_path}")


def main():
    """CLI entry point for variant pool."""
    if not _phase2_enabled():
        _load_config()
        print("Advanced Protection disabled. Set advanced_protection.enabled = true in config/default.json")
        sys.exit(0)

    parser = argparse.ArgumentParser(
        description="Nixon Advanced Protection -- Function Diversity (Polymorphic Implementation Pool)"
    )
    subparsers = parser.add_subparsers(dest="command")

    gen_parser = subparsers.add_parser("generate", help="Generate variants for functions")
    gen_parser.add_argument("source", help="Source Python file")
    gen_parser.add_argument("--functions", required=True, help="Comma-separated function names")
    gen_parser.add_argument("--num-variants", type=int, default=4)
    gen_parser.add_argument("--seed", type=lambda s: bytes.fromhex(s), default=None)
    gen_parser.add_argument("--output-dir", default=None)

    sel_parser = subparsers.add_parser("select", help="Select variants for build")
    sel_parser.add_argument("--seed", required=True, type=lambda s: bytes.fromhex(s))
    sel_parser.add_argument("variants_json", help="JSON file: {fn_name: [variant_sources]}")

    args = parser.parse_args()

    if args.command == "generate":
        _cli_generate(sys.argv[2:])
    elif args.command == "select":
        _cli_select(sys.argv[2:])
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
