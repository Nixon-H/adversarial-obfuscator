"""
graph.py

Purpose:
Core graph data structures for the security knowledge graph. Defines
node types (feature, metric, attack, proof, dependency, conflict),
edge types (depends_on, conflicts_with, subsumes, enhances, weakens,
proves, attacks, measures), and the KnowledgeGraph container class
with query, serialization, and merge operations.

Architectural Role:
Foundation data layer for all knowledge-graph operations. The graph
is built by builder.py and consumed by the synthesis engine, conflict
detector, and artifact generator. Supports JSON and GraphML output.

Execution Context:
Instantiated as an empty graph, then populated by builder.py functions.
Serialized to JSON for persistence and to GraphML for visualization
tools (Gephi, yEd, etc.).

Dependencies:
- Standard library only (json, collections, dataclasses, enum, typing, xml.etree)

Security Relevance:
The typed edge relationships encode expert knowledge about protection
interactions — e.g., "FHE VM CONFLICTS_WITH VM protection" or
"fragmentation ENHANCES micro-fragment". This enables automated
protection planning that respects known conflicts.

Maintenance Notes:
- Adding a new NodeType or EdgeType enum value is a breaking change
  that requires updates to serialization/deserialization in from_dict().
- GraphML output uses XML ElementTree; large graphs (10k+ nodes) may
  be slow to serialize.
- The merge() operation does not deep-merge node metadata; it prefers
  the existing node.
- Query performance is O(n) over all nodes; add indexing for large graphs.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import xml.etree.ElementTree as ET


class NodeType(Enum):
    """Enumeration of node types in the knowledge graph."""
    FEATURE = "feature"
    METRIC = "metric"
    ATTACK = "attack"
    PROOF = "proof"
    DEPENDENCY = "dependency"
    CONFLICT = "conflict"


class EdgeType(Enum):
    """Enumeration of edge types representing named relationships."""
    DEPENDS_ON = "depends_on"
    CONFLICTS_WITH = "conflicts_with"
    SUBSUMES = "subsumes"
    ENHANCES = "enhances"
    WEAKENS = "weakens"
    PROVES = "proves"
    ATTACKS = "attacks"
    MEASURES = "measures"


@dataclass
class GraphNode:
    """
    A node in the knowledge graph.

    Each node has an id, type (feature/metric/attack/proof/etc.),
    optional label/description, extensible metadata dict, and a
    properties dict for structured querying.
    """

    id: str
    node_type: NodeType
    label: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.label:
            self.label = self.id


@dataclass
class GraphEdge:
    """
    A directed, typed edge between two graph nodes.

    source and target are node IDs. edge_type encodes the relationship
    semantics. weight allows expressing the strength of the relationship
    (e.g., 0.8 for a strong enhancement, 0.3 for a weak one).
    """
    source: str
    target: str
    edge_type: EdgeType
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    """
    Directed, typed property graph for protection knowledge.

    Supports adding nodes/edges, querying by node type and edge type,
    serialization to JSON/GraphML, deserialization from dicts, and
    merging with other graphs. Maintains adjacency indexes for
    efficient traversal.
    """

    def __init__(self):
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._edges_from: Dict[str, List[GraphEdge]] = defaultdict(list)
        self._edges_to: Dict[str, List[GraphEdge]] = defaultdict(list)
        self._edge_set: Set[Tuple[str, str, EdgeType]] = set()

    def add_node(self, node: GraphNode) -> None:
        """
        Add a node to the graph. Replaces any existing node with
        the same ID.
        """
        self._nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        """
        Add an edge to the graph. Duplicate edges (same source,
        target, and type) are silently ignored.
        """
        key = (edge.source, edge.target, edge.edge_type)
        if key in self._edge_set:
            return
        self._edge_set.add(key)
        self._edges.append(edge)
        self._edges_from[edge.source].append(edge)
        self._edges_to[edge.target].append(edge)

    def get_node(self, id: str) -> Optional[GraphNode]:
        """Look up a node by its ID. Returns None if not found."""
        return self._nodes.get(id)

    def get_edges_from(self, id: str) -> List[GraphEdge]:
        """Return all edges originating from a node."""
        return self._edges_from.get(id, [])

    def get_edges_to(self, id: str) -> List[GraphEdge]:
        """Return all edges targeting a node."""
        return self._edges_to.get(id, [])

    def get_neighbors(self, id: str) -> List[GraphNode]:
        """
        Return all nodes directly connected to a given node via
        incoming or outgoing edges.
        """
        neighbor_ids: Set[str] = set()
        for e in self._edges_from.get(id, []):
            neighbor_ids.add(e.target)
        for e in self._edges_to.get(id, []):
            neighbor_ids.add(e.source)
        return [self._nodes[nid] for nid in neighbor_ids if nid in self._nodes]

    def query(self, node_type: Optional[NodeType] = None, edge_type: Optional[EdgeType] = None, property_filter: Optional[Dict[str, Any]] = None) -> List[GraphNode]:
        """
        Query nodes by type, edge type, and/or property filter.

        All filters are optional; when multiple are provided they
        are ANDed. property_filter checks exact key-value matches
        in node.properties. edge_type filters to nodes that have
        at least one edge of the given type.
        """
        results = []
        for node in self._nodes.values():
            if node_type is not None and node.node_type != node_type:
                continue
            if property_filter is not None:
                match = True
                for k, v in property_filter.items():
                    if k not in node.properties or node.properties[k] != v:
                        match = False
                        break
                if not match:
                    continue
            if edge_type is not None:
                has_edge = False
                for e in self._edges:
                    if e.edge_type == edge_type and (e.source == node.id or e.target == node.id):
                        has_edge = True
                        break
                if not has_edge:
                    continue
            results.append(node)
        return results

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the graph to a JSON-compatible dict with nodes and edges."""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "node_type": n.node_type.value,
                    "label": n.label,
                    "description": n.description,
                    "metadata": n.metadata,
                    "properties": n.properties,
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "edge_type": e.edge_type.value,
                    "weight": e.weight,
                    "metadata": e.metadata,
                }
                for e in self._edges
            ],
        }

    def to_json(self, path: str) -> None:
        """Write the graph to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    def to_graphml(self, path: str) -> None:
        """Write the graph to a GraphML XML file for visualization tools."""
        root = ET.Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

        node_type_key = ET.SubElement(root, "key")
        node_type_key.set("id", "node_type")
        node_type_key.set("for", "node")
        node_type_key.set("attr.name", "node_type")
        node_type_key.set("attr.type", "string")

        label_key = ET.SubElement(root, "key")
        label_key.set("id", "label")
        label_key.set("for", "node")
        label_key.set("attr.name", "label")
        label_key.set("attr.type", "string")

        desc_key = ET.SubElement(root, "key")
        desc_key.set("id", "description")
        desc_key.set("for", "node")
        desc_key.set("attr.name", "description")
        desc_key.set("attr.type", "string")

        edge_type_key = ET.SubElement(root, "key")
        edge_type_key.set("id", "edge_type")
        edge_type_key.set("for", "edge")
        edge_type_key.set("attr.name", "edge_type")
        edge_type_key.set("attr.type", "string")

        weight_key = ET.SubElement(root, "key")
        weight_key.set("id", "weight")
        weight_key.set("for", "edge")
        weight_key.set("attr.name", "weight")
        weight_key.set("attr.type", "double")

        graph_el = ET.SubElement(root, "graph")
        graph_el.set("id", "G")
        graph_el.set("edgedefault", "directed")

        for node in self._nodes.values():
            node_el = ET.SubElement(graph_el, "node")
            node_el.set("id", node.id)
            d1 = ET.SubElement(node_el, "data")
            d1.set("key", "node_type")
            d1.text = node.node_type.value
            d2 = ET.SubElement(node_el, "data")
            d2.set("key", "label")
            d2.text = node.label
            d3 = ET.SubElement(node_el, "data")
            d3.set("key", "description")
            d3.text = node.description

        for edge in self._edges:
            edge_el = ET.SubElement(graph_el, "edge")
            edge_el.set("source", edge.source)
            edge_el.set("target", edge.target)
            d1 = ET.SubElement(edge_el, "data")
            d1.set("key", "edge_type")
            d1.text = edge.edge_type.value
            d2 = ET.SubElement(edge_el, "data")
            d2.set("key", "weight")
            d2.text = str(edge.weight)

        tree = ET.ElementTree(root)
        tree.write(path, xml_declaration=True, encoding="utf-8")

    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Load graph state from a dict (inverse of to_dict).

        Clears all existing nodes and edges before loading.
        """
        self._nodes.clear()
        self._edges.clear()
        self._edges_from.clear()
        self._edges_to.clear()
        self._edge_set.clear()

        type_map = {e.value: e for e in NodeType}
        for nd in data.get("nodes", []):
            node = GraphNode(
                id=nd["id"],
                node_type=type_map.get(nd["node_type"], NodeType.FEATURE),
                label=nd.get("label", nd["id"]),
                description=nd.get("description", ""),
                metadata=nd.get("metadata", {}),
                properties=nd.get("properties", {}),
            )
            self._nodes[node.id] = node

        edge_type_map = {e.value: e for e in EdgeType}
        for ed in data.get("edges", []):
            edge = GraphEdge(
                source=ed["source"],
                target=ed["target"],
                edge_type=edge_type_map.get(ed["edge_type"], EdgeType.DEPENDS_ON),
                weight=ed.get("weight", 1.0),
                metadata=ed.get("metadata", {}),
            )
            key = (edge.source, edge.target, edge.edge_type)
            self._edge_set.add(key)
            self._edges.append(edge)
            self._edges_from[edge.source].append(edge)
            self._edges_to[edge.target].append(edge)

    def merge(self, other_graph: KnowledgeGraph) -> None:
        """
        Merge another graph into this one.

        Nodes from the other graph are added only if they don't
        already exist. Edges are added via add_edge() (duplicates
        are ignored).
        """
        for node in other_graph._nodes.values():
            if node.id not in self._nodes:
                self._nodes[node.id] = node
        for edge in other_graph._edges:
            self.add_edge(edge)

    def size(self) -> Tuple[int, int]:
        """Return (node_count, edge_count) tuple."""
        return len(self._nodes), len(self._edges)
