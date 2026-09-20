import ast
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from typing import Dict, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _parse(path_or_source):
    if os.path.exists(path_or_source):
        with open(path_or_source, encoding="utf-8") as f:
            return ast.parse(f.read())
    return ast.parse(path_or_source)


def _ast_node_type_distribution(tree):
    types = Counter()
    for node in ast.walk(tree):
        types[type(node).__name__] += 1
    return types


def _ast_depth(tree):
    max_depth = 0

    def _walk(node, depth):
        nonlocal max_depth
        max_depth = max(max_depth, depth)
        for child in ast.iter_child_nodes(node):
            _walk(child, depth + 1)

    _walk(tree, 0)
    return max_depth


def _cfg_blocks_and_edges(tree):
    blocks = set()
    edges = Counter()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            blocks.add(id(node))
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                    blocks.add(id(child))
                    edges["branch"] += 1
            edges["sequential"] += 1
        if isinstance(node, (ast.Return, ast.Raise)):
            edges["exit"] += 1
        if isinstance(node, ast.Call):
            edges["call"] += 1

    return len(blocks), edges


def _kl_divergence(p, q, eps=1e-10):
    divergence = 0.0
    all_keys = set(p.keys()) | set(q.keys())
    for k in all_keys:
        pk = p.get(k, 0) + eps
        qk = q.get(k, 0) + eps
        divergence += pk * math.log2(pk / qk)
    return divergence


def _jensen_shannon(p, q, eps=1e-10):
    m = {}
    all_keys = set(p.keys()) | set(q.keys())
    for k in all_keys:
        pk = p.get(k, 0) + eps
        qk = q.get(k, 0) + eps
        m[k] = (pk + qk) / 2.0

    return (_kl_divergence(p, m, eps) + _kl_divergence(q, m, eps)) / 2.0


def _normalize_counter(c: Counter):
    total = sum(c.values())
    if total == 0:
        return {}
    return {k: v / total for k, v in c.items()}


def compute_cfg_similarity(tree_a, tree_b) -> float:
    blocks_a, edges_a = _cfg_blocks_and_edges(tree_a)
    blocks_b, edges_b = _cfg_blocks_and_edges(tree_b)

    norm_a = _normalize_counter(edges_a)
    norm_b = _normalize_counter(edges_b)

    js = _jensen_shannon(norm_a, norm_b)
    similarity = 1.0 - min(1.0, js)

    block_ratio = min(blocks_a, blocks_b) / max(max(blocks_a, blocks_b), 1)
    similarity = similarity * 0.6 + block_ratio * 0.4
    return round(similarity, 4)


def compute_ast_similarity(tree_a, tree_b) -> float:
    types_a = _ast_node_type_distribution(tree_a)
    types_b = _ast_node_type_distribution(tree_b)

    norm_a = _normalize_counter(types_a)
    norm_b = _normalize_counter(types_b)

    js = _jensen_shannon(norm_a, norm_b)
    tree_sim = 1.0 - min(1.0, js)

    depth_a = _ast_depth(tree_a)
    depth_b = _ast_depth(tree_b)
    depth_ratio = min(depth_a, depth_b) / max(max(depth_a, depth_b), 1)

    total_sim = tree_sim * 0.7 + depth_ratio * 0.3
    return round(total_sim, 4)


def compute_bytecode_similarity(path_a: str, path_b: str) -> float:
    try:
        with open(path_a, "rb") as f:
            data_a = f.read()
        with open(path_b, "rb") as f:
            data_b = f.read()

        def ngrams(data, n=4):
            c = Counter()
            for i in range(len(data) - n + 1):
                c[data[i : i + n]] += 1
            return c

        ng_a = ngrams(data_a)
        ng_b = ngrams(data_b)

        intersection = sum((ng_a & ng_b).values())
        union = sum((ng_a | ng_b).values())
        jaccard = intersection / max(union, 1)

        norm_a = _normalize_counter(ng_a)
        norm_b = _normalize_counter(ng_b)
        js = _jensen_shannon(norm_a, norm_b)
        js_sim = 1.0 - min(1.0, js)

        return round(jaccard * 0.5 + js_sim * 0.5, 4)
    except Exception:
        return 0.0


def compute_ir_similarity(tree_a, tree_b) -> float:
    def count_ssa_features(tree):
        features = Counter()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                features["assign"] += len(node.targets)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                features["store"] += 1
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                features["load"] += 1
            if isinstance(node, ast.BinOp):
                features["binop"] += 1
            if isinstance(node, ast.Call):
                features["call"] += 1
            if isinstance(node, ast.If):
                features["branch"] += 1
            if isinstance(node, (ast.For, ast.While)):
                features["loop"] += 1
            if isinstance(node, ast.FunctionDef):
                features["func"] += 1
        return features

    fa = count_ssa_features(tree_a)
    fb = count_ssa_features(tree_b)

    norm_a = _normalize_counter(fa)
    norm_b = _normalize_counter(fb)

    js = _jensen_shannon(norm_a, norm_b)
    return round(1.0 - min(1.0, js), 4)


def compute_diversity_matrix(variants: list) -> Dict[Tuple[int, int], dict]:
    trees = {}
    for path in variants:
        try:
            trees[path] = _parse(path)
        except SyntaxError:
            trees[path] = None

    matrix = {}
    for i, a in enumerate(variants):
        for j, b in enumerate(variants):
            if i >= j:
                continue
            if trees[a] is None or trees[b] is None:
                continue
            pair = (i, j)
            cfg_sim = compute_cfg_similarity(trees[a], trees[b])
            ast_sim = compute_ast_similarity(trees[a], trees[b])
            ir_sim = compute_ir_similarity(trees[a], trees[b])
            bytecode_sim = compute_bytecode_similarity(a, b)

            overall_diversity = 1.0 - (
                cfg_sim * 0.30 + ast_sim * 0.25 + ir_sim * 0.25 + bytecode_sim * 0.20
            )

            matrix[pair] = {
                "cfg_similarity": cfg_sim,
                "ast_similarity": ast_sim,
                "ir_similarity": ir_sim,
                "bytecode_similarity": bytecode_sim,
                "overall_diversity": round(overall_diversity, 4),
            }
    return matrix


class DiversityMetrics:
    def __init__(self):
        self._cache = {}

    def compare(self, variant_a_path: str, variant_b_path: str) -> dict:
        tree_a = _parse(variant_a_path)
        tree_b = _parse(variant_b_path)

        cfg_sim = compute_cfg_similarity(tree_a, tree_b)
        ast_sim = compute_ast_similarity(tree_a, tree_b)
        ir_sim = compute_ir_similarity(tree_a, tree_b)
        bytecode_sim = compute_bytecode_similarity(variant_a_path, variant_b_path)

        overall_diversity = 1.0 - (
            cfg_sim * 0.30 + ast_sim * 0.25 + ir_sim * 0.25 + bytecode_sim * 0.20
        )

        return {
            "cfg_similarity": cfg_sim,
            "ast_similarity": ast_sim,
            "ir_similarity": ir_sim,
            "bytecode_similarity": bytecode_sim,
            "overall_diversity": round(overall_diversity, 4),
        }

    def fingerprint(self, variant_path: str) -> str:
        tree = _parse(variant_path)

        types = _ast_node_type_distribution(tree)
        blocks, edges = _cfg_blocks_and_edges(tree)
        depth = _ast_depth(tree)

        fingerprint_parts = []
        fingerprint_parts.append(f"blocks:{blocks}")
        for etype, count in sorted(edges.items()):
            fingerprint_parts.append(f"edge_{etype}:{count}")
        for ntype, count in sorted(types.most_common(15)):
            fingerprint_parts.append(f"node_{ntype}:{count}")
        fingerprint_parts.append(f"depth:{depth}")

        raw = "|".join(fingerprint_parts)
        h = hashlib.sha256(raw.encode()).hexdigest()
        return h

    def compare_all(self, variants: list) -> dict:
        matrix = compute_diversity_matrix(variants)
        diversities = [v["overall_diversity"] for v in matrix.values()]
        return {
            "num_variants": len(variants),
            "num_pairs": len(matrix),
            "min_diversity": round(min(diversities), 4) if diversities else 0.0,
            "max_diversity": round(max(diversities), 4) if diversities else 0.0,
            "mean_diversity": round(sum(diversities) / max(len(diversities), 1), 4),
            "matrix": {f"({i},{j})": v for (i, j), v in matrix.items()},
        }

    def generate_report(self, variants: list, output_path: str):
        report = self.compare_all(variants)

        fingerprints = {}
        for path in variants:
            fprint = self.fingerprint(path)
            fprint_short = fprint[:12]
            fingerprints[os.path.basename(path)] = {
                "fingerprint": fprint,
                "fingerprint_short": fprint_short,
            }
        report["fingerprints"] = fingerprints

        unique_fps = set(v["fingerprint"] for v in fingerprints.values())
        report["unique_fingerprints"] = len(unique_fps)
        report["all_unique"] = len(unique_fps) == len(variants)

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        return report
