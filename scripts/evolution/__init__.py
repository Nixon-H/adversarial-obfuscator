"""Code Genome Evolution module (Items 87)."""

from .code_genome import evolve
from .ir_genome import IrGenome, IrInstruction

# Re-exported names: listed explicitly so the intent is
# unambiguous and the unused-import check does not flag them.
__all__ = [
    "IrGenome",
    "IrInstruction",
    "evolve",
]
