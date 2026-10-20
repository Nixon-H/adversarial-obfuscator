"""The pipeline loader must be a working artifact.

The pipeline CLI (``python3 -m obfuscator.core.pipeline build ...``) emits
a different loader from the canonical ``scripts/build.py`` build.  That
loader was broken in two ways and nothing caught it, because no test
rendered it and ran it:

1. ``ANTMAN_SOURCE`` had an ``except`` clause at the wrong indent level,
   so the emitted file could not be parsed at all (SyntaxError).
2. ``Nixon_Enc_strings`` rewrote the loader preamble's literals into
   string-decoder calls -- but the decoder is defined *later* in the
   file, so the artifact raised NameError at import.

Both are regression-tested here end to end: the CLI is driven, the
artifact is produced, and the artifact is executed.
"""
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_BUILD_TIMEOUT = 300


def _run_pipeline_build(source_path, cwd):
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "obfuscator.core.pipeline", "build",
         source_path, "--net-url", "https://127.0.0.1:9443/"],
        cwd=cwd, env=env, capture_output=True, text=True,
        timeout=_BUILD_TIMEOUT)


@pytest.fixture(scope="module")
def pipeline_artifact(tmp_path_factory):
    """Build one artifact with the pipeline CLI; yields its path."""
    work = tmp_path_factory.mktemp("pipeline_loader")
    source = os.path.join(str(work), "hello.py")
    with open(source, "w") as fh:
        fh.write('print("hello-nixon")\n')
    proc = _run_pipeline_build(source, str(work))
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    artifact = os.path.join(str(work), "dist", "hello_protected.py")
    assert os.path.exists(artifact), (
        "pipeline CLI produced no artifact; stdout tail: %s"
        % (proc.stdout[-2000:],))
    return artifact


def test_pipeline_artifact_parses(pipeline_artifact):
    import ast
    with open(pipeline_artifact, encoding="utf-8") as fh:
        ast.parse(fh.read())


def test_pipeline_artifact_runs(pipeline_artifact):
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    proc = subprocess.run([sys.executable, pipeline_artifact],
                          capture_output=True, text=True, timeout=60,
                          env=env)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert "hello-nixon" in proc.stdout, proc.stdout[-2000:]


def test_pipeline_artifact_writes_no_stray_dump_file(pipeline_artifact):
    """The artifact must not dump the decrypted payload to a fixed path.

    It used to write the raw payload source to a hardcoded absolute path
    on the build machine -- on that machine a plaintext copy of the
    protected payload landed in a directory; everywhere else the write
    silently failed.  The dump is now opt-in and goes to a private temp
    file.
    """
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    work = os.path.dirname(os.path.dirname(pipeline_artifact))
    before = set(os.listdir(work))
    subprocess.run([sys.executable, pipeline_artifact], capture_output=True,
                   text=True, timeout=60, env=env)
    after = set(os.listdir(work))
    assert after == before, "artifact created stray files: %r" % (
        sorted(after - before),)


def test_string_pass_does_not_use_the_decoder_before_its_definition():
    """The invariant behind the NameError fix, checked without a build."""
    from obfuscator.core.pipeline import Nixon_Enc_strings
    from obfuscator.core.sources import LOADER_BODY, LOADER_HEAD, VARS

    raw = (LOADER_HEAD + "\n" + LOADER_BODY)
    # Substitute the placeholders the pass cares about; the rest can stay
    # as-is because the pass only rewrites quoted literals.
    raw = raw.replace("{FUNC_STR_DEC}", VARS["FUNC_STR_DEC"])
    encoded = Nixon_Enc_strings(raw)
    lines = encoded.split("\n")
    dec = VARS["FUNC_STR_DEC"]
    dec_at = None
    for i, line in enumerate(lines):
        if line.startswith("def %s(" % (dec,)):
            dec_at = i
            break
    assert dec_at is not None, "decoder definition not found in the loader"
    for i in range(dec_at):
        assert ("%s(" % (dec,)) not in lines[i], (
            "decoder used before it is defined, at loader line %d: %s"
            % (i + 1, lines[i][:120]))
