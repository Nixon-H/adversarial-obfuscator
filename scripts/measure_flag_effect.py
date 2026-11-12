#!/usr/bin/env python3
"""Measure which hardening flags actually change the artefact.

A flag that builds and runs is not evidence that it did anything. This session
found six controls that looked wired and were not (a --validate that never
validated, a CloudBuilder nothing instantiated, a chain secret shipped beside its
ciphertext, ...), so "the build succeeded" is not a measurement.

Method: build the same payload once per flag, hash the emitted artefact, and group
flags that produce a byte-identical result. Flags in the baseline group emit
nothing that survives to the artefact -- either they are already implied by a
lower-level flag, they are reporting-only, or they are decorative.

Usage::

    python3 scripts/measure_flag_effect.py            # full run, writes a report
    python3 scripts/measure_flag_effect.py --quick    # 5 flags, sanity check
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "flag_effect")

#: The verified working set from the maximal-hardening study. Any flag here that
#: produces the same artefact as the baseline is decorative.
CANDIDATES = [
    ["--transforms", "data"],
    ["--transforms", "speculation"],
    ["--transforms", "function-intent"],
    ["--transforms", "struct"],
    ["--audit", "invariant-engine"], ["--audit", "self-audit"],
    ["--audit", "verification-diversity"], ["--audit", "proof-carrying"],
    ["--audit", "verify-preservation"], ["--audit", "verify-mutations"],
    ["--audit", "verify-mba"], ["--audit", "verify-jit"],
    ["--audit", "verify-watermark"], ["--audit", "proof-soundness"],
    ["--audit", "multi-tool"], ["--audit", "trust-boundary"],
    ["--audit", "security-gates"], ["--audit", "verification-bundle"],
    ["--audit", "verify-preservation-formal"],
    ["--research", "crypto-binding"], ["--research", "adaptive"],
    ["--research", "uarch-watermark"], ["--research", "cfg-mutation"],
    ["--research", "class-dispatch"], ["--research", "ssa-mutation"],
    ["--research", "micro-fragment"], ["--research", "fragment"],
    ["--research", "per-exec-recompile"], ["--research", "self-healing"],
    ["--research", "state-isa"], ["--research", "history-bound-decryption"],
    ["--research", "rolling-keys"], ["--research", "ephemeral-isa"],
    ["--research", "flow-entangle"], ["--research", "recovery-prevention"],
    ["--research", "adaptive-classifier-loop"],
    ["--research", "adversarial-loop"], ["--research", "llm-fingerprint"],
    ["--research", "fragment-migration"],
]
#: Baseline every measurement is taken against: the ladder alone.
#:
#: The seed matters more than anything else in this file. Two builds of the same
#: source with the same flags produce DIFFERENT artefacts unless the RNG is
#: pinned -- measured: 16272 vs 16581 bytes for back-to-back runs. Without
#: SEED, "the sha256 changed" is true for every flag including one that does
#: nothing, which makes the whole comparison meaningless.
SEED = ["--transforms", "seed=4242"]
BASE = ["--opt-level", "5"] + SEED
#: Cheap stages only, so a run is seconds not minutes. Documented in the report.
SKIPS = ["--skip", "irgen", "llvmgen", "encrypt", "relay", "extras"]

PAYLOAD = '''def add(a, b):
    return a + b


def greet(name):
    return "hello " + name


print(add(2, 3))
print(greet("world"))
'''


def build(flags: list[str], work: str) -> tuple[str, float, int]:
    """Build in a private dir; return (sha256 of artefact, seconds, bytes)."""
    src = os.path.join(work, "payload.py")
    with open(src, "w", encoding="utf-8") as f:
        f.write(PAYLOAD)
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    env["PYTHONPATH"] = ROOT
    started = time.time()
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "build.py"),
         "--payload", src, "-o", os.path.join(work, "staged.py"),
         "--force-output", *BASE, *flags, *SKIPS],
        cwd=work, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=900,
    )
    elapsed = time.time() - started
    artefact = os.path.join(ROOT, "build", "payload_obfuscated.py")
    if proc.returncode != 0 or not os.path.exists(artefact):
        return f"BUILD-FAILED(rc={proc.returncode})", elapsed, 0
    data = open(artefact, "rb").read()
    digest = hashlib.sha256(data).hexdigest()
    os.remove(artefact)
    return digest, elapsed, len(data)


def main(argv: list[str]) -> int:
    flags = CANDIDATES[:5] if "--quick" in argv else list(CANDIDATES)
    os.makedirs(OUT, exist_ok=True)
    work = tempfile.mkdtemp(prefix="flageffect_")

    print(f"baseline: {' '.join(BASE + SKIPS)}")
    base_digest, base_secs, base_bytes = build([], work)
    print(f"  baseline artefact {base_bytes} bytes in {base_secs:.1f}s "
          f"sha={base_digest[:16]}")

    rows = []
    for i, flag in enumerate(flags, 1):
        label = " ".join(flag)
        digest, secs, size = build(list(flag), work)
        verdict = ("NO-EFFECT" if digest == base_digest
                   else ("FAILED" if digest.startswith("BUILD-FAILED") else "CHANGES"))
        rows.append({"flag": label, "sha256": digest, "bytes": size,
                     "seconds": round(secs, 1), "verdict": verdict})
        print(f"[{i:2d}/{len(flags)}] {label:<40} {verdict:<10} "
              f"{size:>7} bytes {secs:5.1f}s")

    groups: dict[str, list[str]] = {}
    for r in rows:
        groups.setdefault(r["sha256"], []).append(r["flag"])

    report = os.path.join(OUT, "report.json")
    with open(report, "w", encoding="utf-8") as f:
        json.dump({"baseline": {"sha256": base_digest, "bytes": base_bytes,
                                "seconds": round(base_secs, 1),
                                "command": BASE + SKIPS},
                   "flags": rows,
                   "identical_to_baseline": [r["flag"] for r in rows
                                             if r["verdict"] == "NO-EFFECT"],
                   "groups": {k: v for k, v in groups.items() if len(v) > 1}},
                  f, indent=2)

    no_effect = [r["flag"] for r in rows if r["verdict"] == "NO-EFFECT"]
    changes = [r["flag"] for r in rows if r["verdict"] == "CHANGES"]
    failed = [r["flag"] for r in rows if r["verdict"] == "FAILED"]
    print(f"\n{len(changes)} change the artefact, {len(no_effect)} do not, "
          f"{len(failed)} fail to build")
    if no_effect:
        print("no measurable effect at this payload/stage:")
        for f in no_effect:
            print("   ", f)
    print(f"report: {report}")
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
