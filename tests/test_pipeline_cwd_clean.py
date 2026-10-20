"""The build pipeline must not write into the caller's directory.

The pipeline CLI used to write its intermediates -- the packed variants
and the ``.report.json`` -- into whatever directory it happened to be
run from, so a build run from ``~`` littered the home directory and a
build run inside a repository left untracked files behind.

Everything now lands next to the source file.
"""
import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PAYLOAD = '''\
def main():
    print("payload-ok")


if __name__ == "__main__":
    main()
'''


def _run_pipeline(source, cwd, extra=()):
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "obfuscator.core.pipeline", "build", source]
        + list(extra),
        cwd=cwd, env=env, capture_output=True, text=True, timeout=1800)


def test_pipeline_writes_next_to_the_source_not_the_cwd(tmp_path):
    src_dir = tmp_path / "src"
    run_dir = tmp_path / "run"
    src_dir.mkdir()
    run_dir.mkdir()
    source = src_dir / "payload.py"
    source.write_text(PAYLOAD, encoding="utf-8")

    proc = _run_pipeline(str(source), str(run_dir))
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-2000:]

    leftovers = sorted(p.name for p in run_dir.iterdir())
    assert leftovers == [], (
        "the build left files in the working directory: %r" % (leftovers,))

    produced = sorted(p.name for p in src_dir.iterdir())
    assert any(n.endswith(".report.json") for n in produced), (
        "the report was not written next to the source: %r" % (produced,))
    assert any("_Nixon-Enc" in n for n in produced), (
        "the build outputs were not written next to the source: %r"
        % (produced,))
