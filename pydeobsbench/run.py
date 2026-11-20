"""PyDeObsBench runner: build protected artefacts and attack them.

Separated from the protection compiler BY DESIGN (the reviewer's point): this
module never imports the pipeline's scoring code, so the protection system
cannot become its own judge.

Usage:
    python3 -m pydeobsbench.run --profile max --targets tiny inventory
    python3 -m pydeobsbench.run --profile default --targets all --ai
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import statistics
import subprocess
import sys
import tempfile
import time

from . import targets as T
from .ai_probe import probe_ai
from .dynamic_probes import (
    probe_memory_maps, probe_runtime_output, probe_temp_files,
)
from .memory_probe import probe_memory_extraction
from .timing_probe import time_to_recovery
from .static_probes import (
    probe_elf_symbols, probe_native_blob, probe_payload_strings,
    probe_plaintext, probe_section_decrypt,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROFILES = {
    "default": [],
    # MAX (2026-11-20): the full protection set built during the 35-hour
    # session, enabled wherever the harness can self-supply the inputs —
    # native blob (Cython payload + nx_apply_protections), 8 sealed
    # sections, payload transforms, trial/geofence/VM-threshold access
    # gates, watermark, licence binding, VM dispatch, and load-time Ed25519
    # provenance signing (the key is generated per run and pinned via
    # NIXON_PROVENANCE_PUBKEY so the artefact verifies out-of-band).
    # Measured on this profile: build ~17-19 s, runs rc 0 with the token,
    # refuses without it, all six attack_chain routes rc 137 (the bypass
    # route now dies on the PROVENANCE signature, not just merkle).
    "max": [
        "--package", "native", "layers=25", "zips=3", "stego",
        "--section-count", "8",
        "--transforms", "data", "function-intent", "speculation",
        "--access", "trial=7d", "vm-threshold=65", "block-countries=RU,KP",
        "--watermark", "pydeobs-max",
    ],
    # The pre-2026-11-20 max (kept so the §8 baseline stays comparable).
    "max-legacy": ["--package", "layers=25", "zips=3", "stego"],
    "absolute": [
        # ABSOLUTE (2026-11-20): every namespace and gate the harness can
        # self-supply. Host-binding gates (hwid/hwid-lock) use this host's
        # fingerprint, computed per run; the string-seal shard is generated
        # per run and threaded as NX_SEAL_SHARD (build AND every artefact
        # run). kod/driver-check/name-gate are armed as designed: a gate
        # that kills on this host is a MEASUREMENT, not a skip.
        "--section-count", "8",
        "--watermark", "NX-ABS-001",
        "--transforms", "data", "function-intent", "speculation",
        "string-key-env=NX_SEAL_SHARD",
        "--access", "trial=7d", "expire={EXPIRE_DATE}", "hwid={HOST_FP}",
        "hwid-lock", "kod", "driver-check", "name-gate",
        "block-countries=RU,KP", "vm-threshold=65",
        "--package", "native", "layers=25", "zips=3", "stego",
    ],
    # ABSOLUTE with NO Python fallback: the native blob is the ONLY payload
    # path. The loader ships verbatim (stamped + signed), carries no
    # sections and no bytecode fallback (FALLBACK_BLOB=DISABLED), and
    # refuses to run anything if the blob cannot load. Measured 2026-11-20:
    # three consecutive builds green, artefact runs rc 0, zero anti-dump
    # syscalls in the artefact text.
    "absolute-native-only": [
        "--package", "native-only",
        "--watermark", "NX-ABS-001",
        "--transforms", "data", "function-intent", "speculation",
        "string-key-env=NX_SEAL_SHARD",
        "--access", "trial=7d", "expire={EXPIRE_DATE}", "hwid={HOST_FP}",
        "hwid-lock", "kod", "driver-check", "name-gate",
        "block-countries=RU,KP", "vm-threshold=65",
    ],
}

#: Profiles that bind the payload key to a licence token. The token's key
#: material becomes the seal mask and is NOT written into the artefact, so
#: offline derivation must fail -- which is the property that separates a
#: "protected" artefact from a merely obfuscated one. Measured 2026-11-18:
#: section_decrypt reports "HMAC failed on 4/4 sections (key not derivable)"
#: for a token-bound build, while every unbound profile is fully derivable.
LICENCE_PROFILES = {"absolute-licensed", "max", "absolute",
                    "absolute-native-only"}

#: An extra profile that is the ABSOLUTE recipe bound to a licence token.
PROFILES["absolute-licensed"] = PROFILES["absolute"]


def _issue_licence(work_root):
    """Issue a throwaway licence token; returns (token_path, pubkey_hex)."""
    import secrets as _secrets
    import time as _time
    sys.path.insert(0, REPO)
    from obfuscator.licensing import (
        Licence, issue as _issue, public_key_hex, resolve_private_key,
    )
    seed = _secrets.token_hex(32)
    key = resolve_private_key(seed)
    now = _time.time()
    lic = Licence(
        licence_id="pydeobs-%s" % _secrets.token_hex(4),
        customer="pydeobsbench",
        issued_at=now,
        expires_at=now + 7 * 86400,
        features=("pro",),
        key_material=_secrets.token_hex(32),
    )
    tok = os.path.join(work_root, "harness.licence")
    with open(tok, "w", encoding="utf-8") as fh:
        fh.write(_issue(lic, key))
    return tok, public_key_hex(key)


def build(target_name, profile, work_root, licence=None, pubkey=None,
          prov_key=None):
    """Build one protected artefact. Returns (path, build_seconds, log)."""
    src = os.path.join(work_root, target_name + ".py")
    os.makedirs(work_root, exist_ok=True)
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(T.get(target_name)["source"])
    env = dict(os.environ, NIXON_LOG_REDIRECT="0",
               PYTHONPATH=REPO + os.pathsep + os.environ.get("PYTHONPATH", ""),
               TMPDIR=work_root)
    if pubkey:
        env["NIXON_LICENCE_PUBLIC_KEY"] = pubkey
    # §5l boundary push + provenance signing (2026-11-20): every build gets
    # VM dispatch where eligible and a load-time Ed25519 signature (fresh
    # per run; the operator pins the matching public key out of band via
    # NIXON_PROVENANCE_PUBKEY, which run() sets for the harness's own runs).
    env["NIXON_VM_DISPATCH"] = os.environ.get("NIXON_VM_DISPATCH", "alternate")
    if prov_key:
        env["NIXON_ARTEFACT_SIGN_KEY"] = prov_key
    # The seal shard must match between build and every artefact run: one
    # shard per RUN, generated here, exported for the build and stored for
    # run() to publish to the probes' environment.
    if not os.environ.get("NX_SEAL_SHARD"):
        os.environ["NX_SEAL_SHARD"] = secrets.token_hex(32)
    env["NX_SEAL_SHARD"] = os.environ["NX_SEAL_SHARD"]
    profile_flags = list(PROFILES[profile])
    if any("{HOST_FP}" in f or "{EXPIRE_DATE}" in f for f in profile_flags):
        from obfuscator.trial_bind import fallback_fingerprint
        import datetime as _dt
        host_fp = fallback_fingerprint()
        expire = (_dt.date.today() + _dt.timedelta(days=45)).isoformat()
        profile_flags = [f.replace("{HOST_FP}", host_fp)
                          .replace("{EXPIRE_DATE}", expire)
                          for f in profile_flags]
    cmd = [sys.executable, "-m", "obfuscator.core.pipeline", "build", src,
           "--skip-cloud", "--in-place"] + profile_flags
    if profile in LICENCE_PROFILES and licence:
        # --licence is nargs="+": the sub-options must be SEPARATE argv items.
        cmd += ["--licence", "token=%s" % licence, "env-only"]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=work_root, capture_output=True, text=True,
                       timeout=5400, env=env)
    elapsed = time.perf_counter() - t0
    if p.returncode != 0:
        return None, elapsed, (p.stdout + p.stderr)[-3000:]
    dist = os.path.join(work_root, "dist")
    cands = []
    if os.path.isdir(dist):
        cands = [os.path.join(dist, f) for f in os.listdir(dist)
                 if f.endswith("_protected.py") and "_dbg" not in f]
    if not cands:
        cands = [os.path.join(work_root, f) for f in os.listdir(work_root)
                 if f.endswith("_protected.py") and "_dbg" not in f]
    if not cands:
        return None, elapsed, "no artefact produced"
    return sorted(cands)[0], elapsed, p.stdout[-2000:]


def measure_overhead(source_path, artefact_path, runs=5, warmup=1, timeout=180):
    """§8 performance overhead: what protection costs, against its own source.

    Everything else in this harness measures what protection BUYS. This
    measures what it COSTS, and the two only mean something together.

    METHOD: run the unprotected source and the protected artefact `runs` times
    each after `warmup` discarded runs, from the artefact's own directory, and
    compare the MEDIAN wall-clock (a single scheduler hiccup would otherwise
    dominate). A failed run counts as a failure, never as a timing -- a 0.01s
    entry from a process that exited 137 would be a lie.

    MEASURED 2026-11-18 on this machine:

        target      baseline   protected   ratio   size
        tiny         0.021s     0.327s     15.6x   249 B -> 282 KB
        algo         0.018s     0.366s     19.8x   501 B -> 338 KB
        inventory    0.030s     0.338s     11.4x   1,016 B -> 338 KB

    The protected time is ~0.33-0.37s for ALL THREE regardless of payload: the
    cost is fixed loader work (identity gate, self-check over ~2,400 lines,
    section walk, native import), not per-workload overhead. The 11x-20x spread
    comes entirely from the baseline varying. Quoting one ratio would
    misrepresent it, which is why the range is reported.

    HONEST LIMIT: one machine, one interpreter. Only the RATIO is portable.
    """
    env = dict(os.environ, NIXON_LOG_REDIRECT="0")

    def _median_seconds(target):
        # Each script runs from ITS OWN directory: the artefact's identity
        # gate compares abspath(__file__) with abspath(sys.argv[0]) and the
        # unprotected source resolves its own relative imports. Running both
        # from one directory made the baseline fail 5/5 while looking like a
        # protected-path problem.
        workdir = os.path.dirname(os.path.abspath(target))
        for _ in range(warmup):
            try:
                subprocess.run([sys.executable, target], cwd=workdir,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=timeout,
                               env=env)
            except (subprocess.TimeoutExpired, OSError):
                return None, 0
        times, failures = [], 0
        _first_error = [None]
        for _ in range(runs):
            started = time.perf_counter()
            try:
                done = subprocess.run([sys.executable, target], cwd=workdir,
                                      stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL,
                                      timeout=timeout, env=env)
            except subprocess.TimeoutExpired:
                failures += 1
                continue
            if done.returncode != 0:
                failures += 1
                # Keep the first failure's stderr: a bare count cannot be
                # diagnosed, and this metric spent two rounds returning null
                # for a reason nobody could see.
                if _first_error[0] is None:
                    _first_error[0] = (done.stderr or "")[-300:]
                continue
            times.append(time.perf_counter() - started)
        if not times:
            return None, failures, _first_error[0]
        return statistics.median(times), failures, None

    # Pass the ABSOLUTE path: _median_seconds derives the working directory
    # from it, and a bare basename resolved against the harness's own cwd --
    # so both runs executed from the repo, hit the identity gate, and reported
    # a silent non-zero exit (empty stderr, os._exit). That is why this metric
    # returned null twice while the same commands worked by hand.
    prot_s, prot_fail, prot_err = _median_seconds(os.path.abspath(artefact_path))
    result = {
        "probe": "performance_overhead",
        "protected": {"median_s": round(prot_s, 4) if prot_s else None,
                      "failures": prot_fail,
                      "first_error": prot_err},
        "baseline": None, "size": None,
        "ratios": {"runtime": None, "size": None},
    }
    if source_path and os.path.isfile(source_path):
        base_s, base_fail, base_err = _median_seconds(os.path.abspath(source_path))
        result["baseline"] = {"median_s": round(base_s, 4) if base_s else None,
                              "failures": base_fail,
                              "first_error": base_err}
        if prot_s and base_s and base_s > 0:
            result["ratios"]["runtime"] = round(prot_s / base_s, 3)
        size_base = os.path.getsize(source_path)
        size_prot = os.path.getsize(artefact_path)
        result["size"] = {
            "source_bytes": size_base,
            "artefact_bytes": size_prot,
            "delta_bytes": size_prot - size_base,
            "multiplier": (round(size_prot / size_base, 2)
                           if size_base else None),
        }
        result["ratios"]["size"] = result["size"]["multiplier"]
    return result


def _semantic_block(target_name, target):
    """§8 semantic reconstruction: behaviour compared, source kept separate.

    `equivalent_output` is what the independently written implementation in
    ``pydeobsbench/equivalents.py`` prints; `target_output` is the ORIGINAL's
    recorded stdout. Equality between them is the semantic result.

    `source_overlap` is the Jaccard similarity of top-level identifiers between
    the original and the equivalent. It is reported BESIDE the semantic result
    because the two together are the finding: behaviour reproduced with zero
    shared naming means semantic recovery is genuinely measurable here, and a
    high overlap would mean the comparison was really textual.

    Nothing here is inferred. If no equivalent exists, `coverage` says so and
    `equivalent_matches_target` is None -- not False, because "unmeasured" and
    "measured and different" are different results and a boolean would conflate
    them.
    """
    try:
        from . import equivalents as eq
    except Exception as exc:                       # pragma: no cover - defensive
        return {"error": str(exc)[:160], "equivalent_matches_target": None}
    observed = eq.observe(target_name)
    expected = eq.EXPECTED_OUTPUT.get(target_name)
    return {
        "equivalent_output": observed,
        "target_output": expected,
        "equivalent_matches_target": (None if observed is None or expected is None
                                      else observed == expected),
        "source_overlap": eq.source_overlap(target.get("source") or "",
                                            eq.equivalent_source()),
        "coverage": eq.COVERAGE.get(target_name, "none"),
    }


def score(target, probes, target_name=None):
    """Turn probe results into the metrics the reviewer listed.

    ``target_name`` identifies which ground-truth program this is, so the §8
    semantic block can compare against that target's independently written
    equivalent. It defaults to None for callers that only want the older
    metrics; the semantic block then reports itself as unmeasured rather than
    silently scoring against the wrong target.
    """
    plain = probes.get("plaintext", {})
    sec = probes.get("section_decrypt", {})
    pstr = probes.get("payload_strings", {})
    ai = probes.get("ai", {})
    elf = probes.get("elf_symbols", {})
    nblob = probes.get("native_blob", {})
    rt = probes.get("runtime_output", {})
    tmp = probes.get("temp_files", {})
    mem = probes.get("memory_extraction", {})
    tm = probes.get("time_to_recovery", {})
    perf = probes.get("performance_overhead", {})

    joined = pstr.get("joined_text", "") or ""

    # Payload-text matching must be EXACT and loader-aware. Measured
    # 2026-11-18: a naive `n in joined` reported `seal` (matched the loader's
    # own string "bad string seal") and `main` (matched "__main__") as
    # recovered payload names, which made the stronger ABSOLUTE profile look
    # worse than MAX. Two guards:
    #   * word boundaries, not substrings;
    #   * the loader strings that travel with every payload are excluded.
    _loader_strings = ("bad string seal", "string seal authentication failed",
                       "little", "utf-8", "utf8", "ascii", "latin-1",
                       "section-", "nx-", "_nx_", "__main__", "__mp_main__")

    def _payload_hit(name, text):
        for ls in _loader_strings:
            if name == ls or name in ls:
                return False
        return re.search(
            r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])",
            text) is not None

    payload_secrets = [s for s in target["secrets"] if s in joined]
    payload_names = [n for n in target["names"] if _payload_hit(n, joined)]

    runtime_leak = 0
    for s in target["secrets"]:
        if s in (rt.get("stdout", "") + rt.get("stderr", "")):
            runtime_leak += 1

    return {
        "source_reconstruction": {
            # the best an analyst got from ANY static channel
            "names_from_payload": len(payload_names),
            "names_from_ai": ai.get("names_recovered", 0),
            "names_total": len(target["names"]),
        },
        "secret_recovery": {
            "from_plaintext": plain.get("secrets_recovered", 0),
            "from_decrypted_payload": len(payload_secrets),
            "from_ai": ai.get("secrets_recovered", 0),
            "from_runtime_output": runtime_leak,
            "total": len(target["secrets"]),
        },
        "algorithm_recovery": {
            # None means "not measurable" (too few distinctive ground-truth
            # terms to divide by) -- kept distinct from 0.0 ("measured, no
            # recovery") so a report never reads a missing number as a clean
            # zero.
            "ai_overlap": ai.get("algorithm_overlap"),
            "ai_overlap_basis": ai.get("overlap_basis"),
            "ai_overlap_note": ai.get("overlap_note", ""),
            # §8 "time to successful recovery": seconds from artefact handoff
            # to a CORRECT algorithm description. None means the model never
            # got there inside the budget -- deliberately not a large number,
            # because "not recovered" and "recovered slowly" are different
            # results and a number would conflate them.
            "time_to_recovery_s": (tm.get("time_to_recovery_s")
                                   if tm else None),
            "time_to_recovery_elapsed_s": (tm.get("elapsed_s")
                                           if tm else None),
            "time_to_recovery_measured": bool(tm.get("measured")) if tm else False,
            # WHY the answer was None. Without this, "not recovered" and "the
            # probe could not judge" are indistinguishable in the report -- and
            # they are different results with different remedies. Measured
            # 2026-11-19 on `algo`: 13 distinctive markers, 1 hit (`state`),
            # so the model described the LOADER and not the algorithm. That is
            # a genuine non-recovery, not a metric failure, and the marker
            # counts are what let a reader tell the two apart.
            "time_to_recovery_verdict": (
                {"correct": (tm.get("verdict") or {}).get("correct"),
                 "markers_total": (tm.get("verdict") or {}).get("markers_total"),
                 "hits": (tm.get("verdict") or {}).get("hits"),
                 "hit_words": (tm.get("verdict") or {}).get("hit_words"),
                 "hit_numbers": (tm.get("verdict") or {}).get("hit_numbers"),
                 "min_markers": (tm.get("verdict") or {}).get("min_markers"),
                 "note": tm.get("note", "")}
                if tm else None),
            "ground_truth": target["algorithms"],
            # §8 semantic reconstruction, made measurable. The review asks for
            # semantic recovery as DISTINCT from source recovery, and that
            # distinction needs an artifact written from the SPEC rather than
            # from the original source: pydeobsbench/equivalents.py. Reported
            # here rather than only in the test suite so the report shows the
            # comparison the score is based on.
            "semantic": _semantic_block(target_name, target),
            # §8 WHAT THE MODEL ACTUALLY RECOVERED, including the result that
            # matters most and was previously dropped here: `loader_reversed`.
            # Measured 2026-11-19 on a real 'max' artefact, DS 4.1 Flash
            # reconstructed the ENTIRE protection loader from the artefact text
            # -- prctl(PR_SET_DUMPABLE), RLIMIT_CORE, the identity gate and its
            # exit code, constant_time_compare, _nx_self_fail/exit 137, the
            # mlock page-alignment. That is a complete map of the layer the
            # payload is wrapped in.
            #
            # `algorithm_overlap` said "n/a (insufficient distinctive terms)"
            # for the same run, because the tiny target's ground truth yields
            # only two scorable words. Reporting that as resistance would be
            # exactly the proxy the review warns about, so both numbers are
            # carried and neither is allowed to stand alone.
            "model_reconstruction": {
                "loader_reversed": ai.get("loader_reversed"),
                "payload_markers_found": ai.get("payload_markers_found", []),
                "algorithm_text_chars": len(ai.get("algorithm_text") or ""),
                "algorithm_text_head": (ai.get("algorithm_text") or "")[:400],
                "overlap_note": ai.get("overlap_note", ""),
                "refused": ai.get("refused"),
            } if ai else None,
        },
        "patch_resistance": {
            "section_pack_derivable": sec.get("derived", False),
        },
        "cost": {
            # §8 performance overhead: the only metric whose unit is the
            # defender's milliseconds rather than the attacker's effort.
            "size_multiplier": (perf.get("size") or {}).get("multiplier"),
            "artefact_bytes": (perf.get("size") or {}).get("artefact_bytes"),
            "runtime_ratio": (perf.get("ratios") or {}).get("runtime"),
            "baseline_median_s": (perf.get("baseline") or {}).get("median_s"),
            "protected_median_s": (perf.get("protected") or {}).get("median_s"),
        },
        "leakage": {
            "elf_symbols_found": elf.get("found_elf", False),
            "temp_files": tmp.get("new_files", []),
            # Native module: the loader carries its own key, so the blob is
            # always extractable on an unbound build. What varies is what it
            # exposes once extracted.
            "native_blob_present": nblob.get("found", False),
            "native_blob_derivable": nblob.get("derived", False),
            "native_exports": nblob.get("dynamic_exports", []),
            "native_payload_names": nblob.get("payload_names_in_strings", []),
            "native_hardened": {
                "relro": nblob.get("relro"),
                "nx": nblob.get("nx_stack"),
                "symtab": nblob.get("symtab_present"),
                "comment": nblob.get("comment_present"),
            },
            # Runtime memory: measured on the LIVE process, not the artefact.
            # `samples` travels with the result because a 1-sample reading is
            # weak evidence and must not be mistaken for a clean sweep.
            "memory_extraction": {
                "measured": bool(mem.get("ran")) and not mem.get("error"),
                "samples": mem.get("samples", 0),
                "secrets_recovered": mem.get("secrets_recovered", 0),
                "names_recovered": mem.get("names_recovered", 0),
                "secrets_hit": mem.get("secrets_hit", []),
                "names_hit": mem.get("names_hit", []),
                "error": mem.get("error"),
            },
        },
    }


def run(targets, profile, do_ai, out_path):
    work_root = tempfile.mkdtemp(prefix="pydeobs-%s-" % profile)
    licence = pubkey = None
    if profile in LICENCE_PROFILES:
        try:
            licence, pubkey = _issue_licence(work_root)
            print("  issued throwaway licence token", flush=True)
        except Exception as exc:
            print("  licence issue failed: (build will be unbound)" if False else "  licence issue failed: %s (build will be unbound)" % exc,
                  flush=True)
    # Provenance signing: one Ed25519 key per RUN, pinned out of band for
    # every artefact this harness runs (probes inherit os.environ). Restored
    # on exit so the harness never leaks env into the caller's shell.
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey)
    prov_key = Ed25519PrivateKey.generate().private_bytes_raw().hex()
    prov_pub = None
    try:
        from obfuscator.licensing import private_key_from_hex, public_key_hex
        prov_pub = public_key_hex(private_key_from_hex(prov_key))
    except Exception:
        prov_key = None
    _saved_env = {k: os.environ.get(k) for k in
                  ("NIXON_LICENCE", "NIXON_PROVENANCE_PUBKEY",
                   "NIXON_VM_DISPATCH")}
    if licence:
        os.environ["NIXON_LICENCE"] = licence
    if prov_pub:
        os.environ["NIXON_PROVENANCE_PUBKEY"] = prov_pub
    os.environ.setdefault("NIXON_VM_DISPATCH", "alternate")
    results = []
    try:
        for name in targets:
            tgt = T.get(name)
            print("\n=== %s / %s ===" % (profile, name), flush=True)
            art, secs, log = build(name, profile,
                                   os.path.join(work_root, name),
                                   licence=licence, pubkey=pubkey,
                                   prov_key=prov_key)
            if not art:
                print("  BUILD FAILED:", log[-300:], flush=True)
                results.append({"target": name, "profile": profile,
                                "build_failed": True, "build_seconds": secs,
                                "log_tail": log[-800:]})
                continue
            print("  built in %.1fs: %s (%d bytes)"
                  % (secs, os.path.basename(art), os.path.getsize(art)),
                  flush=True)
            text = open(art, encoding="utf-8", errors="replace").read()
            probes = {
                "plaintext": probe_plaintext(tgt, art),
                "section_decrypt": probe_section_decrypt(art),
                "payload_strings": probe_payload_strings(art),
                "elf_symbols": probe_elf_symbols(art),
                "native_blob": probe_native_blob(art, tgt),
                "runtime_output": probe_runtime_output(art),
                "temp_files": probe_temp_files(art),
                "memory_maps": probe_memory_maps(art),
                # The only measurement that tests the review's actual claim:
                # an attacker who EXECUTES the artefact and dumps its memory.
                # Everything else in this harness is static.
                "memory_extraction": probe_memory_extraction(art, tgt),
                # §8 cost side: what the protections above actually charge.
                # The source lives in the per-target build root
                # (work_root/<name>/<name>.py), not beside the artefact: the
                # first wiring used work_root/<name>.py and the baseline came
                # back null, which made the ratio unmeasurable while looking
                # like a clean run.
                "performance_overhead": measure_overhead(
                    os.path.join(work_root, name, name + ".py"), art),
            }
            if do_ai:
                print("  querying DS 4.1 Flash via Mistral...", flush=True)
                probes["ai"] = probe_ai(tgt, text)
                probes["time_to_recovery"] = time_to_recovery(
                    tgt, text)
                a = probes["ai"]
                if a.get("measurement_failed"):
                    print("  AI MEASUREMENT FAILED:", a.get("error"), flush=True)
                else:
                    _ov = a.get("algorithm_overlap")
                    print("  AI: names %d/%d, secrets %d/%d, algo overlap %s"
                          % (a["names_recovered"], a["names_total"],
                             a["secrets_recovered"], a["secrets_total"],
                             ("%.2f" % _ov) if _ov is not None
                             else "n/a (%s)" % (a.get("overlap_note") or "?",
                                                )), flush=True)
            sc = score(tgt, probes, name)
            results.append({
                "target": name, "profile": profile,
                "artefact": art, "artefact_bytes": os.path.getsize(art),
                "build_seconds": round(secs, 1),
                "score": sc, "probes": probes,
            })
            sr = sc["source_reconstruction"]
            sec2 = sc["secret_recovery"]
            print("  => names %d/%d  secrets %d/%d  pack_derivable=%s"
                  % (max(sr["names_from_payload"], sr["names_from_ai"]),
                     sr["names_total"],
                     max(sec2["from_plaintext"], sec2["from_decrypted_payload"],
                         sec2["from_ai"], sec2["from_runtime_output"]),
                     sec2["total"],
                     sc["patch_resistance"]["section_pack_derivable"]),
                  flush=True)
    finally:
        # restore the caller's environment: the licence token path, the
        # provenance pin and the VM-dispatch choice were set for THIS run's
        # probes and must not leak into the invoking shell
        for _k, _v in _saved_env.items():
            if _v is None:
                os.environ.pop(_k, None)
            else:
                os.environ[_k] = _v
        pass  # keep artefacts for inspection

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"profile": profile, "work_root": work_root,
                   "results": results}, fh, indent=2)
    print("\nwrote %s" % out_path)
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pydeobsbench")
    ap.add_argument("--profile", default="max", choices=sorted(PROFILES))
    ap.add_argument("--targets", nargs="+", default=["all"])
    ap.add_argument("--ai", action="store_true",
                    help="query DeepSeek V4.1 Flash via Mistral")
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    names = T.names() if "all" in a.targets else a.targets
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "report", "run-%s-%d.json"
                                % (a.profile, int(time.time())))
    run(names, a.profile, a.ai, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
