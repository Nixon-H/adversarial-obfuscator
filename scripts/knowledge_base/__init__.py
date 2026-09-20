"""
knowledge_base/__init__.py

Purpose:
Exports SecurityKnowledgeBase and build_knowledge_base for use by the
meta-assurance pipeline.

Architectural Role:
Package init for the Security Knowledge Base feature (F199).

Security Relevance:
The knowledge base consolidates all security-relevant information (assumptions,
failures, fixes, attack discoveries) into a searchable repository.
"""
from __future__ import annotations

from .database import SecurityKnowledgeBase, build_knowledge_base

__all__ = [
    "SecurityKnowledgeBase",
    "build_knowledge_base",
]
