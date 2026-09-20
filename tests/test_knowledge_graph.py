"""
test_knowledge_graph.py

Tests for Security Knowledge Graph construction and querying.

Test coverage:
- Positive tests verify graph building, entity/relation extraction, querying
- Negative tests verify empty inputs, missing data, edge cases
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.knowledge_graph import (
    KnowledgeGraph, GraphNode, GraphEdge, NodeType, EdgeType,
    build_knowledge_graph, ALL_FEATURES,
)


class TestGraphNode:
    """
    TestGraphNode
    
    Positive test cases for graphnode.
    """
    def test_graph_node(self):
        node = GraphNode(id="test", node_type=NodeType.FEATURE, label="Test Feature")
        assert node.id == "test"
        assert node.node_type == NodeType.FEATURE
        assert node.label == "Test Feature"

    def test_graph_node_default_label(self):
        node = GraphNode(id="test_id", node_type=NodeType.FEATURE)
        assert node.label == "test_id"

    def test_graph_node_metadata(self):
        node = GraphNode(id="test", node_type=NodeType.METRIC, metadata={"key": "val"})
        assert node.metadata["key"] == "val"

    def test_graph_node_properties(self):
        node = GraphNode(id="test", node_type=NodeType.ATTACK, properties={"targets": ["a"]})
        assert node.properties["targets"] == ["a"]


class TestGraphEdge:
    """
    TestGraphEdge
    
    Positive test cases for graphedge.
    """
    def test_graph_edge(self):
        edge = GraphEdge(source="a", target="b", edge_type=EdgeType.DEPENDS_ON)
        assert edge.source == "a"
        assert edge.target == "b"
        assert edge.edge_type == EdgeType.DEPENDS_ON
        assert edge.weight == 1.0

    def test_graph_edge_weight(self):
        edge = GraphEdge(source="a", target="b", edge_type=EdgeType.WEAKENS, weight=0.5)
        assert edge.weight == 0.5

    def test_graph_edge_metadata(self):
        edge = GraphEdge(source="a", target="b", edge_type=EdgeType.ENHANCES, metadata={"info": "test"})
        assert edge.metadata["info"] == "test"


class TestKnowledgeGraph:
    """
    TestKnowledgeGraph
    
    Positive test cases for knowledgegraph.
    """
    def test_add_node(self):
        kg = KnowledgeGraph()
        node = GraphNode(id="feature_1", node_type=NodeType.FEATURE)
        kg.add_node(node)
        assert kg.get_node("feature_1") is node

    def test_add_edge(self):
        kg = KnowledgeGraph()
        kg.add_node(GraphNode(id="a", node_type=NodeType.FEATURE))
        kg.add_node(GraphNode(id="b", node_type=NodeType.FEATURE))
        edge = GraphEdge(source="a", target="b", edge_type=EdgeType.DEPENDS_ON)
        kg.add_edge(edge)
        assert len(kg.get_edges_from("a")) == 1
        assert len(kg.get_edges_to("b")) == 1

    def test_dedup_nodes(self):
        kg = KnowledgeGraph()
        n1 = GraphNode(id="dup", node_type=NodeType.FEATURE, label="First")
        n2 = GraphNode(id="dup", node_type=NodeType.METRIC, label="Second")
        kg.add_node(n1)
        kg.add_node(n2)
        assert kg.get_node("dup").label == "Second"
        assert kg.size() == (1, 0)

    def test_dedup_edges(self):
        kg = KnowledgeGraph()
        kg.add_node(GraphNode(id="a", node_type=NodeType.FEATURE))
        kg.add_node(GraphNode(id="b", node_type=NodeType.FEATURE))
        e1 = GraphEdge(source="a", target="b", edge_type=EdgeType.DEPENDS_ON)
        e2 = GraphEdge(source="a", target="b", edge_type=EdgeType.DEPENDS_ON)
        kg.add_edge(e1)
        kg.add_edge(e2)
        assert len(kg._edges) == 1

    def test_get_neighbors(self):
        kg = KnowledgeGraph()
        kg.add_node(GraphNode(id="a", node_type=NodeType.FEATURE))
        kg.add_node(GraphNode(id="b", node_type=NodeType.FEATURE))
        kg.add_node(GraphNode(id="c", node_type=NodeType.FEATURE))
        kg.add_edge(GraphEdge(source="a", target="b", edge_type=EdgeType.DEPENDS_ON))
        kg.add_edge(GraphEdge(source="c", target="a", edge_type=EdgeType.ENHANCES))
        neighbors = kg.get_neighbors("a")
        neighbor_ids = {n.id for n in neighbors}
        assert neighbor_ids == {"b", "c"}

    def test_query_by_type(self):
        kg = KnowledgeGraph()
        kg.add_node(GraphNode(id="f1", node_type=NodeType.FEATURE))
        kg.add_node(GraphNode(id="f2", node_type=NodeType.FEATURE))
        kg.add_node(GraphNode(id="m1", node_type=NodeType.METRIC))
        results = kg.query(node_type=NodeType.FEATURE)
        assert len(results) == 2
        results = kg.query(node_type=NodeType.METRIC)
        assert len(results) == 1
        results = kg.query(node_type=NodeType.ATTACK)
        assert len(results) == 0

    def test_query_by_edge_type(self):
        kg = KnowledgeGraph()
        kg.add_node(GraphNode(id="a", node_type=NodeType.FEATURE))
        kg.add_node(GraphNode(id="b", node_type=NodeType.FEATURE))
        kg.add_node(GraphNode(id="c", node_type=NodeType.FEATURE))
        kg.add_edge(GraphEdge(source="a", target="b", edge_type=EdgeType.DEPENDS_ON))
        kg.add_edge(GraphEdge(source="c", target="a", edge_type=EdgeType.ENHANCES))
        results = kg.query(edge_type=EdgeType.DEPENDS_ON)
        assert len(results) == 2
        result_ids = {n.id for n in results}
        assert "a" in result_ids
        assert "b" in result_ids

    def test_query_by_property(self):
        kg = KnowledgeGraph()
        kg.add_node(GraphNode(id="a", node_type=NodeType.FEATURE, properties={"category": "crypto"}))
        kg.add_node(GraphNode(id="b", node_type=NodeType.FEATURE, properties={"category": "control_flow"}))
        results = kg.query(property_filter={"category": "crypto"})
        assert len(results) == 1
        assert results[0].id == "a"

    def test_to_dict(self):
        kg = KnowledgeGraph()
        kg.add_node(GraphNode(id="f1", node_type=NodeType.FEATURE, label="Feature 1"))
        kg.add_node(GraphNode(id="f2", node_type=NodeType.FEATURE, label="Feature 2"))
        kg.add_edge(GraphEdge(source="f1", target="f2", edge_type=EdgeType.DEPENDS_ON, weight=1.0))
        data = kg.to_dict()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["edges"][0]["source"] == "f1"
        assert data["edges"][0]["target"] == "f2"

    def test_to_json(self):
        kg = KnowledgeGraph()
        kg.add_node(GraphNode(id="t", node_type=NodeType.FEATURE))
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp_path = f.name
        try:
            kg.to_json(tmp_path)
            with open(tmp_path) as f:
                data = json.load(f)
            assert len(data["nodes"]) == 1
            assert data["nodes"][0]["id"] == "t"
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_to_graphml(self):
        kg = KnowledgeGraph()
        kg.add_node(GraphNode(id="n1", node_type=NodeType.FEATURE, label="Node 1"))
        kg.add_node(GraphNode(id="n2", node_type=NodeType.FEATURE, label="Node 2"))
        kg.add_edge(GraphEdge(source="n1", target="n2", edge_type=EdgeType.DEPENDS_ON))
        with tempfile.NamedTemporaryFile(mode="w", suffix=".graphml", delete=False) as f:
            tmp_path = f.name
        try:
            kg.to_graphml(tmp_path)
            with open(tmp_path) as f:
                content = f.read()
            assert '<?xml' in content
            assert 'graphml' in content
            assert 'n1' in content
            assert 'n2' in content
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_from_dict(self):
        data = {
            "nodes": [
                {"id": "a", "node_type": "feature", "label": "A", "description": "", "metadata": {}, "properties": {}},
                {"id": "b", "node_type": "feature", "label": "B", "description": "", "metadata": {}, "properties": {}},
            ],
            "edges": [
                {"source": "a", "target": "b", "edge_type": "depends_on", "weight": 1.0, "metadata": {}},
            ],
        }
        kg = KnowledgeGraph()
        kg.from_dict(data)
        assert kg.size() == (2, 1)
        assert kg.get_node("a") is not None

    def test_merge(self):
        kg1 = KnowledgeGraph()
        kg1.add_node(GraphNode(id="a", node_type=NodeType.FEATURE))
        kg2 = KnowledgeGraph()
        kg2.add_node(GraphNode(id="b", node_type=NodeType.METRIC))
        kg2.add_edge(GraphEdge(source="b", target="a", edge_type=EdgeType.MEASURES))
        kg1.merge(kg2)
        assert kg1.size() == (2, 1)
        assert kg1.get_node("b") is not None

    def test_build_knowledge_graph(self):
        kg = build_knowledge_graph()
        node_count, edge_count = kg.size()
        assert node_count > 30
        assert edge_count > 30
        assert kg.get_node("cfg_flatten") is not None
        assert kg.get_node("mba_subs") is not None

    def test_feature_registry(self):
        assert len(ALL_FEATURES) >= 35
        for feat in ALL_FEATURES:
            assert "id" in feat
            assert "name" in feat
            assert "description" in feat
            assert "category" in feat

    def test_empty_graph(self):
        kg = KnowledgeGraph()
        assert kg.size() == (0, 0)
        data = kg.to_dict()
        assert data["nodes"] == []
        assert data["edges"] == []

    def test_missing_node_edge(self):
        kg = KnowledgeGraph()
        edge = GraphEdge(source="nonexistent_a", target="nonexistent_b", edge_type=EdgeType.DEPENDS_ON)
        kg.add_edge(edge)
        assert len(kg.get_edges_from("nonexistent_a")) == 1
        assert kg.get_node("nonexistent_a") is None
        assert kg.get_neighbors("nonexistent_a") == []

    def test_self_loop(self):
        kg = KnowledgeGraph()
        kg.add_node(GraphNode(id="self", node_type=NodeType.FEATURE))
        edge = GraphEdge(source="self", target="self", edge_type=EdgeType.DEPENDS_ON)
        kg.add_edge(edge)
        assert kg.size() == (1, 1)
        neighbors = kg.get_neighbors("self")
        assert len(neighbors) == 1
        assert neighbors[0].id == "self"

    def test_get_edges_to(self):
        kg = KnowledgeGraph()
        kg.add_node(GraphNode(id="a", node_type=NodeType.FEATURE))
        kg.add_node(GraphNode(id="b", node_type=NodeType.FEATURE))
        kg.add_edge(GraphEdge(source="a", target="b", edge_type=EdgeType.DEPENDS_ON))
        edges = kg.get_edges_to("b")
        assert len(edges) == 1
        assert edges[0].source == "a"

    def test_get_edges_from_empty(self):
        kg = KnowledgeGraph()
        assert kg.get_edges_from("missing") == []

    def test_size(self):
        kg = KnowledgeGraph()
        assert kg.size() == (0, 0)
        kg.add_node(GraphNode(id="x", node_type=NodeType.FEATURE))
        assert kg.size() == (1, 0)
