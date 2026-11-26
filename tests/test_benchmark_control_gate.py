"""Regression tests for AI-RE-003 benchmark-score control gating."""
from scripts.benchmark.score_control import control_permitted, validated_for_control


def _validated_result(**overrides):
    meta = {
        "validated": True,
        "method": "held-out recovery correlation",
        "sample_size": 30,
        "spearman_rho": 0.5,
        "ci_lower": 0.1,
    }
    meta.update(overrides)
    return {"score_validation": meta}


def test_unvalidated_benchmark_score_cannot_drive_pass_selection():
    permitted, reason = control_permitted({"overall_score": 0.99})
    assert not permitted
    assert "unvalidated" in reason
    assert not validated_for_control({"overall_score": 0.99})


def test_no_unvalidated_override_escape_hatch_exists():
    source = open("scripts/benchmark/score_control.py", encoding="utf-8").read()
    assert "NIXON_ALLOW_UNVALIDATED" not in source
    assert "os.environ" not in source


def test_held_out_validation_metadata_allows_control():
    permitted, reason = control_permitted(_validated_result())
    assert permitted
    assert "validated" in reason


def test_weak_or_small_validation_does_not_allow_control():
    for kwargs in (
        {"sample_size": 29},
        {"spearman_rho": 0.49},
        {"ci_lower": 0.0},
        {"validated": False},
        {"method": "in-sample recovery correlation"},
    ):
        permitted, _reason = control_permitted(_validated_result(**kwargs))
        assert not permitted, kwargs


def test_adaptive_control_paths_use_the_gate():
    build_src = open("scripts/build.py", encoding="utf-8").read()
    phase_src = open("scripts/phases/phase07_phase2.py", encoding="utf-8").read()
    assert build_src.count("control_permitted(") >= 2  # two adaptive call sites
    assert "Adaptive rewrite disabled" in build_src
    assert "Adaptive adversarial rewrite disabled" in build_src
    assert "control_permitted(results)" in phase_src
    assert "Adaptive rewrite disabled" in phase_src
