"""
__init__.py

Purpose:
Package initializer for the security knowledge graph module. Exports
the core graph data structures and builder functions for constructing
a graph of protection features, metrics, attacks, and proofs.

Architectural Role:
Central graph database for the protection ecosystem. The knowledge
graph is consumed by the synthesis engine (for cost-aware planning),
the conflict detector (for dependency/conflict resolution), the
artifact generator (for attack-surface diagrams), and the coverage
system (for linking protection stats to features).

Execution Context:
Built at pipeline start by build_knowledge_graph() and serialized
to build/knowledge_graph.json. Rebuilt when features are added
or relationships change.

Dependencies:
- graph (KnowledgeGraph, GraphNode, GraphEdge, NodeType, EdgeType)
- builder (build_knowledge_graph, add_all_features, etc.)
- feature_registry (ALL_FEATURES)

Security Relevance:
The knowledge graph encodes all known relationships between protection
features — dependencies, conflicts, enhancements, weakenings, and
subsumptions. This enables automated reasoning about protection plans
and surfaces gaps in the protection model.

Maintenance Notes:
- When adding a new feature to ALL_FEATURES in feature_registry.py,
  the knowledge graph is automatically populated via add_all_features.
- Relationship tables (enhancement_pairs, weakens_pairs, subsumes_pairs)
  in builder.py must be updated manually when new relationships arise.
"""

from .graph import KnowledgeGraph, GraphNode, GraphEdge, NodeType, EdgeType
from .builder import build_knowledge_graph, add_all_features, add_protection_relationships, add_metric_links, add_attack_vectors, add_proof_links
from .builder import graph_to_json, graph_to_graphml
from .feature_registry import ALL_FEATURES

__all__ = [
    "KnowledgeGraph", "GraphNode", "GraphEdge", "NodeType", "EdgeType",
    "build_knowledge_graph", "add_all_features", "add_protection_relationships",
    "add_metric_links", "add_attack_vectors", "add_proof_links",
    "graph_to_json", "graph_to_graphml", "ALL_FEATURES",
]
