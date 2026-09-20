"""
bench_knowledge_graph.py

Benchmarks for security knowledge graph.

Measures graph building, node/edge operations, and serialization performance.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.knowledge_graph import (
    KnowledgeGraph, GraphNode, GraphEdge, NodeType, EdgeType,
    build_knowledge_graph, ALL_FEATURES,
)


def bench_graph_construction():
    start = time.perf_counter()
    for _ in range(100):
        kg = KnowledgeGraph()
        for i in range(100):
            kg.add_node(GraphNode(id=f"node_{i}", node_type=NodeType.FEATURE, label=f"Node {i}"))
        for i in range(99):
            kg.add_edge(GraphEdge(source=f"node_{i}", target=f"node_{i + 1}", edge_type=EdgeType.DEPENDS_ON))
    elapsed = time.perf_counter() - start
    print(f"Graph construction (100 runs, 100 nodes, 99 edges): {elapsed:.4f}s ({elapsed/100*1e3:.2f}ms/run)")


def bench_query():
    kg = KnowledgeGraph()
    for i in range(200):
        kg.add_node(GraphNode(id=f"f_{i}", node_type=NodeType.FEATURE, properties={"category": "test" if i % 2 == 0 else "other"}))
    for i in range(0, 200, 2):
        kg.add_edge(GraphEdge(source=f"f_{i}", target=f"f_{i + 1}", edge_type=EdgeType.DEPENDS_ON))

    start = time.perf_counter()
    for _ in range(1000):
        kg.query(node_type=NodeType.FEATURE, property_filter={"category": "test"})
    elapsed = time.perf_counter() - start
    print(f"Query (1000 runs, filter by type+property): {elapsed:.4f}s ({elapsed/1000*1e3:.2f}ms/run)")


def bench_serialization():
    kg = KnowledgeGraph()
    for feat in ALL_FEATURES:
        kg.add_node(GraphNode(id=feat["id"], node_type=NodeType.FEATURE, label=feat["name"]))
    for feat in ALL_FEATURES:
        for dep in feat.get("depends_on", []):
            kg.add_edge(GraphEdge(source=feat["id"], target=dep, edge_type=EdgeType.DEPENDS_ON))
        for con in feat.get("conflicts_with", []):
            kg.add_edge(GraphEdge(source=feat["id"], target=con, edge_type=EdgeType.CONFLICTS_WITH))

    start = time.perf_counter()
    for _ in range(500):
        _ = kg.to_dict()
    elapsed = time.perf_counter() - start
    print(f"Serialization to dict (500 runs): {elapsed:.4f}s ({elapsed/500*1e3:.2f}ms/run)")


def bench_full_build():
    start = time.perf_counter()
    for _ in range(50):
        kg = build_knowledge_graph()
    elapsed = time.perf_counter() - start
    n, e = kg.size()
    print(f"Full build (50 runs): {elapsed:.4f}s ({elapsed/50*1e3:.2f}ms/run)")
    print(f"  Graph size: {n} nodes, {e} edges")


def bench_neighbor_query():
    kg = build_knowledge_graph()
    all_ids = [n.id for n in kg._nodes.values()]

    start = time.perf_counter()
    for _ in range(1000):
        for nid in all_ids[:20]:
            kg.get_neighbors(nid)
    elapsed = time.perf_counter() - start
    print(f"Neighbor query (1000 runs × 20 nodes): {elapsed:.4f}s ({elapsed/1000/20*1e6:.2f}µs/node)")


if __name__ == "__main__":
    print("=" * 60)
    print("  SECURITY KNOWLEDGE GRAPH BENCHMARKS")
    print("=" * 60)
    bench_graph_construction()
    bench_query()
    bench_serialization()
    bench_full_build()
    bench_neighbor_query()
    print("=" * 60)
