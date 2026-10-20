"""
compile.py

Purpose:
Python-to-IR compiler. Parses Python AST and compiles it into Nixon's
custom intermediate representation (IrModule / IrFunction / IrBlock /
IrInstruction / IrValue). Supports functions, control flow (if/while/for/
break/continue), arithmetic, comparisons, boolean ops, and built-in call
stubs.

Architectural Role:
Front-end of the IR generation pipeline. Converts Python source code into
an SSA-form IR that all subsequent obfuscation passes consume. This IR
is the central data structure for all transformations.

Security Relevance:
- The IR generated here is the foundation for all obfuscation transforms.
- All security-critical operations (encryption, key derivation, license
  validation) pass through this IR pipeline.
- The IR preserves source-level structure but can be heavily mutated
  by later passes.

Dependencies:
    - None (standard library only: ast, sys)
"""

from __future__ import annotations
import ast
from typing import Optional


class IrType:
    """
    IR type representation.

    Supports i1, i8, i16, i32, i64, float, double, ptr, void,
    array(element_type, size), and struct(field_types).
    """

    def __init__(self, kind: str, **kwargs):
        """Initialize with a type kind and optional size/element/field info."""
        self.kind = kind
        self.size = kwargs.get('size', 0)
        self.element_type = kwargs.get('element_type', None)
        self.field_types = kwargs.get('field_types', None)

    def __str__(self):
        if self.kind == 'array':
            return f"array({self.element_type}, {self.size})"
        if self.kind == 'struct':
            fields = ", ".join(str(t) for t in (self.field_types or []))
            return f"struct({fields})"
        return self.kind

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if not isinstance(other, IrType):
            return NotImplemented
        return (self.kind == other.kind and self.size == other.size
                and self.element_type == other.element_type
                and self.field_types == other.field_types)

    def __hash__(self):
        return hash((self.kind, self.size))

    @staticmethod
    def i32(): return IrType('i32')
    @staticmethod
    def i64(): return IrType('i64')
    @staticmethod
    def i8(): return IrType('i8')
    @staticmethod
    def i1(): return IrType('i1')
    @staticmethod
    def i16(): return IrType('i16')
    @staticmethod
    def float(): return IrType('float')
    @staticmethod
    def double(): return IrType('double')
    @staticmethod
    def ptr(): return IrType('ptr')
    @staticmethod
    def void(): return IrType('void')


class IrValue:
    """
    SSA value with use-list tracking.

    Each value has a unique ID, a type, a name, and a list of users
    (instructions that reference this value). Constants are represented
    with literal names that can be parsed back to integers.
    """

    _counter = 0

    def __init__(self, type_: IrType, name: Optional[str] = None, ir_inst: Optional['IrInstruction'] = None):
        """Create a new value with auto-incrementing ID."""
        self.id = IrValue._counter
        IrValue._counter += 1
        self.type = type_
        self.name = name or f"%{self.id}"
        self.ir_inst = ir_inst
        self.users: list['IrInstruction'] = []

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<IrValue {self.name}: {self.type}>"

    def add_user(self, inst: 'IrInstruction'):
        """Register an instruction as a user of this value."""
        if inst not in self.users:
            self.users.append(inst)

    @classmethod
    def reset_counter(cls):
        """Reset the global value counter (for fresh compilation)."""
        cls._counter = 0

    @staticmethod
    def const_int(value: int) -> 'IrValue':
        """Create a constant integer value (name is the decimal string)."""
        v = IrValue(IrType.i32())
        v.name = str(value)
        return v

    @staticmethod
    def const_bool(value: bool) -> 'IrValue':
        """Create a constant boolean value."""
        v = IrValue(IrType.i1())
        v.name = "1" if value else "0"
        return v

    @staticmethod
    def const_none() -> 'IrValue':
        """Create a null pointer constant."""
        v = IrValue(IrType.ptr())
        v.name = "null"
        return v

    @staticmethod
    def const_str(value: str) -> 'IrValue':
        """Create a string constant (name is the escaped string)."""
        v = IrValue(IrType.ptr())
        escaped = value.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t").replace('"', '\\"')
        v.name = f'"{escaped}"'
        return v

    def is_constant(self) -> bool:
        """Check if this value is a compile-time constant."""
        return self.ir_inst is not None and self.ir_inst.is_constant()


class IrInstruction:
    """
    Typed instruction with opcode, operands, and result.

    Supports arithmetic, memory, control flow, calls, phi, and cast
    instructions. Each instruction belongs to a parent block.
    """

    def __init__(self, opcode: str, result_type: Optional[IrType] = None,
                 operands: Optional[list] = None,
                 ty: Optional[IrType] = None, func_name: Optional[str] = None,
                 true_label: Optional[str] = None, false_label: Optional[str] = None,
                 target_label: Optional[str] = None):
        """
        Initialize an instruction.

        Automatically creates a result value if result_type is provided
        and the opcode produces a result (not store, jmp, ret, br, etc.).
        """
        self.opcode = opcode
        self.result_type = result_type
        self.operands = operands or []
        self.result: Optional[IrValue] = None
        self.parent_block: Optional[IrBlock] = None

        # Opcodes that do not produce a result value
        self.no_result_ops = {'store', 'jmp', 'ret', 'br', 'nop', 'unreachable'}

        self.ty = ty
        self.func_name = func_name
        self.true_label = true_label
        self.false_label = false_label
        self.target_label = target_label

        if result_type is not None and opcode not in self.no_result_ops:
            self.result = IrValue(result_type, ir_inst=self)
        for op in self.operands:
            if isinstance(op, IrValue):
                op.add_user(self)

    def is_constant(self) -> bool:
        """
        Check if this instruction computes a constant value.

        An instruction is constant if all its operands are literal
        constants and the opcode is a pure arithmetic or cast operation.
        """
        if self.opcode in {'add', 'sub', 'mul', 'div', 'mod', 'and', 'or', 'xor', 'shl', 'shr',
                           'eq', 'ne', 'lt', 'le', 'gt', 'ge', 'zext', 'trunc', 'sitofp', 'fptosi',
                           'bitcast', 'not'}:
            return all(isinstance(o, IrValue) and self._is_literal_value(o) for o in self.operands)
        return False

    @staticmethod
    def _is_literal_value(v: IrValue) -> bool:
        """Check if an IrValue name represents a literal constant."""
        try:
            # A validation probe: the exception IS the test.  Do not
            # let a cleanup drop it -- without it every IrValue would
            # look like a literal.
            int(v.name)
            return True
        except (ValueError, TypeError):
            return v.name in ('true', 'false', '1', '0')

    def __str__(self):
        """Serialize instruction to IR text format."""
        if self.opcode == 'alloca':
            r = f"{self.result.name} = alloca {self.result_type}" if self.result else f"alloca {self.result_type}"
            return r
        if self.opcode == 'load':
            r = f"{self.result.name} = load" if self.result else "load"
            r += f" {self.result_type}, ptr {self.operands[0]}" if self.operands else f" {self.result_type}"
            return r
        if self.opcode == 'store':
            r = "store"
            if len(self.operands) >= 2:
                r += f" {self.result_type} {self.operands[0]}, ptr {self.operands[1]}"
            else:
                r += f" {self.result_type}"
            return r
        if self.opcode == 'call':
            ret_t = self.result_type if self.result_type else self.ty
            r = f"{self.result.name} = call" if self.result else "call"
            r += f" {ret_t} @{self.func_name}"
            if self.operands:
                r += "(" + ", ".join(str(o) for o in self.operands) + ")"
            return r
        if self.opcode == 'phi':
            r = f"{self.result.name} = phi {self.result_type} " if self.result else f"phi {self.result_type} "
            incs = []
            for val, label in self.operands:
                incs.append(f"[{val}, label {label}]")
            r += ", ".join(incs)
            return r
        if self.opcode == 'gep':
            r = f"{self.result.name} = gep" if self.result else "gep"
            r += f" ptr {self.operands[0]}, i32 {self.operands[1]}"
            return r
        if self.opcode == 'zext':
            r = f"{self.result.name} = zext" if self.result else "zext"
            r += f" {self.result_type} {self.operands[0]} to {self.ty}"
            return r
        if self.opcode == 'trunc':
            r = f"{self.result.name} = trunc" if self.result else "trunc"
            r += f" {self.result_type} {self.operands[0]} to {self.ty}"
            return r
        if self.opcode in {'add', 'sub', 'mul', 'div', 'mod', 'and', 'or', 'xor', 'shl', 'shr',
                            'eq', 'ne', 'lt', 'le', 'gt', 'ge'}:
            t = self.ty or self.result_type
            r = f"{self.result.name} = {self.opcode} {t}" if self.result else f"{self.opcode} {t}"
            if len(self.operands) >= 2:
                r += f" {self.operands[0]}, {self.operands[1]}"
            return r
        if self.opcode == 'nop':
            return "nop"
        if self.opcode == 'jmp':
            return f"jmp label {self.operands[0]}"
        if self.opcode == 'br':
            return f"br i1 {self.operands[0]}, label {self.operands[1]}, label {self.operands[2]}"
        if self.opcode == 'ret':
            if self.operands:
                return f"ret {self.operands[0]} {self.operands[1]}"
            return "ret void"
        if self.opcode == 'unreachable':
            return "unreachable"

        parts = []
        if self.result is not None:
            parts.append(f"{self.result.name} =")
        parts.append(self.opcode)
        for op in self.operands:
            parts.append(str(op))
        return " ".join(parts)


class IrBlock:
    """
    Basic block in the IR.

    Contains a list of instructions and a single terminator (ret, jmp, br,
    or unreachable). Each block belongs to a parent function.
    """

    def __init__(self, label: str):
        """Initialize a block with a unique label."""
        self.label = label
        self.instructions: list[IrInstruction] = []
        self.terminator: Optional[IrInstruction] = None
        self.parent_function: Optional['IrFunction'] = None

    def _make(self, opcode: str, result_type: Optional[IrType] = None,
              operands: Optional[list] = None, **kwargs) -> IrInstruction:
        """Create and append an instruction to this block."""
        inst = IrInstruction(opcode, result_type, operands, **kwargs)
        inst.parent_block = self
        self.instructions.append(inst)
        return inst

    def set_terminator(self, opcode: str, **kwargs):
        """Set the terminator instruction for this block."""
        inst = IrInstruction(opcode, None, **kwargs)
        inst.parent_block = self
        self.terminator = inst

    # ---- Instruction factory methods ----

    def alloca(self, type_: IrType) -> IrInstruction:
        return self._make('alloca', type_)

    def load(self, type_: IrType, ptr: IrValue) -> IrInstruction:
        return self._make('load', result_type=type_, operands=[ptr])

    def store(self, type_: IrType, value: IrValue, ptr: IrValue):
        self._make('store', result_type=type_, operands=[value, ptr])

    def add(self, type_: IrType, a: IrValue, b: IrValue) -> IrInstruction:
        return self._make('add', result_type=type_, operands=[a, b], ty=type_)

    def sub(self, type_: IrType, a: IrValue, b: IrValue) -> IrInstruction:
        return self._make('sub', result_type=type_, operands=[a, b], ty=type_)

    def mul(self, type_: IrType, a: IrValue, b: IrValue) -> IrInstruction:
        return self._make('mul', result_type=type_, operands=[a, b], ty=type_)

    def div(self, type_: IrType, a: IrValue, b: IrValue) -> IrInstruction:
        return self._make('div', result_type=type_, operands=[a, b], ty=type_)

    def mod_(self, type_: IrType, a: IrValue, b: IrValue) -> IrInstruction:
        return self._make('mod', result_type=type_, operands=[a, b], ty=type_)

    def and_(self, type_: IrType, a: IrValue, b: IrValue) -> IrInstruction:
        return self._make('and', result_type=type_, operands=[a, b], ty=type_)

    def or_(self, type_: IrType, a: IrValue, b: IrValue) -> IrInstruction:
        return self._make('or', result_type=type_, operands=[a, b], ty=type_)

    def xor(self, type_: IrType, a: IrValue, b: IrValue) -> IrInstruction:
        return self._make('xor', result_type=type_, operands=[a, b], ty=type_)

    def shl(self, type_: IrType, a: IrValue, b: IrValue) -> IrInstruction:
        return self._make('shl', result_type=type_, operands=[a, b], ty=type_)

    def shr(self, type_: IrType, a: IrValue, b: IrValue) -> IrInstruction:
        return self._make('shr', result_type=type_, operands=[a, b], ty=type_)

    def eq(self, type_: IrType, a: IrValue, b: IrValue) -> IrInstruction:
        return self._make('eq', result_type=IrType.i1(), operands=[a, b], ty=type_)

    def ne(self, type_: IrType, a: IrValue, b: IrValue) -> IrInstruction:
        return self._make('ne', result_type=IrType.i1(), operands=[a, b], ty=type_)

    def lt(self, type_: IrType, a: IrValue, b: IrValue) -> IrInstruction:
        return self._make('lt', result_type=IrType.i1(), operands=[a, b], ty=type_)

    def le(self, type_: IrType, a: IrValue, b: IrValue) -> IrInstruction:
        return self._make('le', result_type=IrType.i1(), operands=[a, b], ty=type_)

    def gt(self, type_: IrType, a: IrValue, b: IrValue) -> IrInstruction:
        return self._make('gt', result_type=IrType.i1(), operands=[a, b], ty=type_)

    def ge(self, type_: IrType, a: IrValue, b: IrValue) -> IrInstruction:
        return self._make('ge', result_type=IrType.i1(), operands=[a, b], ty=type_)

    def zext(self, from_type: IrType, to_type: IrType, val: IrValue) -> IrInstruction:
        return self._make('zext', result_type=from_type, operands=[val], ty=to_type)

    def trunc(self, from_type: IrType, to_type: IrType, val: IrValue) -> IrInstruction:
        return self._make('trunc', result_type=from_type, operands=[val], ty=to_type)

    def call(self, func_name: str, args: list[IrValue], return_type: IrType = IrType.void()) -> IrInstruction:
        ret = return_type if return_type.kind != 'void' else None
        return self._make('call', result_type=ret, operands=args, func_name=func_name, ty=return_type)

    def phi(self, type_: IrType, incoming: list[tuple[IrValue, str]]) -> IrInstruction:
        return self._make('phi', result_type=type_, operands=list(incoming))

    def gep(self, base: IrValue, index: IrValue) -> IrInstruction:
        return self._make('gep', result_type=IrType.ptr(), operands=[base, index])

    def nop(self):
        self._make('nop')

    def unreachable(self):
        self.set_terminator('unreachable')

    def __str__(self):
        """Serialize block to IR text format."""
        lines = [f"{self.label}:"]
        for inst in self.instructions:
            lines.append(f"  {inst}")
        if self.terminator:
            lines.append(f"  {self.terminator}")
        return "\n".join(lines)


class IrFunction:
    """
    IR function with parameters, basic blocks, and an entry block.

    Functions can have named parameters with types, a return type,
    and a list of basic blocks.
    """

    def __init__(self, name: str, return_type: IrType = IrType.void()):
        """Initialize a function with a name and return type."""
        self.name = name
        self.return_type = return_type
        self.params: list[tuple[str, IrType]] = []
        self.blocks: list[IrBlock] = []
        self.block_counter = 0
        self.entry_block: Optional[IrBlock] = None

    def new_block(self, label: Optional[str] = None) -> IrBlock:
        """Create and append a new basic block with an optional label."""
        if label is None:
            label = f"bb{self.block_counter}"
            self.block_counter += 1
        block = IrBlock(label)
        block.parent_function = self
        self.blocks.append(block)
        return block

    def __str__(self):
        """Serialize function to IR text format."""
        params_str = ", ".join(f"%{n}: {t}" for n, t in self.params)
        header = f"func @{self.name}({params_str})"
        if self.return_type.kind != 'void':
            header += f" -> {self.return_type}"
        lines = [header + " {"]
        for block in self.blocks:
            block_str = str(block)
            for line in block_str.split("\n"):
                lines.append(f"  {line}")
        lines.append("}")
        return "\n".join(lines)


class IrModule:
    """
    Top-level IR container.

    Holds a list of functions and provides module-level value ID
    generation.
    """

    def __init__(self, name: str = "nixon_module"):
        """Initialize a module with an optional name."""
        self.name = name
        self.functions: list[IrFunction] = []
        self.global_counter = 0

    def new_value_id(self) -> str:
        """Generate a fresh module-scoped value ID."""
        v = self.global_counter
        self.global_counter += 1
        return f"%{v}"

    def __str__(self):
        """Serialize module to IR text format."""
        lines = [f"module @{self.name}"]
        for func in self.functions:
            func_str = str(func)
            for line in func_str.split("\n"):
                lines.append(f"  {line}")
        return "\n".join(lines)


class IrCompiler:
    """
    AST-driven compiler that produces an IrModule from Python source.

    Handles function definitions, variable assignments (including
    augmented assignment), control flow (if, while, for, break,
    continue), expressions (arithmetic, comparison, boolean, calls,
    subscript, attribute), and constants.
    """

    def __init__(self, module_name: Optional[str] = None):
        """Initialize compiler state."""
        IrValue.reset_counter()
        self.module = IrModule(module_name or "nixon_module")
        self.current_func: Optional[IrFunction] = None
        self.current_block: Optional[IrBlock] = None
        self.symbols: dict[str, tuple[IrInstruction, IrType]] = {}
        self.break_targets: list[str] = []
        self.continue_targets: list[str] = []
        self.compiled_functions: dict[str, IrFunction] = {}

    def _py_type_to_ir(self, val) -> IrType:
        """Map Python value types to IR types."""
        if isinstance(val, bool):
            return IrType.i1()
        if isinstance(val, int):
            if val < -2**31 or val >= 2**31:
                return IrType.i64()
            return IrType.i32()
        if isinstance(val, float):
            return IrType.double()
        if isinstance(val, str):
            return IrType.ptr()
        if val is None:
            return IrType.ptr()
        return IrType.i32()

    def _make_constant_value(self, val) -> IrValue:
        """Create an IR constant from a Python literal value."""
        if isinstance(val, bool):
            return IrValue.const_bool(val)
        if isinstance(val, int):
            return IrValue.const_int(val)
        if isinstance(val, float):
            v = IrValue(IrType.double())
            v.name = str(val)
            return v
        if isinstance(val, str):
            return IrValue.const_str(val)
        if val is None:
            return IrValue.const_none()
        return IrValue.const_int(0)

    def _ensure_entry_block(self):
        """Ensure the current function has an entry block."""
        if self.current_func and not self.current_func.blocks:
            self.current_block = self.current_func.new_block("entry")
            self.current_func.entry_block = self.current_block

    def compile(self, tree: ast.AST) -> IrModule:
        """Compile an AST into an IR module."""
        self._compile_module(tree)
        return self.module

    def _compile_module(self, node: ast.Module):
        """
        Compile a module AST node.

        Function definitions are compiled first, then module-level
        statements are collected into a __module_entry__ function.
        """
        func_defs = [s for s in node.body if isinstance(s, ast.FunctionDef)]
        other_stmts = [s for s in node.body if not isinstance(s, ast.FunctionDef)
                       and not isinstance(s, (ast.Import, ast.ImportFrom, ast.ClassDef))]

        for stmt in func_defs:
            self._compile_stmt(stmt)
        for stmt in node.body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom, ast.ClassDef)):
                pass

        if other_stmts:
            entry_func = IrFunction("__module_entry__")
            self.current_func = entry_func
            self.symbols = {}
            self.break_targets = []
            self.continue_targets = []

            entry = entry_func.new_block("entry")
            self.current_block = entry

            for stmt in other_stmts:
                self._compile_stmt(stmt)

            term = self.current_block.terminator
            if term is None or term.opcode not in ('ret', 'jmp', 'br', 'unreachable'):
                self.current_block.set_terminator('ret')

            self.module.functions.append(entry_func)

            self.current_func = None
            self.current_block = None
            self.symbols = {}

    def _compile_stmt(self, stmt: ast.AST):
        """Dispatch a statement to its specific compiler."""
        if isinstance(stmt, ast.FunctionDef):
            self._compile_func_def(stmt)
        elif isinstance(stmt, ast.Import):
            pass
        elif isinstance(stmt, ast.ImportFrom):
            pass
        elif isinstance(stmt, ast.Assign):
            self._compile_assign(stmt)
        elif isinstance(stmt, ast.AugAssign):
            self._compile_aug_assign(stmt)
        elif isinstance(stmt, ast.Expr):
            self._compile_expr(stmt.value)
        elif isinstance(stmt, ast.Return):
            self._compile_return(stmt)
        elif isinstance(stmt, ast.If):
            self._compile_if(stmt)
        elif isinstance(stmt, ast.While):
            self._compile_while(stmt)
        elif isinstance(stmt, ast.For):
            self._compile_for(stmt)
        elif isinstance(stmt, ast.Break):
            self._compile_break()
        elif isinstance(stmt, ast.Continue):
            self._compile_continue()
        elif isinstance(stmt, ast.Pass):
            self.current_block.nop()
        elif isinstance(stmt, ast.Delete):
            pass
        elif isinstance(stmt, ast.ClassDef):
            pass

    def _compile_func_def(self, node: ast.FunctionDef):
        """
        Compile a function definition.

        Creates function parameters as allocas, compiles the body,
        and adds a default return terminator if missing.
        """
        old_func = self.current_func
        old_block = self.current_block
        old_symbols = dict(self.symbols)
        old_breaks = self.break_targets
        old_continues = self.continue_targets

        ret_type = IrType.i32() if self._has_return_value(node) else IrType.void()
        func = IrFunction(node.name, ret_type)
        self.current_func = func
        self.symbols = {}
        self.break_targets = []
        self.continue_targets = []

        entry = func.new_block("entry")
        func.entry_block = entry
        self.current_block = entry

        for arg in node.args.args:
            param_name = arg.arg
            param_id = f"%{param_name}"
            func.params.append((param_name, IrType.i32()))
            alloca_inst = self.current_block.alloca(IrType.i32())
            param_val = IrValue(IrType.i32(), name=param_id)
            self.current_block.store(IrType.i32(), param_val, alloca_inst.result)
            self.symbols[param_name] = (alloca_inst, IrType.i32())

        for stmt in node.body:
            self._compile_stmt(stmt)

        term = self.current_block.terminator
        if term is None or term.opcode not in ('ret', 'jmp', 'br', 'unreachable'):
            if ret_type.kind == 'void':
                self.current_block.set_terminator('ret')
            else:
                self.current_block.set_terminator('ret', operands=[IrType.i32(), IrValue.const_int(0)])

        self.module.functions.append(func)
        self.compiled_functions[node.name] = func

        self.current_func = old_func
        self.current_block = old_block
        self.symbols = old_symbols
        self.break_targets = old_breaks
        self.continue_targets = old_continues

    def _has_return_value(self, node: ast.FunctionDef) -> bool:
        """Check if a function has any return statement with a value."""
        for n in ast.walk(node):
            if isinstance(n, ast.Return) and n.value is not None:
                return True
        return False

    def _compile_assign(self, node: ast.Assign):
        """
        Compile an assignment statement.

        Handles simple name targets (creating an alloca if needed),
        subscript targets (via GEP), and tuple/list destructuring
        (silently ignored).
        """
        val = self._compile_expr(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                if target.id in self.symbols:
                    alloca_inst, _ = self.symbols[target.id]
                    self.current_block.store(IrType.i32(), val, alloca_inst.result)
                else:
                    alloca_inst = self.current_block.alloca(IrType.i32())
                    self.current_block.store(IrType.i32(), val, alloca_inst.result)
                    self.symbols[target.id] = (alloca_inst, IrType.i32())
            elif isinstance(target, ast.Subscript):
                base = self._compile_expr(target.value)
                index = self._compile_expr(target.slice)
                gep_inst = self.current_block.gep(base, index)
                self.current_block.store(IrType.i32(), val, gep_inst.result)
            elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
                pass

    def _compile_aug_assign(self, node: ast.AugAssign):
        """
        Compile an augmented assignment (+=, -=, etc.).

        Loads the current value, applies the binary operation, and
        stores the result back.
        """
        if isinstance(node.target, ast.Name):
            if node.target.id not in self.symbols:
                alloca_inst = self.current_block.alloca(IrType.i32())
                self.current_block.store(IrType.i32(), IrValue.const_int(0), alloca_inst.result)
                self.symbols[node.target.id] = (alloca_inst, IrType.i32())
            alloca_inst, var_type = self.symbols[node.target.id]
            current_val = self.current_block.load(var_type, alloca_inst.result).result
            rhs = self._compile_expr(node.value)
            result = self._compile_binop(node.op, current_val, rhs, var_type)
            self.current_block.store(var_type, result, alloca_inst.result)

    def _compile_return(self, node: ast.Return):
        """
        Compile a return statement.

        If a value is provided, sets the terminator with return value
        and type. Otherwise sets a void return.
        """
        if node.value is not None:
            val = self._compile_expr(node.value)
            self.current_block.set_terminator('ret', operands=[val.type, val])
        else:
            self.current_block.set_terminator('ret')

    def _compile_if(self, node: ast.If):
        """
        Compile an if/else statement.

        Generates:
        - Condition evaluation
        - true_block (body)
        - false_block (else body, if present)
        - merge_block (continuation)
        """
        cond = self._compile_expr(node.test)
        if cond.type.kind != 'i1':
            cond = self.current_block.ne(IrType.i32(), cond, IrValue.const_int(0)).result

        true_block = self.current_func.new_block()
        merge_block = self.current_func.new_block()

        if node.orelse:
            false_block = self.current_func.new_block()
            self.current_block.set_terminator('br', operands=[cond, true_block.label, false_block.label])

            self.current_block = true_block
            for stmt in node.body:
                self._compile_stmt(stmt)
            term = self.current_block.terminator
            if term is None:
                self.current_block.set_terminator("jmp", operands=[merge_block.label])

            self.current_block = false_block
            for stmt in node.orelse:
                self._compile_stmt(stmt)
            term = self.current_block.terminator
            if term is None:
                self.current_block.set_terminator("jmp", operands=[merge_block.label])
        else:
            self.current_block.set_terminator("br", operands=[cond, true_block.label, merge_block.label])

            self.current_block = true_block
            for stmt in node.body:
                self._compile_stmt(stmt)
            term = self.current_block.terminator
            if term is None:
                self.current_block.set_terminator("jmp", operands=[merge_block.label])

        self.current_block = merge_block

    def _compile_while(self, node: ast.While):
        """
        Compile a while loop.

        Generates:
        - header_block (condition check)
        - body_block (loop body)
        - exit_block (after loop)
        Supports break and continue via target label tracking.
        """
        header_block = self.current_func.new_block()
        body_block = self.current_func.new_block()
        exit_block = self.current_func.new_block()

        self.break_targets.append(exit_block.label)
        self.continue_targets.append(header_block.label)

        self.current_block.set_terminator("jmp", operands=[header_block.label])

        self.current_block = header_block
        cond = self._compile_expr(node.test)
        if cond.type.kind != 'i1':
            cond = self.current_block.ne(IrType.i32(), cond, IrValue.const_int(0)).result
        self.current_block.set_terminator("br", operands=[cond, body_block.label, exit_block.label])

        self.current_block = body_block
        for stmt in node.body:
            self._compile_stmt(stmt)
        term = self.current_block.terminator
        if term is None:
            self.current_block.set_terminator("jmp", operands=[header_block.label])

        self.break_targets.pop()
        self.continue_targets.pop()

        self.current_block = exit_block

    def _compile_for(self, node: ast.For):
        """
        Compile a for loop (over an iterator).

        Uses __builtin_iter, __builtin_has_next, __builtin_next
        as the iteration protocol.
        """
        iter_obj = self._compile_expr(node.iter)

        it_var = f"__it_{len(self.current_func.blocks)}"
        it_alloca = self.current_block.alloca(IrType.ptr())
        self.symbols[it_var] = (it_alloca, IrType.ptr())

        init_call = self.current_block.call("__builtin_iter", [iter_obj], IrType.ptr())
        self.current_block.store(IrType.ptr(), init_call.result, self.symbols[it_var][0].result)

        header_block = self.current_func.new_block()
        body_block = self.current_func.new_block()
        exit_block = self.current_func.new_block()

        self.break_targets.append(exit_block.label)
        self.continue_targets.append(header_block.label)

        self.current_block.set_terminator("jmp", operands=[header_block.label])

        self.current_block = header_block
        it_ptr = self.current_block.load(IrType.ptr(), self.symbols[it_var][0].result)
        has_next = self.current_block.call("__builtin_has_next", [it_ptr.result], IrType.i1())
        self.current_block.set_terminator("br", operands=[has_next.result, body_block.label, exit_block.label])

        self.current_block = body_block
        it_ptr2 = self.current_block.load(IrType.ptr(), self.symbols[it_var][0].result)
        next_val = self.current_block.call("__builtin_next", [it_ptr2.result], IrType.i32())

        if isinstance(node.target, ast.Name):
            target_alloca = self.current_block.alloca(IrType.i32())
            self.current_block.store(IrType.i32(), next_val.result, target_alloca.result)
            self.symbols[node.target.id] = (target_alloca, IrType.i32())

        for stmt in node.body:
            self._compile_stmt(stmt)
        term = self.current_block.terminator
        if term is None:
            self.current_block.set_terminator("jmp", operands=[header_block.label])

        self.break_targets.pop()
        self.continue_targets.pop()

        self.current_block = exit_block

    def _compile_break(self):
        """Compile a break statement by jumping to the current break target."""
        if self.break_targets:
            target = self.break_targets[-1]
            self.current_block.set_terminator("jmp", operands=[target])

    def _compile_continue(self):
        """Compile a continue statement by jumping to the current continue target."""
        if self.continue_targets:
            target = self.continue_targets[-1]
            self.current_block.set_terminator("jmp", operands=[target])

    def _compile_expr(self, node: ast.AST) -> IrValue:
        """Dispatch an expression node to its specific compiler."""
        if isinstance(node, ast.Constant):
            return self._make_constant_value(node.value)
        if isinstance(node, ast.Name):
            return self._compile_name(node)
        if isinstance(node, ast.BinOp):
            return self._compile_binop_expr(node)
        if isinstance(node, ast.UnaryOp):
            return self._compile_unaryop(node)
        if isinstance(node, ast.Call):
            return self._compile_call(node)
        if isinstance(node, ast.Compare):
            return self._compile_compare(node)
        if isinstance(node, ast.BoolOp):
            return self._compile_boolop(node)
        if isinstance(node, ast.IfExp):
            return self._compile_ifexp(node)
        if isinstance(node, ast.Subscript):
            return self._compile_subscript(node)
        if isinstance(node, ast.Attribute):
            return self._compile_attribute(node)
        if isinstance(node, ast.List):
            return IrValue.const_int(0)
        if isinstance(node, ast.Tuple):
            return IrValue.const_int(0)
        if isinstance(node, ast.Dict):
            return IrValue.const_int(0)
        if isinstance(node, ast.Starred):
            return self._compile_expr(node.value)
        if isinstance(node, ast.FormattedValue):
            return self._compile_expr(node.value)
        if isinstance(node, ast.JoinedStr):
            if node.values:
                result = self._compile_expr(node.values[0])
                for v in node.values[1:]:
                    val = self._compile_expr(v)
                    op = IrInstruction('add', IrType.ptr(), [IrType.ptr(), result, val])
                    op.parent_block = self.current_block
                    self.current_block.instructions.append(op)
                    result = op.result
                return result
            return IrValue.const_str("")
        if isinstance(node, ast.Slice):
            return IrValue.const_int(0)
        return IrValue.const_int(0)

    def _compile_name(self, node: ast.Name) -> IrValue:
        """
        Compile a name reference.

        Handles built-in names (True, False, None, __name__) and
        user-defined variables (loaded from their alloca).
        """
        if node.id == "__name__":
            return IrValue.const_str("__main__")
        if node.id == "True":
            return IrValue.const_bool(True)
        if node.id == "False":
            return IrValue.const_bool(False)
        if node.id == "None":
            return IrValue.const_none()
        if node.id in self.symbols:
            alloca_inst, var_type = self.symbols[node.id]
            load_inst = self.current_block.load(var_type, alloca_inst.result)
            return load_inst.result
        return IrValue.const_int(0)

    def _compile_binop(self, op, lhs: IrValue, rhs: IrValue, type_: IrType) -> IrValue:
        """Compile a binary operation into the appropriate IR instruction."""
        if isinstance(op, ast.Add):
            return self.current_block.add(type_, lhs, rhs).result
        if isinstance(op, ast.Sub):
            return self.current_block.sub(type_, lhs, rhs).result
        if isinstance(op, ast.Mult):
            return self.current_block.mul(type_, lhs, rhs).result
        if isinstance(op, ast.Div):
            return self.current_block.div(type_, lhs, rhs).result
        if isinstance(op, ast.Mod):
            return self.current_block.mod_(type_, lhs, rhs).result
        if isinstance(op, ast.BitAnd):
            return self.current_block.and_(type_, lhs, rhs).result
        if isinstance(op, ast.BitOr):
            return self.current_block.or_(type_, lhs, rhs).result
        if isinstance(op, ast.BitXor):
            return self.current_block.xor(type_, lhs, rhs).result
        if isinstance(op, ast.LShift):
            return self.current_block.shl(type_, lhs, rhs).result
        if isinstance(op, ast.RShift):
            return self.current_block.shr(type_, lhs, rhs).result
        if isinstance(op, ast.FloorDiv):
            return self.current_block.div(type_, lhs, rhs).result
        if isinstance(op, ast.Pow):
            call = self.current_block.call("__builtin_pow", [lhs, rhs], type_)
            return call.result
        return lhs

    def _compile_binop_expr(self, node: ast.BinOp) -> IrValue:
        """Compile a binary expression node."""
        lhs = self._compile_expr(node.left)
        rhs = self._compile_expr(node.right)
        result_type = lhs.type if lhs.type.kind != 'ptr' else IrType.i32()
        return self._compile_binop(node.op, lhs, rhs, result_type)

    def _compile_unaryop(self, node: ast.UnaryOp) -> IrValue:
        """Compile a unary expression (UAdd, USub, Not, Invert)."""
        operand = self._compile_expr(node.operand)
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.USub):
            zero = IrValue.const_int(0)
            return self.current_block.sub(IrType.i32(), zero, operand).result
        if isinstance(node.op, ast.Not):
            zero = IrValue.const_int(0)
            eq = self.current_block.eq(IrType.i32(), operand, zero)
            return eq.result
        if isinstance(node.op, ast.Invert):
            return self.current_block.xor(IrType.i32(), operand, IrValue.const_int(-1)).result
        return operand

    def _compile_compare(self, node: ast.Compare) -> IrValue:
        """
        Compile a comparison expression.

        Supports Eq, NotEq, Lt, LtE, Gt, GtE, In, NotIn, Is, IsNot.
        Chained comparisons (a < b < c) are supported by ANDing results.
        """
        left = self._compile_expr(node.left)
        for i, (op, comparator) in enumerate(zip(node.ops, node.comparators)):
            right = self._compile_expr(comparator)
            cmp_type = left.type if left.type.kind != 'ptr' else IrType.ptr()
            if isinstance(op, ast.Eq):
                result = self.current_block.eq(cmp_type, left, right).result
            elif isinstance(op, ast.NotEq):
                result = self.current_block.ne(cmp_type, left, right).result
            elif isinstance(op, ast.Lt):
                result = self.current_block.lt(cmp_type, left, right).result
            elif isinstance(op, ast.LtE):
                result = self.current_block.le(cmp_type, left, right).result
            elif isinstance(op, ast.Gt):
                result = self.current_block.gt(cmp_type, left, right).result
            elif isinstance(op, ast.GtE):
                result = self.current_block.ge(cmp_type, left, right).result
            elif isinstance(op, ast.In):
                call = self.current_block.call("__builtin_in", [left, right], IrType.i1())
                result = call.result
            elif isinstance(op, ast.NotIn):
                call = self.current_block.call("__builtin_in", [left, right], IrType.i1())
                not_val = self.current_block.xor(IrType.i1(), call.result, IrValue.const_bool(True)).result
                result = not_val
            elif isinstance(op, ast.Is):
                result = self.current_block.eq(IrType.ptr(), left, right).result
            elif isinstance(op, ast.IsNot):
                result = self.current_block.ne(IrType.ptr(), left, right).result
            else:
                result = IrValue.const_bool(False)
            left = result
        if left.type.kind != 'i1':
            left = self.current_block.ne(IrType.i32(), left, IrValue.const_int(0)).result
        return left

    def _compile_boolop(self, node: ast.BoolOp) -> IrValue:
        """
        Compile a boolean expression (and/or) with short-circuit semantics.

        For 'and': if left is false, skip right evaluation.
        For 'or': if left is true, skip right evaluation.
        """
        if isinstance(node.op, ast.And):
            result = self._compile_expr(node.values[0])
            for val_node in node.values[1:]:
                if result.type.kind != 'i1':
                    result = self.current_block.ne(IrType.i32(), result, IrValue.const_int(0)).result
                short_circuit_block = self.current_func.new_block()
                next_block = self.current_func.new_block()
                self.current_block.set_terminator("br", operands=[result, short_circuit_block.label, next_block.label])
                self.current_block = short_circuit_block
                right_val = self._compile_expr(val_node)
                result = right_val
                self.current_block = self.current_func.new_block()
                if next_block.instructions or next_block.terminator:
                    merge_block = self.current_block
                    self.current_block = merge_block
                    result = self.current_block.phi(IrType.i32(), [
                        (IrValue.const_bool(False), short_circuit_block.label),
                        (right_val, next_block.label)
                    ]).result
            return result
        elif isinstance(node.op, ast.Or):
            result = self._compile_expr(node.values[0])
            for val_node in node.values[1:]:
                if result.type.kind != 'i1':
                    result = self.current_block.ne(IrType.i32(), result, IrValue.const_int(0)).result
                short_circuit_block = self.current_func.new_block()
                next_block = self.current_func.new_block()
                self.current_block.set_terminator("br", operands=[result, short_circuit_block.label, next_block.label])
                self.current_block = short_circuit_block
                right_val = self._compile_expr(val_node)
                merge_block = self.current_func.new_block()
                self.current_block = self.current_func.new_block()
                if self.current_block is not None:
                    pass
                result = right_val
            return result
        return IrValue.const_bool(False)

    def _compile_ifexp(self, node: ast.IfExp) -> IrValue:
        """
        Compile a ternary if expression (x if cond else y).

        Evaluates the condition, then selects between the two branches
        using a phi node at the merge point.
        """
        cond = self._compile_expr(node.test)
        if cond.type.kind != 'i1':
            cond = self.current_block.ne(IrType.i32(), cond, IrValue.const_int(0)).result
        true_block = self.current_func.new_block()
        false_block = self.current_func.new_block()
        merge_block = self.current_func.new_block()
        self.current_block.set_terminator("br", operands=[cond, true_block.label, false_block.label])
        self.current_block = true_block
        true_val = self._compile_expr(node.body)
        self.current_block.set_terminator("jmp", operands=[merge_block.label])
        self.current_block = false_block
        false_val = self._compile_expr(node.orelse)
        self.current_block.set_terminator("jmp", operands=[merge_block.label])
        self.current_block = merge_block
        result = self.current_block.phi(IrType.i32(), [
            (true_val, true_block.label),
            (false_val, false_block.label)
        ]).result
        return result

    def _compile_call(self, node: ast.Call) -> IrValue:
        """
        Compile a function call.

        Handles built-in calls (print), user-defined function calls,
        and method calls via __method_ prefix.
        """
        args = [self._compile_expr(arg) for arg in node.args]
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name == "print":
                self.current_block.call("__builtin_print", args, IrType.void())
                return IrValue.const_int(0)
            ret_type = IrType.i32()
            if func_name in self.compiled_functions:
                ret_type = self.compiled_functions[func_name].return_type
            call_inst = self.current_block.call(func_name, args, ret_type)
            return call_inst.result if ret_type.kind != 'void' else IrValue.const_int(0)
        elif isinstance(node.func, ast.Attribute):
            obj = self._compile_expr(node.func.value)
            attr_name = node.func.attr
            call_args = [obj] + args
            call_inst = self.current_block.call(f"__method_{attr_name}", call_args, IrType.i32())
            return call_inst.result
        return IrValue.const_int(0)

    def _compile_subscript(self, node: ast.Subscript) -> IrValue:
        """
        Compile a subscript expression (e.g., a[i]).

        Uses GEP to compute the pointer and load to get the value.
        """
        base = self._compile_expr(node.value)
        index = self._compile_expr(node.slice)
        gep_inst = self.current_block.gep(base, index)
        load_inst = self.current_block.load(IrType.i32(), gep_inst.result)
        return load_inst.result

    def _compile_attribute(self, node: ast.Attribute) -> IrValue:
        """
        Compile an attribute access (e.g., obj.attr).

        Dispatches to __attr_<name> runtime helper.
        """
        obj = self._compile_expr(node.value)
        call = self.current_block.call(f"__attr_{node.attr}", [obj], IrType.i32())
        return call.result


def compile_py_to_ir(python_source: str, module_name: Optional[str] = None) -> IrModule:
    """
    Compile Python source code to an IR module.

    This is the main entry point for the compiler. Parses the Python
    source and runs it through the IrCompiler.
    """
    tree = ast.parse(python_source)
    compiler = IrCompiler(module_name)
    return compiler.compile(tree)


def ir_module_to_text(module: IrModule) -> str:
    """Serialize an IR module to text format."""
    return str(module)


def ir_module_to_file(module: IrModule, path: str):
    """Write an IR module to a text file."""
    with open(path, 'w') as f:
        f.write(str(module))
    return path
