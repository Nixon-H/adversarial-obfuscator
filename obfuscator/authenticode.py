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
import shutil
import struct
import subprocess
import tempfile

#: PE security directory index.
SECURITY_DIRECTORY_INDEX = 4

#: WIN_CERTIFICATE revision 2.0 and type 0x0002 (PKCS#7).
WIN_CERT_REVISION_2_0 = 0x0200
WIN_CERT_TYPE_PKCS_SIGNED_DATA = 0x0002

#: The SpcIndirectDataContent OID used by Authenticode for PE images.
SPC_INDIRECT_DATA_OID = "1.3.6.1.4.1.311.2.1.4"

#: CMS/PKCS#7 object identifiers needed by the Authenticode profile.
CMS_SIGNED_DATA_OID = "1.2.840.113549.1.7.2"
CMS_DATA_OID = "1.2.840.113549.1.7.1"
OID_SHA256 = "2.16.840.1.101.3.4.2.1"
OID_CONTENT_TYPE = "1.2.840.113549.1.9.3"
OID_MESSAGE_DIGEST = "1.2.840.113549.1.9.4"

#: Every CMS subprocess is bounded; verification must fail closed on timeout.
OPENSSL_CMS_TIMEOUT = 30

#: Offset of the checksum field in both PE32 and PE32+ optional headers.
PE_CHECKSUM_OFFSET = 64


class AuthenticodeError(Exception):
    """A signing request that cannot be honoured."""


def _openssl_path():
    """Return the real OpenSSL CMS backend, or None (never a fake fallback)."""
    return shutil.which("openssl")


def _openssl_environment():
    """Do not let ambient OpenSSL config/provider variables redirect the CMS."""
    env = os.environ.copy()
    for name in ("OPENSSL_CONF", "OPENSSL_CONF_INCLUDE", "OPENSSL_MODULES",
                 "OPENSSL_ENGINES"):
        env.pop(name, None)
    return env


def available():
    """Whether real CMS signing is available; absence is a hard refusal."""
    if _openssl_path() is None:
        return False
    try:
        from cryptography import x509  # noqa: F401
        from cryptography.hazmat.primitives import serialization  # noqa: F401
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
        chain = x509.load_pem_x509_certificates(blob)
    except ValueError:
        chain = [x509.load_der_x509_certificate(blob)]
    if not chain:
        raise AuthenticodeError("certificate file contains no certificate")
    return key, chain[0], chain


def _pe_layout(data):
    """Validate PE bounds and return the fields used by signing/verification.

    The security directory is a FILE OFFSET, unlike the other data directories.
    Its complete table, the optional header, the declared directory array and
    the section table are all checked before any field is trusted.
    """
    if len(data) < 64 or data[:2] != b"MZ":
        raise AuthenticodeError("not a PE image (no complete MZ header)")
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if e_lfanew < 64 or e_lfanew + 24 > len(data):
        raise AuthenticodeError("PE signature/COFF header is out of bounds")
    if data[e_lfanew:e_lfanew + 4] != b"PE\0\0":
        raise AuthenticodeError("not a PE image (no PE signature)")

    coff = e_lfanew + 4
    num_sections = struct.unpack_from("<H", data, coff + 2)[0]
    opt_size = struct.unpack_from("<H", data, coff + 16)[0]
    opt = coff + 20
    opt_end = opt + opt_size
    if opt_size < 68 or opt_end > len(data):
        raise AuthenticodeError("truncated optional header")
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic == 0x20B:
        num_dirs_off, dirs_off = opt + 108, opt + 112
    elif magic == 0x10B:
        num_dirs_off, dirs_off = opt + 92, opt + 96
    else:
        raise AuthenticodeError("unknown optional-header magic 0x%x" % (magic,))
    if num_dirs_off + 4 > opt_end:
        raise AuthenticodeError("optional header omits NumberOfRvaAndSizes")

    num_dirs = struct.unpack_from("<I", data, num_dirs_off)[0]
    if dirs_off + num_dirs * 8 > opt_end:
        raise AuthenticodeError("data directory table exceeds optional header")
    section_table = opt_end
    if num_sections * 40 > len(data) - section_table:
        raise AuthenticodeError("section table exceeds file bounds")

    sec_entry = None
    cert_offset = cert_size = 0
    if num_dirs > SECURITY_DIRECTORY_INDEX:
        sec_entry = dirs_off + SECURITY_DIRECTORY_INDEX * 8
        cert_offset, cert_size = struct.unpack_from("<II", data, sec_entry)
    if bool(cert_offset) != bool(cert_size):
        raise AuthenticodeError("incomplete security directory entry")
    if cert_offset or cert_size:
        if cert_offset % 8 or cert_size % 8:
            raise AuthenticodeError("certificate table is not 8-byte aligned")
        if cert_offset < section_table + num_sections * 40:
            raise AuthenticodeError("certificate table overlaps PE headers")
        if cert_offset > len(data) or cert_size > len(data) - cert_offset:
            raise AuthenticodeError(
                "certificate table (%d+%d) overruns the file (%d bytes)"
                % (cert_offset, cert_size, len(data)))
        if cert_offset + cert_size != len(data):
            raise AuthenticodeError("certificate table is not at end of file")

    return {"e_lfanew": e_lfanew, "coff": coff, "opt": opt,
            "opt_size": opt_size, "opt_end": opt_end, "magic": magic,
            "num_dirs": num_dirs, "num_dirs_off": num_dirs_off,
            "dirs_off": dirs_off, "sec_entry": sec_entry,
            "cert_offset": cert_offset, "cert_size": cert_size,
            "checksum_off": opt + PE_CHECKSUM_OFFSET,
            "header_end": section_table + num_sections * 40}


def pe_digest(data):
    """The Authenticode SHA-256 digest, with exactly three regions skipped.

    The optional-header checksum, security-directory entry and certificate
    table are omitted rather than zeroed. All PE and certificate-table bounds
    are validated first so malformed input cannot become a digest claim.
    """
    layout = _pe_layout(data)
    skips = [(layout["checksum_off"], layout["checksum_off"] + 4)]
    if layout["sec_entry"] is not None:
        skips.append((layout["sec_entry"], layout["sec_entry"] + 8))
    # The certificate table is outside the hashed range entirely; adding it as
    # a skip region made its end exceed hash_end after signing.
    skips.sort()
    hash_end = layout["cert_offset"] or len(data)

    digest = hashlib.sha256()
    cursor = 0
    for start, end in skips:
        if start < cursor or end > hash_end:
            raise AuthenticodeError(
                "malformed skip region 0x%x-0x%x (hash end is 0x%x bytes)"
                % (start, end, hash_end))
        digest.update(data[cursor:start])
        cursor = end
    digest.update(data[cursor:hash_end])
    # Authenticode hashes an unsigned PE through its 8-byte alignment padding.
    # A signed PE already contains that padding immediately before WIN_CERT.
    if not layout["cert_offset"] and hash_end % 8:
        digest.update(b"\x00" * (8 - hash_end % 8))
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
    # SpcPeImageData ::= SEQUENCE { flags BIT STRING,
    #                               file [0] EXPLICIT SpcLink OPTIONAL }
    # SpcLink.file is [2] EXPLICIT SpcString; its Unicode choice is [0]
    # IMPLICIT BMPSTRING. Authenticode tools use the legacy <<<Obsolete>>>>
    # marker when no page hashes are supplied. The flags BIT STRING has bit 0
    # set (seven unused bits, final byte 0x80).
    obsolete = "<<<Obsolete>>>".encode("utf-16-be")
    spc_string = _der(0x80, obsolete)
    spc_link = _der(0xA2, spc_string)
    spc_pe_image_data = _der_seq(
        _der(0x03, b"\x07\x80"),
        _der(0xA0, spc_link),
    )
    data = _der_seq(_der_oid(SPC_INDIRECT_DATA_OID),
                    _der(0xA0, spc_pe_image_data))   # [0] EXPLICIT
    digest_info = _der_seq(
        _der_seq(_der_oid(file_digest_oid), _der(0x05, b"")),   # AlgorithmId
        _der_octets(digest),                                     # OCTET STRING
    )
    return _der_seq(data, digest_info)


def sign_pe(data, cert_path, key_path, password=None, description=""):
    """Return an Authenticode-signed PE using the real OpenSSL CMS backend.

    ``description`` is retained for API compatibility. The CMS encapsulated
    content type is always ``spcIndirectData``; generic ``pkcs7-data`` is not
    accepted as an Authenticode substitute. Existing certificate tables are
    refused because this module implements one signer, not nested signatures.
    """
    del description
    layout = _pe_layout(data)
    if layout["sec_entry"] is None:
        raise AuthenticodeError(
            "optional header declares %d data directories; cannot hold the "
            "security directory (index %d)"
            % (layout["num_dirs"], SECURITY_DIRECTORY_INDEX))
    if layout["cert_offset"] or layout["cert_size"]:
        raise AuthenticodeError(
            "image already carries a certificate table; multiple signatures "
            "are not supported")
    if not available():
        raise AuthenticodeError(
            "OpenSSL CMS and cryptography are required for Authenticode signing")

    try:
        _key, cert, chain = _load_key_and_cert(cert_path, key_path, password)
    except AuthenticodeError:
        raise
    except Exception as exc:
        raise AuthenticodeError(
            "could not load signing certificate/key (%s)" % type(exc).__name__) from exc

    from cryptography.hazmat.primitives import serialization

    digest = pe_digest(data)
    indirect = _spc_indirect_data(digest)
    try:
        with tempfile.TemporaryDirectory(prefix="nixon-authenticode-") as tmp:
            content_path = os.path.join(tmp, "indirect.der")
            signer_path = os.path.join(tmp, "signer.pem")
            signature_path = os.path.join(tmp, "signature.der")
            with open(content_path, "wb") as handle:
                handle.write(indirect)
            with open(signer_path, "wb") as handle:
                handle.write(cert.public_bytes(serialization.Encoding.PEM))

            # `-no_signing_time` is rejected by OpenSSL 3.0 (Ubuntu 24.04).
            # The signingTime attribute is not part of the Authenticode
            # digest contract, so omitting the flag works across versions.
            cmd = [_openssl_path(), "cms", "-sign", "-binary", "-nodetach",
                   "-nosmimecap", "-md", "sha256",
                   "-econtent_type", SPC_INDIRECT_DATA_OID,
                   "-in", content_path, "-signer", signer_path,
                   "-inkey", key_path, "-outform", "DER", "-out", signature_path]
            if len(chain) > 1:
                chain_path = os.path.join(tmp, "chain.pem")
                with open(chain_path, "wb") as handle:
                    for extra in chain[1:]:
                        handle.write(extra.public_bytes(serialization.Encoding.PEM))
                        handle.write(b"\n")
                cmd.extend(["-certfile", chain_path])
            if password:
                cmd.extend(["-passin", "stdin"])
            try:
                result = subprocess.run(
                    cmd, input=password.encode() if password else None,
                    stdin=None if password else subprocess.DEVNULL,
                    capture_output=True, timeout=OPENSSL_CMS_TIMEOUT,
                    env=_openssl_environment(), check=False)
            except subprocess.TimeoutExpired as exc:
                raise AuthenticodeError("OpenSSL CMS signing timed out") from exc
            except OSError as exc:
                raise AuthenticodeError(
                    "OpenSSL CMS signing backend unavailable (%s)"
                    % type(exc).__name__) from exc
            if result.returncode != 0:
                detail = result.stderr.decode("utf-8", "replace").strip()[-240:]
                raise AuthenticodeError(
                    "OpenSSL CMS signing failed%s"
                    % (": " + detail if detail else ""))
            with open(signature_path, "rb") as handle:
                signature = handle.read()
    except OSError as exc:
        raise AuthenticodeError(
            "could not create CMS signing files (%s)" % type(exc).__name__) from exc

    if not signature or signature[:1] != b"\x30":
        raise AuthenticodeError("OpenSSL CMS returned no DER SignedData")

    # WIN_CERTIFICATE: dwLength, revision, type, DER, then 8-byte padding.
    pad = (8 - len(signature) % 8) % 8
    total = 8 + len(signature) + pad
    win_cert = struct.pack("<IHH", total, WIN_CERT_REVISION_2_0,
                           WIN_CERT_TYPE_PKCS_SIGNED_DATA) + signature + b"\x00" * pad

    out = bytearray(data)
    # The security directory must point at the FIRST byte of WIN_CERTIFICATE,
    # not at the alignment padding that may precede it.  Taking the offset
    # before padding leaves it unaligned for PE images whose length is not
    # already a multiple of eight; the resulting file cannot even pass this
    # module's own layout validation.
    cert_offset = len(out) + ((8 - len(out) % 8) % 8)
    out.extend(b"\x00" * (cert_offset - len(out)))
    out.extend(win_cert)
    struct.pack_into("<II", out, layout["sec_entry"], cert_offset, len(win_cert))
    struct.pack_into("<I", out, layout["checksum_off"],
                     _pe_checksum(bytes(out), layout["checksum_off"]))
    if pe_digest(out) != digest:
        raise AuthenticodeError("internal error: signing changed the PE digest")
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
