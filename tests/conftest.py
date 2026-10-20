import os

# Force the console log path for the test session.  ``setdefault`` would
# let an exported NIXON_LOG_REDIRECT=1 hijack pytest's own stdout (the
# redirect is installed at import time of obfuscator/core/utils.py and
# truncates ./build.log), which silently swallows the test report.
os.environ["NIXON_LOG_REDIRECT"] = "0"

import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def test_script():
    """Return path to a temporary test .py file."""
    fd, path = tempfile.mkstemp(suffix=".py", prefix="nixon_test_", text=True)
    os.close(fd)
    with open(path, "w") as f:
        f.write("def main():\n    return 42\n")
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def build_dir():
    """Return the path to the build/ directory."""
    bd = os.path.join(os.path.dirname(__file__), "..", "build")
    if not os.path.isdir(bd):
        pytest.skip(f"build directory not found at {bd}")
    return os.path.abspath(bd)


@pytest.fixture(autouse=True)
def reset_ir_counter():
    from irgen.compile import IrValue
    IrValue.reset_counter()


@pytest.fixture
def ir_module():
    from irgen.compile import IrModule, IrFunction, IrType
    mod = IrModule("test_mod")
    func = IrFunction("test_func", IrType.i32())
    func.new_block('entry')
    mod.functions.append(func)
    return mod


@pytest.fixture
def ir_func():
    from irgen.compile import IrFunction, IrType
    func = IrFunction("test_func", IrType.i32())
    func.new_block("entry")
    return func
