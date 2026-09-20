"""Item 58: Environmental poly-engine.

Probes the execution environment and generates polymorphic decryption code
that only works in the correct environment. If environment check fails,
the decryption produces garbage.
"""

import base64
import hashlib
import os
import platform
import struct
import sys
from typing import Any, Dict, List, Optional


class PolyEngine:
    """Probes the execution environment and generates polymorphic decryption
    code that only works in the correct environment."""

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed or int.from_bytes(os.urandom(4), "big")

    def probe_python_version(self) -> str:
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def probe_os(self) -> str:
        return platform.system().lower()

    def probe_architecture(self) -> str:
        return platform.machine().lower()

    def probe_cpu_features(self) -> List[str]:
        features: List[str] = []
        cpuinfo_path = "/proc/cpuinfo"
        if os.path.exists(cpuinfo_path):
            try:
                with open(cpuinfo_path, "r") as f:
                    for line in f:
                        if line.startswith("flags"):
                            flags = line.split(":")[1].strip().split()
                            features.extend(flags)
                            break
                        elif line.startswith("Features"):
                            flags = line.split(":")[1].strip().split()
                            features.extend(flags)
                            break
            except (OSError, IndexError):
                pass
        if not features:
            arch = self.probe_architecture()
            if arch in ("amd64", "x86_64"):
                features = ["sse2", "aes_ni", "pclmulqdq"]
            elif "arm" in arch or "aarch" in arch:
                features = ["neon"]
        return sorted(set(features))

    def probe_environment_variables(self) -> Dict[str, str]:
        relevant_keys = ["PATH", "HOME", "USER", "SHELL", "TMPDIR", "LANG",
                         "LD_LIBRARY_PATH", "PYTHONPATH", "DISPLAY"]
        result = {}
        for key in relevant_keys:
            val = os.environ.get(key)
            if val is not None:
                short = val[:64]
                result[key] = short
        return result

    def probe_filesystem_layout(self) -> Dict[str, bool]:
        paths = ["/etc", "/usr", "/usr/local", "/lib", "/lib64",
                 "/proc", "/sys", "/tmp", "/var", "/bin", "/sbin"]
        result = {}
        for path in paths:
            result[path] = os.path.isdir(path)
        return result

    def probe_available_libraries(self) -> Dict[str, str]:
        modules = {}
        for name in ("cryptography", "numpy", "z3", "requests",
                      "llvmlite", "Cython", "psutil", "capstone",
                      "cv2", "PIL", "lxml", "yaml", "cffi"):
            try:
                mod = __import__(name)
                ver = getattr(mod, "__version__", "")
                modules[name] = ver
            except ImportError:
                modules[name] = ""
        return modules

    def get_environment_profile(self) -> Dict[str, Any]:
        return {
            "python": self.probe_python_version(),
            "os": self.probe_os(),
            "arch": self.probe_architecture(),
            "cpu_features": self.probe_cpu_features(),
            "env_vars": self.probe_environment_variables(),
            "fs_layout": self.probe_filesystem_layout(),
            "libraries": self.probe_available_libraries(),
            "fingerprint": self._compute_fingerprint(),
        }

    def _compute_fingerprint(self) -> str:
        parts = [
            self.probe_python_version(),
            self.probe_os(),
            self.probe_architecture(),
            str(sorted(self.probe_cpu_features())),
            str(self.seed),
        ]
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def generate_decrypt_code(self, encrypted_data: bytes,
                              key_material: bytes) -> str:
        """Generate polymorphic decryption code that checks environment."""
        profile = self.get_environment_profile()
        fp = profile["fingerprint"]
        expected_os = profile["os"]
        expected_python = profile["python"]
        expected_arch = profile["arch"]

        encrypted_b64 = base64.b64encode(encrypted_data).decode()
        key_repr = repr(key_material)

        guard_checks = []
        guard_checks.append(
            f'__env_ok = __env_ok and platform.system().lower() == \"{expected_os}\"'
        )
        guard_checks.append(
            f'__env_ok = __env_ok and platform.machine().lower() == \"{expected_arch}\"'
        )
        guard_checks.append(
            f'__env_ok = __env_ok and '
            f'sys.version_info[:2] == ({sys.version_info.major}, {sys.version_info.minor})'
        )

        guards_str = chr(10).join(guard_checks)

        code = f'''# poly-engine fingerprint={fp}
import hashlib, hmac, platform, struct, sys, os
import base64

__env_ok = True
{guards_str}

__key = {key_repr}
__ct = \"{encrypted_b64}\"

if __env_ok:
    __d = base64.b64decode(__ct)
    __k = hashlib.sha256(__key + b\"{fp}\").digest()
    __pt = bytes(__d[i] ^ __k[i % len(__k)] for i in range(len(__d)))
else:
    __d = base64.b64decode(__ct)
    __pt = os.urandom(len(__d))

def __poly_decrypt() -> bytes:
    return __pt

__result = __poly_decrypt()
'''
        return code

    def encrypt_for_environment(self, plaintext: bytes) -> Dict[str, Any]:
        """Encrypt data such that only correct environment can decrypt."""
        profile = self.get_environment_profile()
        fp = profile["fingerprint"]
        key = hashlib.sha256(
            str(self.seed).encode() + fp.encode()
        ).digest()
        iv = os.urandom(16)
        keystream = b""
        counter = 0
        while len(keystream) < len(plaintext):
            block = struct.pack(">Q", counter)
            keystream += hashlib.sha256(key + iv + block).digest()
            counter += 1
        keystream = keystream[:len(plaintext)]
        ciphertext = bytes(p ^ k for p, k in zip(plaintext, keystream))
        decrypt_code = self.generate_decrypt_code(
            ciphertext, key + iv
        )
        return {
            "ciphertext": ciphertext,
            "iv": iv,
            "fingerprint": fp,
            "decrypt_code": decrypt_code,
            "profile": profile,
        }

    def verify_environment(self, profile: Optional[Dict[str, Any]] = None) -> bool:
        if profile is None:
            profile = self.get_environment_profile()
        expected_fp = self._compute_fingerprint()
        return profile.get("fingerprint") == expected_fp
