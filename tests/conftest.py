import os
import tempfile
import pytest


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
