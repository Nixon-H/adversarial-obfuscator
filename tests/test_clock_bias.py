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
import time

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


# ---- wall-clock end-to-end (live timers, structural assertions only) ----


def test_live_timer_structural():
    # REAL perf_counter_ns run: proves the live sampling pipeline works on
    # a live timer without false-positives-by-assertion. Verdict is
    # host-dependent (noisy CI/scheduler can skew it), so assert only
    # STRUCTURAL properties of the returned stats plus a runtime bound.
    t0 = time.monotonic()
    flagged, stats = clock_bias_check(samples=2000)
    dt = time.monotonic() - t0
    assert isinstance(flagged, bool)  # verdict type only, never its value
    assert stats["samples"] == 2000
    assert stats["median_ns"] > 0
    assert stats["p99_ns"] >= stats["median_ns"]
    assert 0.0 <= stats["tail_frac"] <= 1.0
    assert dt < 30.0


def test_live_no_false_positive_on_clean_host():
    # Record 2000 REAL deltas once, then replay the same vector through
    # clock_bias_verdict twice: proves the live-timer -> verdict pipeline
    # operates on real data while staying deterministic (no second live
    # run to go flaky, no verdict-value assertion).
    tick = time.perf_counter_ns
    prev = tick()
    deltas = []
    for _ in range(2000):
        now = tick()
        deltas.append(now - prev)
        prev = now
    assert len(deltas) == 2000
    flagged1, stats1 = clock_bias_verdict(deltas)
    flagged2, stats2 = clock_bias_verdict(list(deltas))
    assert isinstance(flagged1, bool)
    assert flagged1 is flagged2  # deterministic replay of real data
    assert stats1 == stats2
    assert stats1["samples"] == 2000
    assert stats1["median_ns"] > 0
    assert stats1["p99_ns"] >= stats1["median_ns"]
    assert 0.0 <= stats1["tail_frac"] <= 1.0


# ---- clock edge battery (timer-injectable seams, deterministic) ----


def _ticks_from_deltas(deltas, start=1_000_000_000):
    ticks = [start]
    for d in deltas:
        ticks.append(ticks[-1] + d)
    it = iter(ticks)
    return lambda: next(it)


def test_normal_drift_no_flag():
    # Monotonic ~100ns deltas: the healthy-metal shape. No flag.
    flagged, stats = clock_bias_verdict([95 + (i % 11) for i in range(2000)])
    assert flagged is False
    assert stats["median_ns"] > 0
    assert stats["tail_frac"] <= CLOCK_BIAS_TAIL_FRAC_THRESHOLD


def test_extreme_but_uniform_drift_no_flag():
    # Uniformity is the key property: ALL deltas huge but identical means
    # no tail at all (p99/median == 1), so no flag despite the magnitude.
    flagged, stats = clock_bias_verdict([10_000_000] * 2000)
    assert flagged is False
    assert stats["p99_ns"] == stats["median_ns"]
    assert stats["tail_frac"] == 0.0


def test_backwards_jumps_no_crash():
    # Negative deltas (clock stepped backwards mid-vector): must not crash
    # and must yield a sane verdict. Alternating +/- drives the median to
    # <= 0, which never flags by rule.
    flagged, stats = clock_bias_verdict([100, -100] * 1000)
    assert isinstance(flagged, bool)
    assert flagged is False
    assert stats["samples"] == 2000


def test_single_discontinuity_no_flag():
    # One step-change mid-vector (100ns half, 10us half): bimodal but not
    # a *tail* — p99/median ~2x, far below the 50x bar. Documents that a
    # lone regime shift is not virtualization evidence.
    vec = [100] * 1000 + [10000] * 1000
    flagged, stats = clock_bias_verdict(vec)
    assert flagged is False
    assert stats["p99_ns"] / stats["median_ns"] < 50.0


def test_same_vector_both_timer_paths_agree():
    # Same delta vector through the pure verdict path AND the injected-timer
    # sampling path: verdicts and stats must agree exactly.
    vec = _clean()
    flagged_v, stats_v = clock_bias_verdict(vec)
    flagged_c, stats_c = clock_bias_check(
        samples=len(vec), timer=_ticks_from_deltas(vec))
    assert flagged_c is flagged_v
    assert stats_c == stats_v


def test_scheduler_delay_single_fat_outlier_no_flag():
    # One fat outlier among clean samples: proves single-spike immunity
    # (p99 rank needs >1% outliers at N=2000; tail fraction stays ~0.05%).
    d = _clean()
    d[0] = 50_000_000
    flagged, stats = clock_bias_verdict(d)
    assert flagged is False
    assert stats["tail_frac"] < CLOCK_BIAS_TAIL_FRAC_THRESHOLD


def test_virtualization_artifact_periodic_fat_tail_flags():
    # Periodic fat tail (~2% of samples at ~200x median, via timer path):
    # BOTH conditions hold -> flag. Same shape as _vm_like, exercised
    # through the injectable timer seam instead of the verdict seam.
    vec = [20000 if i % 50 == 0 else 95 + (i % 11) for i in range(2000)]
    flagged, stats = clock_bias_check(
        samples=len(vec), timer=_ticks_from_deltas(vec))
    assert flagged is True
    assert stats["tail_frac"] > CLOCK_BIAS_TAIL_FRAC_THRESHOLD
    assert stats["p99_ns"] / stats["median_ns"] > 50.0


def test_integer_overflow_scale_deltas_no_crash():
    # Deltas near 2**63 (counter-width edge): uniform, so no flag; Python
    # bigints must not overflow and the loader mirror must agree.
    vec = [(2 ** 63 - 1) - (i % 7) for i in range(2000)]
    flagged, stats = clock_bias_verdict(vec)
    assert isinstance(flagged, bool)
    assert flagged is False
    assert stats["median_ns"] > 0
    src = loader_snippet_fragment()
    ns = {"_time": __import__("time")}
    exec(compile(src, "<t>", "exec"), ns)
    assert ns["_nx_has_clock_bias"](_deltas=vec) is False


def test_zero_timer_constant_never_flags():
    # Degenerate timer (constant ticks -> all-zero deltas -> median 0):
    # verdict False, never a crash.
    flagged, stats = clock_bias_check(samples=64, timer=lambda: 42)
    assert flagged is False
    assert stats["median_ns"] == 0
    assert stats["samples"] == 64


def test_none_timer_never_crashes():
    # Timer returning None: subtraction raises per-sample, caught -> 0
    # deltas -> degenerate -> False. Loader must survive too.
    flagged, stats = clock_bias_check(samples=16, timer=lambda: None)
    assert flagged is False
    assert stats["median_ns"] == 0


def test_empty_vector_never_flags():
    flagged, stats = clock_bias_verdict([])
    assert flagged is False
    assert stats == {"median_ns": 0, "p99_ns": 0, "tail_frac": 0.0,
                     "samples": 0}


def test_malformed_entries_documented():
    # clock_bias_verdict is strict over explicit vectors: None/str entries
    # raise TypeError (documented here — callers sanitize first). The
    # emitted loader mirror is total instead: it returns False on anything
    # malformed and never raises (loader must not crash the artifact).
    import pytest
    for bad in ([100, None, 200], [100, "x", 200], [None] * 8):
        with pytest.raises(TypeError):
            clock_bias_verdict(bad)
    src = loader_snippet_fragment()
    ns = {"_time": __import__("time")}
    exec(compile(src, "<t>", "exec"), ns)
    f = ns["_nx_has_clock_bias"]
    assert f(_deltas=[100, None, 200]) is False
    assert f(_deltas="not-a-list") is False


def test_replayed_vector_deterministic():
    # Replaying the identical vector twice yields identical verdict+stats
    # (both a clean and a flagging vector).
    for vec in (_clean(), _vm_like()):
        flagged1, stats1 = clock_bias_verdict(vec)
        flagged2, stats2 = clock_bias_verdict(list(vec))
        assert flagged1 is flagged2
        assert stats1 == stats2
