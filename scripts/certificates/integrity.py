"""
certificates/integrity.py

Purpose:
Utility hashing functions for AST nodes, IR text, bytes, and source code.
Used by the certificate system to produce input_hash and output_hash values.

Security Relevance:
Hash functions are the integrity foundation of the certificate chain. All
hashes use SHA-256. The hash_ast function uses ast.dump() which is
sensitive to AST structure — two semantically identical ASTs with different
syntactic forms produce different hashes, which is intentional for detecting
structural changes.

Dependencies:
- ast, hashlib (standard library)
"""
import ast
import hashlib


def hash_ast(tree: ast.AST) -> str:
    source = ast.dump(tree, indent=None)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def hash_ir(ir_text: str) -> str:
    return hashlib.sha256(ir_text.encode("utf-8")).hexdigest()


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_source(source_code: str) -> str:
    return hashlib.sha256(source_code.encode("utf-8")).hexdigest()
