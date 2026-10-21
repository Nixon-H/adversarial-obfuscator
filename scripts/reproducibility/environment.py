"""
reproducibility/environment.py — Environment fingerprinting for reproducibility (F178)

Purpose:
    Captures a comprehensive snapshot of the build environment (Python version,
    OS, CPU, hostname, git commit, installed packages) and provides functions
    to fingerprint and compare environments.

Architectural Role:
    Utility layer consumed by the scorer and checker modules. Environment
    fingerprints are included in reproducibility reports to enable diagnosis
    of environment-dependent variation.

Security Relevance:
    Environment differences are a common cause of non-reproducible builds.
    Explicit fingerprinting and comparison enables root-cause analysis.
"""

from __future__ import annotations

import hashlib
import os  # noqa: F401 (this line binds a name used by an embedded template)
import platform
import subprocess
import sys
import time
from typing import Any, Dict, Optional, Tuple


def _get_git_info() -> Tuple[Optional[str], bool]:
    """Get the current git commit hash and dirty status. Returns (commit, is_dirty)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        commit = result.stdout.strip() if result.returncode == 0 else None
        dirty = False
        if commit:
            diff = subprocess.run(
                ["git", "diff", "--quiet"],
                capture_output=True, timeout=5,
            )
            dirty = diff.returncode != 0
        return commit, dirty
    except (subprocess.SubprocessError, FileNotFoundError):
        return None, False


def _get_installed_packages() -> Dict[str, str]:
    """Return a dict of installed Python package name → version.

    ``importlib.metadata`` is the supported API; ``pkg_resources`` is
    deprecated (and warns on import), so it is only a fallback for a
    Python too old to have the former.
    """
    packages: Dict[str, str] = {}
    try:
        import importlib.metadata as md
        for dist in md.distributions():
            packages[dist.metadata["Name"]] = dist.version
        return packages
    except Exception:
        pass
    try:
        import pkg_resources
        for dist in pkg_resources.working_set:
            packages[dist.key] = dist.version
    except ImportError:
        pass
    return packages


def snapshot_environment() -> Dict[str, str]:
    """Capture a snapshot of the current build environment as a string dict.

    Includes: python_version, os, cpu, hostname, timestamp, git_commit,
    git_dirty, and installed packages.
    """
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    os_name = platform.platform()
    # os.uname() is a SYSCALL.  platform.processor() and
    # platform.machine() each spawn an untimed `uname` subprocess, which
    # can block the build indefinitely when the host is loaded (it hung
    # for five minutes once).  The snapshot wants the architecture, not
    # a subprocess.
    try:
        _uname = os.uname()
        processor = _uname.machine or ""
        hostname = _uname.nodename or ""
    except Exception:
        processor = ""
        hostname = platform.node()
    if not processor:
        processor = os.environ.get("PROCESSOR_ARCHITECTURE", "") or "unknown"
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    git_commit, git_dirty = _get_git_info()

    packages = _get_installed_packages()
    packages_str = ";".join(f"{k}=={v}" for k, v in sorted(packages.items()))

    env = {
        "python_version": python_version,
        "os": os_name,
        "cpu": processor,
        "hostname": hostname,
        "timestamp": timestamp,
        "git_commit": git_commit or "unknown",
        "git_dirty": str(git_dirty),
        "packages": packages_str if packages_str else "none",
    }
    return env


def environment_fingerprint(env: Dict[str, str]) -> str:
    """Compute a SHA-256 fingerprint of an environment dict (excluding the timestamp key)."""
    raw = "|".join(f"{k}={v}" for k, v in sorted(env.items()) if k != "timestamp")
    return hashlib.sha256(raw.encode()).hexdigest()


def compare_environments(env_a: Dict[str, str], env_b: Dict[str, str]) -> Tuple[bool, Dict[str, Tuple[Any, Any]]]:
    """Compare two environment snapshots. Returns (identical, {key: (val_a, val_b)}) for differing keys."""
    differences: Dict[str, Tuple[Any, Any]] = {}
    all_keys = set(env_a.keys()) | set(env_b.keys())
    for key in sorted(all_keys):
        va = env_a.get(key)
        vb = env_b.get(key)
        if va != vb:
            differences[key] = (va, vb)
    return len(differences) == 0, differences
