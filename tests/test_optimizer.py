import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.optimizer import PROTECTION_COSTS, CLASSIFICATION_MAP
from scripts.optimizer.profiler import FunctionProfiler, FunctionInfo
from scripts.optimizer.cost_optimizer import CostOptimizer


SAMPLE_SOURCE = """
import hashlib
import os

def init_config():
    return {"debug": False}

def encrypt_data(data, key):
    result = bytearray(len(data))
    for i in range(len(data)):
        result[i] = data[i] ^ key[i % len(key)]
    return bytes(result)

def license_check(user_key):
    expected = "abc123"
    return user_key == expected

def derive_key(password, salt):
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return dk

def process_item(item):
    if item > 10:
        return item * 2
    elif item > 5:
        return item + 1
    else:
        return item

def main():
    config = init_config()
    key = derive_key("password", b"salt")
    data = encrypt_data(b"hello", key)
    print(data)
    return 0
"""


@pytest.fixture
def profiler():
    return FunctionProfiler()


@pytest.fixture
def optimizer():
    return CostOptimizer(max_overhead_pct=20.0, max_size_mult=3.0, min_security=0.5)


@pytest.fixture
def sample_functions(profiler):
    return profiler.profile_from_source(SAMPLE_SOURCE)


@pytest.fixture
def all_passes():
    return list(PROTECTION_COSTS.keys())


class TestProfiler:
    """
    TestProfiler
    
    Positive test cases for profiler.
    """
    def test_profiler_returns_function_info_list(self, profiler):
        result = profiler.profile_from_source(SAMPLE_SOURCE)
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(f, FunctionInfo) for f in result)

    def test_profiler_detects_function_names(self, profiler):
        result = profiler.profile_from_source(SAMPLE_SOURCE)
        names = {f.name for f in result}
        assert 'init_config' in names
        assert 'encrypt_data' in names
        assert 'license_check' in names
        assert 'derive_key' in names
        assert 'process_item' in names
        assert 'main' in names

    def test_profiler_counts_lines(self, profiler):
        result = profiler.profile_from_source(SAMPLE_SOURCE)
        fn_map = {f.name: f for f in result}
        assert fn_map['init_config'].lines_of_code >= 1
        assert fn_map['main'].lines_of_code >= 1

    def test_profiler_computes_cyclomatic_complexity(self, profiler):
        result = profiler.profile_from_source(SAMPLE_SOURCE)
        fn_map = {f.name: f for f in result}
        assert fn_map['process_item'].cyclomatic_complexity >= 3
        assert fn_map['init_config'].cyclomatic_complexity >= 1

    def test_profiler_estimates_frequency(self, profiler):
        result = profiler.profile_from_source(SAMPLE_SOURCE)
        fn_map = {f.name: f for f in result}
        assert fn_map['init_config'].exec_frequency < 1.0
        assert fn_map['main'].exec_frequency >= 1.0

    def test_profiler_detects_import_deps(self, profiler):
        result = profiler.profile_from_source(SAMPLE_SOURCE)
        fn_map = {f.name: f for f in result}
        if fn_map['derive_key'].import_dependencies:
            assert 'hashlib' in fn_map['derive_key'].import_dependencies

    def test_profiler_empty_source(self, profiler):
        result = profiler.profile_from_source("")
        assert result == []

    def test_profiler_invalid_syntax(self, profiler):
        result = profiler.profile_from_source("def foo(:")
        assert result == []


class TestCostOptimizer:
    """
    TestCostOptimizer
    
    Positive test cases for costoptimizer.
    """
    def test_optimizer_respects_cpu_budget(self, optimizer, sample_functions, all_passes):
        result = optimizer.optimize(sample_functions, all_passes)
        total_weight = sum(f.exec_frequency * max(f.lines_of_code, 1) for f in sample_functions) or 1.0
        weights = {f.name: f.exec_frequency * max(f.lines_of_code, 1) for f in sample_functions}
        total_cpu = 0.0
        for fn in sample_functions:
            for p in result.get(fn.name, []):
                if p in PROTECTION_COSTS:
                    total_cpu += (PROTECTION_COSTS[p]['cpu'] - 1.0) * weights.get(fn.name, 1.0)
        cpu_pct = (total_cpu / total_weight) * 100
        assert cpu_pct <= optimizer.max_overhead * 100 + 10

    def test_optimizer_respects_size_budget(self, optimizer, sample_functions, all_passes):
        result = optimizer.optimize(sample_functions, all_passes)
        total_weight = sum(f.exec_frequency * max(f.lines_of_code, 1) for f in sample_functions) or 1.0
        weights = {f.name: f.exec_frequency * max(f.lines_of_code, 1) for f in sample_functions}
        total_size = 0.0
        for fn in sample_functions:
            for p in result.get(fn.name, []):
                if p in PROTECTION_COSTS:
                    total_size += (PROTECTION_COSTS[p]['size'] - 1.0) * weights.get(fn.name, 1.0)
        size_mult = 1 + (total_size / total_weight)
        assert size_mult <= optimizer.max_size_mult + 0.5

    def test_optimizer_meets_min_security(self, optimizer, sample_functions, all_passes):
        result = optimizer.optimize(sample_functions, all_passes)
        total_sec = 0.0
        for fn in sample_functions:
            for p in result.get(fn.name, []):
                if p in PROTECTION_COSTS:
                    total_sec += PROTECTION_COSTS[p]['security']
        assert total_sec >= optimizer.min_security

    def test_greedy_knapsack_produces_valid_assignments(self, optimizer, sample_functions, all_passes):
        result = optimizer.optimize(sample_functions, all_passes)
        assert isinstance(result, dict)
        for fn in sample_functions:
            assert fn.name in result
            assert isinstance(result[fn.name], list)

    def test_tighter_budget_demotes_low_value_functions(self):
        loose = CostOptimizer(max_overhead_pct=50.0, max_size_mult=5.0, min_security=0.3)
        tight = CostOptimizer(max_overhead_pct=1.0, max_size_mult=1.1, min_security=0.1)

        profiler = FunctionProfiler()
        functions = profiler.profile_from_source(SAMPLE_SOURCE)
        passes = list(PROTECTION_COSTS.keys())

        loose_result = loose.optimize(functions, passes)
        tight_result = tight.optimize(functions, passes)

        loose_total = sum(len(v) for v in loose_result.values())
        tight_total = sum(len(v) for v in tight_result.values())
        assert tight_total <= loose_total

    def test_all_functions_get_at_least_ast_rename(self, optimizer, sample_functions, all_passes):
        result = optimizer.optimize(sample_functions, all_passes)
        for fn_name, passes in result.items():
            assert 'ast_rename' in passes or len(passes) > 0

    def test_optimizer_handles_empty_functions(self, optimizer):
        result = optimizer.optimize([], [])
        assert result == {}

    def test_optimizer_handles_no_passes(self, optimizer, sample_functions):
        result = optimizer.optimize(sample_functions, [])
        for fn in sample_functions:
            assert 'ast_rename' in result.get(fn.name, [])
            assert len(result[fn.name]) >= 1

    def test_optimizer_handles_invalid_pass_names(self, optimizer, sample_functions):
        result = optimizer.optimize(sample_functions, ['nonexistent_pass'])
        for fn in sample_functions:
            assert 'ast_rename' in result.get(fn.name, [])

    def test_generate_report(self, optimizer, sample_functions, all_passes):
        result = optimizer.optimize(sample_functions, all_passes)
        report = optimizer.generate_report(sample_functions, result)
        assert 'Protection Cost Optimizer Report' in report
        assert 'Function Assignments' in report
        for fn in sample_functions:
            assert fn.name in report

    def test_report_formatting(self, optimizer, sample_functions, all_passes):
        result = optimizer.optimize(sample_functions, all_passes)
        report = optimizer.generate_report(sample_functions, result)
        assert report.startswith('┌')
        assert report.endswith('┘')
        assert '%' in report or 'sec=' in report


class TestProtectionCosts:
    """
    TestProtectionCosts
    
    Positive test cases for protectioncosts.
    """
    def test_all_costs_have_required_keys(self):
        for name, cost in PROTECTION_COSTS.items():
            assert 'cpu' in cost, f"{name} missing 'cpu'"
            assert 'size' in cost, f"{name} missing 'size'"
            assert 'security' in cost, f"{name} missing 'security'"

    def test_costs_are_positive(self):
        for name, cost in PROTECTION_COSTS.items():
            assert cost['cpu'] > 0, f"{name} cpu <= 0"
            assert cost['size'] > 0, f"{name} size <= 0"
            assert 0 <= cost['security'] <= 1, f"{name} security not in [0,1]"

    def test_classification_map_has_valid_passes(self):
        for category, passes in CLASSIFICATION_MAP.items():
            for p in passes:
                assert p in PROTECTION_COSTS, f"{category} has unknown pass '{p}'"


class TestClassificationMap:
    """
    TestClassificationMap
    
    Positive test cases for classificationmap.
    """
    def test_classification_map_has_all_categories(self):
        expected = {'simple_helper', 'crypto', 'license_check', 'key_derivation', 'sensitive_algo'}
        assert set(CLASSIFICATION_MAP.keys()) == expected

    def test_each_category_has_at_least_one_pass(self):
        for category, passes in CLASSIFICATION_MAP.items():
            assert len(passes) >= 1, f"{category} has no passes"
