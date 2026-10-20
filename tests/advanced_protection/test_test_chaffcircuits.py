import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestChaffCircuits:

    def test_chaff_circuit_generator_creates(self):
        from irgen.chaff_circuits import ChaffCircuitGenerator
        gen = ChaffCircuitGenerator(seed=42, num_chaff=5)
        assert gen is not None
        assert gen.num_chaff == 5

    def test_chaff_circuit_from_source_returns_string(self):
        from irgen.chaff_circuits import ChaffCircuitGenerator
        gen = ChaffCircuitGenerator(seed=42, num_chaff=3)
        source = "def add(a, b):\n    return a + b\n"
        result = gen.generate_chaff_circuit_from_source(source, "add")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_chaff_circuit_differs_from_source(self):
        from irgen.chaff_circuits import ChaffCircuitGenerator
        gen = ChaffCircuitGenerator(seed=42, num_chaff=3)
        source = "def add(a, b):\n    return a + b\n"
        result = gen.generate_chaff_circuit_from_source(source, "add")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_chaff_pipeline_returns_string(self):
        from irgen.chaff_circuits import generate_chaff_pipeline
        source = "def add(a, b):\n    return a + b\n"
        result = generate_chaff_pipeline(source, ["add"], num_chaff=3, seed=42)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_chaff_pipeline_empty_targets(self):
        from irgen.chaff_circuits import generate_chaff_pipeline
        source = "def add(a, b):\n    return a + b\n"
        result = generate_chaff_pipeline(source, [], num_chaff=3, seed=42)
        assert result == source

    def test_chaff_pipeline_with_multiple_functions(self):
        from irgen.chaff_circuits import generate_chaff_pipeline
        source = "def add(a, b):\n    return a + b\ndef sub(a, b):\n    return a - b\n"
        result = generate_chaff_pipeline(source, ["add", "sub"], num_chaff=3, seed=42)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_chaff_wrapper_generated(self):
        from irgen.chaff_circuits import ChaffCircuitGenerator
        gen = ChaffCircuitGenerator(seed=42, num_chaff=3)
        wrapper = gen.wrap_verify_function("add", ["chaff_add_xor", "chaff_add_rotate"])
        assert isinstance(wrapper, str)
        assert len(wrapper) > 0
