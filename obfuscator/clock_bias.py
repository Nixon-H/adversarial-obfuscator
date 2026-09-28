"""Clock-interrupt-bias timing side-channel detector (V10 claim: REAL signal).

Technique: sample a high-resolution counter (:func:`time.perf_counter_ns`)
in a tight loop of N iterations and examine the distribution of
per-iteration deltas. On bare metal, deltas cluster tightly (interrupts
are rare relative to the loop rate); under a hypervisor / debugger /
emulator, periodic clock-interrupt exits (VM exits, interrupt injection)
create a bimodal tail: a small fraction of deltas are orders of magnitude
larger than the median AND recur systematically (not one-off noise).

Detector rule (conservative: prefers false-negative over false-positive;
this feeds a confidence-weighted score, default tier is Monitor/report):
collect N deltas, compute median + 99th percentile, flag iff
  (p99 / median > P99_MEDIAN_RATIO_THRESHOLD)   # 50x
  AND (fraction of deltas > 10x median exceeds TAIL_FRAC_THRESHOLD)  # 0.5%
BOTH conditions must hold: a single slow iteration (one-off scheduling
noise) moves neither p99 (needs >1% outliers at N=2000) nor the tail
fraction, so it cannot flag. A degenerate timer (median <= 0) never flags.

This module mirrors ``runtime/src/timing.rs`` (``clock_bias_verdict`` /
``clock_bias_stats`` / ``clock_bias_check``) over integer nanosecond
deltas; the shared-vector parity test is ``tests/test_clock_bias.py``.

Loader wiring: :func:`loader_snippet_fragment` returns registry-free,
stdlib-only, ``match``-free Python 3.10-compatible source defining
``_nx_has_clock_bias()`` for emitted loaders. ``obfuscator/vm_score.py``
embeds that fragment by construction and wires the ``clock_bias`` signal
(weight :data:`CLOCK_BIAS_WEIGHT`, in the ``timing=10`` family) into the
runtime ``vm_check`` / ``vm_score_percent`` findings, default ON.

Live-hardware status: DIAGNOSTIC / NON-GATING, permanently. The live
:func:`clock_bias_check` samples a real host counter, so its verdict is
inherently host-noisy: scheduler preemption, CI load spikes, power
management, and hypervisor steal time all widen the delta tail on
otherwise clean metal. A live verdict therefore never gates execution
and never contributes more than its Monitor-tier confidence weight; it
is a diagnostic hint corroborated (or outvoted) by the rest of the
signal ensemble. Deterministic verdicts come only from explicit delta
vectors via :func:`clock_bias_verdict` (unit-testable, no I/O).
"""

import time

# Signal name + weight shared with obfuscator/vm_score.py SIGNALS.
SIGNAL_NAME = "clock_bias"
CLOCK_BIAS_WEIGHT = 10

# Sample count for live checks (mirrors CLOCK_BIAS_SAMPLES in timing.rs).
CLOCK_BIAS_SAMPLES = 2000
# p99/median ratio above which the tail is "orders of magnitude" biased.
CLOCK_BIAS_P99_RATIO_THRESHOLD = 50.0
# Deltas larger than TAIL_FACTOR * median count toward the biased tail.
CLOCK_BIAS_TAIL_FACTOR = 10
# Tail fraction above which the bias is systematic (>0.5% of samples).
CLOCK_BIAS_TAIL_FRAC_THRESHOLD = 0.005

# Serialized threshold copies embedded in loader_snippet_fragment()
# string literals. Python ints/floats repr deterministically; the test
# test_thresholds_serialized_into_snippet fails the build if the
# literals drift from these constants. (The emitter uses plain string
# literals — %r formatting inside the tuple-continuation breaks tuple
# syntax, so the lock is test-side, not emit-side.)
_SERIALIZED_THRESHOLDS = {"samples": 2000, "ratio": 50.0, "factor": 10,
                          "frac": 0.005}
assert _SERIALIZED_THRESHOLDS["samples"] == CLOCK_BIAS_SAMPLES
assert _SERIALIZED_THRESHOLDS["ratio"] == CLOCK_BIAS_P99_RATIO_THRESHOLD
assert _SERIALIZED_THRESHOLDS["factor"] == CLOCK_BIAS_TAIL_FACTOR
assert _SERIALIZED_THRESHOLDS["frac"] == CLOCK_BIAS_TAIL_FRAC_THRESHOLD


def clock_bias_stats(deltas):
    """Compute (median_ns, p99_ns, tail_frac, samples) for a delta vector.

    Pure function over explicit deltas (unit-testable, no I/O). Returns a
    dict with keys ``median_ns``, ``p99_ns``, ``tail_frac``, ``samples``.
    Empty input yields all zeros. Even-length median is the integer mean
    of the two middle values (mirrors the saturating midpoint in Rust).
    """
    ds = list(deltas) if deltas is not None else []
    n = len(ds)
    if n == 0:
        return {"median_ns": 0, "p99_ns": 0, "tail_frac": 0.0, "samples": 0}
    s = sorted(ds)
    if n % 2 == 1:
        median = s[n // 2]
    else:
        median = (s[n // 2 - 1] + s[n // 2]) // 2
    rank = (n * 99 + 99) // 100 - 1
    if rank < 0:
        rank = 0
    if rank >= n:
        rank = n - 1
    p99 = s[rank]
    thresh = median * CLOCK_BIAS_TAIL_FACTOR
    tail = 0
    for d in s:
        if d > thresh:
            tail += 1
    return {
        "median_ns": median,
        "p99_ns": p99,
        "tail_frac": tail / n,
        "samples": n,
    }


def clock_bias_verdict(deltas):
    """Return (flagged, stats) for an explicit delta vector.

    Never flags on empty input or a degenerate (median <= 0) timer.
    """
    stats = clock_bias_stats(deltas)
    if stats["samples"] == 0 or stats["median_ns"] <= 0:
        return (False, stats)
    ratio = stats["p99_ns"] / stats["median_ns"]
    flagged = (
        ratio > CLOCK_BIAS_P99_RATIO_THRESHOLD
        and stats["tail_frac"] > CLOCK_BIAS_TAIL_FRAC_THRESHOLD
    )
    return (bool(flagged), stats)


def clock_bias_check(samples=CLOCK_BIAS_SAMPLES, timer=None):
    """Live check: sample ``timer`` (default :func:`time.perf_counter_ns`)
    in a tight loop, then :func:`clock_bias_verdict`. Returns
    (flagged, stats). ``samples`` <= 0 (or unparseable) falls back to
    :data:`CLOCK_BIAS_SAMPLES`.
    """
    try:
        n = int(samples) if samples else CLOCK_BIAS_SAMPLES
    except Exception:
        n = CLOCK_BIAS_SAMPLES
    if n <= 0:
        n = CLOCK_BIAS_SAMPLES
    tick = timer if timer is not None else time.perf_counter_ns
    deltas = []
    prev = tick()
    for _ in range(n):
        now = tick()
        try:
            deltas.append(now - prev)
        except Exception:
            deltas.append(0)
        prev = now
    return clock_bias_verdict(deltas)


def loader_snippet_fragment():
    """Return Python-3.10-compatible loader source defining
    ``_nx_has_clock_bias()`` (stdlib-only, no ``match`` statement).

    The emitted function needs ``_time`` (``import time as _time``) in
    scope -- the vm_score loader snippet already provides it. Signature
    ``_nx_has_clock_bias(_samples=2000, _timer=None, _deltas=None)``:
    ``_deltas`` is a deterministic test hook (verdict over explicit
    deltas, no sampling); ``_timer`` injects a fake clock. Any exception
    (or degenerate timer) yields ``False`` -- never crash the loader.
    """
    src = (
        "def _nx_has_clock_bias(_samples=2000, _timer=None, _deltas=None):\n"
        "    # Clock-interrupt-bias side-channel check (V10 REAL signal):\n"
        "    # tight perf_counter_ns loop, flag iff p99/median > 50x AND\n"
        "    # tail (>10x median) fraction > 0.5%. Both conditions required\n"
        "    # (one-off noise cannot flag). Conservative: False on any\n"
        "    # error/degenerate timer. Report-tier signal (Monitor default).\n"
        "    try:\n"
        "        _n = int(_samples) if _samples else 2000\n"
        "    except Exception:\n"
        "        _n = 2000\n"
        "    if _n <= 0:\n"
        "        _n = 2000\n"
        "    try:\n"
        "        if _deltas is not None:\n"
        "            _ds = list(_deltas)\n"
        "        else:\n"
        "            _t = _timer if _timer is not None else _time.perf_counter_ns\n"
        "            _ds = []\n"
        "            _prev = _t()\n"
        "            for _i in range(_n):\n"
        "                _now = _t()\n"
        "                try:\n"
        "                    _ds.append(_now - _prev)\n"
        "                except Exception:\n"
        "                    _ds.append(0)\n"
        "                _prev = _now\n"
        "        if not _ds:\n"
        "            return False\n"
        "        _s = sorted(_ds)\n"
        "        _m = len(_s)\n"
        "        if _m % 2 == 1:\n"
        "            _med = _s[_m // 2]\n"
        "        else:\n"
        "            _med = (_s[_m // 2 - 1] + _s[_m // 2]) // 2\n"
        "        if _med <= 0:\n"
        "            return False\n"
        "        _rank = (_m * 99 + 99) // 100 - 1\n"
        "        if _rank < 0:\n"
        "            _rank = 0\n"
        "        if _rank >= _m:\n"
        "            _rank = _m - 1\n"
        "        _p99 = _s[_rank]\n"
        "        _ratio = _p99 / _med\n"
        "        _thr = _med * 10\n"
        "        _tail = 0\n"
        "        for _d in _s:\n"
        "            if _d > _thr:\n"
        "                _tail += 1\n"
        "        _frac = _tail / _m\n"
        "        return bool(_ratio > 50.0 and _frac > 0.005)\n"
        "    except Exception:\n"
        "        return False\n"
    )
    compile(src, "<nx_clock_bias>", "exec")
    return src
