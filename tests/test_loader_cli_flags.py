"""The loader build's flags must behave as documented.

Three things this round changed on the loader CLI:

* ``--opt-level`` now applies to the loader build, so both CLIs
  resolve a protection level the same way.
* ``--section-split`` is ON by default and ``--no-section-split`` is
  the escape hatch -- the switch the FIRST audit asked for.
* ``--watermark`` is a deprecated alias of ``--lock-hwid`` and says so
  when it is used.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from obfuscator.core.pipeline import build_parser  # noqa: E402

PAYLOAD = 'def main():\n    print("FLAG-OK")\n\nif __name__ == "__main__":\n    main()\n'


def _parse(argv):
    parser, _subs = build_parser()
    return parser.parse_args(argv)


def test_section_split_is_on_by_default():
    """The whole encrypted payload should not sit in one buffer."""
    assert _parse(["build", "p.py"]).section_split is True


def test_no_section_split_is_the_escape_hatch():
    assert _parse(["build", "p.py", "--no-section-split"]).section_split is False


def test_opt_level_is_accepted_by_the_loader_build():
    assert _parse(["build", "p.py"]).opt_level is None
    assert _parse(["build", "p.py", "--opt-level", "2"]).opt_level == 2


def test_the_watermark_alias_is_still_accepted():
    assert _parse(["build", "p.py", "--watermark", "W"]).lock_hwid == "W"


def test_the_watermark_alias_warns_when_used(tmp_path):
    source = tmp_path / "p.py"
    source.write_text(PAYLOAD, encoding="utf-8")
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "obfuscator.core.pipeline", "build",
         str(source), "--watermark", "W", "--skip-cloud"],
        capture_output=True, text=True, timeout=900, env=env, cwd=str(tmp_path))
    assert "--watermark" in proc.stdout + proc.stderr, (
        "the deprecated --watermark spelling was used without a warning:\n%s"
        % (proc.stdout[-2000:] + proc.stderr[-1000:]))


def test_the_lock_hwid_flag_does_not_warn(tmp_path):
    source = tmp_path / "p.py"
    source.write_text(PAYLOAD, encoding="utf-8")
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "obfuscator.core.pipeline", "build",
         str(source), "--lock-hwid", "W", "--skip-cloud"],
        capture_output=True, text=True, timeout=900, env=env, cwd=str(tmp_path))
    assert "deprecated" not in proc.stdout + proc.stderr, (
        "--lock-hwid must not warn about a deprecation it does not have")
