import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestFragmentation:
    def test_algorithm_analyzer_empty_module(self, monkeypatch):
        from irgen.fragmentation import AlgorithmAnalyzer
        from irgen.compile import IrModule
        monkeypatch.setattr("irgen.fragmentation._phase2_enabled", lambda: True)
        analyzer = AlgorithmAnalyzer()
        result = analyzer.analyze(IrModule("empty"), "nonexistent")
        assert result == {"fragments": []}

    def test_algorithm_analyzer_with_func(self, monkeypatch, ir_module):
        from irgen.fragmentation import AlgorithmAnalyzer
        from irgen.compile import IrValue, IrType
        monkeypatch.setattr("irgen.fragmentation._phase2_enabled", lambda: True)
        entry = ir_module.functions[0].blocks[0]
        entry.instructions.append(type('Inst', (), {'result': IrValue(IrType.i32()), 'operands': [IrValue(IrType.i32())]})())
        analyzer = AlgorithmAnalyzer()
        result = analyzer.analyze(ir_module, "test_func")
        assert "fragments" in result

    def test_fragment_function_empty(self, monkeypatch):
        from irgen.fragmentation import fragment_function
        from irgen.compile import IrModule
        monkeypatch.setattr("irgen.fragmentation._phase2_enabled", lambda: True)
        frags, meta = fragment_function(IrModule("m"), "f", 3, b"seed")
        assert frags == []
        assert meta == {}

    def test_generate_coordinator(self, monkeypatch):
        from irgen.fragmentation import generate_coordinator
        from irgen.compile import IrFunction, IrType
        monkeypatch.setattr("irgen.fragmentation._phase2_enabled", lambda: True)
        frags = [IrFunction(f"f{i}", IrType.void()) for i in range(3)]
        meta = {"calling_sequence": [0, 1, 2]}
        coord = generate_coordinator(frags, meta, b"seed")
        assert coord is not None

    def test_generate_function_pointer_table(self, monkeypatch):
        from irgen.fragmentation import generate_function_pointer_table
        from irgen.compile import IrFunction, IrType
        monkeypatch.setattr("irgen.fragmentation._phase2_enabled", lambda: True)
        frags = [IrFunction("f0", IrType.void())]
        mod = generate_function_pointer_table(frags, "coord")
        assert len(mod.functions) == 1

    def test_suggest_boundaries(self, monkeypatch):
        from irgen.fragmentation import AlgorithmAnalyzer
        from irgen.compile import IrModule, IrValue, IrType
        monkeypatch.setattr("irgen.fragmentation._phase2_enabled", lambda: True)
        mod = IrModule("m")
        func = type('Func', (), {'name': 'f', 'blocks': []})()
        block = type('Block', (), {'instructions': [], 'label': 'entry'})()
        for i in range(10):
            inst = type('Inst', (), {
                'result': type('V', (), {'id': i, 'name': f'%{i}'})(),
                'operands': []
            })()
            block.instructions.append(inst)
        func.blocks = [block]
        mod.functions = [func]
        analyzer = AlgorithmAnalyzer()
        boundaries = analyzer.suggest_boundaries(mod, "f", 3)
        assert isinstance(boundaries, list)
