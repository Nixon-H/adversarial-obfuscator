#!/usr/bin/env python3
"""Profile the obfuscation pipeline to find hot spots.

Usage: python3 scripts/profile_pipeline.py [--output profile.stats]
"""
import cProfile
import pstats
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SOURCE = "def add(a, b):\n    return a + b\n" * 10
OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "pipeline.prof"

def run():
    from obfuscator.core import ObfuscationTransformer
    t = ObfuscationTransformer(seed=42)
    for _ in range(5):
        t.transform(SOURCE)

if __name__ == "__main__":
    cProfile.run("run()", OUTPUT)
    p = pstats.Stats(OUTPUT)
    p.sort_stats("cumtime").print_stats(20)
    print(f"\nProfile saved to {OUTPUT}")
    print("View with: python3 -m pstats {OUTPUT}")
