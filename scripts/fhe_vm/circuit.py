"""
circuit.py

Purpose:
Defines the FHECircuit (DAG of arithmetic gates) and CircuitEvaluator
for evaluating circuits in plaintext or under FHE encryption. Supports
gates: input, output, const, add, mul, sub.

Architectural Role:
Core circuit abstraction for the FHE VM. Functions are compiled to
FHECircuit instances via the IR adapter (ir_adapter.py). The circuit
is then evaluated by the FHEExecutor under encryption.

Execution Context:
FHECircuit is built by SSAToFHECircuit.convert_function(). It is
consumed by CircuitEvaluator.evaluate_encrypted() (called by
FHEExecutor.execute()) and verify_equivalence().

Dependencies:
- scheme (BGVScheme) for cryptographic operations in evaluator
- ir_adapter (SSAToFHECircuit) for circuit construction
- Standard library (typing, dataclasses)

Security Relevance:
The circuit must correctly represent the original function's semantics.
CircuitEvaluator.evaluate_plain() provides a reference implementation;
verify_equivalence() checks that the encrypted evaluation matches the
plaintext reference on random test inputs.

Maintenance Notes:
- Gate types are limited to {input, output, const, add, mul, sub}.
  Additional gates (comparison, division, bitwise) require extending
  both FHECircuit and BGVScheme.
- The topological sort in _topological_sort uses a simple O(n^2) BFS;
  for large circuits, replace with Kahn's algorithm using an adjacency
  list for O(V+E).
"""

from __future__ import annotations
from typing import Optional, Any
from dataclasses import dataclass, field


@dataclass
class Gate:
    gate_id: int
    gate_type: str
    operands: list[int] = field(default_factory=list)
    value: Optional[Any] = None

    def __repr__(self):
        return f"Gate({self.gate_id}, {self.gate_type}, ops={self.operands}, val={self.value})"


class FHECircuit:
    def __init__(self, name: str = "fhe_circuit"):
        self.name = name
        self.gates: dict[int, Gate] = {}
        self.input_gates: list[int] = []
        self.output_gate: Optional[int] = None
        self.const_gates: list[int] = []
        self._next_id: int = 0

    def new_gate(self, gate_type: str, operands: Optional[list[int]] = None,
                 value: Optional[Any] = None) -> int:
        gid = self._next_id
        self._next_id += 1
        self.gates[gid] = Gate(gid, gate_type, operands or [], value)
        if gate_type == 'input':
            self.input_gates.append(gid)
        elif gate_type == 'const':
            self.const_gates.append(gid)
        return gid

    def set_output(self, gid: int):
        self.output_gate = gid

    def num_ops(self) -> int:
        arithmetic = 0
        for g in self.gates.values():
            if g.gate_type in ('add', 'mul', 'sub'):
                arithmetic += 1
        return arithmetic

    def gate_count(self) -> int:
        return len(self.gates)

    def __str__(self):
        lines = [f"circuit @{self.name} ({self.num_ops()} ops, {self.gate_count()} gates)"]
        for gid in sorted(self.gates):
            g = self.gates[gid]
            if g.gate_type == 'input':
                lines.append(f"  %{gid} = input")
            elif g.gate_type == 'const':
                lines.append(f"  %{gid} = const {g.value}")
            elif g.gate_type == 'add':
                lines.append(f"  %{gid} = add %{g.operands[0]}, %{g.operands[1]}")
            elif g.gate_type == 'sub':
                lines.append(f"  %{gid} = sub %{g.operands[0]}, %{g.operands[1]}")
            elif g.gate_type == 'mul':
                lines.append(f"  %{gid} = mul %{g.operands[0]}, %{g.operands[1]}")
            elif g.gate_type == 'output':
                lines.append(f"  output %{g.operands[0]}")
        return "\n".join(lines)


class CircuitEvaluator:
    def __init__(self, scheme):
        from .scheme import BGVScheme  # noqa: F401 (this line binds a name used by an embedded template)
        self.scheme = scheme

    def evaluate_plain(self, circuit: FHECircuit, inputs: list[int]) -> int:
        values: dict[int, int] = {}
        for gid in circuit.input_gates:
            idx = circuit.input_gates.index(gid)
            values[gid] = inputs[idx] if idx < len(inputs) else 0
        topological_order = self._topological_sort(circuit)
        for gid in topological_order:
            gate = circuit.gates[gid]
            if gate.gate_type == 'const':
                values[gid] = gate.value
            elif gate.gate_type == 'input':
                continue
            elif gate.gate_type == 'add':
                values[gid] = (values[gate.operands[0]] + values[gate.operands[1]]) % self.scheme.params.t
            elif gate.gate_type == 'sub':
                values[gid] = (values[gate.operands[0]] - values[gate.operands[1]]) % self.scheme.params.t
            elif gate.gate_type == 'mul':
                values[gid] = (values[gate.operands[0]] * values[gate.operands[1]]) % self.scheme.params.t
        if circuit.output_gate is not None:
            return values.get(circuit.output_gate, 0)
        return 0

    def evaluate_encrypted(self, circuit: FHECircuit,
                           encrypted_inputs: list) -> tuple:
        ct_values: dict[int, Any] = {}
        for gid in circuit.input_gates:
            idx = circuit.input_gates.index(gid)
            ct_values[gid] = encrypted_inputs[idx] if idx < len(encrypted_inputs) else self.scheme.encrypt(0)
        topological_order = self._topological_sort(circuit)
        for gid in topological_order:
            gate = circuit.gates[gid]
            if gate.gate_type == 'const':
                ct_values[gid] = self.scheme.encrypt(gate.value)
            elif gate.gate_type == 'input':
                continue
            elif gate.gate_type == 'add':
                ct_values[gid] = self.scheme.add(ct_values[gate.operands[0]], ct_values[gate.operands[1]])
            elif gate.gate_type == 'sub':
                ct_values[gid] = self.scheme.sub(ct_values[gate.operands[0]], ct_values[gate.operands[1]])
            elif gate.gate_type == 'mul':
                ct_values[gid] = self.scheme.mul(ct_values[gate.operands[0]], ct_values[gate.operands[1]])
        if circuit.output_gate is not None and circuit.output_gate in ct_values:
            return ct_values[circuit.output_gate]
        return self.scheme.encrypt(0)

    def _topological_sort(self, circuit: FHECircuit) -> list[int]:
        in_degree: dict[int, int] = {}
        for gid, gate in circuit.gates.items():
            if gid not in in_degree:
                in_degree[gid] = 0
            for op in gate.operands:
                if op in circuit.gates:
                    if op not in in_degree:
                        in_degree[op] = 0
                    in_degree[gid] = in_degree.get(gid, 0) + 1
        queue = [gid for gid, deg in in_degree.items() if deg == 0]
        order = []
        while queue:
            gid = queue.pop(0)
            order.append(gid)
            gate = circuit.gates[gid]
            for dep_gid, dep_gate in circuit.gates.items():
                if dep_gid != gid and gid in dep_gate.operands:
                    in_degree[dep_gid] -= 1
                    if in_degree[dep_gid] == 0:
                        queue.append(dep_gid)
        return order


def build_circuit_from_ir(function) -> FHECircuit:
    from .ir_adapter import SSAToFHECircuit
    adapter = SSAToFHECircuit()
    return adapter.convert_function(function)
