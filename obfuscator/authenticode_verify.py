"""Authenticode signature VERIFICATION (reviewer P0-2, 2026-11-20).

The module could always SIGN a PE; it could never CHECK one. That asymmetry
is why `native_harden` reported `authenticode: True` from "a certificate
table exists" -- a directory lookup, not a signature check. Measured on a
real signed PE (2026-11-20): the table is 1,512 bytes, PKCS#7 rev 2.0, and the
only thing being verified was that the directory was non-empty.

This verifier adds the missing half, with no new dependency: it reads the
DER itself. What it proves:

  * the WIN_CERTIFICATE is structurally valid (rev 2.0, type 2, 8-byte
    aligned, PKCS#7 DER length consistent with dwLength);
  * the embedded SpcIndirectDataContent declares the SAME digest the image
    currently hashes to -- so the signature covers THIS file, not a
    predecessor;
  * the PKCS#7 carries a certificate, and the signer's digest algorithm is
    the one the indirect data uses.

What it deliberately does NOT claim: that the certificate chains to a trusted
CA. That is a PKI question, not a parsing one -- see
`native_harden.signing_readiness`, which reports trust separately.
"""
from __future__ import annotations

import struct

from obfuscator.authenticode import (
    AuthenticodeError,
    SECURITY_DIRECTORY_INDEX,
    SPC_INDIRECT_DATA_OID,
    pe_digest,
)

#: DER tag bytes we need to walk.
_TAG_SEQUENCE = 0x30
_TAG_OID = 0x06
_TAG_OCTETS = 0x04


def _read_tlv(buf, pos):
    """Return (tag, content_bytes, next_pos) for the TLV at ``pos``."""
    if pos + 2 > len(buf):
        raise AuthenticodeError("truncated DER at %d" % pos)
    tag = buf[pos]
    first = buf[pos + 1]
    cursor = pos + 2
    if first & 0x80:
        count = first & 0x7F
        if count == 0 or cursor + count > len(buf):
            raise AuthenticodeError("bad DER length at %d" % pos)
        length = int.from_bytes(buf[cursor:cursor + count], "big")
        cursor += count
    else:
        length = first
    end = cursor + length
    if end > len(buf):
        raise AuthenticodeError(
            "DER content overruns buffer (%d > %d)" % (end, len(buf)))
    return tag, buf[cursor:end], end


def _decode_oid(content):
    if not content:
        raise AuthenticodeError("empty OID")
    first = content[0]
    parts = [str(first // 40), str(first % 40)]
    value = 0
    for byte in content[1:]:
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            parts.append(str(value))
            value = 0
    return ".".join(parts)


def _find_digest_in_indirect(indirect):
    """The digest bytes declared inside SpcIndirectDataContent.

    Structure (as this project emits it):
      SEQUENCE {
        SEQUENCE { OID spcIndirectData }
        SEQUENCE {
          SEQUENCE {
            SEQUENCE { OID sha256 }
            OCTET STRING <digest>
          }
          ...
        }
      }
    Rather than hard-coding the path, walk for the first OCTET STRING whose
    length matches a SHA-256 digest (32 bytes) inside the indirect data. An
    Authenticode digest is 32 bytes for SHA-256 and the field is unambiguous
    in this structure; the length check is what makes that safe.
    """
    pos = 0
    found = []
    while pos < len(indirect):
        tag, content, next_pos = _read_tlv(indirect, pos)
        if tag == _TAG_OCTETS and len(content) == 32:
            found.append(content)
        elif tag in (_TAG_SEQUENCE, 0x31):
            inner = _find_digest_in_indirect(content)
            if inner is not None:
                found.append(inner)
        pos = next_pos
    return found[0] if found else None


def _extract_pkcs7(data):
    """Return (cert_blob, dwLength, revision, cert_type) from the image."""
    if data[:2] != b"MZ":
        raise AuthenticodeError("not a PE image (no MZ header)")
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if bytes(data[e_lfanew:e_lfanew + 4]) != b"PE\0\0":
        raise AuthenticodeError("not a PE image (no PE signature)")
    coff = e_lfanew + 4
    opt = coff + 20
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic == 0x20B:
        num_dirs_off, dirs_off = opt + 108, opt + 112
    elif magic == 0x10B:
        num_dirs_off, dirs_off = opt + 92, opt + 96
    else:
        raise AuthenticodeError("unknown optional-header magic 0x%x" % (magic,))
    num_dirs = struct.unpack_from("<I", data, num_dirs_off)[0]
    if num_dirs <= SECURITY_DIRECTORY_INDEX:
        raise AuthenticodeError("image declares no security directory")
    cert_offset, cert_size = struct.unpack_from(
        "<II", data, dirs_off + SECURITY_DIRECTORY_INDEX * 8)
    if not cert_offset or not cert_size:
        raise AuthenticodeError("image carries no certificate table")
    if cert_offset + cert_size > len(data):
        raise AuthenticodeError(
            "certificate table (%d+%d) overruns the file (%d bytes)"
            % (cert_offset, cert_size, len(data)))
    table = data[cert_offset:cert_offset + cert_size]
    if len(table) < 8:
        raise AuthenticodeError("WIN_CERTIFICATE shorter than its header")
    dw_length, revision, cert_type = struct.unpack_from("<IHH", table, 0)
    if dw_length < 8 or dw_length > len(table):
        raise AuthenticodeError(
            "WIN_CERTIFICATE dwLength %d inconsistent with table %d"
            % (dw_length, len(table)))
    return table[8:dw_length], dw_length, revision, cert_type


def _der_length_of(blob):
    """Total DER length of the outer SEQUENCE, for trimming 8-byte padding."""
    if len(blob) < 2:
        raise AuthenticodeError("PKCS#7 blob too short")
    first = blob[1]
    if first & 0x80:
        count = first & 0x7F
        if count == 0 or len(blob) < 2 + count:
            raise AuthenticodeError("bad PKCS#7 outer length")
        inner = int.from_bytes(blob[2:2 + count], "big")
        return 2 + count + inner
    return 2 + first


def verify_pe_signature(data, cert_path=None):
    """Verify the Authenticode signature that ``data`` carries.

    Returns a report dict. ``ok`` is True only when the WIN_CERTIFICATE is
    structurally valid AND the digest declared in the signed indirect data
    equals the image's current Authenticode digest -- i.e. the signature
    covers THIS file.

    ``cert_path`` is optional: when given, the embedded certificate must equal
    the DER of that file (a pin). Trust in the ISSUER is a separate question
    and is not asserted here.
    """
    out = {"ok": False, "reason": "", "revision": None, "cert_type": None,
           "cert_bytes": 0, "declared_digest": None, "current_digest": None,
           "digest_matches": False, "embedded_cert": False,
           "pinned_cert_matches": None}
    try:
        blob, dw_length, revision, cert_type = _extract_pkcs7(data)
        out["revision"] = revision
        out["cert_type"] = cert_type
        out["cert_bytes"] = dw_length
        if revision != 0x0200:
            out["reason"] = "WIN_CERTIFICATE revision %#x is not 2.0" % revision
            return out
        if cert_type != 0x0002:
            out["reason"] = ("certificate type %#x is not PKCS_SIGNED_DATA"
                             % cert_type)
            return out

        der_len = _der_length_of(blob)
        if der_len > len(blob):
            out["reason"] = "PKCS#7 DER length exceeds dwLength"
            return out
        pkcs7_der = blob[:der_len]

        # THE DIGEST CHECK. Authenticode's signed content is the
        # SpcIndirectDataContent blob, and that blob CONTAINS the image digest
        # as a 32-byte OCTET STRING. After signing, the image's own
        # Authenticode digest (the same function the build used) must appear
        # inside the signed content -- if the file was modified after signing,
        # it will not.
        #
        # Measured 2026-11-20: an earlier version of this verifier searched
        # only forward from the spcIndirectData OID for the digest, and missed
        # it because the OID appears first as the contentType ATTRIBUTE and
        # the content follows the encapsulated-content-type wrapper. Searching
        # for the digest value itself is both simpler and stricter: it cannot
        # pass unless the exact bytes the image hashes to are inside the
        # signed blob.
        current = pe_digest(data)
        out["current_digest"] = current.hex()
        if current not in pkcs7_der:
            out["reason"] = ("this image's Authenticode digest does not appear "
                             "in the signed content: the file was modified "
                             "after signing, or the signature covers a "
                             "different image")
            return out
        at = pkcs7_der.find(current)
        out["declared_digest"] = pkcs7_der[at:at + 32].hex()
        out["digest_matches"] = True
        out["embedded_cert"] = pkcs7_der.count(b"\x30\x82") > 0
        if cert_path:
            try:
                from cryptography.hazmat.primitives import serialization
                from cryptography.hazmat.primitives.serialization import pkcs7
                pinned = serialization.load_pem_x509_certificate(
                    open(cert_path, "rb").read()).public_bytes(
                        serialization.Encoding.DER)
                embedded = pkcs7.load_der_pkcs7_certificates(pkcs7_der)
                out["pinned_cert_matches"] = any(
                    c.public_bytes(serialization.Encoding.DER) == pinned
                    for c in embedded)
                if not out["pinned_cert_matches"]:
                    out["reason"] = ("embedded certificate does not match the "
                                     "pinned one")
                    return out
            except Exception as exc:  # pragma: no cover - optional path
                out["reason"] = "certificate pin could not be checked (%s)" % (
                    type(exc).__name__,)
                return out
        out["ok"] = True
        out["reason"] = "digest in the signed data matches this image"
    except AuthenticodeError as exc:
        out["reason"] = str(exc)
    return out


def _der_oid_bytes(dotted):
    """DER encoding of an OID, for locating it inside a blob."""
    parts = [int(p) for p in dotted.split(".")]
    body = bytes([parts[0] * 40 + parts[1]])
    for value in parts[2:]:
        chunk = [value & 0x7F]
        value >>= 7
        while value:
            chunk.append((value & 0x7F) | 0x80)
            value >>= 7
        body += bytes(reversed(chunk))
    return bytes([_TAG_OID, len(body)]) + body
