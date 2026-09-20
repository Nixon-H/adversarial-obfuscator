"""
graph.py

Purpose:
Conflict dependency graph for protection features. Builds a graph
from Conflict objects where nodes are flag names and edges represent
conflicts. Supports query, compatibility checking, connected-component
analysis, and DOT serialization for visualization.

Architectural Role:
Provides a graph abstraction over conflict rules for analysis and
visualization. Used by the artifact generator to produce conflict
diagrams and by the conflict detector for connected-component analysis.

Execution Context:
Built from KNOWN_CONFLICTS during the conflict detection phase.
The graph can be serialized to JSON, DOT (Graphviz), or GraphML.

Dependencies:
- detector (Conflict, ConflictType, Severity)
- Standard library (json, collections, typing)

Security Relevance:
The conflict graph reveals clusters of mutually-incompatible features.
Large connected components indicate areas where feature selection is
constrained and require careful planning.

Maintenance Notes:
- The graph is undirected for conflicts (edges go both ways in _adj).
- get_connected_components() uses DFS and is O(V + E).
- The generate_dot() method produces Graphviz DOT format for
  visualization with tools like xdot or graphviz.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple

from scripts.conflicts.detector import Conflict, ConflictType, Severity


class ConflictGraph:
    def __init__(self):
        self._nodes: Set[str] = set()
        self._edges: List[Tuple[str, str, Conflict]] = []
        self._adj: Dict[str, List[Tuple[str, Conflict]]] = defaultdict(list)

    def add_conflict(
        self,
        a: str,
        b: str,
        conflict_type: ConflictType,
        severity: Severity,
        description: str,
        resolution: str,
    ) -> None:
        conflict = Conflict(
            flag_a=a,
            flag_b=b,
            conflict_type=conflict_type,
            severity=severity,
            description=description,
            resolution=resolution,
        )
        self._nodes.add(a)
        self._nodes.add(b)
        self._edges.append((a, b, conflict))
        self._adj[a].append((b, conflict))
        self._adj[b].append((a, conflict))

    def add_conflict_obj(self, conflict: Conflict) -> None:
        self._nodes.add(conflict.flag_a)
        self._nodes.add(conflict.flag_b)
        self._edges.append((conflict.flag_a, conflict.flag_b, conflict))
        self._adj[conflict.flag_a].append((conflict.flag_b, conflict))
        self._adj[conflict.flag_b].append((conflict.flag_a, conflict))

    def get_conflicts(self, flag: str) -> List[Conflict]:
        return [c for _, c in self._adj.get(flag, [])]

    def is_compatible(self, flags_list: List[str]) -> bool:
        for i in range(len(flags_list)):
            for j in range(i + 1, len(flags_list)):
                a, b = flags_list[i], flags_list[j]
                for neighbor, conflict in self._adj.get(a, []):
                    if neighbor == b:
                        if conflict.conflict_type == ConflictType.INCOMPATIBLE:
                            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": sorted(self._nodes),
            "edges": [
                {
                    "source": a,
                    "target": b,
                    "type": c.conflict_type.value,
                    "severity": c.severity.value,
                    "description": c.description,
                    "resolution": c.resolution,
                }
                for a, b, c in self._edges
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def generate_dot(self) -> str:
        lines = ['digraph ConflictGraph {']
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=box, style=rounded];')
        lines.append('')
        for node in sorted(self._nodes):
            lines.append(f'  "{node}";')
        lines.append('')
        for a, b, c in self._edges:
            style = "dashed" if c.severity == Severity.WARNING else "solid"
            color = "orange" if c.conflict_type == ConflictType.SUBSUMES else "red"
            label = f"{c.conflict_type.value}"
            lines.append(f'  "{a}" -> "{b}" [style={style}, color={color}, label="{label}"];')
        lines.append('}')
        return "\n".join(lines)

    def get_connected_components(self) -> List[Set[str]]:
        visited: Set[str] = set()
        components: List[Set[str]] = []

        for node in self._nodes:
            if node not in visited:
                component: Set[str] = set()
                stack = [node]
                while stack:
                    current = stack.pop()
                    if current in visited:
                        continue
                    visited.add(current)
                    component.add(current)
                    for neighbor, _ in self._adj.get(current, []):
                        if neighbor not in visited:
                            stack.append(neighbor)
                components.append(component)

        return components
