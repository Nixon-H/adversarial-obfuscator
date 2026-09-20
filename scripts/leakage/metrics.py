"""
metrics.py

Purpose:
Low-level similarity and entropy metrics used by the semantic leakage
analyzers. Each function computes a single numeric score comparing
two IR modules (original vs. obfuscated).

Architectural Role:
Computational primitives for the leakage module. These are pure
functions with no side effects, designed to be composed by the
higher-level analyzers in analyzers.py.

Execution Context:
Called by analyzers (VariableLeakageAnalyzer, IntentLeakageAnalyzer,
ArchitectureLeakageAnalyzer) during leakage computation. Each function
takes IR module data and returns a numeric score.

Dependencies:
- Standard library (math, collections.Counter, typing)

Security Relevance:
Each metric captures a different obfuscation quality dimension:
- CFG similarity: how well control-flow obfuscation hides the CFG
- Opcode histogram: how much instruction selection changes
- Entropy: instruction diversity after obfuscation
- Name preservation: identifier renaming effectiveness
- Call graph similarity: call-graph restructuring effectiveness

Maintenance Notes:
- compute_cfg_similarity and compute_call_graph_similarity both use
  Jaccard-based metrics with different weighting schemes.
- compute_name_preservation filters out purely numeric SSA names
  (%0, %1, etc.) which are automatically assigned and not meaningful.
- All functions return 0-100 scores where higher = more similar
  (more leakage). The caller inverts or thresholds as needed.
"""

from __future__ import annotations
import math
from collections import Counter
from typing import Any


def compute_cfg_similarity(cfg_a: dict[str, list[str]], cfg_b: dict[str, list[str]]) -> float:
    """
    Compute Jaccard-based similarity between two CFGs.

    Combines node overlap (40% weight) and edge similarity (60% weight)
    into a 0-100 score. Higher values indicate more structural
    preservation (worse obfuscation).
    """
    nodes_a = set(cfg_a.keys())
    nodes_b = set(cfg_b.keys())
    if not nodes_a and not nodes_b:
        return 100.0
    intersection = nodes_a & nodes_b
    if not intersection:
        return 0.0
    edge_sim = 0.0
    total_possible = 0
    for node in intersection:
        succ_a = set(cfg_a.get(node, []))
        succ_b = set(cfg_b.get(node, []))
        if not succ_a and not succ_b:
            jaccard = 1.0
        else:
            jaccard = len(succ_a & succ_b) / max(len(succ_a | succ_b), 1)
        edge_sim += jaccard
        total_possible += 1
    node_jaccard = len(intersection) / max(len(nodes_a | nodes_b), 1)
    edge_score = edge_sim / max(total_possible, 1)
    return (node_jaccard * 0.4 + edge_score * 0.6) * 100.0


def compute_opcode_histogram(ir_module: Any) -> dict[str, float]:
    """
    Compute the normalized frequency histogram of opcodes in an IR module.

    Returns a dict of opcode -> proportion (0-1). Used by
    IntentLeakageAnalyzer to compare instruction selection patterns.
    """
    counter: Counter[str] = Counter()
    for func in ir_module.functions:
        for block in func.blocks:
            for inst in block.instructions:
                counter[inst.opcode] += 1
            if block.terminator:
                counter[block.terminator.opcode] += 1
    total = sum(counter.values())
    if total == 0:
        return {}
    return {op: count / total for op, count in counter.most_common()}


def compute_entropy(ir_module: Any) -> float:
    """
    Compute the Shannon entropy of opcode distribution in an IR module.

    Higher entropy means more diverse instruction selection, which is
    generally desirable for obfuscation (harder to predict patterns).
    """
    opcodes: list[str] = []
    for func in ir_module.functions:
        for block in func.blocks:
            for inst in block.instructions:
                opcodes.append(inst.opcode)
            if block.terminator:
                opcodes.append(block.terminator.opcode)
    if not opcodes:
        return 0.0
    freq: Counter[str] = Counter(opcodes)
    entropy = 0.0
    for count in freq.values():
        p = count / len(opcodes)
        entropy -= p * math.log2(p)
    return entropy


def compute_name_preservation(original: Any, obfuscated: Any) -> float:
    """
    Measure what percentage of meaningful names survive obfuscation.

    Filters out purely numeric SSA names (%0, %1, etc.) and compares
    function names and instruction result names. A lower score
    indicates better renaming.
    """
    orig_names: set[str] = set()
    for func in original.functions:
        orig_names.add(func.name)
        for block in func.blocks:
            for inst in block.instructions:
                if inst.result and inst.result.name and inst.result.name.startswith("%"):
                    orig_names.add(inst.result.name)
    obf_names: set[str] = set()
    for func in obfuscated.functions:
        obf_names.add(func.name)
        for block in func.blocks:
            for inst in block.instructions:
                if inst.result and inst.result.name and inst.result.name.startswith("%"):
                    obf_names.add(inst.result.name)
    if not orig_names:
        return 100.0
    common = orig_names & obf_names
    meaningful_common = {n for n in common if not n[1:].isdigit()}
    total_meaningful = {n for n in orig_names if not n[1:].isdigit()}
    if not total_meaningful:
        return 100.0
    return len(meaningful_common) / len(total_meaningful) * 100.0


def compute_call_graph_similarity(calls_a: dict[str, list[str]], calls_b: dict[str, list[str]]) -> float:
    """
    Compute Jaccard-based similarity between two call graphs.

    For each function, compares the set of called targets. Returns
    0-100 score. High similarity means the call-graph structure was
    preserved (weak obfuscation).
    """
    funcs_a = set(calls_a.keys())
    funcs_b = set(calls_b.keys())
    if not funcs_a and not funcs_b:
        return 100.0
    if not funcs_a or not funcs_b:
        return 0.0
    all_funcs = funcs_a | funcs_b
    matched = 0
    total = 0
    for f in all_funcs:
        targets_a = set(calls_a.get(f, []))
        targets_b = set(calls_b.get(f, []))
        if targets_a or targets_b:
            jaccard = len(targets_a & targets_b) / max(len(targets_a | targets_b), 1)
            matched += jaccard
            total += 1
    if total == 0:
        return 100.0
    return matched / total * 100.0
