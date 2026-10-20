"""
comparator.py

Purpose:
Provides fuzzy comparison of attack results between original and
replayed executions. Supports numerical, string, list, and dict
comparisons with configurable tolerance.

Architectural Role:
Comparison layer for the attack replay framework. compare_results()
compares two result dicts and returns match status, similarity score,
and detailed deltas. Used by AttackReplay to quantify how much
attack results have changed.

Execution Context:
Called by AttackReplay.replay() after both original and replayed
results are available. The comparison result is stored in the
ReplayResult and fed to AttackHistory for trend analysis.

Dependencies:
- Standard library (difflib, math, typing)

Security Relevance:
Fuzzy comparison is essential because attack results are inherently
non-deterministic (ASLR, schedule, timing). The tolerance parameter
allows acceptable variation while still catching true regressions.

Maintenance Notes:
- Numeric comparison uses relative difference (diff / max(|a|, |b|))
  to handle values of different magnitudes.
- String comparison uses difflib.SequenceMatcher ratio for
  approximate matching.
- Dict comparison checks both key presence and value similarity;
  missing keys in either dict are treated as total mismatches.
"""

import difflib
import math  # noqa: F401 (this line binds a name used by an embedded template)
from typing import Any, Dict, List, Tuple, Union


NumericKey = Union[int, float]


def fuzzy_match(value_a: Any, value_b: Any, tolerance: float = 0.1) -> bool:
    if type(value_a) != type(value_b):
        return False
    if isinstance(value_a, (int, float)):
        if value_a == value_b:
            return True
        if value_a == 0 and value_b == 0:
            return True
        if value_a == 0 or value_b == 0:
            return abs(value_a - value_b) < tolerance
        diff = abs(value_a - value_b) / max(abs(value_a), abs(value_b))
        return diff <= tolerance
    if isinstance(value_a, bool):
        return value_a == value_b
    if isinstance(value_a, str):
        ratio = difflib.SequenceMatcher(None, value_a, value_b).ratio()
        return ratio >= (1.0 - tolerance)
    if isinstance(value_a, (list, tuple)):
        if len(value_a) != len(value_b):
            return False
        return all(fuzzy_match(a, b, tolerance) for a, b in zip(value_a, value_b))
    if isinstance(value_a, dict):
        return _dicts_match(value_a, value_b, tolerance)
    return value_a == value_b


def _dicts_match(a: Dict, b: Dict, tolerance: float) -> bool:
    if set(a.keys()) != set(b.keys()):
        return False
    for k in a:
        if not fuzzy_match(a[k], b[k], tolerance):
            return False
    return True


def _numeric_diff(a: NumericKey, b: NumericKey) -> float:
    if a == b:
        return 0.0
    denom = max(abs(a), abs(b))
    if denom == 0:
        return float(abs(a - b))
    return abs(a - b) / denom


def _compare_values(
    key: str,
    original: Any,
    replayed: Any,
    tolerance: float = 0.1,
) -> Tuple[bool, float, Dict[str, Any]]:
    if type(original) != type(replayed):
        return False, 0.0, {key: {"type_mismatch": f"{type(original).__name__} vs {type(replayed).__name__}"}}

    if isinstance(original, (int, float)):
        diff = _numeric_diff(original, replayed)
        match = diff <= tolerance
        return match, 1.0 - diff, {key: {"original": original, "replayed": replayed, "diff": diff}}

    if isinstance(original, bool):
        match = original == replayed
        return match, 1.0 if match else 0.0, {key: {"original": original, "replayed": replayed, "diff": 0 if match else 1}}

    if isinstance(original, str):
        ratio = difflib.SequenceMatcher(None, original, replayed).ratio()
        match = ratio >= (1.0 - tolerance)
        return match, ratio, {key: {"original": original, "replayed": replayed, "similarity": ratio}}

    if isinstance(original, list):
        if len(original) != len(replayed):
            return False, 0.0, {key: {"length_mismatch": f"{len(original)} vs {len(replayed)}"}}
        elem_matches = []
        for i, (a, b) in enumerate(zip(original, replayed)):
            em, es, _ = _compare_values(f"{key}[{i}]", a, b, tolerance)
            elem_matches.append(es)
        avg_sim = sum(elem_matches) / max(len(elem_matches), 1)
        all_match = all(
            fuzzy_match(a, b, tolerance) for a, b in zip(original, replayed)
        )
        return all_match, avg_sim, {key: {"element_similarities": elem_matches}}

    if isinstance(original, dict):
        all_keys = set(original.keys()) | set(replayed.keys())
        diffs = {}
        matches = []
        for k in all_keys:
            if k not in original:
                diffs[k] = {"added": replayed[k]}
                matches.append(0.0)
            elif k not in replayed:
                diffs[k] = {"removed": original[k]}
                matches.append(0.0)
            else:
                dm, ds, dd = _compare_values(k, original[k], replayed[k], tolerance)
                matches.append(ds)
                if not dm:
                    diffs.update(dd)
        avg_sim = sum(matches) / max(len(matches), 1)
        all_match = avg_sim >= (1.0 - tolerance)
        return all_match, avg_sim, diffs

    return original == replayed, 1.0 if original == replayed else 0.0, {}


def compare_results(
    original: Dict[str, Any],
    replayed: Dict[str, Any],
    tolerance: float = 0.1,
) -> Tuple[bool, float, List[Dict[str, Any]]]:
    if not isinstance(original, dict) or not isinstance(replayed, dict):
        return original == replayed, 1.0 if original == replayed else 0.0, []

    all_keys = set(original.keys()) | set(replayed.keys())
    similarities = []
    deltas = []

    for key in all_keys:
        if key not in original:
            deltas.append({key: {"status": "missing_in_original"}})
            similarities.append(0.0)
        elif key not in replayed:
            deltas.append({key: {"status": "missing_in_replayed"}})
            similarities.append(0.0)
        else:
            match, sim, diff = _compare_values(key, original[key], replayed[key], tolerance)
            similarities.append(sim)
            if not match:
                deltas.append(diff)

    overall_similarity = sum(similarities) / max(len(similarities), 1)
    overall_match = overall_similarity >= (1.0 - tolerance)

    return overall_match, overall_similarity, deltas


def compare_reports(
    report_a: Dict[str, Any],
    report_b: Dict[str, Any],
    tolerance: float = 0.1,
) -> Dict[str, Any]:
    match, similarity, deltas = compare_results(report_a, report_b, tolerance)
    return {
        "match": match,
        "similarity_score": similarity,
        "deltas": deltas,
        "report_a_keys": list(report_a.keys()),
        "report_b_keys": list(report_b.keys()),
    }
