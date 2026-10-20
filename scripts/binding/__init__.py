"""
__init__.py

Purpose:
Package initializer for the crypto-binding module. Exports the
CryptoFragmentBinder, BoundFragment, and Fragment classes that
form the core of the fragment-based protection system.

Architectural Role:
Provides the public API surface for binding cryptographic keys to
code fragments. Fragments are individually encrypted and can be
bound to hardware, VM execution context, or temporal keys.

Security Relevance:
Exports the top-level binding primitive. All submodules
(crypto_binding, temporal_key) are imported here to present a
unified interface. The Fragment class represents an opaque payload
unit with optional encryption.
"""

from .crypto_binding import CryptoFragmentBinder, BoundFragment, Fragment

# Re-exported names: listed explicitly so the intent is
# unambiguous and the unused-import check does not flag them.
__all__ = [
    "BoundFragment",
    "CryptoFragmentBinder",
    "Fragment",
]
