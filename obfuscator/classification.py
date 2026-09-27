#!/usr/bin/env python3
"""
Advanced Protection: Classification Pass

Analyzes Python source code and classifies each function into one of three
categories: standard (90-95%), crown_jewel (5-10%), or jit_target (<1%).

This pass controls which code path each function takes through the pipeline:
  - Standard   → Shadow IR → LLVM → native binary
  - Crown Jewel → VM bytecode compilation, full VM protection
  - JIT Target  → Encrypted template with JIT specialization

Usage:
  python -m obfuscator.classification scan <source.py>
  python -m obfuscator.classification classify <source.py> -o report.txt
"""

import ast
import re
import math
import argparse
import sys
import os


# ---------------------------------------------------------------------------
# Decorator extraction
# ---------------------------------------------------------------------------

def extract_decorations(source: str) -> dict[str, str]:
    """Extract @protect() decorations from source.

    Supported syntax:
        @protect('crown_jewel')
        @protect('jit')
        @protect('standard')

    Returns {function_name: classification}
    """
    decorations = {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return decorations

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if (isinstance(dec, ast.Call)
                        and isinstance(dec.func, ast.Name)
                        and dec.func.id == 'protect'
                        and dec.args
                        and isinstance(dec.args[0], ast.Constant)):
                    label = str(dec.args[0].value).lower()
                    if label == 'jit':
                        decorations[node.name] = 'jit_target'
                    elif label in ('standard', 'crown_jewel'):
                        decorations[node.name] = label
    return decorations


# ---------------------------------------------------------------------------
# Heuristic scoring
# ---------------------------------------------------------------------------

CRYPTO_KEYWORDS = frozenset({
    'aes', 'encrypt', 'decrypt', 'cipher', 'hashlib', 'hmac',
    'derive_key', 'pbkdf2', 'bcrypt', 'argon2', 'sha256', 'sha512',
    'md5', 'rsa', 'dsa', 'ecc', 'elliptic', 'signature', 'verify',
    'padding', 'oracle', 'cbc', 'ctr', 'gcm', 'salted',
})

COMPLEX_FLOW_KEYWORDS = frozenset({
    'while', 'for', 'try', 'except', 'finally', 'with',
    'lambda', 'yield', 'async', 'await', 'global',
})


def _function_size_lines(node: ast.FunctionDef) -> int:
    """Count approximate line count of a function body."""
    if not node.body:
        return 0
    first = node.body[0].lineno if hasattr(node.body[0], 'lineno') else 0
    last = node.body[-1].end_lineno if hasattr(node.body[-1], 'end_lineno') else 0
    return max(0, last - first + 1)


def _count_crypto_ops(node: ast.AST) -> int:
    """Count cryptographic operation indicators in an AST subtree."""
    count = 0
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id in CRYPTO_KEYWORDS:
            count += 1
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            attr = child.func.attr.lower()
            name = child.func.value if isinstance(child.func.value, ast.Name) else None
            # Method calls like cipher.encrypt(), hasher.digest(), hmac.new()
            if any(kw in attr for kw in ('encrypt', 'decrypt', 'hash', 'cipher',
                                          'digest', 'verify', 'sign', 'new',
                                          'pbkdf2', 'derive')):
                count += 1
                if name and name.id in CRYPTO_KEYWORDS:
                    count += 1
    return count


def _count_complex_flow(node: ast.AST) -> int:
    """Count complex control-flow constructs."""
    count = 0
    for child in ast.walk(node):
        if isinstance(child, (ast.While, ast.For, ast.Try, ast.With)):
            count += 1
        if isinstance(child, ast.Lambda):
            count += 1
        if isinstance(child, ast.Yield):
            count += 1
        if isinstance(child, ast.Await):
            count += 1
    return count


def _count_constant_literals(node: ast.AST) -> int:
    """Count constant literals (numbers, strings) that indicate data tables."""
    count = 0
    for child in ast.walk(node):
        if isinstance(child, ast.Constant):
            if isinstance(child.value, (int, float)):
                if abs(child.value) > 1000:
                    count += 1
            elif isinstance(child.value, str) and len(child.value) > 40:
                count += 1
            elif isinstance(child.value, bytes) and len(child.value) > 16:
                count += 1
    return count


def _check_startup_patterns(node: ast.FunctionDef, source_lines: list[str]) -> bool:
    """Heuristic: is this function likely called only at startup?"""
    name_lower = node.name.lower()
    startup_indicators = ('init', 'setup', 'config', 'bootstrap', 'load',
                          'register', 'parse_args', 'read_config', 'import_')
    if any(name_lower.startswith(s) for s in startup_indicators):
        return True
    if _function_size_lines(node) < 10:
        return True
    return False


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------

_SCORE_WEIGHTS = {
    'crypto_ops': 0.35,
    'complex_flow': 0.20,
    'constant_literals': 0.15,
    'startup_small': 0.15,
    'explicit_tag': 0.40,
    'name_bonus': 0.20,
}

_FN_NAME_CRYPTO_KEYWORDS = frozenset({
    'encrypt', 'decrypt', 'cipher', 'hash', 'key', 'sign', 'verify',
    'auth', 'license', 'token', 'salt', 'hmac', 'derive', 'pbkdf',
    'digest', 'signature',
})


def _function_name_bonus(node: ast.FunctionDef) -> float:
    """Direct score bonus if function name suggests cryptographic purpose."""
    name_lower = node.name.lower()
    for kw in _FN_NAME_CRYPTO_KEYWORDS:
        if kw in name_lower:
            return _SCORE_WEIGHTS['name_bonus']
    return 0.0


def _compute_scores(tree: ast.AST, source_lines: list[str]) -> dict:
    """Compute heuristic scores for every function in the AST.

    Returns a dict: {function_name: {'crown_jewel': float, 'jit_target': float}}
    """
    scores = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        crypto = _count_crypto_ops(node)
        complexity = _count_complex_flow(node)
        constants = _count_constant_literals(node)
        is_startup = _check_startup_patterns(node, source_lines)
        size = _function_size_lines(node)
        name_bonus = _function_name_bonus(node)

        crown_jewel_score = 0.0
        jit_score = 0.0

        crown_jewel_score += min(1.0, crypto / 2) * _SCORE_WEIGHTS['crypto_ops']
        crown_jewel_score += min(1.0, complexity / 4) * _SCORE_WEIGHTS['complex_flow']
        crown_jewel_score += min(1.0, constants / 3) * _SCORE_WEIGHTS['constant_literals']
        crown_jewel_score += name_bonus

        if is_startup and size < 10:
            jit_score += min(1.0, (10 - size) / 10) * _SCORE_WEIGHTS['startup_small']

        # Mutual inhibition: strong CJ score suppresses JIT, and vice versa
        if jit_score > 0:
            crown_jewel_score = max(0.0, crown_jewel_score - jit_score * 0.3)
        if crown_jewel_score > 0:
            jit_score = max(0.0, jit_score - crown_jewel_score * 0.3)

        scores[node.name] = {
            'crown_jewel': crown_jewel_score,
            'jit_target': jit_score,
        }

    return scores


# ---------------------------------------------------------------------------
# Classification dispatcher
# ---------------------------------------------------------------------------

def classify_functions(source: str, config: dict | None = None) -> dict[str, str]:
    """Classify each function in the source.

    Returns: {function_name: 'standard' | 'crown_jewel' | 'jit_target'}

    Classification criteria (from config or built-in defaults):
    - Crown jewel: functions matching patterns in config['crown_jewel_patterns']
      or manually tagged with @protect('crown_jewel')
    - JIT target:  functions matching config['jit_patterns']
      or small startup-only functions
    - Everything else: standard
    """
    if config is None:
        config = {}

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise ValueError(f"Cannot parse source: {e}") from e

    source_lines = source.splitlines()

    # 1. Explicit decorations always win
    explicit = extract_decorations(source)

    # 2. Heuristic scores
    scores = _compute_scores(tree, source_lines)

    # 3. Pattern-based overrides from config
    crown_jewel_patterns = config.get('crown_jewel_patterns', [])
    jit_patterns = config.get('jit_patterns', [])

    # 4. Crown-jewel threshold from config or sensible default
    cj_threshold = config.get('crown_jewel_threshold', 0.40)
    jit_threshold = config.get('jit_threshold', 0.35)

    results = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        name = node.name

        # Explicit tag takes precedence
        if name in explicit:
            results[name] = explicit[name]
            continue

        # Pattern match
        if crown_jewel_patterns:
            if any(re.search(p, name) for p in crown_jewel_patterns):
                results[name] = 'crown_jewel'
                continue
        if jit_patterns:
            if any(re.search(p, name) for p in jit_patterns):
                results[name] = 'jit_target'
                continue

        # Heuristic scores
        fn_scores = scores.get(name, {'crown_jewel': 0.0, 'jit_target': 0.0})

        if fn_scores['crown_jewel'] + 1e-9 >= cj_threshold:
            results[name] = 'crown_jewel'
        elif fn_scores['jit_target'] + 1e-9 >= jit_threshold:
            results[name] = 'jit_target'
        else:
            results[name] = 'standard'

    return results


def _score_of(classifications: dict[str, str], fn: str, scores: dict) -> float:
    """Return the relevant heuristic score for a classified function."""
    cls = classifications.get(fn, 'standard')
    fn_scores = scores.get(fn, {'crown_jewel': 0.0, 'jit_target': 0.0})
    if cls == 'crown_jewel':
        return fn_scores.get('crown_jewel', 0.0)
    elif cls == 'jit_target':
        return fn_scores.get('jit_target', 0.0)
    return 0.0


# ---------------------------------------------------------------------------
# Analysis report
# ---------------------------------------------------------------------------

def generate_classification_report(classifications: dict[str, str], source: str) -> str:
    """Generate a human-readable classification report."""
    total = len(classifications)
    if total == 0:
        return "No functions found in source.\n"

    counts = {'standard': 0, 'crown_jewel': 0, 'jit_target': 0}
    buckets = {'standard': [], 'crown_jewel': [], 'jit_target': []}

    try:
        tree = ast.parse(source)
        scores = _compute_scores(tree, source.splitlines())
    except SyntaxError:
        scores = {}

    for fn, cls in classifications.items():
        counts[cls] += 1
        buckets[cls].append(fn)

    def pct(n: int) -> str:
        return f"{n / total * 100:.1f}"

    lines = []
    W = 53
    lines.append("┌" + "─" * W + "┐")
    lines.append("│  Classification Report" + " " * (W - 24) + "│")
    lines.append("├" + "─" * W + "┤")
    lines.append(f"│  Standard:    {counts['standard']:3d} functions ({pct(counts['standard']):>5s}%)  │")
    lines.append(f"│  Crown Jewel: {counts['crown_jewel']:3d} functions ({pct(counts['crown_jewel']):>5s}%)  │")
    lines.append(f"│  JIT Target:  {counts['jit_target']:3d} function{'' if counts['jit_target'] == 1 else 's'} ({pct(counts['jit_target']):>5s}%)  │")
    lines.append("├" + "─" * W + "┤")

    if buckets['crown_jewel']:
        lines.append("│  Crown Jewels:" + " " * (W - 16) + "│")
        for fn in buckets['crown_jewel']:
            sc = _score_of(classifications, fn, scores)
            label = f"    {fn} (score: {sc:.2f})"
            lines.append("│" + label + " " * (W - len(label) - 1) + "│")

    if buckets['jit_target']:
        lines.append("│  JIT Targets:" + " " * (W - 14) + "│")
        for fn in buckets['jit_target']:
            sc = _score_of(classifications, fn, scores)
            label = f"    {fn} (score: {sc:.2f})"
            lines.append("│" + label + " " * (W - len(label) - 1) + "│")

    lines.append("└" + "─" * W + "┘")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Nixon Advanced Protection — Classification Pass",
    )
    parser.add_argument("action", choices=["scan", "classify"],
                        help="scan: print function list; classify: produce report")
    parser.add_argument("source", help="Python source file to analyze")
    parser.add_argument("-o", "--output", help="Write report to file (classify only)")
    parser.add_argument("--cj-threshold", type=float, default=0.40,
                        help="Crown jewel score threshold (default: 0.40)")
    parser.add_argument("--jit-threshold", type=float, default=0.35,
                        help="JIT target score threshold (default: 0.35)")

    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"Error: file not found: {args.source}", file=sys.stderr)
        sys.exit(1)

    with open(args.source, "r") as f:
        source = f.read()

    config = {
        'crown_jewel_threshold': args.cj_threshold,
        'jit_threshold': args.jit_threshold,
    }

    if args.action == "scan":
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            print(f"Syntax error: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"Functions in {args.source}:")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                print(f"  {node.name}")
        sys.exit(0)

    # classify
    classifications = classify_functions(source, config)
    report = generate_classification_report(classifications, source)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
