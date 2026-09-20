"""
phase10_provenance.py

Purpose:
Applies provenance poisoning to the obfuscated payload — injects fake
call graphs, dummy APIs, fake protocol parsers, believable dead paths,
and misleading imports to mislead reverse engineers and LLM analysis.

Architectural Role:
Runs after obfuscation.  Modifies the payload in-place with misleading
provenance signals.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
ast, os, ..common, scripts.provenance.poisoner

Security Relevance:
Provenance poisoning creates false signals that mislead attribution,
LLM analysis, and reverse-engineering heuristics.
"""

import ast
import os


def phase_provenance_poison(payload: str, output: str, opts) -> None:
    """
    Poison the payload with misleading provenance signals.

    Supports categories: fake_call_graphs, fake_apis, fake_protocol_parsers,
    believable_dead_paths, misleading_imports.  Selected via CLI flags or
    a numeric poison_level (1-5).

    Args:
        payload: path to the input .py file
        output: path for the poisoned output
        opts: argparse.Namespace with poison flags
    """
    from ..common import log

    log("PROVENANCE", "Applying provenance poisoning...")

    try:
        from scripts.provenance.poisoner import ProvenancePoisoner
    except ImportError:
        log("ERROR", "Cannot import ProvenancePoisoner")
        return

    all_categories = list(ProvenancePoisoner.CATEGORIES)
    enabled_categories = []
    if opts.poison_all or opts.provenance_poison:
        enabled_categories = list(all_categories)
    else:
        mapping = {
            "poison_call_graph": "fake_call_graphs",
            "poison_apis": "fake_apis",
            "poison_protocols": "fake_protocol_parsers",
            "poison_paths": "believable_dead_paths",
            "poison_imports": "misleading_imports",
        }
        for attr, cat in mapping.items():
            if getattr(opts, attr, False):
                enabled_categories.append(cat)

    if getattr(opts, "poison_level", 0):
        level = min(max(opts.poison_level, 1), 5)
        if level >= 1:
            enabled_categories.append("fake_call_graphs")
        if level >= 2:
            enabled_categories.append("fake_apis")
        if level >= 3:
            enabled_categories.append("fake_protocol_parsers")
        if level >= 4:
            enabled_categories.append("believable_dead_paths")
        if level >= 5:
            enabled_categories.append("misleading_imports")

    enabled_categories = list(dict.fromkeys(enabled_categories))

    if not enabled_categories:
        log("SKIP", "No poisoning categories enabled")
        return

    with open(payload, "r") as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        log("ERROR", f"Syntax error in {payload}: {e}")
        return

    seed = hash(payload + str(opts) + "provenance") & 0xFFFFFFFF
    poisoner = ProvenancePoisoner(seed=seed)
    tree = poisoner.poison(tree, {"categories": enabled_categories})

    result = ast.unparse(tree)
    with open(output, "w") as f:
        f.write(result)

    size = os.path.getsize(output)
    log("PROVENANCE", f"Done: {size/1024:.1f}KB with categories: {enabled_categories}")
