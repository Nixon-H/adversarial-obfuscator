import re
import random
import hashlib


def _get_new_var(base: str = "_obf") -> str:
    h = hashlib.md5(f"{base}_{random.randint(0, 2**32)}".encode()).hexdigest()[:12]
    return f"%{base}_{h}"


def _get_new_label(base: str = "L") -> str:
    h = hashlib.md5(f"{base}_{random.randint(0, 2**32)}".encode()).hexdigest()[:12]
    return f"{base}_{h}"


def _split_functions(llvm_ir: str) -> tuple[list[str], list[tuple[str, str, list[str]]]]:
    lines = llvm_ir.split("\n")
    header_lines = []
    functions = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("define ") and stripped.endswith("{"):
            func_header = line
            body_lines = []
            brace_depth = 1
            i += 1
            while i < len(lines) and brace_depth > 0:
                body_lines.append(lines[i])
                for ch in lines[i]:
                    if ch == "{":
                        brace_depth += 1
                    elif ch == "}":
                        brace_depth -= 1
                i += 1
            if body_lines and body_lines[-1].strip() == "}":
                body_lines = body_lines[:-1]
            name_match = re.search(r'@(\S+)', func_header)
            func_name = name_match.group(1) if name_match else "unknown"
            functions.append((func_header, func_name, body_lines))
        else:
            header_lines.append(line)
            i += 1
    return header_lines, functions


def _get_blocks(body_lines: list[str]) -> list[dict]:
    blocks = []
    current_block = None
    current_lines = []

    for line in body_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            if current_block is not None:
                current_lines.append(line)
            continue

        label_match = re.match(r'^([a-zA-Z_$][a-zA-Z0-9_.$]*)\s*:', stripped)
        if label_match:
            if current_block is not None:
                current_block["lines"] = current_lines
                blocks.append(current_block)
            current_block = {
                "name": label_match.group(1),
                "lines": [],
            }
            current_lines = []
            after_label = line[line.index(":") + 1:].strip()
            if after_label:
                indent = "  " if not line.startswith(" ") else line[:len(line) - len(line.lstrip())]
                current_lines.append(f"{indent}{after_label}")
        elif current_block is not None:
            current_lines.append(line)

    if current_block is not None:
        current_block["lines"] = current_lines
        blocks.append(current_block)

    return blocks


def _join_blocks(blocks: list[dict]) -> list[str]:
    lines = []
    for block in blocks:
        lines.append(f"{block['name']}:")
        for l in block.get("lines", []):
            lines.append(l)
    return lines


def apply_bcf(llvm_ir: str, probability: float = 0.3) -> str:
    header, functions = _split_functions(llvm_ir)
    result_header = "\n".join(header)

    result_bodies = []
    for func_header, func_name, body_lines in functions:
        blocks = _get_blocks(body_lines)
        changed = False
        new_blocks = []

        for block in blocks:
            new_blocks.append(block)
            if random.random() > probability:
                continue

            lines = block["lines"]
            term_idx = -1
            for i in range(len(lines) - 1, -1, -1):
                s = lines[i].strip()
                if s.startswith("ret ") or s.startswith("br label") or s.startswith("switch "):
                    term_idx = i
                    break

            if term_idx < 0:
                continue

            term = lines[term_idx].strip()

            if term.startswith("br label"):
                target_match = re.search(r'label\s+%(\S+)', term)
                if not target_match:
                    continue
                origin = target_match.group(1)

                dead = _get_new_label("dead")
                junk = _get_new_label("junk")
                cond = _get_new_var("cond")
                const1 = _get_new_var("c1")
                const2 = _get_new_var("c2")

                insert = [
                    f"  {const1} = add i32 7, 3",
                    f"  {const2} = sub i32 {const1}, 10",
                    f"  {cond} = icmp eq i32 {const2}, 0",
                    f"  br i1 {cond}, label %{origin}, label %{dead}",
                ]
                lines[term_idx:term_idx + 1] = insert

                dv = _get_new_var("dv")
                new_blocks.append({"name": dead, "lines": [
                    f"  {dv} = add i32 1, 1",
                    f"  br label %{origin}",
                ]})
                jv = _get_new_var("jv")
                new_blocks.append({"name": junk, "lines": [
                    f"  {jv} = sub i32 0, 1",
                    f"  br label %{origin}",
                ]})
                changed = True

        if changed:
            body = _join_blocks(new_blocks)
            result_bodies.append(f"{func_header}\n" + "\n".join(body) + "\n}")
        else:
            result_bodies.append(f"{func_header}\n" + "\n".join(body_lines) + "\n}")

    parts = [result_header] if result_header.strip() else []
    parts.extend(result_bodies)
    return "\n".join(parts)


def apply_fla(llvm_ir: str) -> str:
    header, functions = _split_functions(llvm_ir)
    result_header = "\n".join(header)

    result_bodies = []
    for func_header, func_name, body_lines in functions:
        blocks = _get_blocks(body_lines)
        if len(blocks) < 2:
            result_bodies.append(f"{func_header}\n" + "\n".join(body_lines) + "\n}")
            continue

        state = _get_new_var("state")
        dispatcher = _get_new_label("dispatcher")
        entry_label = _get_new_label("entry_fla")

        block_map = {b["name"]: i for i, b in enumerate(blocks)}

        entry_lines = [
            f"  {state} = alloca i32, align 4",
            f"  store i32 0, ptr {state}, align 4",
            f"  br label %{dispatcher}",
        ]

        sw = _get_new_var("sw")
        dispatcher_lines = [
            f"  {sw} = load i32, ptr {state}, align 4",
            f"  switch i32 {sw}, label %{blocks[0]['name']} [",
        ]
        for i, b in enumerate(blocks):
            dispatcher_lines.append(f"    i32 {i}, label %{b['name']}")
        dispatcher_lines.append("  ]")

        for i, block in enumerate(blocks):
            new_lines = []
            term_found = False
            for line in block["lines"]:
                s = line.strip()
                if s.startswith("br label"):
                    target_match = re.search(r'label\s+%(\S+)', s)
                    if target_match:
                        t = target_match.group(1)
                        if t in block_map:
                            new_lines.append(f"  store i32 {block_map[t]}, ptr {state}, align 4")
                            new_lines.append(f"  br label %{dispatcher}")
                            term_found = True
                            continue
                    new_lines.append(line)
                elif re.match(r'br\s+.*,\s*label\s+%(\S+),\s*label\s+%(\S+)', s):
                    cond_match = re.match(r'(br\s+.+),\s*label\s+%(\S+),\s*label\s+%(\S+)', s)
                    if cond_match:
                        cond_part = cond_match.group(1)
                        true_t = cond_match.group(2)
                        false_t = cond_match.group(3)
                        if true_t in block_map and false_t in block_map:
                            csel = _get_new_var("csel")
                            new_lines.append(f"  store i32 {block_map[false_t]}, ptr {state}, align 4")
                            new_lines.append(f"  {csel} = select {cond_part[3:].strip()}, i32 {block_map[true_t]}, i32 {block_map[false_t]}")
                            new_lines.append(f"  store i32 {csel}, ptr {state}, align 4")
                            new_lines.append(f"  br label %{dispatcher}")
                            term_found = True
                            continue
                    new_lines.append(line)
                elif s.startswith("ret ") or s.startswith("switch ") or s.startswith("unreachable"):
                    new_lines.append(line)
                    term_found = True
                else:
                    new_lines.append(line)

            if not term_found and i + 1 < len(blocks):
                new_lines.append(f"  store i32 {i + 1}, ptr {state}, align 4")
                new_lines.append(f"  br label %{dispatcher}")

            block["lines"] = new_lines

        # Move all alloca instructions to the preamble so their SSA results
        # dominate all uses (after flattening, original blocks may not dominate each other).
        # Bare-numbered allocas are renamed (e.g. %17 → %alloca_17) and sorted to keep
        # LLVM's auto-numbering sequential.
        lifted_allocas = []
        for block in blocks:
            kept = []
            for line in block["lines"]:
                stripped = line.strip()
                if re.match(r'^%\d+\s*=\s*alloca\b', stripped):
                    lifted_allocas.append(line)
                elif re.match(r'^%\S+\s*=\s*alloca\b', stripped):
                    lifted_allocas.append(line)
                else:
                    kept.append(line)
            block["lines"] = kept
        # Sort lifted allocas by their numeric value (named allocas go last)
        def _alloca_sort_key(l):
            m = re.match(r'\s*%(\d+)', l)
            if m:
                return (0, int(m.group(1)))
            return (1, l)
        lifted_allocas.sort(key=_alloca_sort_key)
        # Rename bare-number allocas to avoid auto-numbering gaps when placed in preamble
        renumbered = []
        for line in lifted_allocas:
            m = re.match(r'\s*%(\d+)\s*=', line)
            if m:
                old_num = m.group(1)
                new_name = f'%alloca_{old_num}'
                renumbered.append(re.sub(r'^(\s*)%\d+\s*=', rf'\1{new_name} = ', line))
                old_ref = f'%{old_num}'
                for other_block in blocks:
                    other_block["lines"] = [
                        l.replace(old_ref, new_name) for l in other_block["lines"]
                    ]
            else:
                renumbered.append(line)
        lifted_allocas = renumbered
        entry_lines = lifted_allocas + entry_lines

        flat_preamble = {"name": entry_label, "lines": entry_lines}
        flat_dispatcher = {"name": dispatcher, "lines": dispatcher_lines}
        all_blocks = [flat_preamble, flat_dispatcher] + blocks

        body = _join_blocks(all_blocks)
        result_bodies.append(f"{func_header}\n" + "\n".join(body) + "\n}")

    parts = [result_header] if result_header.strip() else []
    parts.extend(result_bodies)
    return "\n".join(parts)


def _sub_instr(line: str) -> str | list[str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith(";"):
        return None

    eq = stripped.find(" = ")
    if eq < 0:
        return None
    result = stripped[:eq].strip()
    rhs = stripped[eq + 3:].strip()

    add_m = re.match(r'add\s+(i\d+)\s+(%\S+)\s*,\s*(%\S+)', rhs)
    if add_m:
        t, a, b = add_m.groups()
        t1, t2, t3 = _get_new_var("t1"), _get_new_var("t2"), _get_new_var("t3")
        return [
            f"  {t1} = xor {t} {a}, {b}",
            f"  {t2} = and {t} {a}, {b}",
            f"  {t3} = shl {t} {t2}, 1",
            f"  {result} = add {t} {t1}, {t3}",
        ]

    sub_m = re.match(r'sub\s+(i\d+)\s+(%\S+)\s*,\s*(%\S+)', rhs)
    if sub_m:
        t, a, b = sub_m.groups()
        t1, t2, t3 = _get_new_var("t1"), _get_new_var("t2"), _get_new_var("t3")
        return [
            f"  {t1} = add {t} {a}, 1",
            f"  {t2} = xor {t} {b}, -1",
            f"  {t3} = add {t} {t1}, {t2}",
            f"  {result} = sub {t} {t3}, 1",
        ]

    mul_m = re.match(r'mul\s+(i\d+)\s+(%\S+)\s*,\s*(%\S+)', rhs)
    if mul_m:
        t, a, b = mul_m.groups()
        t1, t2, t3 = _get_new_var("t1"), _get_new_var("t2"), _get_new_var("t3")
        return [
            f"  {t1} = add {t} {a}, {a}",
            f"  {t2} = sub {t} {t1}, {a}",
            f"  {t3} = mul {t} {t2}, {b}",
            f"  {result} = mul {t} {t3}, 1",
        ]

    xor_m = re.match(r'xor\s+(i\d+)\s+(%\S+)\s*,\s*(%\S+)', rhs)
    if xor_m:
        t, a, b = xor_m.groups()
        t1, t2, t3 = _get_new_var("t1"), _get_new_var("t2"), _get_new_var("t3")
        return [
            f"  {t1} = or {t} {a}, {b}",
            f"  {t2} = and {t} {a}, {b}",
            f"  {t3} = and {t} {t1}, {t2}",
            f"  {result} = xor {t} {t3}, {t1}",
        ]

    return None


def apply_sub(llvm_ir: str, probability: float = 0.5) -> str:
    header, functions = _split_functions(llvm_ir)
    result_header = "\n".join(header)

    result_bodies = []
    for func_header, func_name, body_lines in functions:
        changed = False
        new_body = []
        for line in body_lines:
            if random.random() <= probability:
                sub_result = _sub_instr(line)
                if sub_result is not None:
                    if isinstance(sub_result, list):
                        new_body.extend(sub_result)
                    else:
                        new_body.append(sub_result)
                    changed = True
                    continue
            new_body.append(line)

        if changed:
            result_bodies.append(f"{func_header}\n" + "\n".join(new_body) + "\n}")
        else:
            result_bodies.append(f"{func_header}\n" + "\n".join(body_lines) + "\n}")

    parts = [result_header] if result_header.strip() else []
    parts.extend(result_bodies)
    return "\n".join(parts)


def apply_replay_poison(llvm_ir: str, num_dead_cases: int = 4) -> str:
    header, functions = _split_functions(llvm_ir)
    result_header = "\n".join(header)

    result_bodies = []
    for func_header, func_name, body_lines in functions:
        blocks = _get_blocks(body_lines)
        new_blocks = []

        for block in blocks:
            lines = block["lines"]
            term_idx = -1
            for i in range(len(lines) - 1, -1, -1):
                s = lines[i].strip()
                if s.startswith("switch "):
                    term_idx = i
                    break

            if term_idx < 0:
                new_blocks.append(block)
                continue

            term = lines[term_idx].strip()
            if not term.startswith("switch "):
                new_blocks.append(block)
                continue

            sw_match = re.match(r'switch\s+i32\s+%\S+,\s*label\s+%\S+\s*\[(.*?)\]', term, re.DOTALL)
            if not sw_match:
                new_blocks.append(block)
                continue

            for j in range(num_dead_cases):
                dead_label = _get_new_label("rddead")
                _get_new_var('re')
                _get_new_var('rc')

                insert_line = f"    i32 {j + 1000 + hash(func_name) % 1000}, label %{dead_label}"
                lines.insert(-1, insert_line)

                eb = _get_new_var("eb")
                po = _get_new_var("po")
                new_blocks.append({"name": dead_label, "lines": [
                    f"  {eb} = call i64 @__rdrand_stub()",
                    f"  {po} = alloca i64, align 8",
                    f"  store i64 {eb}, ptr {po}, align 8",
                    f"  br label %{block['name']}",
                ]})

            new_blocks.append(block)

        body = _join_blocks(new_blocks)
        result_bodies.append(f"{func_header}\n" + "\n".join(body) + "\n}")

    parts = [result_header] if result_header.strip() else []
    parts.extend(result_bodies)

    stub = """
declare i64 @__rdrand_stub()

define internal i64 @__rdrand_stub() {
entry:
  %val = call i64 @llvm.readcyclecounter()
  %entropy = xor i64 %val, 123456789
  ret i64 %entropy
}
"""
    result = "\n".join(parts)
    if "declare i64 @llvm.readcyclecounter" not in result:
        result = "declare i64 @llvm.readcyclecounter()\n" + result
    if "define internal i64 @__rdrand_stub" not in result:
        result += stub
    return result


def apply_speculative_traps(ir_text: str, config: dict | None = None) -> str:
    header, functions = _split_functions(ir_text)
    result_header = "\n".join(header)

    result_bodies = []
    for func_header, func_name, body_lines in functions:
        blocks = _get_blocks(body_lines)
        changed = False
        new_blocks = []

        for block in blocks:
            lines = block["lines"]

            cond_br_idx = -1
            cond_var = None
            true_label = None
            false_label = None

            for i in range(len(lines) - 1, -1, -1):
                s = lines[i].strip()
                m = re.match(r'br\s+i1\s+(%\S+),\s*label\s+%(\S+),\s*label\s+%(\S+)', s)
                if m:
                    cond_br_idx = i
                    cond_var = m.group(1)
                    true_label = m.group(2)
                    false_label = m.group(3)
                    break

            if cond_br_idx < 0:
                new_blocks.append(block)
                continue

            changed = True

            spec_trap = _get_new_label("spec_trap")
            real_check = _get_new_label("real_check")
            ext_var = _get_new_var("cmp_ext")
            hint_var = _get_new_var("trap_hint")
            trap_var = _get_new_var("spec_cond")

            keep_lines = lines[:cond_br_idx]
            keep_lines.append(f"  {ext_var} = zext i1 {cond_var} to i64")
            keep_lines.append(f"  {hint_var} = call i64 @llvm.expect.i64(i64 {ext_var}, i64 1)")
            keep_lines.append(f"  {trap_var} = icmp ne i64 {hint_var}, 0")
            keep_lines.append(f"  br i1 {trap_var}, label %{spec_trap}, label %{real_check}")
            block["lines"] = keep_lines
            new_blocks.append(block)

            poison_addr = _get_new_var("poison_addr")
            poison_val = _get_new_var("poison_val")
            chaos1 = _get_new_var("chaos1")
            chaos2 = _get_new_var("chaos2")

            trap_lines = [
                f"  {poison_addr} = getelementptr i8, ptr @__spec_poison_buf, i64 0",
                f"  {poison_val} = load volatile i64, ptr {poison_addr}",
                f"  store volatile i64 {poison_val}, ptr @__spec_state",
                f"  {chaos1} = xor i64 {poison_val}, 2654435769",
                f"  {chaos2} = mul i64 {chaos1}, 3405691582",
                f"  store volatile i64 {chaos2}, ptr @__spec_scratch",
                f"  br label %{real_check}",
            ]
            new_blocks.append({"name": spec_trap, "lines": trap_lines})

            real_lines = [
                f"  br i1 {cond_var}, label %{true_label}, label %{false_label}",
            ]
            new_blocks.append({"name": real_check, "lines": real_lines})

        if changed:
            body = _join_blocks(new_blocks)
            result_bodies.append(f"{func_header}\n" + "\n".join(body) + "\n}")
        else:
            result_bodies.append(f"{func_header}\n" + "\n".join(body_lines) + "\n}")

    parts = [result_header] if result_header.strip() else []
    parts.extend(result_bodies)
    result = "\n".join(parts)

    globals_to_add = ""
    if "@__spec_poison_buf = global" not in result:
        globals_to_add += "@__spec_poison_buf = global [4096 x i8] zeroinitializer\n"
    if "@__spec_state = global" not in result:
        globals_to_add += "@__spec_state = global i64 0\n"
    if "@__spec_scratch = global" not in result:
        globals_to_add += "@__spec_scratch = global i64 0\n"

    if globals_to_add:
        lines = result.split("\n")
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("define "):
                insert_idx = i
                break
        lines.insert(insert_idx, globals_to_add.rstrip())
        result = "\n".join(lines)

    if "declare i64 @llvm.expect.i64" not in result:
        result = "declare i64 @llvm.expect.i64(i64, i64)\n" + result

    return result


def apply_transient_execution(ir_text: str, config: dict) -> str:
    header, functions = _split_functions(ir_text)
    result_header = "\n".join(header)

    has_declare = any("__transient_block_entry" in line for line in header)

    result_bodies = []
    for func_header, func_name, body_lines in functions:
        blocks = _get_blocks(body_lines)
        if len(blocks) < 2:
            result_bodies.append(f"{func_header}\n" + "\n".join(body_lines) + "\n}")
            continue

        new_blocks = []
        prev_name = None
        prev_idx = -1

        for i, block in enumerate(blocks):
            lines = block["lines"]
            term_idx = -1
            for j in range(len(lines) - 1, -1, -1):
                s = lines[j].strip()
                if s.startswith("ret ") or s.startswith("br ") or s.startswith("switch ") or s.startswith("unreachable"):
                    term_idx = j
                    break

            if term_idx >= 0 and prev_name is not None:
                prev_addr = f"ptrtoint (blockaddress(@{func_name.split('(')[0]}, %{prev_name}) to i64)"
                curr_addr = f"ptrtoint (blockaddress(@{func_name.split('(')[0]}, %{block['name']}) to i64)"
                size_expr = f"sub (i64 {curr_addr}, i64 {prev_addr})"
                call_line = f"  call void @__transient_block_entry(i64 {prev_idx}, i64 {prev_addr}, i64 {size_expr})"
                lines.insert(term_idx, call_line)

            block["lines"] = lines
            new_blocks.append(block)
            prev_name = block["name"]
            prev_idx = i

        body = _join_blocks(new_blocks)
        result_bodies.append(f"{func_header}\n" + "\n".join(body) + "\n}")

    result = result_header
    if result_header.strip():
        result += "\n"
    result += "\n".join(result_bodies)

    if not has_declare and "__transient_block_entry" in result:
        declare = "declare void @__transient_block_entry(i64, i64, i64)"
        result = declare + "\n" + result

    return result


def apply_crypto_checkpointing(ir_text: str, config: dict | None = None) -> str:
    if config is None:
        config = {}
    seed = config.get("seed", 0xDEADBEEF)
    header, functions = _split_functions(ir_text)
    result_header = "\n".join(header)

    result_bodies = []
    for func_header, func_name, body_lines in functions:
        blocks = _get_blocks(body_lines)
        new_blocks = []
        block_id_counter = 0
        has_entry = False

        for i, block in enumerate(blocks):
            block_name = block["name"]
            lines = block["lines"]

            term_idx = -1
            for j in range(len(lines) - 1, -1, -1):
                s = lines[j].strip()
                if s.startswith("ret ") or s.startswith("br ") or s.startswith("switch ") or s.startswith("unreachable"):
                    term_idx = j
                    break

            if i == 0:
                has_entry = True
                seed_var = _get_new_var("cseed")
                init_lines = [
                    f"  {seed_var} = call i64 @__cfg_chain_init(i64 {seed})",
                ]
                lines = init_lines + lines
                if term_idx >= 0:
                    term_idx += len(init_lines)

            if term_idx >= 0:
                adv_var = _get_new_var("cadv")
                adv_line = f"  {adv_var} = call i64 @__cfg_advance_chain()"
                lines.insert(term_idx, adv_line)

            if i > 0:
                tok_var = _get_new_var("ctok")
                vld_var = _get_new_var("cvld")
                fail_label = _get_new_label("cfail")
                real_body_label = _get_new_label("creal")

                verify_lines = [
                    f"  {tok_var} = call i64 @__cfg_get_current_token()",
                    f"  {vld_var} = call i1 @__cfg_verify_block(i64 {block_id_counter}, i64 {tok_var})",
                    f"  br i1 {vld_var}, label %{real_body_label}, label %{fail_label}",
                ]
                block_id_counter += 1

                fail_block = {
                    "name": fail_label,
                    "lines": [
                        "  call void @__cfg_abort()",
                        "  unreachable",
                    ],
                }
                new_blocks.append(fail_block)

                wrapper_block = {
                    "name": block_name,
                    "lines": verify_lines,
                }
                new_blocks.append(wrapper_block)

                block["name"] = real_body_label

            new_blocks.append(block)

        if has_entry and block_id_counter > 0:
            fail_block = {
                "name": _get_new_label("cfail"),
                "lines": [
                    "  call void @__cfg_abort()",
                    "  unreachable",
                ],
            }
            new_blocks.append(fail_block)

        body = _join_blocks(new_blocks)
        result_bodies.append(f"{func_header}\n" + "\n".join(body) + "\n}")

    parts = [result_header] if result_header.strip() else []
    parts.extend(result_bodies)
    result = "\n".join(parts)

    decls = """
declare i64 @__cfg_chain_init(i64)
declare i64 @__cfg_advance_chain()
declare i64 @__cfg_get_current_token()
declare i1 @__cfg_verify_block(i64, i64)
declare void @__cfg_abort()
"""
    if "declare i64 @__cfg_chain_init" not in result:
        result = decls + result

    return result


def apply_all(llvm_ir: str, passes: list[str]) -> str:
    result = llvm_ir
    for p in passes:
        p = p.lower().strip()
        if p in ("bcf", "bogus"):
            result = apply_bcf(result)
        elif p in ("fla", "flatten"):
            result = apply_fla(result)
        elif p in ("sub", "substitute"):
            result = apply_sub(result)
        elif p in ("replay", "replay_poison"):
            result = apply_replay_poison(result)
        elif p in ("transient",):
            result = apply_transient_execution(result, {})
        elif p in ("crypto_cfg", "crypto_checkpoint"):
            result = apply_crypto_checkpointing(result)
        elif p in ("speculative", "spec_traps"):
            result = apply_speculative_traps(result)
    return result
