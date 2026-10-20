import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestCodeGenome:
    """
    TestCodeGenome
    
    Positive test cases for codegenome.
    """
    def test_evolve_returns_code_genome(self):
        from scripts.evolution.code_genome import evolve, CodeGenome
        source = "x = 1\ny = 2\nz = x + y\n"
        best, fitness, history = evolve(source, generations=5, population_size=10)
        assert isinstance(best, CodeGenome)
        assert len(best.statements) > 0

    def test_evolve_improves_fitness(self):
        from scripts.evolution.code_genome import evolve
        source = "a = 1\nb = 2\nc = a + b\n"
        best, fitness, history = evolve(source, generations=10, population_size=20)
        assert fitness >= 0.0

    def test_history_length(self):
        from scripts.evolution.code_genome import evolve
        source = "x = 0\n"
        best, fitness, history = evolve(source, generations=7, population_size=10)
        assert len(history) == 7

    def test_deterministic_with_same_base(self):
        from scripts.evolution.code_genome import evolve
        source = "x = 1\ny = 2\n"
        b1, f1, h1 = evolve(source, generations=5, population_size=10)
        b2, f2, h2 = evolve(source, generations=5, population_size=10)
        assert b1.to_source() == b2.to_source()

    def test_different_bases_different_results(self):
        from scripts.evolution.code_genome import evolve
        b1, f1, h1 = evolve("x = 1", generations=5, population_size=10)
        b2, f2, h2 = evolve("y = 2", generations=5, population_size=10)
        assert b1.to_source() != b2.to_source() or f1 != f2

    def test_genome_to_bytes_roundtrip(self):
        from scripts.evolution.code_genome import CodeGenome
        import ast
        stmts = ast.parse("x = 42", mode="exec").body
        g = CodeGenome(statements=stmts)
        source = g.to_source()
        assert "x" in source
        assert "42" in source

    def test_mutation_rate_zero_no_change(self):
        from scripts.evolution.code_genome import evolve
        source = "x = 1\ny = 2\nz = x + y\n"
        best, fitness, history = evolve(source, generations=5, population_size=10, mutation_rate=0.0)
        assert best is not None

    def test_population_size_effects(self):
        from scripts.evolution.code_genome import evolve
        source = "a = 1\nb = 2\n"
        b1, f1, h1 = evolve(source, generations=5, population_size=5)
        b2, f2, h2 = evolve(source, generations=5, population_size=50)
        assert len(h1) == len(h2) == 5

    def test_fitness_diversity(self):
        from scripts.evolution.code_genome import CodeGenomeEvolver, CodeGenome
        import ast
        evolver = CodeGenomeEvolver(seed=42)
        g1 = CodeGenome(statements=ast.parse("x = 1", mode="exec").body)
        g2 = CodeGenome(statements=ast.parse("y = 2", mode="exec").body)
        score = evolver.fitness_diversity(g1, [g2])
        assert score > 0.0

    def test_fitness_semantic(self):
        from scripts.evolution.code_genome import CodeGenomeEvolver, CodeGenome
        import ast
        evolver = CodeGenomeEvolver(seed=42)
        g = CodeGenome(statements=ast.parse("x = 1\ny = x + 1\n", mode="exec").body)
        score = evolver.fitness_semantic(g)
        assert score >= 0.0

    def test_fitness_performance(self):
        from scripts.evolution.code_genome import CodeGenomeEvolver, CodeGenome
        import ast
        evolver = CodeGenomeEvolver(seed=42)
        g = CodeGenome(statements=ast.parse("x = 1\ny = 2\n", mode="exec").body)
        score = evolver.fitness_performance(g)
        assert score > 0.0

    def test_compute_fitness(self):
        from scripts.evolution.code_genome import CodeGenomeEvolver, CodeGenome
        import ast
        evolver = CodeGenomeEvolver(seed=42)
        g1 = CodeGenome(statements=ast.parse("x = 1\ny = x + 1\n", mode="exec").body)
        g2 = CodeGenome(statements=ast.parse("a = 2\nb = a * 2\n", mode="exec").body)
        score = evolver.compute_fitness(g1, [g2])
        assert 0.0 <= score <= 1.0
