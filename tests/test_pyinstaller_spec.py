"""Batch-2: PyInstaller .spec generation."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.pyinstaller_spec import collect_hidden_imports, generate_spec


def test_stdlib_filtered():
    src = "import os\nimport sys\nimport json\nx = 1\n"
    assert collect_hidden_imports(src) == []


def test_third_party_kept():
    src = "import os\nimport requests\nimport numpy as np\nfrom Crypto.Cipher import AES\n"
    got = collect_hidden_imports(src)
    assert "requests" in got
    assert "numpy" in got
    assert "Crypto" in got
    assert "os" not in got


def test_from_import_top_level_only():
    src = "from mypkg.sub import thing\n"
    assert collect_hidden_imports(src) == ["mypkg"]


def test_relative_imports_skipped():
    src = "from .local import helper\nfrom .. import other\n"
    assert collect_hidden_imports(src) == []


def test_spec_text_contains_hiddenimports_and_entry():
    text = generate_spec("demo", "demo_obfuscated.py", ["requests", "Crypto"])
    assert "hiddenimports" in text
    assert "requests" in text
    assert "demo_obfuscated.py" in text
    assert "EXE" in text
    assert "Analysis" in text
    compile(text, "<spec>", "exec")


def test_cli_flag_exists():
    r = subprocess.run(
        [sys.executable, "scripts/build.py", "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    assert "--pyinstaller-spec" in (r.stdout + r.stderr)


def test_build_with_flag_writes_spec(tmp_path):
    """Simulate the build.py spec-writing block on a tiny payload."""
    payload = tmp_path / "app.py"
    payload.write_text("import requests\nprint(requests.get)\n", encoding="utf-8")
    code = payload.read_text(encoding="utf-8")
    his = collect_hidden_imports(code)
    text = generate_spec("app", str(payload), his)
    spec_path = tmp_path / "app.spec"
    spec_path.write_text(text, encoding="utf-8")
    assert spec_path.is_file()
    assert "requests" in spec_path.read_text(encoding="utf-8")
