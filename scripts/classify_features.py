#!/usr/bin/env python3
"""Phase 5: Claim Validation — Classify all 129 protection/research features."""
# TWIN: scripts/classification/ (function_classifier.py AST-level function
# triage + strategy_selector.py pass selection) — that package classifies
# CODE to pick protections; this script classifies FEATURES to validate
# claims. Different input, different output; do not merge.
import argparse
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(ROOT, "build")
sys.path.insert(0, ROOT)


def _load_build_py():
    with open(os.path.join(ROOT, "scripts", "build.py")) as f:
        return f.read()


BUILD_PY = _load_build_py()

import re as _re  # noqa: E402

_ADD_ARG = _re.compile(r"parser\.add_argument\s*\(")
# build.py with its argument declarations removed: only flag CONSUMERS.
_BUILD_CONSUMPTION = None
_CONSUMERS = None

ALL_PHASE_FILES = set()
pd = os.path.join(ROOT, "scripts", "phases")
if os.path.isdir(pd):
    for f in os.listdir(pd):
        if f.endswith(".py") and f != "__init__.py":
            ALL_PHASE_FILES.add(f.replace(".py", ""))


def _strip_argument_definitions(text):
    """Remove every ``parser.add_argument(...)`` call from build.py.

    What is left is the code that CONSUMES the flags.  Checking for
    ``opts.<name>`` alone gives false "not wired" results, because a
    flag is often consumed through a mapping dict (``--fragment-strings``
    is used as ``{'fragment_strings': ...}``), and a flag can be
    declared with a ``dest`` that differs from its name.
    """
    out = []
    i = 0
    while True:
        m = _ADD_ARG.search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i:m.start()])
        depth = 0
        k = m.end() - 1
        while k < len(text):
            if text[k] == "(":
                depth += 1
            elif text[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        i = k + 1
    return "".join(out)


def _find_argument_call(flag):
    """The ``parser.add_argument(...)`` call that declares ``flag``."""
    i = 0
    while True:
        m = _ADD_ARG.search(BUILD_PY, i)
        if not m:
            return None
        depth = 0
        k = m.end() - 1
        while k < len(BUILD_PY):
            if BUILD_PY[k] == "(":
                depth += 1
            elif BUILD_PY[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        call = BUILD_PY[m.start():k + 1]
        if _re.search(r"[\"']%s[\"']" % _re.escape(flag), call):
            return call
        i = k + 1


def _dest_of(call, flag):
    """The argparse dest a flag binds to."""
    if not call:
        return flag.lstrip("-").replace("-", "_")
    m = _re.search(r"dest\s*=\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']", call)
    if m:
        return m.group(1)
    opts = _re.findall(r"[\"'](--[A-Za-z0-9_-]+)[\"']", call)
    name = flag if flag in opts else (opts[0] if opts else flag)
    return name.lstrip("-").replace("-", "_")


def cli_exists(flag):
    return flag in BUILD_PY


def wired(flag):
    """Is the flag's value consumed anywhere outside its declaration?

    Checking for ``opts.<name>`` alone gives false "not wired" results:
    flags are also consumed through config dicts
    (``--fragment-strings`` -> ``{'fragment_strings': ...}``) and
    through helpers named after them
    (``--advanced-protection`` -> ``load_advanced_protection_config``).
    So: resolve the real ``dest``, then look for it anywhere in the
    consumer side of build.py.
    """
    return _name_in_use(_dest_of(_find_argument_call(flag), flag))


def _consumer_text():
    """Everything that could consume a flag's value.

    ``build.py`` minus its argument declarations, plus every phase and
    package module — because ``opts`` is passed wholesale into the
    phases, so a flag is often consumed there and never named in
    build.py.  Checking build.py alone reported eight wired flags as
    unwired.

    ``feature_map.py`` is excluded: it lists feature names as metadata
    and consuming nothing.
    """
    global _CONSUMERS
    if _CONSUMERS is not None:
        return _CONSUMERS
    parts = [_strip_argument_definitions(BUILD_PY)]
    skip = {"feature_map.py"}
    for base in (os.path.join(ROOT, "scripts"), os.path.join(ROOT, "obfuscator")):
        for dirpath, _dirnames, filenames in os.walk(base):
            if "__pycache__" in dirpath:
                continue
            for fn in filenames:
                if fn.endswith(".py") and fn not in skip:
                    parts.append(_read_file_text(os.path.join(dirpath, fn)))
    _CONSUMERS = "\n".join(parts)
    return _CONSUMERS


def _read_file_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _name_in_use(name):
    # Substring, deliberately: a flag's value is consumed as
    # opts.<dest>, as cfg['<dest>'], and as part of a helper name
    # (load_advanced_protection_config). A word-boundary match would
    # miss the third and report a wired flag as unwired.
    return name in _consumer_text()


def phase_exists(name):
    name = name.lower().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")
    for pf in ALL_PHASE_FILES:
        if name in pf or pf in name:
            return True
    return False


FEATURES = [
    {"id": 1, "name": "CFG Flattening", "category": "Core Pipeline", "cli_flag": "--cfg-flatten"},
    {"id": 2, "name": "Opaque Predicates", "category": "Core Pipeline", "cli_flag": "--opaque-predicates"},
    {"id": 3, "name": "Bogus Exceptions", "category": "Core Pipeline", "cli_flag": "--bogus-exceptions"},
    {"id": 4, "name": "MBA Substitutions", "category": "Core Pipeline", "cli_flag": "--mba-subs"},
    {"id": 5, "name": "String Fragmentation", "category": "Core Pipeline", "cli_flag": "--fragment-strings"},
    {"id": 6, "name": "Unicode Identifiers", "category": "Core Pipeline", "cli_flag": "--unicode-ids"},
    {"id": 7, "name": "SMT Validation", "category": "Core Pipeline", "cli_flag": "--validate"},
    {"id": 8, "name": "Advanced Protection", "category": "Core Pipeline", "cli_flag": "--advanced-protection"},
    {"id": 9, "name": "Phase 2", "category": "Core Pipeline", "cli_flag": "--phase2"},
    {"id": 10, "name": "Classification Pass", "category": "Core Pipeline", "cli_flag": "--classify"},
    {"id": 11, "name": "Adaptive Protection", "category": "Core Pipeline", "cli_flag": "--adaptive"},
    {"id": 12, "name": "Cross-Compile", "category": "Core Pipeline", "cli_flag": "--cross"},
    {"id": 13, "name": "Payload Header Gen", "category": "Core Pipeline", "cli_flag": "--generate-payload-h"},
    {"id": 14, "name": "Skip Obfuscate", "category": "Core Pipeline", "cli_flag": "--skip-obfuscate"},
    {"id": 15, "name": "Skip IR Gen", "category": "Core Pipeline", "cli_flag": "--skip-irgen"},
    {"id": 16, "name": "Skip LLVM Gen", "category": "Core Pipeline", "cli_flag": "--skip-llvmgen"},
    {"id": 17, "name": "Skip Encrypt", "category": "Core Pipeline", "cli_flag": "--skip-encrypt"},
    {"id": 18, "name": "Skip Relay", "category": "Core Pipeline", "cli_flag": "--skip-relay"},
    {"id": 19, "name": "Skip Extras", "category": "Core Pipeline", "cli_flag": "--skip-extras"},
    {"id": 20, "name": "Include Original", "category": "Core Pipeline", "cli_flag": "--include-original"},
    {"id": 21, "name": "Phase 2 Extras", "category": "Core Pipeline", "cli_flag": "--phase2-extras"},
    {"id": 22, "name": "Adversarial Injection", "category": "Core Pipeline", "cli_flag": "--adversarial-injection"},
    {"id": 23, "name": "Adversarial Loop", "category": "Core Pipeline", "cli_flag": "--adversarial-loop"},
    {"id": 24, "name": "Ephemeral ISA", "category": "Core Pipeline", "cli_flag": "--ephemeral-isa"},
    {"id": 25, "name": "MicroJIT", "category": "Core Pipeline", "cli_flag": "--microjit"},
    {"id": 26, "name": "Fragment Reassembly", "category": "Core Pipeline", "cli_flag": "--fragment"},
    {"id": 27, "name": "Cost Optimizer", "category": "Core Pipeline", "cli_flag": "--optimize"},
    {"id": 28, "name": "Provenance Poisoning", "category": "Core Pipeline", "cli_flag": "--provenance-poison"},
    {"id": 29, "name": "Data Obfuscation", "category": "Core Pipeline", "cli_flag": "--data-obfuscation"},
    {"id": 30, "name": "Semantic Watermarking", "category": "Core Pipeline", "cli_flag": "--watermark"},
    {"id": 31, "name": "Watermark Verification", "category": "Core Pipeline", "cli_flag": "--verify-watermark"},
    {"id": 32, "name": "Emit Certificates", "category": "Core Pipeline", "cli_flag": "--emit-certificates"},
    {"id": 33, "name": "Embed Proof", "category": "Core Pipeline", "cli_flag": "--embed-proof"},
    {"id": 34, "name": "Verify MBA", "category": "Core Pipeline", "cli_flag": "--verify-mba"},
    {"id": 35, "name": "Verify Preservation", "category": "Core Pipeline", "cli_flag": "--verify-preservation"},
    {"id": 36, "name": "Metrics Collection", "category": "Core Pipeline", "cli_flag": "--metrics"},
    {"id": 37, "name": "Diversity Generation", "category": "Core Pipeline", "cli_flag": "--diversity"},
    {"id": 38, "name": "ORAM Controller", "category": "Core Pipeline", "cli_flag": "--oram"},
    {"id": 39, "name": "ROP Compilation", "category": "Core Pipeline", "cli_flag": "--rop"},
    {"id": 40, "name": "Attestation Engine", "category": "Core Pipeline", "cli_flag": "--attestation"},
    {"id": 41, "name": "Crypto Binding", "category": "Core Pipeline", "cli_flag": "--crypto-binding"},
    {"id": 42, "name": "LLM-Resilient Obfuscation", "category": "Core Pipeline", "cli_flag": "--llm-resilient"},
    {"id": 43, "name": "Benchmark", "category": "Core Pipeline", "cli_flag": "--benchmark"},
    {"id": 44, "name": "IR Compilation", "category": "Core Pipeline", "cli_flag": "(phase)"},
    {"id": 45, "name": "LLVM Codegen", "category": "Core Pipeline", "cli_flag": "(phase)"},
    {"id": 46, "name": "Binary Encryption", "category": "Core Pipeline", "cli_flag": "(phase)"},
    {"id": 47, "name": "Relay Build", "category": "Core Pipeline", "cli_flag": "(phase)"},
    {"id": 48, "name": "Packaging", "category": "Core Pipeline", "cli_flag": "(phase)"},
    {"id": 49, "name": "Entropy Flatten", "category": "Core Pipeline", "cli_flag": "(internal)"},
    {"id": 50, "name": "Runtime Manifest", "category": "Core Pipeline", "cli_flag": "(internal)"},
    {"id": 51, "name": "Provenance Removal", "category": "Core Pipeline", "cli_flag": "(phase2)"},
    {"id": 52, "name": "Dataflow Obfuscation", "category": "Core Pipeline", "cli_flag": "(phase2)"},
    {"id": 53, "name": "Variant Pool", "category": "Core Pipeline", "cli_flag": "(phase2)"},
    {"id": 54, "name": "VM Compile", "category": "Core Pipeline", "cli_flag": "(phase2)"},
    {"id": 55, "name": "JIT Templates", "category": "Core Pipeline", "cli_flag": "(phase2)"},
    {"id": 56, "name": "Watermark Embedding", "category": "Core Pipeline", "cli_flag": "(phase2)"},
    {"id": 57, "name": "Semantic Fragmentation", "category": "Core Pipeline", "cli_flag": "(phase2)"},
    {"id": 58, "name": "Honey Functions", "category": "Core Pipeline", "cli_flag": "--honey-functions"},
    {"id": 59, "name": "Optional Extras", "category": "Core Pipeline", "cli_flag": "(phase)"},
    {"id": 60, "name": "Unified Evaluation", "category": "Core Pipeline", "cli_flag": "--evaluate"},
    {"id": 61, "name": "Min Resilience", "category": "Core Pipeline", "cli_flag": "--min-resilience"},
    {"id": 62, "name": "Benchmark Report", "category": "Core Pipeline", "cli_flag": "--benchmark-report"},
    {"id": 63, "name": "Diversity Report", "category": "Core Pipeline", "cli_flag": "--diversity-report"},
    {"id": 64, "name": "SMT Validate Fail", "category": "Core Pipeline", "cli_flag": "--validate-fail"},
    {"id": 65, "name": "Advanced Protection Only", "category": "Core Pipeline", "cli_flag": "--advanced-protection-only"},
    {"id": 66, "name": "Phase 2 Only", "category": "Core Pipeline", "cli_flag": "--phase2-only"},
    {"id": 67, "name": "Adversarial Level", "category": "Core Pipeline", "cli_flag": "--adversarial-level"},
    {"id": 68, "name": "Fragment Functions", "category": "Core Pipeline", "cli_flag": "--fragment-functions"},
    {"id": 69, "name": "Fragment Size", "category": "Core Pipeline", "cli_flag": "--fragment-size"},
    {"id": 70, "name": "Attention Poison", "category": "LLM Deception", "cli_flag": "--attention-poison"},
    {"id": 71, "name": "Provenance Storylines", "category": "LLM Deception", "cli_flag": "--multi-agent-deception"},
    {"id": 72, "name": "Decoy APIs", "category": "LLM Deception", "cli_flag": "--decoy-apis"},
    {"id": 73, "name": "LLM Fingerprint", "category": "LLM Deception", "cli_flag": "--llm-fingerprint"},
    {"id": 74, "name": "Adaptive Adversarial Rewriting", "category": "LLM Deception", "cli_flag": "--adaptive-adversarial"},
    {"id": 75, "name": "Reasoning Traps", "category": "LLM Deception", "cli_flag": "--reasoning-traps"},
    {"id": 76, "name": "Context Saturation", "category": "LLM Deception", "cli_flag": "--context-saturation"},
    {"id": 77, "name": "Prompt Resistance", "category": "LLM Deception", "cli_flag": "--prompt-resistance"},
    {"id": 78, "name": "Function Intent", "category": "LLM Deception", "cli_flag": "--function-intent"},
    {"id": 79, "name": "AI-Guided Diversity", "category": "LLM Deception", "cli_flag": "--ai-guided-diversity"},
    {"id": 80, "name": "CFG Mutation", "category": "Runtime Evolution", "cli_flag": "--cfg-mutation"},
    {"id": 81, "name": "Class Dispatch", "category": "Runtime Evolution", "cli_flag": "--class-dispatch"},
    {"id": 82, "name": "Rolling Keys", "category": "Runtime Evolution", "cli_flag": "--rolling-keys"},
    {"id": 83, "name": "SSA Mutation", "category": "Runtime Evolution", "cli_flag": "--ssa-mutation"},
    {"id": 84, "name": "State ISA", "category": "Runtime Evolution", "cli_flag": "--state-isa"},
    {"id": 85, "name": "Per-Exec Recompile", "category": "Runtime Evolution", "cli_flag": "--per-exec-recompile"},
    {"id": 86, "name": "Self-Healing", "category": "Runtime Evolution", "cli_flag": "--self-healing"},
    {"id": 87, "name": "Code Genome", "category": "Runtime Evolution", "cli_flag": "--code-genome"},
    {"id": 88, "name": "Structure Randomization", "category": "Runtime Evolution", "cli_flag": "--struct-randomization"},
    {"id": 89, "name": "History-Bound Decryption", "category": "Runtime Evolution", "cli_flag": "--history-bound-decryption"},
    {"id": 90, "name": "Proof Automata", "category": "Formal Security", "cli_flag": "(internal)"},
    {"id": 91, "name": "Fragment Safety", "category": "Formal Security", "cli_flag": "--prove-fragments"},
    {"id": 92, "name": "VM Correctness", "category": "Formal Security", "cli_flag": "--prove-vm"},
    {"id": 93, "name": "Fragment Safety Proofs", "category": "Formal Security", "cli_flag": "--prove-fragments"},
    {"id": 94, "name": "Pipeline Preservation", "category": "Formal Security", "cli_flag": "--verify-preservation"},
    {"id": 95, "name": "Watermark Survivability", "category": "Formal Security", "cli_flag": "--verify-watermark-survivability"},
    {"id": 96, "name": "Mutation Safety", "category": "Formal Security", "cli_flag": "--verify-mutations"},
    {"id": 97, "name": "JIT Correctness", "category": "Formal Security", "cli_flag": "--verify-jit"},
    {"id": 98, "name": "Composition Safety", "category": "Formal Security", "cli_flag": "(internal)"},
    {"id": 99, "name": "Proof-Aware Optimizer", "category": "Formal Security", "cli_flag": "--proof-aware-optimizer"},
    {"id": 100, "name": "Cost Model", "category": "Evaluation Research", "cli_flag": "--cost-model"},
    {"id": 101, "name": "Multi-Tool", "category": "Evaluation Research", "cli_flag": "--multi-tool"},
    {"id": 102, "name": "Survivability Index", "category": "Evaluation Research", "cli_flag": "--survivability"},
    {"id": 103, "name": "Difficulty Curves", "category": "Evaluation Research", "cli_flag": "(none)"},
    {"id": 104, "name": "Economic Model", "category": "Evaluation Research", "cli_flag": "(none)"},
    {"id": 105, "name": "Calibration Data", "category": "Evaluation Research", "cli_flag": "(none)"},
    {"id": 106, "name": "Angr Benchmark", "category": "Evaluation Research", "cli_flag": "(none)"},
    {"id": 107, "name": "Ghidra Benchmark", "category": "Evaluation Research", "cli_flag": "(none)"},
    {"id": 108, "name": "Binary Ninja Benchmark", "category": "Evaluation Research", "cli_flag": "(none)"},
    {"id": 109, "name": "Evaluation Summary", "category": "Evaluation Research", "cli_flag": "--eval-summary"},
    {"id": 110, "name": "Multi-Binary", "category": "Distributed Protection", "cli_flag": "--multi-binary"},
    {"id": 111, "name": "Cross-Process", "category": "Distributed Protection", "cli_flag": "--cross-process"},
    {"id": 112, "name": "Remote Unlock", "category": "Distributed Protection", "cli_flag": "--remote-unlock"},
    {"id": 113, "name": "Distributed VM", "category": "Distributed Protection", "cli_flag": "--distributed-vm"},
    {"id": 114, "name": "Multi-Host", "category": "Distributed Protection", "cli_flag": "--multi-host"},
    {"id": 115, "name": "Fragment Migration", "category": "Distributed Protection", "cli_flag": "--fragment-migration"},
    {"id": 116, "name": "Distributed Attestation", "category": "Distributed Protection", "cli_flag": "--dist-attestation"},
    {"id": 117, "name": "Distributed Watermark", "category": "Distributed Protection", "cli_flag": "--dist-watermark"},
    {"id": 118, "name": "Distributed Diversity", "category": "Distributed Protection", "cli_flag": "--dist-diversity"},
    {"id": 119, "name": "Recovery Prevention", "category": "Distributed Protection", "cli_flag": "--recovery-prevention"},
    {"id": 120, "name": "HPC Integration", "category": "Hardware Research", "cli_flag": "--hpc"},
    {"id": 121, "name": "HPC Key Derivation", "category": "Hardware Research", "cli_flag": "--hpc-key"},
    {"id": 122, "name": "Emulator Detection", "category": "Hardware Research", "cli_flag": "--hpc-detect"},
    {"id": 123, "name": "Hardware Entropy", "category": "Hardware Research", "cli_flag": "--hw-entropy"},
    {"id": 124, "name": "Cache-Bound Execution", "category": "Hardware Research", "cli_flag": "--cache-bound"},
    {"id": 125, "name": "Branch Entanglement", "category": "Hardware Research", "cli_flag": "--branch-entangle"},
    {"id": 126, "name": "Multi-Core Entanglement", "category": "Hardware Research", "cli_flag": "--multicore-entangle"},
    {"id": 127, "name": "TEE Partition", "category": "Hardware Research", "cli_flag": "--tee"},
    {"id": 128, "name": "SGX Enclave", "category": "Hardware Research", "cli_flag": "--sgx"},
    {"id": 129, "name": "CPU Port / GPU Hybrid", "category": "Hardware Research", "cli_flag": "--cpu-port"},
]


# --- evidence dimensions -------------------------------------------------
#
# The old classifier answered one question ("does a file with a similar
# name exist?") and then returned IMPLEMENTED for everything.  A
# protection is only real if it is implemented, compiled, REACHABLE
# from the entry point, ENABLED, and EXERCISED in the artefact.  Each
# dimension is now separate, and the verdict names the gap.

from scripts.reachability import rust_callgraph as _cg  # noqa: E402

RUST_DECLARED = _cg.module_declarations()
RUST_REACHABLE = _cg.reachable_modules()
RUST_FLAG_BLOCKS = _cg.flag_blocks()
RUST_DEFAULT_TRUE = _cg.default_true_flags()
RUST_SET_ELSEWHERE = _cg.flags_set_true_elsewhere()
RUST_FLAGS = _cg.config_flags()


def _slug(name):
    import re as _re
    return _re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _rust_flag(name):
    """The RuntimeConfig flag gating a feature, if it has one."""
    flag = "enable_" + _slug(name)
    return flag if flag in RUST_FLAGS else None


def _rust_module_missing(flag, slug):
    """The module files the flag references that do not exist."""
    import os as _os
    modules = RUST_FLAG_BLOCKS.get(flag) or ({slug} if slug in RUST_DECLARED else set())
    missing = []
    for m in modules:
        if not _os.path.exists(_os.path.join(ROOT, "runtime", "src", m + ".rs")):
            missing.append(m)
    return missing


def gather_evidence(f):
    """Five independent dimensions, each mechanically answerable."""
    name = f["name"]
    flag = f["cli_flag"]
    slug = _slug(name)
    internal = flag in ("(internal)", "(phase)", "(phase2)", "(none)")

    ev = {
        # 1. implemented: a module/phase/flag for it exists
        "implemented": internal or cli_exists(flag) or phase_exists(name)
                        or (slug in RUST_DECLARED),
        # 2. compiled: Python is never compiled; Rust/C must exist as code
        "compiled": True,
        # 3. reachable: a call path exists from the entry point
        "reachable": True,
        # 4. enabled: nothing gates it off at run time
        "enabled": True,
        # 5. exercised: the built artefact shows it ran (None = no build)
        "exercised": None,
        "reason": "",
    }

    rust_flag = _rust_flag(name)
    if rust_flag:
        missing = _rust_module_missing(rust_flag, slug)
        ev["compiled"] = not missing
        # A handler in init_runtime AND the module in the closure.
        has_handler = rust_flag in RUST_FLAG_BLOCKS
        in_closure = bool((RUST_FLAG_BLOCKS.get(rust_flag) or {slug}) & RUST_REACHABLE)
        ev["reachable"] = has_handler and in_closure
        ev["enabled"] = rust_flag in RUST_DEFAULT_TRUE or rust_flag in RUST_SET_ELSEWHERE
        if not has_handler:
            ev["reason"] = "no handler in init_runtime for %s" % rust_flag
        elif not in_closure:
            ev["reason"] = "gated by %s but not in init_runtime's call graph" % rust_flag
        elif not ev["enabled"]:
            ev["reason"] = "%s is false in RuntimeConfig::default and nothing sets it" % rust_flag
        elif missing:
            ev["reason"] = "module missing: %s" % ", ".join(missing)
    else:
        # A Python feature: "reachable" means the flag is actually wired.
        if not internal:
            ev["reachable"] = wired(flag)
            if not ev["reachable"] and cli_exists(flag):
                ev["reason"] = "flag %s exists but is not wired into the build" % flag

    manifest = _ARTEFACT_MANIFEST
    if manifest is not None:
        ev["exercised"] = _manifest_lists(manifest, f, slug, rust_flag)

    return ev


def classify(ev):
    """Name the gap, do not paper over it."""
    if not ev["implemented"]:
        return "DEAD CODE"
    if not ev["compiled"]:
        return "DEAD CODE"
    if not ev["reachable"]:
        return "COMPILED-UNREACHABLE"
    if not ev["enabled"]:
        return "GATED-OFF"
    if ev["exercised"] is False:
        return "ENABLED-UNEXERCISED"
    if ev["exercised"] is None:
        return "LIVE (unverified)"
    return "LIVE"


_ARTEFACT_MANIFEST = None


def _manifest_lists(manifest, feat, slug, rust_flag):
    """Does the build's artefact manifest show this feature ran?"""
    names = {str(n).lower() for n in manifest.get("features", [])}
    if slug in names or feat["name"].lower() in names:
        return True
    if rust_flag and rust_flag in names:
        return True
    # A manifest that exists but does not list the feature is evidence
    # that it did not run.
    return False


def load_artefact_manifest(path):
    """Read the manifest the build emits next to the artefact."""
    global _ARTEFACT_MANIFEST
    try:
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, dict):
            _ARTEFACT_MANIFEST = data
            return data
    except (OSError, ValueError):
        pass
    _ARTEFACT_MANIFEST = None
    return None


CLASSES = ["LIVE", "LIVE (unverified)", "ENABLED-UNEXERCISED", "GATED-OFF",
           "COMPILED-UNREACHABLE", "DEAD CODE"]


def build_report():
    results = []
    counts = {c: 0 for c in CLASSES}
    for feat in FEATURES:
        ev = gather_evidence(feat)
        cls = classify(ev)
        counts.setdefault(cls, 0)
        counts[cls] += 1
        results.append({
            "id": feat["id"],
            "name": feat["name"],
            "category": feat["category"],
            "cli_flag": feat["cli_flag"],
            "classification": cls,
            "live_in_artifact": cls == "LIVE",
            "reason": ev.pop("reason", ""),
            "evidence": ev,
        })
    return {
        "report_version": "2.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artefact_manifest": bool(_ARTEFACT_MANIFEST),
        "summary": {"total": len(FEATURES), **{c.lower().replace(" ", "_").replace("(", "").replace(")", ""): n
                                               for c, n in counts.items()}},
        "features": results,
    }


def print_summary(report):
    s = report["summary"]
    print(f"\n{'=' * 68}")
    print("  FEATURE CLASSIFICATION REPORT (evidence-based)")
    print(f"{'=' * 68}")
    print(f"  Total features: {s['total']}")
    for c in CLASSES:
        key = c.lower().replace(" ", "_").replace("(", "").replace(")", "")
        print(f"  {c:24s} {s.get(key, 0):3d}")
    if not report.get("artefact_manifest"):
        print("\n  NOTE: no artefact manifest — 'exercised' is unverified.")
        print("        Build with --classify-features and pass --from-build.")
    print(f"{'=' * 68}")
    for c in CLASSES:
        rows = [f for f in report["features"] if f["classification"] == c]
        if not rows or c == "LIVE":
            continue
        print(f"\n  {c}:")
        for f in rows:
            line = f"    Item {f['id']:3d}  {f['name']:32s} ({f['category']})"
            print(line)
            if f.get("reason"):
                print(f"         {f['reason']}")
    print()


def write_json(report, path):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  Report written -> {path}")


def main():
    parser = argparse.ArgumentParser(description="Classify all protection/research features")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    parser.add_argument("--report", action="store_true", help="Output human-readable summary to stdout")
    parser.add_argument("--output", default=None, help="Path for JSON output file")
    parser.add_argument("--from-build", default=None,
                        help="Build dir holding artefact_manifest.json (makes 'exercised' checkable)")
    parser.add_argument("--require-live", default=None, metavar="N",
                        help="Exit non-zero unless at least N features are LIVE")
    opts = parser.parse_args()

    if opts.from_build:
        from scripts.artifacts.manifest import manifest_path
        load_artefact_manifest(manifest_path(opts.from_build))

    report = build_report()
    if opts.json:
        print(json.dumps(report, indent=2))
    elif opts.output:
        write_json(report, opts.output)
        print_summary(report)
    elif opts.report:
        print_summary(report)
    else:
        write_json(report, os.path.join(BUILD_DIR, "feature_classification.json"))
        print_summary(report)

    if opts.require_live is not None:
        live = report["summary"].get("live", 0)
        need = int(opts.require_live)
        if live < need:
            print(f"FAIL: {live} LIVE feature(s), {need} required", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())


if __name__ == "__main__":
    main()
