"""
Tests for unified evaluation report (Phase 4).
"""
import json  # noqa: F401 (this line binds a name used by an embedded template)
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evaluation.unified_report import generate_evaluation_report
from scripts.evaluation.runtime_overhead import measure_runtime_overhead
from scripts.evaluation.binary_size import measure_binary_size, measure_size_overhead


SAMPLE_OBFUSCATED = """
import sys
def _0xa1b2c3d4(x):
    if __debug__:
        return 0
    _0xe5f6a7b8 = 0
    for _0xc9d0e1f2 in range(x):
        _0xe5f6a7b8 += _0xc9d0e1f2
    return _0xe5f6a7b8

if __name__ == "__main__":
    print(_0xa1b2c3d4(10))
"""


class TestRuntimeOverhead:
    """
    TestRuntimeOverhead
    
    Positive test cases for runtimeoverhead.
    """
    def test_measure_execution_time(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(SAMPLE_OBFUSCATED)
            f.flush()
            try:
                result = measure_runtime_overhead(f.name, f.name, iterations=2)
                assert result["overhead_ratio"] > 0
                assert "mean" in result["unprotected"]
                assert "mean" in result["protected"]
            finally:
                os.unlink(f.name)


class TestBinarySize:
    """
    TestBinarySize
    
    Positive test cases for binarysize.
    """
    def test_measure_size(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(SAMPLE_OBFUSCATED)
            f.flush()
            try:
                result = measure_binary_size(f.name)
                assert result["bytes"] > 0
                assert result["exists"]
            finally:
                os.unlink(f.name)

    def test_size_overhead(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f1:
            f1.write(SAMPLE_OBFUSCATED)
            f1.flush()
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f2:
                f2.write(SAMPLE_OBFUSCATED * 2)
                f2.flush()
                try:
                    result = measure_size_overhead(f1.name, f2.name)
                    assert result["overhead_ratio"] > 1.0
                    assert result["unprotected"]["bytes"] > 0
                    assert result["protected"]["bytes"] > result["unprotected"]["bytes"]
                finally:
                    os.unlink(f1.name)
                    os.unlink(f2.name)


class TestUnifiedReport:
    """
    TestUnifiedReport
    
    Positive test cases for unifiedreport.
    """
    def test_generate_report(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(SAMPLE_OBFUSCATED)
            f.flush()
            out_path = os.path.join(tempfile.gettempdir(), "test_eval_report.json")
            try:
                report = generate_evaluation_report(
                    obfuscated_source_path=f.name,
                    original_source_path=f.name,
                    output_path=out_path,
                )
                assert isinstance(report, dict)
                assert "metrics" in report
                assert "summary" in report
                assert report["summary"]["total_metrics"] == 9
            finally:
                os.unlink(f.name)
                if os.path.exists(out_path):
                    os.unlink(out_path)
