"""
__init__.py

Purpose:
Package initializer for the benchmark module. Exports the top-level
benchmarking classes used for AI-based protection evaluation.

Architectural Role:
Entry point for the benchmarking subsystem. Aggregates AIBenchmark
(static proxy metrics), LLMEvaluator (LLM-based deobfuscation
simulation), BenchmarkReport (HTML/text report generation), and
HybridBenchmark (hybrid human-AI reverse engineering model).

Dependencies:
.ai_eval, .llm_api, .report, .hybrid_bench

Security Relevance:
Benchmarking measures the effectiveness of protection passes and
drives adaptive rewriting via BenchmarkFeedbackAnalyzer.
"""

from .ai_eval import AIBenchmark
from .llm_api import LLMEvaluator
from .report import BenchmarkReport
from .hybrid_bench import HybridBenchmark

__all__ = ["AIBenchmark", "LLMEvaluator", "BenchmarkReport", "HybridBenchmark"]
