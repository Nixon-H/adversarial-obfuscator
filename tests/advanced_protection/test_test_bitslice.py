import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestBitSlice:

    @pytest.fixture(autouse=True)
    def reset_ids(self):
        from irgen.compile import IrValue
        IrValue.reset_counter()

    def test_bit_decomposition_64bit(self):
        from irgen.bitslice import BitSliceCompiler
        bsc = BitSliceCompiler(word_size=64)
        bits = bsc.slice_value(0xDEADBEEFCAFEBABE)
        assert len(bits) == 64
        assert bits[0] == 0  # LSB
        assert bits[63] == 1  # MSB
        assert bsc.recombine(bits) == 0xDEADBEEFCAFEBABE
        assert bsc.slice_value(0) == [0] * 64
        assert bsc.slice_value(1) == [1] + [0] * 63
        assert bsc.recombine(bsc.slice_value(42)) == 42

    def test_bit_decomposition_32bit(self):
        from irgen.bitslice import BitSliceCompiler
        bsc = BitSliceCompiler(word_size=32)
        bits = bsc.slice_value(0xDEADBEEF)
        assert len(bits) == 32
        assert bsc.recombine(bits) == 0xDEADBEEF

    def test_add_bitslice(self):
        from irgen.bitslice import BitSliceCompiler
        bsc = BitSliceCompiler(word_size=64)

        a_bits = bsc.slice_value(42)
        b_bits = bsc.slice_value(58)
        result, carry = bsc.add_bitslice(a_bits, b_bits)
        assert bsc.recombine(result) == 100

        result, carry = bsc.add_bitslice(bsc.slice_value(0), bsc.slice_value(0))
        assert bsc.recombine(result) == 0

        result, carry = bsc.add_bitslice(bsc.slice_value(2**63 - 1), bsc.slice_value(1))
        assert bsc.recombine(result) == 2**63
        assert carry == 0

        result, carry = bsc.add_bitslice(bsc.slice_value(123456789), bsc.slice_value(987654321))
        assert bsc.recombine(result) == 123456789 + 987654321

    def test_sub_bitslice(self):
        from irgen.bitslice import BitSliceCompiler
        bsc = BitSliceCompiler(word_size=64)

        result, carry = bsc.sub_bitslice(bsc.slice_value(100), bsc.slice_value(58))
        assert bsc.recombine(result) == 42

        result, carry = bsc.sub_bitslice(bsc.slice_value(42), bsc.slice_value(42))
        assert bsc.recombine(result) == 0

        result, carry = bsc.sub_bitslice(bsc.slice_value(1000), bsc.slice_value(1))
        assert bsc.recombine(result) == 999

    def test_mul_bitslice(self):
        from irgen.bitslice import BitSliceCompiler
        bsc = BitSliceCompiler(word_size=64)

        result, carry = bsc.mul_bitslice(bsc.slice_value(7), bsc.slice_value(6))
        assert bsc.recombine(result) == 42

        result, carry = bsc.mul_bitslice(bsc.slice_value(0), bsc.slice_value(999))
        assert bsc.recombine(result) == 0

        result, carry = bsc.mul_bitslice(bsc.slice_value(123), bsc.slice_value(456))
        assert bsc.recombine(result) == 123 * 456

        result, carry = bsc.mul_bitslice(bsc.slice_value(1), bsc.slice_value(2**60))
        assert bsc.recombine(result) == 2**60

    def test_xor_bitslice(self):
        from irgen.bitslice import BitSliceCompiler
        bsc = BitSliceCompiler(word_size=64)
        a, b = 0xAAAA, 0x5555
        result = bsc.xor_bitslice(bsc.slice_value(a), bsc.slice_value(b))
        assert bsc.recombine(result) == (a ^ b)

    def test_and_bitslice(self):
        from irgen.bitslice import BitSliceCompiler
        bsc = BitSliceCompiler(word_size=64)
        a, b = 0xFF00, 0x0FF0
        result = bsc.and_bitslice(bsc.slice_value(a), bsc.slice_value(b))
        assert bsc.recombine(result) == (a & b)

    def test_or_bitslice(self):
        from irgen.bitslice import BitSliceCompiler
        bsc = BitSliceCompiler(word_size=64)
        a, b = 0xFF00, 0x0FF0
        result = bsc.or_bitslice(bsc.slice_value(a), bsc.slice_value(b))
        assert bsc.recombine(result) == (a | b)

    def test_shl_bitslice(self):
        from irgen.bitslice import BitSliceCompiler
        bsc = BitSliceCompiler(word_size=64)
        val = 0xFF
        result = bsc.shl_bitslice(bsc.slice_value(val), 8)
        assert bsc.recombine(result) == (val << 8)

        result = bsc.shl_bitslice(bsc.slice_value(val), 0)
        assert bsc.recombine(result) == val

        result = bsc.shl_bitslice(bsc.slice_value(1), 63)
        assert bsc.recombine(result) == 2**63

    def test_shr_bitslice(self):
        from irgen.bitslice import BitSliceCompiler
        bsc = BitSliceCompiler(word_size=64)
        val = 0xFF00
        result = bsc.shr_bitslice(bsc.slice_value(val), 8)
        assert bsc.recombine(result) == (val >> 8)

        result = bsc.shr_bitslice(bsc.slice_value(2**63), 63)
        assert bsc.recombine(result) == 1

        result = bsc.shr_bitslice(bsc.slice_value(val), 0)
        assert bsc.recombine(result) == val

    def test_cmp_eq_bitslice(self):
        from irgen.bitslice import BitSliceCompiler
        bsc = BitSliceCompiler(word_size=64)

        eq = bsc.cmp_eq_bitslice(bsc.slice_value(42), bsc.slice_value(42))
        assert eq == [1]

        eq = bsc.cmp_eq_bitslice(bsc.slice_value(42), bsc.slice_value(43))
        assert eq == [0]

    def test_cmp_lt_bitslice(self):
        from irgen.bitslice import BitSliceCompiler
        bsc = BitSliceCompiler(word_size=64)

        lt = bsc.cmp_lt_bitslice(bsc.slice_value(10), bsc.slice_value(20))
        assert lt == [1]

        lt = bsc.cmp_lt_bitslice(bsc.slice_value(20), bsc.slice_value(10))
        assert lt == [0]

        lt = bsc.cmp_lt_bitslice(bsc.slice_value(-5), bsc.slice_value(10))
        assert lt == [1]

        lt = bsc.cmp_lt_bitslice(bsc.slice_value(10), bsc.slice_value(-5))
        assert lt == [0]

        lt = bsc.cmp_lt_bitslice(bsc.slice_value(42), bsc.slice_value(42))
        assert lt == [0]

    def test_word_size_configuration(self):
        from irgen.bitslice import BitSliceCompiler

        bsc32 = BitSliceCompiler(word_size=32)
        bits = bsc32.slice_value(0xFFFFFFFF)
        assert len(bits) == 32
        result, carry = bsc32.add_bitslice(bsc32.slice_value(1), bsc32.slice_value(1))
        assert bsc32.recombine(result) == 2

        bsc64 = BitSliceCompiler(word_size=64)
        bits = bsc64.slice_value(0xFFFFFFFFFFFFFFFF)
        assert len(bits) == 64

    def test_full_ir_transformation_basic(self):
        from irgen.bitslice import transform_ir_function, BitSliceCompiler
        from irgen.compile import IrFunction, IrType, IrValue, IrInstruction

        IrValue.reset_counter()
        func = IrFunction("test_add", IrType.i32())
        entry = func.new_block("entry")
        a = IrValue(IrType.i32())
        a.name = "%a"
        b = IrValue(IrType.i32())
        b.name = "%b"

        val_a = IrValue(IrType.i32())
        val_a.name = "10"
        val_b = IrValue(IrType.i32())
        val_b.name = "20"

        inst = IrInstruction('add', IrType.i32(), [val_a, val_b], ty=IrType.i32())
        inst.parent_block = entry
        entry.instructions.append(inst)

        entry.set_terminator("ret", operands=[IrType.i32(), inst.result])

        compiler = BitSliceCompiler(word_size=32)
        transform_ir_function(func, compiler)

        ir_text = str(func)
        assert " add " not in ir_text, "No add instruction should remain"
        assert " xor " in ir_text or " and " in ir_text or " or " in ir_text

    def test_full_ir_transformation_complex(self):
        from irgen.bitslice import transform_ir_function, BitSliceCompiler
        from irgen.compile import IrFunction, IrType, IrValue, IrInstruction

        IrValue.reset_counter()
        func = IrFunction("test_mixed", IrType.i32())
        entry = func.new_block("entry")

        va = IrValue(IrType.i32())
        va.name = "5"
        vb = IrValue(IrType.i32())
        vb.name = "3"

        add_inst = IrInstruction('add', IrType.i32(), [va, vb], ty=IrType.i32())
        add_inst.parent_block = entry
        entry.instructions.append(add_inst)

        sub_inst = IrInstruction('sub', IrType.i32(), [va, vb], ty=IrType.i32())
        sub_inst.parent_block = entry
        entry.instructions.append(sub_inst)

        eq_inst = IrInstruction('eq', IrType.i32(), [va, vb], ty=IrType.i32())
        eq_inst.parent_block = entry
        entry.instructions.append(eq_inst)

        entry.set_terminator("ret", operands=[IrType.i32(), add_inst.result])

        compiler = BitSliceCompiler(word_size=32)
        transform_ir_function(func, compiler)

        ir_text = str(func)
        assert " add " not in ir_text
        assert " sub " not in ir_text
        assert " eq " not in ir_text
        assert " xor " in ir_text

    def test_generate_bitslice_ir_output(self):
        from irgen.bitslice import generate_bitslice_ir
        from irgen.compile import compile_py_to_ir, ir_module_to_text, IrValue

        IrValue.reset_counter()
        source = "def add(a, b):\n    return a + b\n"
        module = compile_py_to_ir(source)
        ir_text = ir_module_to_text(module)

        result = generate_bitslice_ir(ir_text)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "module @" in result
