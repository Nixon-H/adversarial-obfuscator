"""Randomized fixed-literal residue pass (Batch C GAP 2, #28).

Fixed literal tokens baked into every build (marker names, version tags,
separator strings, padding constants, header magic, section names, error
strings, nonce labels) are a cross-build signature: identical literals in
two artifacts prove common provenance. This pass replaces 8 families of
such literals with per-build randomized equivalents derived from
SHA-256(seed), keeping a build-side map so the runtime still resolves.

The simplest correct approach — consistent with the existing babel-name
randomization (name_gate.build_mapping) — is: rename internal marker
CONSTANTS consistently. The map records {family: {original: randomized}}
so callers/tests can resolve runtime tokens back to canonical families.

Design (additive, default ON, deterministic under seed):
- ``RESIDUE_FAMILIES``: 8 token families with canonical literals.
- ``build_residue_map(seed)``: deterministic {family: {orig: token}}.
- ``apply_residue(source, seed_or_map, enabled=True)``: string-level
  whole-token replacement on the assembled payload text. Whole-token
  (regex word-boundary or exact) replacement avoids corrupting
  substrings; disabled (enabled=False) or empty source is a no-op.
- ``pipeline.build_pipeline`` wires it: after payload assembly
  (post-apply_ast_mutation, pre-return) with options key
  ``residue_random`` (default True) and ``residue_seed`` (defaults to
  the transform seed). Never breaks: guarded try/except at the call
  site, no-op when disabled.

Python 3.10 compatible: no match statements, no X|Y annotations.
"""

from __future__ import annotations

import hashlib
import random
import re
from typing import Dict, Optional, Tuple, Union

# 8 fixed-literal token families. Canonical literals are the stable
# strings that would otherwise appear verbatim in every artifact.
RESIDUE_FAMILIES: Dict[str, Tuple[str, ...]] = {
    # Internal runtime marker names (loader/payload coordination).
    "markers": (
        "_NX_BUILD_ID",
        "_NX_HWID_LOCK",
        "_NX_HWID_STATIC",
        "_NX_TRIAL_GATE",
        "_NX_KOD_ARMED",
        "_NX_VM_THRESHOLD",
    ),
    # Version tags embedded in headers/envelopes.
    "versions": (
        "NYS1",
        "NIXON-OBF-V1",
        "NX-ARTIFACT-1",
    ),
    # Separator strings used when joining/splitting envelopes.
    "separators": (
        "::NX::",
        "|NX|",
        "--NX-SEP--",
    ),
    # Padding constants used to align sections/blobs.
    "padding": (
        "NX_PAD_16",
        "NX_PAD_64",
        "NX_ZERO_FILL",
    ),
    # Header magic prefixes on emitted blobs.
    "magic": (
        "NXH1",
        "NXBLOB1",
        "NXSEC1",
    ),
    # Section names in split/sealed streaming envelopes.
    "sections": (
        "NX_SEC_HDR",
        "NX_SEC_BODY",
        "NX_SEC_TAIL",
    ),
    # Error strings raised on integrity failure paths.
    "errors": (
        "NX_INTEGRITY_FAIL",
        "NX_TAMPER_DETECTED",
        "NX_DECRYPT_FAIL",
    ),
    # Nonce/key labels in emitted key-share envelopes.
    "nonces": (
        "NX_NONCE_A",
        "NX_NONCE_B",
        "NX_KEY_SHARE",
    ),
}

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _rand_token(rng: random.Random, prefix: str = "_nxr_") -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    return prefix + "".join(rng.choice(alphabet) for _ in range(12))


def build_residue_map(seed: Union[bytes, str, int]) -> Dict[str, Dict[str, str]]:
    """Build the per-build {family: {original: randomized}} map.

    Deterministic for the same seed: SHA-256(seed + family + literal).
    """
    if isinstance(seed, int):
        seed_b = str(seed).encode("utf-8")
    elif isinstance(seed, str):
        seed_b = seed.encode("utf-8")
    else:
        seed_b = bytes(seed)
    mapping: Dict[str, Dict[str, str]] = {}
    for family in sorted(RESIDUE_FAMILIES):
        fam_map: Dict[str, str] = {}
        for literal in RESIDUE_FAMILIES[family]:
            digest = hashlib.sha256(
                seed_b + b":" + family.encode() + b":" + literal.encode()
            ).hexdigest()
            # Marker-likes keep a leading underscore + uppercase shape so
            # renamed module globals still read as private constants;
            # other families get a lowercase babel-style token.
            if literal.startswith("_"):
                token = "_NXR_" + digest[:12].upper()
            else:
                token = "_nxr_" + digest[:12]
            # Guard against a (practically impossible) collision inside
            # one family; re-derive with a counter if it ever happens.
            ctr = 0
            while token in fam_map.values():
                ctr += 1
                token = token + str(ctr)
            fam_map[literal] = token
        mapping[family] = fam_map
    return mapping


def _flatten(mapping: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    flat: Dict[str, str] = {}
    for fam_map in mapping.values():
        flat.update(fam_map)
    return flat


def apply_residue(
    source: str,
    seed_or_map: Union[bytes, str, int, Dict[str, Dict[str, str]], None] = None,
    enabled: bool = True,
) -> Tuple[str, Dict[str, Dict[str, str]]]:
    """Replace fixed literals with per-build randomized equivalents.

    Returns (new_source, map). Whole-token replacement only: the source
    is split on [A-Za-z0-9_] runs and each run is looked up verbatim.
    No-op when enabled=False, source is empty, or seed_or_map is None
    with no seed to derive from (empty map returned).
    """
    if not enabled or not source:
        return source, {}
    if seed_or_map is None:
        return source, {}
    if isinstance(seed_or_map, dict):
        mapping = seed_or_map
    else:
        mapping = build_residue_map(seed_or_map)
    flat = _flatten(mapping)
    if not flat:
        return source, mapping

    parts = []
    pos = 0
    for m in _TOKEN_RE.finditer(source):
        start, end = m.span()
        parts.append(source[pos:start])
        parts.append(flat.get(m.group(0), m.group(0)))
        pos = end
    parts.append(source[pos:])
    return "".join(parts), mapping


def resolve_token(
    token: str, mapping: Dict[str, Dict[str, str]]
) -> Optional[Tuple[str, str]]:
    """Resolve a randomized token back to (family, original)."""
    for family, fam_map in mapping.items():
        for orig, rand in fam_map.items():
            if token == rand:
                return (family, orig)
    return None


def residue_literals_in(source: str) -> Dict[str, list]:
    """Report which canonical residue literals still occur in source."""
    found: Dict[str, list] = {}
    for family, literals in RESIDUE_FAMILIES.items():
        hits = [lit for lit in literals if lit in source]
        if hits:
            found[family] = hits
    return found
