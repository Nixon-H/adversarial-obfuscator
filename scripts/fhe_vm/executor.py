"""
executor.py

Purpose:
Orchestrates the full FHE execution pipeline: key generation, input
encryption, circuit evaluation, and result decryption. Also provides
equivalence verification between the original IR function and the
FHE circuit.

Architectural Role:
Execution layer for the FHE VM. FHEExecutor wraps the BGV scheme,
circuit evaluator, and timing instrumentation into a unified API.
verify_equivalence() is a standalone function for testing correctness.

Execution Context:
FHEExecutor is instantiated when --fhe-vm is active. The
run_full_pipeline() method executes keygen -> encrypt -> execute ->
decrypt. Timing data is collected per stage for performance analysis.

Dependencies:
- scheme (BGVScheme, BGVParameters, BGVKeyPair)
- circuit (FHECircuit, CircuitEvaluator)
- ir_adapter (SSAToFHECircuit, is_fhe_compatible)
- irgen.compile (IrValue) for plaintext evaluation
- Standard library (time, typing)

Security Relevance:
The FHE execution pipeline provides computation on encrypted data.
The equivalence verification (verify_equivalence()) is critical: it
ensures the FHE circuit computes the same function as the original
IR. Without this check, a buggy circuit could silently produce wrong
results.

Maintenance Notes:
- _evaluate_ir_plain() is a simplified IR interpreter that handles
  only alloca/store/load/add/sub/mul/ret. Complex functions with
  control flow or calls will produce incorrect plaintext results.
- The run_full_pipeline() method catches all exceptions and returns
  a failure dict rather than propagating errors.
"""

from __future__ import annotations
import time
from typing import Optional, Any

from irgen.compile import IrValue
from .scheme import BGVScheme, BGVParameters, BGVKeyPair
from .circuit import FHECircuit, CircuitEvaluator
from .ir_adapter import SSAToFHECircuit, is_fhe_compatible


class FHEExecutor:
    def __init__(self, params: Optional[BGVParameters] = None):
        self.scheme = BGVScheme(params)
        self.keypair: Optional[BGVKeyPair] = None
        self.evaluator: Optional[CircuitEvaluator] = None
        self._timings: dict[str, float] = {}

    def generate_keys(self) -> BGVKeyPair:
        t0 = time.perf_counter()
        self.keypair = self.scheme.keygen()
        self.evaluator = CircuitEvaluator(self.scheme)
        elapsed = time.perf_counter() - t0
        self._timings['keygen'] = elapsed
        return self.keypair

    def encrypt_inputs(self, values: list[int]) -> list:
        t0 = time.perf_counter()
        result = self.scheme.encrypt_array(values)
        elapsed = time.perf_counter() - t0
        self._timings['encrypt'] = elapsed
        return result

    def execute(self, circuit: FHECircuit,
                encrypted_inputs: list) -> Any:
        if self.evaluator is None:
            raise RuntimeError("No evaluator; call generate_keys() first")
        t0 = time.perf_counter()
        result = self.evaluator.evaluate_encrypted(circuit, encrypted_inputs)
        elapsed = time.perf_counter() - t0
        self._timings['evaluate'] = elapsed
        return result

    def decrypt_result(self, ct_result) -> int:
        t0 = time.perf_counter()
        val = self.scheme.decrypt(ct_result)
        elapsed = time.perf_counter() - t0
        self._timings['decrypt'] = elapsed
        return val

    def get_timings(self) -> dict[str, float]:
        return dict(self._timings)

    def run_full_pipeline(self, circuit: FHECircuit,
                          inputs: list[int]) -> dict:
        """Run full FHE pipeline: keygen → encrypt → execute → decrypt.

        Returns dict with {'result': int, 'timings': dict, 'success': bool}.
        On failure, returns {'result': None, 'timings': {}, 'success': False,
        'error': str}.
        """
        try:
            self.generate_keys()
            encrypted = self.encrypt_inputs(inputs)
            ct_result = self.execute(circuit, encrypted)
            plain_result = self.decrypt_result(ct_result)
            return {
                'result': plain_result,
                'timings': self.get_timings(),
                'success': True,
                'error': None,
            }
        except Exception as e:
            return {
                'result': None,
                'timings': {},
                'success': False,
                'error': str(e),
            }


def verify_equivalence(original_ir, fhe_circuit: FHECircuit,
                       test_inputs: Optional[list[list[int]]] = None) -> dict:
    """Verify that the FHE circuit matches the original IR.

    Tests on random inputs and checks that plain evaluation of the
    circuit matches the expected output.
    """
    from .scheme import BGVParameters
    params = BGVParameters()
    scheme = BGVScheme(params)
    scheme.keygen()
    evaluator = CircuitEvaluator(scheme)

    if test_inputs is None:
        test_inputs = []
        import random
        for _ in range(10):
            test_inputs.append([random.randint(0, params.t - 1) for _ in range(len(fhe_circuit.input_gates))])

    num_inputs = len(fhe_circuit.input_gates)
    failures = 0
    total = 0
    details = []

    for inp in test_inputs:
        padded = inp[:num_inputs]
        while len(padded) < num_inputs:
            padded.append(0)
        circuit_result = evaluator.evaluate_plain(fhe_circuit, padded)
        expected = _evaluate_ir_plain(original_ir, padded, modulo=params.t)
        equivalent = (circuit_result == expected)
        total += 1
        if not equivalent:
            failures += 1
        details.append({
            'inputs': padded,
            'expected': expected,
            'circuit_result': circuit_result,
            'equivalent': equivalent,
        })

    return {
        'total': total,
        'failures': failures,
        'passed': total - failures,
        'equivalent': failures == 0,
        'details': details,
    }


def _evaluate_ir_plain(function, inputs: list[int], modulo: Optional[int] = None) -> int:
    """Evaluate an IrFunction on plain integer inputs."""
    from irgen.compile import IrValue
    values: dict[int, int] = {}
    param_map: dict[str, int] = {}
    for i, (pname, _) in enumerate(function.params):
        param_map[pname] = inputs[i] if i < len(inputs) else 0
    block = function.blocks[0]
    last_val = 0
    for inst in block.instructions:
        op = inst.opcode
        if op == 'alloca':
            if inst.result:
                values[inst.result.id] = 0
        elif op == 'store':
            val = _resolve_ir_value(inst.operands[0], values, param_map)
            if inst.operands[1] and hasattr(inst.operands[1], 'id'):
                values[inst.operands[1].id] = val
        elif op == 'load':
            ptr = inst.operands[0]
            if inst.result and hasattr(ptr, 'id'):
                values[inst.result.id] = values.get(ptr.id, 0)
                last_val = values[inst.result.id]
        elif op == 'add':
            l = _resolve_ir_value(inst.operands[0], values, param_map)
            r = _resolve_ir_value(inst.operands[1], values, param_map)
            if inst.result:
                res = l + r
                values[inst.result.id] = res % modulo if modulo else res
                last_val = values[inst.result.id]
        elif op == 'sub':
            l = _resolve_ir_value(inst.operands[0], values, param_map)
            r = _resolve_ir_value(inst.operands[1], values, param_map)
            if inst.result:
                res = l - r
                values[inst.result.id] = res % modulo if modulo else res
                last_val = values[inst.result.id]
        elif op == 'mul':
            l = _resolve_ir_value(inst.operands[0], values, param_map)
            r = _resolve_ir_value(inst.operands[1], values, param_map)
            if inst.result:
                res = l * r
                values[inst.result.id] = res % modulo if modulo else res
                last_val = values[inst.result.id]
        elif op == 'ret':
            if inst.operands and len(inst.operands) >= 2:
                return _resolve_ir_value(inst.operands[1], values, param_map)
    if block.terminator and block.terminator.opcode == 'ret':
        term_op = block.terminator
        if len(term_op.operands) >= 2:
            return _resolve_ir_value(term_op.operands[1], values, param_map)
    return abs(last_val) % modulo if modulo else abs(last_val)


def _resolve_ir_value(val, values: dict[int, int],
                      param_map: dict[str, int]) -> int:
    if isinstance(val, IrValue):
        if val.id in values:
            return values[val.id]
        name = val.name or ''
        if name in param_map:
            return param_map[name]
        stripped = name.lstrip('%')
        if stripped != name and stripped in param_map:
            return param_map[stripped]
        try:
            return int(name)
        except (ValueError, TypeError):
            return 0
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0
