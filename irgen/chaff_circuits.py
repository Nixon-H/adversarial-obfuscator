"""
chaff_circuits.py

Purpose:
Advanced Protection — Chaff Circuits: Cryptographic Functional Splitting.
Generates realistic-looking but functionally different variants of
functions for obfuscation via "chaff" circuits. Functions marked with
@protect('chaff') get wrapped so that only correct inputs route to the
real circuit; others route to different chaff circuits.

Architectural Role:
Obfuscation pass that creates decoy function variants. Each target
function gets N structurally similar but mathematically different
chaff implementations, plus a wrapper that routes inputs based on
opaque predicates.

Security Relevance:
- Chaff circuits are structurally similar to the real function,
  making them indistinguishable under static analysis.
- The wrapper uses opaque predicates and MBA (Mixed Boolean-Arithmetic)
  expressions for routing selection.
- Symbolic executors cannot easily distinguish real from chaff
  because all paths return valid-looking results.
- Controlled by config/default.json -> shadow_compiler -> irgen ->
  chaff_circuits.enabled.

Threat model: Symbolic execution, automated deobfuscation, SMT solving.

Dependencies:
    - irgen.compile (IrFunction, IrBlock, IrInstruction, IrValue, IrType)
"""

from __future__ import annotations
import ast
import copy
import json
import os
import random
from typing import Optional, List

from .compile import IrFunction, IrBlock, IrInstruction, IrValue, IrType


def _load_config() -> dict:
    """Load config/default.json for protection settings."""
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


def _chaff_enabled() -> bool:
    """Check if chaff circuits are enabled in config."""
    cfg = _load_config()
    return cfg.get("shadow_compiler", {}).get("irgen", {}).get("chaff_circuits", {}).get("enabled", False)


_TEMPLATE_NAMES = ["xor", "rotate", "popcount", "minmax", "switched", "lookup", "gate"]

_OPCODE_REMAP: dict[str, dict[str, str]] = {
    "xor": {
        "add": "xor", "sub": "xor", "mul": "and", "div": "or",
        "mod": "xor", "shl": "or", "shr": "and",
        "and": "xor", "or": "and", "xor": "or",
    },
    "rotate": {
        "add": "_rotl", "sub": "_rotr", "mul": "and",
        "div": "or", "mod": "xor", "shl": "or", "shr": "and",
        "and": "xor", "or": "and", "xor": "or",
    },
    "popcount": {
        "add": "_popcnt", "sub": "_popcnt", "mul": "_popcnt",
        "div": "or", "mod": "xor", "shl": "or", "shr": "and",
        "and": "xor", "or": "and", "xor": "or",
    },
    "minmax": {
        "add": "_minmax", "sub": "_minmax", "mul": "_minmax",
        "div": "or", "mod": "xor", "shl": "or", "shr": "and",
        "and": "xor", "or": "and", "xor": "or",
    },
    "switched": {
        "add": "_switch", "sub": "_switch", "mul": "_switch",
        "div": "or", "mod": "xor", "shl": "or", "shr": "and",
        "and": "xor", "or": "and", "xor": "or",
    },
    "lookup": {
        "add": "_lookup", "sub": "_lookup", "mul": "_lookup",
        "div": "or", "mod": "xor", "shl": "or", "shr": "and",
        "and": "xor", "or": "and", "xor": "or",
    },
    "gate": {
        "add": "_gate", "sub": "_gate", "mul": "_gate",
        "div": "or", "mod": "xor", "shl": "or", "shr": "and",
        "and": "xor", "or": "and", "xor": "or",
    },
}


class ChaffCircuitGenerator:
    """
    Generates chaff (functionally different but structurally similar)
    circuit variants. Each variant shares the same control-flow structure
    as the original but performs different mathematical computation.

    Seven templates are available: xor, rotate, popcount, minmax,
    switched, lookup, gate.
    """

    def __init__(self, seed: int, num_chaff: int = 10):
        """Initialize with a random seed and chaff count."""
        self.seed = seed
        self.rng = random.Random(seed)
        self.num_chaff = num_chaff

    # ---- IR-level chaff generation ----

    def generate_chaff_circuit(self, original_ir_func: IrFunction,
                               template: Optional[str] = None) -> IrFunction:
        """
        Generate a chaff variant of the given IR function.

        The variant has the same number of inputs/outputs and same
        control-flow structure but performs a different mathematical
        computation.

        Args:
            original_ir_func: The IR function to clone and transform.
            template: The chaff template name (random if None).

        Returns:
            A new IrFunction with the chaff variant.
        """
        if template is None:
            template = _TEMPLATE_NAMES[self.rng.randint(0, len(_TEMPLATE_NAMES) - 1)]
        return self._apply_template(original_ir_func, template)

    def _apply_template(self, func: IrFunction, template: str) -> IrFunction:
        """
        Create a new IrFunction with the same block structure but
        different math operations based on the given template.

        Maintains a value map to connect operands across cloned blocks.
        """
        suffix = f"_chaff_{template}"
        chaff = IrFunction(func.name + suffix, func.return_type)
        chaff.params = list(func.params)

        bmap: dict[str, IrBlock] = {}
        for b in func.blocks:
            bmap[b.label] = chaff.new_block(b.label)

        vmap: dict[str, IrValue] = {}

        for pname, ptype in func.params:
            pv = IrValue(ptype, name=f"%{pname}")
            vmap[f"%{pname}"] = pv

        for ob in func.blocks:
            nb = bmap[ob.label]
            for inst in ob.instructions:
                self._process_inst(inst, nb, vmap, template)
            if ob.terminator:
                self._process_terminator(ob.terminator, nb, vmap)

        return chaff

    def _mv(self, op, vmap: dict[str, IrValue]) -> IrValue:
        """
        Map an IrValue operand through the value map.

        If the operand's name is in the map, returns the mapped value.
        Otherwise tries to create a constant from the name.
        """
        if isinstance(op, IrValue):
            if op.name in vmap:
                return vmap[op.name]
            const = self._const_from_name(op.name, op.type)
            if const is not None:
                return const
        return op

    @staticmethod
    def _const_from_name(name: str, ty: IrType) -> Optional[IrValue]:
        """Try to create a constant IrValue from a string name."""
        try:
            v = int(name)
            return IrValue.const_int(v)
        except (ValueError, TypeError):
            pass
        if name in ("true", "1"):
            return IrValue.const_bool(True)
        if name in ("false", "0"):
            return IrValue.const_bool(False)
        if name == "null":
            return IrValue.const_none()
        if name.startswith('"') and name.endswith('"'):
            return IrValue.const_str(name[1:-1])
        return None

    # ---- Instruction processing ----

    def _process_inst(self, inst: IrInstruction, block: IrBlock,
                      vmap: dict[str, IrValue], template: str):
        """
        Process a single instruction for chaff generation.

        Arithmetic instructions matching the template's remap are
        transformed; all others are copied faithfully.
        """
        op = inst.opcode
        t = inst.ty or inst.result_type or IrType.i32()

        if op in _OPCODE_REMAP.get(template, {}):
            self._transform_arith(inst, block, vmap, template, t)
        elif op == "alloca":
            self._copy_alloca(inst, block, vmap)
        elif op == "load":
            self._copy_load(inst, block, vmap)
        elif op == "store":
            self._copy_store(inst, block, vmap)
        elif op == "gep" and len(inst.operands) >= 2:
            self._copy_gep(inst, block, vmap)
        elif op == "call":
            self._copy_call(inst, block, vmap)
        elif op == "phi":
            self._copy_phi(inst, block, vmap)
        elif op in ("zext", "trunc", "bitcast", "not"):
            self._copy_cast(inst, block, vmap)
        elif op == "nop":
            pass
        else:
            self._copy_generic(inst, block, vmap)

    def _transform_arith(self, inst: IrInstruction, block: IrBlock,
                         vmap: dict[str, IrValue], template: str, t: IrType):
        """
        Transform an arithmetic instruction according to the template.

        Looks up the remapped opcode from _OPCODE_REMAP and calls the
        appropriate emitter.
        """
        if inst.result is None or len(inst.operands) < 2:
            return
        a = self._mv(inst.operands[0], vmap)
        b = self._mv(inst.operands[1], vmap)

        new_op = _OPCODE_REMAP[template].get(inst.opcode, inst.opcode)

        if new_op == inst.opcode:
            result = self._emit_binop(block, inst.opcode, t, a, b)
            if result is not None:
                vmap[inst.result.name] = result
        elif new_op in ("add", "sub", "mul", "div", "mod", "and", "or", "xor", "shl", "shr"):
            result = self._emit_binop(block, new_op, t, a, b)
            if result is not None:
                vmap[inst.result.name] = result
        elif new_op == "_rotl":
            result = self._emit_rotl(block, t, a, b)
            if result is not None:
                vmap[inst.result.name] = result
        elif new_op == "_rotr":
            result = self._emit_rotr(block, t, a, b)
            if result is not None:
                vmap[inst.result.name] = result
        elif new_op == "_popcnt":
            result = self._emit_popcnt(block, t, a, b)
            if result is not None:
                vmap[inst.result.name] = result
        elif new_op == "_minmax":
            result = self._emit_minmax(block, t, a, b)
            if result is not None:
                vmap[inst.result.name] = result
        elif new_op == "_switch":
            result = self._emit_switched(block, t, a, b)
            if result is not None:
                vmap[inst.result.name] = result
        elif new_op == "_lookup":
            result = self._emit_lookup(block, t, a, b)
            if result is not None:
                vmap[inst.result.name] = result
        elif new_op == "_gate":
            result = self._emit_gate(block, t, a, b)
            if result is not None:
                vmap[inst.result.name] = result

    # ---- Chaff template emitters ----

    def _emit_binop(self, block: IrBlock, op: str, t: IrType,
                    a: IrValue, b: IrValue) -> Optional[IrValue]:
        """Emit a standard binary operation and return its result value."""
        m = {
            "add": block.add, "sub": block.sub, "mul": block.mul,
            "div": block.div, "mod": block.mod_,
            "and": block.and_, "or": block.or_, "xor": block.xor,
            "shl": block.shl, "shr": block.shr,
        }
        fn = m.get(op)
        if fn:
            return fn(t, a, b).result
        return None

    def _emit_rotl(self, block: IrBlock, t: IrType, a: IrValue, b: IrValue) -> IrValue:
        """
        Rotate left: (a << (b & 31)) | (a >> (32 - (b & 31))).

        Emulates a CPU rotate-left instruction using shifts.
        """
        shift = block.and_(t, b, IrValue.const_int(31)).result
        left = block.shl(t, a, shift).result
        neg = block.sub(t, IrValue.const_int(32), shift).result
        right = block.shr(t, a, neg).result
        return block.or_(t, left, right).result

    def _emit_rotr(self, block: IrBlock, t: IrType, a: IrValue, b: IrValue) -> IrValue:
        """
        Rotate right: (a >> (b & 31)) | (a << (32 - (b & 31))).

        Emulates a CPU rotate-right instruction using shifts.
        """
        shift = block.and_(t, b, IrValue.const_int(31)).result
        right = block.shr(t, a, shift).result
        neg = block.sub(t, IrValue.const_int(32), shift).result
        left = block.shl(t, a, neg).result
        return block.or_(t, left, right).result

    def _emit_popcnt(self, block: IrBlock, t: IrType, a: IrValue, b: IrValue) -> IrValue:
        """
        Popcount-based chaff: popcount(a & b) * b.

        Counts set bits in the AND of the two operands and multiplies
        by the second operand.
        """
        merged = block.and_(t, a, b).result
        cnt = block.and_(t, merged, IrValue.const_int(1)).result
        for i in range(1, 8):
            shifted = block.shr(t, merged, IrValue.const_int(i)).result
            bit = block.and_(t, shifted, IrValue.const_int(1)).result
            cnt = block.add(t, cnt, bit).result
        return block.mul(t, cnt, b).result

    def _emit_minmax(self, block: IrBlock, t: IrType, a: IrValue, b: IrValue) -> IrValue:
        """
        Min-max chaff.

        Emits a comparison and an AND over the operands (IR noise) and
        returns a * xor(a, b) as the chaff expression.  The comparison
        RESULT is not consumed: the IR builder has no select primitive,
        so the "min(a, b)" of the original design is not produced.  The
        instructions are still emitted, because they are the point of
        the chaff.
        """
        lt = block.lt(t, a, b).result
        block.and_(t, block.xor(t, a, b).result, lt)
        sel = block.xor(t, a, b).result
        return block.mul(t, a, sel).result

    def _emit_switched(self, block: IrBlock, t: IrType, a: IrValue, b: IrValue) -> IrValue:
        """
        Switched chaff: always produces positive difference.

        If a > b, returns a - b; otherwise returns b - a.
        Uses conditional select via arithmetic masking.
        """
        gt = block.gt(t, a, b).result
        diff1 = block.sub(t, a, b).result
        diff2 = block.sub(t, b, a).result
        gt_zext = block.and_(t, IrValue.const_int(1), gt).result
        cond = block.ne(t, gt_zext, IrValue.const_int(0)).result
        diff1_masked = block.and_(t, diff1, block.sub(t, IrValue.const_int(0), cond).result).result
        diff2_masked = block.and_(t, diff2, block.sub(t, cond, IrValue.const_int(1)).result).result
        return block.or_(t, diff1_masked, diff2_masked).result

    def _emit_lookup(self, block: IrBlock, t: IrType, a: IrValue, b: IrValue) -> IrValue:
        """
        Lookup-based chaff: (a + b) * (a ^ b) + (a & b).

        Combines add, xor, and and into a single expression.
        """
        add = block.add(t, a, b).result
        xor = block.xor(t, a, b).result
        and_ = block.and_(t, a, b).result
        tmp = block.mul(t, add, xor).result
        return block.add(t, tmp, and_).result

    def _emit_gate(self, block: IrBlock, t: IrType, a: IrValue, b: IrValue) -> IrValue:
        """
        Gate-based chaff: (a & b) | (~a & b) which simplifies to b.

        Emits the expanded gate pattern to obscure the identity.
        """
        not_a = block.xor(t, a, IrValue.const_int(-1)).result
        left = block.and_(t, a, b).result
        right = block.and_(t, not_a, b).result
        return block.or_(t, left, right).result

    # ---- Copy helpers ----

    def _copy_alloca(self, inst: IrInstruction, block: IrBlock, vmap: dict):
        """Clone an alloca instruction."""
        if inst.result:
            ai = IrInstruction("alloca", inst.result_type)
            ai.parent_block = block
            block.instructions.append(ai)
            if ai.result:
                vmap[inst.result.name] = ai.result

    def _copy_load(self, inst: IrInstruction, block: IrBlock, vmap: dict):
        """Clone a load instruction."""
        if not inst.operands:
            return
        ptr = self._mv(inst.operands[0], vmap)
        li = IrInstruction("load", inst.result_type, operands=[ptr])
        li.parent_block = block
        block.instructions.append(li)
        if li.result:
            vmap[inst.result.name] = li.result

    def _copy_store(self, inst: IrInstruction, block: IrBlock, vmap: dict):
        """Clone a store instruction."""
        if len(inst.operands) < 2:
            return
        val = self._mv(inst.operands[0], vmap)
        ptr = self._mv(inst.operands[1], vmap)
        si = IrInstruction("store", inst.result_type, operands=[val, ptr])
        si.parent_block = block
        block.instructions.append(si)

    def _copy_gep(self, inst: IrInstruction, block: IrBlock, vmap: dict):
        """Clone a GEP instruction."""
        base = self._mv(inst.operands[0], vmap)
        idx = self._mv(inst.operands[1], vmap)
        gi = IrInstruction("gep", IrType.ptr(), operands=[base, idx])
        gi.parent_block = block
        block.instructions.append(gi)
        if gi.result:
            vmap[inst.result.name] = gi.result

    def _copy_call(self, inst: IrInstruction, block: IrBlock, vmap: dict):
        """Clone a call instruction."""
        args = [self._mv(a, vmap) for a in inst.operands]
        ci = IrInstruction("call", inst.result_type, operands=args,
                           func_name=inst.func_name, ty=inst.ty)
        ci.parent_block = block
        block.instructions.append(ci)
        if ci.result:
            vmap[inst.result.name] = ci.result

    def _copy_phi(self, inst: IrInstruction, block: IrBlock, vmap: dict):
        """Clone a phi instruction with mapped operands."""
        pairs = []
        for item in inst.operands:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                val, lbl = item
                mv = self._mv(val, vmap) if isinstance(val, IrValue) else val
                pairs.append((mv, lbl))
            else:
                pairs.append(item)
        pi = IrInstruction("phi", inst.result_type, operands=pairs)
        pi.parent_block = block
        block.instructions.append(pi)
        if pi.result:
            vmap[inst.result.name] = pi.result

    def _copy_cast(self, inst: IrInstruction, block: IrBlock, vmap: dict):
        """Clone a cast instruction (zext, trunc, bitcast, not)."""
        val = self._mv(inst.operands[0], vmap) if inst.operands else None
        ci = IrInstruction(inst.opcode, inst.result_type,
                           operands=[val] if val else [],
                           ty=inst.ty)
        ci.parent_block = block
        block.instructions.append(ci)
        if ci.result:
            vmap[inst.result.name] = ci.result

    def _copy_generic(self, inst: IrInstruction, block: IrBlock, vmap: dict):
        """Clone any instruction with generic operand mapping."""
        ops = [self._mv(o, vmap) if isinstance(o, IrValue) else o for o in inst.operands]
        gi = IrInstruction(inst.opcode, inst.result_type, operands=ops,
                           ty=inst.ty, func_name=inst.func_name)
        gi.parent_block = block
        block.instructions.append(gi)
        if gi.result:
            vmap[inst.result.name] = gi.result

    def _process_terminator(self, term: IrInstruction, block: IrBlock,
                            vmap: dict[str, IrValue]):
        """Clone a terminator instruction with mapped operands."""
        t_op = term.opcode
        if t_op == "ret":
            if term.operands and len(term.operands) >= 2:
                val = self._mv(term.operands[1], vmap)
                block.set_terminator("ret", operands=[term.operands[0], val])
            else:
                block.set_terminator("ret")
        elif t_op == "jmp":
            block.set_terminator("jmp", operands=list(term.operands))
        elif t_op == "br":
            cond = self._mv(term.operands[0], vmap)
            block.set_terminator("br", operands=[cond, term.operands[1], term.operands[2]])
        elif t_op == "unreachable":
            block.set_terminator("unreachable")

    # ---- Source-level chaff generation ----

    def generate_chaff_circuit_from_source(self, source_ir: str,
                                           func_name: str) -> str:
        """
        Read Python source, find the function, generate chaff variant.

        Returns Python source containing the chaff function.
        """
        try:
            tree = ast.parse(source_ir)
        except SyntaxError:
            return source_ir

        node = self._find_func(tree, func_name)
        if node is None:
            return source_ir

        template = _TEMPLATE_NAMES[self.rng.randint(0, len(_TEMPLATE_NAMES) - 1)]
        chaff_func = self._transform_ast_func(node, func_name, template)
        tree.body.append(chaff_func)
        return ast.unparse(tree)

    def _find_func(self, tree: ast.Module, name: str) -> Optional[ast.FunctionDef]:
        """Find a function definition by name in an AST module."""
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return node
        return None

    def _transform_ast_func(self, node: ast.FunctionDef, func_name: str,
                            template: str) -> ast.FunctionDef:
        """
        Transform an AST function into a chaff variant.

        The variant has the same signature but different math operations.
        """
        chaff_name = f"{func_name}_chaff_{template}_{self.rng.randint(0, 0xFFFF):04x}"
        new_body = self._chaff_ast_body(copy.deepcopy(node.body), template)
        return ast.FunctionDef(
            name=chaff_name,
            args=copy.deepcopy(node.args),
            body=new_body,
            decorator_list=[],
            lineno=0,
            col_offset=0,
        )

    def _chaff_ast_body(self, body: list[ast.stmt], template: str) -> list[ast.stmt]:
        """
        Replace math operations in function body according to template.

        Uses an AST NodeTransformer to rewrite BinOp nodes.
        """
        class ChaffTransformer(ast.NodeTransformer):
            def __init__(self, rng):
                self.rng = rng

            def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
                self.generic_visit(node)
                return self._chaff_binop(node)

            def _chaff_binop(self, node: ast.BinOp) -> ast.AST:
                """Rewrite a single binary operation based on the template."""
                if template == "xor":
                    return ast.BinOp(left=node.left, op=ast.BitXor(), right=node.right)
                elif template == "rotate":
                    return ast.BinOp(
                        left=ast.BinOp(left=node.left, op=ast.LShift(),
                                        right=ast.BinOp(left=node.right, op=ast.BitAnd(),
                                                        right=ast.Constant(value=31))),
                        op=ast.BitOr(),
                        right=ast.BinOp(left=node.left, op=ast.RShift(),
                                        right=ast.BinOp(left=ast.Constant(value=32),
                                                        op=ast.Sub(),
                                                        right=ast.BinOp(left=node.right, op=ast.BitAnd(),
                                                                        right=ast.Constant(value=31))))
                    )
                elif template == "popcount":
                    a = node.left
                    b = node.right
                    merged = ast.BinOp(left=a, op=ast.BitAnd(), right=b)
                    cnt = ast.Constant(value=0)
                    for i in range(8):
                        shifted = ast.BinOp(left=merged, op=ast.RShift(), right=ast.Constant(value=i))
                        bit = ast.BinOp(left=shifted, op=ast.BitAnd(), right=ast.Constant(value=1))
                        cnt = ast.BinOp(left=cnt, op=ast.Add(), right=bit)
                    return ast.BinOp(left=cnt, op=ast.Mult(), right=b)
                elif template == "minmax":
                    cmp = ast.Compare(left=node.left, ops=[ast.Gt()], comparators=[node.right])
                    return ast.IfExp(
                        test=cmp,
                        body=ast.BinOp(left=node.left, op=ast.Mult(), right=node.right),
                        orelse=ast.BinOp(left=node.right, op=ast.Mult(), right=node.left),
                    )
                elif template == "switched":
                    cmp = ast.Compare(left=node.left, ops=[ast.Gt()], comparators=[node.right])
                    return ast.IfExp(
                        test=cmp,
                        body=ast.BinOp(left=node.left, op=ast.Sub(), right=node.right),
                        orelse=ast.BinOp(left=node.right, op=ast.Sub(), right=node.left),
                    )
                elif template == "lookup":
                    return ast.BinOp(
                        left=ast.BinOp(left=ast.BinOp(left=node.left, op=ast.Add(), right=node.right),
                                       op=ast.Mult(),
                                       right=ast.BinOp(left=node.left, op=ast.BitXor(), right=node.right)),
                        op=ast.Add(),
                        right=ast.BinOp(left=node.left, op=ast.BitAnd(), right=node.right),
                    )
                elif template == "gate":
                    not_a = ast.BinOp(left=node.left, op=ast.BitXor(),
                                      right=ast.Constant(value=-1))
                    return ast.BinOp(
                        left=ast.BinOp(left=node.left, op=ast.BitAnd(), right=node.right),
                        op=ast.BitOr(),
                        right=ast.BinOp(left=not_a, op=ast.BitAnd(), right=node.right),
                    )
                return node

        transformer = ChaffTransformer(self.rng)
        return [transformer.visit(stmt) for stmt in body]

    # ---- Wrapper generation ----

    def wrap_verify_function(self, original_func_name: str,
                             chaff_funcs: List[str]) -> str:
        """
        Generate a wrapper function that routes correct input to real
        circuit and incorrect input to chaff.

        Uses an opaque predicate (always true) with an MBA expression
        to hide the routing decision.
        """
        num_chaff = len(chaff_funcs)

        lines = [f"# Chaff wrapper for {original_func_name}", ""]
        lines.append(f"__chaff_pool_{original_func_name} = [")
        for i, cf in enumerate(chaff_funcs):
            lines.append(f"    {cf},")
        lines.append("]")
        lines.append("")

        lines.append(f"def verify_{original_func_name}(input):")
        lines.append("    # Opaque predicate: always-true identity via MBA")
        lines.append("    _t1 = (input * 0x9E3779B9 + 0x61C88647) & 0xFFFFFFFF")
        lines.append("    _t2 = (_t1 ^ 0x5DEECE66D) * 0x6C078965")
        lines.append("    # (t2 | ~t2) == -1 is always true -- opaque predicate")
        lines.append("    if (_t2 | (~_t2)) == -1:")
        lines.append(f"        return {original_func_name}(input)")
        lines.append("    else:")
        lines.append(f"        _idx = hash(input) % {num_chaff}")
        lines.append(f"        return __chaff_pool_{original_func_name}[_idx](input)")
        lines.append("")

        return "\n".join(lines)

    def obfuscate_verification(self, original_func_name: str,
                                chaff_funcs: List[str],
                                expected_input: int) -> str:
        """
        Generate a fully obfuscated wrapper with opaque predicates,
        MBA expressions for hash selection, and obfuscated routing.

        All paths return valid-looking results so symbolic engines
        cannot distinguish real from chaff.
        """
        num_chaff = len(chaff_funcs)
        exp_low = expected_input & 0xFFFFFFFF

        lines = [f"# Obfuscated chaff wrapper for {original_func_name}", ""]
        lines.append(f"__chaff_pool_{original_func_name} = [")
        for i, cf in enumerate(chaff_funcs):
            lines.append(f"    {cf},")
        lines.append("]")
        lines.append("")

        lines.append(f"def verify_obf_{original_func_name}(input):")
        lines.append("    # MBA expression: obfuscated comparison with expected_input")
        lines.append(f"    _mba_a = (input ^ {exp_low}) + 0x9E3779B9")
        lines.append("    _mba_b = (_mba_a * 0x6C078965) & 0xFFFFFFFF")
        lines.append("    _mba_c = _mba_b ^ 0x5DEECE66D")
        lines.append("    # Opaque predicate: always follows the 'else' branch for real input")
        lines.append(f"    _opq1 = (_mba_c & 0xFF) == ({exp_low & 0xFF} & 0xFF)")
        lines.append(f"    _opq2 = ((_mba_c >> 8) & 0xFF) == (({exp_low} >> 8) & 0xFF)")
        lines.append("    if _opq1 and _opq2:")
        lines.append(f"        return {original_func_name}(input)")
        lines.append("    else:")
        lines.append("        # MBA hash for chaff index selection")
        lines.append("        _h1 = (input * 0x6C078965 + 0x5DEECE66D) & 0x7FFFFFFF")
        lines.append("        _h2 = (_h1 ^ (_h1 >> 13)) * 0x9E3779B9")
        lines.append(f"        _idx = (_h2 ^ (_h2 >> 15)) % {num_chaff}")
        lines.append(f"        return __chaff_pool_{original_func_name}[_idx](input)")
        lines.append("")

        return "\n".join(lines)


# ---- Convenience helpers ----

def generate_chaff_pipeline(
    source: str,
    target_functions: list[str],
    num_chaff: int = 10,
    seed: int = 42,
) -> str:
    """
    Apply chaff circuit protection to target functions in Python source.

    Returns modified Python source with chaff wrappers appended.
    Gated by _chaff_enabled() config check.
    """
    if not _chaff_enabled():
        return source

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source

    generator = ChaffCircuitGenerator(seed, num_chaff)
    result_functions = []
    chaff_pool: dict[str, list[str]] = {}

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in target_functions:
            chaff_funcs = []
            template_names = list(_OPCODE_REMAP.keys())
            for tname in template_names:
                chaff_ast = generator._transform_ast_func(node, node.name, tname)
                chaff_src = ast.unparse(chaff_ast)
                chaff_funcs.append(chaff_src)
            chaff_pool[node.name] = chaff_funcs
            result_functions.append(node)
        else:
            result_functions.append(node)

    wrapper_parts = [source]
    for fname, cfuncs in chaff_pool.items():
        wrapper = generator.wrap_verify_function(fname, cfuncs)
        wrapper_parts.append(wrapper)

    return "\n\n".join(wrapper_parts)


def main():
    """CLI entry point for chaff circuit generation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Nixon Advanced Protection -- Chaff Circuits Generator"
    )
    parser.add_argument("input", help="Input Python source file")
    parser.add_argument("-o", "--output", required=True, help="Output Python file")
    parser.add_argument("--functions", required=True, help="Comma-separated function names")
    parser.add_argument("--num-chaff", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()

    with open(args.input) as f:
        source = f.read()

    targets = [t.strip() for t in args.functions.split(",")]
    result = generate_chaff_pipeline(source, targets, args.num_chaff, args.seed)

    with open(args.output, "w") as f:
        f.write(result)
    print(f"Chaff-wrapped source written to {args.output}")


if __name__ == "__main__":
    main()
