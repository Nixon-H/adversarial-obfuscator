import zlib


def _crc32_string(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def inject_integrity_check(llvm_ir: str) -> str:
    checksum = _crc32_string(llvm_ir.encode("utf-8"))

    funcs = f"""
; === Shadow Integrity Check ===
@__shadow_text_crc32 = internal constant i32 {checksum}

declare i32 @exit(i32)

define void @__shadow_integrity_check(i8* %base, i64 %size) {{
entry:
  %crc = call i32 @__shadow_crc32_impl(i8* %base, i64 %size)
  %expected = load i32, i32* @__shadow_text_crc32
  %match = icmp eq i32 %crc, %expected
  br i1 %match, label %ok, label %tamper

ok:
  ret void

tamper:
  call i32 @exit(i32 -1)
  ret void
}}

define internal i32 @__shadow_crc32_impl(i8* %data, i64 %size) {{
entry:
  %crc = alloca i32, align 4
  store i32 -1, i32* %crc, align 4
  %table = alloca [256 x i32], align 4
  call void @__shadow_crc32_init_table(ptr %table)
  br label %loop

loop:
  %idx = phi i64 [0, %entry], [%next_idx, %body]
  %cmp = icmp ult i64 %idx, %size
  br i1 %cmp, label %body, label %done

body:
  %ptr = getelementptr i8, i8* %data, i64 %idx
  %byte = load i8, i8* %ptr, align 1
  %cur_crc = load i32, i32* %crc, align 4
  %byte_z = zext i8 %byte to i32
  %idx2 = xor i32 %cur_crc, %byte_z
  %idx2_masked = and i32 %idx2, 255
  %table_ptr = getelementptr [256 x i32], ptr %table, i64 0, i32 %idx2_masked
  %table_val = load i32, i32* %table_ptr, align 4
  %shr = lshr i32 %cur_crc, 8
  %new_crc = xor i32 %shr, %table_val
  store i32 %new_crc, i32* %crc, align 4
  %next_idx = add i64 %idx, 1
  br label %loop

done:
  %final = load i32, i32* %crc, align 4
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

define void @__shadow_tamper_handler() {{
  call i32 @exit(i32 -1)
  unreachable
}}
"""

    lines = llvm_ir.split("\n")
    result = []
    inserted = False
    for line in lines:
        result.append(line)
        if not inserted and "target datalayout" in line:
            for fline in funcs.strip().split("\n"):
                result.append(fline)
            inserted = True

    if not inserted:
        for fline in funcs.strip().split("\n"):
            result.append(fline)

    return "\n".join(result)
