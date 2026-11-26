"""Fail-closed Authenticode CMS verification.

A certificate-table directory is only presence metadata. This module verifies
the actual WIN_CERTIFICATE: bounded PE/DER structure, the Authenticode
``spcIndirectData`` content type, signed attributes, the signer signature, the
encapsulated PE digest, and an optional exact signer-certificate pin.

Cryptographic CMS verification is delegated to the installed OpenSSL ``cms``
backend. No substring/OID/digest search is used, and a missing, failing, or
timed-out backend always returns ``ok=False``. Certificate-chain trust is a
separate policy decision; ``-noverify`` here skips PKI trust, not the signer
signature, signed attributes, or message digest.
"""
from __future__ import annotations

import hashlib
import os
import struct
import subprocess
import tempfile

from obfuscator.authenticode import (
    AuthenticodeError,
    CMS_DATA_OID,
    CMS_SIGNED_DATA_OID,
    OID_CONTENT_TYPE,
    OID_MESSAGE_DIGEST,
    OID_SHA256,
    OPENSSL_CMS_TIMEOUT,
    SPC_INDIRECT_DATA_OID,
    _openssl_environment,
    _openssl_path,
    _pe_layout,
    pe_digest,
)

_TAG_SEQUENCE = 0x30
_TAG_SET = 0x31
_TAG_OID = 0x06
_TAG_OCTETS = 0x04
_TAG_NULL = 0x05
_TAG_INTEGER = 0x02


def _der_node(buf, pos=0):
    """Return (tag, content_start, content_end, next_pos) for strict DER."""
    if pos < 0 or pos + 2 > len(buf):
        raise AuthenticodeError("truncated DER at %d" % pos)
    tag = buf[pos]
    if tag & 0x1F == 0x1F:
        raise AuthenticodeError("high-tag-number DER is not supported")
    first = buf[pos + 1]
    cursor = pos + 2
    if first & 0x80:
        count = first & 0x7F
        if count == 0 or count > 4 or cursor + count > len(buf):
            raise AuthenticodeError("bad DER length at %d" % pos)
        if buf[cursor] == 0:
            raise AuthenticodeError("non-minimal DER length at %d" % pos)
        length = int.from_bytes(buf[cursor:cursor + count], "big")
        if length < 0x80:
            raise AuthenticodeError("non-minimal DER length at %d" % pos)
        cursor += count
    else:
        length = first
    end = cursor + length
    if end > len(buf):
        raise AuthenticodeError(
            "DER content overruns buffer (%d > %d)" % (end, len(buf)))
    return tag, cursor, end, end


def _read_tlv(buf, pos):
    """Compatibility helper: return (tag, content_bytes, next_pos)."""
    tag, start, end, next_pos = _der_node(buf, pos)
    return tag, buf[start:end], next_pos


def _der_children(buf, node):
    tag, start, end, _next = node
    if tag != _TAG_SEQUENCE:
        raise AuthenticodeError("expected DER SEQUENCE")
    children = []
    pos = start
    while pos < end:
        child = _der_node(buf, pos)
        children.append(child)
        pos = child[3]
    if pos != end:
        raise AuthenticodeError("DER SEQUENCE has trailing bytes")
    return children


def _decode_oid(content):
    if not content:
        raise AuthenticodeError("empty OID")
    first = content[0]
    if first < 40:
        arcs = [0, first]
    elif first < 80:
        arcs = [1, first - 40]
    else:
        arcs = [2, first - 80]
    value = 0
    at_start = True
    for byte in content[1:]:
        if at_start and byte == 0x80:
            raise AuthenticodeError("non-minimal OID arc")
        value = (value << 7) | (byte & 0x7F)
        at_start = False
        if not byte & 0x80:
            arcs.append(str(value))
            value = 0
            at_start = True
    if not at_start:
        raise AuthenticodeError("unterminated OID arc")
    return ".".join(str(arc) for arc in arcs)


def _node_oid(buf, node, expected=None):
    if node[0] != _TAG_OID:
        raise AuthenticodeError("expected DER OBJECT IDENTIFIER")
    oid = _decode_oid(buf[node[1]:node[2]])
    if expected is not None and oid != expected:
        raise AuthenticodeError("expected OID %s, got %s" % (expected, oid))
    return oid


def _algorithm_oid(buf, node):
    fields = _der_children(buf, node)
    if not 1 <= len(fields) <= 2:
        raise AuthenticodeError("malformed AlgorithmIdentifier")
    oid = _node_oid(buf, fields[0])
    if len(fields) == 2 and fields[1][0] != _TAG_NULL:
        raise AuthenticodeError("unsupported AlgorithmIdentifier parameters")
    return oid


def _validate_spc_pe_image_data(buf, value_node):
    """Validate the no-page-hash SpcPeImageData profile emitted by sign_pe."""
    if value_node[0] != 0xA0:
        raise AuthenticodeError("SpcPeImageData is not explicitly tagged")
    image = _der_node(buf, value_node[1])
    if image[0] != _TAG_SEQUENCE or image[3] != value_node[2]:
        raise AuthenticodeError("malformed SpcPeImageData")
    fields = _der_children(buf, image)
    if len(fields) != 2 or fields[0][0] != 0x03 or fields[1][0] != 0xA0:
        raise AuthenticodeError("malformed SpcPeImageData flags/file")
    bits = buf[fields[0][1]:fields[0][2]]
    if not bits or bits[0] > 7 or (len(bits) == 1 and bits[0] != 0) \
            or (len(bits) > 1 and bits[-1] & ((1 << bits[0]) - 1)):
        raise AuthenticodeError("malformed SpcPeImageData flags BIT STRING")
    link = _der_node(buf, fields[1][1])
    if link[0] != 0xA2 or link[3] != fields[1][2]:
        raise AuthenticodeError("unsupported or malformed SpcLink file choice")
    spc_string = _der_node(buf, link[1])
    if spc_string[0] not in (0x80, 0x81) or spc_string[3] != link[2]:
        raise AuthenticodeError("malformed SpcString file marker")
    if spc_string[0] == 0x80 and (spc_string[2] - spc_string[1]) % 2:
        raise AuthenticodeError("SpcString BMPSTRING has an odd byte length")


def _parse_spc_indirect_data(buf):
    root = _der_node(buf)
    if root[0] != _TAG_SEQUENCE or root[3] != len(buf):
        raise AuthenticodeError("SpcIndirectDataContent is not one DER SEQUENCE")
    fields = _der_children(buf, root)
    if len(fields) != 2 or fields[0][0] != _TAG_SEQUENCE \
            or fields[1][0] != _TAG_SEQUENCE:
        raise AuthenticodeError("malformed SpcIndirectDataContent")

    attribute = _der_children(buf, fields[0])
    if len(attribute) != 2:
        raise AuthenticodeError("malformed SpcAttributeTypeAndOptionalValue")
    _node_oid(buf, attribute[0], SPC_INDIRECT_DATA_OID)
    _validate_spc_pe_image_data(buf, attribute[1])

    digest_info = _der_children(buf, fields[1])
    if len(digest_info) != 2 or digest_info[0][0] != _TAG_SEQUENCE \
            or digest_info[1][0] != _TAG_OCTETS:
        raise AuthenticodeError("malformed SpcIndirectData DigestInfo")
    if _algorithm_oid(buf, digest_info[0]) != OID_SHA256:
        raise AuthenticodeError("SpcIndirectData digest is not SHA-256")
    digest = buf[digest_info[1][1]:digest_info[1][2]]
    if len(digest) != 32:
        raise AuthenticodeError("SpcIndirectData digest is not 32 bytes")
    return digest


def _parse_signed_attributes(buf, attrs_node, content, econtent_type):
    if attrs_node[0] != 0xA0:
        raise AuthenticodeError("Authenticode SignerInfo lacks signed attributes")
    attributes = _der_children(
        buf, (_TAG_SEQUENCE, attrs_node[1], attrs_node[2], attrs_node[3]))
    seen = set()
    message_digest = None
    for attribute in attributes:
        fields = _der_children(buf, attribute)
        if len(fields) != 2 or fields[1][0] != _TAG_SET:
            raise AuthenticodeError("malformed signed attribute")
        oid = _node_oid(buf, fields[0])
        values = []
        pos = fields[1][1]
        while pos < fields[1][2]:
            value = _der_node(buf, pos)
            values.append(value)
            pos = value[3]
        if not values or pos != fields[1][2]:
            raise AuthenticodeError("signed attribute has no value")
        if oid in (OID_CONTENT_TYPE, OID_MESSAGE_DIGEST):
            if oid in seen or len(values) != 1:
                raise AuthenticodeError("duplicate Authenticode signed attribute")
            seen.add(oid)
        if oid == OID_CONTENT_TYPE:
            actual = _node_oid(buf, values[0])
            if actual != econtent_type or actual != SPC_INDIRECT_DATA_OID:
                raise AuthenticodeError(
                    "signed contentType attribute is not SpcIndirectData")
        elif oid == OID_MESSAGE_DIGEST:
            if values[0][0] != _TAG_OCTETS:
                raise AuthenticodeError("messageDigest attribute is not OCTET STRING")
            message_digest = buf[values[0][1]:values[0][2]]
    if seen != {OID_CONTENT_TYPE, OID_MESSAGE_DIGEST}:
        raise AuthenticodeError("required Authenticode signed attributes are missing")
    expected = hashlib.sha256(content).digest()
    if message_digest != expected:
        raise AuthenticodeError(
            "signed messageDigest attribute does not hash SpcIndirectData")
    return True


def _parse_cms(pkcs7_der):
    """Validate the exact ContentInfo/SignedData path; never search bytes."""
    root = _der_node(pkcs7_der)
    if root[0] != _TAG_SEQUENCE or root[3] != len(pkcs7_der):
        raise AuthenticodeError("CMS ContentInfo is not one DER SEQUENCE")
    content_info = _der_children(pkcs7_der, root)
    if len(content_info) != 2:
        raise AuthenticodeError("malformed CMS ContentInfo")
    _node_oid(pkcs7_der, content_info[0], CMS_SIGNED_DATA_OID)
    if content_info[1][0] != 0xA0:
        raise AuthenticodeError("CMS SignedData is not explicitly tagged")
    signed_data = _der_node(pkcs7_der, content_info[1][1])
    if signed_data[0] != _TAG_SEQUENCE or signed_data[3] != content_info[1][2]:
        raise AuthenticodeError("malformed CMS SignedData wrapper")
    fields = _der_children(pkcs7_der, signed_data)
    if len(fields) < 4 or fields[0][0] != _TAG_INTEGER \
            or fields[1][0] != _TAG_SET or fields[2][0] != _TAG_SEQUENCE:
        raise AuthenticodeError("malformed CMS SignedData structure")

    digest_algorithms = []
    pos = fields[1][1]
    while pos < fields[1][2]:
        algorithm = _der_node(pkcs7_der, pos)
        digest_algorithms.append(_algorithm_oid(pkcs7_der, algorithm))
        pos = algorithm[3]
    if pos != fields[1][2]:
        raise AuthenticodeError("malformed SignedData digestAlgorithms SET")
    if OID_SHA256 not in digest_algorithms:
        raise AuthenticodeError("SignedData does not advertise SHA-256")

    encap = _der_children(pkcs7_der, fields[2])
    if len(encap) != 2 or encap[1][0] != 0xA0:
        raise AuthenticodeError(
            "Authenticode SignedData lacks encapsulated SpcIndirectData")
    econtent_type = _node_oid(pkcs7_der, encap[0])
    if econtent_type == CMS_DATA_OID or econtent_type != SPC_INDIRECT_DATA_OID:
        raise AuthenticodeError(
            "CMS eContentType is not SpcIndirectData (%s)" % SPC_INDIRECT_DATA_OID)
    content = _der_node(pkcs7_der, encap[1][1])
    if content[0] != _TAG_OCTETS or content[3] != encap[1][2]:
        raise AuthenticodeError("encapsulated SpcIndirectData is not one OCTET STRING")
    indirect = pkcs7_der[content[1]:content[2]]
    declared_digest = _parse_spc_indirect_data(indirect)

    index = 3
    embedded_cert = False
    if index < len(fields) and fields[index][0] == 0xA0:
        cert_pos = fields[index][1]
        while cert_pos < fields[index][2]:
            cert = _der_node(pkcs7_der, cert_pos)
            if cert[0] != _TAG_SEQUENCE:
                raise AuthenticodeError("SignedData certificate choice is not X.509")
            embedded_cert = True
            cert_pos = cert[3]
        index += 1
    if index < len(fields) and fields[index][0] == 0xA1:
        index += 1                         # structurally bounded CRL set
    if index != len(fields) - 1 or fields[index][0] != _TAG_SET:
        raise AuthenticodeError("SignedData lacks a final signerInfos SET")
    if not embedded_cert:
        raise AuthenticodeError("SignedData carries no signer certificate")

    signer_pos = fields[index][1]
    signer = _der_node(pkcs7_der, signer_pos)
    if signer[0] != _TAG_SEQUENCE or signer[3] != fields[index][2]:
        raise AuthenticodeError("exactly one CMS signer is required")
    signer_fields = _der_children(pkcs7_der, signer)
    if len(signer_fields) < 6 or signer_fields[0][0] != _TAG_INTEGER:
        raise AuthenticodeError("malformed CMS SignerInfo")
    if signer_fields[1][0] not in (_TAG_SEQUENCE, 0x80):
        raise AuthenticodeError("malformed CMS signer identifier")
    if signer_fields[2][0] != _TAG_SEQUENCE \
            or _algorithm_oid(pkcs7_der, signer_fields[2]) != OID_SHA256:
        raise AuthenticodeError("CMS signer digest algorithm is not SHA-256")
    message_digest_matches = _parse_signed_attributes(
        pkcs7_der, signer_fields[3], indirect, econtent_type)
    if signer_fields[4][0] != _TAG_SEQUENCE:
        raise AuthenticodeError("malformed CMS signatureAlgorithm")
    _algorithm_oid(pkcs7_der, signer_fields[4])
    if signer_fields[5][0] != _TAG_OCTETS \
            or signer_fields[5][1] == signer_fields[5][2]:
        raise AuthenticodeError("CMS signer signature is empty or malformed")
    if len(signer_fields) not in (6, 7) \
            or (len(signer_fields) == 7 and signer_fields[6][0] != 0xA1):
        raise AuthenticodeError("malformed unsigned signer attributes")

    return {"econtent_type": econtent_type, "content": indirect,
            "declared_digest": declared_digest,
            "content_type_matches": True,
            "message_digest_matches": message_digest_matches,
            "embedded_cert": embedded_cert}


def _extract_pkcs7(data):
    """Return (cert_blob, dwLength, revision, cert_type) from a bounded PE."""
    layout = _pe_layout(data)
    if not layout["cert_offset"] or not layout["cert_size"]:
        raise AuthenticodeError("image carries no certificate table")
    if layout["cert_size"] < 8:
        raise AuthenticodeError("WIN_CERTIFICATE shorter than its header")
    table = data[layout["cert_offset"]:
                 layout["cert_offset"] + layout["cert_size"]]
    dw_length, revision, cert_type = struct.unpack_from("<IHH", table, 0)
    if dw_length != layout["cert_size"]:
        raise AuthenticodeError(
            "WIN_CERTIFICATE dwLength %d inconsistent with table %d"
            % (dw_length, layout["cert_size"]))
    return table[8:dw_length], dw_length, revision, cert_type


def _der_length_of(blob):
    """Total strict-DER length of the outer ContentInfo SEQUENCE."""
    node = _der_node(blob)
    if node[0] != _TAG_SEQUENCE:
        raise AuthenticodeError("PKCS#7 blob does not start with a DER SEQUENCE")
    return node[3]


def _openssl_verify(pkcs7_der, content):
    openssl = _openssl_path()
    if openssl is None:
        raise AuthenticodeError("OpenSSL CMS verification backend unavailable")
    try:
        with tempfile.TemporaryDirectory(prefix="nixon-authenticode-verify-") as tmp:
            cms_path = os.path.join(tmp, "signature.der")
            content_path = os.path.join(tmp, "indirect.der")
            signer_path = os.path.join(tmp, "signer.pem")
            verified_path = os.path.join(tmp, "verified.der")
            with open(cms_path, "wb") as handle:
                handle.write(pkcs7_der)
            with open(content_path, "wb") as handle:
                handle.write(content)
            cmd = [openssl, "cms", "-verify", "-binary", "-inform", "DER",
                   "-in", cms_path, "-content", content_path, "-noverify",
                   "-verify_retcode", "-signer", signer_path,
                   "-out", verified_path]
            try:
                result = subprocess.run(
                    cmd, stdin=subprocess.DEVNULL, capture_output=True,
                    timeout=OPENSSL_CMS_TIMEOUT, check=False,
                    env=_openssl_environment())
            except subprocess.TimeoutExpired as exc:
                raise AuthenticodeError("OpenSSL CMS verification timed out") from exc
            except OSError as exc:
                raise AuthenticodeError(
                    "OpenSSL CMS verification backend unavailable (%s)"
                    % type(exc).__name__) from exc
            if result.returncode != 0:
                detail = result.stderr.decode("utf-8", "replace").strip()[-240:]
                raise AuthenticodeError(
                    "CMS signer signature or signed attributes failed verification%s"
                    % (": " + detail if detail else ""))
            with open(verified_path, "rb") as handle:
                verified = handle.read()
            with open(signer_path, "rb") as handle:
                signer_pem = handle.read()
    except OSError as exc:
        raise AuthenticodeError(
            "could not create CMS verification files (%s)" % type(exc).__name__) from exc
    if verified != content:
        raise AuthenticodeError(
            "CMS verified content does not match encapsulated SpcIndirectData")
    if not signer_pem:
        raise AuthenticodeError("OpenSSL CMS returned no signer certificate")
    return signer_pem


def _certificate_der(blob):
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization

    try:
        cert = x509.load_pem_x509_certificate(blob)
    except ValueError:
        cert = x509.load_der_x509_certificate(blob)
    return cert.public_bytes(serialization.Encoding.DER)


def verify_pe_signature(data, cert_path=None):
    """Verify the embedded Authenticode signature and optional exact cert pin.

    The returned schema is stable on every path. ``ok`` becomes True only
    after structural checks, PE-digest equality, signed-attribute checks,
    OpenSSL signer-signature verification, and (when supplied) exact signer
    certificate equality all succeed.
    """
    out = {"ok": False, "reason": "", "revision": None, "cert_type": None,
           "cert_bytes": 0, "declared_digest": None, "current_digest": None,
           "digest_matches": False, "embedded_cert": False,
           "pinned_cert_matches": False if cert_path else None,
           "econtent_type": None, "content_type_matches": False,
           "message_digest_matches": False, "signer_signature_verified": False,
           "cms_backend": None}
    try:
        blob, dw_length, revision, cert_type = _extract_pkcs7(data)
        out.update({"revision": revision, "cert_type": cert_type,
                    "cert_bytes": dw_length})
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
        if any(blob[der_len:]):
            out["reason"] = "WIN_CERTIFICATE has nonzero bytes after DER"
            return out
        pkcs7_der = blob[:der_len]
        parsed = _parse_cms(pkcs7_der)
        out.update({"econtent_type": parsed["econtent_type"],
                    "content_type_matches": parsed["content_type_matches"],
                    "message_digest_matches": parsed["message_digest_matches"],
                    "embedded_cert": parsed["embedded_cert"],
                    "declared_digest": parsed["declared_digest"].hex()})

        current = pe_digest(data)
        out["current_digest"] = current.hex()
        if current != parsed["declared_digest"]:
            out["reason"] = (
                "encapsulated SpcIndirectData digest does not match this PE: "
                "the file was modified after signing or covers another image")
            return out
        out["digest_matches"] = True

        signer_pem = _openssl_verify(pkcs7_der, parsed["content"])
        out["signer_signature_verified"] = True
        out["cms_backend"] = "openssl-cms"
        if cert_path:
            with open(cert_path, "rb") as handle:
                pinned = _certificate_der(handle.read())
            signer = _certificate_der(signer_pem)
            out["pinned_cert_matches"] = pinned == signer
            if not out["pinned_cert_matches"]:
                out["reason"] = (
                    "embedded signer certificate does not match the pinned one")
                return out
        out["ok"] = True
        out["reason"] = (
            "CMS signer signature, signed attributes, and PE digest verified")
    except AuthenticodeError as exc:
        out["reason"] = str(exc)
    except Exception as exc:
        out["reason"] = "signature verification failed (%s)" % type(exc).__name__
    return out
