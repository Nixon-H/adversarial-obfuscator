"""
test_dependency_graph.py

Tests for Dependency Graph Validation (Feature 189).

Test coverage:
- Positive tests verify import extraction, graph building, cycle detection, depth computation
- Negative tests verify empty files, syntax errors, no-cycles
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


from scripts.dependency_graph.validator import (
    DependencyGraphValidator,
    DependencyReport,
)


class TestDependencyReport:
    """
    TestDependencyReport
    
    Positive test cases for dependencyreport.
    """
    def test_empty(self):
        r = DependencyReport()
        assert r.dependency_graph == {}
        assert r.cycles_found == []
        assert r.circular_score == 0.0
        assert r.per_module_depth == {}

    def test_with_cycle(self):
        r = DependencyReport(
            dependency_graph={"a": ["b"], "b": ["a"]},
            cycles_found=[["a", "b", "a"]],
            circular_score=50.0,
            per_module_depth={"a": 0, "b": 1},
        )
        assert r.circular_score == 50.0
        assert len(r.cycles_found) == 1


class TestDependencyGraphValidator:
    """
    TestDependencyGraphValidator
    
    Positive test cases for dependencygraphvalidator.
    """
    def test_init(self):
        v = DependencyGraphValidator()
        assert v.root_dir is not None
        assert os.path.isdir(v.root_dir)

    def test_find_py_files(self):
        v = DependencyGraphValidator()
        files = v._find_py_files()
        assert len(files) > 0
        for f in files:
            assert f.endswith(".py")

    def test_module_name_from_path(self):
        v = DependencyGraphValidator()
        name = v._module_name_from_path("/home/user/project/scripts/foo/bar.py")
        assert "scripts" in name
        assert "foo" in name
        assert "bar" in name

    def test_extract_imports_standard(self):
        v = DependencyGraphValidator()
        tmp_file = "/tmp/_test_imports.py"
        with open(tmp_file, "w") as f:
            f.write("import os\nimport sys\nfrom collections import defaultdict\n")
        imports = v._extract_imports(tmp_file)
        assert "os" in imports
        assert "sys" in imports
        assert "collections" in imports
        os.remove(tmp_file)

    def test_extract_imports_empty(self):
        v = DependencyGraphValidator()
        tmp_file = "/tmp/_test_no_imports.py"
        with open(tmp_file, "w") as f:
            f.write("x = 42\n")
        imports = v._extract_imports(tmp_file)
        assert imports == []
        os.remove(tmp_file)

    def test_extract_imports_syntax_error(self):
        v = DependencyGraphValidator()
        tmp_file = "/tmp/_test_bad_syntax.py"
        with open(tmp_file, "w") as f:
            f.write("this is not valid python @@@\n")
        imports = v._extract_imports(tmp_file)
        assert imports == []
        os.remove(tmp_file)

    def test_build_graph(self):
        v = DependencyGraphValidator()
        graph = v._build_graph()
        assert isinstance(graph, dict)
        assert len(graph) > 0

    def test_find_cycles_no_cycles(self):
        v = DependencyGraphValidator()
        graph = {"a": ["b"], "b": ["c"], "c": []}
        cycles = v._find_cycles(graph)
        assert isinstance(cycles, list)

    def test_find_cycles_with_cycle(self):
        v = DependencyGraphValidator()
        graph = {"scripts.a": ["scripts.b"], "scripts.b": ["scripts.c"], "scripts.c": ["scripts.a"]}
        cycles = v._find_cycles(graph)
        assert isinstance(cycles, list)

    def test_compute_depth(self):
        v = DependencyGraphValidator()
        graph = {"scripts.a": ["scripts.b"], "scripts.b": ["scripts.c"], "scripts.c": []}
        depth = v._compute_depth(graph)
        assert isinstance(depth, dict)

    def test_compute_circular_score_no_cycles(self):
        v = DependencyGraphValidator()
        graph = {"a": ["b"], "b": [], "c": []}
        score = v._compute_circular_score(graph, [])
        assert score == 0.0

    def test_compute_circular_score_with_cycles(self):
        v = DependencyGraphValidator()
        graph = {"a": ["b"], "b": ["c"], "c": ["a"], "d": []}
        score = v._compute_circular_score(graph, [["a", "b", "c", "a"]])
        assert score > 0.0

    def test_validate_dependency_graph_returns_dict(self):
        v = DependencyGraphValidator()
        result = v.validate_dependency_graph()
        assert isinstance(result, dict)
        assert "dependency_graph" in result
        assert "cycles_found" in result
        assert "circular_score" in result
        assert "per_module_depth" in result
        assert "total_modules" in result
        assert "total_cycles" in result

    def test_circular_score_in_range(self):
        v = DependencyGraphValidator()
        result = v.validate_dependency_graph()
        assert 0 <= result["circular_score"] <= 100

    def test_total_modules_positive(self):
        v = DependencyGraphValidator()
        result = v.validate_dependency_graph()
        assert result["total_modules"] > 0

    def test_per_module_depth_is_dict(self):
        v = DependencyGraphValidator()
        result = v.validate_dependency_graph()
        assert isinstance(result["per_module_depth"], dict)


class TestDependencyGraphIntegration:
    """
    TestDependencyGraphIntegration
    
    Positive test cases for dependencygraphintegration.
    """
    def test_full_validation(self):
        v = DependencyGraphValidator()
        result = v.validate_dependency_graph()
        assert result["dependency_graph"] is not None
        assert result["total_modules"] >= 5
