"""`.rodata` encryption: string literals must not survive in the artifact.

The documented gap was that native binaries protect code, not string
literals.  These tests pin the whole path: the section is encrypted in
place, the stub decrypts it before the original entry runs, the artifact
still executes, and the guards that keep it safe actually fire.
"""
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from encrypt import elf as elfmod  # noqa: E402
from encrypt import encrypt as encmod  # noqa: E402
from encrypt import stub as stubmod  # noqa: E402

CANARY = "NIXON-RODATA-CANARY-9f3a2b"

SOURCE = f"""
#include <stdio.h>
#include <string.h>
static const char *SECRET = "{CANARY}";
int main(void) {{
    printf("hello %s\\n", SECRET);
    printf("len=%zu\\n", strlen(SECRET));
    return 0;
}}
"""


def _have_gcc():
    return shutil.which("gcc") is not None


pytestmark = pytest.mark.skipif(not _have_gcc(), reason="gcc not installed")


@pytest.fixture(scope="module")
def binary(tmp_path_factory):
    d = tmp_path_factory.mktemp("rodata")
    src = d / "prog.c"
    src.write_text(SOURCE)
    out = d / "prog"
    subprocess.run(["gcc", "-O1", "-no-pie", str(src), "-o", str(out)],
                   check=True, capture_output=True)
    return out


def _encrypt(binary, out, rodata=True):
    return encmod.encrypt_binary(str(binary), str(out), encrypt_rodata=rodata)


def _run(path):
    os.chmod(path, 0o755)
    return subprocess.run([str(path)], capture_output=True, text=True)


def test_canary_is_present_before_encryption(binary):
    assert CANARY.encode() in binary.read_bytes()


def test_rodata_is_encrypted_and_the_binary_still_runs(binary, tmp_path):
    out = tmp_path / "prog.enc"
    result = _encrypt(binary, out)
    assert result["rodata_encrypted"] is True
    assert result["rodata_size"] > 0

    blob = out.read_bytes()
    assert CANARY.encode() not in blob, "string literal survived in the artifact"

    run = _run(out)
    assert run.returncode == 0, run.stderr
    assert CANARY in run.stdout
    assert "len=26" in run.stdout


def test_rodata_encryption_is_fail_closed_without_the_key(binary, tmp_path):
    out = tmp_path / "prog.enc"
    _encrypt(binary, out)
    os.unlink(str(out) + ".key")
    run = _run(out)
    assert run.returncode == 1
    assert CANARY not in run.stdout


def test_disabled_rodata_leaves_the_section_untouched(binary, tmp_path):
    out = tmp_path / "prog.plain"
    result = _encrypt(binary, out, rodata=False)
    assert result["rodata_encrypted"] is False
    assert result["rodata_skipped_reason"] == "disabled"
    assert CANARY.encode() in out.read_bytes()
    assert _run(out).returncode == 0


def test_rodata_keystream_is_domain_separated_from_text():
    seed = bytes(range(32))
    ro = encmod._rodata_keystream(seed, 64)
    assert len(ro) == 64
    # Same seed, different domain -> different stream than the .text path.
    text_ks = b""
    for i in range(1):
        blk_key = encmod.aes.derive_block_key(seed, i, 64)
        nonce = encmod.hashlib.sha256(blk_key).digest()[:8]
        text_ks += encmod.aes.aes256_ctr_keystream(blk_key, nonce, 64)
    assert ro != text_ks


def test_rodata_keystream_is_deterministic_and_length_exact():
    seed = b"\x01" * 32
    assert encmod._rodata_keystream(seed, 10) == encmod._rodata_keystream(seed, 10)
    assert len(encmod._rodata_keystream(seed, 5000)) == 5000


def test_plan_skips_when_disabled(binary):
    elf = elfmod.ELFParser(binary.read_bytes())
    plan = encmod._plan_rodata_encryption(elf, b"\x00" * 32, False)
    assert plan["size"] == 0
    assert plan["skipped_reason"] == "disabled"


def test_plan_skips_when_the_runtime_key_is_missing(binary):
    elf = elfmod.ELFParser(binary.read_bytes())
    plan = encmod._plan_rodata_encryption(elf, b"\x00" * 32, True)
    assert plan["size"] == 0
    assert plan["skipped_reason"] == "runtime key unavailable"


def test_plan_skips_when_rodata_overlaps_another_section(binary):
    """The stub must never decrypt data it does not own."""
    elf = elfmod.ELFParser(binary.read_bytes())
    idx, ro = elf.get_rodata_section()
    assert ro is not None
    ro["addr"] = elf.get_text_section()[1]["addr"]
    plan = encmod._plan_rodata_encryption(elf, b"\x00" * 32, True,
                                          runtime_key=b"\x11" * 32)
    assert plan["size"] == 0
    assert "overlaps the .rodata span" in plan["skipped_reason"]


class _FakeELF:
    """Minimal stand-in so the page guard can be exercised in isolation."""

    def __init__(self, text_addr, ro_addr, ro_size=16):
        self.data = b"\x00" * 0x4000
        self._text = {"addr": text_addr, "size": 0x40, "offset": 0x1000,
                      "type": elfmod.SHT_PROGBITS, "flags": 0x6}
        self._ro = {"addr": ro_addr, "size": ro_size, "offset": 0x2000,
                    "type": elfmod.SHT_PROGBITS, "flags": 0x2}
        self.sections = [self._text, self._ro]

    def get_rodata_sections(self):
        return [(1, self._ro)]

    def get_text_section(self):
        return 0, self._text

    def page_range(self, section):
        page = 0x1000
        return (section["addr"] & ~(page - 1),
                (section["addr"] + section["size"] + page - 1) & ~(page - 1))

    def section_name(self, section):
        return b".text" if section is self._text else b".rodata"


def test_plan_skips_when_rodata_shares_a_page_with_text():
    """Restoring a shared page to read-only would strip execute permission."""
    # .rodata sits after .text in the same 4 KiB page, no section overlap.
    elf = _FakeELF(text_addr=0x401000, ro_addr=0x401080)
    plan = encmod._plan_rodata_encryption(elf, b"\x00" * 32, True,
                                          runtime_key=b"\x11" * 32)
    assert plan["size"] == 0
    assert "shares a page with .text" in plan["skipped_reason"]


def test_plan_accepts_rodata_on_its_own_page():
    elf = _FakeELF(text_addr=0x401000, ro_addr=0x402000)
    plan = encmod._plan_rodata_encryption(elf, b"\x00" * 32, True,
                                          runtime_key=b"\x11" * 32)
    assert plan["size"] == 16
    assert plan["addr"] == 0x402000


def test_plan_skips_a_missing_rodata_section():
    elf = elfmod.ELFParser(open("/bin/true", "rb").read())
    idx, sec = elf.get_rodata_section()
    if sec is not None:
        pytest.skip("/bin/true has a .rodata section")
    plan = encmod._plan_rodata_encryption(elf, b"\x00" * 32, True,
                                          runtime_key=b"\x11" * 32)
    assert plan["size"] == 0
    assert plan["skipped_reason"] == "no .rodata section"


def test_replace_rodata_rejects_a_length_change(binary):
    elf = elfmod.ELFParser(binary.read_bytes())
    idx, sec = elf.get_rodata_section()
    with pytest.raises(ValueError, match="replace_rodata needs"):
        elf.replace_rodata(b"\x00" * (sec["size"] + 1))


def test_replace_rodata_keeps_every_offset(binary):
    data = binary.read_bytes()
    elf = elfmod.ELFParser(data)
    idx, sec = elf.get_rodata_section()
    before = {s["name_idx"]: (s["offset"], s["addr"], s["size"])
              for s in elf.sections}
    elf.replace_rodata(b"\xAA" * sec["size"])
    after = {s["name_idx"]: (s["offset"], s["addr"], s["size"])
             for s in elf.sections}
    assert before == after
    assert len(elf.data) == len(data)


def test_page_range_is_page_aligned(binary):
    elf = elfmod.ELFParser(binary.read_bytes())
    idx, sec = elf.get_rodata_section()
    start, end = elf.page_range(sec)
    assert start % 0x1000 == 0
    assert end % 0x1000 == 0
    assert start <= sec["addr"]
    assert end >= sec["addr"] + sec["size"]


def test_stub_size_matches_the_built_stub_with_rodata():
    key_path = "/tmp/some.key"
    built = stubmod.make_stub_with_keystream(
        64, 0, b"A" * 64, key_path=key_path,
        rodata_size=32, rodata_base_delta=-100, rodata_keystream=b"B" * 32)
    assert len(built) == stubmod.stub_size(64, len(key_path) + 1, 32)


def test_rodata_stub_is_larger_than_the_plain_keyed_stub():
    assert stubmod.STUB_CODE_SIZE_KEYED_RO > stubmod.STUB_CODE_SIZE_KEYED


def test_rodata_requires_a_key_path():
    """An unmasked keystream would make the section trivially recoverable."""
    with pytest.raises(ValueError, match="requires key_path"):
        stubmod.make_stub_with_keystream(
            64, 0, b"A" * 64, rodata_size=32, rodata_keystream=b"B" * 32)


def test_rodata_keystream_length_must_match():
    with pytest.raises(ValueError, match="rodata keystream length"):
        stubmod.make_stub_with_keystream(
            64, 0, b"A" * 64, key_path="/tmp/k",
            rodata_size=32, rodata_keystream=b"B" * 31)


def test_negative_rodata_size_is_rejected():
    with pytest.raises(ValueError, match="rodata_size must be non-negative"):
        stubmod.make_stub_with_keystream(
            64, 0, b"A" * 64, key_path="/tmp/k", rodata_size=-1)


def test_plain_stub_is_unchanged_by_the_rodata_addition():
    """The non-rodata path must stay byte-identical to the pre-existing stub."""
    built = stubmod.make_stub_with_keystream(64, 0, b"A" * 64, key_path="/tmp/k")
    assert len(built) == stubmod.stub_size(64, len("/tmp/k") + 1)
    assert len(built) == (stubmod.STUB_CODE_SIZE_KEYED
                          + stubmod.STUB_HEADER_SIZE_KEYED + 64 + len("/tmp/k") + 1)


def test_phase_passes_rodata_flag_when_enabled(monkeypatch):
    from scripts.phases import phase04_encrypt as p4

    seen = {}
    monkeypatch.setattr(p4, "run", lambda cmd, **kw: seen.setdefault("cmd", cmd))
    monkeypatch.setattr(p4, "_rodata_encryption_enabled", lambda: True)
    p4.phase_encrypt_binary("in.o", "out.enc")
    assert "--rodata" in seen["cmd"]


def test_phase_omits_rodata_flag_when_disabled(monkeypatch):
    from scripts.phases import phase04_encrypt as p4

    seen = {}
    monkeypatch.setattr(p4, "run", lambda cmd, **kw: seen.setdefault("cmd", cmd))
    monkeypatch.setattr(p4, "_rodata_encryption_enabled", lambda: False)
    p4.phase_encrypt_binary("in.o", "out.enc")
    assert "--rodata" not in seen["cmd"]


def test_phase_defaults_to_enabled_when_config_is_unreadable(monkeypatch):
    from scripts.phases import phase04_encrypt as p4

    monkeypatch.setattr(p4.os.path, "join", lambda *a: "/nonexistent/default.json")
    assert p4._rodata_encryption_enabled() is True
