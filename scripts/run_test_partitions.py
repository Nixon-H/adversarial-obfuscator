#!/usr/bin/env python3
"""Run the complete pytest suite in bounded, independently executable partitions."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNNER = Path(os.environ.get("TEST_PARTITION_PYTEST_RUNNER", ROOT / "scripts" / "run_pytest.py")).resolve()
OUT_DIR = ROOT / "audit" / "2026-11-25-full" / "test-partitions"

CATEGORY_KEYWORDS = {
    "distributed-network": (
        "distributed", "remote", "network", "relay", "http", "outbound",
        "multi_host", "fragment_migration", "cross_process", "vm_cluster",
    ),
    "vm-ir-llvm": (
        "vm", "irgen", "llvm", "bytecode", "ephemeral", "microjit", "watermark",
        "port_entangle", "variant", "chaff", "mutation", "lowering", "ollvm",
        "instruction_universe",
    ),
    "crypto-container": (
        "encrypt", "crypto", "aes", "chacha", "ed25519", "aead", "container",
        "authenticode", "section_split", "salt", "key", "shamir",
    ),
    "build-native-loader": (
        "build", "native", "loader", "artifact", "artefact", "pipeline", "compile",
        "cython", "packag", "docker", "ci_", "workflow", "reproducible", "portable",
        "c_core", "payload", "manifest", "section", "cli",
    ),
    "security-licensing": (
        "security", "redteam", "licence", "license", "attest", "integrity", "rollback",
        "update", "hwid", "hostguard", "kill", "audit", "provenance", "signature",
        "trust", "anti", "cfi", "hardening", "tamper", "replay", "seed",
    ),
}


def test_files() -> list[Path]:
    files = []
    for path in (ROOT / "tests").rglob("*.py"):
        rel = path.relative_to(ROOT)
        if any(part in {"test_data", "fixtures", "__pycache__"} for part in rel.parts):
            continue
        if path.name.startswith(("test_", "bench_")):
            files.append(path)
    return sorted(files)


def category(path: Path) -> str:
    name = path.name.lower()
    for label, words in CATEGORY_KEYWORDS.items():
        if any(word in name for word in words):
            return label
    return "unit-static"


def partitions(files: list[Path]) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    for path in files:
        groups.setdefault(category(path), []).append(path)
    # Keep the broad static/unit bucket manageable without splitting related
    # subsystem buckets that depend on shared setup/order.
    unit = groups.get("unit-static", [])
    if len(unit) > 80:
        groups.pop("unit-static", None)
        shard_size = (len(unit) + 3) // 4
        for index in range(4):
            shard = unit[index * shard_size:(index + 1) * shard_size]
            if shard:
                groups[f"unit-static-{index + 1}"] = shard
    return groups


def run_partition(name: str, files: list[Path], timeout: int, test_timeout: int, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{name}.log"
    command = [
        sys.executable, str(RUNNER), "-q", "--tb=short", "-p", "no:cacheprovider",
        *[str(path.relative_to(ROOT)) for path in files],
    ]
    env = dict(os.environ)
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "NIXON_TEST_TIMEOUT": str(test_timeout),
        "TMPDIR": tempfile.gettempdir(),
    })
    started = time.monotonic()
    with output_path.open("wb") as output:
        process = subprocess.Popen(
            command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=10)
            returncode = 124
    duration = time.monotonic() - started
    text = output_path.read_text(encoding="utf-8", errors="replace")
    counts = {}
    for count, label in re.findall(
        r"(\d+) (passed|failed|skipped|xfailed|xpassed|errors?|deselected)", text
    ):
        counts[label] = int(count)
    return {
        "name": name,
        "file_count": len(files),
        "command": command,
        "returncode": returncode,
        "timed_out": returncode == 124,
        "duration_seconds": round(duration, 3),
        "counts": counts,
        "output_tail": text[-4000:],
        "log": str(output_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=1800,
                        help="outer deadline per partition in seconds")
    parser.add_argument("--test-timeout", type=int, default=120,
                        help="per-test SIGALRM deadline in seconds")
    parser.add_argument("--only", nargs="*", help="run only named partitions")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR,
                        help="directory for partition logs and results.json")
    args = parser.parse_args()
    files = test_files()
    groups = partitions(files)
    if args.only:
        unknown = set(args.only) - set(groups)
        if unknown:
            raise SystemExit(f"unknown partitions: {sorted(unknown)}")
        groups = {name: groups[name] for name in args.only}
    manifest = {
        "runner": str(RUNNER),
        "file_count": len(files),
        "partition_file_counts": {name: len(paths) for name, paths in groups.items()},
        "partitions": [],
    }
    for name, paths in groups.items():
        print(f"=== {name}: {len(paths)} files ===", flush=True)
        result = run_partition(name, paths, args.timeout, args.test_timeout, args.out_dir)
        manifest["partitions"].append(result)
        (args.out_dir / "results.json").write_text(json.dumps(manifest, indent=2))
        print(f"=== {name}: rc={result['returncode']} "
              f"{result['duration_seconds']}s ===", flush=True)
        if result["returncode"] != 0:
            print(result["output_tail"], flush=True)
    failed = [p["name"] for p in manifest["partitions"] if p["returncode"] != 0]
    manifest["failed_partitions"] = failed
    manifest["all_partitions_passed"] = not failed
    (args.out_dir / "results.json").write_text(json.dumps(manifest, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
