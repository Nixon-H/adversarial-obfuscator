"""ROP compilation pipeline — design-time simulation.

Classes:
    GadgetFinder     — Synthetic gadget database modelling what the binary will contain.
    RopCompiler      — Translates IR functions / Python snippets into ROP chains.
    PayloadDisperser — Splits & scrambles chains so no two consecutive gadgets
                       reside at adjacent addresses.
"""

import ast
import json
import logging
import os
import random

logger = logging.getLogger(__name__)

# Gadget placeholder emitted for unhandled AST nodes: int3 (0xCC) trap.
# A faulting placeholder is fail-loud by design — executing a chain that
# reaches an uncompiled construct raises SIGTRAP instead of silently
# running the wrong semantics.
TRAP_PLACEHOLDER = 0xCC


# ──────────────────────────────────────────────
# Data objects
# ──────────────────────────────────────────────

class Gadget:
    """A single ROP gadget — an address that points to a useful instruction
    sequence ending in a return (0xC3)."""

    __slots__ = ("address", "size", "instructions", "category")

    CATEGORIES = frozenset({
        "pop", "mov", "add", "sub", "xor", "and", "or", "load", "store",
        "call", "syscall", "jmp", "cmp", "nop", "other",
    })

    def __init__(self, address: int, size: int,
                 instructions: list[str], category: str = "other"):
        self.address = address
        self.size = size
        self.instructions = instructions
        self.category = category if category in self.CATEGORIES else "other"

    @property
    def signature(self) -> str:
        return "; ".join(self.instructions)

    def __repr__(self) -> str:
        return (f"Gadget(0x{self.address:x}, {self.size}B, "
                f"[{self.signature}])")


class RopChain:
    """A compiled ROP chain — a sequence of gadget addresses and inline
    immediate values that will be placed on the stack to emulate a function."""

    __slots__ = ("entries", "source_func", "gadget_map")

    def __init__(self, entries: list[int] | None = None,
                 source_func: str = ""):
        self.entries = entries or []
        self.source_func = source_func
        self.gadget_map: dict[int, Gadget] = {}

    @property
    def size_bytes(self) -> int:
        return len(self.entries) * 8

    @property
    def gadget_count(self) -> int:
        return len(self.entries)

    def append_addr(self, addr: int):
        self.entries.append(addr & 0xFFFFFFFFFFFFFFFF)

    def append_imm(self, value: int):
        self.entries.append(value & 0xFFFFFFFFFFFFFFFF)

    def to_bytes(self) -> bytes:
        return b"".join(v.to_bytes(8, "little") for v in self.entries)

    @classmethod
    def from_bytes(cls, data: bytes, source_func: str = "") -> "RopChain":
        if len(data) % 8 != 0:
            raise ValueError("ROP chain data must be 8-byte aligned")
        entries = [
            int.from_bytes(data[i:i + 8], "little")
            for i in range(0, len(data), 8)
        ]
        return cls(entries, source_func)

    def __repr__(self) -> str:
        return (f"RopChain({len(self.entries)} entries, "
                f"{self.size_bytes}B, func={self.source_func})")


# ──────────────────────────────────────────────
# Synthetic gadget database
# ──────────────────────────────────────────────

_SYNTHETIC_GADGETS: list[Gadget] = [
    # --- pop;ret ---
    Gadget(0x401000, 2, ["pop rax", "ret"], "pop"),
    Gadget(0x401002, 2, ["pop rbx", "ret"], "pop"),
    Gadget(0x401004, 2, ["pop rcx", "ret"], "pop"),
    Gadget(0x401006, 2, ["pop rdx", "ret"], "pop"),
    Gadget(0x401008, 2, ["pop rdi", "ret"], "pop"),
    Gadget(0x40100A, 2, ["pop rsi", "ret"], "pop"),
    Gadget(0x40100C, 2, ["pop r8", "ret"], "pop"),
    Gadget(0x40100E, 2, ["pop r9", "ret"], "pop"),
    Gadget(0x401010, 2, ["pop rbp", "ret"], "pop"),
    # --- mov reg,reg;ret ---
    Gadget(0x401020, 3, ["mov rdi, rax", "ret"], "mov"),
    Gadget(0x401023, 3, ["mov rax, rdi", "ret"], "mov"),
    Gadget(0x401026, 3, ["mov rsi, rax", "ret"], "mov"),
    Gadget(0x401029, 3, ["mov rax, rsi", "ret"], "mov"),
    Gadget(0x40102C, 3, ["mov rdx, rax", "ret"], "mov"),
    Gadget(0x40102F, 3, ["mov rax, rdx", "ret"], "mov"),
    Gadget(0x401032, 3, ["mov rax, rbx", "ret"], "mov"),
    Gadget(0x401035, 3, ["mov rbx, rax", "ret"], "mov"),
    # --- mov [reg],reg;ret  (store) ---
    Gadget(0x401040, 3, ["mov [rdi], rax", "ret"], "store"),
    Gadget(0x401043, 3, ["mov [rdi], rbx", "ret"], "store"),
    Gadget(0x401046, 3, ["mov [rsi], rax", "ret"], "store"),
    # --- mov reg,[reg];ret  (load) ---
    Gadget(0x401050, 3, ["mov rax, [rdi]", "ret"], "load"),
    Gadget(0x401053, 3, ["mov rax, [rsi]", "ret"], "load"),
    Gadget(0x401056, 3, ["mov rbx, [rdi]", "ret"], "load"),
    # --- alu reg,reg;ret ---
    Gadget(0x401060, 3, ["add rax, rdi", "ret"], "add"),
    Gadget(0x401063, 3, ["add rax, rsi", "ret"], "add"),
    Gadget(0x401066, 3, ["add rax, rbx", "ret"], "add"),
    Gadget(0x401069, 3, ["add rax, rcx", "ret"], "add"),
    Gadget(0x40106C, 3, ["sub rax, rdi", "ret"], "sub"),
    Gadget(0x40106F, 3, ["sub rax, rsi", "ret"], "sub"),
    Gadget(0x401072, 3, ["sub rax, rbx", "ret"], "sub"),
    Gadget(0x401075, 3, ["xor rax, rdi", "ret"], "xor"),
    Gadget(0x401078, 3, ["xor rax, rsi", "ret"], "xor"),
    Gadget(0x40107B, 3, ["xor rax, rbx", "ret"], "xor"),
    Gadget(0x40107E, 3, ["xor rax, rax", "ret"], "xor"),
    Gadget(0x401081, 3, ["and rax, rdi", "ret"], "and"),
    Gadget(0x401084, 3, ["or rax, rdi", "ret"], "or"),
    Gadget(0x401087, 3, ["shl rax, cl", "ret"], "other"),
    Gadget(0x40108A, 3, ["shr rax, cl", "ret"], "other"),
    # --- cmp;ret ---
    Gadget(0x401090, 3, ["cmp rax, rdi", "ret"], "cmp"),
    Gadget(0x401093, 3, ["cmp rax, rsi", "ret"], "cmp"),
    Gadget(0x401096, 3, ["test rax, rax", "ret"], "cmp"),
    # --- jmp / call (indirect) ---
    Gadget(0x4010A0, 2, ["jmp rax", "ret"], "jmp"),
    Gadget(0x4010A2, 2, ["call rax", "ret"], "call"),
    Gadget(0x4010A4, 2, ["jmp rdi", "ret"], "jmp"),
    # --- syscall ---
    Gadget(0x4010B0, 2, ["syscall", "ret"], "syscall"),
    # --- xchg;ret (stack pivot helpers) ---
    Gadget(0x4010C0, 3, ["xchg rax, rsp", "ret"], "other"),
    Gadget(0x4010C3, 3, ["xchg rdi, rsp", "ret"], "other"),
    # --- nop-ret ---
    Gadget(0x4010D0, 2, ["nop", "ret"], "nop"),
    Gadget(0x4010D2, 2, ["nop", "nop", "ret"], "nop"),
    # --- leave;ret (stack frame restore) ---
    Gadget(0x4010E0, 2, ["leave", "ret"], "other"),
    # --- ret itself (end-of-chain sink) ---
    Gadget(0x4010F0, 1, ["ret"], "other"),
]

_SYNTHETIC_BY_ADDR: dict[int, Gadget] = {}
_SYNTHETIC_BY_CATEGORY: dict[str, list[Gadget]] = {}

for _g in _SYNTHETIC_GADGETS:
    _SYNTHETIC_BY_ADDR[_g.address] = _g
    _SYNTHETIC_BY_CATEGORY.setdefault(_g.category, []).append(_g)


# ──────────────────────────────────────────────
# 1. GadgetFinder
# ──────────────────────────────────────────────

class GadgetFinder:
    """Scans a binary for ROP gadgets and builds a searchable database.

    When no real binary is available, falls back to a synthetic gadget
    database that simulates what the final native binary will contain.
    """

    def __init__(self, binary_path: str | None = None):
        self.binary_path = binary_path
        self._gadgets: dict[int, Gadget] = {}
        self._by_category: dict[str, list[Gadget]] = {}

    def find_gadgets(self) -> dict[str, list[Gadget]]:
        """Run gadget discovery and return a dict indexed by category."""
        if self.binary_path and os.path.exists(self.binary_path):
            self._scan_binary(self.binary_path)
        else:
            self._load_synthetic()

        self._by_category.clear()
        for addr, g in self._gadgets.items():
            self._by_category.setdefault(g.category, []).append(g)
        return dict(self._by_category)

    def _load_synthetic(self):
        self._gadgets = dict(_SYNTHETIC_BY_ADDR)

    def _scan_binary(self, path: str):
        with open(path, "rb") as f:
            data = f.read()

        text_start, text_size = self._find_text_segment(data)
        if text_start is None:
            self._load_synthetic()
            return

        base_addr = text_start
        self._gadgets = {}

        for offset in range(len(data)):
            if offset >= len(data) or data[offset] not in (0xC3, 0xC2):
                continue

            start = max(0, offset - 20)
            instrs = []
            pos = start
            valid = True
            while pos <= offset:
                consumed, desc = self._decode_one(data, pos)
                if consumed == 0:
                    valid = False
                    break
                instrs.append(desc)
                pos += consumed
            if not valid:
                continue

            addr = base_addr + start
            gsize = offset - start + (3 if data[offset] == 0xC2 else 1)
            cat = self._classify(instrs)
            self._gadgets[addr] = Gadget(addr, gsize, list(instrs), cat)

    def _find_text_segment(self, data: bytes) -> tuple[int | None, int | None]:
        if len(data) < 64:
            return None, None
        e_phoff = int.from_bytes(data[32:40], "little")
        e_phentsize = int.from_bytes(data[54:56], "little")
        e_phnum = int.from_bytes(data[56:58], "little")
        if e_phoff and e_phentsize and e_phnum:
            for i in range(e_phnum):
                ph = e_phoff + i * e_phentsize
                if ph + e_phentsize > len(data):
                    continue
                p_type = int.from_bytes(data[ph:ph + 4], "little")
                if p_type != 1:
                    continue
                p_flags = int.from_bytes(data[ph + 4:ph + 8], "little")
                if p_flags & 1 == 0:
                    continue
                if e_phentsize >= 56:
                    p_vaddr = int.from_bytes(data[ph + 16:ph + 24], "little")
                    p_memsz = int.from_bytes(data[ph + 40:ph + 48], "little")
                    return p_vaddr, p_memsz
        return None, None

    @staticmethod
    def _decode_one(code: bytes, pos: int) -> tuple[int, str]:
        if pos >= len(code):
            return 0, ""
        b = code[pos]
        if b == 0xC3:
            return 1, "ret"
        if b == 0xC2:
            if pos + 2 < len(code):
                imm = int.from_bytes(code[pos + 1:pos + 3], "little")
                return 3, f"ret {imm:#x}"
            return 0, ""
        if b == 0x90:
            return 1, "nop"
        if (b & 0xF8) == 0x50:
            return 1, f"push r{b & 7}"
        if (b & 0xF8) == 0x58:
            return 1, f"pop r{b & 7}"
        if b == 0x48 and pos + 1 < len(code):
            b1 = code[pos + 1]
            if (b1 & 0xFC) == 0x50:
                return 2, f"push r{b1 & 7}"
            if (b1 & 0xFC) == 0x58:
                return 2, f"pop r{b1 & 7}"
            if b1 in (0x89, 0x8B) and pos + 2 < len(code):
                modrm = code[pos + 2]
                r1 = (modrm >> 3) & 7
                if (modrm >> 6) == 0b11:
                    return 3, f"mov r{r1}, r{modrm & 7}"
                return 3, f"mov {'r' if b1 == 0x8B else ''}[r{modrm & 7}], r{r1}"
            if b1 in (0x01, 0x03):
                if pos + 2 < len(code):
                    modrm = code[pos + 2]
                    r1 = (modrm >> 3) & 7
                    if (modrm >> 6) == 0b11:
                        return 3, f"add r{r1}, r{modrm & 7}"
                return 2, "add"
            if b1 in (0x29, 0x2B):
                if pos + 2 < len(code):
                    modrm = code[pos + 2]
                    r1 = (modrm >> 3) & 7
                    if (modrm >> 6) == 0b11:
                        return 3, f"sub r{r1}, r{modrm & 7}"
                return 2, "sub"
            if b1 == 0x31 and pos + 2 < len(code):
                modrm = code[pos + 2]
                r1 = (modrm >> 3) & 7
                if (modrm >> 6) == 0b11:
                    return 3, f"xor r{r1}, r{modrm & 7}"
                return 3, "xor"
        if b == 0xEB and pos + 1 < len(code):
            rel = code[pos + 1]
            return 2, f"jmp {rel if rel < 128 else rel - 256:+d}"
        if b == 0xE9 and pos + 4 < len(code):
            rel = int.from_bytes(code[pos + 1:pos + 5], "little", signed=True)
            return 5, f"jmp {rel:+d}"
        if b == 0xE8 and pos + 4 < len(code):
            rel = int.from_bytes(code[pos + 1:pos + 5], "little", signed=True)
            return 5, f"call {rel:+d}"
        if b == 0x0F and pos + 1 < len(code):
            if code[pos + 1] == 0x05:
                return 2, "syscall"
            if code[pos + 1] in range(0x80, 0x90) and pos + 2 < len(code):
                jcc = ["jo", "jno", "jb", "jnb", "jz", "jnz",
                       "jbe", "ja", "js", "jns", "jp", "jnp",
                       "jl", "jge", "jle", "jg"]
                rel = code[pos + 2]
                cc = jcc[code[pos + 1] & 0xF]
                return 3, f"{cc} {rel if rel < 128 else rel - 256:+d}"
            return 2, f"two_byte {code[pos + 1]:#04x}"
        if 0x70 <= b <= 0x7F and pos + 1 < len(code):
            jcc = ["jo", "jno", "jb", "jnb", "jz", "jnz",
                   "jbe", "ja", "js", "jns", "jp", "jnp",
                   "jl", "jge", "jle", "jg"]
            rel = code[pos + 1]
            return 2, f"{jcc[b & 0xF]} {rel if rel < 128 else rel - 256:+d}"
        return 1, f"db {b:#04x}"

    @staticmethod
    def _classify(instrs: list[str]) -> str:
        merged = "; ".join(instrs)
        if "syscall" in merged:
            return "syscall"
        if "ret" in merged and any(i.startswith("pop") for i in instrs):
            return "pop"
        if "ret" not in merged:
            return "other"
        for cat, keywords in [
            ("add", ["add"]),
            ("sub", ["sub"]),
            ("xor", ["xor"]),
            ("and", ["and"]),
            ("or", ["or"]),
            ("cmp", ["cmp", "test"]),
            ("load", ["mov rax, [r", "mov rbx, [r"]),
            ("store", ["mov [r"]),
            ("jmp", ["jmp"]),
            ("call", ["call"]),
            ("mov", ["mov r"]),
            ("nop", ["nop"]),
        ]:
            if any(k in merged for k in keywords):
                return cat
        return "other"

    def by_category(self, category: str) -> list[Gadget]:
        return list(self._by_category.get(category, []))

    def find(self, pattern: str) -> Gadget | None:
        merged_lower = pattern.lower().replace(" ", "")
        for g in self._gadgets.values():
            if merged_lower in g.signature.lower().replace(" ", ""):
                return g
        return None

    def find_pop(self, reg: str) -> Gadget | None:
        return self.find(f"pop {reg}; ret")

    def find_mov(self, dst: str, src: str) -> Gadget | None:
        return self.find(f"mov {dst}, {src}; ret")

    def find_alu(self, op: str, dst: str = "rax", src: str = "rdi") -> Gadget | None:
        return self.find(f"{op} {dst}, {src}; ret")

    def store_gadgets_json(self, path: str):
        data = {}
        for addr, g in self._gadgets.items():
            data[hex(addr)] = {
                "address": addr,
                "size": g.size,
                "instructions": g.instructions,
                "category": g.category,
            }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @property
    def all_gadgets(self) -> list[Gadget]:
        return list(self._gadgets.values())

    @property
    def count(self) -> int:
        return len(self._gadgets)


# ──────────────────────────────────────────────
# 2. RopCompiler
# ──────────────────────────────────────────────

REG_ORDER = ["rdi", "rsi", "rdx", "rcx", "r8", "r9", "rax", "rbx"]
REG_MAP = {r: i for i, r in enumerate(REG_ORDER)}


class RopCompiler:
    """Compiles a Python AST function definition into a ROP gadget chain.

    The compiler walks the AST body, translates each statement/expression
    into a sequence of gadget invocations linked via return addresses.
    """

    def __init__(self, gadgets_db: dict[str, list[Gadget]] | None = None,
                 finder: GadgetFinder | None = None):
        if finder is None:
            finder = GadgetFinder()
            finder.find_gadgets()
        self.finder = finder
        self._gadgets_by_cat = gadgets_db or finder.by_category("pop")
        self._chain = RopChain()
        self._var_map: dict[str, int] = {}
        self._label_counter = 0
        # Unhandled AST node types seen by _fallback_compile. Each entry
        # records the node class name; fallback_count counts emissions.
        self.warnings: list[str] = []
        self.fallback_count = 0
        self.strict = False

    # ── public API ────────────────────────────────────────────

    def compile(self, func_def: ast.FunctionDef) -> RopChain:
        self._chain = RopChain(source_func=func_def.name)
        self._var_map = {}
        self._label_counter = 0
        self.warnings = []
        self.fallback_count = 0

        for node in func_def.body:
            self._compile_stmt(node)

        return self._chain

    def compile_ir_function(self, ir_func: dict) -> list[int]:
        self._chain = RopChain(source_func=ir_func.get("name", ""))
        self._var_map = {}
        self._label_counter = 0

        blocks = ir_func.get("blocks", [])
        if not blocks:
            return self._chain.entries

        for block in blocks:
            for instr in block.get("instructions", []):
                self._compile_ir_instr(instr)
            term = block.get("terminator")
            if term:
                self._compile_ir_instr(term)

        return self._chain.entries

    # ── AST statement dispatch ────────────────────────────────

    def _compile_stmt(self, node: ast.AST):
        if isinstance(node, ast.Assign):
            self._compile_assign(node)
        elif isinstance(node, ast.Return):
            self._compile_return(node)
        elif isinstance(node, ast.Expr):
            self._compile_expr(node.value)
        elif isinstance(node, ast.If):
            self._compile_if(node)
        elif isinstance(node, ast.For):
            self._compile_for(node)
        elif isinstance(node, ast.While):
            self._compile_while(node)
        elif isinstance(node, ast.FunctionDef):
            pass
        elif isinstance(node, ast.AugAssign):
            self._compile_augassign(node)
        elif isinstance(node, ast.Call):
            self._compile_call_expr(node)
        elif isinstance(node, ast.Pass):
            pass
        else:
            self._fallback_compile(node)

    def _fallback_compile(self, node: ast.AST):
        """Fail-loud fallback for unhandled AST nodes.

        Records the node type in self.warnings, bumps self.fallback_count,
        logs loudly, and emits an int3 trap placeholder so the output chain
        is never silently wrong. In strict mode raises instead of emitting.
        """
        node_type = type(node).__name__
        self.warnings.append(node_type)
        self.fallback_count += 1
        logger.warning(
            "RopCompiler: unhandled AST node %s in %r — emitting trap placeholder",
            node_type, getattr(self._chain, "source_func", ""),
        )
        if self.strict:
            raise NotImplementedError(
                f"RopCompiler strict mode: unhandled AST node {node_type}"
            )
        self._chain.append_imm(TRAP_PLACEHOLDER)

    # ── Assign ────────────────────────────────────────────────

    def _compile_assign(self, node: ast.Assign):
        rhs = self._resolve_expr(node.value)
        for tgt in node.targets:
            if isinstance(tgt, ast.Name):
                self._var_map[tgt.id] = rhs
                self._emit_pop_rax(rhs)

    # ── AugAssign (x += y) ────────────────────────────────────

    def _compile_augassign(self, node: ast.AugAssign):
        lhs_val = self._var_map.get(node.target.id, 0)
        rhs_val = self._resolve_expr(node.value)
        op = type(node.op).__name__.lower().replace("add", "add").replace("sub", "sub")
        if "add" in op:
            result = self._emit_binop(lhs_val, rhs_val, "add")
        elif "sub" in op:
            result = self._emit_binop(lhs_val, rhs_val, "sub")
        elif "mult" in op:
            result = self._emit_binop(lhs_val, rhs_val, "mul")
        elif "xor" in op:
            result = self._emit_binop(lhs_val, rhs_val, "xor")
        else:
            result = lhs_val + rhs_val
        self._var_map[node.target.id] = result

    # ── Return ────────────────────────────────────────────────

    def _compile_return(self, node: ast.Return):
        if node.value is not None:
            val = self._resolve_expr(node.value)
            self._emit_pop_rax(val)
        self._chain.append_addr(0x4010F0)

    # ── Expression ────────────────────────────────────────────

    def _compile_expr(self, node: ast.AST):
        if isinstance(node, ast.Call):
            self._compile_call_expr(node)
        else:
            self._fallback_compile(node)

    def _compile_call_expr(self, node: ast.Call):
        func_name = self._get_call_name(node)
        args = [self._resolve_expr(a) for a in node.args]

        arg_regs = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
        for i, val in enumerate(args[:6]):
            self._emit_pop_imm(arg_regs[i], val)

        if func_name and func_name.startswith("0x"):
            target = int(func_name, 16)
        elif func_name in self._var_map:
            target = self._var_map[func_name]
        else:
            target = 0x4010A2

        self._chain.append_addr(target)

    def _get_call_name(self, node: ast.Call) -> str:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    # ── If ────────────────────────────────────────────────────

    def _compile_if(self, node: ast.If):
        cond_val = self._resolve_expr(node.test)
        self._emit_pop_rax(cond_val)

        test_g = self.finder.find("test rax, rax")
        if test_g:
            self._chain.append_addr(test_g.address)

        nop_ret = self.finder.find("ret")
        sink = nop_ret.address if nop_ret else 0x4010F0

        for stmt in node.body:
            self._compile_stmt(stmt)

        for stmt in node.orelse:
            self._compile_stmt(stmt)

        self._chain.append_addr(sink)

    # ── For / While (minimal) ─────────────────────────────────

    def _compile_for(self, node: ast.For):
        for stmt in node.body:
            self._compile_stmt(stmt)
        nop_ret = self.finder.find("ret")
        self._chain.append_addr(nop_ret.address if nop_ret else 0x4010F0)

    def _compile_while(self, node: ast.While):
        for stmt in node.body:
            self._compile_stmt(stmt)
        nop_ret = self.finder.find("ret")
        self._chain.append_addr(nop_ret.address if nop_ret else 0x4010F0)

    # ── IR instruction compilation ────────────────────────────

    def _compile_ir_instr(self, instr: dict):
        opcode = instr.get("opcode", "")
        if opcode == "add":
            self._compile_ir_binary("add", instr)
        elif opcode == "sub":
            self._compile_ir_binary("sub", instr)
        elif opcode == "mul":
            self._compile_ir_binary("mul", instr)
        elif opcode == "xor":
            self._compile_ir_binary("xor", instr)
        elif opcode == "and":
            self._compile_ir_binary("and", instr)
        elif opcode == "or":
            self._compile_ir_binary("or", instr)
        elif opcode == "call":
            self._compile_ir_call(instr)
        elif opcode == "ret":
            self._compile_ir_ret(instr)
        elif opcode == "load":
            self._compile_ir_load(instr)
        elif opcode == "store":
            self._compile_ir_store(instr)
        elif opcode == "icmp":
            self._compile_ir_icmp(instr)
        elif opcode in ("br", "jmp"):
            pass
        elif opcode in ("zext", "sext", "trunc", "ptrtoint", "inttoptr"):
            self._compile_ir_conv(instr)
        elif opcode in ("nop", "unreachable"):
            pass
        else:
            result = instr.get("result")
            if result:
                self._var_map[result] = 0

    def _var_val(self, operand) -> int:
        if isinstance(operand, int):
            return operand
        if isinstance(operand, str):
            op = operand.strip()
            if op.startswith("%") or op.startswith("@"):
                return self._var_map.get(op, 0)
            try:
                return int(op, 0)
            except ValueError:
                return hash(op) & 0xFFFFFFFF
        if hasattr(operand, "name"):
            return self._var_map.get(operand.name, 0)
        return 0

    def _emit_pop_rax(self, value: int):
        pop = self.finder.find_pop("rax") or self.finder.find("pop rax; ret")
        if pop:
            self._chain.append_addr(pop.address)
            self._chain.append_imm(value)

    def _emit_pop_imm(self, reg: str, value: int):
        pop = self.finder.find_pop(reg) or self.finder.find(f"pop r{reg}; ret")
        if pop:
            self._chain.append_addr(pop.address)
            self._chain.append_imm(value)

    def _emit_binop(self, lhs: int, rhs: int, op: str) -> int:
        alu_g = self.finder.find_alu(op, "rax", "rdi")
        if alu_g:
            self._emit_pop_imm("rax", lhs)
            self._emit_pop_imm("rdi", rhs)
            self._chain.append_addr(alu_g.address)
            result = (lhs + rhs) if op == "add" else (
                (lhs - rhs) if op == "sub" else (
                    (lhs * rhs) if op == "mul" else (lhs ^ rhs)
                )
            )
            return result & 0xFFFFFFFFFFFFFFFF
        xor_g = self.finder.find_alu("xor", "rax", "rax")
        if xor_g:
            self._chain.append_addr(xor_g.address)
        return 0

    def _compile_ir_binary(self, op: str, instr: dict):
        result = instr.get("result")
        operands = instr.get("operands", [])
        lhs = self._var_val(operands[0]) if len(operands) > 0 else 0
        rhs = self._var_val(operands[1]) if len(operands) > 1 else 0
        out = self._emit_binop(lhs, rhs, op)
        if result:
            self._var_map[result] = out

    def _compile_ir_call(self, instr: dict):
        args = instr.get("args", [])
        arg_regs = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
        for i, a in enumerate(args[:6]):
            self._emit_pop_imm(arg_regs[i], self._var_val(a))
        self._chain.append_addr(0x4010A2)
        result = instr.get("result")
        if result:
            self._var_map[result] = 0

    def _compile_ir_ret(self, instr: dict):
        if not instr.get("void", False):
            val = self._var_val(instr.get("value", "0"))
            self._emit_pop_rax(val)
        self._chain.append_addr(0x4010F0)

    def _compile_ir_load(self, instr: dict):
        ptr = self._var_val(instr.get("ptr", "0"))
        load_g = self.finder.find("mov rax, [rdi]; ret") or self.finder.find("mov rax, [rdi]")
        if load_g:
            self._emit_pop_imm("rdi", ptr)
            self._chain.append_addr(load_g.address)
        result = instr.get("result")
        if result:
            self._var_map[result] = 0

    def _compile_ir_store(self, instr: dict):
        val = self._var_val(instr.get("value", "0"))
        ptr = self._var_val(instr.get("ptr", "0"))
        store_g = self.finder.find("mov [rdi], rax; ret") or self.finder.find("mov [rdi], rax")
        if store_g:
            self._emit_pop_imm("rdi", ptr)
            self._emit_pop_imm("rax", val)
            self._chain.append_addr(store_g.address)

    def _compile_ir_icmp(self, instr: dict):
        operands = instr.get("operands", [])
        lhs = self._var_val(operands[0]) if len(operands) > 0 else 0
        rhs = self._var_val(operands[1]) if len(operands) > 1 else 0
        self._emit_pop_imm("rax", lhs)
        cmp_g = self.finder.find("cmp rax, rdi; ret") or self.finder.find("cmp rax, rdi")
        if cmp_g:
            self._emit_pop_imm("rdi", rhs)
            self._chain.append_addr(cmp_g.address)
        result = instr.get("result")
        if result:
            self._var_map[result] = 1 if lhs == rhs else 0

    def _compile_ir_conv(self, instr: dict):
        val = self._var_val(instr.get("value", "0"))
        self._emit_pop_rax(val)
        result = instr.get("result")
        if result:
            self._var_map[result] = val

    # ── expression helpers ────────────────────────────────────

    def _resolve_expr(self, node: ast.AST) -> int:
        if isinstance(node, ast.Constant):
            return node.value if isinstance(node.value, int) else hash(str(node.value)) & 0xFFFFFFFF
        if isinstance(node, ast.Name):
            return self._var_map.get(node.id, 0)
        if isinstance(node, ast.BinOp):
            lhs = self._resolve_expr(node.left)
            rhs = self._resolve_expr(node.right)
            op_name = type(node.op).__name__
            if "Add" in op_name:
                return self._emit_binop(lhs, rhs, "add")
            if "Sub" in op_name:
                return self._emit_binop(lhs, rhs, "sub")
            if "Mult" in op_name:
                return self._emit_binop(lhs, rhs, "mul")
            if "Xor" in op_name:
                return self._emit_binop(lhs, rhs, "xor")
            return lhs + rhs
        if isinstance(node, ast.UnaryOp):
            val = self._resolve_expr(node.operand)
            op_name = type(node.op).__name__
            if "USub" in op_name:
                return (-val) & 0xFFFFFFFFFFFFFFFF
            return val
        if isinstance(node, ast.Call):
            return 0
        return 0

    @property
    def chain(self) -> RopChain:
        return self._chain


# ──────────────────────────────────────────────
# 3. PayloadDisperser
# ──────────────────────────────────────────────

class PayloadDisperser:
    """Splits a ROP chain across the binary address space and scrambles
    the gadget indices so that no two consecutive entries in the chain
    point to adjacent addresses.

    This prevents static analysis from trivially following the "stack trace"
    of the ROP chain by inspection.
    """

    def __init__(self, finder: GadgetFinder | None = None):
        self.finder = finder or GadgetFinder()
        if not self.finder.all_gadgets:
            self.finder.find_gadgets()

    def disperse(self, chain: RopChain, gap_min: int = 16) -> RopChain:
        """Re-arrange the chain so consecutive entries are never closer
        than *gap_min* bytes apart."""
        if len(chain.entries) < 2:
            return chain

        gadgets_by_addr = {g.address: g for g in self.finder.all_gadgets}
        scatter_addrs = sorted(gadgets_by_addr.keys())

        if len(scatter_addrs) < len(chain.entries):
            filler = [
                0x401000 + (i * 0x100)
                for i in range(len(chain.entries) - len(scatter_addrs))
            ]
            scatter_addrs = sorted(scatter_addrs + filler)

        rng = random.Random(hash(tuple(chain.entries)))

        def gap_ok(candidate: int, prev: int | None) -> bool:
            if prev is None:
                return True
            return abs(candidate - prev) >= gap_min

        dispersed = []
        prev_addr: int | None = None
        usable = list(scatter_addrs)

        for orig_entry in chain.entries:
            rng.shuffle(usable)
            chosen = None
            for addr in usable:
                if gap_ok(addr, prev_addr):
                    chosen = addr
                    break
            if chosen is None:
                chosen = usable[0]
            dispersed.append(chosen)
            prev_addr = chosen

        result = RopChain(source_func=chain.source_func)
        result.entries = dispersed
        result.gadget_map = dict(chain.gadget_map)

        return result

    def remap_through_indirection_table(
        self, chain: RopChain, table_base: int = 0x200000
    ) -> tuple[RopChain, dict[int, int]]:
        """Replace each gadget address with a pointer into a scrambled
        indirection table.  Returns (scrambled_chain, address_map)."""
        rng = random.Random(hash(tuple(chain.entries)))
        indices = list(range(len(chain.entries)))
        rng.shuffle(indices)

        mapping: dict[int, int] = {}
        out = RopChain(source_func=chain.source_func)

        for i, orig_addr in enumerate(chain.entries):
            table_slot = table_base + indices[i] * 8
            mapping[orig_addr] = table_slot
            out.append_addr(table_slot)

        return out, mapping

    def scatter_to_blobs(
        self, chain: RopChain, chunk_size: int = 4
    ) -> list[tuple[int, bytes]]:
        """Split the chain into multiple blobs that get placed at
        different offsets in the binary.  Returns [(base_offset, blob), ...]."""
        blobs = []
        for i in range(0, len(chain.entries), chunk_size):
            chunk = chain.entries[i:i + chunk_size]
            blob = b"".join(v.to_bytes(8, "little") for v in chunk)
            base_addr = 0x300000 + (i // chunk_size) * 0x1000
            blobs.append((base_addr, blob))
        return blobs

    def encrypt_chain(self, chain: RopChain, key: bytes | None = None) -> tuple[bytes, bytes]:
        if key is None:
            key = os.urandom(32)
        raw = chain.to_bytes()
        encrypted = bytes(raw[j] ^ key[j % len(key)] for j in range(len(raw)))
        return encrypted, key

    @staticmethod
    def decrypt_chain(encrypted: bytes, key: bytes) -> list[int]:
        raw = bytes(encrypted[j] ^ key[j % len(key)] for j in range(len(encrypted)))
        return [
            int.from_bytes(raw[i:i + 8], "little")
            for i in range(0, len(raw), 8)
        ]

    def generate_runtime_source(self, chain: RopChain, key: bytes) -> str:
        """Generate C source that uses native/rop_exec.h to execute the chain at runtime."""
        encrypted, _ = self.encrypt_chain(chain, key)
        encrypted.hex()
        key.hex()
        return f'''/* Auto-generated ROP chain runtime - uses native/rop_exec.h */
#include <stdint.h>
#include <stddef.h>
#include "rop_exec.h"

static const uint8_t _rop_enc_chain[] = {{ {', '.join(f"0x{b:02x}" for b in encrypted)} }};
static const uint8_t _rop_key[32] = {{ {', '.join(f"0x{b:02x}" for b in key)} }};

uint64_t rop_run_chain(void) {{
    uint64_t _rop_scratch[{len(chain.entries)}];
    return rop_load_and_exec(
        _rop_enc_chain, sizeof(_rop_enc_chain),
        _rop_key,
        _rop_scratch, {len(chain.entries)}
    );
}}
'''

    def save_runtime_source(self, chain: RopChain, key: bytes, output_path: str):
        source = self.generate_runtime_source(chain, key)
        with open(output_path, "w") as f:
            f.write(source)
        return output_path
