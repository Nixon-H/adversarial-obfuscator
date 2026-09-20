"""
__init__.py

Purpose:
Package initializer for the plaintext exposure metric module. Exports
the exposure tracker, metric, instrumentors, and simulator for
measuring how long sensitive data remains in plaintext memory.

Architectural Role:
One of the core security metrics. Plaintext exposure measures the
time window where encrypted fragments are decrypted in memory,
directly quantifying one of the primary attack surfaces (cold boot,
memory dump, probe).

Execution Context:
Instantiated during build pipeline execution. Instrumentors are
attached to each protection pass. The metric is computed at build
completion and fed to the security regression gates.

Dependencies:
- tracker (ExposureEvent, ExposureTracker, ExposureEventType)
- metric (PlaintextExposureMetric, ExposureReport, compute_exposure_score)
- instrumentors (MicroJIT/Fragmentation/HistoryBound/FHE ExposureInstrumentor)
- simulator (ExposureSimulator)

Security Relevance:
The exposure metric is a key input to the security regression gates.
High exposure scores indicate that data spends too long in plaintext,
making it vulnerable to memory disclosure attacks. The instrumentors
allow per-protection tracking (microjit, fragmentation, FHE, etc.).

Maintenance Notes:
- Adding a new protection with exposure tracking requires:
  (1) a new instrumentor class in instrumentors.py
  (2) registering it in the protection pipeline
  (3) adding the component name to the simulator's protection_config
"""

from .tracker import ExposureEvent, ExposureTracker, ExposureEventType
from .metric import PlaintextExposureMetric, ExposureReport
from .instrumentors import (
    MicroJITExposureInstrumentor,
    FragmentationExposureInstrumentor,
    HistoryBoundExposureInstrumentor,
    FHEExposureInstrumentor,
)
from .simulator import ExposureSimulator
from .metric import compute_exposure_score

__all__ = [
    "ExposureEvent",
    "ExposureTracker",
    "ExposureEventType",
    "PlaintextExposureMetric",
    "ExposureReport",
    "MicroJITExposureInstrumentor",
    "FragmentationExposureInstrumentor",
    "HistoryBoundExposureInstrumentor",
    "FHEExposureInstrumentor",
    "ExposureSimulator",
    "compute_exposure_score",
]
