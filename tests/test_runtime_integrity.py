"""The integrity check must be live, correct, and fail loudly.

`RuntimeConfig::default()` leaves `integrity_expected_crc` at `None`, so
`verify_text_section` was never called — the check existed and did
nothing. `scripts/runtime_config.py` now produces the expected value
from the built binary; the relay reads it at start-up.

Two properties are worth more than the plumbing:

* the build-time CRC equals what the runtime hashes from
  /proc/self/maps (otherwise enabling the check bricks the binary);
* a tampered binary is refused **with a non-zero exit** — it used to
  exit 0, because the register-scrubbing asm destroyed the exit code.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts import runtime_config as rc  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RELAY = os.path.join(ROOT, "build", "orbital-relay")


class TestCrc:
    def test_known_vector(self):
        # The standard check value for CRC-32/ISO-HDLC.
        assert rc.crc32(b"123456789") == 0xCBF43926

    def test_matches_a_known_zlib_value(self):
        import zlib
        data = bytes(range(256))
        assert rc.crc32(data) == zlib.crc32(data) & 0xFFFFFFFF

    def test_executable_segment_is_not_empty(self):
        assert len(rc.executable_segment(sys.executable)) > 0

    def test_segment_changes_when_a_byte_changes(self, tmp_path):
        copy = tmp_path / "patched"
        shutil.copy2(sys.executable, copy)
        before = rc.expected_crc(str(copy))
        data = bytearray(copy.read_bytes())
        seg = rc.executable_segment(str(copy))
        off = data.find(seg[:64])
        assert off >= 0
        data[off + 16] ^= 0xFF
        copy.write_bytes(data)
        assert rc.expected_crc(str(copy)) != before


class TestConfigFile:
    def test_written_round_trip(self, tmp_path):
        copy = tmp_path / "relay"
        shutil.copy2(sys.executable, copy)
        path = rc.write_config(str(copy), str(tmp_path))
        with open(path) as f:
            data = json.load(f)
        assert data["integrity_expected_crc"] == rc.expected_crc(str(copy))

    def test_not_an_elf(self, tmp_path):
        bad = tmp_path / "notelf"
        bad.write_text("hello")
        with pytest.raises(ValueError):
            rc.expected_crc(str(bad))


@pytest.mark.skipif(not os.path.exists(RELAY), reason="relay not built (make relay)")
class TestAgainstTheRealBinary:
    def test_the_built_relay_passes_its_own_check(self, tmp_path):
        shutil.copy2(RELAY, tmp_path / "relay")
        rc.write_config(str(tmp_path / "relay"), str(tmp_path))
        probe = tmp_path / "integrity_probe.py"
        probe.write_text('print("INTEGRITY_PROBE_OK")\n')
        result = subprocess.run(
            [str(tmp_path / "relay"), "--payload", str(probe)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr
        assert "INTEGRITY_PROBE_OK" in result.stdout

    def test_a_patched_binary_is_refused_with_a_non_zero_exit(self, tmp_path):
        binary = tmp_path / "relay"
        shutil.copy2(RELAY, binary)
        rc.write_config(str(binary), str(tmp_path))
        probe = tmp_path / "probe.py"
        probe.write_text('print("MUST_NOT_RUN")\n')

        data = bytearray(binary.read_bytes())
        seg = rc.executable_segment(str(binary))
        off = data.find(seg[:64])
        assert off >= 0, "executable segment not located in the file"
        data[off + 32] ^= 0xFF
        binary.write_bytes(data)
        binary.chmod(0o755)

        result = subprocess.run(
            [str(binary), "--payload", str(probe)],
            capture_output=True, text=True, timeout=30,
        )
        assert "MUST_NOT_RUN" not in result.stdout, "tampered binary ran the payload"
        assert result.returncode != 0, (
            "a tampered binary exited %d — the scrub destroyed the exit code"
            % result.returncode
        )
