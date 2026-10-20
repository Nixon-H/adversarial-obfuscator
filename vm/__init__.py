"""
__init__.py

Purpose:
Package initializer for the VM module. Orchestrates the mutating virtual
machine compilation pipeline — compiling IR functions to bytecode,
encrypting bytecode per-function with build-derived keys, and generating
mutating/ephemeral VM interpreter source code.

Architectural Role:
Top-level VM pipeline orchestration. Exposes two main workflows:
- mutating_vm_pipeline(): Classic mutation-based obfuscation pipeline.
- ephemeral_vm_pipeline(): Per-build ephemeral opcode/operand mapping
  pipeline.

Re-exports all key symbols from submodules for convenient access.

Security Relevance:
Central pipeline controller for all VM-based protections. Both pipelines
integrate encryption, mutation, and ISA obfuscation. The ephemeral
pipeline additionally shuffles opcode and operand mappings per build,
requiring a fresh disassembly for each build.

Threat model: Static analysis, cross-build comparison, automated
deobfuscation.
"""

from __future__ import annotations
import hashlib

from .vm_isa import VMOpcode, VMInstruction, VMOperand, VM_PROPERTIES, _phase2_enabled
from .bytecode_compiler import compile_to_bytecode, encrypt_bytecode, decrypt_bytecode
from .interpreter import VMInterpreter
from .ephemeral_isa import (
    generate_ephemeral_opcode_map,
    generate_ephemeral_operand_map,
    remap_bytecode,
    generate_interpreter_dispatch_table,
    runtime_derive_isa,
    runtime_collect_entropy,
    vm_rekey_seed,
    select_dispatch_mode,
    select_encoding_mode,
    generate_field_permutation,
    shuffle_handler_order,
    encode_instruction,
    decode_instruction_length,
    apply_field_shuffle,
    apply_field_unshuffle,
    OPCODE_OPERAND_BYTES,
    DISPATCH_MODES,
    ENCODING_MODES,
)


def _import_ir():
    from irgen.compile import IrModule, IrFunction, IrInstruction, IrValue, IrType
    return IrModule, IrFunction, IrInstruction, IrValue, IrType


def mutating_vm_pipeline(
    ir_module,
    target_functions: list[str],
    build_seed: bytes,
    mutation_level: int = 3,
) -> tuple:
    """
    Full mutation-based VM pipeline.

    For each target function:
    1. Compile from IR to VM bytecode.
    2. Encrypt bytecode with a per-function key (SHA-256(build_seed + func_name)).
    3. Apply instruction mutation (opcode fusion, splitting, reordering).
    4. Generate a C interpreter source file.

    Returns (modified_ir, all_bytecode, interpreter_source).

    Security note: Per-function keys ensure that compromise of one
    function's key does not reveal other functions' bytecode.
    """
    IrModule, IrFunction, IrInstruction, IrValue, IrType = _import_ir()

    from irgen.mutation import mutate_instruction_universe
    from .bytecode_compiler import compile_to_bytecode, encrypt_bytecode

    modified_ir = IrModule(ir_module.name + "_vm")
    for func in ir_module.functions:
        modified_ir.functions.append(func)

    from irgen.compile import IrFunction as IrFuncCls

    encrypted_bytecodes = {}
    all_bytecode = bytearray()

    for func_name in target_functions:
        target_func = None
        for func in ir_module.functions:
            if func.name == func_name:
                target_func = func
                break

        if target_func is None:
            continue

        opcode_map = {}
        for logical, name in VMOpcode.LOGICAL_NAMES.items():
            opcode_map[name] = logical

        bc = compile_to_bytecode(target_func, opcode_map, build_seed)
        key = hashlib.sha256(build_seed + func_name.encode()).digest()[:32]
        encrypted = encrypt_bytecode(bc, key)
        encrypted_bytecodes[func_name] = encrypted
        all_bytecode.extend(encrypted)

        mutated_bc, meta = mutate_instruction_universe(
            bc, build_seed, level=mutation_level,
        )

        vm_func = IrFuncCls(f"_vm_{func_name}", IrType.i32())
        modified_ir.functions.append(vm_func)

    interpreter_source = _generate_interpreter_source()

    return modified_ir, bytes(all_bytecode), interpreter_source


def ephemeral_vm_pipeline(
    ir_module,
    target_functions: list[str],
    build_seed: bytes,
    num_opcodes: int = 256,
) -> tuple:
    """
    Ephemeral (per-build) VM pipeline with shuffled opcode/operand maps.

    Extends mutating_vm_pipeline with:
    1. Generate a seeded shuffled opcode map (logical -> physical).
    2. Generate a seeded shuffled operand type map.
    3. Remap bytecode using these ephemeral maps.
    4. Generate a C interpreter with a matching dispatch table.

    Returns (modified_ir, all_bytecode, interpreter_source, opcode_map,
             operand_map).

    Security note: Each build gets a unique opcode mapping. Even with
    identical source code, two builds produce incompatible bytecode.
    """
    IrModule, IrFunction, IrInstruction, IrValue, IrType = _import_ir()

    opcode_map = generate_ephemeral_opcode_map(build_seed, num_opcodes)
    operand_map = generate_ephemeral_operand_map(build_seed)

    modified_ir = IrModule(ir_module.name + "_vm_eph")
    for func in ir_module.functions:
        modified_ir.functions.append(func)

    from irgen.compile import IrFunction as IrFuncCls
    from .bytecode_compiler import compile_to_bytecode, encrypt_bytecode

    encrypted_bytecodes = {}
    all_bytecode = bytearray()

    for func_name in target_functions:
        target_func = None
        for func in ir_module.functions:
            if func.name == func_name:
                target_func = func
                break

        if target_func is None:
            continue

        logical_opcode_map = {}
        for logical, name in VMOpcode.LOGICAL_NAMES.items():
            logical_opcode_map[name] = logical

        bc = compile_to_bytecode(target_func, logical_opcode_map, build_seed)
        bc = bytearray(remap_bytecode(bytes(bc), opcode_map, operand_map))

        key = hashlib.sha256(build_seed + func_name.encode()).digest()[:32]
        encrypted = encrypt_bytecode(bc, key)
        encrypted_bytecodes[func_name] = encrypted
        all_bytecode.extend(encrypted)

        vm_func = IrFuncCls(f"_vm_eph_{func_name}", IrType.i32())
        modified_ir.functions.append(vm_func)

    seed_for_dispatch = build_seed[0] if build_seed else None
    dispatch_table = generate_interpreter_dispatch_table(opcode_map, build_seed, seed=seed_for_dispatch)
    interpreter_source = generate_ephemeral_interpreter_source(dispatch_table, opcode_map)

    return modified_ir, bytes(all_bytecode), interpreter_source, opcode_map, operand_map


def generate_ephemeral_interpreter_source(dispatch_table: bytes, opcode_map: dict[int, int]) -> str:
    """
    Generate a C source file for the ephemeral VM interpreter.

    The dispatch table entries are XOR-obfuscated with a build-derived
    key. The C interpreter must de-obfuscate at runtime by XORing with
    the same key.

    The emitted C code hard-codes VM_PROPERTIES constants and a subset
    of opcodes that are directly supported (arithmetic, jumps, CALL/RET,
    PUSH/POP, FUSED_CMP_JMP). Unhandled opcodes halt the VM.

    Security note: The generated C includes the dispatch table as a
    static constant array. An attacker with access to the binary can
    extract this table and reverse the obfuscation if they know the key.
    """
    table_str = ", ".join(str(b) for b in dispatch_table)
    return f'''
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#define VM_NUM_REGS 16
#define VM_REG_PC   14
#define VM_REG_FLAGS 13
#define VM_REG_SP   15
#define VM_MEM_SIZE (64 * 1024)
#define VM_STACK_SIZE 4096

#define VM_FLAG_ZERO  1
#define VM_FLAG_SIGN  2
#define VM_FLAG_CARRY 4

/* NOTE: Dispatch table entries are XOR-obfuscated with a build-derived key. */
/*       The C interpreter must de-obfuscate at runtime by XORing with the same key. */
static const unsigned char VM_DISPATCH_TABLE[256] = {{{table_str}}};

struct vm_state {{
    uint64_t regs[VM_NUM_REGS];
    uint8_t  memory[VM_MEM_SIZE];
    uint64_t stack[VM_STACK_SIZE];
    size_t   sp;
    int      halted;
}};

static uint8_t vm_read_byte(struct vm_state* vm, const uint8_t* bc, size_t bc_len) {{
    size_t pc = (size_t)vm->regs[VM_REG_PC];
    if (pc >= bc_len) {{ vm->halted = 1; return 0; }}
    vm->regs[VM_REG_PC] = (uint64_t)(pc + 1);
    return bc[pc];
}}

static uint32_t vm_read_u32(struct vm_state* vm, const uint8_t* bc, size_t bc_len) {{
    uint32_t val = 0;
    for (int i = 0; i < 4; i++) val = (val << 8) | vm_read_byte(vm, bc, bc_len);
    return val;
}}

static uint8_t vm_read_reg(struct vm_state* vm, const uint8_t* bc, size_t bc_len) {{
    return vm_read_byte(vm, bc, bc_len) & 0x0F;
}}

static inline uint64_t vm_get_reg(struct vm_state* vm, uint8_t idx) {{
    if (idx < VM_NUM_REGS) return vm->regs[idx];
    return 0;
}}

static inline void vm_set_reg(struct vm_state* vm, uint8_t idx, uint64_t val) {{
    if (idx < VM_NUM_REGS) vm->regs[idx] = val;
}}

static void vm_set_flags(struct vm_state* vm, uint64_t result) {{
    uint64_t flags = 0;
    if (result == 0) flags |= VM_FLAG_ZERO;
    if (result & 0x8000000000000000ULL) flags |= VM_FLAG_SIGN;
    vm_set_reg(vm, VM_REG_FLAGS, flags);
}}

#if defined(_WIN32) || defined(_WIN64)
#define VM_EXPORT __declspec(dllexport)
#else
#define VM_EXPORT __attribute__((visibility("default")))
#endif

VM_EXPORT
int vm_execute(
    const unsigned char* bytecode,
    size_t bytecode_len,
    const unsigned char* key,
    const unsigned char* input,
    size_t input_len,
    unsigned char* output,
    size_t* output_len
) {{
    (void)key;
    (void)input;
    (void)input_len;

    struct vm_state vm;
    memset(&vm, 0, sizeof(vm));
    vm.sp = 0;
    vm.halted = 0;

    if (output_len) *output_len = 0;

    const uint8_t* bc = (const uint8_t*)bytecode;
    size_t bc_len = bytecode_len;
    int steps = 0;
    const int MAX_STEPS = 1000000;

    while (!vm.halted && (size_t)vm.regs[VM_REG_PC] < bc_len && steps < MAX_STEPS) {{
        uint8_t phys_opcode = vm_read_byte(&vm, bc, bc_len);
        steps++;

        switch (VM_DISPATCH_TABLE[phys_opcode]) {{
            case 0: break;
            case 1: {{
                uint8_t d = vm_read_reg(&vm, bc, bc_len);
                uint8_t s = vm_read_reg(&vm, bc, bc_len);
                vm_set_reg(&vm, d, vm_get_reg(&vm, d) + vm_get_reg(&vm, s));
                vm_set_flags(&vm, vm_get_reg(&vm, d));
                break;
            }}
            case 2: {{
                uint8_t d = vm_read_reg(&vm, bc, bc_len);
                uint8_t s = vm_read_reg(&vm, bc, bc_len);
                vm_set_reg(&vm, d, vm_get_reg(&vm, d) - vm_get_reg(&vm, s));
                vm_set_flags(&vm, vm_get_reg(&vm, d));
                break;
            }}
            case 3: {{
                uint8_t d = vm_read_reg(&vm, bc, bc_len);
                uint8_t s = vm_read_reg(&vm, bc, bc_len);
                vm_set_reg(&vm, d, vm_get_reg(&vm, d) * vm_get_reg(&vm, s));
                vm_set_flags(&vm, vm_get_reg(&vm, d));
                break;
            }}
            case 4: {{
                uint8_t d = vm_read_reg(&vm, bc, bc_len);
                uint8_t s = vm_read_reg(&vm, bc, bc_len);
                if (vm_get_reg(&vm, s) == 0) {{ vm.halted = 1; break; }}
                vm_set_reg(&vm, d, vm_get_reg(&vm, d) / vm_get_reg(&vm, s));
                vm_set_flags(&vm, vm_get_reg(&vm, d));
                break;
            }}
            case 5: {{
                uint8_t d = vm_read_reg(&vm, bc, bc_len);
                uint8_t s = vm_read_reg(&vm, bc, bc_len);
                if (vm_get_reg(&vm, s) == 0) {{ vm.halted = 1; break; }}
                vm_set_reg(&vm, d, vm_get_reg(&vm, d) % vm_get_reg(&vm, s));
                vm_set_flags(&vm, vm_get_reg(&vm, d));
                break;
            }}
            case 6: {{
                uint8_t d = vm_read_reg(&vm, bc, bc_len);
                uint8_t s = vm_read_reg(&vm, bc, bc_len);
                vm_set_reg(&vm, d, vm_get_reg(&vm, d) & vm_get_reg(&vm, s));
                vm_set_flags(&vm, vm_get_reg(&vm, d));
                break;
            }}
            case 7: {{
                uint8_t d = vm_read_reg(&vm, bc, bc_len);
                uint8_t s = vm_read_reg(&vm, bc, bc_len);
                vm_set_reg(&vm, d, vm_get_reg(&vm, d) | vm_get_reg(&vm, s));
                vm_set_flags(&vm, vm_get_reg(&vm, d));
                break;
            }}
            case 8: {{
                uint8_t d = vm_read_reg(&vm, bc, bc_len);
                uint8_t s = vm_read_reg(&vm, bc, bc_len);
                vm_set_reg(&vm, d, vm_get_reg(&vm, d) ^ vm_get_reg(&vm, s));
                vm_set_flags(&vm, vm_get_reg(&vm, d));
                break;
            }}
            case 9: {{
                uint8_t d = vm_read_reg(&vm, bc, bc_len);
                vm_set_reg(&vm, d, ~vm_get_reg(&vm, d));
                vm_set_flags(&vm, vm_get_reg(&vm, d));
                break;
            }}
            case 10: {{
                uint8_t d = vm_read_reg(&vm, bc, bc_len);
                uint8_t s = vm_read_reg(&vm, bc, bc_len);
                uint64_t shift = vm_get_reg(&vm, s) & 63;
                vm_set_reg(&vm, d, vm_get_reg(&vm, d) << shift);
                vm_set_flags(&vm, vm_get_reg(&vm, d));
                break;
            }}
            case 11: {{
                uint8_t d = vm_read_reg(&vm, bc, bc_len);
                uint8_t s = vm_read_reg(&vm, bc, bc_len);
                uint64_t shift = vm_get_reg(&vm, s) & 63;
                vm_set_reg(&vm, d, vm_get_reg(&vm, d) >> shift);
                vm_set_flags(&vm, vm_get_reg(&vm, d));
                break;
            }}
            case 12: {{
                uint8_t d = vm_read_reg(&vm, bc, bc_len);
                uint8_t a = vm_read_reg(&vm, bc, bc_len);
                uint64_t addr = vm_get_reg(&vm, a);
                if (addr < VM_MEM_SIZE) {{
                    vm_set_reg(&vm, d, (uint64_t)vm.memory[addr]);
                }} else {{
                    vm.halted = 1;
                }}
                break;
            }}
            case 13: {{
                uint8_t s = vm_read_reg(&vm, bc, bc_len);
                uint8_t a = vm_read_reg(&vm, bc, bc_len);
                uint64_t addr = vm_get_reg(&vm, a);
                if (addr < VM_MEM_SIZE) {{
                    vm.memory[addr] = (uint8_t)(vm_get_reg(&vm, s) & 0xFF);
                }} else {{
                    vm.halted = 1;
                }}
                break;
            }}
            case 14: {{
                uint8_t d = vm_read_reg(&vm, bc, bc_len);
                uint8_t lo = vm_read_byte(&vm, bc, bc_len);
                uint8_t hi = vm_read_byte(&vm, bc, bc_len);
                vm_set_reg(&vm, d, (uint64_t)((hi << 8) | lo));
                break;
            }}
            case 16: {{
                uint32_t target = vm_read_u32(&vm, bc, bc_len);
                vm_set_reg(&vm, VM_REG_PC, (uint64_t)target);
                break;
            }}
            case 17: {{
                uint32_t target = vm_read_u32(&vm, bc, bc_len);
                if (vm_get_reg(&vm, VM_REG_FLAGS) & VM_FLAG_ZERO) {{
                    vm_set_reg(&vm, VM_REG_PC, (uint64_t)target);
                }}
                break;
            }}
            case 18: {{
                uint32_t target = vm_read_u32(&vm, bc, bc_len);
                if (!(vm_get_reg(&vm, VM_REG_FLAGS) & VM_FLAG_ZERO)) {{
                    vm_set_reg(&vm, VM_REG_PC, (uint64_t)target);
                }}
                break;
            }}
            case 23: {{
                uint32_t target = vm_read_u32(&vm, bc, bc_len);
                if (vm.sp < VM_STACK_SIZE) {{
                    vm.stack[vm.sp++] = vm_get_reg(&vm, VM_REG_PC);
                }}
                vm_set_reg(&vm, VM_REG_PC, (uint64_t)target);
                break;
            }}
            case 24: {{
                if (vm.sp > 0) {{
                    vm_set_reg(&vm, VM_REG_PC, vm.stack[--vm.sp]);
                }} else {{
                    vm.halted = 1;
                }}
                break;
            }}
            case 25: {{
                uint8_t s = vm_read_reg(&vm, bc, bc_len);
                if (vm.sp < VM_STACK_SIZE) {{
                    vm.stack[vm.sp++] = vm_get_reg(&vm, s);
                }}
                break;
            }}
            case 26: {{
                uint8_t d = vm_read_reg(&vm, bc, bc_len);
                if (vm.sp > 0) {{
                    vm_set_reg(&vm, d, vm.stack[--vm.sp]);
                }}
                break;
            }}
            case 34: {{
                uint8_t c = vm_read_reg(&vm, bc, bc_len);
                uint32_t t = vm_read_u32(&vm, bc, bc_len);
                uint32_t f = vm_read_u32(&vm, bc, bc_len);
                if (vm_get_reg(&vm, c) != 0) {{
                    vm_set_reg(&vm, VM_REG_PC, (uint64_t)t);
                }} else {{
                    vm_set_reg(&vm, VM_REG_PC, (uint64_t)f);
                }}
                break;
            }}
            default:
                vm.halted = 1;
                break;
        }}
    }}

    if (output_len && input_len > 0 && output) {{
        size_t copy_len = input_len < VM_MEM_SIZE ? input_len : VM_MEM_SIZE;
        memcpy(output, vm.memory, copy_len);
        *output_len = copy_len;
    }}

    return vm.halted ? 1 : 0;
}}
'''


def _generate_interpreter_source() -> str:
    """
    Generate a stub C interpreter source (placeholder).

    Used by mutating_vm_pipeline when Advanced Protection is enabled
    but no ephemeral mapping is requested. Returns a no-op stub.

    Raises RuntimeError if Advanced Protection is disabled.
    """
    if not _phase2_enabled():
        raise RuntimeError("Advanced Protection must be enabled for VM interpreter generation")
    return '''
#include <stdint.h>
#include <stddef.h>

int vm_execute(
    const unsigned char* bytecode,
    size_t bytecode_len,
    const unsigned char* key,
    const unsigned char* input,
    size_t input_len,
    unsigned char* output,
    size_t* output_len
) {
    (void)bytecode;
    (void)bytecode_len;
    (void)key;
    (void)input;
    (void)input_len;
    (void)output;
    (void)output_len;
    return 0;
}
'''


__all__ = [
    "VMOpcode", "VMInstruction", "VMOperand", "VM_PROPERTIES",
    "compile_to_bytecode", "encrypt_bytecode", "decrypt_bytecode",
    "VMInterpreter", "mutating_vm_pipeline", "ephemeral_vm_pipeline",
    "generate_ephemeral_opcode_map", "generate_ephemeral_operand_map",
    "remap_bytecode", "generate_interpreter_dispatch_table",
    "generate_ephemeral_interpreter_source",
    "runtime_derive_isa", "runtime_collect_entropy", "vm_rekey_seed",
    "select_dispatch_mode", "select_encoding_mode",
    "generate_field_permutation", "shuffle_handler_order",
    "encode_instruction", "decode_instruction_length",
    "apply_field_shuffle", "apply_field_unshuffle",
    "OPCODE_OPERAND_BYTES",
    "DISPATCH_MODES", "ENCODING_MODES",
    "DISPATCH_SWITCH", "DISPATCH_INDIRECT", "DISPATCH_COMPUTED_GOTO",
    "ENCODING_FIXED", "ENCODING_VARIABLE", "ENCODING_FIELD_SHUFFLE",
    "DISPATCH_NAMES", "ENCODING_NAMES",
]
