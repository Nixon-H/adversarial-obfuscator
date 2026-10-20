"""A symlinked build input must be surfaced, not silently embedded.

The pipeline embeds its build inputs verbatim, so a symlinked input
embeds whatever it points at.  The build host is trusted, so this is
NOT refused -- refusing would break legitimate setups that symlink a
runtime -- but it is warned about, because "the artifact contains a
file nobody named" must not be silent.

The trust boundary itself is recorded in ``THREAT_MODEL.md`` and
``docs/failure-modes.md`` row 13.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import scripts.generate_payload_h as gph  # noqa: E402


def _make_symlinked_input(tmp_path):
    real = tmp_path / "real_payload.py"
    real.write_bytes(b"print('x')\n")
    link = tmp_path / "link_payload.py"
    os.symlink(str(real), str(link))
    return str(link)


def test_symlinked_build_input_is_warned_about(tmp_path, capsys):
    link = _make_symlinked_input(tmp_path)
    out = tmp_path / "payload.h"
    gph.generate_payload_h(
        obfuscated_py_path=link,
        python_dll_path=None,
        rust_exe_path=None,
        output_path=str(out),
    )
    captured = capsys.readouterr().out
    assert "symlink" in captured.lower(), (
        "a symlinked build input was embedded without a warning:\n%s"
        % captured)
    assert link in captured
    assert out.exists()


def test_regular_build_input_is_not_warned_about(tmp_path, capsys):
    plain = tmp_path / "payload.py"
    plain.write_bytes(b"print('x')\n")
    out = tmp_path / "payload.h"
    gph.generate_payload_h(
        obfuscated_py_path=str(plain),
        python_dll_path=None,
        rust_exe_path=None,
        output_path=str(out),
    )
    captured = capsys.readouterr().out
    assert "symlink" not in captured.lower(), (
        "a regular build input produced a symlink warning:\n%s" % captured)


def test_the_threat_model_states_the_build_host_trust_boundary():
    path = os.path.join(ROOT, "THREAT_MODEL.md")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    assert "Build-host trust boundary" in text
    assert "build host is trusted" in text.lower()
