"""archive_safety.py

Purpose:
    One confinement check for every archive this project extracts.

Architectural Role:
    The build farm downloads and unpacks artifacts, the artifact bundler
    verifies a bundle by extracting it, and the tool-download path
    unpacks a dependency.  Each of those used to grow its own
    extraction, and two of them had no confinement at all.

    This module is the shared check.  It is deliberately free of side
    effects and of any dependency beyond the standard library, so that
    both the library (``obfuscator.core.utils``) and the build
    scripts (``scripts.artifacts.bundler``) can use it without
    importing each other.

Security Relevance:
    An archive member named ``../x`` -- or one behind a symlink --
    would otherwise write outside the extraction directory (ZipSlip /
    tar traversal).  The check is on the RESOLVED destination, so
    neither a ``..`` component nor a symlinked member can escape.

    The tar path additionally uses the standard library's ``data``
    filter where it exists (3.12+, and the 3.9-3.11 security
    backports): it is stricter than this check -- it also strips
    absolute paths and refuses links that point outside -- and it is
    the behaviour Python 3.14 will apply by default.  Without the
    explicit argument, 3.14 changes the default silently.
"""

from __future__ import annotations

import os
import tarfile
import zipfile


def confined_member_path(base_dir: str, member_name: str) -> str:
    """The resolved destination of an archive member, or raise.

    Raises :class:`ValueError` when the member would land outside
    ``base_dir``.
    """
    base_real = os.path.realpath(base_dir)
    dest = os.path.realpath(os.path.join(base_dir, member_name))
    if dest != base_real and not dest.startswith(base_real + os.sep):
        raise ValueError(
            "refusing archive member escaping output dir: %r" % (member_name,))
    return dest


def extract_zip_confined(zip_path: str, output_dir: str) -> None:
    """Extract *zip_path* into *output_dir*, refusing to escape it."""
    with zipfile.ZipFile(zip_path, "r") as z:
        for member in z.namelist():
            confined_member_path(output_dir, member)
        z.extractall(output_dir)


def extract_tar_confined(tar_path: str, output_dir: str,
                          mode: str = "r:*") -> None:
    """Extract *tar_path* into *output_dir*, refusing to escape it."""
    with tarfile.open(tar_path, mode) as t:
        for member in t.getmembers():
            confined_member_path(output_dir, member.name)
        if hasattr(tarfile, "data_filter"):
            # Explicit, because Python 3.14 changes the default.
            t.extractall(output_dir, filter="data")
        else:
            t.extractall(output_dir)
