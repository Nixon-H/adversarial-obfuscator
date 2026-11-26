"""Control-plane gate for benchmark-derived adaptive rewriting.

The composite protection score is a diagnostic until it has been correlated
with independently measured recovery success on held-out artifacts. AI-RE-003
requires that this unvalidated number must not silently select protection
passes. This module centralises that gate so every adaptive control path uses
the same policy.
"""
MINIMUM_VALIDATION_SAMPLE_SIZE = 30
MINIMUM_SPEARMAN_RHO = 0.5

def validation_metadata(results):
    """Return the score-validation metadata block from a benchmark result."""
    if not isinstance(results, dict):
        return {}
    value = (results.get("score_validation")
             or results.get("validation")
             or results.get("protection_score_validation")
             or {})
    return value if isinstance(value, dict) else {}


def validated_for_control(results):
    """True only when the score has objective held-out recovery evidence.

    Acceptance criteria are deliberately strict and machine-readable:

    * ``validated`` is true;
    * ``method`` names held-out recovery correlation;
    * ``sample_size`` is at least 30 independent artifact/scenario pairs;
    * ``spearman_rho`` (or ``correlation``) is at least 0.5;
    * the lower confidence bound, when supplied, is positive.

    No current repository benchmark result satisfies these criteria. The score
    therefore remains a diagnostic, not a release or pass-selection gate.
    """
    meta = validation_metadata(results)
    if meta.get("validated") is not True:
        return False
    method = str(meta.get("method", "")).lower()
    if "held" not in method or "recovery" not in method:
        return False
    try:
        sample_size = int(meta.get("sample_size", 0))
    except (TypeError, ValueError):
        return False
    if sample_size < MINIMUM_VALIDATION_SAMPLE_SIZE:
        return False
    try:
        rho = float(meta.get("spearman_rho", meta.get("correlation", 0.0)))
    except (TypeError, ValueError):
        return False
    if rho < MINIMUM_SPEARMAN_RHO:
        return False
    if "ci_lower" in meta:
        try:
            if float(meta.get("ci_lower")) <= 0.0:
                return False
        except (TypeError, ValueError):
            return False
    return True


def control_permitted(results):
    """Return ``(permitted, reason)`` for benchmark-driven pass selection."""
    if validated_for_control(results):
        return True, "validated held-out recovery correlation"
    return False, ("benchmark score is unvalidated for pass selection; "
                   "use it as a diagnostic until held-out validation exists")
