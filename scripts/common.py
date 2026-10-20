"""
common.py

Purpose:
Shared infrastructure for the Nixon build pipeline. Provides path constants,
atomic file I/O, structured logging, and subprocess execution primitives used
by every stage of the pipeline.

Architectural Role:
Foundation layer — all pipeline scripts (build.py, phases, metrics) import
from this module rather than duplicating path logic or I/O helpers. Centralising
these utilities here enforces consistent error handling and a uniform logging
format across the entire codebase.

Execution Context:
Imported at module load time by build.py and phase files. Path constants are
evaluated once relative to this file's location on disk.

Dependencies:
- os, sys, json: standard library path/module resolution
- shutil: file copy operations
- subprocess: external tool execution
- time: log timestamp formatting

Security Relevance:
atomic_write prevents partial-file-read races by writing to a temp path then
renaming atomically. run() surfaces command output for auditability.
"""
import json  # noqa: F401 (this line binds a name used by an embedded template)
import os
import shutil  # noqa: F401 (this line binds a name used by an embedded template)
import subprocess
import sys  # noqa: F401 (this line binds a name used by an embedded template)
import time

# Root of the project repository — derived from this file's location
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Primary output directory for all build artifacts
BUILD_DIR = os.path.join(ROOT, "build")

# Directory containing Rust relay source code
RELAY_DIR = os.path.join(ROOT, "relay")

# Path to the obfuscator entry point
OBFUSCATOR = os.path.join(ROOT, "obfuscator", "core.py")

# JSON configuration for the Rust relay build
CONFIG_FILE = os.path.join(ROOT, "config", "relay.json")

# Fallback configuration file with default settings
DEFAULT_CONFIG = os.path.join(ROOT, "config", "default.json")


def atomic_write(path, data, mode="w"):
    """
    atomic_write

    Purpose:
    Write data to a file atomically: content is first written to a temporary
    sibling file, then renamed over the target. This prevents partial reads
    by other processes and leaves no half-written files on crash.

    Inputs:
    - path (str): destination file path
    - data (str | bytes): content to write
    - mode (str): file open mode, default "w" (text), "wb" for binary

    Outputs:
    - None. On failure the temp file is cleaned up before the exception
      propagates.

    Security:
    Atomic rename guarantees readers see either the old content or the new
    content, never a partial write. Temp file is removed on error to avoid
    leaking sensitive data to disk.
    """
    tmp = path + ".tmp"
    try:
        with open(tmp, mode) as f:
            f.write(data)
        os.rename(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def log(phase, msg):
    """
    log

    Purpose:
    Emit a timestamped, phase-labelled message to stdout. Every pipeline stage
    uses this for a consistent, grep-able log format.

    Inputs:
    - phase (str): short label identifying the pipeline stage (padded to 12
      characters in output)
    - msg (str): informative message

    Outputs:
    - None. Prints to stdout.
    """
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{phase:>12}] {msg}")


def run(cmd, cwd=None, check=True, timeout=900):
    """
    run

    Purpose:
    Execute an external command, log it, and return the completed process.
    Centralised here so every pipeline stage logs commands uniformly and
    errors are handled consistently.

    Inputs:
    - cmd (list[str] | str): command to execute
    - cwd (str | None): working directory (defaults to ROOT)
    - check (bool): if True, raise CalledProcessError on non-zero exit
    - timeout (float | None): seconds before the child is killed
      (default 900; None disables). Callers with tighter budgets pass
      their own value through.

    Outputs:
    - subprocess.CompletedProcess: result with stdout, stderr, returncode

    Security:
    The command is logged before execution, providing an audit trail of
    every external tool invocation. The caller must validate command
    arguments as this function does not perform input sanitisation.
    """
    log("CMD", " ".join(cmd) if isinstance(cmd, list) else cmd)
    result = subprocess.run(cmd, cwd=cwd or ROOT, check=False, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode != 0:
        if result.stdout:
            log("CMD", f"stdout:\n{result.stdout[:2000]}")
        if result.stderr:
            log("CMD", f"stderr:\n{result.stderr[:2000]}")
        result.check_returncode()
    return result
