"""
feature_effectiveness/scorer.py

Purpose:
Evaluates how effectively each security feature demonstrates its impact.
Scores are based on three criteria:
1. Impact metric — does the feature compute a measurable score?
2. Before/after comparison — does it show improvement over a baseline?
3. Resistance benchmark — does it include adversarial/benchmark tests?

Architectural Role:
Used by the meta-assurance pipeline to produce a feature effectiveness score
(F193) consumed by the protection ROI engine (F194).

Security Relevance:
Features that cannot demonstrate measurable impact or resistance to attacks
may provide only cosmetic protection. Low-scoring features are candidates for
removal or redesign.
"""
from __future__ import annotations

import ast
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)


@dataclass
class FeatureEffectiveness:
    """
    FeatureEffectiveness

    Purpose:
    Stores the effectiveness assessment for a single feature, including
    its scores across three dimensions and the overall score.

    Lifecycle:
    Created by _score_feature(); aggregated in compute_feature_effectiveness().
    """
    feature_name: str
    file_path: str
    has_impact_metric: bool
    has_before_after: bool
    has_resistance_benchmark: bool
    docstring_purpose: str
    tests_found: list[str]
    benchmarks_found: list[str]
    impact_metric_score: float
    before_after_score: float
    resistance_score: float
    overall_score: float


# Regex patterns for identifying impact metrics, before/after comparisons,
# and resistance benchmarks in feature source code and tests.
PURPOSE_PATTERNS = [
    r"(?:Detect|Scan|Analyze|Compute|Track|Measure|Generate|Validate|Verify|Enforce|Protect|Secure|Obfuscate|Encrypt|Monitor|Audit|Check|Test|Evaluate|Assess|Calculate)\s+\w+",
    r"(?:Feature|Item|Phase|Function|Class|Module)\s+\d+.*",
    r"feature\s+\d+[:\s].*",
    r"protection\s+against\s+\w+",
    r"resists?\s+\d+%",
    r"improves?\s+\w+\s+by\s+\d+%",
    r"reduces?\s+\w+\s+by\s+\d+%",
]

BEFORE_AFTER_PATTERNS = [
    r"before.*after",
    r"original.*obfuscated",
    r"baseline.*comparison",
    r"improvement",
    r"reduction",
    r"increase.*%",
    r"decrease.*%",
]

RESISTANCE_BENCHMARK_PATTERNS = [
    r"resist.*\d+%",
    r"benchmark.*attack",
    r"adversarial.*bench",
    r"survivability",
    r"resilience.*score",
    r"bench_\w+",
    r"pytest.*benchmark",
    r"benchmark_metric",
]


class FeatureEffectivenessScorer:
    """
    FeatureEffectivenessScorer

    Purpose:
    Discovers features from the scripts/ tree, evaluates each against
    impact, before/after, and resistance criteria, and produces per-feature
    and overall effectiveness scores.

    Lifecycle:
    Created on demand; compute_feature_effectiveness() drives the analysis.
    """
    def __init__(self, scripts_dir: str | None = None, tests_dir: str | None = None):
        self.scripts_dir = scripts_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
        )
        self.tests_dir = tests_dir or os.path.join(
            os.path.dirname(self.scripts_dir), "tests"
        )

    def compute_feature_effectiveness(self) -> dict[str, Any]:
        """
        compute_feature_effectiveness

        Purpose:
        Main entry point — discovers features, scores each, and returns a
        report with per-feature scores, overall score, and low-impact features.

        Inputs:
        None

        Outputs:
        Dict with per_feature_scores, overall_score, low_impact_features,
        total_features.
        """
        features = self._discover_features()
        scores = []
        for feat in features:
            score = self._score_feature(feat)
            scores.append(score)

        overall_score = round(
            sum(s.overall_score for s in scores) / max(len(scores), 1), 2
        )
        low_impact = [
            s.feature_name for s in scores if s.overall_score < 30.0
        ]

        return {
            "per_feature_scores": [
                {
                    "feature_name": s.feature_name,
                    "file_path": s.file_path,
                    "docstring_purpose": s.docstring_purpose,
                    "has_impact_metric": s.has_impact_metric,
                    "has_before_after_comparison": s.has_before_after,
                    "has_resistance_benchmark": s.has_resistance_benchmark,
                    "impact_metric_score": s.impact_metric_score,
                    "before_after_score": s.before_after_score,
                    "resistance_score": s.resistance_score,
                    "overall_score": s.overall_score,
                    "tests_found": s.tests_found,
                    "benchmarks_found": s.benchmarks_found,
                }
                for s in scores
            ],
            "overall_score": overall_score,
            "low_impact_features": low_impact,
            "total_features": len(scores),
        }

    def _discover_features(self) -> list[dict[str, Any]]:
        """
        _discover_features

        Purpose:
        Discovers features by listing subdirectories under scripts/ and
        scanning their .py files, plus any phase files under scripts/phases/.

        Inputs:
        None

        Outputs:
        List of dicts with feature_name, package, file_path, docstring_purpose.
        """
        features: list[dict[str, Any]] = []
        seen_names: set[str] = set()

        # Discover from scripts subdirectories (feature packages)
        for name in os.listdir(self.scripts_dir):
            pkg_dir = os.path.join(self.scripts_dir, name)
            if not os.path.isdir(pkg_dir) or name.startswith("__") or name in ("phases", "build.py"):
                continue
            for fname in os.listdir(pkg_dir):
                if not fname.endswith(".py") or fname.startswith("__"):
                    continue
                fpath = os.path.join(pkg_dir, fname)
                purpose = self._extract_purpose(fpath)
                fname_clean = fname.replace(".py", "")
                if fname_clean not in seen_names:
                    seen_names.add(fname_clean)
                    features.append({
                        "feature_name": fname_clean,
                        "package": name,
                        "file_path": fpath,
                        "docstring_purpose": purpose,
                    })

        # Also discover phase files
        phases_dir = os.path.join(self.scripts_dir, "phases")
        if os.path.isdir(phases_dir):
            for fname in sorted(os.listdir(phases_dir)):
                if not fname.endswith(".py") or fname.startswith("__"):
                    continue
                fpath = os.path.join(phases_dir, fname)
                purpose = self._extract_purpose(fpath)
                fname_clean = fname.replace(".py", "")
                if fname_clean not in seen_names:
                    seen_names.add(fname_clean)
                    features.append({
                        "feature_name": fname_clean,
                        "package": "phases",
                        "file_path": fpath,
                        "docstring_purpose": purpose,
                    })

        return features

    def _extract_purpose(self, file_path: str) -> str:
        """
        _extract_purpose

        Purpose:
        Extracts the first line of the docstring from a Python file's module,
        class, or function definition.

        Inputs:
        file_path — absolute path to the .py file

        Outputs:
        First line of the docstring, or empty string.
        """
        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                source = f.read()
            tree = ast.parse(source, filename=file_path)
        except (SyntaxError, OSError):
            return ""

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                doc = ast.get_docstring(node)
                if doc:
                    first_line = doc.strip().split("\n")[0]
                    return first_line[:200]
        return ""

    def _score_feature(self, feature: dict[str, Any]) -> FeatureEffectiveness:
        """
        _score_feature

        Purpose:
        Scores a single feature by checking its source, tests, and benchmarks
        for impact metrics, before/after comparisons, and resistance benchmarks.

        Inputs:
        feature — dict with feature_name, file_path, docstring_purpose

        Outputs:
        FeatureEffectiveness dataclass with all scores.
        """
        name = feature["feature_name"]
        fpath = feature["file_path"]
        purpose = feature["docstring_purpose"]

        tests = self._find_tests(name)
        benchmarks = self._find_benchmarks(name)

        source_text = self._read_file(fpath)
        has_impact = self._check_impact_metric(source_text)
        has_before_after = self._check_before_after(source_text, tests + benchmarks)
        has_resistance = self._check_resistance_benchmark(source_text, benchmarks)

        impact_score = 40.0 if has_impact else 0.0
        before_after_score = 30.0 if has_before_after else 0.0
        resistance_score = 30.0 if has_resistance else 0.0

        for test_path in tests:
            test_text = self._read_file(test_path)
            if not has_impact and self._check_impact_metric(test_text):
                has_impact = True
                impact_score = 40.0
            if not has_before_after and self._check_before_after(test_text, []):
                has_before_after = True
                before_after_score = 30.0

        for bench_path in benchmarks:
            bench_text = self._read_file(bench_path)
            if not has_resistance and self._check_resistance_benchmark(bench_text, []):
                has_resistance = True
                resistance_score = 30.0
            if not has_impact and self._check_impact_metric(bench_text):
                has_impact = True
                impact_score = 40.0

        overall = round(impact_score + before_after_score + resistance_score, 2)

        return FeatureEffectiveness(
            feature_name=name,
            file_path=fpath,
            has_impact_metric=has_impact,
            has_before_after=has_before_after,
            has_resistance_benchmark=has_resistance,
            docstring_purpose=purpose,
            tests_found=tests,
            benchmarks_found=benchmarks,
            impact_metric_score=impact_score,
            before_after_score=before_after_score,
            resistance_score=resistance_score,
            overall_score=overall,
        )

    def _find_tests(self, feature_name: str) -> list[str]:
        """
        _find_tests

        Purpose:
        Finds test files matching a feature name in the tests/ directory.

        Inputs:
        feature_name — the feature name to match

        Outputs:
        List of test file paths.
        """
        tests: list[str] = []
        if not os.path.isdir(self.tests_dir):
            return tests
        for fname in os.listdir(self.tests_dir):
            if not fname.endswith(".py"):
                continue
            if feature_name.replace("phase_", "") in fname or feature_name in fname:
                if fname.startswith("test_"):
                    tests.append(os.path.join(self.tests_dir, fname))
        return tests

    def _find_benchmarks(self, feature_name: str) -> list[str]:
        """
        _find_benchmarks

        Purpose:
        Finds benchmark files matching a feature name in the tests/ directory.

        Inputs:
        feature_name — the feature name to match

        Outputs:
        List of benchmark file paths.
        """
        benches: list[str] = []
        if not os.path.isdir(self.tests_dir):
            return benches
        for fname in os.listdir(self.tests_dir):
            if not fname.endswith(".py"):
                continue
            if feature_name.replace("phase_", "") in fname or feature_name in fname:
                if fname.startswith("bench_"):
                    benches.append(os.path.join(self.tests_dir, fname))
        return benches

    def _read_file(self, path: str) -> str:
        """
        _read_file

        Purpose:
        Reads a file's contents, handling encoding errors gracefully.

        Inputs:
        path — absolute path to the file

        Outputs:
        File contents as a string, or empty string on error.
        """
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError:
            return ""

    def _check_impact_metric(self, text: str) -> bool:
        """
        _check_impact_metric

        Purpose:
        Checks whether text contains keywords indicating an impact metric
        (score, metric, effectiveness, resilience, etc.).

        Inputs:
        text — file content to search

        Outputs:
        True if an impact metric pattern is found.
        """
        if not text:
            return False
        patterns = [
            r"score",
            r"metric",
            r"measure",
            r"compute_.*score",
            r"overall.*score",
            r"resilience.*\d",
            r"effectiveness",
            r"impact.*score",
            r"security.*score",
            r"protection.*score",
            r"efficacy",
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    def _check_before_after(self, text: str, extra_texts: list[str]) -> bool:
        """
        _check_before_after

        Purpose:
        Checks whether text or extra texts contain before/after comparison
        keywords (improvement, reduction, baseline, etc.).

        Inputs:
        text — primary file content
        extra_texts — additional file paths to search

        Outputs:
        True if a before/after pattern is found.
        """
        combined = text + " ".join(self._read_file(t) for t in extra_texts)
        if not combined:
            return False
        return any(re.search(p, combined, re.IGNORECASE) for p in BEFORE_AFTER_PATTERNS)

    def _check_resistance_benchmark(self, text: str, extra_texts: list[str]) -> bool:
        """
        _check_resistance_benchmark

        Purpose:
        Checks whether text or extra texts contain resistance/benchmark
        keywords (resist, adversarial, survivability, benchmark).

        Inputs:
        text — primary file content
        extra_texts — additional file paths to search

        Outputs:
        True if a resistance benchmark pattern is found.
        """
        combined = text + " ".join(self._read_file(t) for t in extra_texts)
        if not combined:
            return False
        return any(re.search(p, combined, re.IGNORECASE) for p in RESISTANCE_BENCHMARK_PATTERNS)
