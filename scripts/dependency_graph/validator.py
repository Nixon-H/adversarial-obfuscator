"""
dependency_graph/validator.py

Purpose:
Builds a dependency graph from all Python files under scripts/, detects
circular dependencies, computes per-module dependency depth, and produces
a circular dependency score.

Architectural Role:
Used by the meta-assurance pipeline to validate that module dependencies
are acyclic and well-structured before release scoring.

Security Relevance:
Circular dependencies can leak trust boundaries — module A trusts B, B trusts
C, C trusts A — creating an unverified trust loop. High circular scores
indicate structural risk.
"""
from __future__ import annotations

import ast
import os
import sys
from collections import deque
from dataclasses import dataclass, field
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)


@dataclass
class DependencyReport:
    """
    DependencyReport

    Purpose:
    Aggregates the full dependency graph, detected cycles, circular score,
    and per-module depth.

    Lifecycle:
    Populated by DependencyGraphValidator.validate_dependency_graph().
    """
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)
    cycles_found: list[list[str]] = field(default_factory=list)
    circular_score: float = 0.0
    per_module_depth: dict[str, int] = field(default_factory=dict)


class DependencyGraphValidator:
    """
    DependencyGraphValidator

    Purpose:
    Builds and validates the module dependency graph by extracting imports
    from every .py file and running cycle detection and depth analysis.

    Lifecycle:
    Created on demand; validate_dependency_graph() drives the analysis.
    """
    def __init__(self, root_dir: str | None = None):
        self.root_dir = root_dir or _ROOT
        self.report = DependencyReport()

    def _find_py_files(self) -> list[str]:
        """
        _find_py_files

        Purpose:
        Recursively finds all .py files under the scripts/ directory.

        Inputs:
        None

        Outputs:
        List of absolute file paths.
        """
        scripts_dir = os.path.join(self.root_dir, "scripts")
        if not os.path.isdir(scripts_dir):
            return []
        result = []
        for root, _dirs, files in os.walk(scripts_dir):
            for f in files:
                if f.endswith(".py"):
                    result.append(os.path.join(root, f))
        return result

    def _module_name_from_path(self, file_path: str) -> str:
        """
        _module_name_from_path

        Purpose:
        Converts a file path to a dotted module name relative to root_dir.

        Inputs:
        file_path — absolute path to the file

        Outputs:
        Dotted module name string.
        """
        rel = os.path.relpath(file_path, self.root_dir)
        rel = rel.replace(".py", "")
        parts = rel.split(os.sep)
        return ".".join(parts)

    def _extract_imports(self, file_path: str) -> list[str]:
        """
        _extract_imports

        Purpose:
        Parses a .py file's AST and extracts all import and import-from statements.

        Inputs:
        file_path — absolute path to the .py file

        Outputs:
        List of imported module names.
        """
        imports = []
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                source = f.read()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except (SyntaxError, UnicodeDecodeError):
            pass
        return imports

    def _build_graph(self) -> dict[str, list[str]]:
        """
        _build_graph

        Purpose:
        Constructs a dependency graph where keys are module names and values
        are lists of local imports (scripts.* or relative imports).

        Inputs:
        None

        Outputs:
        Dict mapping module name -> list of dependency module names.
        """
        graph: dict[str, list[str]] = {}
        py_files = self._find_py_files()
        for file_path in py_files:
            module_name = self._module_name_from_path(file_path)
            imports = self._extract_imports(file_path)
            local_imports = []
            for imp in imports:
                if imp.startswith("scripts.") or imp.startswith("scripts"):
                    local_imports.append(imp)
                elif imp.startswith("..") or imp.startswith("."):
                    local_imports.append(imp)
            graph[module_name] = local_imports
        return graph

    def _find_cycles(self, graph: dict[str, list[str]]) -> list[list[str]]:
        """
        _find_cycles

        Purpose:
        Performs DFS-based cycle detection on the dependency graph. Returns
        all unique cycles found.

        Inputs:
        graph — dict mapping module name -> list of dependencies

        Outputs:
        List of cycles, each cycle being a list of module names.
        """
        cycles = []
        sorted_nodes = sorted(graph.keys())

        def dfs(node: str, path: list[str], visited: set[str], rec_stack: set[str]):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, []):
                neighbor = neighbor.split(".")[0]
                full_neighbor = None
                for gn in sorted_nodes:
                    if gn.endswith(f"/{neighbor}") or gn.endswith(f".{neighbor}") or gn == neighbor:
                        full_neighbor = gn
                        break
                if full_neighbor is None:
                    continue
                if full_neighbor not in visited:
                    cycle = dfs(full_neighbor, path + [full_neighbor], visited, rec_stack)
                    if cycle:
                        cycles.append(cycle)
                elif full_neighbor in rec_stack:
                    cycle_start = path[path.index(full_neighbor):]
                    cycle_path = cycle_start + [full_neighbor]
                    if cycle_path not in cycles:
                        cycles.append(cycle_path)
            rec_stack.discard(node)
            return None

        for node in sorted_nodes:
            visited: set[str] = set()
            rec_stack: set[str] = set()
            dfs(node, [node], visited, rec_stack)

        return cycles

    def _compute_depth(self, graph: dict[str, list[str]]) -> dict[str, int]:
        """
        _compute_depth

        Purpose:
        Computes the dependency depth of each module using topological sort
        (Kahn's algorithm). Modules with no dependencies have depth 0.

        Inputs:
        graph — dict mapping module name -> list of dependencies

        Outputs:
        Dict mapping module name -> depth integer.
        """
        in_degree: dict[str, int] = {node: 0 for node in graph}
        adj: dict[str, list[str]] = {node: [] for node in graph}

        sorted_nodes = sorted(graph.keys())
        for node, deps in graph.items():
            for dep in deps:
                dep_base = dep.split(".")[0]
                full_dep = None
                for gn in sorted_nodes:
                    if gn.endswith(f"/{dep_base}") or gn.endswith(f".{dep_base}") or gn == dep_base:
                        full_dep = gn
                        break
                if full_dep and full_dep in adj:
                    adj[full_dep].append(node)
                    in_degree[node] = in_degree.get(node, 0) + 1

        queue: deque[str] = deque()
        for node, deg in in_degree.items():
            if deg == 0:
                queue.append(node)

        depth: dict[str, int] = {node: 0 for node in graph}
        while queue:
            node = queue.popleft()
            for neighbor in adj.get(node, []):
                depth[neighbor] = max(depth[neighbor], depth[node] + 1)
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return depth

    def _compute_circular_score(self, graph: dict[str, list[str]], cycles: list[list[str]]) -> float:
        """
        _compute_circular_score

        Purpose:
        Calculates a 0-100 score based on the ratio of nodes in cycles and
        the number of cycles relative to total node count.

        Inputs:
        graph — the dependency graph
        cycles — list of detected cycles

        Outputs:
        Float between 0.0 (no circularity) and 100.0 (fully circular).
        """
        total_nodes = len(graph)
        if total_nodes == 0:
            return 0.0

        nodes_in_cycles: set[str] = set()
        for cycle in cycles:
            for node in cycle:
                nodes_in_cycles.add(node)

        cycle_ratio = len(nodes_in_cycles) / total_nodes
        cycle_count_score = min(len(cycles) / max(total_nodes / 5, 1), 1.0)

        score = (cycle_ratio * 0.6 + cycle_count_score * 0.4) * 100
        return round(min(score, 100.0), 1)

    def validate_dependency_graph(self) -> dict[str, Any]:
        """
        validate_dependency_graph

        Purpose:
        Main entry point — builds the graph, detects cycles, computes depth,
        and calculates the circular score.

        Inputs:
        None

        Outputs:
        Dict with dependency_graph, cycles_found, circular_score,
        per_module_depth, total_modules, total_cycles.
        """
        graph = self._build_graph()
        self.report.dependency_graph = graph

        cycles = self._find_cycles(graph)
        self.report.cycles_found = cycles

        depth = self._compute_depth(graph)
        self.report.per_module_depth = depth

        self.report.circular_score = self._compute_circular_score(graph, cycles)

        return self._to_dict()

    def _to_dict(self) -> dict[str, Any]:
        """
        _to_dict

        Purpose:
        Serializes the DependencyReport to a plain dict for JSON output.

        Inputs:
        None

        Outputs:
        Dict with all report fields.
        """
        return {
            "dependency_graph": {
                module: deps
                for module, deps in self.report.dependency_graph.items()
            },
            "cycles_found": [
                {
                    "cycle_path": cycle,
                    "length": len(cycle),
                }
                for cycle in self.report.cycles_found
            ],
            "circular_score": self.report.circular_score,
            "per_module_depth": self.report.per_module_depth,
            "total_modules": len(self.report.dependency_graph),
            "total_cycles": len(self.report.cycles_found),
        }
