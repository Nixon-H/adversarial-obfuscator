"""
__init__.py

Purpose:
Package initializer for the runtime security module. Exports the
ChallengeResponse protocol and PythonORAM implementation for use
by other components in the protection pipeline.

Architectural Role:
Serves as the namespace package for runtime-level security primitives
that execute alongside protected code. These modules provide
cryptographic attestation and access-pattern obfuscation that operate
at the Python/runtime layer.

Security Relevance:
Empty init — no security properties. Exists to enable importing from
the submodules. The submodules themselves provide challenge-response
authentication and ORAM-based access pattern hiding.
"""
