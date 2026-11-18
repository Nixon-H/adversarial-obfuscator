"""Static probes: what an analyst recovers WITHOUT executing the artefact.

Each probe returns a structured result so the report can separate
"cannot" from "did not try". Probes are deliberately independent: a single
patched defence must not disable the whole measurement.
"""
from __future__ import annotations

import base64
import bz2
import json
import lzma
import marshal
import re
import subprocess
import types
import zlib


def _read(path):
    with open(path, "rb") as fh:
        return fh.read()


def _mask_loader_namespace(text):
    """Blank out the loader's own namespace before scanning for payload names.

    A hand-maintained list of loader identifiers is a losing game: every new
    gate adds another `_NX_*` name, and several contain payload-ish substrings
    (`_NX_CUSTOMER_SALT` contains `SALT`, `[NX_SB_FRAG:SALT]` contains it too).
    Instead, blank EVERY identifier that starts with the loader's prefixes --
    `_NX_`, `_nx_`, `NX_`, and the `_nixon_` babel namespace -- which is
    exactly the set the runtime owns.
    """
    masked = re.sub(r"_NX_[A-Za-z0-9_]*", lambda m: " " * len(m.group(0)), text)
    masked = re.sub(r"_nx_[A-Za-z0-9_]*", lambda m: " " * len(m.group(0)), masked)
    # the bootstrap-fragment comment markers read `# [NX_SB_FRAG:<NAME>]`, so
    # the payload-ish word sits after a colon and survives an identifier
    # prefix match. Blank the whole bracketed marker.
    masked = re.sub(r"\[[^\]\n]*NX_SB_FRAG[^\]\n]*\]",
                    lambda m: " " * len(m.group(0)), masked)
    masked = re.sub(r"NX_SB_[A-Za-z0-9_]*", lambda m: " " * len(m.group(0)), masked)
    masked = re.sub(r"_nixon_[^\s\W]*", lambda m: " " * len(m.group(0)), masked)
    return masked


def probe_plaintext(target, artefact_path):
    """Are any ground-truth secrets or names literally present?

    Loader identifiers are masked out first: several of them contain payload
    names as substrings (`_NX_CUSTOMER_SALT` contains `SALT`), which made a
    naive scan report a leak on every artefact.
    """
    data = _read(artefact_path)
    text = data.decode("utf-8", "replace")
    masked = _mask_loader_namespace(text)
    secrets = [s for s in target["secrets"] if s in masked]
    names = [n for n in target["names"]
             if re.search(r"(?<![A-Za-z0-9_])" + re.escape(n) + r"(?![A-Za-z0-9_])",
                          masked)]
    return {
        "probe": "plaintext",
        "secrets_recovered": len(secrets),
        "secrets_total": len(target["secrets"]),
        "secrets_hit": secrets,
        "names_recovered": len(names),
        "names_total": len(target["names"]),
        "names_hit": names,
    }


def probe_elf_symbols(artefact_path):
    """Does the shipped native blob leak symbols?

    The blob is embedded base64; extract the largest blob, decode it, and run
    nm/readelf on the result if it is an ELF.
    """
    data = _read(artefact_path)
    text = data.decode("utf-8", "replace")
    # the loader embeds blobs base64 (b64) or base85
    candidates = re.findall(r"[A-Za-z0-9+/=]{2000,}", text)
    blobs = []
    for c in candidates[:20]:
        try:
            raw = base64.b64decode(c, validate=False)
        except Exception:
            continue
        if raw[:4] == b"\x7fELF":
            blobs.append(raw)
    if not blobs:
        return {"probe": "elf_symbols", "found_elf": False, "symbols": []}
    import tempfile
    import os
    out = {}
    for idx, raw in enumerate(blobs[:3]):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "blob%d.so" % idx)
        with open(p, "wb") as fh:
            fh.write(raw)
        dyn = subprocess.run(["nm", "-D", "--defined-only", p],
                             capture_output=True, text=True).stdout
        syms = [ln.split()[-1] for ln in dyn.splitlines() if ln.strip()]
        out[idx] = syms
        # also look for leaked strings inside the ELF
        strings = subprocess.run(["strings", "-n", "6", p],
                                 capture_output=True, text=True).stdout
        out["strings_%d" % idx] = strings
    return {"probe": "elf_symbols", "found_elf": True, "detail": out}


def probe_section_decrypt(artefact_path):
    """Can the section pack be decoded with only what the artefact carries?

    This is the no-licence offline attack: the shares and build id are in the
    artefact, so the key is derivable. For a licence-bound artefact the key
    material is NOT present and this must fail.
    """
    import hashlib
    import hmac

    text = _read(artefact_path).decode("utf-8", "replace")
    m = re.search(r"_NX_SECTION_PACK\s*=\s*'([^']+)'", text)
    if not m:
        return {"probe": "section_decrypt", "applicable": False,
                "reason": "no section pack literal"}
    s0m = re.search(r'_BLOB_S0\s*=\s*"([^"]+)"', text)
    s1m = re.search(r'_BLOB_S1\s*=\s*"([^"]+)"', text)
    bidm = re.search(r'_NX_BUILD_ID\s*=\s*"([^"]+)"', text)
    if not (s0m and s1m and bidm):
        return {"probe": "section_decrypt", "applicable": True,
                "derived": False, "reason": "shares or build id absent"}

    s0 = base64.b64decode(s0m.group(1))
    s1 = base64.b64decode(s1m.group(1))
    bid = bidm.group(1)
    raw = bytearray(a ^ b for a, b in zip(s0, s1))
    mask = hashlib.sha256(bid.encode()).digest()
    key = bytes(b ^ mask[i % 32] for i, b in enumerate(raw))
    saltm = re.search(r'_NX_CUSTOMER_SALT\s*=\s*"([^"]*)"', text)
    if saltm and saltm.group(1):
        cm = hashlib.sha256(b"nx-customer:" + saltm.group(1).encode()).digest()
        key = bytes(b ^ cm[i % 32] for i, b in enumerate(key))

    pack = json.loads(base64.b85decode(m.group(1)).decode("utf-8"))

    def ks(k, n, ln):
        out = bytearray()
        c = 0
        while len(out) < ln:
            out.extend(hashlib.sha256(k + n + c.to_bytes(8, "big")).digest())
            c += 1
        return bytes(out[:ln])

    joined = bytearray()
    verified = 0
    for sec in sorted(pack["sections"], key=lambda s: s["i"]):
        nonce = bytes.fromhex(sec["nonce"])
        sk = hashlib.sha256(b"nx-section-key:" + key
                            + sec["i"].to_bytes(4, "big") + nonce).digest()
        enc = bytes.fromhex(sec["data"])
        tagged = bytes(a ^ b for a, b in zip(enc, ks(sk, nonce, len(enc))))
        tag, part = tagged[:32], tagged[32:]
        if hmac.compare_digest(
                hmac.new(sk + nonce, part, hashlib.sha256).digest(), tag):
            verified += 1
            joined.extend(part)

    if verified != pack["count"]:
        return {"probe": "section_decrypt", "applicable": True,
                "derived": False,
                "reason": "HMAC failed on %d/%d sections (key not derivable)"
                          % (pack["count"] - verified, pack["count"])}

    # unwrap the compression envelope
    data = bytes(joined)
    opened = None
    for fn in (zlib.decompress, bz2.decompress, lzma.decompress):
        try:
            opened = fn(data[1:])
            break
        except Exception:
            continue
    return {
        "probe": "section_decrypt", "applicable": True, "derived": True,
        "payload_bytes": len(data),
        "decompressed_bytes": len(opened) if opened else None,
        "reason": "all %d sections verified and joined offline" % verified,
    }


def probe_payload_strings(artefact_path):
    """Peel the section pack all the way to payload constants.

    Returns the ground-truth secrets that survive into the decrypted payload.
    """
    import hashlib
    import hmac

    text = _read(artefact_path).decode("utf-8", "replace")
    m = re.search(r"_NX_SECTION_PACK\s*=\s*'([^']+)'", text)
    s0m = re.search(r'_BLOB_S0\s*=\s*"([^"]+)"', text)
    s1m = re.search(r'_BLOB_S1\s*=\s*"([^"]+)"', text)
    bidm = re.search(r'_NX_BUILD_ID\s*=\s*"([^"]+)"', text)
    if not (m and s0m and s1m and bidm):
        return {"probe": "payload_strings", "applicable": False}

    s0 = base64.b64decode(s0m.group(1))
    s1 = base64.b64decode(s1m.group(1))
    raw = bytearray(a ^ b for a, b in zip(s0, s1))
    mask = hashlib.sha256(bidm.group(1).encode()).digest()
    key = bytes(b ^ mask[i % 32] for i, b in enumerate(raw))
    saltm = re.search(r'_NX_CUSTOMER_SALT\s*=\s*"([^"]*)"', text)
    if saltm and saltm.group(1):
        cm = hashlib.sha256(b"nx-customer:" + saltm.group(1).encode()).digest()
        key = bytes(b ^ cm[i % 32] for i, b in enumerate(key))

    pack = json.loads(base64.b85decode(m.group(1)).decode("utf-8"))

    def ks(k, n, ln):
        out = bytearray()
        c = 0
        while len(out) < ln:
            out.extend(hashlib.sha256(k + n + c.to_bytes(8, "big")).digest())
            c += 1
        return bytes(out[:ln])

    joined = bytearray()
    for sec in sorted(pack["sections"], key=lambda s: s["i"]):
        nonce = bytes.fromhex(sec["nonce"])
        sk = hashlib.sha256(b"nx-section-key:" + key
                            + sec["i"].to_bytes(4, "big") + nonce).digest()
        enc = bytes.fromhex(sec["data"])
        tagged = bytes(a ^ b for a, b in zip(enc, ks(sk, nonce, len(enc))))
        tag, part = tagged[:32], tagged[32:]
        if not hmac.compare_digest(
                hmac.new(sk + nonce, part, hashlib.sha256).digest(), tag):
            return {"probe": "payload_strings", "applicable": True,
                    "derived": False}
        joined.extend(part)

    data = bytes(joined)
    inner = None
    for fn in (zlib.decompress, bz2.decompress, lzma.decompress):
        try:
            inner = fn(data[1:])
            break
        except Exception:
            continue
    if inner is None:
        return {"probe": "payload_strings", "applicable": True,
                "derived": True, "payload_strings": []}

    strings = []
    try:
        code = marshal.loads(inner)

        def walk(c):
            for k in c.co_consts:
                if isinstance(k, str):
                    strings.append(k)
                elif isinstance(k, types.CodeType):
                    walk(k)
        walk(code)
    except Exception:
        strings = [inner.decode("utf-8", "replace")[:4000]]

    blob = "\n".join(strings)
    return {"probe": "payload_strings", "applicable": True, "derived": True,
            "payload_strings": strings[:40], "joined_text": blob[:8000]}
