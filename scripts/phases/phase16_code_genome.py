"""
phase16_code_genome.py

Purpose:
Runs a genetic algorithm to evolve both source-level and IR-level code
genomes.  Evolves toward higher obfuscation fitness, producing evolved
genome files for runtime use.

Architectural Role:
Experimental phase — applies evolutionary techniques to find
harder-to-analyze code variants.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
ast, json, os, ..common, scripts.evolution.code_genome,
scripts.evolution.ir_genome

Security Relevance:
Evolutionary code generation discovers obfuscation patterns that
are resistant to current analysis tools.
"""

import ast
import json
import os

from ..common import log, BUILD_DIR


def phase_code_genome(base_genome_path=None, generations=50, population_size=30):
    """
    Evolve source and IR genomes toward optimal obfuscation fitness.

    Args:
        base_genome_path: optional path to seed the genome
        generations: number of evolution generations
        population_size: population per generation
    """
    log("CODE_GENOME", f"Running code genome evolution ({generations} gen, {population_size} pop)")
    log("CODE_GENOME", f"Running code genome evolution ({generations} gen, {population_size} pop)")

    source_text = None
    if base_genome_path and os.path.exists(base_genome_path):
        with open(base_genome_path, "r") as f:
            source_text = f.read()

    if not source_text:
        source_text = "x = 1\ny = 2\nz = x + y\n"

    try:
        from scripts.evolution.code_genome import evolve, CodeGenome, evolve_ir_genome
        from scripts.evolution.ir_genome import IrGenome, IrInstruction, IR_INSTRUCTIONS

        best_genome, fitness, history = evolve(
            source_text,
            generations=generations,
            population_size=population_size,
        )

        out_source_path = os.path.join(BUILD_DIR, "evolved_genome.py")
        with open(out_source_path, "w") as f:
            f.write(best_genome.to_source())

        out_bin_path = os.path.join(BUILD_DIR, "evolved_genome.bin")
        with open(out_bin_path, "wb") as f:
            f.write(best_genome.to_bytes())

        out_history_path = os.path.join(BUILD_DIR, "evolution_history.json")
        with open(out_history_path, "w") as f:
            f.write(json.dumps([{"gen": g, "fitness": f_} for g, f_ in history], indent=2))

        log("CODE_GENOME", f"Best fitness: {fitness:.6f}")
        log("CODE_GENOME", f"Genome source → {out_source_path}")
        log("CODE_GENOME", f"Genome binary → {out_bin_path}")

        base_instrs = [
            IrInstruction(opcode=IR_INSTRUCTIONS.get("add", 0x01), rd=0, rs1=1, rs2=2, imm=0),
            IrInstruction(opcode=IR_INSTRUCTIONS.get("xor", 0x06), rd=0, rs1=0, rs2=1, imm=0),
            IrInstruction(opcode=IR_INSTRUCTIONS.get("mul", 0x03), rd=2, rs1=0, rs2=3, imm=0),
        ]
        ir_best, ir_fitness, ir_history = evolve_ir_genome(
            base_instrs,
            generations=generations,
            population_size=population_size,
        )

        out_ir_path = os.path.join(BUILD_DIR, "evolved_ir_genome.ir")
        with open(out_ir_path, "w") as f:
            f.write(ir_best.to_ir_text())

        out_ir_bin_path = os.path.join(BUILD_DIR, "evolved_ir_genome.bin")
        with open(out_ir_bin_path, "wb") as f:
            f.write(ir_best.encode())

        out_ir_history_path = os.path.join(BUILD_DIR, "evolution_ir_history.json")
        with open(out_ir_history_path, "w") as f:
            f.write(json.dumps([{"gen": g, "fitness": f_} for g, f_ in ir_history], indent=2))

        log("CODE_GENOME", f"IR genome best fitness: {ir_fitness:.6f}")
        log("CODE_GENOME", f"IR genome → {out_ir_path}")
        log("CODE_GENOME", f"IR genome binary → {out_ir_bin_path}")
    except Exception as e:
        log("ERROR", f"Code genome evolution failed: {e}")
