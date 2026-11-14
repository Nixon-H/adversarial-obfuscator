"""Regression tests for the round-3 audit fixes.

Each test pins a defect that was found by reading the code and confirmed by
execution: a wrong arithmetic identity, an encoding mismatch, a dead branch,
or a transform that produced invalid output.
"""

import ast
import subprocess

import pytest

from irgen.compile import IrBlock, IrFunction, IrModule, IrType, IrValue


# ---- llvmgen -------------------------------------------------------------

def test_sub_substitution_is_a_minus_b():
    from llvmgen.passes import _sub_instr

    lines = _sub_instr("  %r = sub i32 %a, %b")
    assert lines is not None
    # Evaluate the emitted sequence with a and b bound to concrete values.
    env = {"%a": 10, "%b": 3}
    for line in lines:
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        target, expr = line.split(" = ", 1)
        op, rest = expr.split(" ", 1)
        rest = rest.split(" ", 1)[1] if rest.split(" ", 1)[0].startswith("i") else rest
        args = [a.strip() for a in rest.split(",", 1)]
        vals = [env.get(a, None) if a.startswith("%") else int(a) for a in args]
        if op == "add":
            env[target] = vals[0] + vals[1]
        elif op == "sub":
            env[target] = vals[0] - vals[1]
        elif op == "xor":
            env[target] = vals[0] ^ vals[1]
        elif op == "and":
            env[target] = vals[0] & vals[1]
        elif op == "shl":
            env[target] = vals[0] << vals[1]
        else:
            raise AssertionError(f"unexpected op {op}")
    assert env["%r"] == 7


def test_gep_ptr_type_lookup_uses_the_stored_key():
    from llvmgen.lower import NixonIRParser

    source = """module @m
func @f(%p: ptr) -> i32 {
entry:
  %q = gep ptr %p, i32 1
  ret i32 0
}
"""
    module = NixonIRParser(source).parse()
    gep = module["functions"][0]["blocks"][0]["instructions"][0]
    assert gep["opcode"] == "getelementptr"
    assert gep["ptr_type"] == "ptr"


def test_integrity_check_is_self_consistent(tmp_path):
    from llvmgen.integrity import inject_integrity_check

    ir = "define i32 @main() {\nentry:\n  ret i32 0\n}\n"
    out = inject_integrity_check(ir)
    assert "@llvm.global_ctors" in out
    assert "__shadow_integrity_check" in out
    # The blob must contain the module text the CRC was taken over.
    assert "ret i32 0" in out


# ---- irgen ---------------------------------------------------------------

def test_watermark_round_trip():
    import irgen.watermark as wm

    module = IrModule("m")
    func = IrFunction("main", IrType.i32())
    module.functions.append(func)
    block = IrBlock("entry")
    func.blocks.append(block)
    block.set_terminator("ret", operands=[])

    payload = b"\xAB\xCD"
    wm.embed_watermark(module, payload, {"build_seed": "seed-1"})
    assert wm.detect_watermark(module, b"seed-1") == payload


def test_watermark_block_is_not_its_own_successor():
    import irgen.watermark as wm

    module = IrModule("m")
    func = IrFunction("main", IrType.i32())
    module.functions.append(func)
    block = IrBlock("entry")
    func.blocks.append(block)
    block.set_terminator("ret", operands=[])

    wm.embed_watermark(module, b"\x01", {"build_seed": "s"})
    for blk in func.blocks:
        if (blk.label.startswith("_wm_") and blk.terminator is not None
                and blk.terminator.opcode == "br"):
            assert len(blk.terminator.operands) >= 3
            assert blk.terminator.operands[1] != blk.label


def test_microjit_pins_stack_pointers():
    from irgen.microjit import MicroJITEngine, REG_RBP, REG_RSP

    engine = MicroJITEngine(seed=7)
    mapping = engine.generate_random_register_map()
    assert mapping[REG_RSP] == REG_RSP
    assert mapping[REG_RBP] == REG_RBP


def test_microjit_never_changes_instruction_length():
    from irgen.microjit import MicroJITEngine

    engine = MicroJITEngine(seed=3)
    # mov rax, rbx ; ret
    code = bytes([0x48, 0x89, 0xD8, 0xC3])
    out = engine.swap_registers(code, {0: 1, 1: 0, 2: 3, 3: 2, 4: 4, 5: 5, 6: 6, 7: 7})
    assert len(out) == len(code)


def test_class_specializer_keeps_definitions_before_uses():
    from irgen.class_specializer import _reschedule_instructions

    class Inst:
        def __init__(self, opcode, operands=(), name=None):
            self.opcode = opcode
            self.operands = list(operands)
            self.result = type("R", (), {"name": name})() if name else None

    class Block:
        def __init__(self, instructions):
            self.instructions = instructions

    class Variant:
        def __init__(self, blocks):
            self.blocks = blocks

    a = Inst("add", [], "%a")
    b = Inst("mul", [a.result], "%b")
    c = Inst("sub", [b.result], "%c")
    block = Block([a, b, c])
    _reschedule_instructions(Variant([block]), 1, b"\x00" * 8)

    order = [inst.result.name for inst in block.instructions]
    assert order.index("%a") < order.index("%b") < order.index("%c")


def test_variant_renamer_keeps_builtins_and_parameters():
    from irgen.variant_pool import _scramble_variable_names

    source = "def f(x):\n    total = 0\n    for i in range(x):\n        total = total + i\n    return total\n"
    renamed = _scramble_variable_names(source, b"seed")
    tree = ast.parse(renamed)
    func = tree.body[0]
    assert func.name == "f"
    assert len(func.args.args) == 1
    # The renamed function must still run.
    namespace = {}
    exec(renamed, namespace)
    assert namespace["f"](4) == 6


def test_fragmentation_coordinator_calls_every_fragment():
    from irgen.fragmentation import generate_coordinator

    frags = [IrFunction(f"frag{i}", IrType.void()) for i in range(4)]
    meta = {"calling_sequence": [0, 1, 2, 3]}
    coord = generate_coordinator(frags, meta, b"seed")
    calls = [i for i in coord.blocks[0].instructions if i.opcode == "call"]
    assert len(calls) == 4


def test_rop_stub_pushes_the_cookie():
    from irgen.rop_compiler import RopFunctionCompiler

    compiler = RopFunctionCompiler({})
    stub = compiler.emit_stack_pivot([0x42424242], 0x1000)
    # mov rax, imm64 ; push rax
    assert bytes([0x48, 0xB8]) in stub
    assert stub[stub.index(bytes([0x48, 0xB8])) + 10] == 0x50


def test_chaff_rotate_avoids_shift_by_width():
    from irgen.chaff_circuits import ChaffCircuitGenerator

    gen = ChaffCircuitGenerator(seed=1)
    block = IrBlock("entry")
    a = IrValue(IrType.i32(), "%a")
    b = IrValue(IrType.i32(), "%b")
    gen._emit_rotl(block, IrType.i32(), a, b)
    # No constant operand may equal the bit width (32) for a shift.
    for inst in block.instructions:
        if inst.opcode in ("shl", "shr"):
            for op in inst.operands:
                if getattr(op, "name", "").isdigit():
                    assert int(op.name) < 32


# ---- scripts -------------------------------------------------------------

def test_micro_fragment_wipes_and_reports_length_mismatch():
    from scripts.fragment.micro_fragment import MicroFragment, MicroFragmentExecutor

    executor = MicroFragmentExecutor(master_key=b"k" * 32, fragment_size=64)
    frag = MicroFragment(index=0, encrypted=b"", plaintext_len=10)
    ok, err = executor.execute_fragment(frag, {}, {})
    assert not ok
    assert "expected 10 bytes" in err


def test_multi_binary_does_not_serialize_cross_keys():
    from scripts.distributed.multi_binary import MultiBinaryDistributor

    dist = MultiBinaryDistributor(master_secret=b"s" * 32)
    binaries, index = dist.distribute([b"alpha", b"beta"], 2)
    blob = index.serialize()
    for key in index.cross_keys:
        assert key not in blob
    assert dist.reconstruct(binaries) == [b"alpha", b"beta"]


def test_cross_key_derivation_is_symmetric():
    from scripts.distributed.multi_binary import MultiBinaryDistributor

    dist = MultiBinaryDistributor(master_secret=b"s" * 32)
    assert dist._derive_cross_key(0, 2) == dist._derive_cross_key(2, 0)


def test_challenge_response_locks_only_on_failure():
    from scripts.runtime.challenge_response import ChallengeResponse

    proto = ChallengeResponse(max_failures=2)
    proto._record_failure("peer-a")
    assert not proto.is_self_destructed()
    proto._record_failure("peer-a")
    assert proto.is_self_destructed()


def test_skip_flags_do_not_conflict_with_unused_features():
    from scripts.conflicts import KNOWN_CONFLICTS, ConflictDetector

    detector = ConflictDetector(KNOWN_CONFLICTS)
    assert detector.check_flags({"skip_llvmgen": True}) == []
    assert detector.check_flags({"skip_irgen": True}) == []


def test_skip_flag_conflicts_when_the_feature_is_requested():
    from scripts.conflicts import KNOWN_CONFLICTS, ConflictDetector

    detector = ConflictDetector(KNOWN_CONFLICTS)
    conflicts = detector.check_flags({"skip_llvmgen": True, "rop": True})
    assert conflicts


# ---- encrypt -------------------------------------------------------------

def test_encrypt_output_is_executable(tmp_path):
    import shutil

    from encrypt.encrypt import encrypt_binary

    if shutil.which("gcc") is None:
        pytest.skip("gcc not available")
    src = tmp_path / "h.c"
    src.write_text("int main(void) { return 0; }\n")
    exe = tmp_path / "h"
    subprocess.run(["gcc", "-O0", "-o", str(exe), str(src)], check=True)
    out = tmp_path / "h.enc"
    encrypt_binary(str(exe), str(out), block_size=64)
    assert out.stat().st_mode & 0o111


# ---- transforms: code checksums ------------------------------------------

def _run_checksum_module(tmp_path, source, rename):
    """Apply the checksum injector (and optionally the renamer), then exec."""
    from obfuscator.core.transforms import CodeChecksumInjector

    tree = CodeChecksumInjector().visit(ast.parse(source))
    if rename:
        from obfuscator.core.transforms import SymbolRenamer

        tree = SymbolRenamer().visit(tree)
    ast.fix_missing_locations(tree)
    path = tmp_path / "mod.py"
    path.write_text(ast.unparse(tree))
    ns = {"__name__": "mod"}
    exec(compile(path.read_text(), str(path), "exec"), ns)
    return ns


def test_code_checksums_do_not_false_positive(tmp_path):
    """The old injector hashed ast.unparse output and compared it against
    inspect.getsource at runtime, so every function of every build that
    enabled the transform raised "integrity check failed"."""
    ns = _run_checksum_module(
        tmp_path,
        "def add(a, b):\n    return a + b\n\ndef mul(a, b):\n    return a * b\n",
        rename=False,
    )
    assert ns["add"](2, 3) == 5
    assert ns["mul"](2, 3) == 6
    ns["_nx_verify"]()


def test_code_checksums_detect_replacement(tmp_path):
    ns = _run_checksum_module(
        tmp_path,
        "def add(a, b):\n    return a + b\n\ndef mul(a, b):\n    return a * b\n",
        rename=False,
    )
    ns["mul"] = lambda a, b: 999
    with pytest.raises(RuntimeError, match="integrity check failed"):
        ns["add"](1, 1)


def test_code_checksums_survive_symbol_rename(tmp_path):
    """Targets are Name nodes, not string literals, so the renamer rewrites
    them with the defs; the baseline keys off __name__ to stay in step."""
    ns = _run_checksum_module(
        tmp_path,
        "def add(a, b):\n    return a + b\n\ndef mul(a, b):\n    return a * b\n",
        rename=True,
    )
    assert ns["_nx_verify"]() is None
    tracked = {k for k in ns["_nx_chk"] if not k.startswith("_nx_")}
    assert len(tracked) == 2
    # Whatever the functions are called now, replacing one is still caught.
    victim = next(iter(tracked))
    ns[victim] = lambda *a, **k: 0
    with pytest.raises(RuntimeError, match="integrity check failed"):
        ns["_nx_verify"]()


def test_code_checksums_skip_methods_and_closures(tmp_path):
    ns = _run_checksum_module(
        tmp_path,
        "def outer(n):\n"
        "    def inner(x):\n"
        "        return x + 1\n"
        "    return inner(n)\n"
        "\n"
        "class K:\n"
        "    def method(self):\n"
        "        return 1\n",
        rename=False,
    )
    assert ns["outer"](1) == 2
    assert ns["K"]().method() == 1
    tracked = {k for k in ns["_nx_chk"] if not k.startswith("_nx_")}
    assert tracked == {"outer"}


def test_code_checksums_preserve_docstrings(tmp_path):
    ns = _run_checksum_module(
        tmp_path,
        'def documented(a):\n    """Keep me."""\n    return a * 2\n',
        rename=False,
    )
    assert ns["documented"].__doc__ == "Keep me."
    assert ns["documented"](3) == 6
