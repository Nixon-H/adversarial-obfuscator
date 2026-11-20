"""§7: the manifest must record the native blob the artefact actually carries.

Measured 2026-11-20. A `--package native` build produced a deliverable whose
`NATIVE_BLOBS` held a 110,488-byte .so, and running it loaded that module from
a temp `_nx_*.so` (module origin proved the native path, not bytecode). The
build manifest beside the very same artefact said:

    "native_blob": {"bytes": 0, "sha256": ""}

Two independent facts were wrong with that:

  * It was FALSE. A reader using the manifest to answer "is this artefact
    native, and which object is inside it" got the opposite answer.
  * It was UNFIXABLE by inspection. The compiled modules never touch disk --
    the build holds them base64-encoded and XOR-packs them straight into the
    loader -- so there was no path for `native_blob_path` to hash, and no
    caller ever set it. A control that can only ever report "absent" is worse
    than no control: it trains a reader to ignore the field.

These tests pin the replacement contract: the record is built from the
in-memory mapping, covers every embedded platform, states which form the hash
covers, and stays honestly empty for a bytecode-only artefact.
"""
import base64
import hashlib
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.build_manifest import write_manifest  # noqa: E402


def _artefact(tmp_path, body="print('x')\n"):
    p = tmp_path / "art.py"
    p.write_text(body, encoding="utf-8")
    return str(p)


def _record(tmp_path, **kwargs):
    art = _artefact(tmp_path)
    path = write_manifest(art, **kwargs)
    return json.loads(open(path, encoding="utf-8").read())["native_blob"]


def test_native_blob_record_is_written_from_the_in_memory_mapping(tmp_path):
    """The exact defect: a real blob must not be recorded as bytes: 0."""
    elf = b"\x7fELF" + bytes(range(256)) * 4
    rec = _record(tmp_path, native_blobs={
        "linux": base64.b64encode(elf).decode("ascii")})
    assert rec["bytes"] == len(elf), rec
    assert rec["sha256"] == hashlib.sha256(elf).hexdigest(), rec
    assert rec["platforms"]["linux"]["bytes"] == len(elf), rec


def test_the_record_states_which_form_the_hash_covers(tmp_path):
    """Packed bytes and plaintext bytes hash differently; say which is which.

    The artefact carries the object image XOR-packed against the loader's
    derived key. Anyone hashing the embedded base64 literal gets a different
    digest than this record and would reasonably conclude the artefact had
    been tampered with. Naming the form is what stops that false positive.
    """
    elf = b"\x7fELF" + b"\x02" * 128
    rec = _record(tmp_path, native_blobs={
        "linux": base64.b64encode(elf).decode("ascii")})
    assert rec["hashed_form"] == "plaintext-object-image", rec
    packed = bytes(b ^ 0x5A for b in elf)
    assert hashlib.sha256(packed).hexdigest() != rec["sha256"], \
        "the test's packing must differ from the plaintext to be meaningful"


def test_record_covers_every_embedded_platform(tmp_path):
    """One-platform and three-platform builds must not look the same."""
    win = b"MZ" + b"\x00" * 400
    lin = b"\x7fELF" + b"\x01" * 300
    rec = _record(tmp_path, native_blobs={
        "windows": base64.b64encode(win).decode("ascii"),
        "linux": base64.b64encode(lin).decode("ascii"),
        "darwin": "",
    })
    assert set(rec["platforms"]) == {"windows", "linux"}, rec
    # The top-level pair describes the largest blob, so a reader that only
    # knows the single-blob schema still sees a real size and its digest.
    assert rec["bytes"] == len(win), rec
    assert rec["sha256"] == rec["platforms"]["windows"]["sha256"], rec


def test_empty_platforms_are_not_recorded_as_blobs(tmp_path):
    """`{'linux': '', 'windows': ''}` is a bytecode build, not a native one."""
    rec = _record(tmp_path, native_blobs={"linux": "", "windows": "", "darwin": ""})
    assert rec["bytes"] == 0, rec
    assert rec["platforms"] == {}, rec


def test_python_only_build_records_no_native_blob(tmp_path):
    """The fix must not invent a blob for a bytecode-only artefact."""
    rec = _record(tmp_path)
    assert rec["bytes"] == 0, rec
    assert rec["sha256"] == "", rec
    assert rec["platforms"] == {}, rec


def test_native_blob_path_still_works_for_callers_that_have_a_file(tmp_path):
    """The pre-existing file-based input must keep its meaning."""
    blob = tmp_path / "payload.so"
    blob.write_bytes(b"\x7fELF" + b"\x03" * 64)
    rec = _record(tmp_path, native_blob_path=str(blob))
    assert rec["bytes"] == 68, rec
    assert rec["sha256"] == hashlib.sha256(blob.read_bytes()).hexdigest(), rec
