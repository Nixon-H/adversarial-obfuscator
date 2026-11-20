"""§3 Authenticode: the mechanism, gated on an operator-supplied certificate.

The honest status before this was "Authenticode not present, and cannot be
trusted here" — correct about the CERTIFICATE, wrong to leave the mechanism
unimplemented. A self-signed certificate is not trusted by Windows, so shipping
one would make the artefact look signed while changing nothing the OS enforces.

What is testable, and what these tests establish:

  * the digest Authenticode signs is computed over the image with exactly three
    regions SKIPPED — the checksum, the security directory entry, and the
    certificate table — and that digest is IDENTICAL before and after signing.
    That identity is the property that makes a signature verifiable at all, and
    getting it wrong yields a file that carries a signature and fails every
    verifier;
  * the emitted blob is a WIN_CERTIFICATE of revision 2.0 / type 0x0002 wrapping
    a parseable PKCS#7 SignedData whose certificate chain is the operator's;
  * the security directory points at it, and `native_harden.verify_pe_bytes`
    reports `authenticode: True` from the bytes rather than from a claim;
  * signing is REFUSED when no certificate is supplied, so a build never ships
    a signature it cannot produce.
"""
import os
import struct
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def _authenticode():
    return pytest.importorskip("obfuscator.authenticode")


def _make_cert(tmp_path):
    """Generate a throwaway key + certificate for the MECHANISM tests.

    Explicitly NOT a credential: it is created per-test, never written into the
    repository, and cannot sign anything a platform would trust. Its only job is
    to let the signing code run end to end.
    """
    pytest.importorskip("cryptography")
    import datetime

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "nx-test-only")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=1))
            .sign(key, hashes.SHA256()))
    cert_path = tmp_path / "c.pem"
    key_path = tmp_path / "k.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    return str(cert_path), str(key_path)


def _pe(**overrides):
    """A minimal PE for signing tests: headers only, plus a stub section."""
    ac = _authenticode()
    e_lfanew = 0x80
    head = bytearray(e_lfanew)
    head[0:2] = b"MZ"
    struct.pack_into("<I", head, 0x3C, e_lfanew)
    coff = bytearray(20)
    struct.pack_into("<H", coff, 0, 0x8664)
    struct.pack_into("<H", coff, 2, 1)
    struct.pack_into("<H", coff, 16, 0xF0)
    opt = bytearray(0xF0)
    struct.pack_into("<H", opt, 0, 0x20B)
    struct.pack_into("<H", opt, 70, overrides.get("dll", 0x4160))
    struct.pack_into("<I", opt, 56, 0x2000)      # SizeOfImage
    struct.pack_into("<I", opt, 108, 16)         # NumberOfRvaAndSizes
    struct.pack_into("<II", opt, 112 + 10 * 8, 0x3000, 0x48)   # load config
    body = bytes(head) + b"PE\0\0" + bytes(coff) + bytes(opt)
    return body + b"\x00" * 512


# ── the digest: the property that makes a signature verifiable ───────────

def test_the_digest_is_identical_before_and_after_signing(tmp_path):
    """THE critical property.

    Authenticode signs the image with the checksum, the security directory
    entry and the certificate table skipped. If signing changed any other byte,
    the digest a verifier recomputes would differ from the one that was signed
    and the signature would be worthless.

    Two bugs were found here by this assertion: writing SizeOfImage during
    signing (it is NOT an excluded region), and ZEROING the certificate table
    instead of skipping it (which hashed 1360 padding bytes the original image
    never had).
    """
    ac = _authenticode()
    cert, key = _make_cert(tmp_path)
    original = _pe()
    signed = ac.sign_pe(original, cert, key)
    assert signed != original
    assert len(signed) > len(original)
    assert ac.pe_digest(original) == ac.pe_digest(signed)


def test_the_three_excluded_regions_are_the_only_ones(tmp_path):
    """Normalising the three regions makes the two images agree byte for byte.

    A stronger statement than digest equality: it shows nothing ELSE moved. The
    signed image is truncated back to the original length after normalisation,
    because the certificate table was appended past the original EOF and is one
    of the regions we zero.
    """
    ac = _authenticode()
    cert, key = _make_cert(tmp_path)
    original = _pe()
    signed = ac.sign_pe(original, cert, key)

    def normalise(data, length):
        raw = bytearray(data[:length])
        e = struct.unpack_from("<I", raw, 0x3C)[0]
        opt = e + 4 + 20
        struct.pack_into("<I", raw, opt + 64, 0)                 # checksum
        struct.pack_into("<II", raw, opt + 112 + 4 * 8, 0, 0)    # dir entry
        return bytes(raw)

    assert normalise(original, len(original)) == normalise(signed, len(original))


# ── the emitted structure ────────────────────────────────────────────────

def test_the_security_directory_points_at_a_win_certificate(tmp_path):
    ac = _authenticode()
    cert, key = _make_cert(tmp_path)
    signed = ac.sign_pe(_pe(), cert, key)
    e = struct.unpack_from("<I", signed, 0x3C)[0]
    opt = e + 4 + 20
    offset, size = struct.unpack_from("<II", signed, opt + 112 + 4 * 8)
    assert offset > 0 and size > 8
    length, revision, ctype = struct.unpack_from("<IHH", signed, offset)
    assert revision == ac.WIN_CERT_REVISION_2_0
    assert ctype == ac.WIN_CERT_TYPE_PKCS_SIGNED_DATA
    assert length == size, "dwLength must match the directory entry"
    assert length % 8 == 0, "WIN_CERTIFICATE must be 8-byte aligned"


def test_the_payload_is_parseable_pkcs7_carrying_the_operators_cert(tmp_path):
    ac = _authenticode()
    cert, key = _make_cert(tmp_path)
    signed = ac.sign_pe(_pe(), cert, key)
    e = struct.unpack_from("<I", signed, 0x3C)[0]
    opt = e + 4 + 20
    offset, size = struct.unpack_from("<II", signed, opt + 112 + 4 * 8)
    blob = signed[offset + 8:offset + size]
    assert blob[0] == 0x30, "PKCS#7 blob must start with a DER SEQUENCE"
    # WIN_CERTIFICATE pads the blob to 8 bytes, so the DER SEQUENCE is shorter
    # than the padding-rounded field. Trim to the declared length: parsing the
    # padded bytes makes `cryptography` warn about "ExtraData" and fall back to
    # BER, which is expected but noisy.
    if blob[1] & 0x80:
        nlen = blob[1] & 0x7F
        der_len = 2 + nlen + int.from_bytes(blob[2:2 + nlen], "big")
    else:
        der_len = 2 + blob[1]
    blob = blob[:der_len]
    from cryptography.hazmat.primitives.serialization import pkcs7
    certs = pkcs7.load_der_pkcs7_certificates(blob)
    assert len(certs) >= 1
    assert "nx-test-only" in certs[0].subject.rfc4514_string()


def test_verify_pe_bytes_reads_the_signature_from_the_bytes(tmp_path):
    """The verifier must report what the object carries, not what we say."""
    from obfuscator import native_harden as nh
    ac = _authenticode()
    cert, key = _make_cert(tmp_path)
    unsigned = _pe()
    signed = ac.sign_pe(unsigned, cert, key)
    assert nh.verify_pe_bytes(unsigned)["authenticode"] is False
    report = nh.verify_pe_bytes(signed)
    assert report["authenticode"] is True
    assert report["valid"] is True
    # Signing must not disturb the other hardening bits.
    assert report["aslr"] is True and report["dep"] is True


# ── refusals ─────────────────────────────────────────────────────────────

def test_signing_a_non_pe_is_refused(tmp_path):
    ac = _authenticode()
    cert, key = _make_cert(tmp_path)
    for blob in (b"", b"not a pe", b"MZ" + b"\x00" * 200):
        with pytest.raises(ac.AuthenticodeError):
            ac.sign_pe(blob, cert, key)


def test_no_certificate_from_the_environment_means_no_signing(monkeypatch):
    """A build must never ship a signature it could not produce.

    `credentials_from_env` returning None is what the build gates on; an
    unset variable must not be treated as "sign with something".
    """
    ac = _authenticode()
    for var in ("NIXON_AUTHENTICODE_CERT", "NIXON_AUTHENTICODE_KEY",
                "NIXON_AUTHENTICODE_PASS"):
        monkeypatch.delenv(var, raising=False)
    assert ac.credentials_from_env() is None

    monkeypatch.setenv("NIXON_AUTHENTICODE_CERT", "/tmp/x.pem")
    assert ac.credentials_from_env() is None, (
        "a certificate without a key must not count as configured")


def test_credentials_are_read_from_the_environment_only(monkeypatch):
    """The operator supplies paths via env vars; nothing is embedded here."""
    ac = _authenticode()
    monkeypatch.setenv("NIXON_AUTHENTICODE_CERT", "/c.pem")
    monkeypatch.setenv("NIXON_AUTHENTICODE_KEY", "/k.pem")
    monkeypatch.delenv("NIXON_AUTHENTICODE_PASS", raising=False)
    got = ac.credentials_from_env()
    assert got == {"cert": "/c.pem", "key": "/k.pem", "password": None}


def test_a_missing_key_file_raises_rather_than_signing(tmp_path):
    ac = _authenticode()
    cert, _key = _make_cert(tmp_path)
    with pytest.raises(Exception):
        ac.sign_pe(_pe(), cert, str(tmp_path / "nope.pem"))


# ── the signature must be WINDOWS-Valid, and verifiable (2026-11-20) ─────
#
# Before this batch the signer emitted a generic PKCS#7 signature: the image
# digest was hashed into the messageDigest attribute, but the
# SpcIndirectDataContent was DETACHED, so the spcIndirectData OID never
# appeared in the blob and the image digest was not embedded. Windows would
# not have recognised the file as signed, while native_harden reported
# authenticode: True on the strength of a non-empty directory.

SPC_OID_DER = bytes.fromhex("060a2b060104018237020104")


def test_the_signed_blob_carries_the_spc_indirect_data_oid(tmp_path):
    """Authenticode's contentType must be spcIndirectData, not pkcs7-data."""
    ac = _authenticode()
    cert, key = _make_cert(tmp_path)
    signed = ac.sign_pe(_pe(), cert, key)
    assert SPC_OID_DER in signed, (
        "the spcIndirectData OID is absent: this is a generic PKCS#7 "
        "signature that Windows will not accept as Authenticode")


def test_the_signed_blob_embeds_the_image_digest(tmp_path):
    """The signed content must CONTAIN the digest, not just hash it."""
    ac = _authenticode()
    cert, key = _make_cert(tmp_path)
    unsigned = _pe()
    signed = ac.sign_pe(unsigned, cert, key)
    assert ac.pe_digest(unsigned) in signed, (
        "the image's Authenticode digest is not embedded in the signed "
        "content; a Windows verifier has nothing to compare against")


def test_the_verifier_accepts_a_signature_it_produced(tmp_path):
    from obfuscator.authenticode_verify import verify_pe_signature
    ac = _authenticode()
    cert, key = _make_cert(tmp_path)
    signed = ac.sign_pe(_pe(), cert, key)
    report = verify_pe_signature(signed)
    assert report["ok"] is True, report["reason"]
    assert report["digest_matches"] is True
    assert report["revision"] == 0x0200
    assert report["cert_type"] == 0x0002


def test_the_verifier_rejects_an_image_modified_after_signing(tmp_path):
    """THE property that makes a signature a signature."""
    from obfuscator.authenticode_verify import verify_pe_signature
    ac = _authenticode()
    cert, key = _make_cert(tmp_path)
    signed = bytearray(ac.sign_pe(_pe(), cert, key))
    signed[0x200] ^= 0xFF              # one byte inside the image body
    report = verify_pe_signature(bytes(signed))
    assert report["ok"] is False
    assert "does not appear in the signed content" in report["reason"]


def test_the_verifier_rejects_an_unsigned_image(tmp_path):
    from obfuscator.authenticode_verify import verify_pe_signature
    report = verify_pe_signature(_pe())
    assert report["ok"] is False
    assert "no certificate table" in report["reason"]


def test_native_harden_separates_presence_from_verification(tmp_path):
    """A certificate table existing must not read as 'signed'."""
    from obfuscator import native_harden as nh
    ac = _authenticode()
    cert, key = _make_cert(tmp_path)
    unsigned_rep = nh.verify_pe_bytes(_pe())
    assert unsigned_rep["authenticode"] is False
    assert unsigned_rep["authenticode_verified"] is False
    signed_rep = nh.verify_pe_bytes(ac.sign_pe(_pe(), cert, key))
    assert signed_rep["authenticode"] is True
    assert signed_rep["authenticode_verified"] is True, (
        "the digest does not verify: %s"
        % (signed_rep.get("authenticode_reason"),))
