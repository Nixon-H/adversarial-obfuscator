"""
metrics/__init__.py

Purpose:
Re-exports all metric classes and standalone computation functions so that
pipeline code can import them from a single location:
    from scripts.metrics import ResilienceMetrics, ContextSaturationMetrics, ...

Architectural Role:
Facade / namespace package. Each metric family lives in its own module
(resilience.py, context_saturation.py, prompt_resistance.py) and is
re-exported here.

Execution Context:
Imported by build.py and evaluation scripts.

Dependencies:
- .resilience: ResilienceMetrics, compute_cfg_entropy, compute_cyclomatic,
  compute_instruction_diversity, compute_dead_code,
  compute_symbolic_resistance, compute_static_confusion
- .context_saturation: ContextSaturationMetrics
- .prompt_resistance: PromptResistanceMetrics
"""
from .resilience import ResilienceMetrics, compute_cfg_entropy, compute_cyclomatic, compute_instruction_diversity, compute_dead_code, compute_symbolic_resistance, compute_static_confusion
from .context_saturation import ContextSaturationMetrics
from .prompt_resistance import PromptResistanceMetrics

__all__ = [
    "ResilienceMetrics",
    "compute_cfg_entropy",
    "compute_cyclomatic",
    "compute_instruction_diversity",
    "compute_dead_code",
    "compute_symbolic_resistance",
    "compute_static_confusion",
    "ContextSaturationMetrics",
    "PromptResistanceMetrics",
]
