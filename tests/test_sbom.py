"""Tests for scripts/sbom.py — stdlib-only SBOM generator (no network)."""

import ast
import copy
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.sbom import (
    build_sbom,
    canonical_name,
    parse_requirements,
)

REQ = os.path.join(os.path.dirname(__file__), "..", "requirements.txt")
SBOM_PY = os.path.join(os.path.dirname(__file__), "..", "scripts", "sbom.py")


def test_pins_parse():
    pins = parse_requirements(REQ)
    assert len(pins) >= 7, pins
    names = {canonical_name(n) for n, _ in pins}
    for expected in (
        "requests",
        "urllib3",
        "numpy",
        "cython",
        "cryptography",
        "pytest",
        "z3-solver",
    ):
        assert expected in names, names
    for _, pin in pins:
        assert pin and " " not in pin


def test_versions_resolve():
    sbom = build_sbom(REQ)
    assert sbom["packages"], "no packages resolved"
    for pkg in sbom["packages"]:
        assert pkg["name"] and pkg["version"], pkg
        assert pkg["source"] == "requirements.txt", pkg


def test_json_valid_and_shaped(tmp_path):
    out = str(tmp_path / "sbom.json")
    rc = subprocess.run(
        [sys.executable, SBOM_PY, "--output", out],
        capture_output=True,
        text=True,
        timeout=60,
        env={k: v for k, v in os.environ.items()
             if k not in ("SOURCE_DATE_EPOCH",)},
    ).returncode
    assert rc == 0
    with open(out, encoding="utf-8") as fh:
        data = json.load(fh)  # raises if invalid JSON
    assert data["tool"].startswith("nixon-sbom ")
    assert data["timestamp"]
    assert isinstance(data["packages"], list) and data["packages"]
    assert [p["name"] for p in data["packages"]] == sorted(
        p["name"] for p in data["packages"]
    )


def test_no_network_usage():
    """sbom.py must not import any network-capable modules (AST check)."""
    with open(SBOM_PY, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    banned = {
        "socket",
        "urllib",
        "http",
        "requests",
        "pip",
        "subprocess",
        "ftplib",
        "smtplib",
    }
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not (imported & banned), imported & banned


def test_deterministic_modulo_timestamp(tmp_path):
    """Two runs differ only in `timestamp` (wall clock), nothing else."""
    outs = [str(tmp_path / ("sbom%d.json" % i)) for i in (0, 1)]
    for out in outs:
        assert subprocess.run(
            [sys.executable, SBOM_PY, "--output", out],
            capture_output=True,
            timeout=60,
        ).returncode == 0
    first, second = (json.load(open(p, encoding="utf-8")) for p in outs)
    first.pop("timestamp")
    second.pop("timestamp")
    assert first == second


def test_source_date_epoch_freezes_timestamp(tmp_path):
    """SOURCE_DATE_EPOCH set -> byte-identical output across runs."""
    env = dict(os.environ, SOURCE_DATE_EPOCH="1700000000")
    outs = [str(tmp_path / ("frozen%d.json" % i)) for i in (0, 1)]
    for out in outs:
        assert subprocess.run(
            [sys.executable, SBOM_PY, "--output", out],
            capture_output=True,
            timeout=60,
            env=env,
        ).returncode == 0
    blobs = [open(p, "rb").read() for p in outs]
    assert blobs[0] == blobs[1]
    data = json.loads(blobs[0].decode("utf-8"))
    assert data["timestamp"].startswith("2023-11-14"), data["timestamp"]
    # Sanity: frozen otherwise equals unfrozen modulo timestamp.
    live = copy.deepcopy(build_sbom(REQ))
    live.pop("timestamp")
    frozen = dict(data)
    frozen.pop("timestamp")
    assert live == frozen
