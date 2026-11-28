"""Precision regression tests for the irgen/llvmgen/vm audit (shard D1)."""

import random

import pytest

from irgen.compile import (
    IrBlock,
    IrFunction,
    IrInstruction,
    IrModule,
    IrType,
    IrValue,
    compile_py_to_ir,
)


def test_microjit_rbp_helpers_encode_rbp_not_rip_relative():
    from irgen.microjit import _load_register_from_rbp, _store_register_at_rbp

    # 48 89 85 04 00 00 00 is mov [rbp+4], rax.  The old mod=00 encoding
    # (89 05) was RIP-relative, not frame-relative.
    assert _store_register_at_rbp(0, 4) == bytes.fromhex("48 89 85 04000000")
    assert _load_register_from_rbp(0, 4) == bytes.fromhex("48 8b 85 04000000")
    assert _store_register_at_rbp(0, -4).hex() == "488985fcffffff"


@pytest.mark.parametrize("hexcode,expected", [
    ("4883c001", 4),              # add rax, 1
    ("0501000000", 5),            # add eax, 1
    ("7402", 2),                  # je +2
    ("0f8401000000", 6),          # jz near +1
    ("0f94c0", 3),                # sete al
    ("48c7c001000000", 7),        # mov rax, 1 (C7 /0)
    ("48b80100000000000000", 10), # mov rax, imm64
    ("0f1f00", 3),                # multibyte nop
    ("488b0488", 4),              # mov rax, [rax+rcx*4]
    ("4050", 2),                  # bare REX 0x40 is a valid prefix
    ("c5f877", 0),                # VEX remains fail-closed
])
def test_microjit_instruction_lengths_are_exact(hexcode, expected):
    from irgen.microjit import _instruction_length

    assert _instruction_length(bytes.fromhex(hexcode), 0) == expected


def test_microjit_register_decoding_uses_rex_extensions_and_sib():
    from irgen.microjit import _get_instruction_regs

    assert 8 in _get_instruction_regs(bytes.fromhex("49b80100000000000000"), 0)
    assert 1 not in _get_instruction_regs(bytes.fromhex("49b80100000000000000"), 0)
    assert _get_instruction_regs(bytes.fromhex("58"), 0) == {0}  # pop rax
    regs = _get_instruction_regs(bytes.fromhex("488b0488"), 0)
    assert {0, 1} <= regs  # ModRM reg, SIB base, and SIB index


def test_microjit_sib_register_swap_rewrites_sib_and_preserves_length():
    from irgen.microjit import MicroJITEngine

    code = bytes.fromhex("488b0488")  # mov rax, [rax+rcx*4]
    out = MicroJITEngine(1).swap_registers(code, {0: 1, 1: 0})
    assert out == bytes.fromhex("488b0c81")  # mov rcx, [rcx+rax*4]
    assert len(out) == len(code)


def test_microjit_stack_rewrite_does_not_eat_mov_immediate():
    from irgen.microjit import MicroJITEngine

    code = bytes.fromhex("48b80500000000000000")  # mov rax, 5
    assert MicroJITEngine(1).alter_stack_offsets(code, 8) == code
    frame = bytes.fromhex("488b4504")  # mov rax, [rbp+4]
    assert MicroJITEngine(1).alter_stack_offsets(frame, 8) == bytes.fromhex("488b450c")


def test_ir_zext_result_has_destination_type():
    module = compile_py_to_ir("def f():\n    return True\n")
    func = next(f for f in module.functions if f.name == "f")
    zext = next(i for b in func.blocks for i in b.instructions if i.opcode == "zext")
    assert zext.result.type == IrType.i32()
    assert "zext i1" in str(zext) and "to i32" in str(zext)


def test_ir_statements_after_terminator_stay_unreachable():
    module = compile_py_to_ir('def f():\n    return 1\n    print("x")\n')
    text = str(module)
    assert "__builtin_print" not in text


def test_ir_for_loop_variable_alloca_dominates_use_after_loop():
    module = compile_py_to_ir("def f():\n    for i in [1, 2]:\n        pass\n    return i\n")
    func = next(f for f in module.functions if f.name == "f")
    allocas = [(b.label, i) for b in func.blocks for i in b.instructions if i.opcode == "alloca"]
    assert allocas and all(label == "entry" for label, _ in allocas)


def test_ir_boolop_preserves_python_operand_value():
    module = compile_py_to_ir("def f():\n    x = 0 or 5\n    return x\n")
    text = str(module)
    assert "phi i32 [0," in text and "[5," in text
    assert "phi i1" not in text


def test_ir_nested_boolop_phi_uses_actual_predecessor_label():
    module = compile_py_to_ir("def f():\n    x = 0 or (0 or 5)\n    return x\n")
    text = str(module)
    assert "[%7, label bb5]" in text or re_search_phi_actual(text)


def re_search_phi_actual(text):
    # Value numbering is intentionally not part of the contract; require a
    # phi incoming edge from the nested merge block bb5.
    return "label bb5]" in text


def test_ir_ifexp_uses_branch_value_type_not_hardcoded_i32():
    module = compile_py_to_ir("def f():\n    return 1.5 if True else 2.5\n")
    assert "phi double" in str(module)
    assert "phi i32 [1.5" not in str(module)


def test_optimizer_constant_folding_uses_fixed_width_and_trunc_width():
    from irgen.optimize import _fold_instruction

    add = IrInstruction("add", IrType.i32(), [IrValue.const_int(2147483647), IrValue.const_int(1)])
    assert _fold_instruction(add).name == str(-2147483648)

    trunc = IrInstruction("trunc", IrType.i8(), [IrValue.const_int(258)], ty=IrType.i32())
    assert _fold_instruction(trunc).name == "2"

    shr = IrInstruction("shr", IrType.i32(), [IrValue.const_int(-1), IrValue.const_int(1)])
    assert _fold_instruction(shr).name == "-1"


def test_optimizer_store_load_forwarding_respects_alias_barrier():
    from irgen.optimize import optimize

    func = IrFunction("f", IrType.i32())
    block = IrBlock("entry")
    func.blocks.append(block)
    p = IrValue(IrType.ptr(), "%p")
    one = IrValue.const_int(1)
    two = IrValue.const_int(2)
    zero = IrValue.const_int(0)
    block.store(IrType.i32(), one, p)
    q = block.gep(p, zero)
    block.store(IrType.i32(), two, q.result)
    load = block.load(IrType.i32(), p)
    block.set_terminator("ret", operands=[IrType.i32(), load.result])
    module = IrModule("m")
    module.functions.append(func)

    optimize(module, level=2)
    # The first store must not be forwarded through the intervening aliasing
    # store.  Either the load remains, or the correct second-store value is used.
    ret_value = block.terminator.operands[1]
    assert getattr(ret_value, "name", None) != "1"


def test_bitslice_shift_right_is_arithmetic():
    from irgen.bitslice import BitSliceCompiler

    bits = BitSliceCompiler(word_size=8)
    value = bits.slice_value(0b11110000)  # negative signed byte
    assert bits.recombine(bits.shr_bitslice(value, 1)) == 0b11111000


def test_lower_comment_stripper_preserves_semicolon_in_string():
    from llvmgen.lower import NixonIRParser

    parser = NixonIRParser("")
    assert parser._remove_comments('  store i32 "abc;def", ptr %x ; comment') == 'store i32 "abc;def", ptr %x'


def test_lower_select_emits_i1_condition_type():
    from llvmgen.lower import _emit_instruction

    instr = {"result": "%1", "opcode": "select", "type": "i32",
             "cond": "%c", "true_val": "%a", "false_val": "%b"}
    assert _emit_instruction(instr) == "  %1 = select i1 %c, i32 %a, i32 %b"


def test_lower_renumber_accounts_for_numeric_parameters():
    from llvmgen.lower import _renumber_function

    func = {"params": [{"name": "%0", "type": "i32"}],
            "blocks": [{"instructions": [{"result": "%7", "operands": ["%7"]}]}]}
    _renumber_function(func)
    assert func["blocks"][0]["instructions"][0]["result"] == "%1"


def test_vm_nop_translation_is_single_zero_width_instruction():
    from vm.bytecode_compiler import _Rng, _translate_instruction
    from vm.vm_isa import VMOpcode

    seq = _translate_instruction(IrInstruction("nop"), None, _Rng(b"0" * 16), ctx={})
    assert len(seq) == 1 and seq[0].opcode == VMOpcode.NOP
    assert len(seq[0].encode()) == 1


def test_vm_alloca_store_load_preserve_wide_values():
    from vm.bytecode_compiler import compile_to_bytecode
    from vm.interpreter import VMInterpreter

    module = compile_py_to_ir("def f():\n    a = 300\n    return a\n")
    func = next(f for f in module.functions if f.name == "f")
    bytecode = compile_to_bytecode(func, None, b"1234567890123456")
    state = VMInterpreter(bytes(bytecode)).run(max_steps=100000)
    assert state["halted"]
    assert state["regs"][1] == 300


def test_vm_modulo_register_collision_fails_closed():
    from vm.bytecode_compiler import compile_to_bytecode

    IrValue.reset_counter()
    IrValue(IrType.i32(), "spacer0")  # id 0, not used
    a = IrValue(IrType.i32(), "%a")   # id 1 -> r2
    for i in range(11):
        IrValue(IrType.i32(), f"spacer{i + 1}")
    b = IrValue(IrType.i32(), "%b")   # id 13 -> same r2
    func = IrFunction("collision", IrType.i32())
    block = IrBlock("entry")
    func.blocks.append(block)
    result = block._make("add", IrType.i32(), [a, b])
    block.set_terminator("ret", operands=[IrType.i32(), result.result])
    with pytest.raises(NotImplementedError, match="register allocation collision"):
        compile_to_bytecode(func, None, b"1234567890123456")


def test_fragmentation_preserves_original_when_fragments_are_not_materialized():
    from irgen.fragmentation import fragment_pipeline

    module = compile_py_to_ir("def f():\n    x = 1\n    y = 2\n    z = 3\n    return x + y + z\n")
    out = fragment_pipeline(module, ["f"], num_fragments=2, seed=b"0" * 16)
    original = next(f for f in out.functions if f.name == "f")
    assert sum(len(b.instructions) for b in original.blocks) > 0
    assert original is module.functions[0]


def test_class_specializer_nops_serialize_as_ir():
    from irgen.class_specializer import generate_class_variants

    func = compile_py_to_ir("def f():\n    x = 1\n    return x\n").functions[0]
    variant = generate_class_variants(func, 3, 1)[2]
    text = "\n".join(str(block) for block in variant.blocks)
    assert "nop" in text
    assert "<" not in text and "__main__" not in text


def test_watermark_opaque_predicates_have_correct_truth_values():
    from irgen.watermark import _make_opaque_predicate

    def evaluate(block, predicate):
        env = {}
        for inst in block.instructions:
            args = []
            for op in inst.operands:
                if isinstance(op, IrValue):
                    args.append(env.get(op.name, int(op.name) if op.name.lstrip("-").isdigit() else 0))
            if inst.opcode == "eq":
                value = int(args[0] == args[1])
            elif inst.opcode == "ne":
                value = int(args[0] != args[1])
            elif inst.opcode == "or":
                value = int(bool(args[0]) or bool(args[1]))
            elif inst.opcode == "and":
                value = int(bool(args[0]) and bool(args[1]))
            else:
                continue
            env[inst.result.name] = value
        return env[predicate.result.name]

    for seed in range(8):
        false_block = IrBlock("f")
        false_pred = _make_opaque_predicate(false_block, False, random.Random(seed))
        true_block = IrBlock("t")
        true_pred = _make_opaque_predicate(true_block, True, random.Random(seed))
        assert evaluate(false_block, false_pred) == 0
        assert evaluate(true_block, true_pred) == 1


def test_jit_template_parameter_replacement_respects_identifier_boundary():
    from irgen.jit_template import generate_template

    func = IrFunction("f", IrType.i32())
    func.params = [("x", IrType.i32())]
    block = IrBlock("entry")
    func.blocks.append(block)
    x = IrValue(IrType.i32(), "%x")
    x1 = IrValue(IrType.i32(), "%x1")
    block.add(IrType.i32(), x, x1)
    block.set_terminator("ret", operands=[IrType.i32(), x1])
    out = generate_template(func, ["x"], b"seed")
    assert "{slot_0}, %x1" in out["template_ir"]
    assert "{slot_0}1" not in out["template_ir"]


def test_oram_annotation_does_not_break_explicit_line_continuation():
    from irgen.oram import annotate_oram_variables

    source = "def f():\n    x = 1 + \\\n        2\n    return x\n"
    annotated = annotate_oram_variables(source, ["x"])
    compile(annotated, "<oram-test>", "exec")
    assert "# oram: x" not in annotated.splitlines()[1]
