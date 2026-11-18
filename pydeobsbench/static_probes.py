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


def probe_packed_elf_symbols(artefact_path):
    """Extract the native blob from INSIDE the section pack and inspect it.

    The first version of this probe only looked for a top-level base64 ELF and
    reported `found_elf: False` on every sectioned artefact -- a gap in the
    probe, not a clean result (the blob lives inside the sealed pack, encoded
    again). This decodes the pack, unwraps the compression envelope, pulls the
    module blob out of the marshalled payload, and runs nm/strings on it.
    """
    import hashlib
    import hmac
    import marshal
    import tempfile
    import types

    text = _read(artefact_path).decode("utf-8", "replace")
    m = re.search(r"_NX_SECTION_PACK\s*=\s*'([^']+)'", text)
    s0m = re.search(r'_BLOB_S0\s*=\s*"([^"]+)"', text)
    s1m = re.search(r'_BLOB_S1\s*=\s*"([^"]+)"', text)
    bidm = re.search(r'_NX_BUILD_ID\s*=\s*"([^"]+)"', text)
    if not (m and s0m and s1m and bidm):
        return {"probe": "packed_elf", "applicable": False}

    s0 = base64.b64decode(s0m.group(1))
    s1 = base64.b64decode(s1m.group(1))
    raw = bytearray(a ^ b for a, b in zip(s0, s1))
    mask = hashlib.sha256(bidm.group(1).encode()).digest()
    key = bytes(b ^ mask[i % 32] for i, b in enumerate(raw))
    saltm = re.search(r'_NX_CUSTOMER_SALT\s*=\s*"([^"]*)"', text)
    if saltm and saltm.group(1):
        cm = hashlib.sha256(b"nx-customer:" + saltm.group(1).encode()).digest()
        key = bytes(b ^ cm[i % 32] for i, b in enumerate(key))

    try:
        pack = json.loads(base64.b85decode(m.group(1)).decode("utf-8"))
    except Exception as exc:
        return {"probe": "packed_elf", "applicable": True,
                "error": str(exc)[:120]}

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
        if not hmac.compare_digest(
                hmac.new(sk + nonce, tagged[32:], hashlib.sha256).digest(),
                tagged[:32]):
            return {"probe": "packed_elf", "applicable": True,
                    "derived": False, "found_elf": False,
                    "reason": "pack not derivable (licence-bound)"}
        joined.extend(tagged[32:])

    data = bytes(joined)
    inner = None
    for fn in (zlib.decompress, bz2.decompress, lzma.decompress):
        try:
            inner = fn(data[1:])
            break
        except Exception:
            continue
    if inner is None:
        return {"probe": "packed_elf", "applicable": True,
                "derived": True, "found_elf": False,
                "reason": "no compression envelope"}

    # the payload may carry the native module as a base64 literal
    elfs = []
    try:
        code = marshal.loads(inner)
        strings = []
        blob = []
        def walk(c):
            for k in c.co_consts:
                if isinstance(k, str):
                    strings.append(k)
                elif isinstance(k, types.CodeType):
                    walk(k)
        walk(code)
        for s in strings:
            if len(s) < 512:
                continue
            for cand in (base64.b64decode, base64.b85decode):
                try:
                    d = cand(s + "=" * (-len(s) % 4))
                except Exception:
                    continue
                if d[:4] == b"\x7fELF":
                    elfs.append(d)
    except Exception:
        pass

    if not elfs:
        return {"probe": "packed_elf", "applicable": True, "derived": True,
                "found_elf": False,
                "reason": "payload carries no base64 ELF literal"}

    d = tempfile.mkdtemp()
    p = os.path.join(d, "mod.so")
    with open(p, "wb") as fh:
        fh.write(elfs[0])
    dyn = subprocess.run(["nm", "-D", "--defined-only", p],
                         capture_output=True, text=True).stdout
    syms = [ln.split()[-1] for ln in dyn.splitlines() if ln.strip()]
    strs = subprocess.run(["strings", "-n", "8", p],
                          capture_output=True, text=True).stdout
    # do any ground-truth-ish identifiers appear in the native module?
    return {"probe": "packed_elf", "applicable": True, "derived": True,
            "found_elf": True, "elf_bytes": len(elfs[0]),
            "exported_symbols": syms[:60],
            "symbol_count": len(syms),
            "string_sample": [s for s in strs.splitlines() if s.strip()][:40]}


def probe_native_blob(artefact_path, target=None):
    """Extract the embedded native module and measure what it leaks.

    The earlier ELF probes looked for a base64 ELF literal or dug through the
    section pack, and both reported `found_elf: False` on artefacts that DO
    carry a ~140 KB .so -- a probe gap, not a clean result (the report listed
    it as limit 4).  This one performs the same derivation the loader performs
    (shares -> build-id salt -> customer mask -> XOR), which is exactly what an
    analyst does, then measures the things that matter about a shipped blob:

      * is the object file reachable at all (it always is: the loader carries
        the key, so "encrypted blob" is not a protection boundary);
      * does `nm -D` expose more than the module init symbol;
      * do the target's ground-truth identifiers appear in its strings;
      * is the ELF actually hardened (RELRO, NX, .comment, .symtab).

    `derived: False` for a licence-bound artefact means the blob genuinely is
    not recoverable without the token -- that is the property to quote.
    """
    import ast
    import hashlib
    import os
    import tempfile

    text = _read(artefact_path).decode("utf-8", "replace")

    # NATIVE_BLOBS is a dict literal; parse with ast so a re-quoted or
    # line-wrapped emission still parses.
    blobs = None
    try:
        for node in ast.parse(text).body:
            if isinstance(node, ast.Assign) and \
                    getattr(node.targets[0], "id", "") == "NATIVE_BLOBS":
                blobs = ast.literal_eval(node.value)
                break
    except Exception:
        blobs = None
    if not blobs or not any(blobs.values()):
        return {"probe": "native_blob", "applicable": True,
                "found": False, "reason": "no native blob embedded"}

    platform_key = "linux"
    b64 = blobs.get(platform_key) or ""
    if not b64:
        for k, v in blobs.items():
            if v:
                platform_key, b64 = k, v
                break

    s0m = re.search(r'_BLOB_S0\s*=\s*"([^"]+)"', text)
    s1m = re.search(r'_BLOB_S1\s*=\s*"([^"]+)"', text)
    bidm = re.search(r'_NX_BUILD_ID\s*=\s*"([^"]+)"', text)
    if not (s0m and s1m and bidm):
        return {"probe": "native_blob", "applicable": True,
                "found": True, "derived": False,
                "reason": "key shares / build id not present in artefact"}

    try:
        raw = bytes(a ^ b for a, b in
                    zip(base64.b64decode(s0m.group(1)),
                        base64.b64decode(s1m.group(1))))
        mask = hashlib.sha256(bidm.group(1).encode()).digest()
        key = bytes(b ^ mask[i % 32] for i, b in enumerate(raw))
        saltm = re.search(r'_NX_CUSTOMER_SALT\s*=\s*"([^"]*)"', text)
        if saltm and saltm.group(1):
            cm = hashlib.sha256(
                b"nx-customer:" + saltm.group(1).encode()).digest()
            key = bytes(b ^ cm[i % 32] for i, b in enumerate(key))
    except Exception as exc:
        return {"probe": "native_blob", "applicable": True,
                "found": True, "derived": False, "error": str(exc)[:120]}

    try:
        packed = base64.b64decode(b64, validate=True)
    except Exception:
        try:
            packed = base64.b85decode(b64)
        except Exception as exc:
            return {"probe": "native_blob", "applicable": True,
                    "found": True, "derived": False,
                    "error": "blob codec: %s" % str(exc)[:80]}
    plain = bytes(b ^ key[i % len(key)] for i, b in enumerate(packed))
    if plain[:4] != b"\x7fELF":
        return {"probe": "native_blob", "applicable": True,
                "found": True, "derived": True, "valid_object": False,
                "magic": plain[:8].hex(),
                "note": "blob is not a raw object file. If the artefact still "
                        "runs, the loader XORed it into garbage and the "
                        "payload came from the bytecode fallback."}

    d = tempfile.mkdtemp(prefix="nx-blob-probe-")
    p = os.path.join(d, "mod.so")
    with open(p, "wb") as fh:
        fh.write(plain)

    def _run(argv):
        try:
            return subprocess.run(argv, capture_output=True,
                                  text=True).stdout
        except Exception:
            return ""

    dyn = _run(["nm", "-D", "--defined-only", p])
    exports = [ln.split()[-1] for ln in dyn.splitlines() if len(ln.split()) >= 3]
    sec = _run(["readelf", "-SW", p])
    prog = _run(["readelf", "-lW", p])
    strings = _run(["strings", "-n", "6", p])

    names_hit = []
    if target:
        for n in target.get("names", []):
            if re.search(r"(?<![A-Za-z0-9_])" + re.escape(n) +
                         r"(?![A-Za-z0-9_])", strings):
                names_hit.append(n)
    pyx = sorted(set(re.findall(r"__pyx_[A-Za-z0-9_]+", strings)))
    _stk = [ln for ln in prog.splitlines() if "GNU_STACK" in ln]

    return {
        "probe": "native_blob",
        "applicable": True,
        "found": True,
        "derived": True,
        "valid_object": True,
        "platform": platform_key,
        "elf_bytes": len(plain),
        "dynamic_exports": exports,
        "export_count": len(exports),
        "symtab_present": ".symtab" in sec,
        "comment_present": ".comment" in sec,
        "relro": "GNU_RELRO" in prog,
        "nx_stack": bool(_stk) and "RWE" not in _stk[0],
        "payload_names_in_strings": names_hit,
        "pyx_strings": pyx[:20],
        "pyx_string_count": len(pyx),
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
