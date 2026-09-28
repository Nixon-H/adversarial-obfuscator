"""Item 58: Environmental poly-engine.

Detects execution environment characteristics (OS, Python version, installed
modules, CPU features) and generates environment-specific code variants that
adapt to the detected platform.

TWIN: scripts/poly/poly_engine.py (PolyEngine) — that module emits
polymorphic decryptors bound to the environment; this module fingerprints
the platform to pick code variants. Different output; do not merge.
"""

import hashlib
import os
import platform
import struct
import sys
from typing import Any, Dict, List, Optional, Tuple


class EnvironmentalPolyEngine:
    """Detects environment characteristics and generates code variants
    adapted to the specific platform and runtime."""

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed or int.from_bytes(os.urandom(4), "big")
        self._env_fingerprint: Optional[str] = None
        self._variants: Dict[str, str] = {}

    def detect_os(self) -> str:
        return platform.system().lower()

    def detect_python_version(self) -> str:
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def detect_architecture(self) -> str:
        return platform.machine().lower()

    def detect_hardware_features(self) -> List[str]:
        features = []
        proc = platform.processor()
        if proc:
            features.append(proc.lower().replace(" ", "_"))
        if platform.machine().lower() in ("amd64", "x86_64"):
            features.extend(["sse2", "aes_ni"])
        elif platform.machine().lower().startswith("arm"):
            features.append("neon")
        elif platform.machine().lower().startswith("aarch"):
            features.append("neon")
            features.append("crc32")
        return features

    def detect_installed_modules(self) -> Dict[str, str]:
        modules = {}
        for name in ("cryptography", "numpy", "z3", "requests",
                      "llvmlite", "Cython", "psutil", "capstone"):
            try:
                mod = __import__(name)
                ver = getattr(mod, "__version__", "")
                modules[name] = ver
            except ImportError:
                modules[name] = ""
        return modules

    def get_environment_fingerprint(self) -> str:
        if self._env_fingerprint is not None:
            return self._env_fingerprint
        parts = [
            self.detect_os(),
            self.detect_python_version(),
            self.detect_architecture(),
            str(self.seed),
        ]
        parts.extend(sorted(self.detect_hardware_features()))
        raw = "|".join(parts)
        self._env_fingerprint = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return self._env_fingerprint

    def get_environment_profile(self) -> Dict[str, Any]:
        return {
            "os": self.detect_os(),
            "python": self.detect_python_version(),
            "arch": self.detect_architecture(),
            "hardware_features": self.detect_hardware_features(),
            "installed_modules": self.detect_installed_modules(),
            "fingerprint": self.get_environment_fingerprint(),
            "platform_details": platform.platform(),
            "node": platform.node(),
            "processor": platform.processor(),
        }

    def _os_specific_mba(self, value: int, os_name: str) -> int:
        if os_name == "linux":
            return (value * 7 + 11) ^ 0xA5A5A5A5
        elif os_name == "windows":
            return (value * 3 + 5) ^ 0x5A5A5A5A
        elif os_name == "darwin":
            return (value * 13 + 17) ^ 0x3C3C3C3C
        return (value * 5 + 3) ^ 0xF0F0F0F0

    def generate_poly_variant(self, name: str, code: str) -> str:
        """Generate an environment-adapted variant of the given code."""
        profile = self.get_environment_profile()
        os_name = profile["os"]
        arch = profile["arch"]
        features = profile["hardware_features"]
        fingerprint = profile["fingerprint"]

        feature_guards = []
        for feat in features:
            guard = f"__env_has_{feat} = True"
            feature_guards.append(guard)

        variant = f"# env=fingerprint:{fingerprint} os:{os_name} arch:{arch}\n"
        variant += f"# seed={self.seed}\n"
        if feature_guards:
            variant += "# " + " ".join(feature_guards) + "\n"

        variant += code + "\n"
        self._variants[name] = variant
        return variant

    def adapt_value_to_environment(self, value: int) -> Tuple[int, str]:
        """Apply environment-specific MBA to a value, returning (adapted, explanation)."""
        profile = self.get_environment_profile()
        os_name = profile["os"]
        adapted = self._os_specific_mba(value, os_name)
        adapted = (adapted ^ hash(profile["fingerprint"])) & 0xFFFFFFFF
        explanation = f"os={os_name} fingerprint={profile['fingerprint']}"
        return adapted, explanation

    def get_variant(self, name: str) -> Optional[str]:
        return self._variants.get(name)

    def get_all_variants(self) -> Dict[str, str]:
        return dict(self._variants)
