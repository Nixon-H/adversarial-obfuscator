"""
phase_adversarial_bench.py

Purpose:
Generates and runs adversarial benchmark tests — systematically probes
the pipeline with adversarial inputs designed to bypass protections
and reports vulnerability rate.

Architectural Role:
Adversarial evaluation phase — stress-tests protection effectiveness.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.adversarial_bench

Security Relevance:
Adversarial benchmarking reveals weaknesses that standard testing
would miss by targeting known bypass techniques.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.adversarial_bench import AdversarialBenchGenerator, AdversarialTestSuite


def phase_adversarial_bench(args: Any) -> Optional[dict]:
    """
    Generate and run adversarial benchmark tests.

    Args:
        args: argparse.Namespace

    Returns:
        dict with report or None if disabled
    """
    enabled = getattr(args, "adversarial_bench", False)
    if not enabled:
        log("ADV_BENCH", "Adversarial benchmark disabled (use --adversarial-bench)")
        return None

    count = getattr(args, "adversarial_bench_count", 20)
    log("ADV_BENCH", f"Generating {count} adversarial test programs...")

    generator = AdversarialBenchGenerator()
    suite = AdversarialTestSuite()
    suite.load_tests(generator, count=count)

    log("ADV_BENCH", f"Running {len(suite.tests)} adversarial tests...")
    suite.run_all(pipeline=None)

    report = suite.generate_report()

    print()
    print("=" * 60)
    print("  ADVERSARIAL BENCH REPORT")
    print("=" * 60)
    print(f"  Total tests:                    {report['total_tests']}")
    print(f"  Vulnerabilities found:          {report['vulnerabilities_found']}")
    print(f"  Vulnerability rate:             {report['vulnerability_rate']:.2f}%")
    print(f"  Failing targets:                {', '.join(report['failing_targets']) if report['failing_targets'] else 'none'}")
    print(f"  Total elapsed:                  {report['total_elapsed_ms']:.2f}ms")
    print()
    for system, sys_data in sorted(report.get("by_system", {}).items()):
        print(f"  [{system:>12s}] {sys_data['total']:2d} tests, "
              f"{sys_data['vulnerabilities']:2d} vulns, "
              f"{sys_data['average_elapsed_ms']:.2f}ms avg")
    print("=" * 60)
    print()

    report_path = os.path.join(BUILD_DIR, "adversarial_bench_report.json")
    os.makedirs(BUILD_DIR, exist_ok=True)
    atomic_write(report_path, json.dumps(report, indent=2))
    log("ADV_BENCH", f"Report saved to {report_path}")

    return report
