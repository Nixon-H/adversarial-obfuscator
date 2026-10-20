"""
feedback.py

Purpose:
Adaptive Adversarial Rewriting feedback analyzer. Consumes AIBenchmark
results and produces a WeaknessProfile identifying which metrics scored
below threshold, along with recommended remediation actions.

Architectural Role:
Feedback loop for the adaptive obfuscation pipeline. After benchmarking,
BenchmarkFeedbackAnalyzer.analyze() produces a WeaknessProfile that the
pipeline uses to select additional protection passes targeting the
identified weaknesses. Supports history persistence via save/load.

Dependencies:
json, os

Security Relevance:
Closes the benchmark → rewrite loop. Without feedback analysis, the
pipeline would apply the same protection stack regardless of measured
effectiveness. WeaknessProfile.recommended_actions directly drives
the adaptive mutation strategy.
"""

import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class WeaknessProfile:
    """
    Container for benchmark weakness analysis results.

    Attributes:
        failed_metrics: List of metric keys that scored below threshold.
        weak_scores: Dict mapping metric key to its numeric score.
        recommended_actions: List of pass names to strengthen.
    """

    def __init__(
        self,
        failed_metrics: list[str],
        weak_scores: dict[str, float],
        recommended_actions: list[str],
    ):
        """
        Initialize a WeaknessProfile with analysis results.

        Args:
            failed_metrics: Metric keys below threshold.
            weak_scores: Per-metric score map.
            recommended_actions: Actions to remediate weaknesses.
        """
        self.failed_metrics = failed_metrics
        self.weak_scores = weak_scores
        self.recommended_actions = recommended_actions

    def to_dict(self) -> dict:
        """Serialize the profile to a JSON-compatible dict."""
        return {
            "failed_metrics": self.failed_metrics,
            "weak_scores": self.weak_scores,
            "recommended_actions": self.recommended_actions,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WeaknessProfile":
        """Deserialize a profile from a dict (inverse of to_dict)."""
        return cls(
            failed_metrics=d.get("failed_metrics", []),
            weak_scores=d.get("weak_scores", {}),
            recommended_actions=d.get("recommended_actions", []),
        )


class BenchmarkFeedbackAnalyzer:
    """
    Analyzes AIBenchmark results and produces adaptive rewriting feedback.

    Compares each metric score against a configurable threshold (default 0.5).
    Metrics below threshold are flagged as weaknesses, and the _recommend
    method maps each weakness to specific remediation actions.
    """

    THRESHOLD = 0.5

    def __init__(self, threshold: float = THRESHOLD):
        """Initialize with a configurable score threshold."""
        self.threshold = threshold

    def analyze(self, results: dict) -> WeaknessProfile:
        """
        Analyze benchmark results and produce a weakness profile.

        For each metric in the results dict, compares the score against
        self.threshold. Metrics below threshold are recorded as failed,
        and _recommend() is invoked to generate remediation actions.
        """
        failed_metrics: list[str] = []
        weak_scores: dict[str, float] = {}

        for key in ["naming_recovery", "semantic_leakage", "decompilation_resistance",
                     "complexity_impact", "entropy", "static_confusion"]:
            if key in results and isinstance(results[key], dict):
                score = results[key].get("score", 0.0)
                weak_scores[key] = score
                if score < self.threshold:
                    failed_metrics.append(key)

        recommended_actions = self._recommend(failed_metrics, weak_scores)
        return WeaknessProfile(failed_metrics, weak_scores, recommended_actions)

    def _recommend(self, failed: list[str], scores: dict[str, float]) -> list[str]:
        """
        Map failed metrics to concrete remediation actions.

        Each weakness maps to one or more pass names that the pipeline
        should apply more aggressively. For example, weak naming_recovery
        maps to 'strengthen_symbol_renaming'.
        """
        actions: list[str] = []
        if "naming_recovery" in failed:
            actions.append("strengthen_symbol_renaming")
        if "decompilation_resistance" in failed:
            actions.append("add_opaque_predicates")
            actions.append("add_exec_eval_patterns")
        if "semantic_leakage" in failed:
            actions.append("add_junk_ast_patterns")
        if "static_confusion" in failed:
            actions.append("add_decoy_apis")
            actions.append("add_misleading_imports")
        if "complexity_impact" in failed:
            actions.append("increase_dispatch_fan_out")
        if "entropy" in failed:
            actions.append("add_string_encoding")
        return actions

    def save_history(self, profile: WeaknessProfile, history_path: str):
        """
        Append a weakness profile to a JSON history file.

        Creates parent directories if needed. Handles corrupt/missing
        history gracefully by starting fresh.
        """
        history: list = []
        if os.path.exists(history_path):
            try:
                with open(history_path) as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []
        history.append(profile.to_dict())
        os.makedirs(os.path.dirname(history_path), exist_ok=True)
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)

    def load_history(self, history_path: str) -> list[dict]:
        """Load the full weakness profile history from a JSON file."""
        if not os.path.exists(history_path):
            return []
        try:
            with open(history_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
