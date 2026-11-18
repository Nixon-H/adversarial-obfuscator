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
import subprocess
import sys
import tempfile
import time

from . import targets as T
from .ai_probe import probe_ai
from .dynamic_probes import (
    probe_memory_maps, probe_runtime_output, probe_temp_files,
)
from .static_probes import (
    probe_elf_symbols, probe_payload_strings, probe_plaintext,
    probe_section_decrypt,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROFILES = {
    "default": [],
    "max": ["--package", "layers=25", "zips=3", "stego"],
    "absolute": [
        "--section-count", "8",
        "--transforms", "data", "function-intent", "speculation",
        "--access", "trial=7d", "block-countries=RU,KP", "vm-threshold=65",
        "--package", "native", "layers=25", "zips=3",
    ],
}


def build(target_name, profile, work_root):
    """Build one protected artefact. Returns (path, build_seconds, log)."""
    src = os.path.join(work_root, target_name + ".py")
    os.makedirs(work_root, exist_ok=True)
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(T.get(target_name)["source"])
    env = dict(os.environ, NIXON_LOG_REDIRECT="0",
               PYTHONPATH=REPO + os.pathsep + os.environ.get("PYTHONPATH", ""),
               TMPDIR=work_root)
    cmd = [sys.executable, "-m", "obfuscator.core.pipeline", "build", src,
           "--skip-cloud", "--in-place"] + PROFILES[profile]
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


def score(target, probes):
    """Turn probe results into the metrics the reviewer listed."""
    plain = probes.get("plaintext", {})
    sec = probes.get("section_decrypt", {})
    pstr = probes.get("payload_strings", {})
    ai = probes.get("ai", {})
    elf = probes.get("elf_symbols", {})
    rt = probes.get("runtime_output", {})
    tmp = probes.get("temp_files", {})

    joined = pstr.get("joined_text", "") or ""
    payload_secrets = [s for s in target["secrets"] if s in joined]
    payload_names = [n for n in target["names"]
                     if n in joined]

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
            "ai_overlap": ai.get("algorithm_overlap", 0.0),
            "ground_truth": target["algorithms"],
        },
        "patch_resistance": {
            "section_pack_derivable": sec.get("derived", False),
        },
        "leakage": {
            "elf_symbols_found": elf.get("found_elf", False),
            "temp_files": tmp.get("new_files", []),
        },
    }


def run(targets, profile, do_ai, out_path):
    work_root = tempfile.mkdtemp(prefix="pydeobs-%s-" % profile)
    results = []
    try:
        for name in targets:
            tgt = T.get(name)
            print("\n=== %s / %s ===" % (profile, name), flush=True)
            art, secs, log = build(name, profile, os.path.join(work_root, name))
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
                "runtime_output": probe_runtime_output(art),
                "temp_files": probe_temp_files(art),
                "memory_maps": probe_memory_maps(art),
            }
            if do_ai:
                print("  querying DS 4.1 Flash via Mistral...", flush=True)
                probes["ai"] = probe_ai(tgt, text)
                a = probes["ai"]
                if a.get("measurement_failed"):
                    print("  AI MEASUREMENT FAILED:", a.get("error"), flush=True)
                else:
                    print("  AI: names %d/%d, secrets %d/%d, algo overlap %.2f"
                          % (a["names_recovered"], a["names_total"],
                             a["secrets_recovered"], a["secrets_total"],
                             a["algorithm_overlap"]), flush=True)
            sc = score(tgt, probes)
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
