"""
phase_verification_diversity.py

Purpose:
Analyzes verification diversity — measures how many different verification
strategies (type checking, model checking, testing, formal proof) cover
each module.  Higher diversity means fewer blind spots.

Architectural Role:
Verification quality phase — ensures multi-layered verification coverage.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.verification_diversity.*

Security Relevance:
Verification diversity prevents single-method failures; if one verifier
misses a bug, another may catch it.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.verification_diversity.diversity import analyze_verification_diversity



def phase_verification_diversity(args: Any) -> dict | None:
    """
    Analyze verification diversity across modules.

    Args:
        args: argparse.Namespace

    Returns:
        dict with diversity_score and disagreements, or None if disabled
    """
    enabled = getattr(args, "verification_diversity", False)
    if not enabled:
        log("DIVERSITY", "Verification diversity analyzer disabled (use --verification-diversity)")
        return None
    log("DIVERSITY", "Analyzing verification diversity...")
    result = analyze_verification_diversity()
    os.makedirs(BUILD_DIR, exist_ok=True)
    atomic_write(os.path.join(BUILD_DIR, "verification_diversity.json"), json.dumps(result, indent=2))
    print("\n" + "=" * 60 + "\n  VERIFICATION DIVERSITY\n" + "=" * 60)
    print(f"  Diversity Score:    {result.get('diversity_score', 0):.1f}/100")
    print(f"  Total Modules:      {result.get('total_modules', 0)}")
    print(f"  Disagreements:      {len(result.get('disagreements', []))}")
    for strat, res in result.get("per_strategy_results", {}).items():
        print(f"  {strat:>12s}: {len(res)} results")
    print("=" * 60)
    return result
