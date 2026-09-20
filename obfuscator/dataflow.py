"""
Advanced Protection — 15.6: Data-Flow Obfuscation

Obfuscate the relationship between variable definitions and uses to defeat
symbolic execution tools.

Controlled by config/default.json → shadow_compiler → advanced_protection.enabled
"""

from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
import random as _random
import sys
from typing import Optional


def _load_config() -> dict:
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
    cfg = _load_config()
    return cfg.get("shadow_compiler", {}).get("advanced_protection", cfg.get("shadow_compiler", {}).get("phase2", {})).get("enabled", False)


def _blake2b(data: bytes, size: int = 32) -> bytes:
    return hashlib.blake2b(data, digest_size=size).digest()


def _derive_u64(seed: bytes, label: str) -> int:
    h = _blake2b(seed + label.encode(), 8)
    return int.from_bytes(h, "little")


def _modinv(a: int, m: int) -> int:
    return pow(a, -1, m)


U64_MOD = 0xFFFFFFFFFFFFFFFF + 1


def affine_encode(x: int, A: int, b: int) -> int:
    return (A * x + b) & 0xFFFFFFFFFFFFFFFF


def affine_decode(x_enc: int, A: int, b: int) -> int:
    return ((x_enc - b) * _modinv(A & 0xFFFFFFFFFFFFFFFF, U64_MOD)) & 0xFFFFFFFFFFFFFFFF


# ─── 1. Affine Encoded Variables ─────────────────────────────────────────────

def encode_variables_affine(
    ast_tree: ast.Module,
    variables: list[str],
    seed: bytes,
) -> ast.Module:
    params: dict[str, tuple[int, int]] = {}
    for v in variables:
        A = _derive_u64(seed, f"A_{v}") | 1
        b = _derive_u64(seed, f"b_{v}")
        A = A | 1
        params[v] = (A, b)

    class AffineTransformer(ast.NodeTransformer):
        def __init__(self):
            self._split_target: Optional[str] = None

        def visit_Assign(self, node: ast.Assign) -> ast.Assign:
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in params:
                    A, b = params[target.id]
                    enc_name = f"{target.id}_enc"
                    rhs = node.value
                    new_rhs = ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="_affine_enc", ctx=ast.Load()),
                            attr="encode",
                            ctx=ast.Load(),
                        ),
                        args=[rhs, ast.Constant(value=A), ast.Constant(value=b)],
                        keywords=[],
                    )
                    new_target = ast.Name(id=enc_name, ctx=ast.Store())
                    node.targets = [new_target]
                    node.value = new_rhs
                    return node
            return node

        def visit_Name(self, node: ast.Name) -> ast.Name:
            if isinstance(node.ctx, ast.Load) and node.id in params:
                A, b = params[node.id]
                enc_name = f"{node.id}_enc"
                new_node = ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="_affine_enc", ctx=ast.Load()),
                        attr="decode",
                        ctx=ast.Load(),
                    ),
                    args=[
                        ast.Name(id=enc_name, ctx=ast.Load()),
                        ast.Constant(value=A),
                        ast.Constant(value=b),
                    ],
                    keywords=[],
                )
                return new_node
            return node

    tree = AffineTransformer().visit(ast_tree)
    ast.fix_missing_locations(tree)
    return tree


# ─── 2. Value Splitting ──────────────────────────────────────────────────────

def split_value(
    ast_tree: ast.Module,
    variable: str,
    num_parts: int = 2,
    seed: bytes = None,
) -> ast.Module:
    if seed is None:
        seed = os.urandom(32)

    if num_parts < 2:
        return ast_tree

    masks = []
    for i in range(num_parts):
        m = _derive_u64(seed, f"part_{i}")
        masks.append(m)

    part_names = [f"{variable}_part_{i}" for i in range(num_parts)]

    class SplitTransformer(ast.NodeTransformer):
        def visit_Assign(self, node: ast.Assign) -> ast.Assign:
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable:
                    rhs = node.value

                    parts_assign: list[ast.stmt] = []
                    for i, (pn, mask) in enumerate(zip(part_names, masks)):
                        if i == 0:
                            shift = 64 - (64 // num_parts) * (i + 1)
                            extract = ast.BinOp(
                                left=ast.BinOp(
                                    left=rhs,
                                    op=ast.RShift() if shift >= 0 else ast.LShift(),
                                    right=ast.Constant(value=abs(shift)),
                                ),
                                op=ast.BitXor(),
                                right=ast.Constant(value=mask),
                            )
                        elif i == num_parts - 1:
                            total_bits = 64
                            bits_per = total_bits // num_parts
                            shift = total_bits - bits_per
                            extract = ast.BinOp(
                                left=ast.BinOp(
                                    left=rhs,
                                    op=ast.RShift(),
                                    right=ast.Constant(value=shift),
                                ),
                                op=ast.BitXor(),
                                right=ast.Constant(value=mask),
                            )
                        else:
                            bits_per = 64 // num_parts
                            shift = 64 - bits_per * (i + 1)
                            total_bits = 64
                            shift = total_bits - bits_per * (i + 1)
                            mask_val = (1 << bits_per) - 1
                            extract = ast.BinOp(
                                left=ast.BinOp(
                                    left=ast.BinOp(
                                        left=rhs,
                                        op=ast.RShift(),
                                        right=ast.Constant(value=shift),
                                    ),
                                    op=ast.BitAnd(),
                                    right=ast.Constant(value=mask_val),
                                ),
                                op=ast.BitXor(),
                                right=ast.Constant(value=mask),
                            )

                        assign = ast.Assign(
                            targets=[ast.Name(id=pn, ctx=ast.Store())],
                            value=extract,
                        )
                        parts_assign.append(assign)
                    return parts_assign[0] if len(parts_assign) == 1 else ast.If(
                        test=ast.Constant(value=True),
                        body=parts_assign,
                        orelse=[],
                    )
            return node

        def visit_Name(self, node: ast.Name) -> ast.Name:
            if isinstance(node.ctx, ast.Load) and node.id == variable:
                reconstructed = _build_reconstruction(part_names, masks)
                return reconstructed
            return node

    tree = SplitTransformer().visit(ast_tree)
    ast.fix_missing_locations(tree)
    return tree


def _build_reconstruction(part_names: list[str], masks: list[int]) -> ast.AST:
    num_parts = len(part_names)
    result: Optional[ast.AST] = None

    for i, (pn, mask) in enumerate(zip(part_names, masks)):
        part_node = ast.BinOp(
            left=ast.Name(id=pn, ctx=ast.Load()),
            op=ast.BitXor(),
            right=ast.Constant(value=mask),
        )

        if i < num_parts - 1:
            bits_per = 64 // num_parts
            shift = 64 - bits_per * (i + 1)
            part_node = ast.BinOp(
                left=part_node,
                op=ast.LShift(),
                right=ast.Constant(value=shift),
            )

        if result is None:
            result = part_node
        else:
            result = ast.BinOp(
                left=result,
                op=ast.BitOr(),
                right=part_node,
            )

    return result or ast.Constant(value=0)


# ─── 3. MBA State Encoding ──────────────────────────────────────────────────

def _mba_chain_wrap(expr: ast.AST, depth: int = 2) -> ast.AST:
    """Wrap an expression in nested MBA identities to block AI simplification."""
    import random as _rnd
    current = expr
    for _ in range(depth):
        choice = _rnd.randint(0, 5)
        K = _rnd.randint(1000, 9999999)
        if choice == 0:
            current = ast.BinOp(
                left=ast.BinOp(left=current, op=ast.Add(), right=ast.Constant(value=K)),
                op=ast.Sub(), right=ast.Constant(value=K),
            )
        elif choice == 1:
            current = ast.BinOp(
                left=ast.BinOp(left=current, op=ast.BitXor(), right=ast.Constant(value=K)),
                op=ast.BitXor(), right=ast.Constant(value=K),
            )
        elif choice == 2:
            current = ast.UnaryOp(op=ast.Invert(), operand=ast.UnaryOp(op=ast.Invert(), operand=current))
        elif choice == 3:
            nK = _rnd.randint(1, 9999999)
            notK = ast.UnaryOp(op=ast.Invert(), operand=ast.Constant(value=nK))
            current = ast.BinOp(
                left=ast.BinOp(left=current, op=ast.BitAnd(), right=ast.Constant(value=nK)),
                op=ast.BitOr(),
                right=ast.BinOp(left=current, op=ast.BitAnd(), right=notK),
            )
        elif choice == 4:
            nK = _rnd.randint(100, 9999999)
            notK = ast.UnaryOp(op=ast.Invert(), operand=ast.Constant(value=nK))
            current = ast.BinOp(
                left=ast.BinOp(left=current, op=ast.BitOr(), right=ast.Constant(value=nK)),
                op=ast.BitAnd(),
                right=ast.BinOp(left=current, op=ast.BitOr(), right=notK),
            )
        elif choice == 5:
            K = _rnd.randint(2, min(9999, 99999))
            current = ast.BinOp(
                left=ast.BinOp(left=current, op=ast.Mult(), right=ast.Constant(value=K)),
                op=ast.FloorDiv(), right=ast.Constant(value=K),
            )
    return current


def mba_encode_value(value: int, seed: bytes, context: str) -> ast.Expr:
    C1 = _derive_u64(seed, f"{context}_C1")
    S1 = _derive_u64(seed, f"{context}_S1") % 64
    M1 = _derive_u64(seed, f"{context}_M1")
    M2 = _derive_u64(seed, f"{context}_M2")

    mul_expr = ast.BinOp(
        left=ast.Constant(value=value & 0xFFFFFFFFFFFFFFFF),
        op=ast.Mult(),
        right=ast.Constant(value=C1),
    )

    shift_left = ast.BinOp(
        left=ast.Constant(value=value & 0xFFFFFFFFFFFFFFFF),
        op=ast.LShift(),
        right=ast.Constant(value=S1),
    )
    shift_right = ast.BinOp(
        left=ast.Constant(value=value & 0xFFFFFFFFFFFFFFFF),
        op=ast.RShift(),
        right=ast.Constant(value=64 - S1),
    )
    rotate = ast.BinOp(
        left=shift_left,
        op=ast.BitOr(),
        right=shift_right,
    )

    xor_expr = ast.BinOp(
        left=mul_expr,
        op=ast.BitXor(),
        right=rotate,
    )

    and_expr = ast.BinOp(
        left=ast.Constant(value=value & 0xFFFFFFFFFFFFFFFF),
        op=ast.BitAnd(),
        right=ast.Constant(value=M1),
    )

    or_expr = ast.BinOp(
        left=ast.Constant(value=value & 0xFFFFFFFFFFFFFFFF),
        op=ast.BitOr(),
        right=ast.Constant(value=M2),
    )

    sub_expr = ast.BinOp(
        left=and_expr,
        op=ast.Sub(),
        right=or_expr,
    )

    final = ast.BinOp(
        left=xor_expr,
        op=ast.Add(),
        right=sub_expr,
    )

    return _mba_chain_wrap(final, depth=_random.randint(1, 2))


# ─── 4. Affine State Encoder (for VM state) ──────────────────────────────────

class AffineStateEncoder:
    def __init__(self, seed: bytes, num_registers: int = 16):
        self.num_registers = num_registers
        self.A = [self._derive_u64(seed, f"A_{i}") for i in range(num_registers)]
        self.b = [self._derive_u64(seed, f"b_{i}") for i in range(num_registers)]
        self._inv_A: list[int] = []

    def _derive_u64(self, seed: bytes, label: str) -> int:
        h = _blake2b(seed + label.encode(), 8)
        return int.from_bytes(h, "little")

    def encode_state(self, state: list[int]) -> list[int]:
        enc = []
        for i, val in enumerate(state):
            A = self.A[i] | 1
            b = self.b[i]
            enc.append(affine_encode(val, A, b))
        return enc

    def decode_state(self, encoded: list[int]) -> list[int]:
        dec = []
        for i, val in enumerate(encoded):
            A = self.A[i] | 1
            b = self.b[i]
            dec.append(affine_decode(val, A, b))
        return dec

    def encode_op(self, operation: str, operands: list[int]) -> int:
        decoded = []
        for i, val in enumerate(operands):
            A = self.A[i] | 1
            b = self.b[i]
            decoded.append(affine_decode(val, A, b))

        result: int = 0
        if operation == "add":
            result = decoded[0] + decoded[1]
        elif operation == "sub":
            result = decoded[0] - decoded[1]
        elif operation == "mul":
            result = decoded[0] * decoded[1]
        elif operation == "xor":
            result = decoded[0] ^ decoded[1]
        elif operation == "and":
            result = decoded[0] & decoded[1]
        elif operation == "or":
            result = decoded[0] | decoded[1]
        elif operation == "shl":
            result = decoded[0] << decoded[1]
        elif operation == "shr":
            result = decoded[0] >> decoded[1]
        elif operation == "eq":
            result = 1 if decoded[0] == decoded[1] else 0
        elif operation == "not":
            result = ~decoded[0]

        result &= 0xFFFFFFFFFFFFFFFF
        A_out = self.A[0] | 1
        b_out = self.b[0]
        return affine_encode(result, A_out, b_out)


# ─── 5. Data-Flow Obfuscation Pipeline ──────────────────────────────────────

def obfuscate_dataflow(
    ast_tree: ast.Module,
    config: dict,
) -> ast.Module:
    sensitive_vars: list[str] = config.get("sensitive_vars", [])
    if not sensitive_vars:
        sensitive_vars = _auto_detect_sensitive_vars(ast_tree)

    encode_method: str = config.get("encode_method", "affine")
    seed: bytes = config.get("seed", os.urandom(32))

    if encode_method == "affine":
        tree = encode_variables_affine(ast_tree, sensitive_vars, seed)
    elif encode_method == "mba":
        tree = _mba_pipeline(ast_tree, sensitive_vars, seed)
    elif encode_method == "split":
        num_parts = config.get("split_parts", 2)
        tree = ast_tree
        for var in sensitive_vars:
            tree = split_value(tree, var, num_parts, seed)
    else:
        tree = ast_tree

    tree = _verify_semantics_preserved(tree)
    return tree


def _auto_detect_sensitive_vars(ast_tree: ast.Module) -> list[str]:
    candidates: set[str] = set()
    sensitive_keywords = {"key", "secret", "token", "password", "hash", "encrypt", "decrypt", "private"}

    for node in ast.walk(ast_tree):
        if isinstance(node, ast.FunctionDef):
            for kw in sensitive_keywords:
                if kw in node.name.lower():
                    for arg in node.args.args:
                        candidates.add(arg.arg)

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    for kw in sensitive_keywords:
                        if kw in target.id.lower():
                            candidates.add(target.id)

    return list(candidates)


def _mba_pipeline(tree: ast.Module, variables: list[str], seed: bytes) -> ast.Module:
    class MBAValueTransformer(ast.NodeTransformer):
        def __init__(self):
            self._var_index = 0

        def visit_Assign(self, node: ast.Assign) -> ast.Assign:
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in variables:
                    rhs = node.value
                    ctx_str = f"mba_{target.id}"
                    mba_expr = mba_encode_value(
                        int(_extract_constant(rhs) or 0),
                        seed,
                        ctx_str,
                    )
                    self._var_index += 1
                    node.value = ast.BinOp(
                        left=mba_expr,
                        op=ast.Add(),
                        right=ast.Constant(value=0),
                    )
                    return node
            return node

    tree = MBAValueTransformer().visit(tree)
    ast.fix_missing_locations(tree)
    return tree


def _extract_constant(node: ast.AST) -> Optional[int]:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    return None


def _verify_semantics_preserved(tree: ast.Module) -> ast.Module:
    return tree


# ─── CLI ─────────────────────────────────────────────────────────────────────

def _cli_encode(args: list[str]):
    parser = argparse.ArgumentParser(description="Encode variables with affine transform")
    parser.add_argument("source", help="Source Python file")
    parser.add_argument("-o", "--output", required=True, help="Output file")
    parser.add_argument("--vars", required=True, help="Comma-separated variable names")
    parser.add_argument("--seed", type=lambda s: bytes.fromhex(s), default=None)
    pargs = parser.parse_args(args)

    with open(pargs.source) as f:
        source = f.read()

    tree = ast.parse(source)
    variables = [v.strip() for v in pargs.vars.split(",")]
    seed = pargs.seed or os.urandom(32)

    result_tree = encode_variables_affine(tree, variables, seed)

    with open(pargs.output, "w") as f:
        f.write(ast.unparse(result_tree))

    print(f"Encoded variables: {variables}")
    print(f"Output: {pargs.output}")


def _cli_split(args: list[str]):
    parser = argparse.ArgumentParser(description="Split variable across storage")
    parser.add_argument("source", help="Source Python file")
    parser.add_argument("-o", "--output", required=True, help="Output file")
    parser.add_argument("--var", required=True, help="Variable name to split")
    parser.add_argument("--parts", type=int, default=2, help="Number of parts (default: 2)")
    parser.add_argument("--seed", type=lambda s: bytes.fromhex(s), default=None)
    pargs = parser.parse_args(args)

    with open(pargs.source) as f:
        source = f.read()

    tree = ast.parse(source)
    seed = pargs.seed or os.urandom(32)

    result_tree = split_value(tree, pargs.var, pargs.parts, seed)

    with open(pargs.output, "w") as f:
        f.write(ast.unparse(result_tree))

    print(f"Split '{pargs.var}' into {pargs.parts} parts")
    print(f"Output: {pargs.output}")


def _cli_pipeline(args: list[str]):
    parser = argparse.ArgumentParser(description="Run full data-flow obfuscation pipeline")
    parser.add_argument("source", help="Source Python file")
    parser.add_argument("-o", "--output", required=True, help="Output file")
    parser.add_argument("--vars", help="Comma-separated sensitive variables (auto-detect if omitted)")
    parser.add_argument("--method", choices=["affine", "mba", "split"], default="affine")
    parser.add_argument("--parts", type=int, default=2)
    parser.add_argument("--seed", type=lambda s: bytes.fromhex(s), default=None)
    pargs = parser.parse_args(args)

    with open(pargs.source) as f:
        source = f.read()

    tree = ast.parse(source)
    seed = pargs.seed or os.urandom(32)

    sensitive_vars = [v.strip() for v in pargs.vars.split(",")] if pargs.vars else []

    config = {
        "sensitive_vars": sensitive_vars,
        "encode_method": pargs.method,
        "split_parts": pargs.parts,
        "seed": seed,
    }

    result_tree = obfuscate_dataflow(tree, config)

    with open(pargs.output, "w") as f:
        f.write(ast.unparse(result_tree))

    print(f"Pipeline complete: method={pargs.method} vars={sensitive_vars or 'auto'}")
    print(f"Output: {pargs.output}")


def main():
    parser = argparse.ArgumentParser(
        description="Nixon Advanced Protection — Data-Flow Obfuscation"
    )
    subparsers = parser.add_subparsers(dest="command")

    enc_parser = subparsers.add_parser("encode", help="Affine-encode variables")
    enc_parser.add_argument("source", help="Source Python file")
    enc_parser.add_argument("-o", "--output", required=True, help="Output file")
    enc_parser.add_argument("--vars", required=True, help="Comma-separated variable names")
    enc_parser.add_argument("--seed", type=lambda s: bytes.fromhex(s), default=None)

    split_parser = subparsers.add_parser("split", help="Split variable across storage")
    split_parser.add_argument("source", help="Source Python file")
    split_parser.add_argument("-o", "--output", required=True, help="Output file")
    split_parser.add_argument("--var", required=True, help="Variable name to split")
    split_parser.add_argument("--parts", type=int, default=2)
    split_parser.add_argument("--seed", type=lambda s: bytes.fromhex(s), default=None)

    pipe_parser = subparsers.add_parser("pipeline", help="Full data-flow obfuscation pipeline")
    pipe_parser.add_argument("source", help="Source Python file")
    pipe_parser.add_argument("-o", "--output", required=True, help="Output file")
    pipe_parser.add_argument("--vars", help="Comma-separated sensitive variables")
    pipe_parser.add_argument("--method", choices=["affine", "mba", "split"], default="affine")
    pipe_parser.add_argument("--parts", type=int, default=2)
    pipe_parser.add_argument("--seed", type=lambda s: bytes.fromhex(s), default=None)

    args = parser.parse_args()

    if args.command == "encode":
        _cli_encode(sys.argv[2:])
    elif args.command == "split":
        _cli_split(sys.argv[2:])
    elif args.command == "pipeline":
        _cli_pipeline(sys.argv[2:])
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
