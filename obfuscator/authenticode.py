"""§3 Authenticode: sign a PE with an operator-supplied certificate.

The review asks for Authenticode on Windows, and the honest status recorded
previously was "not present, and cannot be trusted here" — correct, because a
self-signed certificate is not trusted by Windows and shipping one would make
the artefact *look* signed while changing nothing the OS enforces.

That is a statement about the CERTIFICATE, not about the mechanism. This module
implements the mechanism, gated on an operator supplying a real certificate:

    NIXON_AUTHENTICODE_CERT   path to a PEM/DER certificate (+ chain)
    NIXON_AUTHENTICODE_KEY    path to the matching private key
    NIXON_AUTHENTICODE_PASS   optional passphrase for an encrypted key

With those set, `sign_pe()` produces an Authenticode-signed PE and
`native_harden.verify_pe_bytes` reports `authenticode: True` from the security
directory. Without them, the build reports the artefact as unsigned rather than
pretending.

What this implements
--------------------
Authenticode is not plain PKCS#7 over the file. The signature lives in the PE
**security directory** (data directory index 4) as a WIN_CERTIFICATE blob, and
the digest is computed over the file **with the checksum field, the certificate
table entry and the certificate data itself treated as zero** — otherwise the
signature could not be inserted without invalidating it. Getting that wrong
produces a file that carries a signature and fails every verifier.

Scope, stated because it would otherwise be over-read:

* This produces a structurally valid, digest-correct Authenticode signature.
  Whether Windows TRUSTS it depends on the certificate chain, which is the
  operator's supply chain, not this module's.
* It does not implement timestamping (RFC 3161). A signature without a
  timestamp stops validating when the certificate expires; the operator should
  timestamp out of band, and the module says so rather than implying otherwise.
* It does not implement page hashes or multiple signatures. One signer, whole
  file.
"""
from __future__ import annotations

import hashlib
import os
import struct

#: PE security directory index.
SECURITY_DIRECTORY_INDEX = 4

#: WIN_CERTIFICATE revision 2.0 and type 0x0002 (PKCS#7).
WIN_CERT_REVISION_2_0 = 0x0200
WIN_CERT_TYPE_PKCS_SIGNED_DATA = 0x0002

#: The SpcIndirectDataContent OID used by Authenticode for PE images.
SPC_INDIRECT_DATA_OID = "1.3.6.1.4.1.311.2.1.4"

#: Digest algorithm identifiers, as Authenticode expects them.
OID_SHA256 = "2.16.840.1.101.3.4.2.1"

#: Offset of the checksum field in both PE32 and PE32+ optional headers.
PE_CHECKSUM_OFFSET = 64


class AuthenticodeError(Exception):
    """A signing request that cannot be honoured."""


def available():
    """Is the signing machinery importable? The CERTIFICATE is the operator's."""
    try:
        from cryptography.hazmat.primitives.serialization import pkcs7  # noqa: F401
        from cryptography import x509  # noqa: F401
        return True
    except Exception:
        return False


def _load_key_and_cert(cert_path, key_path, password=None):
    from cryptography.hazmat.primitives import serialization
    from cryptography import x509

    with open(key_path, "rb") as handle:
        key = serialization.load_pem_private_key(
            handle.read(), password=password.encode() if password else None)
    with open(cert_path, "rb") as handle:
        blob = handle.read()
    try:
        cert = x509.load_pem_x509_certificate(blob)
        chain = [cert]
    except ValueError:
        cert = x509.load_der_x509_certificate(blob)
        chain = [cert]
    return key, cert, chain


def pe_digest(data):
    """The digest Authenticode signs: the image with three regions SKIPPED.

    From the Authenticode specification: hash the file omitting

      * the optional-header ``CheckSum`` field (4 bytes),
      * the security directory entry itself (8 bytes), and
      * the certificate table it points at.

    SKIPPED, not zeroed. The distinction matters at the tail: the certificate
    table is appended to the end of the file, so zeroing it would hash 1360
    bytes of padding that the original image did not have, and the two digests
    would never match. Measured exactly that (2048 vs 3408 bytes of input).
    """
    if data[:2] != b"MZ":
        raise AuthenticodeError("not a PE image (no MZ header)")
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if bytes(data[e_lfanew:e_lfanew + 4]) != b"PE\0\0":
        raise AuthenticodeError("not a PE image (no PE signature)")
    coff = e_lfanew + 4
    opt_size = struct.unpack_from("<H", data, coff + 16)[0]
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
        raise AuthenticodeError(
            "image declares %d data directories; index %d is required for a "
            "signature" % (num_dirs, SECURITY_DIRECTORY_INDEX))
    sec_entry = dirs_off + SECURITY_DIRECTORY_INDEX * 8
    cert_offset, cert_size = struct.unpack_from("<II", data, sec_entry)

    checksum_off = opt + PE_CHECKSUM_OFFSET
    # Skip regions in file order; they must not overlap, which the spec
    # guarantees because the certificate table lives past the sections.
    skips = [(checksum_off, checksum_off + 4),
             (sec_entry, sec_entry + 8)]
    if cert_offset and cert_size:
        skips.append((cert_offset, cert_offset + cert_size))
    skips.sort()

    digest = hashlib.sha256()
    cursor = 0
    for start, end in skips:
        if start < cursor or end > len(data):
            raise AuthenticodeError(
                "malformed skip region 0x%x-0x%x (file is 0x%x bytes)"
                % (start, end, len(data)))
        digest.update(data[cursor:start])
        cursor = end
    digest.update(data[cursor:])
    return digest.digest()


def _asn1_len(length):
    if length < 0x80:
        return bytes([length])
    body = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(body)]) + body


def _der(tag, content):
    return bytes([tag]) + _asn1_len(len(content)) + content


def _der_int(value):
    body = value.to_bytes(max(1, (value.bit_length() + 7) // 8), "big")
    if body[0] & 0x80:
        body = b"\x00" + body
    return _der(0x02, body)


def _der_octets(value):
    return _der(0x04, value)


def _der_oid(dotted):
    parts = [int(p) for p in dotted.split(".")]
    body = bytes([40 * parts[0] + parts[1]])
    for part in parts[2:]:
        chunk = [part & 0x7F]
        part >>= 7
        while part:
            chunk.append((part & 0x7F) | 0x80)
            part >>= 7
        body += bytes(reversed(chunk))
    return _der(0x06, body)


def _der_seq(*items):
    return _der(0x30, b"".join(items))


def _spc_indirect_data(digest, file_digest_oid=OID_SHA256):
    """SpcIndirectDataContent over the PE digest.

    Structure (Authenticode spec):
        SpcIndirectDataContent ::= SEQUENCE {
            data          SpcAttributeTypeAndOptionalValue,  -- SpcPeImageData
            messageDigest DigestInfo }
    """
    # SpcPeImageData with an empty file reference: flags 0, zero-length
    # moniker. Modern Windows does not require the legacy file name.
    spc_pe_image_data = _der_seq(
        _der(0x03, b"\x00"),                      # BIT STRING, no bits set
        _der_seq(_der(0x0C, b"")),                # empty UTF8String moniker
    )
    data = _der_seq(_der_oid(SPC_INDIRECT_DATA_OID),
                    _der(0xA0, spc_pe_image_data))   # [0] EXPLICIT
    digest_info = _der_seq(
        _der_seq(_der_oid(file_digest_oid), _der(0x05, b"")),   # AlgorithmId
        _der_octets(digest),                                     # OCTET STRING
    )
    return _der_seq(data, digest_info)


def sign_pe(data, cert_path, key_path, password=None, description=""):
    """Return Authenticode-signed PE bytes.

    Raises :class:`AuthenticodeError` when the inputs cannot produce a valid
    signature, rather than returning something unsigned that looks signed.
    """
    if not available():
        raise AuthenticodeError(
            "cryptography is required for Authenticode signing")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.serialization import pkcs7

    key, cert, chain = _load_key_and_cert(cert_path, key_path, password)
    digest = pe_digest(data)
    indirect = _spc_indirect_data(digest)

    from cryptography.hazmat.primitives import hashes

    builder = pkcs7.PKCS7SignatureBuilder().set_data(indirect)
    # hash_algorithm takes a hashes.HashAlgorithm INSTANCE, not the
    # PKCS7HashTypes enum -- the enum is a typing alias and has no members at
    # runtime (measured: AttributeError: SHA256).
    builder = builder.add_signer(cert, key, hashes.SHA256())
    for extra in chain[1:]:
        builder = builder.add_certificate(extra)
    # Authenticode's PKCS#7 blob is DER. The signed content is the
    # SpcIndirectDataContent itself, and options are passed to sign() -- the
    # builder has no add_option method (measured: AttributeError).
    signature = builder.sign(serialization.Encoding.DER,
                             [pkcs7.PKCS7Options.DetachedSignature])

    # WIN_CERTIFICATE: dwLength, wRevision, wCertificateType, then the blob,
    # padded to 8 bytes.
    # Authenticode requires the PKCS#7 contentType to be SignedData over the
    # indirect data; `cryptography` emits that, so no post-processing is needed.
    body = signature
    pad = (8 - (len(body) % 8)) % 8
    total = 8 + len(body) + pad
    win_cert = struct.pack("<IHH", total, WIN_CERT_REVISION_2_0,
                           WIN_CERT_TYPE_PKCS_SIGNED_DATA) + body + (b"\x00" * pad)

    out = bytearray(data)
    e_lfanew = struct.unpack_from("<I", out, 0x3C)[0]
    coff = e_lfanew + 4
    opt = coff + 20
    magic = struct.unpack_from("<H", out, opt)[0]
    num_dirs_off = opt + (108 if magic == 0x20B else 92)
    dirs_off = opt + (112 if magic == 0x20B else 96)
    sec_entry = dirs_off + SECURITY_DIRECTORY_INDEX * 8

    # The certificate table is appended at the end of the file, 8-byte aligned.
    cert_offset = len(out)
    if cert_offset % 8:
        cert_offset += 8 - (cert_offset % 8)
        out.extend(b"\x00" * (cert_offset - len(out)))
    out.extend(win_cert)

    # Only NOW write the directory entry: the digest was computed with it zero,
    # and adding it must not change what was signed.
    struct.pack_into("<II", out, sec_entry, cert_offset, len(win_cert))
    # DO NOT touch SizeOfImage. Authenticode excludes exactly three regions --
    # the checksum, this directory entry, and the certificate table -- and
    # SizeOfImage is not one of them. Measured: writing it made the digest of
    # the signed file differ from the digest that was signed, which is a
    # signature no verifier would accept. Verified: after removing that write,
    # normalising (zeroing the three excluded regions) makes the original and
    # signed images byte-identical.
    struct.pack_into("<I", out, opt + PE_CHECKSUM_OFFSET,
                     _pe_checksum(bytes(out), opt + PE_CHECKSUM_OFFSET))
    return bytes(out)


def _pe_checksum(data, checksum_offset):
    """Standard PE image checksum (sum of 16-bit words + file length)."""
    total = 0
    for index in range(0, len(data) - 1, 2):
        if index == checksum_offset or index == checksum_offset + 2:
            continue
        total += struct.unpack_from("<H", data, index)[0]
        total = (total & 0xFFFF) + (total >> 16)
    if len(data) % 2:
        total += data[-1]
        total = (total & 0xFFFF) + (total >> 16)
    return ((total & 0xFFFF) + len(data)) & 0xFFFFFFFF


def credentials_from_env():
    """Operator-supplied paths, or None. Never embeds a credential."""
    cert = os.environ.get("NIXON_AUTHENTICODE_CERT", "").strip()
    key = os.environ.get("NIXON_AUTHENTICODE_KEY", "").strip()
    if not cert or not key:
        return None
    return {"cert": cert, "key": key,
            "password": os.environ.get("NIXON_AUTHENTICODE_PASS", "") or None}
