"""Startup integrity check for generated LLVM IR.

The check hashes a copy of the module text that is embedded in the binary and
compares it against a compile-time constant. Both sides are the same bytes, so
the comparison is meaningful: patching the embedded blob (or the constant)
makes the program exit before ``main`` runs.

An earlier version hashed the IR text but compared it against a CRC of a
runtime memory region passed by the caller. Those two values can never agree,
and nothing called the check, so ``--integrity`` only added dead code that
would have aborted the process if it had ever been wired up.
"""

import zlib


def _crc32_string(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def _llvm_string_literal(data: bytes) -> str:
    """Render bytes as an LLVM string constant body (no surrounding quotes)."""
    out = []
    for byte in data:
        if byte in (0x22, 0x5C) or byte < 0x20 or byte > 0x7E:
            out.append(f"\\{byte:02X}")
        else:
            out.append(chr(byte))
    return "".join(out)


def inject_integrity_check(llvm_ir: str) -> str:
    payload = llvm_ir.encode("utf-8")
    checksum = _crc32_string(payload)
    literal = _llvm_string_literal(payload)

    funcs = f"""
; === Shadow Integrity Check ===
@__shadow_ir_blob = private constant [{len(payload)} x i8] c"{literal}"
@__shadow_text_crc32 = internal constant i32 {checksum}

declare i32 @exit(i32)

@llvm.global_ctors = appending global [1 x {{ i32, ptr, ptr }}] [{{ i32, ptr, ptr }} {{ i32 65535, ptr @__shadow_integrity_check, ptr null }}]

define void @__shadow_integrity_check() {{
entry:
  %crc = call i32 @__shadow_crc32_impl(ptr @__shadow_ir_blob, i64 {len(payload)})
  %expected = load i32, ptr @__shadow_text_crc32
  %match = icmp eq i32 %crc, %expected
  br i1 %match, label %ok, label %tamper

ok:
  ret void

tamper:
  call void @__shadow_tamper_handler()
  unreachable
}}

define internal i32 @__shadow_crc32_impl(ptr %data, i64 %size) {{
entry:
  %crc = alloca i32, align 4
  store i32 -1, ptr %crc, align 4
  %table = alloca [256 x i32], align 4
  call void @__shadow_crc32_init_table(ptr %table)
  br label %loop

loop:
  %idx = phi i64 [0, %entry], [%next_idx, %body]
  %cmp = icmp ult i64 %idx, %size
  br i1 %cmp, label %body, label %done

body:
  %ptr = getelementptr i8, ptr %data, i64 %idx
  %byte = load i8, ptr %ptr, align 1
  %cur_crc = load i32, ptr %crc, align 4
  %byte_z = zext i8 %byte to i32
  %idx2 = xor i32 %cur_crc, %byte_z
  %idx2_masked = and i32 %idx2, 255
  %table_ptr = getelementptr [256 x i32], ptr %table, i64 0, i32 %idx2_masked
  %table_val = load i32, ptr %table_ptr, align 4
  %shr = lshr i32 %cur_crc, 8
  %new_crc = xor i32 %shr, %table_val
  store i32 %new_crc, ptr %crc, align 4
  %next_idx = add i64 %idx, 1
  br label %loop

done:
  %final = load i32, ptr %crc, align 4
  %final_inv = xor i32 %final, -1
  ret i32 %final_inv
}}

define internal void @__shadow_crc32_init_table(ptr %table) {{
entry:
  br label %outer

outer:
  %i = phi i32 [0, %entry], [%next_i, %outer_done]
  %i_cmp = icmp ult i32 %i, 256
  br i1 %i_cmp, label %setup, label %done

setup:
  br label %inner

inner:
  %c = phi i32 [%i, %setup], [%c_next, %inner_done]
  %j = phi i32 [0, %setup], [%next_j, %inner_done]
  %j_cmp = icmp ult i32 %j, 8
  br i1 %j_cmp, label %bit, label %outer_done

bit:
  %c_and = and i32 %c, 1
  %is_set = icmp ne i32 %c_and, 0
  %c_shift = lshr i32 %c, 1
  br i1 %is_set, label %xor_branch, label %skip

xor_branch:
  %c_xor = xor i32 %c_shift, 3988292384
  br label %inner_done

skip:
  br label %inner_done

inner_done:
  %c_next = phi i32 [%c_xor, %xor_branch], [%c_shift, %skip]
  %next_j = add i32 %j, 1
  br label %inner

outer_done:
  %gep = getelementptr i32, ptr %table, i32 %i
  store i32 %c, ptr %gep, align 4
  %next_i = add i32 %i, 1
  br label %outer

done:
  ret void
}}

define internal void @__shadow_tamper_handler() {{
  call i32 @exit(i32 -1)
  unreachable
}}
"""

    lines = llvm_ir.split("\n")
    # Insert after the module preamble (source_filename/target lines).
    # Inserting after `target datalayout` alone left `target triple`
    # below the injected functions, which llc rejects.
    insert_at = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("target ", "source_filename")):
            insert_at = i + 1
    result = (lines[:insert_at] + funcs.strip().split("\n")
              + lines[insert_at:])
    return "\n".join(result)
