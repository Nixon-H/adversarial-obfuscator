from __future__ import annotations

import numpy as np

from .np_obfuscation import MatrixBranchingProgram

_rng = np.random.default_rng()


def verify_equivalence(
    ir_function,
    obfuscated_bp: MatrixBranchingProgram,
    num_samples: int = 100,
) -> dict:
    """Test input/output equivalence across random inputs.

    Returns dict with:
        'equivalent'  — True if all samples match
        'score'       — fraction of matching outputs (0..1)
        'samples'     — number of samples tested
        'mismatches'  — list of (input_str, expected, got) for failures
    """
    param_count = len(getattr(ir_function, 'params', []))
    mismatches = []

    for _ in range(num_samples):
        inputs = []
        for _p in range(param_count):
            inputs.append(int(_rng.integers(-100, 100)))
        input_bits = _to_bits(inputs)

        bp_output = obfuscated_bp.evaluate(input_bits, param_values=np.array(inputs, dtype=float))
        ir_output = _eval_ir_function(ir_function, inputs)

        if not _approx_equal(bp_output, ir_output, tol=1e-6):
            mismatches.append((str(inputs), ir_output, bp_output))

    score = 1.0 - len(mismatches) / max(num_samples, 1)
    return {
        'equivalent': len(mismatches) == 0,
        'score': score,
        'samples': num_samples,
        'mismatches': mismatches,
        'note': 'MEASURED equivalence — not a formal proof',
    }


def compute_equivalence_score(original_func, obfuscated_bp: MatrixBranchingProgram) -> float:
    """Fraction of matching outputs across random inputs."""
    result = verify_equivalence(original_func, obfuscated_bp, num_samples=100)
    return result['score']


def _to_bits(values: list[int], bits_per_value: int = 16) -> list[int]:
    bits = []
    for v in values:
        av = abs(v)
        for j in range(bits_per_value):
            bits.append((av >> j) & 1)
    return bits or [0]


def _eval_ir_function(ir_function, inputs: list[int]) -> float:
    body = getattr(ir_function, 'blocks', None)
    if not body:
        return 0.0
    block = body[0]
    state = {f'%{n}': v for (n, _t), v in zip(
        getattr(ir_function, 'params', []), inputs)}
    state['1'] = 1
    state['0'] = 0

    for inst in getattr(block, 'instructions', []):
        _simulate_inst(inst, state)
    term = getattr(block, 'terminator', None)
    if term and term.opcode == 'ret':
        operands = getattr(term, 'operands', [])
        if len(operands) >= 2:
            v = operands[1]
            if isinstance(v, int):
                return float(v)
            if hasattr(v, 'name') and v.name in state:
                return float(state[v.name])
            if hasattr(v, 'name'):
                try:
                    return float(v.name)
                except (ValueError, TypeError):
                    return 0.0
        return 0.0
    return 0.0


def _simulate_inst(inst, state: dict):
    op = getattr(inst, 'opcode', '')
    operands = getattr(inst, 'operands', [])
    result = getattr(inst, 'result', None)
    result_name = getattr(result, 'name', None) if result else None

    args = []
    for opnd in operands:
        if isinstance(opnd, int):
            args.append(float(opnd))
        elif hasattr(opnd, 'name'):
            try:
                args.append(float(opnd.name))
            except (ValueError, TypeError):
                args.append(float(state.get(opnd.name, 0)))
        else:
            args.append(0.0)

    if op == 'store' and len(args) >= 1 and len(operands) >= 2:
        ptr = operands[1]
        if hasattr(ptr, 'name'):
            state[ptr.name] = args[0]
        return

    if result_name is None:
        return

    if op == 'load':
        state[result_name] = args[0] if args else 0.0
    elif op == 'alloca':
        state[result_name] = 0.0
    elif op == 'gep':
        state[result_name] = 0.0
    elif op == 'phi':
        if args:
            state[result_name] = args[0]
    elif op == 'not':
        state[result_name] = 1.0 if args[0] == 0.0 else 0.0
    elif op == 'nop':
        pass
    elif op == 'zext':
        state[result_name] = args[0] if args else 0.0
    elif op == 'call' and len(operands) >= 1:
        state[result_name] = args[0] if args else 0.0
    elif op in ('eq', 'ne', 'lt', 'le', 'gt', 'ge') and len(args) >= 2:
        if op == 'eq':
            state[result_name] = 1.0 if args[0] == args[1] else 0.0
        elif op == 'ne':
            state[result_name] = 1.0 if args[0] != args[1] else 0.0
        elif op == 'lt':
            state[result_name] = 1.0 if args[0] < args[1] else 0.0
        elif op == 'le':
            state[result_name] = 1.0 if args[0] <= args[1] else 0.0
        elif op == 'gt':
            state[result_name] = 1.0 if args[0] > args[1] else 0.0
        elif op == 'ge':
            state[result_name] = 1.0 if args[0] >= args[1] else 0.0
    elif len(args) >= 2:
        if op == 'add':
            state[result_name] = args[0] + args[1]
        elif op == 'sub':
            state[result_name] = args[0] - args[1]
        elif op == 'mul':
            state[result_name] = args[0] * args[1]
        elif op == 'div':
            state[result_name] = args[0] / args[1] if args[1] != 0 else 0.0
        elif op == 'mod':
            state[result_name] = args[0] % args[1] if args[1] != 0 else 0.0
        elif op == 'and':
            state[result_name] = float(int(args[0]) & int(args[1]))
        elif op == 'or':
            state[result_name] = float(int(args[0]) | int(args[1]))
        elif op == 'xor':
            state[result_name] = float(int(args[0]) ^ int(args[1]))
        elif op == 'shl':
            state[result_name] = float(int(args[0]) << int(args[1]))
        elif op == 'shr':
            state[result_name] = float(int(args[0]) >> int(args[1]))


def _approx_equal(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) < tol
