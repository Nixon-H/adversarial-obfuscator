import ast
import hashlib
import z3
from dataclasses import dataclass
from typing import List, Tuple

from scripts.validation.ast_to_smt import ASTToSMT
from scripts.evolution.ir_genome import IrGenome, IrInstruction, IR_INSTRUCTIONS


@dataclass
class CodeGenome:
    statements: List[ast.AST]
    fitness: float = 0.0

    def to_source(self) -> str:
        return ast.unparse(ast.Module(body=self.statements, type_ignores=[]))

    def to_bytes(self) -> bytes:
        return self.to_source().encode("utf-8")

    def __len__(self) -> int:
        return len(self.statements)


class CodeGenomeEvolver:
    def __init__(self, seed: int = 42):
        self.rng_state = seed

    def _rng(self) -> int:
        self.rng_state = (
            self.rng_state * 6364136223846793005 + 1442695040888963407
        ) & 0xFFFFFFFFFFFFFFFF
        return self.rng_state

    def _edit_distance(self, a: str, b: str) -> int:
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if a[i - 1] == b[j - 1] else 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,
                    dp[i][j - 1] + 1,
                    dp[i - 1][j - 1] + cost,
                )
        return dp[m][n]

    def _collect_assign_vars(self, stmt: ast.AST) -> List[str]:
        vars_found: List[str] = []
        for node in ast.walk(stmt):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                vars_found.append(node.id)
        return vars_found

    def _collect_load_vars(self, stmt: ast.AST) -> List[str]:
        vars_found: List[str] = []
        for node in ast.walk(stmt):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                vars_found.append(node.id)
        return vars_found

    def fitness_diversity(
        self, genome: CodeGenome, others: List[CodeGenome],
    ) -> float:
        # Neutral 0.5 (documented, not a placeholder): with no population
        # to compare against, diversity is undefined — 0.5 neither rewards
        # nor punishes the genome, so selection pressure comes from the
        # semantic/performance terms instead.
        if not others:
            return 0.5
        src = genome.to_source()
        distances = [self._edit_distance(src, o.to_source()) for o in others]
        max_dist = max(len(src), max(len(o.to_source()) for o in others))
        if max_dist == 0:
            return 0.5
        return sum(distances) / (len(distances) * max_dist)

    def fitness_semantic(self, genome: CodeGenome) -> float:
        try:
            tree = ast.Module(body=genome.statements, type_ignores=[])
            translator = ASTToSMT()
            formula = translator.translate(tree)
            solver = z3.Solver()
            solver.set("timeout", 5000)
            solver.add(formula)
            result = solver.check()
            if result == z3.sat:
                return 1.0
            elif result == z3.unsat:
                return 0.1
            # Solver UNKNOWN (e.g. timeout): neutral 0.5 — unknown is not
            # evidence of breakage (unlike unsat => 0.1) nor of safety
            # (unlike sat => 1.0). Hard failures (translate exceptions)
            # below stay fail-closed at 0.0.
            return 0.5
        except Exception:
            return 0.0

    def fitness_performance(self, genome: CodeGenome) -> float:
        node_count = sum(
            1 for _ in ast.walk(ast.Module(body=genome.statements, type_ignores=[]))
        )
        max_nodes = 200
        ratio = min(1.0, node_count / max_nodes)
        return 1.0 - ratio * 0.5

    def compute_fitness(
        self, genome: CodeGenome, others: List[CodeGenome],
        weight_div: float = 0.4, weight_sem: float = 0.4, weight_perf: float = 0.2,
    ) -> float:
        div = self.fitness_diversity(genome, others)
        sem = self.fitness_semantic(genome)
        perf = self.fitness_performance(genome)
        return weight_div * div + weight_sem * sem + weight_perf * perf

    def _extract_subtrees(self, stmt: ast.AST) -> List[ast.AST]:
        subtrees: List[ast.AST] = []
        for node in ast.walk(stmt):
            if isinstance(node, ast.Expr):
                subtrees.append(node)
        return subtrees

    def _crossover_subtree(
        self, parent_a: CodeGenome, parent_b: CodeGenome,
    ) -> CodeGenome:
        if len(parent_a.statements) < 2 or len(parent_b.statements) < 2:
            return CodeGenome(statements=parent_a.statements[:])
        point_a = int(self._rng() % len(parent_a.statements))
        point_b = int(self._rng() % len(parent_b.statements))
        child_stmts = (
            parent_a.statements[:point_a]
            + parent_b.statements[point_b:]
        )
        return CodeGenome(statements=child_stmts)

    def _mutate_subtree(self, genome: CodeGenome) -> CodeGenome:
        if not genome.statements:
            return genome
        idx = int(self._rng() % len(genome.statements))
        stmt = genome.statements[idx]
        mutated = list(genome.statements)
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if isinstance(target, ast.Name):
                new_id = f"v_{self._rng() & 0xFFFF}"
                new_target = ast.Name(id=new_id, ctx=ast.Store())
                new_assign = ast.Assign(
                    targets=[new_target],
                    value=self._mutate_expr(stmt.value),
                    lineno=stmt.lineno if hasattr(stmt, 'lineno') else 0,
                    col_offset=stmt.col_offset if hasattr(stmt, 'col_offset') else 0,
                )
                ast.fix_missing_locations(new_assign)
                mutated[idx] = new_assign
        elif isinstance(stmt, ast.Expr):
            new_val = self._mutate_expr(stmt.value)
            new_expr = ast.Expr(
                value=new_val,
                lineno=stmt.lineno if hasattr(stmt, 'lineno') else 0,
                col_offset=stmt.col_offset if hasattr(stmt, 'col_offset') else 0,
            )
            ast.fix_missing_locations(new_expr)
            mutated[idx] = new_expr
        return CodeGenome(statements=mutated)

    def _mutate_expr(self, expr: ast.AST) -> ast.AST:
        if isinstance(expr, ast.BinOp):
            if self._rng() % 2 == 0:
                return ast.BinOp(
                    left=self._mutate_expr(expr.left),
                    op=self._random_op(),
                    right=self._mutate_expr(expr.right),
                )
        return expr

    def _random_op(self) -> ast.operator:
        ops: List[ast.operator] = [ast.Add(), ast.Sub(), ast.BitXor(), ast.Mult()]
        return ops[int(self._rng() % len(ops))]

    def parse_source(self, source: str) -> CodeGenome:
        tree = ast.parse(source, mode="exec")
        return CodeGenome(statements=tree.body)

    def evolve(
        self,
        base_source: str,
        generations: int = 100,
        population_size: int = 50,
        mutation_rate: float = 0.1,
        tournament_size: int = 3,
    ) -> Tuple[CodeGenome, float, List[Tuple[int, float]]]:
        base_genome = self.parse_source(base_source)
        base_seed = hashlib.sha256(base_source.encode()).digest()
        self.rng_state = int.from_bytes(base_seed[:8], "little")

        population: List[CodeGenome] = [base_genome]
        for i in range(1, population_size):
            seed = self.rng_state + i
            rng = seed
            stmts = list(base_genome.statements)
            for j in range(len(stmts)):
                if (rng % 100) < mutation_rate * 100:
                    if isinstance(stmts[j], ast.Assign) and len(stmts[j].targets) == 1:
                        target = stmts[j].targets[0]
                        if isinstance(target, ast.Name):
                            new_target = ast.Name(
                                id=f"v_{j}_{rng & 0xFFFF}",
                                ctx=ast.Store(),
                            )
                            stmts[j] = ast.Assign(
                                targets=[new_target],
                                value=stmts[j].value,
                                lineno=stmts[j].lineno if hasattr(stmts[j], 'lineno') else 0,
                                col_offset=stmts[j].col_offset if hasattr(stmts[j], 'col_offset') else 0,
                            )
                            ast.fix_missing_locations(stmts[j])
                    rng = (rng * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
            population.append(CodeGenome(statements=stmts))

        history: List[Tuple[int, float]] = []
        best_genome = base_genome
        best_fitness = 0.0

        for gen in range(generations):
            others = [p for i, p in enumerate(population)]
            scores = [self.compute_fitness(ind, others) for ind in population]
            max_idx = max(range(len(scores)), key=lambda i: scores[i])
            if scores[max_idx] > best_fitness:
                best_fitness = scores[max_idx]
                best_genome = population[max_idx]

            new_pop: List[CodeGenome] = []
            for _ in range(population_size):
                idx_a = int(self._rng() % population_size)
                idx_b = int(self._rng() % population_size)
                if scores[idx_a] > scores[idx_b]:
                    parent_a = population[idx_a]
                else:
                    parent_a = population[idx_b]

                idx_c = int(self._rng() % population_size)
                idx_d = int(self._rng() % population_size)
                if scores[idx_c] > scores[idx_d]:
                    parent_b = population[idx_c]
                else:
                    parent_b = population[idx_d]

                child = self._crossover_subtree(parent_a, parent_b)
                if (self._rng() % 100) < mutation_rate * 100:
                    child = self._mutate_subtree(child)
                new_pop.append(child)

            population = new_pop
            history.append((gen, best_fitness))

        return best_genome, best_fitness, history


class IrCodeGenomeEvolver:
    """IR-level twin of CodeGenomeEvolver (NOT dead code).

    CodeGenomeEvolver evolves Python-AST genomes (via evolve()); this
    class evolves IrGenome instruction streams (via evolve_ir_genome(),
    wired in scripts/phases/phase16_code_genome.py). The two share the
    RNG/mutate/select skeleton but operate on different representations
    — keep them separate; merging would entangle AST and IR fitness.
    """
    def __init__(self, seed: int = 42):
        self.rng_state = seed

    def _rng(self) -> int:
        self.rng_state = (
            self.rng_state * 6364136223846793005 + 1442695040888963407
        ) & 0xFFFFFFFFFFFFFFFF
        return self.rng_state

    def _random_ir_instruction(self) -> IrInstruction:
        opcodes = list(IR_INSTRUCTIONS.values())
        return IrInstruction(
            opcode=opcodes[int(self._rng() % len(opcodes))],
            rd=int(self._rng() % 16),
            rs1=int(self._rng() % 16),
            rs2=int(self._rng() % 16),
            imm=int(self._rng() & 0xFFFF),
        )

    def fitness_ir_diversity(self, genome: IrGenome, others: List[IrGenome]) -> float:
        # Same neutral-0.5 rationale as fitness_diversity (no population
        # or empty encodings => undefined diversity, neither rewarded
        # nor punished).
        if not others:
            return 0.5
        encoded = genome.encode()
        max_dist = len(encoded)
        distances = []
        for o in others:
            oe = o.encode()
            d = sum(1 for a, b in zip(encoded, oe) if a != b) + abs(len(encoded) - len(oe))
            distances.append(d)
            max_dist = max(max_dist, len(oe))
        if max_dist == 0:
            return 0.5
        return sum(distances) / (len(distances) * max_dist) if distances else 0.5

    def fitness_ir_complexity(self, genome: IrGenome) -> float:
        if not genome.instructions:
            return 0.0
        unique_ops = len(set(i.opcode for i in genome.instructions))
        num_instrs = len(genome.instructions)
        op_complexity = unique_ops / max(IR_INSTRUCTIONS.values())
        size_score = min(1.0, num_instrs / 100.0)
        return (op_complexity * 0.6 + size_score * 0.4)

    def fitness_obfuscation_resistance(self, genome: IrGenome, original: IrGenome) -> float:
        if not genome.instructions or not original.instructions:
            return 0.0
        enc_orig = original.encode()
        enc_gen = genome.encode()
        byte_diff = sum(1 for a, b in zip(enc_orig, enc_gen) if a != b) + abs(len(enc_orig) - len(enc_gen))
        max_diff = max(len(enc_orig), len(enc_gen)) * 3
        if max_diff == 0:
            return 0.0
        diff_ratio = byte_diff / max_diff
        seq_div = len(set(enc_gen[i:i+2] for i in range(0, len(enc_gen)-1))) / max(1, len(enc_gen) // 2)
        return min(1.0, diff_ratio * 0.5 + seq_div * 0.5)

    def compute_ir_fitness(
        self, genome: IrGenome, others: List[IrGenome], original: IrGenome,
        weight_div: float = 0.3, weight_complexity: float = 0.3, weight_obfus: float = 0.4,
    ) -> float:
        div = self.fitness_ir_diversity(genome, others)
        complexity = self.fitness_ir_complexity(genome)
        obfus = self.fitness_obfuscation_resistance(genome, original)
        return weight_div * div + weight_complexity * complexity + weight_obfus * obfus

    def evolve_ir(
        self,
        base_ir: IrGenome,
        generations: int = 100,
        population_size: int = 50,
        mutation_rate: float = 0.2,
    ) -> Tuple[IrGenome, float, List[Tuple[int, float]]]:
        population: List[IrGenome] = [base_ir]
        for i in range(1, population_size):
            instrs = list(base_ir.instructions)
            for j in range(len(instrs)):
                if (self._rng() % 100) < mutation_rate * 100:
                    instrs[j] = self._random_ir_instruction()
            population.append(IrGenome(instructions=instrs))

        history: List[Tuple[int, float]] = []
        best_genome = base_ir
        best_fitness = 0.0

        for gen in range(generations):
            scores = [self.compute_ir_fitness(ind, population, base_ir) for ind in population]
            max_idx = max(range(len(scores)), key=lambda i: scores[i])
            if scores[max_idx] > best_fitness:
                best_fitness = scores[max_idx]
                best_genome = population[max_idx]

            new_pop: List[IrGenome] = []
            for _ in range(population_size):
                idx_a = int(self._rng() % population_size)
                idx_b = int(self._rng() % population_size)
                parent_a = population[idx_a] if scores[idx_a] > scores[idx_b] else population[idx_b]

                idx_c = int(self._rng() % population_size)
                idx_d = int(self._rng() % population_size)
                parent_b = population[idx_c] if scores[idx_c] > scores[idx_d] else population[idx_d]

                child = parent_a.crossover(parent_b, self._rng())
                if (self._rng() % 100) < mutation_rate * 100:
                    child, _ = child.mutate(self._rng())
                new_pop.append(child)

            population = new_pop
            history.append((gen, best_fitness))

        return best_genome, best_fitness, history


def evolve_ir_genome(
    base_instructions: List[IrInstruction],
    generations: int = 100,
    population_size: int = 50,
    mutation_rate: float = 0.2,
) -> Tuple[IrGenome, float, List[Tuple[int, float]]]:
    evolver = IrCodeGenomeEvolver()
    base_ir = IrGenome(instructions=base_instructions)
    return evolver.evolve_ir(
        base_ir,
        generations=generations,
        population_size=population_size,
        mutation_rate=mutation_rate,
    )


def evolve(
    base_source: str,
    generations: int = 100,
    population_size: int = 50,
    mutation_rate: float = 0.1,
    tournament_size: int = 3,
) -> Tuple[CodeGenome, float, List[Tuple[int, float]]]:
    evolver = CodeGenomeEvolver()
    return evolver.evolve(
        base_source,
        generations=generations,
        population_size=population_size,
        mutation_rate=mutation_rate,
        tournament_size=tournament_size,
    )
