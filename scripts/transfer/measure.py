"""Endpoints, transfer metric, CIs, falsification test (G2).

Primary endpoint (pre-registered, protocol.py):
  S_cfg = correctly recovered target functions / ground-truth functions.
  A function counts recovered iff its mapped candidate passes ALL of its
  ground-truth vectors when executed in a subprocess.

Secondary: S_cfg_boundary (arity match only), S_const (literal recovery),
S_deobf (recovered by UNRENAMED correct-arity candidate passing all
vectors — measures identifier-resistance failure), attack_time_s.

Transfer (frozen definition):
  T_ij = S(B_j | P_i) / S(B_j | P_j)
Zero-denominator rule: denom 0 and numer 0 -> T=1.0 flagged "tie-zero";
denom 0 and numer>0 -> T=+inf, capped at CAP_RATIO and flagged
"zero-self". Capped values are reported, never silently dropped.

Uncertainty: bootstrap percentile CIs over ground-truth functions
(resample function indices, B=BOOTSTRAP_B, seeded) + two-sided
Mann-Whitney U (normal approx, tie-corrected) for hetero-vs-seed.
Small-n caveat: with 3 builds/arm the rank-sum floor is p~0.10 —
protocol recommends >=6/arm for inference; smoke runs report CIs only.
"""
import math
import random

from scripts.transfer import protocol

CAP_RATIO = 10.0

# Cross-build attack taxonomy (what transfers, not just how much).
# Each covered type maps to a measured endpoint; uncovered types are
# reported as null WITH reason (never silently dropped, never zeroed).
TRANSFER_TYPES = (
    ("function", "S_cfg_boundary",
     "covered: arity-boundary mapping transfer"),
    ("semantic", "S_cfg",
     "covered: vector-confirmed recovery transfer (PRIMARY)"),
    ("constant", "S_const",
     "covered: literal-recovery transfer"),
    ("name", "S_deobf",
     "covered: by-name recovery transfer (identifier-resistance failure)"),
    ("cfg", None,
     "uncovered: no CFG-edge recovery arm; needs edge-level measurement"),
    ("dataflow", None,
     "uncovered: no dataflow-recovery arm"),
    ("vm", None,
     "uncovered: no VM/dispatcher-recovery arm"),
)


def taxonomy_transfer(recoveries, ground_truth, vectors):
    """Per-type T vectors. Returns {type: {...}}.

    Covered types reuse the frozen transfer definition
    (transfer_matrix) on their endpoint. Uncovered types return
    {"status": "uncovered", "reason": ...} with entries=[] and
    T=None — an explicit gap, not a zero.
    """
    out = {}
    for tname, endpoint, note in TRANSFER_TYPES:
        if endpoint is None:
            out[tname] = {"status": "uncovered", "reason": note,
                          "entries": [], "T": None}
            continue
        entries = transfer_matrix(recoveries, ground_truth, vectors,
                                  endpoint=endpoint)
        h_t = [e["T"] for e in entries
               if e["dev"].startswith(protocol.ARM_HETERO)
               and e["target"].startswith(protocol.ARM_HETERO)]
        s_t = [e["T"] for e in entries
               if e["dev"].startswith(protocol.ARM_SEED_ONLY)
               and e["target"].startswith(protocol.ARM_SEED_ONLY)]
        out[tname] = {"status": "covered", "reason": note,
                      "entries": entries, "T_hetero": h_t, "T_seed": s_t,
                      "falsification": falsification_verdict(h_t, s_t)}
    return out


def score_recovery(recovery, ground_truth, vectors):
    """Compute all endpoints from one apply() recovery dict."""
    funcs = [f["name"] for f in ground_truth["functions"]]
    per = recovery.get("per_func", {})
    rec = bnd = deob = 0
    for name in funcs:
        pf = per.get(name, {})
        total = pf.get("total", 0)
        passed = pf.get("passed", 0)
        if total > 0 and passed == total:
            rec += 1
        cand = (pf.get("candidate") or "")
        if cand:
            bnd += 1
        if cand == name and total > 0 and passed == total:
            deob += 1
    n = max(len(funcs), 1)
    consts = ground_truth.get("constants", [])
    found = recovery.get("constants_found", [])
    return {
        "S_cfg": rec / n,
        "S_cfg_boundary": bnd / n,
        "S_const": (len(found) / len(consts)) if consts else 1.0,
        "S_deobf": deob / n,
        "attack_time_s": recovery.get("attack_time_s", 0.0),
        "n_functions": len(funcs),
    }


def transfer_ratio(s_cross, s_self):
    """T with zero-denominator rule. Returns (value, flag)."""
    if s_self > 0:
        return s_cross / s_self, "ok"
    if s_cross == 0:
        return 1.0, "tie-zero"
    return CAP_RATIO, "zero-self"


def transfer_matrix(recoveries, ground_truth, vectors, endpoint="S_cfg"):
    """recoveries: {(dev_key, tgt_key): recovery}. Returns T entries.

    dev_key/tgt_key identify builds; self entries (dev==tgt) give the
    denominator S(B_j | P_j).
    """
    scores = {}
    for key, rec in recoveries.items():
        if rec.get("status") != "ok":
            continue
        scores[key] = score_recovery(rec, ground_truth, vectors)[endpoint]
    entries = []
    targets = sorted({t for _, t in scores})
    for t in targets:
        s_self = scores.get((t, t))
        if s_self is None:
            continue
        for d in sorted({x for x, _ in scores}):
            if (d, t) not in scores:
                continue
            val, flag = transfer_ratio(scores[(d, t)], s_self)
            entries.append({"dev": d, "target": t, "T": val, "flag": flag,
                            "S_cross": scores[(d, t)], "S_self": s_self})
    return entries


def bootstrap_ci(values, b=None, seed=0):
    """Percentile bootstrap CI of the mean. Returns (lo, hi)."""
    b = b or protocol.BOOTSTRAP_B
    rng = random.Random(seed)
    n = len(values)
    if n == 0:
        return (0.0, 0.0)
    if n == 1:
        return (values[0], values[0])
    means = []
    for _ in range(b):
        s = sum(values[rng.randrange(n)] for _ in range(n)) / n
        means.append(s)
    means.sort()
    return (means[int(0.025 * b)], means[min(int(0.975 * b), b - 1)])


def mann_whitney_u(x, y):
    """Two-sided Mann-Whitney U (normal approx, tie-corrected).

    Returns (U, p). Small-n caveat documented in module docstring.
    """
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return 0.0, 1.0
    pooled = sorted([(v, 0) for v in x] + [(v, 1) for v in y])
    ranks, i = {}, 0
    n = n1 + n2
    rank_of = [0.0] * n
    while i < n:
        j = i
        while j < n and pooled[j][0] == pooled[i][0]:
            j += 1
        avg = (i + 1 + j) / 2.0
        for k in range(i, j):
            rank_of[k] = avg
        i = j
    r1 = sum(rank_of[k] for k in range(n) if pooled[k][1] == 0)
    u1 = r1 - n1 * (n1 + 1) / 2.0
    u = min(u1, n1 * n2 - u1)
    mu = n1 * n2 / 2.0
    # Tie correction over rank groups.
    t_sum = 0.0
    i = 0
    vals = sorted(v for v, _ in pooled)
    while i < n:
        j = i
        while j < n and vals[j] == vals[i]:
            j += 1
        t = j - i
        t_sum += t ** 3 - t
        i = j
    var = n1 * n2 / 12.0 * ((n + 1) - t_sum / (n * (n - 1)) if n > 1 else 0.0)
    if var <= 0:
        return u, 1.0
    z = (u - mu + (0.5 if u < mu else -0.5)) / math.sqrt(var)
    p = math.erfc(abs(z) / math.sqrt(2.0))
    return u, min(max(p, 0.0), 1.0)


def falsification_verdict(t_hetero, t_seed):
    """H1/H0 verdict. Returns dict with U, p, direction, verdict string.

    Verdict CLAIM only if p < 0.05 AND median(hetero) < median(seed).
    Otherwise: "no-distinguishable-difference — do not claim transfer
    resistance" (protocol falsification rule).
    """
    import statistics
    u, p = mann_whitney_u(t_hetero, t_seed)
    med_h = statistics.median(t_hetero) if t_hetero else 1.0
    med_s = statistics.median(t_seed) if t_seed else 1.0
    claim = bool(p < 0.05 and med_h < med_s)
    return {"U": u, "p": p, "median_hetero": med_h, "median_seed": med_s,
            "claim_transfer_resistance": claim,
            "verdict": ("SUPPORTS-H1" if claim
                        else "FAIL-TO-DISTINGUISH — do not claim transfer resistance")}
