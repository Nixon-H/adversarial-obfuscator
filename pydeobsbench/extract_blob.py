"""Extract the embedded native blob from a shipped artefact and audit it.

This is the PyDeObsBench probe the report listed as missing ("native symbol
probe against the section pack"): an analyst who has the artefact can compute
the same key the loader computes, because the loader carries the shares.  So
the blob never protects itself -- the question is only what it leaks once
extracted.

Usage: python3 extract_blob.py <artefact> [outdir]
"""
import ast
import base64
import hashlib
import os
import subprocess
import sys
import tempfile


def _literals(tree):
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                name = getattr(tgt, "id", None)
                if not name:
                    continue
                try:
                    out[name] = ast.literal_eval(node.value)
                except Exception:
                    pass
    return out


def extract(artefact):
    src = open(artefact, encoding="utf-8", errors="surrogateescape").read()
    tree = ast.parse(src)
    lit = _literals(tree)
    blobs = lit.get("NATIVE_BLOBS") or {}
    s0 = base64.b64decode(lit["_BLOB_S0"])
    s1 = base64.b64decode(lit["_BLOB_S1"])
    raw_key = bytes(a ^ b for a, b in zip(s0, s1))
    mask = hashlib.sha256(str(lit["_NX_BUILD_ID"]).encode()).digest()
    key = bytes(b ^ mask[i % len(mask)] for i, b in enumerate(raw_key))
    salt = str(lit.get("_NX_CUSTOMER_SALT") or "")
    if not salt and lit.get("_NX_LICENCE_BOUND"):
        # Licence-bound: the mask comes from the token at runtime, so the
        # blob is NOT derivable from the artefact alone.  Report and stop.
        return None, "licence-bound (blob key needs the token)"
    if salt:
        cm = hashlib.sha256(b"nx-customer:" + salt.encode()).digest()
        key = bytes(b ^ cm[i % len(cm)] for i, b in enumerate(key))
    return (blobs, key), None


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    art = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else tempfile.mkdtemp(prefix="nx-blob-")
    got, err = extract(art)
    if err:
        print("blob NOT derivable: %s" % err)
        return 2
    blobs, key = got
    os.makedirs(outdir, exist_ok=True)
    rc = 0
    for plat, b64 in sorted(blobs.items()):
        if not b64:
            continue
        packed = base64.b64decode(b64)
        if packed.startswith(b"NXS1"):
            if len(packed) < 20:
                print("%s: truncated NXS1 stream envelope" % plat)
                rc = 1
                continue
            nonce = packed[4:20]
            ciphertext = packed[20:]
            stream = bytearray()
            counter = 0
            while len(stream) < len(ciphertext):
                stream.extend(hashlib.sha256(key + nonce + counter.to_bytes(8, "big")).digest())
                counter += 1
            plain = bytes(c ^ k for c, k in zip(ciphertext, stream[:len(ciphertext)]))
        else:
            plain = bytes(b ^ key[i % len(key)] for i, b in enumerate(packed))
        p = os.path.join(outdir, plat + os.path.splitext(art)[1].replace(".py", ".so"))
        with open(p, "wb") as fh:
            fh.write(plain)
        print("%s: %d bytes, magic=%r -> %s" % (plat, len(plain), plain[:4], p))
        nm = subprocess.run(["nm", "-D", "--defined-only", p],
                            capture_output=True, text=True)
        syms = [ln.split()[-1] for ln in nm.stdout.strip().splitlines() if ln.strip()]
        print("  exported symbols: %s" % (syms or "(none)"))
        rc = 0
    return rc


if __name__ == "__main__":
    sys.exit(main())
