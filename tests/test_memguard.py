"""§4 anti-dump control: the shipped artefact must refuse external memory reads.

Measured 2026-11-18, before the control existed: a protected artefact exposed
its own payload secrets in `rw-p [anon]` pages for 91% of its lifetime, and a
parent process reading `/proc/<pid>/mem` recovered 4/4 secrets on the
`inventory` target. This test pins the control that closes that channel.

The control is `PR_SET_DUMPABLE=0` in the emitted loader (obfuscator/memguard.py),
plus `RLIMIT_CORE=0` so a crash cannot write a heap image. Verified directly in
scripts/verify_dumpable.py; asserted here so a regression in the loader is
caught rather than shipped.

This test deliberately does NOT assert "memory is clean" -- it asserts the
external channel is closed. A process can always read its own memory, and
CPython cannot guarantee erasure. Claiming more than that would be false.
"""
import os
import subprocess
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── 1. the snippet is emitted into every loader ───────────────────────────

def test_memguard_snippet_is_emitted_in_the_loader():
    import obfuscator.core.pipeline as pipeline
    src, _blobs, _fb = pipeline.generate_hybrid_loader_script(
        {"windows": "", "linux": "", "darwin": "", "android": ""},
        b"", "11" * 32, section_split=True)
    assert "_nx_mem_harden" in src, "anti-dump snippet missing from loader"
    assert "prctl(4, 0" in src, "PR_SET_DUMPABLE not applied"
    assert "RLIMIT_CORE" in src, "core limit not applied"


def test_memguard_snippet_runs_and_reports_its_effect():
    """The snippet must actually apply the controls, and say so.

    A hardening call that silently no-ops is indistinguishable from one that
    works unless it is read back -- which is why the snippet records the
    result instead of returning None.
    """
    from obfuscator.memguard import emit_snippet
    namespace = {}
    exec(compile(emit_snippet(), "<memguard>", "exec"), namespace)
    result = namespace.get("_NX_MEM_HARDENING") or {}
    assert result.get("dumpable") == "ok", \
        "PR_SET_DUMPABLE did not apply: %r" % (result.get("dumpable"),)
    assert result.get("core_limit") == "0", \
        "core dump limit not zeroed: %r" % (result.get("core_limit"),)


# ── 2. the control is real: /proc/<pid>/mem becomes unreadable ────────────

def test_prctl_dumpable_blocks_external_memory_read():
    """Measured behaviour of PR_SET_DUMPABLE=0, as the loader relies on it."""
    workdir = tempfile.mkdtemp(prefix="dumpable-")
    script = os.path.join(workdir, "child.py")
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(
            "import ctypes, sys, time\n"
            "libc = ctypes.CDLL('libc.so.6', use_errno=True)\n"
            "libc.prctl(4, 0, 0, 0, 0)\n"
            "sys.stdout.write('ready\\n')\n"
            "sys.stdout.flush()\n"
            "time.sleep(3)\n")
    proc = subprocess.Popen([sys.executable, script, "3"],
                            stdout=subprocess.PIPE, text=True)
    try:
        time.sleep(0.8)
        with pytest.raises(PermissionError):
            fd = os.open("/proc/%d/mem" % proc.pid, os.O_RDONLY)
            os.close(fd)
    finally:
        proc.kill()
        proc.wait()


# ── 3. end to end: a hardened artefact does not yield its secret ──────────

@pytest.mark.skipif(not os.environ.get("NIXON_E2E_NATIVE"),
                    reason="set NIXON_E2E_NATIVE=1 for the full build (~60s)")
def test_hardened_artifact_hides_its_secret_from_a_memory_probe(tmp_path):
    """Build with the control, then try to steal the secret from memory.

    Before the control this recovered the target's KEY constant. The assert is
    on the recovered secret count -- and on the probe having actually read
    memory, so a broken probe cannot pass this test by reading nothing.
    """
    from pydeobsbench.memory_probe import probe_memory_extraction
    from pydeobsbench.targets import TARGETS as T

    target = T["cipher"]
    src = target["source"].rstrip() + "\n\nimport time as _t\n_t.sleep(2.0)\n"
    (tmp_path / "cipher.py").write_text(src, encoding="utf-8")
    env = dict(os.environ, NIXON_LOG_REDIRECT="0",
               PYTHONPATH=REPO, TMPDIR=str(tmp_path))
    build = subprocess.run(
        [sys.executable, "-m", "obfuscator.core.pipeline", "build", "cipher.py",
         "--skip-cloud", "--in-place", "--package", "native",
         "layers=25", "zips=3"],
        cwd=tmp_path, capture_output=True, text=True, timeout=900, env=env)
    assert build.returncode == 0, (build.stdout + build.stderr)[-3000:]

    art = tmp_path / "dist" / "cipher_protected.py"
    assert art.exists(), "no artefact produced"
    result = probe_memory_extraction(str(art), target, samples=80, settle=0.01)

    assert result.get("ran"), "probe did not run"
    # The probe must have really looked: either it read bytes, or the process
    # refused it outright. A run that read nothing and was not blocked is a
    # broken measurement, not a clean result.
    assert result.get("bytes_read", 0) > 0 or result.get("blocked"), \
        "probe neither read memory nor was blocked: %r" % (result,)
    assert result.get("secrets_recovered", 0) == 0, \
        "anti-dump control did not prevent secret recovery: %r" % (
            result.get("secrets_hit"),)
