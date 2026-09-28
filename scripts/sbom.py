#!/usr/bin/env python3
"""Generate a CycloneDX-ish SBOM from requirements.txt pins + installed metadata.

Stdlib only (argparse, json, os, re, datetime, importlib.metadata) — no new
dependencies, no network access. Reads ``requirements.txt`` ``==`` pins and
resolves each version via :mod:`importlib.metadata` (falling back to the pin
when the distribution is not installed in the current environment).

Reproducible-build support: honors ``SOURCE_DATE_EPOCH`` for the ``timestamp``
field (https://reproducible-builds.org/specs/source-date-epoch/). Set it in
CI to get byte-identical SBOM output across runs.

Usage:
    python3 scripts/sbom.py [--requirements requirements.txt]
                            [--output sbom.json]
"""

import argparse
import datetime
import importlib.metadata as metadata
import json
import os
import re
import sys

TOOL_NAME = "nixon-sbom"
TOOL_VERSION = "1.0.0"

# name[extras]==version, with optional trailing "; marker" or comment.
# Comment stripping (whitespace + '#') happens before matching.
_PIN_RE = re.compile(
    r"^([A-Za-z0-9_.\-]+(?:\[[A-Za-z0-9_,.\- ]+\])?)\s*==\s*"
    r"([A-Za-z0-9_.\-+!*]+?)\s*(?:;\s*.*)?$"
)
_COMMENT_RE = re.compile(r"\s+#.*$")


def canonical_name(name):
    """PEP 503-ish normalization for metadata lookups (no `packaging` dep)."""
    base = name.split("[", 1)[0]
    return re.sub(r"[-_.]+", "-", base).lower()


def parse_requirements(path):
    """Parse ``==`` pins from a requirements file.

    Returns a list of ``(name, pin_version)`` preserving file order.
    Non-pin lines (options, ``-r`` includes, editable installs, bare names)
    are skipped.
    """
    pins = []
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            line = _COMMENT_RE.sub("", line).strip()
            if not line or line.startswith(("-", "http://", "https://")):
                continue
            match = _PIN_RE.match(line)
            if match:
                pins.append((match.group(1).strip(), match.group(2).strip()))
    return pins


def resolve_version(name, pin):
    """Prefer the installed distribution version; fall back to the pin."""
    try:
        return metadata.version(canonical_name(name))
    except metadata.PackageNotFoundError:
        return pin
    except Exception:
        return pin


def build_sbom(requirements_path):
    """Build the SBOM dict. ``timestamp`` honors ``SOURCE_DATE_EPOCH``."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch is not None:
        try:
            timestamp = datetime.datetime.fromtimestamp(
                int(epoch), tz=datetime.timezone.utc
            ).isoformat()
        except (ValueError, OverflowError, OSError):
            timestamp = None
    else:
        timestamp = None
    if timestamp is None:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    pins = parse_requirements(requirements_path)
    seen = set()
    packages = []
    for name, pin in pins:
        key = canonical_name(name)
        if key in seen:
            continue
        seen.add(key)
        packages.append(
            {
                "name": key,
                "version": resolve_version(name, pin),
                "source": "requirements.txt",
            }
        )
    packages.sort(key=lambda p: p["name"])
    return {
        "tool": "%s %s" % (TOOL_NAME, TOOL_VERSION),
        "timestamp": timestamp,
        "packages": packages,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Emit CycloneDX-ish SBOM JSON.")
    parser.add_argument(
        "--requirements",
        default="requirements.txt",
        help="requirements file to parse pins from",
    )
    parser.add_argument(
        "--output",
        default="sbom.json",
        help="output path (default: sbom.json)",
    )
    args = parser.parse_args(argv)
    sbom = build_sbom(args.requirements)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(sbom, fh, indent=2)
        fh.write("\n")
    print("wrote %s (%d packages)" % (args.output, len(sbom["packages"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
