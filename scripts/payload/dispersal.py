"""Item 69: Payload dispersal execution model.

Spread payload execution across multiple disjoint contexts that must be
combined to reconstruct the original behavior.  A payload function is split
into disjoint slices, each executed independently, with reconstructed state
at merge points.
"""

import ast
import hashlib
import os
import struct
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class Slice:
    index: int
    source: str
    input_vars: List[str] = field(default_factory=list)
    output_vars: List[str] = field(default_factory=list)
    entry_condition: str = ""


@dataclass
class MergePoint:
    slice_indices: List[int]
    output_map: Dict[str, str]


class PayloadDisperser:
    """Splits a payload function into disjoint slices, each executed
    independently.  State is reconstructed at merge points by combining
    outputs from multiple slices."""

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed or int.from_bytes(os.urandom(4), "big")
        self.slices: List[Slice] = []
        self.merge_points: List[MergePoint] = []

    def _parse_function(self, source: str) -> ast.FunctionDef:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                return node
        raise ValueError("No function definition found in source")

    def _extract_var_names(self, node: ast.AST) -> List[str]:
        vars_found: List[str] = []
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                if n.id not in vars_found:
                    vars_found.append(n.id)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if n.id not in vars_found:
                    vars_found.append(n.id)
        return vars_found

    def disperse(self, source: str, num_slices: int = 3) -> List[Slice]:
        """Split a payload function's body into disjoint slices."""
        func = self._parse_function(source)
        body_stmts = func.body
        if len(body_stmts) < num_slices:
            num_slices = max(1, len(body_stmts))
        chunk_size = max(1, len(body_stmts) // num_slices)
        self.slices = []
        all_vars: List[str] = []
        for n in ast.walk(func):
            if isinstance(n, ast.Name):
                if n.id not in all_vars:
                    all_vars.append(n.id)
        for i in range(num_slices):
            start = i * chunk_size
            end = start + chunk_size if i < num_slices - 1 else len(body_stmts)
            stmts = body_stmts[start:end]
            slice_src = ast.unparse(stmts)
            vars_in = self._extract_var_names(stmts[0]) if stmts else []
            vars_out = self._extract_var_names(stmts[-1]) if stmts else []
            sl = Slice(
                index=i,
                source=slice_src,
                input_vars=vars_in,
                output_vars=vars_out,
            )
            self.slices.append(sl)
        return self.slices

    def create_merge_points(self) -> List[MergePoint]:
        """Create merge points that reconstruct state from slice outputs."""
        self.merge_points = []
        if len(self.slices) < 2:
            return self.merge_points
        for i in range(0, len(self.slices) - 1, 2):
            pair = [self.slices[i], self.slices[i + 1]]
            output_map: Dict[str, str] = {}
            for s in pair:
                for v in s.output_vars:
                    if v not in output_map:
                        output_map[v] = f"merged_{v}_{i}"
            mp = MergePoint(
                slice_indices=[s.index for s in pair],
                output_map=output_map,
            )
            self.merge_points.append(mp)
        return self.merge_points

    def reconstruct(self, slice_results: Dict[int, Dict[str, Any]],
                    merge_strategy: Callable = None) -> Dict[str, Any]:
        """Reconstruct final state from independent slice execution results."""
        if merge_strategy is None:
            merge_strategy = self._default_merge
        return merge_strategy(slice_results)

    def _default_merge(self, slice_results: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        for idx in sorted(slice_results.keys()):
            result = slice_results[idx]
            for k, v in result.items():
                merged[k] = v
        return merged

    def get_dispersal_summary(self) -> dict:
        return {
            "num_slices": len(self.slices),
            "num_merge_points": len(self.merge_points),
            "slices": [
                {"index": s.index, "source_len": len(s.source),
                 "input_vars": s.input_vars, "output_vars": s.output_vars}
                for s in self.slices
            ],
            "merge_points": [
                {"indices": mp.slice_indices, "outputs": list(mp.output_map.keys())}
                for mp in self.merge_points
            ],
        }
