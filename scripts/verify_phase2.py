#!/usr/bin/env python3
"""Verify all Advanced Protection components are properly installed and importable."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

COMPONENTS = [
    'obfuscator.classification',
    'obfuscator.provenance',
    'obfuscator.dataflow',
    'irgen.watermark',
    'irgen.variant_pool',
    'irgen.fragmentation',
    'irgen.jit_template',
    'irgen.mutation',
    'vm.vm_isa',
    'vm.bytecode_compiler',
    'vm.interpreter',
]


def verify():
    """Try importing all Advanced Protection components."""
    results = {}
    for component in COMPONENTS:
        try:
            __import__(component)
            results[component] = True
        except ImportError as e:
            results[component] = False
            print(f"  MISSING: {component} — {e}")

    available = sum(results.values())
    total = len(results)
    print(f"Advanced Protection components: {available}/{total} available")
    return all(results.values())


if __name__ == "__main__":
    success = verify()
    exit(0 if success else 1)
