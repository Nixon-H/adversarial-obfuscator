"""Clock-interrupt-bias detector tests (V10 REAL side-channel signal).

Covers the Python counterpart (obfuscator/clock_bias.py), parity with the
Rust implementation in runtime/src/timing.rs on shared synthetic vectors,
the emitted loader fragment (3.10-parseable, stdlib-only, no match), and
the vm_score wiring (clock_bias weight 10 alongside timing, default ON).
All vectors are deterministic -- no sleeps, no wall-clock sampling in
assertions (except a structural smoke of clock_bias_check with a fake
timer and a tiny live sample).
"""

import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator import clock_bias as cb
from obfuscator.clock_bias import (
    CLOCK_BIAS_SAMPLES,
    CLOCK_BIAS_TAIL_FRAC_THRESHOLD,
    CLOCK_BIAS_P99_RATIO_THRESHOLD,
    CLOCK_BIAS_TAIL_FACTOR,
    CLOCK_BIAS_WEIGHT,
    SIGNAL_NAME,
    clock_bias_check,
    clock_bias_stats,
    clock_bias_verdict,
    loader_snippet_fragment,
)
from obfuscator.vm_score import SIGNALS, _SUBSET_WEIGHTS, emit_loader_snippet


def _clean(n=2000):
    return [95 + (i % 11) for i in range(n)]


def _vm_like(n=2000):
    # ~2% periodic outliers at ~200x the median (see timing.rs:
    # p99 rank needs >1% outliers to land on an outlier).
    return [20000 if i % 50 == 0 else 95 + (i % 11) for i in range(n)]


def test_constants_mirror_rust():
    assert SIGNAL_NAME == "clock_bias"
    assert CLOCK_BIAS_WEIGHT == 10
    assert CLOCK_BIAS_SAMPLES == 2000
    assert CLOCK_BIAS_P99_RATIO_THRESHOLD == 50.0
    assert CLOCK_BIAS_TAIL_FACTOR == 10
    assert CLOCK_BIAS_TAIL_FRAC_THRESHOLD == 0.005


def test_thresholds_serialized_into_snippet():
    # Emitted _nx_has_clock_bias carries literal threshold copies;
    # this test fails if they drift from the module constants.
    from obfuscator import clock_bias as _cb
    src = _cb.loader_snippet_fragment()
    assert "_samples=%r" % CLOCK_BIAS_SAMPLES in src
    assert "%r" % CLOCK_BIAS_P99_RATIO_THRESHOLD in src
    assert "%r" % CLOCK_BIAS_TAIL_FACTOR in src
    assert "%r" % CLOCK_BIAS_TAIL_FRAC_THRESHOLD in src


def test_clean_no_flag():
    flagged, stats = clock_bias_verdict(_clean())
    assert flagged is False
    assert stats["samples"] == 2000
    assert stats["median_ns"] > 0
    assert stats["tail_frac"] <= CLOCK_BIAS_TAIL_FRAC_THRESHOLD


def test_vm_like_flags():
    flagged, stats = clock_bias_verdict(_vm_like())
    assert abs(stats["tail_frac"] - 0.02) < 1e-9
    assert stats["p99_ns"] / stats["median_ns"] > 50.0
    assert flagged is True


def test_single_spike_no_flag():
    d = _clean()
    d[777] = 1_000_000
    flagged, stats = clock_bias_verdict(d)
    assert flagged is False  # one-off noise moves neither p99 nor tail frac
    assert stats["tail_frac"] < CLOCK_BIAS_TAIL_FRAC_THRESHOLD


def test_noisy_unimodal_no_flag():
    d = [100 + (i * 37 % 200) for i in range(2000)]
    flagged, stats = clock_bias_verdict(d)
    assert flagged is False
    assert stats["tail_frac"] == 0.0  # max 3x median, tail rule empty


def test_empty_and_degenerate_never_flag():
    flagged, stats = clock_bias_verdict([])
    assert flagged is False
    assert stats["samples"] == 0
    flagged, stats = clock_bias_verdict([0] * 64)
    assert flagged is False
    assert stats["median_ns"] == 0
    flagged, _ = clock_bias_verdict(None)
    assert flagged is False


def test_stats_median_p99_units():
    stats = clock_bias_stats(list(range(1, 101)))
    assert stats["median_ns"] == 50  # even n: (50+51)//2
    assert stats["p99_ns"] == 99
    assert stats["samples"] == 100
    assert stats["tail_frac"] == 0.0


def test_parity_vectors_shared_with_rust():
    # Same verdicts the Rust unit tests assert in timing.rs.
    cases = [
        (_clean(), False),
        (_vm_like(), True),
    ]
    d = _clean()
    d[777] = 1_000_000
    cases.append((d, False))
    noisy = [100 + (i * 37 % 200) for i in range(2000)]
    cases.append((noisy, False))
    for vec, expected in cases:
        flagged, _ = clock_bias_verdict(vec)
        assert flagged is expected


def test_check_with_fake_timer():
    ticks = iter(range(0, 10_000_000, 100))

    def fake():
        return next(ticks)

    flagged, stats = clock_bias_check(samples=64, timer=fake)
    assert flagged is False
    assert stats["samples"] == 64
    assert stats["median_ns"] == 100
    # samples<=0 falls back to default count (fake timer must cover it).
    ticks2 = iter(range(0, (CLOCK_BIAS_SAMPLES + 8) * 100, 100))
    flagged2, stats2 = clock_bias_check(samples=0, timer=lambda: next(ticks2))
    assert stats2["samples"] == CLOCK_BIAS_SAMPLES
    assert flagged2 is False


def test_check_bad_samples_falls_back():
    ticks = iter(range(0, (CLOCK_BIAS_SAMPLES + 8) * 50, 50))
    _, stats = clock_bias_check(samples="bogus", timer=lambda: next(ticks))
    assert stats["samples"] == CLOCK_BIAS_SAMPLES


def test_live_check_structural_only():
    flagged, stats = clock_bias_check(samples=64)
    assert stats["samples"] == 64
    assert isinstance(flagged, bool)


def test_loader_fragment_parses_310_and_verdicts():
    src = loader_snippet_fragment()
    compile(src, "<t>", "exec")
    ast.parse(src, feature_version=(3, 10))
    assert "match " not in src
    ns = {"_time": __import__("time")}
    exec(compile(src, "<t>", "exec"), ns)
    f = ns["_nx_has_clock_bias"]
    assert f(_deltas=_clean()) is False
    assert f(_deltas=_vm_like()) is True
    d = _clean()
    d[5] = 5_000_000
    assert f(_deltas=d) is False
    assert f(_deltas=[]) is False
    assert f(_deltas=[0] * 32) is False
    assert f(_deltas=None, _samples=8) in (True, False)  # live path: no crash


def test_loader_fragment_never_raises():
    src = loader_snippet_fragment()
    ns = {"_time": __import__("time")}
    exec(compile(src, "<t>", "exec"), ns)
    f = ns["_nx_has_clock_bias"]

    def boom():
        raise OSError("no clock")

    assert f(_timer=boom, _samples=16) is False
    assert f(_deltas="not-a-list") is False


def test_vm_score_wiring_clock_bias_additive():
    d = dict(SIGNALS)
    # New signal present at the timing-family weight; existing weights
    # unchanged (explicit allowlist -- this test is the deliberate
    # weight-sync update for the additive clock_bias signal).
    assert d["clock_bias"] == 10
    assert d["timing"] == 10
    for name, w in (("cpuid_hypervisor", 25), ("vm_processes", 25),
                    ("registry_keys", 20), ("mac_prefix", 20),
                    ("wmi_bios", 20), ("drivers", 20),
                    ("fs_artifacts", 15), ("net_adapters", 15),
                    ("services", 15), ("timing", 10),
                    ("sysinfo", 10), ("hw_constraints", 10),
                    ("dmi_strings", 20)):
        assert d[name] == w, name
    # Build-time total grows additively 225 -> 235.
    assert sum(w for _, w in SIGNALS) == 235
    # Subset mirrors SIGNALS for clock_bias and stays loader-wired.
    assert _SUBSET_WEIGHTS["clock_bias"] == 10
    assert sum(_SUBSET_WEIGHTS.values()) == 195


def test_snippet_wires_clock_bias_default_on():
    src = emit_loader_snippet()
    compile(src, "<t>", "exec")
    ast.parse(src, feature_version=(3, 10))
    assert "match " not in src
    ns = {}
    exec(compile(src, "<t>", "exec"), ns)
    assert ns["_NX_VM_WEIGHTS"] == _SUBSET_WEIGHTS
    assert ns["_NX_VM_WEIGHTS"]["clock_bias"] == 10
    assert callable(ns["_nx_has_clock_bias"])
    # vm_check + vm_score_percent consult clock_bias (default ON).
    assert src.count('"clock_bias"') >= 2
    assert "_nx_has_clock_bias()" in src
    # Deterministic hook: force the bias signal and check scoring math.
    findings_hit = {n: False for n, _ in SIGNALS}
    findings_hit["clock_bias"] = True
    from obfuscator.vm_score import score
    hit, total, pct = score(findings_hit)
    assert (hit, total) == (10, 235)
    assert abs(pct - 10 / 235 * 100) < 1e-9
