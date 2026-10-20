"""Importing the obfuscator modules must not touch the filesystem.

``obfuscator/core/utils.py`` used to open ``./build.log`` (mode ``"w"``)
as a side effect of being imported, and redirect stdout/stderr into it.
Two problems with that:

* merely importing the module created a file in whatever directory the
  caller happened to be in;
* mode ``"w"`` truncated an existing ``build.log`` — including a file
  that had nothing to do with this project.

The redirect is now explicit: an entry point calls
``enable_log_redirect()``.  These tests lock that down.
"""
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_IMPORT_SNIPPETS = [
    "import obfuscator.core.utils",
    "import obfuscator.core.pipeline",
    "import obfuscator.core.sources",
    "import obfuscator.core.transforms",
    "from obfuscator.core import ObfuscationTransformer",
]


def _run_python(code, cwd, env=None):
    environ = dict(os.environ)
    environ["PYTHONPATH"] = REPO_ROOT + os.pathsep + environ.get("PYTHONPATH", "")
    environ["NIXON_LOG_REDIRECT"] = "0"
    if env:
        environ.update(env)
    return subprocess.run([sys.executable, "-c", code], cwd=cwd, env=environ,
                          capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize("snippet", _IMPORT_SNIPPETS)
def test_import_creates_no_log_file(snippet, tmp_path):
    """Importing must not create build.log in the working directory."""
    work = tmp_path / ("import_%d" % abs(hash(snippet)))
    work.mkdir()
    proc = _run_python(snippet, str(work))
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert not (work / "build.log").exists(), (
        "importing %s created build.log" % (snippet,))
    assert list(work.iterdir()) == [], (
        "importing %s created %r" % (snippet, list(work.iterdir())))


def test_import_does_not_truncate_an_existing_log(tmp_path):
    """A pre-existing build.log must survive an import untouched."""
    work = tmp_path / "existing"
    work.mkdir()
    log = work / "build.log"
    log.write_text("PRECIOUS LOG CONTENT\n", encoding="utf-8")
    before = log.stat().st_mtime_ns
    proc = _run_python("import obfuscator.core.utils", str(work))
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert log.read_text(encoding="utf-8") == "PRECIOUS LOG CONTENT\n"
    assert log.stat().st_mtime_ns == before, "build.log was rewritten"


def test_explicit_redirect_still_logs(tmp_path):
    """The explicit entry point still produces a log file."""
    work = tmp_path / "explicit"
    work.mkdir()
    code = (
        "import obfuscator.core.utils as u\n"
        "print('hello from the logger')\n"
        "u.enable_log_redirect()\n"
        "print('after redirect')\n"
    )
    environ = dict(os.environ)
    environ["PYTHONPATH"] = REPO_ROOT + os.pathsep + environ.get("PYTHONPATH", "")
    environ.pop("NIXON_LOG_REDIRECT", None)  # default is "1" -> redirect on
    proc = subprocess.run([sys.executable, "-c", code], cwd=str(work),
                          env=environ, capture_output=True, text=True,
                          timeout=120)
    assert proc.returncode == 0, proc.stderr[-2000:]
    log = work / "build.log"
    assert log.exists(), "enable_log_redirect() did not create the log"
    body = log.read_text(encoding="utf-8")
    assert "after redirect" in body, body[-500:]
    # The log must not be world-readable.
    assert (log.stat().st_mode & 0o077) == 0, oct(log.stat().st_mode)


def test_redirect_is_off_when_the_env_says_so(tmp_path):
    """NIXON_LOG_REDIRECT=0 keeps everything on the console."""
    work = tmp_path / "off"
    work.mkdir()
    code = ("import obfuscator.core.utils as u\n"
            "print('console line')\n"
            "u.enable_log_redirect()\n")
    proc = _run_python(code, str(work), env={"NIXON_LOG_REDIRECT": "0"})
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "console line" in proc.stdout
    assert not (work / "build.log").exists()
