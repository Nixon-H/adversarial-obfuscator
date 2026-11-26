#!/usr/bin/env python3
"""Compile-time regressions for payload.h self-containment.

Run with:

    python3 native/test_payload_header.py

A C++17 compiler is required; the test is skipped when none is available.
"""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
NATIVE = ROOT / "native"
GENERATOR = ROOT / "scripts" / "generate_payload_h.py"
REQUIRED_INCLUDES = ("<cstddef>", "<cstdint>", "<cstdlib>", "<new>", "<vector>")


def _compiler():
    return shutil.which("c++") or shutil.which("g++")


def _compile_header(header, extra_args=()):
    compiler = _compiler()
    source = (
        f'#include "{header}"\n'
        "int main() {\n"
        "    SecureVector<std::uint8_t> values;\n"
        "    values.reserve(1);\n"
        "    values.push_back(static_cast<std::uint8_t>(NIXON_OBF_KEY));\n"
        "    return values.size() == 1 && NIXON_PAYLOAD_LEN > 0 ? 0 : 1;\n"
        "}\n"
    )
    return subprocess.run(
        [
            compiler,
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-fsyntax-only",
            "-x",
            "c++",
            *extra_args,
            "-",
        ],
        input=source,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
        cwd=ROOT,
    )


@unittest.skipUnless(_compiler(), "a C++ compiler is required")
class PayloadHeaderRegression(unittest.TestCase):
    def test_existing_generated_header_is_self_contained(self):
        header = NATIVE / "payload.h"
        if not header.is_file():
            self.skipTest("generated native/payload.h is not present")
        text = header.read_text(encoding="utf-8")
        for include in REQUIRED_INCLUDES:
            self.assertTrue(f"#include {include}" in text, f"missing #include {include}")
        result = _compile_header(header)
        self.assertEqual(
            result.returncode,
            0,
            msg=f"payload.h did not compile standalone:\n{result.stderr}",
        )

    def test_generator_emits_self_contained_header(self):
        with tempfile.TemporaryDirectory(prefix="ao-payload-", dir="/tmp/opencode") as tmp:
            tmp_path = Path(tmp)
            payload = tmp_path / "payload.py"
            output = tmp_path / "payload.h"
            payload.write_text("print('payload header regression')\n", encoding="utf-8")
            generated = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--obfuscated-py",
                    str(payload),
                    "--output",
                    str(output),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
                check=False,
                cwd=ROOT,
            )
            self.assertEqual(
                generated.returncode,
                0,
                msg=f"generator failed:\n{generated.stdout}\n{generated.stderr}",
            )
            text = output.read_text(encoding="utf-8")
            for include in REQUIRED_INCLUDES:
                self.assertIn(f"#include {include}", text)
            self.assertTrue(
                "#ifdef _WIN32\n#include <windows.h>\n#endif" in text,
                "missing conditional windows.h include",
            )
            result = _compile_header(output)
            self.assertEqual(
                result.returncode,
                0,
                msg=f"generated payload.h did not compile standalone:\n{result.stderr}",
            )

    def test_generator_windows_allocator_include_is_self_contained(self):
        with tempfile.TemporaryDirectory(prefix="ao-payload-win-", dir="/tmp/opencode") as tmp:
            tmp_path = Path(tmp)
            payload = tmp_path / "payload.py"
            output = tmp_path / "payload.h"
            include_dir = tmp_path / "include"
            include_dir.mkdir()
            payload.write_text("print('windows header regression')\n", encoding="utf-8")
            (include_dir / "windows.h").write_text(
                "#pragma once\n"
                "#include <cstddef>\n"
                "#define MEM_COMMIT 0x1000UL\n"
                "#define MEM_RESERVE 0x2000UL\n"
                "#define MEM_RELEASE 0x8000UL\n"
                "#define PAGE_READWRITE 0x04UL\n"
                'extern "C" void* VirtualAlloc(void*, std::size_t, unsigned long, unsigned long);\n'
                'extern "C" int VirtualFree(void*, std::size_t, unsigned long);\n',
                encoding="utf-8",
            )
            generated = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--obfuscated-py",
                    str(payload),
                    "--output",
                    str(output),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
                check=False,
                cwd=ROOT,
            )
            self.assertEqual(
                generated.returncode,
                0,
                msg=f"generator failed:\n{generated.stdout}\n{generated.stderr}",
            )
            result = _compile_header(output, ("-D_WIN32", "-I", str(include_dir)))
            self.assertEqual(
                result.returncode,
                0,
                msg=f"generated Windows payload.h did not compile standalone:\n{result.stderr}",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
