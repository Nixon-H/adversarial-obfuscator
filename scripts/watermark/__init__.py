"""Semantic Watermarking for Nixon IR.

Embeds ownership information into the intermediate representation's structural
decisions rather than into data constants, making removal require semantic
recompilation that changes program behavior.
"""

from .semantic_watermark import (
    embed_watermark,
    extract_watermark,
    verify_watermark,
    message_to_bits,
    bits_to_message,
)

__all__ = [
    "embed_watermark",
    "extract_watermark",
    "verify_watermark",
    "message_to_bits",
    "bits_to_message",
]
