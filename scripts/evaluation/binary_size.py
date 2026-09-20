"""Measure binary size overhead of protection."""
import os
from typing import Dict


def measure_binary_size(file_path: str) -> Dict:
    """Measure size of a binary file in bytes."""
    if not os.path.exists(file_path):
        return {"bytes": 0, "exists": False}
    size_bytes = os.path.getsize(file_path)
    return {
        "bytes": size_bytes,
        "kilobytes": size_bytes / 1024,
        "exists": True,
    }


def measure_size_overhead(unprotected_path: str, protected_path: str) -> Dict:
    """Measure size overhead as (protected_size / unprotected_size)."""
    unprotected = measure_binary_size(unprotected_path)
    protected = measure_binary_size(protected_path)
    if unprotected["bytes"] > 0:
        ratio = protected["bytes"] / unprotected["bytes"]
    else:
        ratio = float('inf')
    return {
        "unprotected": unprotected,
        "protected": protected,
        "overhead_ratio": ratio,
        "overhead_percentage": (ratio - 1.0) * 100,
    }
