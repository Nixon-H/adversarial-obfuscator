from __future__ import annotations

import numpy as np

from .np_obfuscation import MatrixBranchingProgram


_LINEAR_OPS = frozenset({
    'add', 'sub', 'mul', 'zext', 'trunc', 'eq', 'ne', 'lt', 'le', 'gt', 'ge',
})

_NON_LINEAR_OPS = frozenset({
    'div', 'mod', 'and', 'or', 'xor', 'shl', 'shr',
})

_ALLOWED_OPS = _LINEAR_OPS | _NON_LINEAR_OPS | frozenset({
    'alloca', 'load', 'store', 'ret', 'nop', 'call', 'phi', 'jmp',
})


def is_io_compatible(function) -> tuple[bool, str]:
    blocks = getattr(function, 'blocks', [])
    params = getattr(function, 'params', [])

    if not blocks:
        return False, 'no blocks'

    if len(blocks) > 1:
        return False, f'multiple blocks ({len(blocks)}): control flow present'

    block = blocks[0]
    instructions = getattr(block, 'instructions', [])

    arith_count = 0
    for inst in instructions:
        op = getattr(inst, 'opcode', '')
        if op in _NON_LINEAR_OPS:
            return False, f'non-linear operation not supported: {op}'
        if op == 'mul':
            operands = getattr(inst, 'operands', [])
            if len(operands) >= 2:
                lhs_is_var = _is_variable(operands[0])
                rhs_is_var = _is_variable(operands[1])
                if lhs_is_var and rhs_is_var:
                    return False, 'variable×variable multiplication not supported'
        if op in _LINEAR_OPS:
            arith_count += 1
        elif op not in _ALLOWED_OPS:
            return False, f'unsupported opcode: {op}'
        elif op == 'call':
            func_name = getattr(inst, 'func_name', '')
            if func_name not in {'__builtin_print'}:
                return False, f'unsupported call: {func_name}'

    if arith_count > 5:
        return False, f'too many arithmetic ops ({arith_count} > 5)'

    if arith_count == 0:
        return False, 'no arithmetic operations'

    for _name, ptype in params:
        if ptype.kind not in ('i1', 'i8', 'i16', 'i32', 'i64'):
            return False, f'non-integer parameter type: {ptype}'

    return True, 'compatible'


def _is_variable(opnd) -> bool:
    name = getattr(opnd, 'name', None)
    if name is None:
        return False
    try:
        float(name)
        return False
    except (ValueError, TypeError):
        return True


def ir_to_branching_program(function) -> MatrixBranchingProgram | None:
    try:
        return _build_bp(function)
    except Exception:
        return None


def _build_bp(function) -> MatrixBranchingProgram:
    blocks = getattr(function, 'blocks', [])
    block = blocks[0]
    instructions = getattr(block, 'instructions', [])
    params = getattr(function, 'params', [])
    term = getattr(block, 'terminator', None)

    param_names = [n for n, _t in params]

    # Build dataflow: track which SSA name maps to which param name or constant
    # and which alloca holds what.
    name_to_value: dict[str, float | str] = {}  # name -> param_name or constant
    alloca_to_name: dict[str, str] = {}  # alloca result name -> stores which param name
    load_to_name: dict[str, str] = {}  # load result name -> which alloca
    param_indices: dict[str, int] = {n: i for i, n in enumerate(param_names)}
    arith_results: list[tuple[str, str, list]] = []  # (result_name, opcode, [operand_names])

    for pn in param_names:
        name_to_value[pn] = pn

    for inst in instructions:
        op = getattr(inst, 'opcode', '')
        r = getattr(inst, 'result', None)
        rname = getattr(r, 'name', None) if r else None
        operands = getattr(inst, 'operands', [])

        if op == 'alloca' and rname:
            alloca_to_name[rname] = rname

        elif op == 'store' and len(operands) >= 2:
            val = operands[0]
            ptr = operands[1]
            val_name = getattr(val, 'name', None) if hasattr(val, 'name') else None
            ptr_name = getattr(ptr, 'name', None) if hasattr(ptr, 'name') else None
            if val_name and ptr_name:
                raw_name = val_name.lstrip('%')
                if raw_name in param_names or raw_name in name_to_value:
                    stored_val = name_to_value.get(raw_name, raw_name)
                    alloca_to_name[ptr_name] = stored_val if isinstance(stored_val, str) else str(stored_val)
                else:
                    alloca_to_name[ptr_name] = val_name

        elif op == 'load' and rname and len(operands) >= 1:
            ptr = operands[0]
            ptr_name = getattr(ptr, 'name', None) if hasattr(ptr, 'name') else None
            if ptr_name and ptr_name in alloca_to_name:
                load_to_name[rname] = alloca_to_name[ptr_name]
            else:
                load_to_name[rname] = str(ptr_name or '0')

        elif op in _LINEAR_OPS and rname:
            arg_names = []
            for opnd in operands:
                if isinstance(opnd, int):
                    arg_names.append(str(opnd))
                elif hasattr(opnd, 'name'):
                    arg_names.append(opnd.name)
                else:
                    arg_names.append('0')
            arith_results.append((rname, op, arg_names))
            # Resolve value through load chains for result tracking
            resolved = _resolve_name_chain(rname, load_to_name, alloca_to_name, param_names)
            name_to_value[rname] = resolved if resolved else rname

    if not arith_results:
        scalar_zero = np.zeros(1)
        return MatrixBranchingProgram(
            [(np.array([[1.0]]), np.array([[1.0]]))],
            start_vector=np.array([0.0]),
            output_index=0,
        )

    # Build the state vector and matrices from arithmetic results
    # State vector: [param_0, param_1, ..., param_k, 1]
    initial_dim = len(param_names) + 1
    name_to_idx: dict[str, int] = {}
    for i, pn in enumerate(param_names):
        name_to_idx[pn] = i

    # Build a sequence of 2x2 or larger matrices
    # For each arithmetic op, we extend the state space with a new dimension
    # and build a matrix that computes the result

    state_dim = initial_dim
    matrices = []

    for rname, op, arg_names in arith_results:
        dim = state_dim + 1

        # Resolve arg_names to state indices
        lhs_idx = _find_idx(arg_names[0] if len(arg_names) > 0 else '0', name_to_idx,
                            param_names, load_to_name, alloca_to_name)
        rhs_idx = _find_idx(arg_names[1] if len(arg_names) > 1 else '1', name_to_idx,
                            param_names, load_to_name, alloca_to_name)

        if lhs_idx is None:
            lhs_idx = state_dim - 1
        if rhs_idx is None:
            rhs_idx = state_dim - 1

        m = np.eye(dim)

        new_col = dim - 1
        m[:, new_col] = 0.0

        lhs_val = _get_constant_val(arg_names[0], param_indices)
        rhs_val = _get_constant_val(arg_names[1], param_indices)

        if op == 'add':
            m[lhs_idx, new_col] = 1.0
            m[rhs_idx, new_col] = 1.0
        elif op == 'sub':
            m[lhs_idx, new_col] = 1.0
            m[rhs_idx, new_col] = -1.0
        elif op in ('mul',):
            if rhs_val is not None:
                m[lhs_idx, new_col] = rhs_val
            elif lhs_val is not None:
                m[rhs_idx, new_col] = lhs_val
            else:
                m[lhs_idx, new_col] = 1.0
                m[rhs_idx, new_col] = 1.0
        elif op in ('eq', 'ne', 'lt', 'le', 'gt', 'ge', 'zext', 'trunc'):
            m[lhs_idx if lhs_idx is not None else state_dim - 1, new_col] = 1.0

        matrices.append(m)
        name_to_idx[rname] = state_dim
        state_dim = dim

    if not matrices:
        scalar_zero = np.zeros(1)
        return MatrixBranchingProgram(
            [(np.array([[1.0]]), np.array([[1.0]]))],
            start_vector=np.array([0.0]),
            output_index=0,
        )

    output_index = 0
    if term and term.opcode == 'ret':
        operands = getattr(term, 'operands', [])
        if len(operands) >= 2:
            ret_val = operands[1]
            ret_name = getattr(ret_val, 'name', None) if hasattr(ret_val, 'name') else None
            if ret_name:
                # Trace through load chain
                for rn, op, _args in arith_results:
                    if rn == ret_name or (ret_name in load_to_name and load_to_name[ret_name] == rn):
                        if rn in name_to_idx:
                            output_index = name_to_idx[rn]
                            break
                # If ret_name is a param
                if ret_name in param_indices:
                    output_index = param_indices[ret_name]
                # Try name_to_idx directly
                if ret_name in name_to_idx:
                    output_index = name_to_idx[ret_name]

    start_vec = np.zeros(state_dim)
    start_vec[0:len(param_names)] = 0.0
    start_vec[len(param_names)] = 1.0

    obf_pairs = [(m.copy(), m.copy()) for m in matrices]
    bp = MatrixBranchingProgram(
        obf_pairs,
        start_vector=start_vec,
        output_index=output_index,
    )

    _pad_bp_matrices(bp)
    return bp


def _find_idx(name: str, name_to_idx: dict, param_names: list,
              load_to_name: dict, alloca_to_name: dict) -> int | None:
    raw = name.lstrip('%')
    if raw in name_to_idx:
        return name_to_idx[raw]
    if raw in param_names:
        return param_names.index(raw)
    if name in load_to_name:
        resolved = load_to_name[name]
    elif raw in load_to_name:
        resolved = load_to_name[raw]
    else:
        resolved = None
    if resolved is not None:
        if resolved in name_to_idx:
            return name_to_idx[resolved]
        if resolved in param_names:
            return param_names.index(resolved)
    try:
        int(raw)
        return len(param_names)
    except (ValueError, TypeError):
        pass
    return None


def _get_constant_val(name: str, param_indices: dict) -> float | None:
    if name in param_indices:
        return None
    try:
        return float(name)
    except (ValueError, TypeError):
        return None


def _resolve_name_chain(name, load_to_name, alloca_to_name, param_names):
    if name in param_names:
        return name
    if name in load_to_name:
        return _resolve_name_chain(load_to_name[name], load_to_name, alloca_to_name, param_names)
    return name


def _pad_bp_matrices(bp: MatrixBranchingProgram):
    max_dim = bp.dim
    for m0, m1 in bp.matrices:
        d = m0.shape[0]
        if d > max_dim:
            max_dim = d
    if max_dim <= bp.dim:
        return

    new_pairs = []
    for m0, m1 in bp.matrices:
        d0, d1 = m0.shape[0], m1.shape[0]
        if d0 < max_dim or d1 < max_dim:
            p0 = np.eye(max_dim)
            p0[:d0, :d0] = m0
            p1 = np.eye(max_dim)
            p1[:d1, :d1] = m1
            new_pairs.append((p0, p1))
        else:
            new_pairs.append((m0, m1))
    bp.matrices = new_pairs

    if len(bp.start_vector) < max_dim:
        sv = np.zeros(max_dim)
        sv[:len(bp.start_vector)] = bp.start_vector
        bp.start_vector = sv
    bp.dim = max_dim
