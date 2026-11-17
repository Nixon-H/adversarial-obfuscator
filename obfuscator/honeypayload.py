"""Honeypayloads: a plausible decoy payload shipped ahead of the real one.

The benchmark agents spend most of their budget on *decryption*.  This module
makes that budget work against them: a second, realistic-looking payload is
sealed at a shallower layer than the real one, under a **different** key.  An
analyst who breaks the outer layer finds a complete, self-consistent program
and has no signal that it is not the deliverable — the real payload sits
behind an additional gate the decoy does not have.

Design constraints (each one is a test):

* The decoy must be **plausible**: real-looking logic, plausible names, a
  working `main()`.  A stub that prints "decoy" is worthless.
* It must be **self-consistent**: running it produces sensible output, so an
  analyst who executes it does not immediately conclude it is fake.
* It must be **cheap**: generating it costs a few milliseconds and a few KB.
* It must be **inert with respect to the real payload**: the decoy's key is
  derived from the build id only, never from the licence, so breaking it
  teaches the analyst nothing about the real key chain.
* The real payload must remain reachable: the decoy never replaces it.

The decoy is emitted as an extra sealed pack (``_NX_HONEY_PACK``) with its own
key hint.  The loader ignores it on the normal path; it exists so that a
static analyst finds two candidate payloads and cannot tell which is which
without doing strictly more work than recovering the real one.
"""
from __future__ import annotations

import hashlib
from typing import Optional

#: A realistic-looking payload.  Deliberately mundane: a licence-check
#: helper, a checksum routine and a small CLI, which is what a "protected
#: tool" usually looks like.  The constants are plausible but wrong -- an
#: analyst who extracts them learns nothing usable.
_DECOY_TEMPLATE = '''\
"""Deployment helper for the licensed runtime.

Resolves the runtime endpoint, verifies the local build stamp and prints the
resolved configuration.  Kept dependency-free so it can ship as a single file.
"""
import hashlib
import json
import os
import sys

API_BASE = "https://api.{vendor}.internal/v2"
BUILD_STAMP = "{stamp}"
LICENCE_SALT = "{salt}"
RETRY_LIMIT = {retry}


def build_fingerprint():
    """Stable fingerprint for this build (used by the endpoint resolver)."""
    material = (BUILD_STAMP + LICENCE_SALT).encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:32]


def resolve_endpoint(region="eu-west-1"):
    """Pick the regional endpoint for this build."""
    digest = build_fingerprint()
    shard = int(digest[:4], 16) % {shards}
    return "{{}}/{{}}/shard-{{}}".format(API_BASE, region, shard)


def verify_stamp(candidate):
    """Compare a candidate stamp against the one baked into this build."""
    return hashlib.sha256(candidate.encode("utf-8")).hexdigest()[:16] == BUILD_STAMP[:16]


def load_config(path=None):
    """Read the local configuration, falling back to defaults."""
    path = path or os.path.join(os.path.expanduser("~"), ".{vendor}", "config.json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("config must be an object")
        return data
    except (OSError, ValueError):
        return {{"region": "eu-west-1", "retries": RETRY_LIMIT}}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    config = load_config()
    endpoint = resolve_endpoint(config.get("region", "eu-west-1"))
    print("build:", build_fingerprint())
    print("endpoint:", endpoint)
    print("retries:", config.get("retries", RETRY_LIMIT))
    if argv and argv[0] == "--verify":
        print("stamp-ok:", verify_stamp(argv[1] if len(argv) > 1 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

#: Plausible vendor names for the decoy's constants.
_VENDORS = ("northgate", "cobaltline", "meridian", "atlasworks", "harborlight")


def generate_decoy(seed: bytes, vendor: Optional[str] = None) -> str:
    """Return a plausible decoy payload as source text.

    ``seed`` makes the decoy deterministic per build (so two builds of the
    same payload do not produce the same decoy, but a rebuild does).
    """
    digest = hashlib.sha256(bytes(seed)).digest()
    vendor_name = vendor or _VENDORS[digest[0] % len(_VENDORS)]
    stamp = digest[1:9].hex()
    salt = digest[9:17].hex()
    retry = 2 + (digest[17] % 4)
    shards = 2 + (digest[18] % 6)
    return _DECOY_TEMPLATE.format(
        vendor=vendor_name, stamp=stamp, salt=salt,
        retry=retry, shards=shards)


def decoy_key(build_id: str) -> bytes:
    """The decoy's sealing key.

    Derived from the BUILD ID ONLY -- never from the licence.  That is what
    keeps the decoy inert: recovering it tells an analyst nothing about the
    licence-bound key chain that protects the real payload.
    """
    return hashlib.sha256(
        b"nx-honey-decoy:" + str(build_id).encode("utf-8")).digest()


def build_honey_pack(seed: bytes, build_id: str, *, sections: int = 2) -> dict:
    """Seal the decoy into its own pack, with its own key hint.

    Returns ``{"pack_b85": str, "key_hint": str, "source": str}``.
    """
    import base64

    from obfuscator.section_split import pack_json

    source = generate_decoy(seed)
    key = decoy_key(build_id)
    # Compress with the same envelope the real payload uses, so the two are
    # indistinguishable by shape.
    import zlib
    stream = bytes([0x00]) + zlib.compress(source.encode("utf-8"))
    # Deterministic per build: the decoy's section nonces derive from the
    # honey seed, so two builds with the same inputs produce byte-identical
    # decoys (reproducible builds + the byte-identity loader tests).
    js, session_key = pack_json(stream, sections=sections, key=key,
                                nonce_seed=seed)
    return {
        "pack_b85": base64.b85encode(js).decode("ascii"),
        "key_hint": hashlib.sha256(session_key).hexdigest()[:16],
        "source": source,
    }


def emit_honey_snippet(var_name: str = "_NX_HONEY_PACK") -> str:
    """Loader-side declaration of the decoy pack.

    The loader never decrypts this on the normal path; it is present so a
    static analyst finds a second, complete-looking payload.
    """
    return (
        "# Secondary payload pack (build stamp + endpoint resolver).\n"
        "%s = ''\n" % (var_name,)
    )


def decoy_is_plausible(source: str) -> bool:
    """Cheap sanity gate: the decoy must look like a real program.

    Used by the tests and by the build (a decoy that fails this is not
    emitted at all -- shipping a broken decoy is worse than shipping none,
    because it advertises that something is fake).
    """
    required = ("def main(", "if __name__", "hashlib", "return")
    return all(marker in source for marker in required)
