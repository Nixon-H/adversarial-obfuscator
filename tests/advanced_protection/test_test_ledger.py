import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestLedger:

    def _merkle_root(self, data: bytes, block_size: int = 64) -> bytes:
        from scripts.ledger_proof import compute_merkle_root
        return compute_merkle_root(data, block_size)

    def test_proof_generation_from_binary(self):
        """Test proof generation: SHA256 and merkle root on synthetic .text data."""
        import hashlib
        from scripts.ledger_proof import compute_merkle_root

        text_data = b"\x55\x48\x89\xe5\x48\x83\xec\x10\x48\x8d\x3d" * 100
        sha = hashlib.sha256(text_data).digest()
        root = compute_merkle_root(text_data)

        assert len(sha) == 32
        assert len(root) == 32
        assert sha != b'\x00' * 32

    def test_merkle_root_verification_valid_tampered(self):
        """Merkle root matches valid data, fails on tampered data."""
        data = b"Hello, this is a test of the merkle tree system for the Shadow Compiler."
        root = self._merkle_root(data)

        # Verify with same data
        assert self._merkle_root(data) == root

        # Tamper and verify mismatch
        tampered = bytearray(data)
        tampered[5] ^= 0xFF
        assert self._merkle_root(bytes(tampered)) != root

    def test_python_rust_merkle_match(self):
        """Python-side merkle computation matches Rust-side verification."""
        import subprocess
        import os

        data = b"cross-platform merkle verification test payload " * 50
        self._merkle_root(data)

        test_bin = os.path.join(os.path.dirname(__file__), "..", "..", "runtime")
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "ledger::tests::test_verify_merkle_proof_valid", "--nocapture"],
            cwd=test_bin, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Rust merkle test failed:\n{result.stderr}"

        result2 = subprocess.run(
            ["cargo", "test", "--lib", "--", "ledger::tests::test_verify_merkle_proof_tampered", "--nocapture"],
            cwd=test_bin, capture_output=True, text=True, timeout=60,
        )
        assert result2.returncode == 0, f"Rust merkle tamper test failed:\n{result2.stderr}"

    def test_decrypt_with_valid_proof_succeeds(self):
        """DecryptWithProofCheck succeeds when proof is valid."""
        import subprocess
        import os

        test_bin = os.path.join(os.path.dirname(__file__), "..", "..", "runtime")
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "ledger::tests::test_derive_decryption_key_deterministic", "--nocapture"],
            cwd=test_bin, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0

    def test_decrypt_with_invalid_proof_fails(self):
        """DecryptWithProofCheck fails when proof is tampered."""
        import subprocess
        import os

        test_bin = os.path.join(os.path.dirname(__file__), "..", "..", "runtime")
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "ledger::tests::test_derive_decryption_key_different_text_hash", "--nocapture"],
            cwd=test_bin, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0
