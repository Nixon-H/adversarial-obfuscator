import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestORAM:

    def test_oram_controller_creates_and_initializes(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "oram::tests::test_new_controller_initializes", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"oram init test failed:\n{result.stderr}"

    def test_oram_read_write_roundtrip(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "oram::tests::test_read_write_roundtrip", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"oram roundtrip test failed:\n{result.stderr}"

    def test_oram_different_blocks_different_leaves(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "oram::tests::test_different_blocks_map_to_different_leaves", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"oram leaf test failed:\n{result.stderr}"

    def test_oram_stress_100_random_ops(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "oram::tests::test_stress_random_ops", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"oram stress test failed:\n{result.stderr}"

    def test_oram_all_paths_same_length(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "oram::tests::test_all_paths_same_length", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"oram path-length test failed:\n{result.stderr}"

    def test_oram_python_annotation(self):
        from irgen.oram import annotate_oram_variables, detect_oram_annotations
        source = """x = 42
y = x + 1
z = y * 2
"""
        annotated = annotate_oram_variables(source, ["x", "z"])
        assert "# oram: x" in annotated
        assert "# oram: z" in annotated
        assert "# oram: y" not in annotated
        detected = detect_oram_annotations(annotated)
        assert "x" in detected
        assert "z" in detected
        assert "y" not in detected

    def test_oram_python_config_generation(self):
        from irgen.oram import generate_oram_config
        config = generate_oram_config(["secret", "key", "token"], 256)
        assert config["enabled"] is True
        assert config["num_blocks"] == 256
        assert config["tree_height"] == 8
        assert config["block_size"] == 64
        assert "secret" in config["leaf_mapping"]
        assert "key" in config["leaf_mapping"]
        assert "token" in config["leaf_mapping"]
        assert len(config["variables"]) == 3
