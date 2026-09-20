#!/usr/bin/env python3
"""
Deobfuscation Agent — analyzes obfuscated IR and AST to detect weaknesses
and generate feedback for the Compiler Mutation Engine.
"""

import ast
import os
import re
import random
import sys
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class AnalysisReport:
    ir_path: str = ""
    source: str = ""
    constant_folding_opportunities: int = 0
    cfg_flattening_detected: bool = False
    opaque_predicates_detected: bool = False
    opaque_predicate_count: int = 0
    dead_code_blocks: int = 0
    mba_patterns_detectable: int = 0
    deobfuscation_score: float = 1.0
    detected_patterns: List[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


class DeobfuscationAgent:
    MBA_PATTERNS = [
        re.compile(r'xor\s+.*,\s*and|and\s+.*,\s*xor'),
        re.compile(r'add\s+.*,\s*xor|xor\s+.*,\s*add'),
        re.compile(r'sub\s+.*,\s*add.*,\s*1'),
        re.compile(r'shl\s+.*,\s*1.*add|xor.*shl'),
    ]

    OPAQUE_PRED_PATTERNS = [
        re.compile(r'icmp\s+eq\s+i\d+\s+\d+,\s*\d+'),
        re.compile(r'icmp\s+ne\s+i\d+\s+\d+,\s*\d+'),
        re.compile(r'icmp\s+(eq|ne)\s+i\d+\s+%\S+,\s+%\S+'),
    ]

    DEAD_CODE_PATTERNS = [
        re.compile(r'dead_\w+\s*:'),
        re.compile(r'junk_\w+\s*:'),
    ]

    def __init__(self, config: dict):
        self.config = config
        self.feedback_history = []

    def analyze_obfuscated_ir(self, ir_path: str) -> AnalysisReport:
        report = AnalysisReport(ir_path=ir_path)

        if not os.path.exists(ir_path):
            report.details["error"] = f"File not found: {ir_path}"
            report.deobfuscation_score = 0.0
            return report

        with open(ir_path, "rb") as f:
            raw = f.read()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = raw.decode("latin-1")

        # 1. Constant folding detection
        const_ops = len(re.findall(r'(add|sub|mul|and|or|xor)\s+i\d+\s+\d+,\s*\d+', content))
        report.constant_folding_opportunities = const_ops

        # 2. CFG flattening detection
        switch_count = len(re.findall(r'switch\s+i32', content))
        dispatcher_count = len(re.findall(r'dispatcher_\w+\s*:', content))
        report.cfg_flattening_detected = switch_count > 1 or dispatcher_count > 0

        # 3. Opaque predicate detection
        pred_count = 0
        for pattern in self.OPAQUE_PRED_PATTERNS:
            pred_count += len(pattern.findall(content))
        report.opaque_predicates_detected = pred_count > 0
        report.opaque_predicate_count = pred_count

        # 4. Dead code detection
        dead_count = 0
        for pattern in self.DEAD_CODE_PATTERNS:
            dead_count += len(pattern.findall(content))
        # Also detect unreachable blocks after unconditional branches
        unreachable = len(re.findall(r'br\s+label.*\n(?!\s+br\s+label)', content))
        report.dead_code_blocks = dead_count + unreachable

        # 5. MBA pattern detection
        mba_count = 0
        for pattern in self.MBA_PATTERNS:
            mba_count += len(pattern.findall(content))
        report.mba_patterns_detectable = mba_count

        # Build detected patterns list
        patterns = []
        if report.cfg_flattening_detected:
            patterns.append("cfg_flattening")
        if report.opaque_predicates_detected:
            patterns.append("opaque_predicates")
        if report.constant_folding_opportunities > 3:
            patterns.append("constant_folding_possible")
        if report.dead_code_blocks > 0:
            patterns.append("dead_code_detectable")
        if report.mba_patterns_detectable > 0:
            patterns.append("mba_patterns_detectable")
        report.detected_patterns = patterns

        # Compute deobfuscation score (0 = fully deobfuscated, 1 = fully resistant)
        score = 1.0
        if report.cfg_flattening_detected:
            score -= 0.15 * min(switch_count, 5) / 5
        if report.opaque_predicates_detected:
            simplicity = 1.0 - min(pred_count, 10) / 10
            score -= 0.2 * simplicity
        if report.constant_folding_opportunities > 3:
            score -= 0.15 * min(const_ops, 10) / 10
        if report.dead_code_blocks > 2:
            score += 0.1
        if report.mba_patterns_detectable > 0:
            score -= 0.15 * min(mba_count, 8) / 8

        report.deobfuscation_score = max(0.0, min(1.0, score))
        report.details["switch_count"] = switch_count
        report.details["dispatcher_count"] = dispatcher_count
        report.details["pred_count"] = pred_count
        report.details["dead_count"] = dead_count
        report.details["mba_count"] = mba_count
        return report

    def analyze_obfuscated_ast(self, python_source: str) -> AnalysisReport:
        report = AnalysisReport(source=python_source)
        try:
            tree = ast.parse(python_source)
        except SyntaxError:
            report.details["error"] = "Syntax error in source"
            report.deobfuscation_score = 0.0
            return report

        opaque_count = 0
        dead_looking = 0
        mba_looking = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if self._is_opaque_predicate_ast(node):
                    opaque_count += 1
            elif isinstance(node, ast.BinOp):
                if isinstance(node.op, (ast.BitXor, ast.BitAnd, ast.LShift)):
                    mba_looking += 1
            elif isinstance(node, ast.Expr):
                if isinstance(node.value, ast.Constant):
                    dead_looking += 1
                elif isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                    if node.value.func.id in ('hashlib', 'sha256', 'md5'):
                        dead_looking += 1

        report.opaque_predicates_detected = opaque_count > 0
        report.opaque_predicate_count = opaque_count
        report.dead_code_blocks = dead_looking
        report.mba_patterns_detectable = mba_looking

        patterns = []
        if opaque_count > 0:
            patterns.append("opaque_predicates")
            report.opaque_predicates_detected = True
        if dead_looking > 2:
            patterns.append("dead_code_detectable")
        if mba_looking > 3:
            patterns.append("mba_patterns_detectable")
        report.detected_patterns = patterns

        score = 1.0
        if opaque_count > 0:
            score -= 0.25 * min(opaque_count, 6) / 6
        if dead_looking > 2:
            score += 0.1
        if mba_looking > 3:
            score -= 0.15 * min(mba_looking, 10) / 10

        report.deobfuscation_score = max(0.0, min(1.0, score))
        report.details["opaque_ast_count"] = opaque_count
        report.details["dead_looking_ast"] = dead_looking
        report.details["mba_looking_ast"] = mba_looking
        return report

    def _is_opaque_predicate_ast(self, if_node: ast.If) -> bool:
        if isinstance(if_node.test, ast.Compare):
            left = if_node.test.left
            if isinstance(left, ast.BinOp):
                return True
            if isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute):
                if left.func.attr in ('sha256', 'md5', 'sha1'):
                    return True
            if isinstance(if_node.test.ops[0], ast.Eq):
                for c in if_node.test.comparators:
                    if isinstance(c, ast.Constant) and isinstance(c.value, int):
                        if c.value in (0, 1) and self._is_complex_expr(left):
                            return True
        return False

    def _is_complex_expr(self, node: ast.AST, depth: int = 0) -> bool:
        if depth > 3:
            return True
        if isinstance(node, ast.BinOp):
            return self._is_complex_expr(node.left, depth + 1) or self._is_complex_expr(node.right, depth + 1)
        return isinstance(node, ast.Call)

    def simulate_deobfuscation(self, ir_path: str) -> Tuple[bool, str]:
        if not os.path.exists(ir_path):
            return False, "IR file not found"

        with open(ir_path, "rb") as f:
            raw = f.read()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = raw.decode("latin-1")

        simplified = content

        # Simplify constant expressions
        simplified = re.sub(
            r'%(\S+)\s*=\s*add\s+i\d+\s+(\d+),\s*(\d+)',
            lambda m: f'%{m.group(1)} = add i32 {int(m.group(2)) + int(m.group(3))}, 0',
            simplified
        )

        simplified = re.sub(
            r'%(\S+)\s*=\s*sub\s+i\d+\s+(\d+),\s*(\d+)',
            lambda m: f'%{m.group(1)} = sub i32 {int(m.group(2)) - int(m.group(3))}, 0',
            simplified
        )

        # Remove dead blocks (basic heuristic)
        lines = simplified.split("\n")
        cleaned = []
        skip_dead = False
        for line in lines:
            stripped = line.strip()
            if re.match(r'(dead|junk)_\w+\s*:', stripped):
                skip_dead = True
            if skip_dead:
                if stripped == '' or stripped.startswith(';'):
                    pass
                elif stripped.startswith('br label') or stripped.startswith('ret '):
                    skip_dead = False
                    continue
                elif re.match(r'%\w+\s*=', stripped):
                    continue
                elif skip_dead and not stripped.startswith(' '):
                    skip_dead = False
                else:
                    continue
            cleaned.append(line)

        original_ops = len(re.findall(r'=\s*(add|sub|mul|xor|and|or|shl)\s', content))
        cleaned_ops = len(re.findall(r'=\s*(add|sub|mul|xor|and|or|shl)\s', "\n".join(cleaned)))

        reduction = (original_ops - cleaned_ops) / max(original_ops, 1)
        success = reduction > 0.1 or reduction < 0
        return success, "\n".join(cleaned)

    def generate_feedback(self, report: AnalysisReport) -> dict:
        weaknesses = []
        recommendations = []

        if report.cfg_flattening_detected and report.details.get("switch_count", 0) < 4:
            weaknesses.append("cfg_flattening_too_few_cases")
            recommendations.append("increase_switch_cases")
            recommendations.append("add_random_dispatcher_blocks")

        if report.opaque_predicates_detected and report.opaque_predicate_count < 5:
            weaknesses.append("opaque_predicates_too_simple")
            recommendations.append("increase_predicate_nesting")
            recommendations.append("add_more_variables_to_predicates")

        if report.mba_patterns_detectable > 0:
            weaknesses.append("mba_patterns_detectable")
            recommendations.append("increase_mba_complexity")
            recommendations.append("increase_bit_width")

        if report.constant_folding_opportunities > 5:
            weaknesses.append("constant_folding_possible")
            recommendations.append("use_dynamic_values_in_expressions")

        if report.dead_code_blocks < 3 and report.deobfuscation_score < 0.8:
            weaknesses.append("insufficient_dead_code")
            recommendations.append("add_more_realistic_dead_code")

        if not weaknesses:
            recommendations.append("maintain_current_strength")

        self.feedback_history.append({
            "score": report.deobfuscation_score,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
        })

        return {
            "weaknesses": weaknesses,
            "recommendations": recommendations,
            "deobfuscation_score": report.deobfuscation_score,
            "detected_patterns": report.detected_patterns,
        }


if __name__ == "__main__":
    agent = DeobfuscationAgent({"seed": 0})
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        report = agent.analyze_obfuscated_ir(sys.argv[1])
        feedback = agent.generate_feedback(report)
        print(f"Score: {report.deobfuscation_score:.2f}")
        print(f"Weaknesses: {feedback['weaknesses']}")
        print(f"Recommendations: {feedback['recommendations']}")
