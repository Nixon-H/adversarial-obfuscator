"""
jit_template.py

Purpose:
JIT template code generation (Advanced Protection). Generates JIT-compiled
template functions that can be instantiated at runtime with different
constants or embedded as inline assembly snippets. Templates are encrypted
and XOR-obfuscated in the binary.

Architectural Role:
Runtime code generation pass. Converts IR functions into template IR with
parameter slots, then encrypts them for runtime decryption and JIT
compilation. Each build produces different template encodings.

Security Relevance:
- Templates are encrypted in the binary with a build-specific key.
- Only the JIT specializer runtime can decrypt and instantiate them.
- The same high-level function produces different machine code at
  different call sites (different slot values = different code).
- Template blobs include integrity hashes via SHA-256.

Threat model: Static analysis, binary diffing, signature detection.

Dependencies:
    - irgen.compile (IrModule, IrFunction, IrBlock, IrInstruction, IrValue, IrType)
"""

from __future__ import annotations
import hashlib
import json
import os
import struct
import sys
import argparse
from typing import Optional
from .compile import IrModule, IrFunction, IrBlock, IrInstruction, IrValue, IrType


def _load_config():
    """Load the project config for phase2 gating."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "default.json")
    try:
        with open(config_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _phase2_enabled() -> bool:
    """Check if phase2 (advanced protection) is enabled in config."""
    cfg = _load_config()
    return cfg.get("shadow_compiler", {}).get("advanced_protection", cfg.get("shadow_compiler", {}).get("phase2", {})).get("enabled", False)


def _xor_encrypt(data: bytes, key: bytes) -> bytes:
    """XOR-encrypt data with a repeating key."""
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])


def generate_template(
    ir_function: IrFunction,
    template_params: list[str],
    seed: bytes
) -> dict:
    """
    Generate a JIT template from an IR function.

    Parameters listed in template_params are replaced with {slot_N}
    placeholders. The specializer IR is also generated.

    Args:
        ir_function: The IR function to template.
        template_params: Parameter names to make templatable.
        seed: Build seed for deterministic slot naming.

    Returns:
        Dict with template_ir, slot_map, specializer_ir, and metadata.
    """
    if not _phase2_enabled():
        raise RuntimeError("Advanced Protection must be enabled for JIT template generation")
    func_name = ir_function.name
    blocks = ir_function.blocks
    template_ir_lines = []
    slot_map = {}
    slot_id = 0
    template_ir_lines.append(f"func @{func_name}_template(")
    param_names = []
    for pname, ptype in ir_function.params:
        if pname in template_params:
            slot_key = f"slot_{slot_id}"
            template_ir_lines.append(f"  %{pname}: {ptype}  ; {{slot_{slot_id}}}")
            slot_map[slot_key] = {
                "param_name": pname,
                "param_type": str(ptype),
                "slot_index": slot_id,
            }
            param_names.append(pname)
            slot_id += 1
        else:
            template_ir_lines.append(f"  %{pname}: {ptype}")
    template_ir_lines.append(") {")
    for block in blocks:
        template_ir_lines.append(f"  {block.label}:")
        for inst in block.instructions:
            inst_str = str(inst)
            for pname in template_params:
                if pname in inst_str:
                    for si in range(slot_id):
                        lookup = f"slot_{si}"
                        if lookup in slot_map and slot_map[lookup]["param_name"] == pname:
                            inst_str = inst_str.replace(f"%{pname}", f"{{slot_{si}}}")
            template_ir_lines.append(f"    {inst_str}")
        if block.terminator:
            template_ir_lines.append(f"    {block.terminator}")
    template_ir_lines.append("}")
    template_ir = "\n".join(template_ir_lines)
    specializer_lines = [
        f"; JIT specializer for @{func_name}",
        "func @__jit_specialize(enc_template: ptr, key_buf: ptr, runtime_vals: ptr) -> ptr {",
        "entry:",
        "  ; Decrypt -> parse IR -> fill slots -> exec alloc -> jit",
        "  %result = call ptr @__jit_internal_specialize(ptr enc_template, ptr key_buf, ptr runtime_vals)",
        "  ret ptr %result",
        "}",
    ]
    specializer_ir = "\n".join(specializer_lines)
    return {
        "template_ir": template_ir,
        "slot_map": slot_map,
        "specializer_ir": specializer_ir,
        "metadata": {
            "function_size_estimate": len(template_ir),
            "num_slots": slot_id,
            "slot_types": [slot_map[s]["param_type"] for s in sorted(slot_map.keys())],
        },
    }


_ENCRYPT_MAGIC = 0x4A4954


def encrypt_template(template: dict, key: bytes) -> bytes:
    """
    Encrypt a JIT template for binary embedding.

    Compresses the template IR, slot map, and specializer IR with
    zlib, XOR-encrypts with the key, and prepends a header with
    magic number, version, and metadata hash.
    """
    if not template:
        return b""
    template_ir_bytes = template.get("template_ir", "").encode("utf-8")
    slot_map_bytes = json.dumps(template.get("slot_map", {}), separators=(",", ":")).encode("utf-8")
    specializer_bytes = template.get("specializer_ir", "").encode("utf-8")
    import zlib
    comp_ir = zlib.compress(template_ir_bytes)
    comp_slot = zlib.compress(slot_map_bytes)
    comp_spec = zlib.compress(specializer_bytes)
    meta = template.get("metadata", {})
    meta_bytes = json.dumps(meta, separators=(",", ":")).encode("utf-8")
    metadata_hash = hashlib.sha256(meta_bytes).digest()
    payload = comp_ir + comp_slot + comp_spec
    xor_key = key.ljust(32, b'\0')[:32]
    encrypted = _xor_encrypt(payload, xor_key)
    header = struct.pack("<III", _ENCRYPT_MAGIC, 1, len(comp_ir))
    header += struct.pack("<II", len(comp_slot), len(comp_spec))
    header += metadata_hash[:32]
    return header + encrypted


def jit_pipeline(
    ir_module: IrModule,
    target_functions: list[str],
    seed: bytes
) -> tuple[IrModule, list[bytes]]:
    """
    Apply JIT templating to target functions in an IR module.

    Returns the modified module with JIT init functions and the
    encrypted template blobs.
    """
    if not _phase2_enabled():
        return ir_module, []
    if seed is None:
        import secrets
        seed = secrets.token_bytes(32)
    result = IrModule(ir_module.name + "_jit")
    template_blobs = []
    for func in ir_module.functions:
        if func.name in target_functions:
            template_params = [p[0] for p in func.params]
            template = generate_template(func, template_params, seed)
            enc_key = hashlib.sha256(seed + func.name.encode()).digest()[:32]
            blob = encrypt_template(template, enc_key)
            template_blobs.append(blob)
            init_func = IrFunction(f"__jit_init_{func.name}", IrType.void())
            entry = init_func.new_block("entry")
            entry.instructions.append(
                IrInstruction('call', result_type=IrType.void(), operands=[],
                              func_name=f"__jit_register_template_{func.name}")
            )
            entry.set_terminator('ret')
            result.functions.append(init_func)
        else:
            result.functions.append(func)
    return result, template_blobs


def main():
    """CLI entry point for JIT template system."""
    parser = argparse.ArgumentParser(
        description="Nixon JIT Template System (Advanced Protection)"
    )
    sub = parser.add_subparsers(dest="command")

    gen_p = sub.add_parser("generate", help="Generate JIT templates from IR")
    gen_p.add_argument("input", help="Input IR file")
    gen_p.add_argument("--functions", required=True, help="Comma-separated function names")

    enc_p = sub.add_parser("encrypt", help="Encrypt a template JSON")
    enc_p.add_argument("input", help="Input template JSON file")
    enc_p.add_argument("-o", "--output", required=True, help="Output encrypted blob file")
    enc_p.add_argument("--key", help="Hex encryption key (32 bytes)")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "generate":
        with open(args.input) as f:
            source = f.read()
        from .compile import compile_py_to_ir
        mod = compile_py_to_ir(source)
        targets = [t.strip() for t in args.functions.split(",")]
        import secrets
        seed = secrets.token_bytes(32)
        for func in mod.functions:
            if func.name in targets:
                template = generate_template(func, [p[0] for p in func.params], seed)
                print(json.dumps(template, indent=2))
    elif args.command == "encrypt":
        with open(args.input) as f:
            template = json.load(f)
        key = bytes.fromhex(args.key) if args.key else b'\0' * 32
        blob = encrypt_template(template, key)
        with open(args.output, "wb") as f:
            f.write(blob)
        print(f"Encrypted template written to {args.output} ({len(blob)} bytes)")


if __name__ == "__main__":
    main()
