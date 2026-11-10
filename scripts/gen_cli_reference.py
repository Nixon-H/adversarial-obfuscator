#!/usr/bin/env python3
"""Generate the complete CLI reference for docs/CLI.md from the live parsers.

The reference used to live in the README, hand-written, listing 42 flags while
the parser had 271. Hand-maintained references drift the moment a flag is
added, and a reference that is 15% right is worse than none: a reader assumes
the rest of the surface does not exist. The reference now lives in
``docs/CLI.md``, next to the usage prose, and the README links to it.

This emits every option, with the parser's own help text, grouped by area.
``tests/test_readme_matches_cli.py`` re-runs it and fails if the document is
stale, so the block cannot drift silently again.

Usage::

    python3 scripts/gen_cli_reference.py            # print the blocks
    python3 scripts/gen_cli_reference.py --check    # exit 1 if CLI.md is stale
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI_DOC = os.path.join(ROOT, "docs", "CLI.md")
START = "<!-- BEGIN GENERATED CLI REFERENCE -->"
END = "<!-- END GENERATED CLI REFERENCE -->"
LOADER_START = "<!-- BEGIN GENERATED LOADER REFERENCE -->"
LOADER_END = "<!-- END GENERATED LOADER REFERENCE -->"

#: Ordered (heading, predicate). First match wins, so put the specific areas
#: before the catch-all. Predicates see the bare flag name without dashes.
GROUPS = [
    ("Input, output and build control", lambda f: f in {
        "payload", "output", "force-output", "version", "cross",
        "generate-payload-h", "no-generate-payload-h", "python-dll",
        "rust-exe", "skip-conflict-check", "include-original",
    } or f.startswith("skip-")),
    ("Obfuscation ladder and AST transforms", lambda f: f.startswith("no-") or f in {
        "opt-level", "lowering", "lowering-level", "validate", "validate-fail",
        "advanced-protection", "advanced-protection-only", "phase2",
        "phase2-extras", "phase2-only", "classify", "adaptive",
        "adaptive-adversarial", "adaptive-classifier-loop",
        "adversarial-injection", "adversarial-level", "adversarial-loop",
        "adversarial-bench", "adversarial-bench-count",
        "cfg-mutation", "cfg-mutation-variants", "class-dispatch",
        "class-dispatch-count", "ssa-mutation", "ssa-variants",
        "struct-randomization", "branch-entangle", "multicore-entangle",
        "randomization-level", "randomization-seed",
        "data-obfuscation", "data-obf-level", "speculation-obfuscation",
        "micro-fragment", "micro-fragment-size", "fragment",
        "fragment-size", "fragment-functions", "fragment-strings",
        "fragment-migration", "per-exec-recompile", "self-healing",
    }),
    ("Anti-analysis, counter-REA and deception", lambda f: f.startswith((
        "anti-rea", "exclude-rea", "poison-", "decoy-", "honey-",
        "reasoning-trap", "prompt-resistance", "attention-poison",
        "llm-", "multi-agent", "multi-tool", "storyline-", "trap-",
        "provenance-", "uaarch-", "uarch-",
    )) or f in {
        "anti-rea-level", "manipulation-detector", "false-confidence-audit",
        "self-critique", "independent-audit", "red-team", "red-team-output",
        "attack-corpus", "attack-store", "capture-attacks", "replay-attacks",
    }),
    ("Runtime integrity, anti-tamper and attestation", lambda f: f.startswith((
        "temporal-", "rolling-", "state-isa", "history-bound", "ephemeral-",
        "self-destruct", "anti-debug", "anti-vm",
    )) or f in {
        "attestation", "dist-attestation", "dist-attestation-nodes",
        "challenge-response", "crypto-binding", "snapshot", "no-snapshot",
        "stdlib-audit", "no-stdlib-audit", "audit-hook", "no-audit-hook-plant",
        "audit-drift", "audit-timing", "driver-check", "hostguard",
        "invariant-engine", "self-audit", "recovery-prevention",
        "recovery-prevention-nodes", "trust-boundary",
    }),
    ("Licensing, binding, watermarking and provenance", lambda f: f.startswith((
        "hwid", "watermark", "dist-watermark", "licence", "trial",
        "customer-", "name-gate", "rename-internal", "sign-",
        "provenance", "embed-proof", "zk-state", "remote-unlock",
    )) or f in {
        "watermark", "verify-watermark", "verify-watermark-survivability",
        "emit-certificates", "verify-preservation",
        "verify-preservation-formal",
    }),
    ("Packaging, loaders, native backends and build farm", lambda f: f.startswith((
        "pytoc", "pyinstaller", "simd-vm", "fhe-vm", "oram", "rop",
        "sgx", "tee", "zk-", "vm-", "jit", "nuitka", "docker",
        "section-", "split-", "microjit", "multi-binary", "multi-host",
        "distributed-", "dist-", "diversity", "gpu", "hpc", "cpu-",
        "kernel-assist", "uarch-diversity",
    )) or f in {
        "platform", "resume", "public", "tor", "tor-proxy", "exclude-android",
        "python", "native", "native-only", "remote-unlock-ttl",
        "crypto-binding", "emit-certificates",
    }),
    ("Verification, proofs and formal checking", lambda f: f.startswith((
        "verify-", "prove-", "proof-",
    )) or f in {
        "confidence-interval", "confidence-level", "gate-threshold",
        "min-resilience", "min-security", "reality-score",
        "reproducibility-score", "release-confidence", "evidence-completeness",
        "evidence-ledger", "verification-bundle", "verification-bundle-output",
        "verification-diversity", "claim-audit",
    }),
    ("Research, evaluation and reporting", lambda f: f.startswith((
        "benchmark", "evaluate", "eval-", "metrics", "report",
        "survivability", "analyst-time", "cost-model", "protection-roi",
        "security-debt", "security-gates", "threat-coverage",
        "feature-effectiveness", "semantic-leakage", "plaintext-exposure",
        "reachability-report", "coverage-", "dependency-graph",
        "knowledge-", "assumptions-report", "retirement-report",
        "longitudinal-tracking", "self-critique", "attack-surface",
        "runtime-truth", "adversarial-bench", "generate-artifacts",
        "artifacts-output", "synthesis", "evolution-", "genome-",
        "code-genome", "fingerprint", "classify-features", "io-research",
        "history-bound", "update-baseline", "synthesis-",
    ))),
]


def _help_text(target: str = "build") -> str:
    if target == "loader":
        cmd = [sys.executable, "-m", "obfuscator.core.pipeline", "build", "--help"]
    else:
        cmd = [sys.executable, os.path.join(ROOT, "scripts", "build.py"), "--help"]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=ROOT,
    )
    return proc.stdout


def parse_options(help_text: str) -> list[tuple[str, str, str]]:
    """Return [(flag_name_bare, invocation, description)] in parser order."""
    lines = help_text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == "options:")
    except StopIteration:
        start = 0
    body = lines[start + 1:]

    entries: list[list[str]] = []
    cur: list[str] | None = None
    for line in body:
        if re.match(r"^\s{2,}--?[a-zA-Z]", line):
            if cur:
                entries.append(cur)
            cur = [line.strip()]
        elif cur is not None and line.strip():
            cur.append(line.strip())
        elif cur is not None and not line.strip():
            entries.append(cur)
            cur = None
    if cur:
        entries.append(cur)

    out = []
    for e in entries:
        head = e[0]
        # "--opt-level {0,1,2}" or "-o, --output OUTPUT, -O OUTPUT"
        m = re.search(r"(?:^|,\s*)(--[a-z0-9][a-z0-9-]*)", head)
        if not m:
            continue
        flag = m.group(1)
        bare = flag[2:]
        # argparse puts the invocation, then two or more spaces, then the help
        # text on the same line, with any wrapping on continuation lines.
        inv, _, same_line = head.partition("  ")
        invocation = " ".join(inv.split())
        # Python 3.13 renders "-o, --output OUTPUT"; 3.10/3.11 render
        # "-o OUTPUT, --output OUTPUT". Normalise the multi-flag form so the
        # generated block does not depend on the interpreter that ran it.
        invocation = re.sub(
            r'^(-[A-Za-z]) ([A-Z][A-Z0-9_]*), (--[a-z0-9][a-z0-9-]*)',
            r'\1, \3',
            invocation,
        )
        desc_parts = [same_line.strip()] if same_line.strip() else []
        desc_parts.extend(e[1:])
        desc = " ".join(p for p in desc_parts if p)
        out.append((bare, invocation, desc))
    return out


def render(options: list[tuple[str, str, str]], start: str = START,
           end: str = END, producer: str = "scripts/build.py") -> str:
    seen: set[str] = set()
    buckets: dict[str, list[tuple[str, str, str]]] = {}
    for bare, invocation, desc in options:
        if bare in seen:
            continue
        seen.add(bare)
        for heading, pred in GROUPS:
            if pred(bare):
                buckets.setdefault(heading, []).append((bare, invocation, desc))
                break
        else:
            buckets.setdefault("Other", []).append((bare, invocation, desc))

    lines = [start, ""]
    lines.append(
        f"Every option `{producer}` accepts, generated from its own `--help` "
        "by\n`scripts/gen_cli_reference.py` and checked by "
        "`tests/test_readme_matches_cli.py`,\nso it cannot drift. "
        "Editorial notes are marked where a flag is inert or archived."
    )
    lines.append("")
    total = sum(len(v) for v in buckets.values())
    lines.append(f"**{total} options.**")
    lines.append("")

    order = [h for h, _ in GROUPS] + ["Other"]
    for heading in order:
        if heading not in buckets:
            continue
        lines.append(f"### {heading}")
        lines.append("")
        lines.append("| Option | What it does |")
        lines.append("|---|---|")
        for bare, invocation, desc in sorted(buckets[heading], key=lambda t: t[0]):
            note = NOTES.get(bare, "")
            d = (desc or "—").replace("|", "\\|")
            if note:
                d = f"{d} {note}" if d != "—" else note
            lines.append(f"| `{invocation}` | {d} |")
        lines.append("")
    lines.append(end)
    return "\n".join(lines)


#: Flags whose behaviour contradicts their name, or which no longer do work.
#: Kept here rather than in prose so the generated table carries the warning
#: next to the flag a reader is actually looking at.
NOTES = {
    "temporal-keys": (
        "**Inert and slow.** Derives a window key by ratcheting from epoch 0 to "
        "the current 60 s window (~19 s per build, growing every minute), then "
        "writes scheduling metadata that nothing reads. Its verifier "
        "(`verify_key_in_window`) only compares a timestamp against the key's own "
        "fields, so it proves nothing. No key material is written to disk."
    ),
    "crypto-binding": (
        "**Build-time only.** `verify_chain` decrypts the bound fragments during "
        "the build to validate them; nothing decrypts at run time. The chain "
        "secret is deliberately not written into `payload.h`."
    ),
    "randomization-seed": (
        "**Partial seeding only.** Seeds structure randomisation, speculation and "
        "the CPU-port phase; it does **not** make builds byte-reproducible, because "
        "the emitters draw thousands of values directly from `secrets` and several "
        "cross the pack/run boundary."
    ),
    "seed": (
        "**Reproducibility seed.** Seeds the global `random` module, the AST "
        "transformer's RNG and its `secrets` patch, and several injectors. With "
        "the same payload, tool version and flags, the source emitter is "
        "byte-identical. It does **not** make the packed loader reproducible, and "
        "it is not key material. `--skip-obfuscate` is the copy path."
    ),
    "build-id": (
        "**Lowering-kernel seed only.** Seeds the `--pytoc` semantic-lowering symbol "
        "map and is recorded in the manifest. It does not make the whole build "
        "reproducible, and a non-`--pytoc` build does not use it."
    ),
    "lock-hwid": (
        "**Not a whole-build seed.** Registers a licence for the target HWID and "
        "seeds the loader's polymorphic-map/VM RNG only; the blob and string keys "
        "remain random. The help text's 'seeds the build deterministically' is "
        "broader than the implementation."
    ),
    "pin-structure": (
        "**Structure only.** Pins emitter draws and the build timestamp; key "
        "material is not pinned, so artefacts are not byte-identical."
    ),
    "cfg-mutation": (
        "**Metadata-only.** The phase writes `cfg_mutation_config`/variants; the "
        "runtime module was archived and no component reads them. Not a runtime "
        "protection."
    ),
    "class-dispatch": (
        "**Metadata-only.** Writes `class_dispatch_config.json`; no runtime "
        "consumer. Not a runtime protection."
    ),
    "ssa-mutation": (
        "**Metadata-only.** Writes `ssa_mutation_variants.json`; no runtime "
        "consumer. Not a runtime protection."
    ),
    "state-isa": (
        "**Metadata-only.** Writes `state_isa_config.json`; no runtime consumer. "
        "Not a runtime protection."
    ),
    "per-exec-recompile": (
        "**Metadata-only.** Writes `per_exec_recompile_config.json`; no runtime "
        "consumer. Not a runtime protection."
    ),
    "self-healing": (
        "**Metadata-only.** Writes `self_healing_config.json`; the runtime module "
        "was archived and no component reads it. Not a runtime protection."
    ),
}


def splice(block: str, document: str, start: str = START,
           end: str = END) -> str:
    if start not in document or end not in document:
        raise SystemExit(f"the CLI document is missing the {start} / {end} markers")
    head, rest = document.split(start, 1)
    _, tail = rest.split(end, 1)
    return head + block + tail


BLOCKS = (
    ("build", START, END, "scripts/build.py"),
    ("loader", LOADER_START, LOADER_END,
     "python3 -m obfuscator.core.pipeline build"),
)


def main(argv: list[str]) -> int:
    built = []
    for target, start, end, producer in BLOCKS:
        options = parse_options(_help_text(target))
        built.append((target, start, end, options,
                      render(options, start, end, producer)))

    if "--check" in argv:
        document = open(CLI_DOC, encoding="utf-8").read()
        stale = []
        for target, start, end, options, block in built:
            if start not in document or end not in document:
                print(f"CLI.md has no {target} reference markers")
                return 1
            current = start + document.split(start, 1)[1].split(end, 1)[0] + end
            if current.strip() != block.strip():
                stale.append(target)
        if stale:
            print("stale references: %s; run "
                  "python3 scripts/gen_cli_reference.py --write" % ", ".join(stale))
            return 1
        print("CLI references are current (%s)" %
              ", ".join(f"{t}: {len(o)}" for t, _, _, o, _ in built))
        return 0

    if "--write" in argv:
        document = open(CLI_DOC, encoding="utf-8").read()
        for target, start, end, options, block in built:
            document = splice(block, document, start, end)
        open(CLI_DOC, "w", encoding="utf-8").write(document)
        print("wrote " + ", ".join(f"{t}: {len(o)}" for t, _, _, o, _ in built))
        return 0

    for _t, _s, _e, _o, block in built:
        print(block)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
