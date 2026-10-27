"""``--section-split`` must work through the real command line.

The loader-level behaviour is covered by ``test_section_split_wiring.py``:
the pack is emitted, the sections are sealed, the artifact runs, and a
tampered section kills it.

What that file does NOT cover is the path a user actually takes: the
CLI flag -> the pipeline kwarg -> the pack.  A break anywhere in that
chain would leave the feature silently inert, which is exactly the
state the module was in before it was wired up.

The pack itself cannot be grepped out of the artifact -- it is a sealed
literal by then -- so the evidence here is behavioural: the flag must
change the artifact, and the artifact must still run.
"""
import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PAYLOAD = '''\
def main():
    print("SECTION-CLI-OK")


if __name__ == "__main__":
    main()
'''


def _build(source, cwd, extra=()):
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "obfuscator.core.pipeline", "build", source]
        + list(extra),
        cwd=cwd, env=env, capture_output=True, text=True, timeout=1800)


def _prepare(tmp_path, name):
    src_dir = tmp_path / name
    run_dir = tmp_path / (name + "-run")
    src_dir.mkdir()
    run_dir.mkdir()
    source = src_dir / "payload.py"
    source.write_text(PAYLOAD, encoding="utf-8")
    return src_dir, run_dir, source


def _packed_artifact(src_dir):
    """The runnable artifact the build leaves next to the source."""
    candidates = [n for n in sorted(os.listdir(str(src_dir)))
                  if n.endswith(".py") and "_Nixon-Enc" in n
                  and "Packed" in n]
    assert candidates, ("no packed artifact next to the source: %r"
                        % sorted(os.listdir(str(src_dir))))
    return os.path.join(str(src_dir), candidates[0])


def _run(path):
    """Run the artifact; on a hang, dump its stack instead of nothing.

    This run timed out after 300 s on the 3.13 runner while the same
    artifact finishes in under a second here.  A bare TimeoutExpired says
    nothing about where it sits, so the child runs under faulthandler and
    gets SIGABRT on timeout.
    """
    env = dict(os.environ, NIXON_LOG_REDIRECT="0", PYTHONFAULTHANDLER="1")
    proc = subprocess.Popen([sys.executable, path], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, env=env)
    try:
        out, err = proc.communicate(timeout=300)
    except subprocess.TimeoutExpired:
        try:
            import signal as _signal
            proc.send_signal(_signal.SIGABRT)
        except Exception:
            pass
        try:
            out, err = proc.communicate(timeout=30)
        except Exception:
            out, err = "", ""
        print("[!] artifact run timed out; child stack:")
        print((err or "")[-4000:])
        raise
    return subprocess.CompletedProcess([sys.executable, path], proc.returncode, out, err)


def test_section_split_flag_produces_a_working_artifact(tmp_path):
    src_dir, run_dir, source = _prepare(tmp_path, "split")
    proc = _build(str(source), str(run_dir),
                  ["--section-split", "--section-count", "4"])
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-2000:]

    artifact = _packed_artifact(src_dir)
    run = _run(artifact)
    assert run.returncode == 0, run.stderr[-3000:]
    assert "SECTION-CLI-OK" in run.stdout, run.stdout[-2000:]


def test_section_split_flag_changes_the_artifact(tmp_path):
    """The flag must actually reach the loader, not be swallowed."""
    plain_dir, plain_run, plain_source = _prepare(tmp_path, "plain")
    split_dir, split_run, split_source = _prepare(tmp_path, "split")

    assert _build(str(plain_source), str(plain_run)).returncode == 0
    assert _build(str(split_source), str(split_run),
                  ["--section-split", "--section-count", "4"]).returncode == 0

    plain = open(_packed_artifact(plain_dir), "rb").read()
    split = open(_packed_artifact(split_dir), "rb").read()
    assert plain != split, (
        "--section-split produced a byte-identical artifact: the flag did "
        "not reach the loader")
