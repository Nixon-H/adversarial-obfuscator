"""Live build/verification subprocesses must have explicit deadlines."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE_FILES = [
    ROOT / "scripts" / "build.py",
    ROOT / "obfuscator" / "core" / "pipeline.py",
    ROOT / "obfuscator" / "remote_exec.py",
]


def test_direct_subprocess_run_calls_have_timeouts():
    missing = []
    for path in LIVE_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "run"
                    and isinstance(func.value, ast.Attribute)
                    and func.value.attr == "subprocess"):
                continue
            if not any(kw.arg == "timeout" for kw in node.keywords):
                missing.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not missing, "unbounded subprocess.run calls: " + ", ".join(missing)
