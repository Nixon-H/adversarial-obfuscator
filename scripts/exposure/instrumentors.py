"""
instrumentors.py

Purpose:
Protection-specific instrumentors that inject exposure tracking calls
into the protection pipeline. Each instrumentor knows when its
protection component transitions data between plaintext and encrypted
states.

Architectural Role:
Bridge between the protection pipeline and the exposure tracker.
Each instrumentor wraps a protection component (MicroJIT, fragmentation,
history-bound decryption, FHE) and calls record_appearance/record_disappearance
at the appropriate transition points.

Execution Context:
Instantiated with a shared ExposureTracker. Called by protection passes
during execution. Each instrumentor's methods are side-effect-only
(they return the original object unchanged).

Dependencies:
- tracker (ExposureTracker)
- Standard library (hashlib, secrets, typing)

Security Relevance:
Instrumentors define when the exposure metric considers data "exposed".
If an instrumentor misses a transition, the exposure score will be
inaccurate (either over- or under-reporting).

Maintenance Notes:
- The instrumentors use placeholder byte sequences (e.g., b"microjit_plaintext")
  for data hashing. In a production system, the actual data bytes
  should be hashed for accurate deduplication.
- The MicroJIT instrumentor records all three events (appear, encrypt,
  disappear) in a single call; this may not reflect real timing.
"""

from __future__ import annotations
import hashlib  # noqa: F401 (this line binds a name used by an embedded template)
import secrets  # noqa: F401 (this line binds a name used by an embedded template)
from typing import Any

from .tracker import ExposureTracker


class MicroJITExposureInstrumentor:
    """
    Tracks plaintext exposure for MicroJIT-protected functions.

    Records appearance at JIT compilation, encryption, and
    disappearance after execution.
    """

    def __init__(self, tracker: ExposureTracker) -> None:
        self._tracker = tracker

    def instrument_microjit(self, ir_function: Any) -> Any:
        """
        Wrap a MicroJIT IR function with exposure tracking.

        Records plaintext appearance, encryption, and disappearance.
        Returns the function unchanged; tracking is side-effect only.
        """
        if ir_function is None:
            return None
        self._tracker.record_appearance("microjit", getattr(ir_function, "name", "unknown"), b"microjit_plaintext")
        self._tracker.record_encryption("microjit", getattr(ir_function, "name", "unknown"))
        self._tracker.record_disappearance("microjit", getattr(ir_function, "name", "unknown"), b"microjit_encrypted")
        return ir_function


class FragmentationExposureInstrumentor:
    """
    Tracks plaintext exposure for fragmentation-protected fragments.

    Each fragment is tracked individually (fragment_0, fragment_1, etc.)
    with separate appearance, encryption, and disappearance events.
    """

    def __init__(self, tracker: ExposureTracker) -> None:
        self._tracker = tracker

    def instrument_fragment(self, fragment: Any) -> Any:
        """
        Wrap a single fragment with exposure tracking.

        Records plaintext appearance, encryption, and disappearance
        for the given fragment ID. Returns the fragment unchanged.
        """
        if fragment is None:
            return None
        fid = str(getattr(fragment, "id", "unknown"))
        self._tracker.record_appearance("fragmentation", f"fragment_{fid}", b"fragment_plaintext")
        self._tracker.record_encryption("fragmentation", f"fragment_{fid}")
        self._tracker.record_disappearance("fragmentation", f"fragment_{fid}", b"fragment_encrypted")
        return fragment


class HistoryBoundExposureInstrumentor:
    """
    Tracks plaintext exposure for history-bound decryption.

    Decryption reveals plaintext; encryption hides it again.
    """

    def __init__(self, tracker: ExposureTracker) -> None:
        self._tracker = tracker

    def instrument_decryption(self, function_name: str) -> None:
        """
        Record history-bound decryption event.

        Decryption makes plaintext appear in memory.
        """
        self._tracker.record_decryption("history_bound", function_name)
        self._tracker.record_appearance("history_bound", function_name, b"history_decrypted_data")

    def instrument_encryption(self, function_name: str) -> None:
        """
        Record history-bound encryption event.

        Encryption makes plaintext disappear from memory.
        """
        self._tracker.record_disappearance("history_bound", function_name, b"history_decrypted_data")
        self._tracker.record_encryption("history_bound", function_name)


class FHEExposureInstrumentor:
    """
    Tracks plaintext exposure for FHE-protected computations.

    In FHE, input plaintext is encrypted once, computed on in
    ciphertext, and only decrypted at the output. Exposure events
    track the initial encryption and final decryption.
    """

    def __init__(self, tracker: ExposureTracker) -> None:
        self._tracker = tracker

    def instrument_encryption(self, function_name: str) -> None:
        self._tracker.record_appearance("fhe_vm", function_name, b"fhe_plaintext_input")
        self._tracker.record_encryption("fhe_vm", function_name)

    def instrument_decryption(self, function_name: str) -> None:
        self._tracker.record_decryption("fhe_vm", function_name)
        self._tracker.record_disappearance("fhe_vm", function_name, b"fhe_plaintext_output")
