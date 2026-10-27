"""manifest.py

Purpose:
    Record what a build actually put in the artefact, so the feature
    report can be generated from evidence instead of from names.

Architectural Role:
    ``scripts/classify_features.py`` answers five questions per
    feature; this module supplies the evidence for the fifth
    ("exercised"): the built artefact's own contents.

    The manifest is intentionally mechanical — file hashes, exported
    symbols, gate markers grepped out of the emitted loader, the Rust
    modules compiled and the runtime flags set.  Nothing here is a
    claim about design intent.

Security Relevance:
    A report that says a protection is live when the artefact does not
    contain it is worse than no report.  The manifest makes the
    difference checkable, and the build fails when a claimed-live
    feature has no evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess

MANIFEST_NAME = "artefact_manifest.json"

# Exported symbols that mean the C backend is genuinely present.
C_SYMBOL_MARKERS = (
    "FHE_new", "FHE_encrypt_batch", "FHE_add_batch", "FHE_dec_batch",
    "FHE_free_array", "ORAM_new", "ORAM_access",
)

def manifest_path(build_dir: str) -> str:
    return os.path.join(build_dir, MANIFEST_NAME)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def loader_gates(loader_path: str) -> list:
    """Gates we can actually prove are in the artefact.

    The per-build hardening renames the loader's own symbols each build
    (Hardening A2.1/A2.2), so the old `_nx_<name>_gate` markers this
    used to grep for no longer exist — the manifest reported zero gates
    on a perfectly good artefact.  What survives the renaming is
    behaviour: an HMAC over the payload, and an integrity verification
    step.  Only those two are claimed; saying more would be guessing at
    a symbol name.

    Absence is meaningful for these two, which is why they are worth
    reporting at all.
    """
    text = _read(loader_path)
    if not text:
        return []
    out = set()
    if re.search(r"\bhmac\b", text, re.IGNORECASE):
        out.add("payload_mac")
    if re.search(r"\b_nx_verify\b", text) or "INTERP_HASH" in text:
        out.add("self_integrity")
    return sorted(out)


def c_symbols(so_path: str) -> list:
    """Exported symbols of a shared object, filtered to the FHE/ORAM ABI."""
    if not os.path.exists(so_path):
        return []
    try:
        out = subprocess.run(["nm", "-D", "--defined-only", so_path],
                             capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    present = [s for s in C_SYMBOL_MARKERS if s in out]
    return present


def rust_state() -> dict:
    """The Rust modules compiled and the flags the relay can set."""
    try:
        from scripts.reachability import rust_callgraph as cg
    except ImportError:
        return {"modules": [], "reachable": [], "flags_enabled": []}
    return {
        "modules": sorted(cg.module_declarations()),
        "reachable": sorted(cg.reachable_modules()),
        "flags_enabled": sorted(cg.default_true_flags() | cg.flags_set_true_elsewhere()),
    }


def collect(build_dir: str, artefact_path: str | None = None) -> dict:
    """Build the manifest for what is currently on disk."""
    artefact_path = artefact_path or os.path.join(build_dir, "obfuscated.py")
    gates = loader_gates(artefact_path)
    so = os.path.join(build_dir, "nixon_core.so")
    syms = c_symbols(so)
    rust = rust_state()

    features = set(gates)
    features |= {s.lower() for s in syms}
    # Rust features are only "exercised" if the module is reachable AND
    # the flag that gates it is on.
    for mod in rust["reachable"]:
        if ("enable_" + mod) in rust["flags_enabled"]:
            features.add(mod)

    return {
        "artefact": {
            "path": os.path.relpath(artefact_path, build_dir) if os.path.exists(artefact_path) else None,
            "exists": os.path.exists(artefact_path),
            "sha256": _sha256(artefact_path) if os.path.exists(artefact_path) else "",
            "size": os.path.getsize(artefact_path) if os.path.exists(artefact_path) else 0,
        },
        "loader_gates": gates,
        "c_symbols": syms,
        "rust": rust,
        "features": sorted(features),
    }


def write_manifest(build_dir: str, artefact_path: str | None = None) -> str:
    """Collect and write the manifest; returns its path."""
    data = collect(build_dir, artefact_path)
    path = manifest_path(build_dir)
    os.makedirs(build_dir, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)
    return path
