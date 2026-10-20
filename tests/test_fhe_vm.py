"""
test_fhe_vm.py

Tests for FHE-VM: scheme, circuit, IR adapter, executor.

Test Categories:
- Positive tests verify scheme correctness (encrypt/decrypt, homomorphic operations),
  circuit construction/evaluation, IR adapter conversion, and executor pipeline.
- Negative tests verify graceful rejection of control flow, too many ops,
  unsupported operations, and empty functions.

Coverage:
- BGV scheme: parameters, key generation, encrypt/decrypt, add/mul/sub, noise tracking
- Circuit: construction, plain/encrypted evaluation, topological sort, IR-based building
- IR adapter: function conversion, output gate wiring
- Compatibility checks: control flow, op count limits, unsupported ops
- Executor: keygen, encrypt, execute, full pipeline, fallback on failure
- Equivalence verification between original IR and FHE circuit
- Phase integration: manifest structure, summary
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.fhe_vm.scheme import BGVParameters, BGVScheme
from scripts.fhe_vm.circuit import FHECircuit, CircuitEvaluator, build_circuit_from_ir
from scripts.fhe_vm.ir_adapter import SSAToFHECircuit, is_fhe_compatible
from scripts.fhe_vm.executor import FHEExecutor, verify_equivalence
from irgen.compile import compile_py_to_ir, IrModule, IrFunction, IrValue, IrType


# =========================================================================
# Scheme tests
# =========================================================================

class TestBGVScheme:
    """
    TestBGVScheme

    Positive test cases for BGV parameter defaults, key generation,
    encrypt/decrypt roundtrips, and homomorphic addition/multiplication/subtraction.
    """
    def test_parameters_defaults(self):
        params = BGVParameters()
        assert params.n == 8
        assert params.t == 7
        assert params.q == 1073741827

    def test_key_generation(self):
        scheme = BGVScheme()
        kp = scheme.keygen()
        assert kp.secret_key is not None
        assert len(kp.secret_key) == 8
        assert kp.public_key is not None
        assert len(kp.public_key) == 2
        assert kp.relin_key is not None
        assert len(kp.relin_key) > 0

    def test_encrypt_decrypt_single(self):
        scheme = BGVScheme()
        scheme.keygen()
        ct = scheme.encrypt(5)
        pt = scheme.decrypt(ct)
        assert pt == 5

    def test_encrypt_decrypt_many_values(self):
        scheme = BGVScheme()
        scheme.keygen()
        for v in [0, 1, 7, 8, -1, -2]:
            ct = scheme.encrypt(v % scheme.params.t)
            pt = scheme.decrypt(ct)
            assert pt == v % scheme.params.t, f"Failed for value {v}"

    def test_encrypt_decrypt_array(self):
        scheme = BGVScheme()
        scheme.keygen()
        values = [1, 2, 3, 4, 5]
        cts = scheme.encrypt_array(values)
        pts = scheme.decrypt_array(cts)
        assert pts == values

    def test_add_homomorphic(self):
        scheme = BGVScheme()
        scheme.keygen()
        ct_a = scheme.encrypt(3)
        ct_b = scheme.encrypt(5)
        ct_sum = scheme.add(ct_a, ct_b)
        pt = scheme.decrypt(ct_sum)
        assert pt == (3 + 5) % scheme.params.t

    def test_mul_homomorphic(self):
        scheme = BGVScheme()
        scheme.keygen()
        ct_a = scheme.encrypt(2)
        ct_b = scheme.encrypt(3)
        ct_prod = scheme.mul(ct_a, ct_b)
        pt = scheme.decrypt(ct_prod)
        assert pt == (2 * 3) % scheme.params.t

    def test_sub_homomorphic(self):
        scheme = BGVScheme()
        scheme.keygen()
        ct_a = scheme.encrypt(10)
        ct_b = scheme.encrypt(3)
        ct_diff = scheme.sub(ct_a, ct_b)
        pt = scheme.decrypt(ct_diff)
        assert pt == (10 - 3) % scheme.params.t

    def test_multiplication_chain(self):
        scheme = BGVScheme()
        scheme.keygen()
        ct_a = scheme.encrypt(2)
        ct_b = scheme.encrypt(3)
        ct_c = scheme.encrypt(4)
        ct_ab = scheme.mul(ct_a, ct_b)
        ct_abc = scheme.mul(ct_ab, ct_c)
        pt = scheme.decrypt(ct_abc)
        assert pt == (2 * 3 * 4) % scheme.params.t

    def test_noise_tracking(self):
        scheme = BGVScheme()
        scheme.keygen()
        tracker = scheme.error_tracker
        assert tracker is not None
        initial_budget = tracker.remaining_budget()
        ct_a = scheme.encrypt(1)
        ct_b = scheme.encrypt(1)
        for _ in range(3):
            ct_a = scheme.mul(ct_a, ct_b)
        assert tracker.ops_since_reset > 0
        assert tracker.remaining_budget() <= initial_budget

    def test_encrypt_with_external_pk(self):
        scheme = BGVScheme()
        kp = scheme.keygen()
        ct = scheme.encrypt(3, pk=kp.public_key)
        pt = scheme.decrypt(ct, sk=kp.secret_key)
        assert pt == 3

    def test_error_growth_exhaustion(self):
        params = BGVParameters(n=4, t=3, q=7)
        scheme = BGVScheme(params)
        scheme.keygen()
        ct_a = scheme.encrypt(1)
        ct_b = scheme.encrypt(1)
        for _ in range(5):
            if scheme.error_tracker and not scheme.error_tracker.is_exhausted():
                ct_a = scheme.mul(ct_a, ct_b)
        assert scheme.error_tracker is None or scheme.error_tracker.ops_since_reset > 0


# =========================================================================
# Circuit tests
# =========================================================================

class TestFHECircuit:
    """
    TestFHECircuit

    Positive test cases for FHE circuit construction, plain/encrypted evaluation,
    topological sorting, IR-based circuit building, and string representation.
    """
    def test_create_circuit(self):
        circuit = FHECircuit("test")
        i1 = circuit.new_gate('input')
        i2 = circuit.new_gate('input')
        a1 = circuit.new_gate('add', [i1, i2])
        circuit.set_output(a1)
        assert circuit.gate_count() == 3
        assert circuit.num_ops() == 1
        assert circuit.output_gate == a1

    def test_circuit_with_const(self):
        circuit = FHECircuit("const_test")
        i1 = circuit.new_gate('input')
        c1 = circuit.new_gate('const', value=5)
        m1 = circuit.new_gate('mul', [i1, c1])
        circuit.set_output(m1)
        assert circuit.const_gates == [c1]
        assert circuit.num_ops() == 1

    def test_plain_evaluate_add(self):
        scheme = BGVScheme()
        scheme.keygen()
        evaluator = CircuitEvaluator(scheme)
        circuit = FHECircuit("add_test")
        i1 = circuit.new_gate('input')
        i2 = circuit.new_gate('input')
        a1 = circuit.new_gate('add', [i1, i2])
        circuit.set_output(a1)
        result = evaluator.evaluate_plain(circuit, [3, 4])
        assert result == (3 + 4) % scheme.params.t

    def test_plain_evaluate_mul(self):
        scheme = BGVScheme()
        scheme.keygen()
        evaluator = CircuitEvaluator(scheme)
        circuit = FHECircuit("mul_test")
        i1 = circuit.new_gate('input')
        i2 = circuit.new_gate('input')
        m1 = circuit.new_gate('mul', [i1, i2])
        circuit.set_output(m1)
        result = evaluator.evaluate_plain(circuit, [3, 4])
        assert result == (3 * 4) % scheme.params.t

    def test_plain_evaluate_complex(self):
        scheme = BGVScheme()
        scheme.keygen()
        evaluator = CircuitEvaluator(scheme)
        circuit = FHECircuit("complex")
        i1 = circuit.new_gate('input')
        i2 = circuit.new_gate('input')
        c1 = circuit.new_gate('const', value=2)
        m1 = circuit.new_gate('mul', [i1, i2])
        a1 = circuit.new_gate('add', [m1, c1])
        circuit.set_output(a1)
        result = evaluator.evaluate_plain(circuit, [3, 4])
        assert result == (3 * 4 + 2) % scheme.params.t

    def test_encrypted_evaluate(self):
        scheme = BGVScheme()
        scheme.keygen()
        evaluator = CircuitEvaluator(scheme)
        circuit = FHECircuit("enc_test")
        i1 = circuit.new_gate('input')
        i2 = circuit.new_gate('input')
        a1 = circuit.new_gate('add', [i1, i2])
        circuit.set_output(a1)
        ct1 = scheme.encrypt(3)
        ct2 = scheme.encrypt(4)
        ct_result = evaluator.evaluate_encrypted(circuit, [ct1, ct2])
        pt = scheme.decrypt(ct_result)
        expected = (3 + 4) % scheme.params.t
        assert pt == expected

    def test_topological_sort(self):
        scheme = BGVScheme()
        scheme.keygen()
        evaluator = CircuitEvaluator(scheme)
        circuit = FHECircuit("sort_test")
        i1 = circuit.new_gate('input')
        i2 = circuit.new_gate('input')
        m1 = circuit.new_gate('mul', [i1, i2])
        a1 = circuit.new_gate('add', [m1, i1])
        circuit.set_output(a1)
        order = evaluator._topological_sort(circuit)
        assert len(order) == circuit.gate_count()
        i1_idx = order.index(i1)
        i2_idx = order.index(i2)
        m1_idx = order.index(m1)
        a1_idx = order.index(a1)
        assert m1_idx > i1_idx
        assert m1_idx > i2_idx
        assert a1_idx > m1_idx

    def test_build_circuit_from_ir(self):
        source = """
def add(a, b):
    return a + b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        circuit = build_circuit_from_ir(func)
        assert circuit.name == "add"
        assert circuit.num_ops() >= 1

    def test_circuit_str(self):
        circuit = FHECircuit("test")
        i1 = circuit.new_gate('input')
        i2 = circuit.new_gate('input')
        a1 = circuit.new_gate('add', [i1, i2])
        circuit.set_output(a1)
        s = str(circuit)
        assert "circuit @test" in s
        assert "input" in s
        assert "add" in s


# =========================================================================
# IR Adapter tests
# =========================================================================

class TestSSAToFHECircuit:
    """
    TestSSAToFHECircuit

    Positive test cases for converting SSA IR functions into FHE circuits,
    covering addition, multiplication, complex arithmetic, and constants.
    """
    def test_simple_add(self):
        source = """
def add(a, b):
    return a + b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        adapter = SSAToFHECircuit()
        circuit = adapter.convert_function(func)
        assert circuit is not None
        assert circuit.num_ops() >= 1

    def test_simple_mul(self):
        source = """
def mul(a, b):
    return a * b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        adapter = SSAToFHECircuit()
        circuit = adapter.convert_function(func)
        assert circuit is not None

    def test_complex_arithmetic(self):
        source = """
def compute(a, b):
    return a * b + a
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        adapter = SSAToFHECircuit()
        circuit = adapter.convert_function(func)
        assert circuit is not None
        assert circuit.num_ops() >= 2

    def test_with_constants(self):
        source = """
def add_const(a):
    return a + 5
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        adapter = SSAToFHECircuit()
        circuit = adapter.convert_function(func)
        assert circuit is not None

    def test_output_gate_set(self):
        source = """
def add(a, b):
    return a + b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        adapter = SSAToFHECircuit()
        circuit = adapter.convert_function(func)
        assert circuit.output_gate is not None


# =========================================================================
# is_fhe_compatible tests
# =========================================================================

class TestCompatibility:
    """
    TestCompatibility

    Positive and negative test cases for FHE compatibility checks,
    validating which IR functions can be expressed as FHE circuits.
    """
    def test_compatible_simple(self):
        source = """
def add(a, b):
    return a + b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        compatible, reason = is_fhe_compatible(func)
        assert compatible, f"Should be compatible: {reason}"

    def test_compatible_mul(self):
        source = """
def mul(a, b):
    return a * b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        compatible, reason = is_fhe_compatible(func)
        assert compatible, f"Should be compatible: {reason}"

    def test_incompatible_control_flow(self):
        source = """
def max(a, b):
    if a > b:
        return a
    return b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        compatible, reason = is_fhe_compatible(func)
        assert not compatible
        assert "control flow" in reason or "multiple" in reason or "block" in reason

    def test_incompatible_too_many_ops(self):
        def build_big_function():
            mod = IrModule("test")
            func = IrFunction("big", IrType.i32())
            func.params.append(("a", IrType.i32()))
            entry = func.new_block("entry")
            for _ in range(15):
                entry.add(IrType.i32(), IrValue.const_int(1), IrValue.const_int(1))
            entry.set_terminator("ret", operands=[IrType.i32(), IrValue.const_int(0)])
            mod.functions.append(func)
            return mod
        mod = build_big_function()
        func = mod.functions[0]
        compatible, reason = is_fhe_compatible(func)
        assert not compatible
        assert "too many" in reason

    def test_incompatible_unsupported_op(self):
        source = """
def with_call(a):
    return abs(a)
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        compatible, reason = is_fhe_compatible(func)
        assert not compatible

    def test_compatible_sub(self):
        source = """
def sub(a, b):
    return a - b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        compatible, reason = is_fhe_compatible(func)
        assert compatible, f"Should be compatible: {reason}"


# =========================================================================
# Executor tests
# =========================================================================

class TestFHEExecutor:
    """
    TestFHEExecutor

    Positive test cases for the FHE executor pipeline: key generation,
    input encryption, circuit execution, result decryption, and timing metadata.
    """
    def test_generate_keys(self):
        executor = FHEExecutor()
        kp = executor.generate_keys()
        assert kp is not None
        assert kp.secret_key is not None

    def test_encrypt_inputs(self):
        executor = FHEExecutor()
        executor.generate_keys()
        cts = executor.encrypt_inputs([1, 2, 3])
        assert len(cts) == 3

    def test_execute_add_circuit(self):
        executor = FHEExecutor()
        executor.generate_keys()
        circuit = FHECircuit("add")
        i1 = circuit.new_gate('input')
        i2 = circuit.new_gate('input')
        a1 = circuit.new_gate('add', [i1, i2])
        circuit.set_output(a1)
        cts = executor.encrypt_inputs([3, 4])
        ct_result = executor.execute(circuit, cts)
        pt = executor.decrypt_result(ct_result)
        assert pt == (3 + 4) % executor.scheme.params.t

    def test_full_pipeline_success(self):
        executor = FHEExecutor()
        circuit = FHECircuit("mul")
        i1 = circuit.new_gate('input')
        i2 = circuit.new_gate('input')
        m1 = circuit.new_gate('mul', [i1, i2])
        circuit.set_output(m1)
        result = executor.run_full_pipeline(circuit, [2, 3])
        assert result['success']
        assert result['result'] == (2 * 3) % executor.scheme.params.t

    def test_full_pipeline_timings(self):
        executor = FHEExecutor()
        circuit = FHECircuit("add")
        i1 = circuit.new_gate('input')
        i2 = circuit.new_gate('input')
        a1 = circuit.new_gate('add', [i1, i2])
        circuit.set_output(a1)
        result = executor.run_full_pipeline(circuit, [5, 7])
        assert result['success']
        assert 'keygen' in result['timings']
        assert 'encrypt' in result['timings']
        assert 'evaluate' in result['timings']
        assert 'decrypt' in result['timings']

    def test_fallback_on_failure(self):
        executor = FHEExecutor()
        circuit = FHECircuit("bad")
        i1 = circuit.new_gate('input')
        i2 = circuit.new_gate('input')
        circuit.new_gate('mul', [i1, i2])
        circuit.set_output(i1)
        result = executor.run_full_pipeline(circuit, [1, 1])
        assert result['success']


# =========================================================================
# Equivalence verification tests
# =========================================================================

class TestEquivalence:
    """
    TestEquivalence

    Positive test cases verifying that original IR functions and their
    FHE circuit counterparts produce equivalent outputs for given inputs.
    """
    def test_simple_add_equivalent(self):
        source = """
def add(a, b):
    return a + b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        adapter = SSAToFHECircuit()
        circuit = adapter.convert_function(func)
        eq_result = verify_equivalence(func, circuit)
        assert eq_result['equivalent'], f"Circuit should be equivalent: {eq_result['failures']}/{eq_result['total']} failed"

    def test_simple_mul_equivalent(self):
        source = """
def mul(a, b):
    return a * b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        adapter = SSAToFHECircuit()
        circuit = adapter.convert_function(func)
        eq_result = verify_equivalence(func, circuit)
        assert eq_result['equivalent']

    def test_complex_equivalent(self):
        source = """
def compute(a, b):
    return a * b + a
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        adapter = SSAToFHECircuit()
        circuit = adapter.convert_function(func)
        eq_result = verify_equivalence(func, circuit)
        assert eq_result['equivalent']

    def test_sub_equivalent(self):
        source = """
def sub(a, b):
    return a - b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        adapter = SSAToFHECircuit()
        circuit = adapter.convert_function(func)
        eq_result = verify_equivalence(func, circuit)
        assert eq_result['equivalent']

    def test_input_output_equivalence(self):
        executor = FHEExecutor()
        source = """
def add(a, b):
    return a + b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        adapter = SSAToFHECircuit()
        circuit = adapter.convert_function(func)
        executor.generate_keys()
        cts = executor.encrypt_inputs([3, 4])
        ct_result = executor.execute(circuit, cts)
        pt = executor.decrypt_result(ct_result)
        eq_result = verify_equivalence(func, circuit, [[3, 4]])
        expected = eq_result['details'][0]['expected']
        assert pt == expected, f"Encrypted result {pt} != plain expected {expected}"


# =========================================================================
# Negative tests
# =========================================================================

class TestNegative:
    """
    TestNegative

    Negative test cases — exercises error handling, edge cases, and
    invalid input rejection for FHE-VM components.
    """
    def test_control_flow_rejected(self):
        source = """
def with_loop(n):
    s = 0
    for i in range(n):
        s += i
    return s
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        compatible, reason = is_fhe_compatible(func)
        assert not compatible, "Control flow should be rejected"

    def test_too_many_ops_rejected(self):
        source = """
def many_ops(a, b, c, d, e, f, g, h):
    x1 = a + b
    x2 = c + d
    x3 = e + f
    x4 = g + h
    x5 = x1 * x2
    x6 = x3 * x4
    x7 = x5 + x6
    x8 = x7 * a
    x9 = x8 + b
    x10 = x9 * c
    x11 = x10 + d
    return x11
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        compatible, reason = is_fhe_compatible(func)
        assert not compatible, "Too many ops should be rejected"

    def test_unsupported_op_rejected(self):
        source = """
def with_call(a):
    return abs(a)
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        compatible, reason = is_fhe_compatible(func)
        assert not compatible, "Functions with calls should be rejected"

    def test_empty_function_rejected(self):
        source = """
def empty():
    pass
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        compatible, reason = is_fhe_compatible(func)
        assert not compatible, f"Empty function should be rejected: {reason}"

    def test_adapter_raises_on_incompatible(self):
        source = """
def max(a, b):
    if a > b:
        return a
    return b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        adapter = SSAToFHECircuit()
        with pytest.raises(ValueError, match="not FHE-compatible"):
            adapter.convert_function(func)

    def test_no_op_functions_handle_gracefully(self):
        source = """
def identity(a):
    return a
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        adapter = SSAToFHECircuit()
        circuit = adapter.convert_function(func)
        assert circuit is not None


# =========================================================================
# Phase test
# =========================================================================

class TestPhase:
    """
    TestPhase

    Integration tests for the FHE-VM phase: importability, execution,
    and manifest structure verification.
    """
    def test_phase_importable(self):
        from scripts.phases.phase_fhe_vm import phase_fhe_vm
        assert phase_fhe_vm is not None

    def test_phase_runs_without_error(self):
        from scripts.phases.phase_fhe_vm import phase_fhe_vm
        import argparse
        args = argparse.Namespace(
            fhe_vm=True,
            fhe_vm_functions=None,
            payload=None,
        )
        source = """
def add(a, b):
    return a + b
"""
        ir_module = compile_py_to_ir(source)
        result = phase_fhe_vm(args, ir_module)
        assert result is not None
        assert 'functions' in result
        assert 'add' in result['functions']

    def test_phase_manifest_structure(self):
        from scripts.phases.phase_fhe_vm import phase_fhe_vm
        import argparse
        args = argparse.Namespace(
            fhe_vm=True,
            fhe_vm_functions=None,
            payload=None,
        )
        source = """
def add(a, b):
    return a + b

def mul(a, b):
    return a * b
"""
        ir_module = compile_py_to_ir(source)
        result = phase_fhe_vm(args, ir_module)
        assert 'summary' in result
        assert result['summary']['total_functions'] >= 2
