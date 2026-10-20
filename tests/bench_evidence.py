"""
bench_evidence.py

Benchmarks for Evidence Ledger (Feature 168).

Measures claim registration, evidence addition, and verification performance.
"""
import hashlib
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evidence.ledger import EvidenceLedger, build_evidence_ledger


def _create_large_ledger(tmp_path: str, num_claims: int = 100, files_per_claim: int = 5) -> EvidenceLedger:
    ledger = EvidenceLedger()
    for i in range(num_claims):
        cname = f"benchmark_claim_{i}"
        ledger.register_claim(cname, "benchmark", "security", "measured")
        for j in range(files_per_claim):
            fpath = os.path.join(tmp_path, f"evidence_{i}_{j}.txt")
            with open(fpath, "w") as f:
                f.write(f"evidence data for claim {i} file {j}\n" * 50)
            ledger.add_evidence(cname, "test", fpath)
    return ledger


def bench_ledger_build():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build_dir = os.path.join(root, "build")
    os.makedirs(build_dir, exist_ok=True)

    start = time.perf_counter()
    ledger = build_evidence_ledger(build_dir)
    elapsed = time.perf_counter() - start

    print(f"\n[bench] EvidenceLedger.build_evidence_ledger: {elapsed*1000:.2f}ms")
    print(f"[bench]   Claims: {len(ledger.claims)}, Evidence: {sum(len(v) for v in ledger.evidence.values())}")
    return elapsed


def bench_ledger_verify_all(tmp_path):
    ledger = _create_large_ledger(str(tmp_path), num_claims=200, files_per_claim=3)

    start = time.perf_counter()
    results = ledger.verify_all()
    elapsed = time.perf_counter() - start

    total_ev = sum(len(v) for v in results.values())
    verified = sum(1 for ev_list in results.values() for ev in ev_list if ev.verified)
    print(f"\n[bench] EvidenceLedger.verify_all: {elapsed*1000:.2f}ms")
    print(f"[bench]   Total evidence: {total_ev}, Verified: {verified}")
    return elapsed


def bench_ledger_serialize(tmp_path):
    ledger = _create_large_ledger(str(tmp_path), num_claims=100, files_per_claim=5)

    start = time.perf_counter()
    d = ledger.to_dict()

    json_path = os.path.join(str(tmp_path), "bench_ledger.json")
    with open(json_path, "w") as f:
        json.dump(d, f, indent=2)
    serialize_elapsed = time.perf_counter() - start

    fsize = os.path.getsize(json_path)
    print(f"\n[bench] EvidenceLedger.to_dict + to_json: {serialize_elapsed*1000:.2f}ms")
    print(f"[bench]   JSON size: {fsize} bytes")
    return serialize_elapsed


def bench_evidence_hash(tmp_path):
    num_files = 500
    paths = []
    for i in range(num_files):
        fpath = os.path.join(str(tmp_path), f"hash_file_{i}.dat")
        with open(fpath, "wb") as f:
            f.write(os.urandom(4096))
        paths.append(fpath)

    start = time.perf_counter()
    for p in paths:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        _ = h.hexdigest()
    elapsed = time.perf_counter() - start

    print(f"\n[bench] SHA256 hash of {num_files} × 4KB files: {elapsed*1000:.2f}ms")
    print(f"[bench]   Per file: {elapsed/num_files*1000:.4f}ms")
    return elapsed


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        bench_ledger_build()
        bench_ledger_verify_all(tmp)
        bench_ledger_serialize(tmp)
        bench_evidence_hash(tmp)
