"""
builder.py

Purpose:
Constructs a fully-populated KnowledgeGraph from the feature registry,
known conflicts, attack vectors, metric definitions, and proof
annotations. Optionally links coverage and conflict data.

Architectural Role:
Builder layer for the knowledge graph. Uses the factory pattern:
build_knowledge_graph() creates a new graph and populates it by
calling add_all_features, add_protection_relationships,
add_metric_links, add_attack_vectors, and add_proof_links.
Optionally attaches coverage and conflict data.

Execution Context:
Called during knowledge graph build step. The builder reads from
ALL_FEATURES (feature_registry.py) and hardcoded relationship tables
below. Coverage and conflict data are linked optionally.

Dependencies:
- graph (KnowledgeGraph, GraphNode, GraphEdge, NodeType, EdgeType)
- feature_registry (ALL_FEATURES, FEATURE_NAMES)

Security Relevance:
Encodes all expert knowledge about protection interactions (what
enhances what, what conflicts with what, what attacks what) into
a machine-readable graph. This graph drives automated protection
planning and reasoning.

Maintenance Notes:
- The ATTACK_VECTORS and METRIC_IDS lists are hardcoded here and must
  be updated when new attack vectors or metrics are added.
- Relationship pairs (enhancement_pairs, weakens_pairs, subsumes_pairs)
  are hardcoded; adding a new pair requires updating the respective list.
- The _link_coverage_data and _link_conflict_graph methods use duck
  typing and wrap with try/except to handle missing data gracefully.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .graph import KnowledgeGraph, GraphNode, GraphEdge, NodeType, EdgeType
from .feature_registry import ALL_FEATURES, FEATURE_NAMES

ATTACK_VECTORS: List[Dict[str, Any]] = [
    {"id": "ghidra_static", "name": "Ghidra Static Analysis", "targets": ["cfg_flatten", "opaque_predicates"]},
    {"id": "angr_symbolic", "name": "Angr Symbolic Execution", "targets": ["opaque_predicates", "bogus_exceptions"]},
    {"id": "llm_decompile", "name": "LLM Decompilation", "targets": ["unicode_ids", "fragment_strings"]},
    {"id": "symbolic_exec", "name": "Symbolic Execution Engine", "targets": ["cfg_flatten", "mba_subs"]},
    {"id": "taint_analysis", "name": "Taint Analysis", "targets": ["data_obfuscation", "crypto_binding"]},
    {"id": "side_channel", "name": "Side-Channel Timing", "targets": ["tee", "sgx", "cache_bound"]},
    {"id": "differential", "name": "Differential Analysis", "targets": ["diversity", "code_genome"]},
    {"id": "fuzzing", "name": "Fuzz Testing", "targets": ["vm_protection", "state_isa"]},
    {"id": "power_analysis", "name": "Power Analysis", "targets": ["hpc", "tee"]},
    {"id": "emulation", "name": "Emulation Detection Bypass", "targets": ["hpc", "cache_bound"]},
]

METRIC_IDS: List[Dict[str, Any]] = [
    {"id": "coverage", "name": "Protection Coverage", "description": "Percentage of functions covered by each protection"},
    {"id": "exposure", "name": "Plaintext Exposure", "description": "Time window where plaintext is exposed in memory"},
    {"id": "leakage", "name": "Semantic Leakage", "description": "Information leakage between original and obfuscated code"},
    {"id": "proof_coverage", "name": "Proof Coverage", "description": "Percentage of protections covered by formal proofs"},
    {"id": "resilience", "name": "Resilience Score", "description": "Overall protection resilience against reverse engineering"},
    {"id": "entropy", "name": "Code Entropy", "description": "Shannon entropy of obfuscated binary"},
    {"id": "survivability", "name": "Survivability Index", "description": "Expected survival time against determined adversary"},
]


def build_knowledge_graph(coverage_map: Any = None, conflict_graph: Any = None) -> KnowledgeGraph:
    """
    Construct and populate a complete knowledge graph.

    Starts with all features from the registry, then adds protection
    relationships (depends_on, conflicts_with, enhances, weakens,
    subsumes), metric links, attack vectors, and proof links.
    Optionally attaches coverage data and conflict-graph edges.
    Returns the populated KnowledgeGraph.
    """
    kg = KnowledgeGraph()
    add_all_features(kg)
    add_protection_relationships(kg)
    add_metric_links(kg)
    add_attack_vectors(kg)
    add_proof_links(kg)

    if coverage_map is not None:
        _link_coverage_data(kg, coverage_map)

    if conflict_graph is not None:
        _link_conflict_graph(kg, conflict_graph)

    return kg


def add_all_features(graph: KnowledgeGraph) -> None:
    """
    Add all features from ALL_FEATURES to the graph as FEATURE nodes.
    """
    for feat in ALL_FEATURES:
        node = GraphNode(
            id=feat["id"],
            node_type=NodeType.FEATURE,
            label=feat["name"],
            description=feat["description"],
            properties={
                "category": feat["category"],
            },
            metadata={
                "depends_on": feat["depends_on"],
                "conflicts_with": feat["conflicts_with"],
            },
        )
        graph.add_node(node)


def add_protection_relationships(graph: KnowledgeGraph) -> None:
    """
    Add dependency, conflict, enhancement, weakening, and subsumption
    edges between features based on ALL_FEATURES metadata and
    hardcoded relationship tables.
    """
    for feat in ALL_FEATURES:
        for dep_id in feat.get("depends_on", []):
            if graph.get_node(dep_id) is None:
                dep_node = GraphNode(
                    id=dep_id,
                    node_type=NodeType.DEPENDENCY,
                    label=dep_id,
                    description=f"Dependency referenced by {feat['id']}",
                )
                graph.add_node(dep_node)
            edge = GraphEdge(
                source=feat["id"],
                target=dep_id,
                edge_type=EdgeType.DEPENDS_ON,
                weight=1.0,
            )
            graph.add_edge(edge)

        for conflict_id in feat.get("conflicts_with", []):
            if graph.get_node(conflict_id) is None:
                conflict_node = GraphNode(
                    id=conflict_id,
                    node_type=NodeType.CONFLICT,
                    label=conflict_id,
                    description=f"Conflict referenced by {feat['id']}",
                )
                graph.add_node(conflict_node)
            edge = GraphEdge(
                source=feat["id"],
                target=conflict_id,
                edge_type=EdgeType.CONFLICTS_WITH,
                weight=1.0,
            )
            graph.add_edge(edge)

    enhancement_pairs = [
        ("crypto_binding", "flow_entangle"), ("flow_entangle", "attestation"),
        ("rolling_keys", "temporal_keys"), ("fragmentation", "micro_fragment"),
        ("fragmentation", "payload_dispersal"), ("diversity", "code_genome"),
        ("diversity", "poly_engine"), ("diversity", "per_exec_recompile"),
        ("cfg_flatten", "control_flow_flatten"), ("state_isa", "vm_protection"),
    ]
    for src, tgt in enhancement_pairs:
        if graph.get_node(src) and graph.get_node(tgt):
            edge = GraphEdge(source=src, target=tgt, edge_type=EdgeType.ENHANCES, weight=0.8)
            graph.add_edge(edge)

    weakens_pairs = [
        ("cfg_flatten", "ssa_mutation"), ("cfg_flatten", "history_bound_decryption"),
        ("ir_encryption", "proof_carrying"), ("fragmentation", "proof_carrying"),
        ("opaque_predicates", "proof_carrying"), ("fragment_strings", "watermark"),
        ("kernel_assist", "tee"), ("kernel_assist", "sgx"),
        ("fhe_vm", "vm_protection"), ("fhe_vm", "rop_protection"),
    ]
    for src, tgt in weakens_pairs:
        if graph.get_node(src) and graph.get_node(tgt):
            edge = GraphEdge(source=src, target=tgt, edge_type=EdgeType.WEAKENS, weight=0.6)
            graph.add_edge(edge)

    subsumes_pairs = [
        ("control_flow_flatten", "cfg_flatten"), ("micro_fragment", "fragmentation"),
        ("distributed_protection", "payload_dispersal"),
    ]
    for src, tgt in subsumes_pairs:
        if graph.get_node(src) and graph.get_node(tgt):
            edge = GraphEdge(source=src, target=tgt, edge_type=EdgeType.SUBSUMES, weight=0.9)
            graph.add_edge(edge)


def add_metric_links(graph: KnowledgeGraph) -> None:
    """
    Add METRIC nodes and MEASURES edges linking metrics to the
    features they evaluate.
    """
    for metric in METRIC_IDS:
        node = GraphNode(
            id=metric["id"],
            node_type=NodeType.METRIC,
            label=metric["name"],
            description=metric["description"],
        )
        graph.add_node(node)

    metric_feature_links = [
        ("coverage", "cfg_flatten"), ("coverage", "opaque_predicates"),
        ("coverage", "mba_subs"), ("coverage", "fragment_strings"),
        ("exposure", "fragmentation"), ("exposure", "micro_fragment"),
        ("exposure", "microjit"), ("exposure", "fhe_vm"),
        ("leakage", "ir_encryption"), ("leakage", "data_obfuscation"),
        ("proof_coverage", "proof_carrying"), ("proof_coverage", "mba_subs"),
        ("resilience", "vm_protection"), ("resilience", "diversity"),
        ("survivability", "self_healing"), ("survivability", "code_genome"),
        ("entropy", "entropy_flatten"),
    ]
    for metric_id, feat_id in metric_feature_links:
        if graph.get_node(metric_id) and graph.get_node(feat_id):
            edge = GraphEdge(
                source=metric_id,
                target=feat_id,
                edge_type=EdgeType.MEASURES,
                weight=1.0,
            )
            graph.add_edge(edge)


def add_attack_vectors(graph: KnowledgeGraph) -> None:
    """
    Add ATTACK nodes and ATTACKS edges linking each attack vector
    to the features it targets.
    """
    for attack in ATTACK_VECTORS:
        node = GraphNode(
            id=attack["id"],
            node_type=NodeType.ATTACK,
            label=attack["name"],
            description=f"Attack vector: {attack['name']}",
            properties={"targets": attack["targets"]},
        )
        graph.add_node(node)

        for target_id in attack["targets"]:
            if graph.get_node(target_id):
                edge = GraphEdge(
                    source=attack["id"],
                    target=target_id,
                    edge_type=EdgeType.ATTACKS,
                    weight=0.7,
                )
                graph.add_edge(edge)


def add_proof_links(graph: KnowledgeGraph) -> None:
    """
    Add PROOF nodes and PROVES edges linking each proof to the
    features it formally verifies.
    """
    proof_nodes = [
        {"id": "vm_correctness_proof", "label": "VM Correctness Proof", "proves": ["vm_protection", "state_isa"]},
        {"id": "fragment_safety_proof", "label": "Fragment Safety Proof", "proves": ["fragmentation", "micro_fragment"]},
        {"id": "watermark_survivability_proof", "label": "Watermark Survivability Proof", "proves": ["watermark"]},
        {"id": "mutation_safety_proof", "label": "Mutation Safety Proof", "proves": ["cfg_mutation", "ssa_mutation"]},
        {"id": "jit_correctness_proof", "label": "JIT Correctness Proof", "proves": ["microjit"]},
        {"id": "equivalence_proof", "label": "Semantic Equivalence Proof", "proves": ["proof_carrying", "mba_subs"]},
    ]
    for pn in proof_nodes:
        node = GraphNode(
            id=pn["id"],
            node_type=NodeType.PROOF,
            label=pn["label"],
            description=f"Formal proof for {', '.join(pn['proves'])}",
        )
        graph.add_node(node)

        for target_id in pn["proves"]:
            if graph.get_node(target_id):
                edge = GraphEdge(
                    source=pn["id"],
                    target=target_id,
                    edge_type=EdgeType.PROVES,
                    weight=1.0,
                )
                graph.add_edge(edge)


def _link_coverage_data(kg: KnowledgeGraph, coverage_map: Any) -> None:
    try:
        if hasattr(coverage_map, "per_protection_stats"):
            for pname, stats in coverage_map.per_protection_stats.items():
                feat_id = pname.lower().replace(" ", "_").replace("-", "_")
                if kg.get_node(feat_id) is None:
                    continue
                ratio = stats.get("coverage_ratio", 0)
                metric_node = GraphNode(
                    id=f"coverage_{feat_id}",
                    node_type=NodeType.METRIC,
                    label=f"Coverage.{pname}",
                    description=f"Coverage ratio for {pname}: {ratio:.2%}",
                    properties={"ratio": ratio, "covered": stats.get("functions_covered", 0)},
                )
                kg.add_node(metric_node)
                edge = GraphEdge(
                    source=metric_node.id,
                    target=feat_id,
                    edge_type=EdgeType.MEASURES,
                    weight=ratio,
                )
                kg.add_edge(edge)
    except Exception:
        pass


def _link_conflict_graph(kg: KnowledgeGraph, conflict_graph: Any) -> None:
    try:
        if hasattr(conflict_graph, "to_dict"):
            data = conflict_graph.to_dict()
            for edge_data in data.get("edges", []):
                src_id = edge_data.get("source", "").replace("--", "").replace("no_", "")
                tgt_id = edge_data.get("target", "").replace("--", "").replace("no_", "")
                if kg.get_node(src_id) and kg.get_node(tgt_id):
                    edge = GraphEdge(
                        source=src_id,
                        target=tgt_id,
                        edge_type=EdgeType.CONFLICTS_WITH,
                        weight=1.0,
                        metadata={
                            "type": edge_data.get("type", ""),
                            "severity": edge_data.get("severity", ""),
                            "description": edge_data.get("description", ""),
                        },
                    )
                    kg.add_edge(edge)
    except Exception:
        pass


def graph_to_json(graph: KnowledgeGraph) -> str:
    return json.dumps(graph.to_dict(), indent=2)


def graph_to_graphml(graph: KnowledgeGraph) -> str:
    import io
    buf = io.StringIO()
    graph.to_graphml(buf)
    return buf.getvalue()
