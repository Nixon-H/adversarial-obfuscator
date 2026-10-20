"""
phase_knowledge_graph.py

Purpose:
Builds a security knowledge graph connecting features, metrics, attacks,
and proofs into a directed graph.  Exported as JSON and GraphML for
visualization and analysis.

Architectural Role:
Analysis/visualization phase — runs after protections to map the
security landscape.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
os, typing, ..common, ..knowledge_graph

Security Relevance:
The knowledge graph provides a holistic view of the security posture,
revealing relationships between protections and attack vectors.
"""

from __future__ import annotations

import os

from ..common import BUILD_DIR, log
from ..knowledge_graph import build_knowledge_graph


def phase_knowledge_graph(args, coverage_map=None, conflict_graph=None):
    """
    Build security knowledge graph from pipeline outputs.

    Args:
        args: argparse.Namespace
        coverage_map: optional coverage map data
        conflict_graph: optional conflict data

    Returns:
        KnowledgeGraph or None if disabled
    """
    enabled = getattr(args, "knowledge_graph", False)
    if not enabled:
        log("KNOWLEDGE_GRAPH", "Security knowledge graph disabled (use --knowledge-graph to enable)")
        return None

    output_dir = getattr(args, "knowledge_graph_output", None) or os.path.join(BUILD_DIR, "knowledge_graph")
    os.makedirs(output_dir, exist_ok=True)

    log("KNOWLEDGE_GRAPH", "Building security knowledge graph...")

    kg = build_knowledge_graph(coverage_map=coverage_map, conflict_graph=conflict_graph)

    json_path = os.path.join(output_dir, "knowledge_graph.json")
    kg.to_json(json_path)
    log("KNOWLEDGE_GRAPH", f"JSON knowledge graph → {json_path}")

    graphml_path = os.path.join(output_dir, "knowledge_graph.graphml")
    kg.to_graphml(graphml_path)
    log("KNOWLEDGE_GRAPH", f"GraphML knowledge graph → {graphml_path}")

    node_count, edge_count = kg.size()
    log("KNOWLEDGE_GRAPH", f"Graph stats: {node_count} nodes, {edge_count} edges")

    feature_count = len([n for n in kg._nodes.values() if n.node_type.value == "feature"])
    metric_count = len([n for n in kg._nodes.values() if n.node_type.value == "metric"])
    attack_count = len([n for n in kg._nodes.values() if n.node_type.value == "attack"])
    proof_count = len([n for n in kg._nodes.values() if n.node_type.value == "proof"])
    log("KNOWLEDGE_GRAPH", f"  Features: {feature_count}, Metrics: {metric_count}, Attacks: {attack_count}, Proofs: {proof_count}")

    print()
    print("=" * 60)
    print("  SECURITY KNOWLEDGE GRAPH")
    print("=" * 60)
    print(f"  Total nodes: {node_count}")
    print(f"  Total edges: {edge_count}")
    print(f"  Feature nodes: {feature_count}")
    print(f"  Metric nodes: {metric_count}")
    print(f"  Attack nodes: {attack_count}")
    print(f"  Proof nodes: {proof_count}")
    print(f"  JSON: {json_path}")
    print(f"  GraphML: {graphml_path}")
    print("=" * 60)
    print()

    return kg
