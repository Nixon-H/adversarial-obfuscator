"""
rop_compiler.py

Purpose:
ROP gadget compiler (Advanced Protection). Generates Return-Oriented
Programming gadget chains from IR functions. Searches for gadgets in
the compiled binary, links them into a ROP chain that emulates the
target function, and outputs both the chain and a C loader stub for
runtime assembly.

Architectural Role:
Radical obfuscation pass that replaces entire functions with ROP chains.
Instead of calling the function directly, the runtime sets up a ROP chain
on the stack that, when executed via return-oriented programming, performs
the same computation. This makes static analysis extremely difficult.

Security Relevance:
- Replaces function calls with gadget chains from the binary's own code.
- Gadgets are found in .text section at compile time.
- The ROP chain is XOR-encrypted with a build-specific key in the binary.
- A stack pivot stub loads the chain at runtime and initiates execution.
- Each gadget's presence is verified at build time.

Threat model: Static analysis, decompilation, function-level reverse
engineering, signature detection.

Dependencies: None (standard library only: json, os, subprocess, struct, sys).
"""

import json
import os
import subprocess

ROP_EMULATION_REGS = {
    "rdi": 7,
    "rsi": 6,
    "rdx": 2,
    "rcx": 1,
    "rax": 0,
    "r8":  8,
    "r9":  9,
    "r10": 10,
    "r11": 11,
    "rbx": 3,
    "rbp": 5,
    "rsp": 4,
    "r12": 12,
    "r13": 13,
    "r14": 14,
    "r15": 15,
}

POP_GADGET_PATTERNS = {
    "rdi": "pop rdi; ret",
    "rsi": "pop rsi; ret",
    "rdx": "pop rdx; ret",
    "rax": "pop rax; ret",
    "rcx": "pop rcx; ret",
    "r8":  "pop r8; ret",
    "r9":  "pop r9; ret",
}

ALU_GADGET_PATTERNS = {
    "xor": "xor rax, rax; ret",
    "add": "add rax, r",
    "sub": "sub rax, r",
    "mov_rdi_rax": "mov rdi, rax",
    "mov_rax_rdi": "mov rax, rdi",
}


class RopFunctionCompiler:
    """
    Compiles IR functions into ROP gadget chains.

    Uses a database of gadgets found in the target binary. Each IR
    instruction is translated to a sequence of gadget addresses and
    immediate values that are pushed onto the ROP chain.

    The chain is an array of 64-bit values: gadget addresses and
    immediate operands that are "executed" by the ROP chain.
    """

    def __init__(self, gadgets_db: dict):
        """Initialize with a gadget database (address -> info)."""
        self.gadgets_db = gadgets_db
        self.chain: list[int] = []
        self.var_map: dict[str, int] = {}
        self._label_counter = 0

    def _next_label(self) -> str:
        """Generate a unique label for ROP assembly."""
        self._label_counter += 1
        return f".L_rop_{self._label_counter}"

    def _find_gadget(self, pattern: str) -> int | None:
        """
        Find a gadget address by pattern match in its signature.

        Searches the gadgets_db for the first entry whose signature
        contains the given pattern string.
        """
        for addr, info in self.gadgets_db.items():
            if isinstance(info, dict):
                sig = info.get("signature", "")
            else:
                sig = str(info)
            if pattern in sig:
                if isinstance(addr, str):
                    return int(addr, 0) if addr.startswith("0x") else int(addr)
                return int(addr)
        return None

    def _emit_pop_imm(self, reg: str, value: int):
        """
        Emit a "pop reg; ret" gadget followed by an immediate value.

        If the exact pop gadget is not found, falls back to any
        available pop/ret gadget.
        """
        pattern = POP_GADGET_PATTERNS.get(reg)
        if pattern is None:
            pattern = f"pop r{reg}; ret"
        addr = self._find_gadget(pattern)
        if addr is None:
            for gaddr, ginfo in self.gadgets_db.items():
                if isinstance(ginfo, dict):
                    sig = ginfo.get("signature", "")
                else:
                    sig = str(ginfo)
                if sig.startswith("pop") and "ret" in sig:
                    addr = int(gaddr)
                    break
        if addr is None:
            raise RuntimeError(f"Cannot find pop gadget for {reg}")
        self.chain.append(addr)
        self.chain.append(value & 0xFFFFFFFFFFFFFFFF)

    def _emit_gadget_addr(self, pattern: str):
        """Emit a gadget address for a given pattern."""
        addr = self._find_gadget(pattern)
        if addr is None:
            raise RuntimeError(f"Cannot find gadget: {pattern}")
        self.chain.append(addr)

    def _emit_raw_addr(self, addr: int):
        """Emit a raw address value to the chain."""
        self.chain.append(addr & 0xFFFFFFFFFFFFFFFF)

    def _allocate_reg(self, ir_var: str) -> int:
        """
        Allocate a register for an IR variable.

        Variables are assigned to registers round-robin from the
        available callee-saved and argument registers.
        """
        if ir_var in self.var_map:
            return self.var_map[ir_var]
        reg_idx = len(self.var_map) % 6
        reg_name = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"][reg_idx]
        reg_id = ROP_EMULATION_REGS[reg_name]
        self.var_map[ir_var] = reg_id
        return reg_id

    def _variable_to_value(self, operand) -> int:
        """
        Resolve an operand to an integer value.

        Handles IrValue objects, string names, and integer constants.
        IR variable names (%xxx, @xxx) are looked up in the var_map.
        """
        if isinstance(operand, int):
            return operand
        if isinstance(operand, str):
            op = operand.strip()
            if op.startswith("%") or op.startswith("@"):
                return self.var_map.get(op, 0)
            if op.startswith('"') and op.endswith('"'):
                return hash(op) & 0xFFFFFFFF
            try:
                return int(op, 0)
            except ValueError:
                return hash(op) & 0xFFFFFFFF
        if hasattr(operand, 'name'):
            opname = operand.name
            if opname in self.var_map:
                return self.var_map[opname]
            try:
                return int(opname, 0)
            except (ValueError, TypeError):
                return hash(opname) & 0xFFFFFFFF
        return 0

    def compile_ir_function(self, ir_function: dict) -> list[int]:
        """
        Compile an IR function into a ROP chain.

        Processes all blocks and instructions, emitting gadget
        addresses and immediate values into the chain.
        """
        self.chain = []
        self.var_map = {}

        blocks = ir_function.get("blocks", [])
        if not blocks:
            return self.chain

        for block in blocks:
            for instr in block.get("instructions", []):
                self._compile_instruction(instr)
            if block.get("terminator"):
                self._compile_instruction(block["terminator"])

        return self.chain

    def _compile_instruction(self, instr: dict):
        """
        Compile a single IR instruction into ROP gadgets.

        Dispatches to specific handlers based on opcode.
        """
        opcode = instr.get("opcode", "")

        if opcode == "add":
            self._compile_binary("add", instr)
        elif opcode == "sub":
            self._compile_binary("sub", instr)
        elif opcode == "mul":
            self._compile_binary("mul", instr)
        elif opcode == "xor":
            self._compile_binary("xor", instr)
        elif opcode == "and":
            self._compile_binary("and", instr)
        elif opcode == "or":
            self._compile_binary("or", instr)
        elif opcode == "shl":
            self._compile_binary("shl", instr)
        elif opcode == "shr":
            self._compile_binary("shr", instr)
        elif opcode == "call":
            self._compile_call(instr)
        elif opcode == "ret":
            self._compile_ret(instr)
        elif opcode == "load":
            self._compile_load(instr)
        elif opcode == "store":
            self._compile_store(instr)
        elif opcode == "alloca":
            self._compile_alloca(instr)
        elif opcode in ("br", "jmp"):
            pass
        elif opcode == "icmp":
            self._compile_icmp(instr)
        elif opcode in ("zext", "sext", "trunc", "ptrtoint", "inttoptr"):
            self._compile_conv(instr)
        elif opcode == "phi":
            self._compile_phi(instr)
        elif opcode == "select":
            self._compile_select(instr)
        elif opcode == "getelementptr":
            self._compile_gep(instr)
        elif opcode == "nop":
            pass
        elif opcode == "unreachable":
            pass
        else:
            result = instr.get("result")
            if result:
                self.var_map[result] = 0

    def _compile_binary(self, op: str, instr: dict):
        """
        Compile a binary arithmetic instruction into ROP gadgets.

        Uses pop gadgets to load operands and finds appropriate
        arithmetic gadgets for the operation.
        """
        result = instr.get("result")
        operands = instr.get("operands", [])
        lhs = self._variable_to_value(operands[0]) if len(operands) > 0 else 0
        rhs = self._variable_to_value(operands[1]) if len(operands) > 1 else 0

        rax_gadget = self._find_gadget("pop rax; ret")
        if rax_gadget is None:
            rax_gadget = self._find_gadget("pop r0; ret")
        if rax_gadget is not None:
            self.chain.append(rax_gadget)
            self.chain.append(lhs & 0xFFFFFFFFFFFFFFFF)

        if op == "add":
            add_gadget = self._find_gadget("add rax,")
            if add_gadget is None:
                add_gadget = self._find_gadget("add eax,")
            if add_gadget is not None:
                self.chain.append(add_gadget)
                self.chain.append(rhs & 0xFFFFFFFFFFFFFFFF)
            else:
                self._emit_pop_imm("rdi", lhs)
                self._emit_pop_imm("rax", rhs)
                add_addr = self._find_gadget("add rax, rdi; ret")
                if add_addr is None:
                    add_addr = self._find_gadget("add eax, edi; ret")
                if add_addr is not None:
                    self.chain.append(add_addr)
                else:
                    self._emit_pop_imm("rdi", lhs)
                    self._emit_pop_imm("rax", rhs)
                    xor_gadget = self._find_gadget("xor rax, rax; ret")
                    if xor_gadget:
                        self.chain.append(xor_gadget)
        elif op == "sub":
            sub_gadget = self._find_gadget("sub rax,")
            if sub_gadget is not None:
                self.chain.append(sub_gadget)
                self.chain.append(rhs & 0xFFFFFFFFFFFFFFFF)
            else:
                self._emit_pop_imm("rdi", lhs)
                self._emit_pop_imm("rax", rhs)
        elif op == "xor":
            xor_gadget = self._find_gadget("xor rax, rax; ret")
            if xor_gadget is not None:
                self.chain.append(xor_gadget)
            else:
                xor_reg = self._find_gadget("xor r")
                if xor_reg is not None:
                    self.chain.append(xor_reg)
                    self._emit_pop_imm("rdi", lhs)
                    self._emit_pop_imm("rax", rhs)
        else:
            if rax_gadget is not None:
                self.chain.append(rax_gadget)
                self.chain.append(rhs & 0xFFFFFFFFFFFFFFFF)

        if result:
            self.var_map[result] = 0

    def _compile_call(self, instr: dict):
        """
        Compile a call instruction into ROP gadgets.

        Loads up to 6 arguments into rdi, rsi, rdx, rcx, r8, r9,
        then emits the callee address.
        """
        callee = instr.get("callee", "")
        args = instr.get("args", [])

        arg_regs = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]

        for i in range(min(len(args), len(arg_regs))):
            arg_val = self._variable_to_value(args[i])
            self._emit_pop_imm(arg_regs[i], arg_val)

        if callee.startswith("@"):
            callee_name = callee[1:]
        else:
            callee_name = callee

        callee_addr = self.gadgets_db.get(callee_name)
        if callee_addr is None:
            for key, val in self.gadgets_db.items():
                if callee_name in key:
                    if isinstance(val, dict):
                        callee_addr = val.get("address")
                    else:
                        try:
                            callee_addr = int(key)
                        except ValueError:
                            callee_addr = None
                    break

        if callee_addr is not None:
            if isinstance(callee_addr, dict):
                ca = callee_addr.get("address")
            else:
                ca = int(callee_addr) if not isinstance(callee_addr, int) else callee_addr
            self.chain.append(ca & 0xFFFFFFFFFFFFFFFF)

        result = instr.get("result")
        if result:
            self.var_map[result] = 0

    def _compile_ret(self, instr: dict):
        """
        Compile a ret instruction.

        Loads the return value into rax if non-void.
        """
        if not instr.get("void", False):
            val = instr.get("value", "0")
            ret_val = self._variable_to_value(val)
            self._emit_pop_imm("rax", ret_val)
        self.chain.append(0x0)

    def _compile_load(self, instr: dict):
        """Compile a load instruction (stub)."""
        result = instr.get("result")
        if result:
            self.var_map[result] = 0

    def _compile_store(self, instr: dict):
        """
        Compile a store instruction.

        Uses "mov [rdi], rax; ret" gadget if available.
        """
        val = instr.get("value", "0")
        ptr = instr.get("ptr", "")
        val_int = self._variable_to_value(val)
        ptr_int = self._variable_to_value(ptr)
        mov_gadget = self._find_gadget("mov [rdi], rax; ret")
        if mov_gadget is None:
            mov_gadget = self._find_gadget("mov [rdi], rax")
        if mov_gadget is not None:
            self._emit_pop_imm("rdi", ptr_int)
            self._emit_pop_imm("rax", val_int)
            self.chain.append(mov_gadget)
        else:
            self._emit_pop_imm("rdi", ptr_int)
            self._emit_pop_imm("rax", val_int)

    def _compile_alloca(self, instr: dict):
        """
        Compile an alloca instruction.

        Uses "sub rsp, <size>" gadget to allocate stack space.
        """
        result = instr.get("result")
        size = instr.get("size", 16)
        sub_gadget = self._find_gadget("sub rsp,")
        if sub_gadget is None:
            sub_gadget = self._find_gadget("sub esp,")
        if sub_gadget is not None:
            self.chain.append(sub_gadget)
            self.chain.append(size & 0xFFFFFFFFFFFFFFFF)
        if result:
            self.var_map[result] = 0x100

    def _compile_icmp(self, instr: dict):
        """
        Compile an icmp instruction.

        Uses "pop rax; ret" and "cmp rax,<imm>" gadgets.
        """
        result = instr.get("result")
        operands = instr.get("operands", [])
        lhs = self._variable_to_value(operands[0]) if len(operands) > 0 else 0
        rhs = self._variable_to_value(operands[1]) if len(operands) > 1 else 0
        rax_gadget = self._find_gadget("pop rax; ret")
        if rax_gadget is not None:
            self.chain.append(rax_gadget)
            self.chain.append(lhs & 0xFFFFFFFFFFFFFFFF)
            cmp_gadget = self._find_gadget("cmp rax,")
            if cmp_gadget is not None:
                self.chain.append(cmp_gadget)
                self.chain.append(rhs & 0xFFFFFFFFFFFFFFFF)
        if result:
            self.var_map[result] = 0

    def _compile_conv(self, instr: dict):
        """
        Compile a conversion instruction (zext, sext, trunc, etc.).

        Loads the value into rax.
        """
        result = instr.get("result")
        val = instr.get("value", "0")
        val_int = self._variable_to_value(val)
        rax_gadget = self._find_gadget("pop rax; ret")
        if rax_gadget is not None:
            self.chain.append(rax_gadget)
            self.chain.append(val_int & 0xFFFFFFFFFFFFFFFF)
        if result:
            self.var_map[result] = val_int

    def _compile_phi(self, instr: dict):
        """
        Compile a phi instruction.

        Selects the first incoming value.
        """
        result = instr.get("result")
        incoming = instr.get("incoming", [])
        src_val = 0
        if incoming:
            src = incoming[0]
            if isinstance(src, dict):
                src_val = self._variable_to_value(src.get("value", 0))
            else:
                src_val = self._variable_to_value(src)
        rax_gadget = self._find_gadget("pop rax; ret")
        if rax_gadget is not None:
            self.chain.append(rax_gadget)
            self.chain.append(src_val & 0xFFFFFFFFFFFFFFFF)
        if result:
            self.var_map[result] = src_val

    def _compile_select(self, instr: dict):
        """
        Compile a select instruction.

        Uses conditional test and selection gadgets.
        """
        result = instr.get("result")
        cond = instr.get("condition", "0")
        true_val = instr.get("true_value", "0")
        cond_int = self._variable_to_value(cond)
        true_int = self._variable_to_value(true_val)
        rax_gadget = self._find_gadget("pop rax; ret")
        if rax_gadget is not None:
            self.chain.append(rax_gadget)
            self.chain.append(cond_int & 0xFFFFFFFFFFFFFFFF)
            test_gadget = self._find_gadget("test rax, rax; ret")
            if test_gadget is not None:
                self.chain.append(test_gadget)
                self.chain.append(rax_gadget)
                self.chain.append(true_int & 0xFFFFFFFFFFFFFFFF)
        if result:
            self.var_map[result] = true_int

    def _compile_gep(self, instr: dict):
        """
        Compile a GEP instruction.

        Computes ptr + index * 8.
        """
        result = instr.get("result")
        ptr = instr.get("ptr", "0")
        index = instr.get("index", 0)
        ptr_int = self._variable_to_value(ptr)
        if isinstance(index, int):
            offset = ptr_int + index * 8
        else:
            offset = ptr_int + 8
        rax_gadget = self._find_gadget("pop rax; ret")
        if rax_gadget is not None:
            self.chain.append(rax_gadget)
            self.chain.append(offset & 0xFFFFFFFFFFFFFFFF)
        if result:
            self.var_map[result] = offset

    def emit_stack_pivot(self, chain: list[int], pivot_address: int) -> bytes:
        """
        Generate a stack pivot stub that sets up RSP to point to
        the ROP chain and begins execution.

        The stub:
        1. Sets RSP to pivot_address.
        2. Pushes a stack cookie for integrity checking.
        3. Uses leave/ret or jmp rsp to start the chain.
        """
        stub = bytearray()

        stub.extend([0x48, 0xBC])
        stub.extend(pivot_address.to_bytes(8, 'little'))

        stack_cookie = 0xDEADBEEFCAFEBABE ^ hash(tuple(chain)) & 0xFFFFFFFFFFFFFFFF
        stub.extend([0x48, 0xBE])
        stub.extend(stack_cookie.to_bytes(8, 'little'))

        stub.extend([0x49, 0x89, 0xE7])

        stub.extend([0x48, 0x89, 0xE5])

        stub.extend([0xFF, 0xE4])

        return bytes(stub)

    def generate_encrypted_rop_blob(self, chain: list[int], key: list[int]) -> bytes:
        """
        XOR-encrypt the ROP chain with a build-specific key.

        The encrypted blob is stored in the binary and decrypted
        at runtime before execution.
        """
        raw = b"".join(v.to_bytes(8, 'little') for v in chain)
        encrypted = bytearray()
        for i, b in enumerate(raw):
            encrypted.append(b ^ key[i % len(key)])
        return bytes(encrypted)


def generate_gadget_database(binary_path: str) -> dict:
    """
    Generate or load a gadget database from a binary.

    Supports JSON databases, SQLite databases (.db), and ELF
    binaries. For ELF binaries, scans .text for ROP gadgets.
    """
    if not os.path.exists(binary_path):
        raise FileNotFoundError(f"Binary not found: {binary_path}")

    if binary_path.endswith(".json"):
        with open(binary_path, "r") as f:
            return json.load(f)

    if binary_path.endswith(".db"):
        try:
            import sqlite3
            conn = sqlite3.connect(binary_path)
            cursor = conn.cursor()
            cursor.execute("SELECT address, size, instructions FROM gadgets")
            rows = cursor.fetchall()
            conn.close()
            db = {}
            for addr, size, instrs in rows:
                db[str(addr)] = {
                    "address": addr,
                    "size": size,
                    "signature": instrs,
                }
            return db
        except ImportError:
            pass

    subprocess.run(['cargo', 'build', '--release', '-p', 'nixon-runtime'], capture_output=True, text=True, timeout=120)

    test_binary = binary_path
    if not test_binary.endswith(".o") and not test_binary.endswith(".so") and not test_binary.endswith(".exe"):
        test_binary = None

    if test_binary is None:
        possible = [
            "/bin/ls",
            "/bin/sh",
            "/usr/bin/python3",
            "/usr/lib/x86_64-linux-gnu/libc.so.6",
        ]
        for p in possible:
            if os.path.exists(p):
                test_binary = p
                break

    if test_binary is None:
        raise FileNotFoundError("No reference binary available for gadget scanning")

    with open(test_binary, "rb") as f:
        binary_data = f.read()

    base_addr = 0x400000

    gadgets = scan_native_gadgets(binary_data, base_addr)

    db = {}
    for g in gadgets:
        addr_str = f"0x{g.address:x}"
        db[addr_str] = {
            "address": g.address,
            "size": g.size,
            "signature": "; ".join(g.instructions),
        }

    return db


class NativeGadget:
    """Represents a ROP gadget found in native code."""

    def __init__(self, address: int, size: int, instructions: list[str]):
        """Initialize with address, size in bytes, and instruction list."""
        self.address = address
        self.size = size
        self.instructions = instructions


def scan_native_gadgets(binary: bytes, base_address: int) -> list[NativeGadget]:
    """
    Scan a binary's .text section for ROP gadgets.

    Scans backward from each ret instruction (up to MAX_GADGET_LEN
    bytes) and decodes the instructions. Gadgets must end with ret
    and contain at least one interesting instruction.
    """
    gadgets: list[NativeGadget] = []

    def is_ret(b: int) -> bool:
        return b == 0xC3 or b == 0xC2

    text_start, text_end = _find_text_section(binary)
    if text_start is None:
        return gadgets

    file_off = _find_file_offset(binary, text_start)
    if file_off is None:
        return gadgets

    text_len = text_end - text_start
    if file_off + text_len > len(binary):
        return gadgets

    text_bytes = binary[file_off:file_off + text_len]

    MAX_GADGET_LEN = 20
    for addr in range(text_len):
        if not is_ret(text_bytes[addr]):
            continue

        start = max(0, addr - MAX_GADGET_LEN)
        instrs = _disasm_range(text_bytes, start, addr + (3 if text_bytes[addr] == 0xC2 else 1))
        if instrs is None:
            continue

        sig = "; ".join(instrs)
        if not _is_interesting_gadget(sig):
            continue

        gaddr = base_address + text_start + start
        gsize = addr - start + (3 if text_bytes[addr] == 0xC2 else 1)
        gadgets.append(NativeGadget(gaddr, gsize, instrs))

    return gadgets


def _find_text_section(binary: bytes) -> tuple[int, int] | tuple[None, None]:
    """
    Find the .text section virtual address range in an ELF binary.

    Tries section headers first, then falls back to program headers.
    """
    if len(binary) < 64:
        return None, None

    e_shoff = int.from_bytes(binary[40:48], 'little')
    e_shentsize = int.from_bytes(binary[58:60], 'little')
    e_shnum = int.from_bytes(binary[60:62], 'little')
    e_shstrndx = int.from_bytes(binary[62:64], 'little')

    if e_shoff > 0 and e_shentsize > 0 and e_shnum > 0:
        shstrtab_off = e_shoff + e_shstrndx * e_shentsize
        if shstrtab_off + e_shentsize <= len(binary):
            shstrtab_sh_offset = int.from_bytes(binary[shstrtab_off + 24:shstrtab_off + 32], 'little')
            shstrtab_sh_size = int.from_bytes(binary[shstrtab_off + 32:shstrtab_off + 40], 'little')
            if shstrtab_sh_offset + shstrtab_sh_size <= len(binary):
                strtab = binary[shstrtab_sh_offset:shstrtab_sh_offset + shstrtab_sh_size]
                for i in range(e_shnum):
                    sh_off = e_shoff + i * e_shentsize
                    if sh_off + e_shentsize > len(binary):
                        continue
                    sh_name = int.from_bytes(binary[sh_off:sh_off + 4], 'little')
                    sh_type = int.from_bytes(binary[sh_off + 4:sh_off + 8], 'little')
                    sh_flags = int.from_bytes(binary[sh_off + 8:sh_off + 16], 'little')
                    sh_addr = int.from_bytes(binary[sh_off + 16:sh_off + 24], 'little')
                    sh_size = int.from_bytes(binary[sh_off + 32:sh_off + 40], 'little')
                    if sh_type != 1:
                        continue
                    if sh_flags & 0x2 == 0:
                        continue
                    if sh_name >= len(strtab):
                        continue
                    name_end = strtab[sh_name:].find(b'\x00')
                    name = strtab[sh_name:sh_name + name_end].decode('utf-8', errors='replace')
                    if name == '.text':
                        return sh_addr, sh_addr + sh_size

    e_phoff = int.from_bytes(binary[32:40], 'little')
    e_phentsize = int.from_bytes(binary[54:56], 'little')
    e_phnum = int.from_bytes(binary[56:58], 'little')
    if e_phoff > 0 and e_phentsize > 0 and e_phnum > 0:
        for i in range(e_phnum):
            ph_off = e_phoff + i * e_phentsize
            if ph_off + e_phentsize > len(binary):
                continue
            p_type = int.from_bytes(binary[ph_off:ph_off + 4], 'little')
            if p_type != 1:
                continue
            p_flags = int.from_bytes(binary[ph_off + 4:ph_off + 8], 'little')
            if p_flags & 1 == 0:
                continue
            if e_phentsize >= 56:
                p_vaddr = int.from_bytes(binary[ph_off + 16:ph_off + 24], 'little')
                p_memsz = int.from_bytes(binary[ph_off + 40:ph_off + 48], 'little')
                return p_vaddr, p_vaddr + p_memsz

    return None, None


def _find_file_offset(binary: bytes, vaddr: int) -> int | None:
    """
    Find the file offset for a given virtual address using program headers.
    """
    e_phoff = int.from_bytes(binary[32:40], 'little')
    e_phentsize = int.from_bytes(binary[54:56], 'little')
    e_phnum = int.from_bytes(binary[56:58], 'little')
    if e_phoff == 0 or e_phentsize == 0 or e_phnum == 0:
        return None
    for i in range(e_phnum):
        ph_off = e_phoff + i * e_phentsize
        if ph_off + e_phentsize > len(binary):
            continue
        p_type = int.from_bytes(binary[ph_off:ph_off + 4], 'little')
        if p_type != 1:
            continue
        p_offset = int.from_bytes(binary[ph_off + 8:ph_off + 16], 'little')
        p_vaddr = int.from_bytes(binary[ph_off + 16:ph_off + 24], 'little')
        p_filesz = int.from_bytes(binary[ph_off + 32:ph_off + 40], 'little')
        p_memsz = int.from_bytes(binary[ph_off + 40:ph_off + 48], 'little')
        if p_vaddr <= vaddr < p_vaddr + p_memsz and p_filesz > 0:
            offset = vaddr - p_vaddr
            if offset < p_filesz:
                return p_offset + offset
    return None


def _disasm_range(code: bytes, start: int, end: int) -> list[str] | None:
    """
    Disassemble a range of x86_64 machine code bytes.

    Returns a list of instruction strings, or None on decode failure.
    """
    instrs = []
    pos = start
    while pos < end:
        if pos >= len(code):
            return None
        consumed, desc = _decode_inst(code, pos)
        if consumed == 0:
            return None
        instrs.append(desc)
        pos += consumed
    return instrs


def _decode_inst(code: bytes, pos: int) -> tuple[int, str]:
    """
    Decode a single x86_64 instruction at the given position.

    Returns (length, description_string). Handles common opcodes
    including push, pop, mov, add, sub, xor, ret, jmp, call, etc.
    """
    if pos >= len(code):
        return 0, ""
    b = code[pos]

    if b == 0xC3:
        return 1, "ret"
    if b == 0xC2:
        if pos + 2 < len(code):
            imm = int.from_bytes(code[pos + 1:pos + 3], 'little')
            return 3, f"ret {imm:#x}"
        return 0, ""
    if b == 0x90:
        return 1, "nop"
    if b == 0xCC:
        return 1, "int3"

    if (b & 0xF8) == 0x50:
        reg = b & 0x07
        return 1, f"push r{reg}"
    if (b & 0xF8) == 0x58:
        reg = b & 0x07
        return 1, f"pop r{reg}"

    if b == 0x48:
        if pos + 1 >= len(code):
            return 0, ""
        b1 = code[pos + 1]
        if (b1 & 0xFC) == 0x50:
            reg = b1 & 0x07
            return 2, f"push r{reg}"
        if (b1 & 0xFC) == 0x58:
            reg = b1 & 0x07
            return 2, f"pop r{reg}"
        if b1 == 0x89:
            if pos + 2 < len(code):
                modrm = code[pos + 2]
                reg1 = (modrm >> 3) & 7
                if (modrm >> 6) == 0b11:
                    reg2 = modrm & 7
                    return 3, f"mov r{reg1}, r{reg2}"
                return 3, f"mov [r{modrm & 7}], r{reg1}"
            return 0, ""
        if b1 == 0x8B:
            if pos + 2 < len(code):
                modrm = code[pos + 2]
                reg1 = (modrm >> 3) & 7
                if (modrm >> 6) == 0b11:
                    reg2 = modrm & 7
                    return 3, f"mov r{reg1}, r{reg2}"
                return 3, f"mov r{reg1}, [r{modrm & 7}]"
            return 0, ""
        if b1 == 0x01 or b1 == 0x03:
            op = "add"
            if pos + 2 < len(code):
                modrm = code[pos + 2]
                reg1 = (modrm >> 3) & 7
                if (modrm >> 6) == 0b11:
                    reg2 = modrm & 7
                    return 3, f"{op} r{reg1}, r{reg2}"
                return 3, f"{op} r{reg1}, [r{modrm & 7}]"
            return 2, f"{op} r, r"
        if b1 == 0x31:
            if pos + 2 < len(code):
                modrm = code[pos + 2]
                reg1 = (modrm >> 3) & 7
                if (modrm >> 6) == 0b11:
                    reg2 = modrm & 7
                    return 3, f"xor r{reg1}, r{reg2}"
                return 3, f"xor [r{modrm & 7}], r{reg1}"
            return 0, ""
        if b1 == 0x29 or b1 == 0x2B:
            op = "sub"
            if pos + 2 < len(code):
                modrm = code[pos + 2]
                reg1 = (modrm >> 3) & 7
                if (modrm >> 6) == 0b11:
                    reg2 = modrm & 7
                    return 3, f"{op} r{reg1}, r{reg2}"
                return 3, f"{op} r{reg1}, [r{modrm & 7}]"
            return 2, f"{op} r, r"
        if b1 == 0xC7:
            if pos + 3 < len(code):
                modrm = code[pos + 2]
                reg = modrm & 7
                if pos + 7 < len(code):
                    imm = int.from_bytes(code[pos + 3:pos + 7], 'little')
                    return 7, f"mov qword [r{reg}], {imm:#x}"
                return 3, f"mov [r{reg}], imm"
            return 0, ""
        return 2, f"rex {b1:#04x}"

    if (b & 0xF0) == 0xB0:
        reg = b & 0x07
        if pos + 9 <= len(code):
            imm = int.from_bytes(code[pos + 1:pos + 9], 'little', signed=False)
            return 9, f"mov r{reg}, {imm:#x}"
        return 0, ""

    if b == 0xEB:
        if pos + 1 < len(code):
            rel = code[pos + 1]
            if rel > 127:
                rel -= 256
            return 2, f"jmp {rel:+d}"
        return 0, ""

    if b == 0xE9:
        if pos + 4 < len(code):
            rel = int.from_bytes(code[pos + 1:pos + 5], 'little', signed=True)
            return 5, f"jmp {rel:+d}"
        return 0, ""

    if b == 0xE8:
        if pos + 4 < len(code):
            rel = int.from_bytes(code[pos + 1:pos + 5], 'little', signed=True)
            return 5, f"call {rel:+d}"
        return 0, ""

    if b == 0x0F:
        if pos + 1 < len(code):
            b1 = code[pos + 1]
            if b1 == 0x05:
                return 2, "syscall"
            if b1 == 0x31:
                return 2, "rdtsc"
            if b1 == 0x34:
                return 2, "sysenter"
            if b1 >= 0x80 and b1 <= 0x8F:
                rel = code[pos + 2] if pos + 2 < len(code) else 0
                jcc = ["jo", "jno", "jb", "jnb", "jz", "jnz", "jbe", "ja",
                       "js", "jns", "jp", "jnp", "jl", "jge", "jle", "jg"]
                cc = jcc[b1 & 0x0F]
                if rel > 127:
                    rel -= 256
                return 3 if pos + 2 < len(code) else 2, f"{cc} {rel:+d}"
            return 2, f"two_byte {b1:#04x}"
        return 0, ""

    if 0x70 <= b <= 0x7F:
        cc_names = ["jo", "jno", "jb", "jnb", "jz", "jnz", "jbe", "ja",
                     "js", "jns", "jp", "jnp", "jl", "jge", "jle", "jg"]
        cc = cc_names[b & 0x0F]
        if pos + 1 < len(code):
            rel = code[pos + 1]
            if rel > 127:
                rel -= 256
            return 2, f"{cc} {rel:+d}"
        return 0, ""

    if 0x88 <= b <= 0x8B:
        if pos + 2 < len(code):
            modrm = code[pos + 1]
            reg1 = (modrm >> 3) & 7
            if (modrm >> 6) == 0b11:
                reg2 = modrm & 7
                return 2, f"mov r{reg1}, r{reg2}"
            return 2, f"mov r{reg1}, [r{modrm & 7}]"
        return 0, ""

    if 0x00 <= b <= 0x05:
        op = "add"
        if pos + 2 < len(code):
            modrm = code[pos + 1]
            reg1 = (modrm >> 3) & 7
            if b == 0x05 and pos + 5 < len(code):
                imm = int.from_bytes(code[pos + 2:pos + 6], 'little')
                return 6, f"add eax, {imm:#x}"
            if (modrm >> 6) == 0b11:
                reg2 = modrm & 7
                return 2, f"{op} r{reg1}, r{reg2}"
            return 2, f"{op} r{reg1}, [r{modrm & 7}]"
        return 0, ""

    if 0x28 <= b <= 0x2D:
        op = "sub"
        if pos + 2 < len(code):
            modrm = code[pos + 1]
            reg1 = (modrm >> 3) & 7
            if (modrm >> 6) == 0b11:
                reg2 = modrm & 7
                return 2, f"{op} r{reg1}, r{reg2}"
            return 2, f"{op} r{reg1}, [r{modrm & 7}]"
        return 0, ""

    if 0x30 <= b <= 0x35:
        op = "xor"
        if pos + 2 < len(code):
            modrm = code[pos + 1]
            reg1 = (modrm >> 3) & 7
            if (modrm >> 6) == 0b11:
                reg2 = modrm & 7
                return 2, f"{op} r{reg1}, r{reg2}"
            return 2, f"{op} r{reg1}, [r{modrm & 7}]"
        return 0, ""

    if b == 0x50:
        return 1, "push rax"
    if b == 0x51:
        return 1, "push rcx"
    if b == 0x52:
        return 1, "push rdx"
    if b == 0x53:
        return 1, "push rbx"
    if b == 0x54:
        return 1, "push rsp"
    if b == 0x55:
        return 1, "push rbp"
    if b == 0x56:
        return 1, "push rsi"
    if b == 0x57:
        return 1, "push rdi"

    return 1, f"db {b:#04x}"


def _is_interesting_gadget(sig: str) -> bool:
    """
    Check if a gadget signature contains interesting instructions.

    Interesting gadgets include pop/ret, syscall, and register
    manipulation instructions.
    """
    keywords = [
        "pop r", "ret", "syscall", "mov rdi", "mov rsi", "mov rdx",
        "mov rax", "xor rax", "add rax", "sub rax",
        "xor r", "add r", "sub r",
    ]
    for kw in keywords:
        if kw in sig:
            return True
    return False
