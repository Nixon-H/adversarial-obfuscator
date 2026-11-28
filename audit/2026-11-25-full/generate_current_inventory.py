#!/usr/bin/env python3
"""Generate a current-tree file/symbol/CLI/import inventory for the full audit."""
from __future__ import annotations

import ast
import csv
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE_SUFFIXES = {
    ".py", ".rs", ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".s", ".asm",
    ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".sh", ".md", ".txt",
}
GENERATED_PARTS = {
    "build", "archive", "target", "ci-artifacts", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".mimosa", "__pycache__", ".git",
    # Untracked benchmark/scratch campaign written concurrently with this
    # audit (444 MB, zero tracked files).  It is not product source.
    "re-bench",
}
NATIVE_NON_FUNCTION_TOKENS = {
    "if", "for", "while", "switch", "catch", "defined", "__attribute__", "__declspec",
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def walk_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        for filename in filenames:
            yield Path(dirpath) / filename


def qualified(stack: list[str], name: str) -> str:
    return ".".join(stack + [name])


def python_symbols(path: Path, text: str):
    tree = ast.parse(text, filename=rel(path))
    symbols = []
    flags = []
    imports = []

    def visit_body(body, stack):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                name = node.name
                symbols.append({
                    "module": rel(path), "kind": kind, "name": name,
                    "qualified": qualified(stack, name), "line": node.lineno,
                    "exported": not name.startswith("_") or name.startswith("__"),
                    "language": "python",
                })
                visit_body(node.body, stack + [name])
            else:
                for child in ast.iter_child_nodes(node):
                    visit_body([child], stack)

    visit_body(tree.body, [])
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "add_argument":
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                        and arg.value.startswith("-"):
                    flags.append(arg.value)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    return symbols, sorted(set(flags)), sorted(set(x for x in imports if x))


def native_symbols(path: Path, text: str):
    found = []
    suffix = path.suffix.lower()
    patterns = []
    if suffix == ".rs":
        patterns = [
            r"\bpub(?:\([^)]*\))?\s+(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\bpub(?:\([^)]*\))?\s+(?:struct|enum|trait|type)\s+([A-Za-z_][A-Za-z0-9_]*)",
        ]
    elif suffix in {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp"}:
        patterns = [r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\([^;{}()]*\)\s*\{"]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.M):
            name = match.group(1)
            if name in NATIVE_NON_FUNCTION_TOKENS:
                continue
            found.append({
                "module": rel(path), "name": name,
                "line": text.count("\n", 0, match.start()) + 1,
                "language": suffix,
            })
    return found


def main():
    files = []
    symbols = []
    native = []
    cli = []
    edges = []
    markers = []
    parse_errors = []
    for path in sorted(walk_files(), key=lambda p: rel(p)):
        name = rel(path)
        try:
            size = path.stat().st_size
        except OSError:
            continue
        parts = path.relative_to(ROOT).parts
        generated = any(part in GENERATED_PARTS for part in parts) or \
            name.startswith("docs/research/")
        source = path.suffix.lower() in SOURCE_SUFFIXES and not generated
        files.append({"path": name, "suffix": path.suffix.lower(), "bytes": size,
                      "generated_area": generated, "source": source})
        if generated:
            continue
        if path.suffix.lower() not in {".py", ".rs", ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            parse_errors.append({"path": name, "error": str(exc)})
            continue
        if path.suffix.lower() == ".py":
            try:
                module_symbols, flags, imports = python_symbols(path, text)
            except (SyntaxError, ValueError) as exc:
                parse_errors.append({"path": name, "error": str(exc)})
                continue
            symbols.extend(module_symbols)
            if flags:
                cli.append({"module": name, "flags": flags})
            edges.extend({"source": name, "target": target} for target in imports)
        else:
            native.extend(native_symbols(path, text))
        for line_no, line in enumerate(text.splitlines(), 1):
            if re.search(r"\b(TODO|FIXME|XXX|NotImplementedError)\b", line):
                markers.append({"path": name, "line": line_no, "text": line.strip()[:300]})

    inventory = {
        "generated": "2026-11-25-full",
        "root": str(ROOT),
        "file_count": len(files),
        "source_file_count": sum(1 for f in files if f["source"]),
        "python_file_count": sum(1 for f in files if f["suffix"] == ".py"),
        "files": files,
        "symbols": symbols,
        "native_symbols": native,
        "cli_commands": cli,
        "cli_flags_total": sum(len(entry["flags"]) for entry in cli),
        "import_edges": edges,
        "markers": markers,
        "parse_errors": parse_errors,
    }
    (OUT / "repository-inventory.json").write_text(json.dumps(inventory, indent=2))

    fields = ["id", "category", "module", "symbol", "kind", "status", "evidence", "limitation"]
    rows = []
    counter = 0

    def add(category, module, symbol, kind, status="STATICALLY CHECKED",
            evidence="Current-tree source inventory", limitation="Independent functional execution not established"):
        nonlocal counter
        counter += 1
        rows.append({"id": f"A{counter:06d}", "category": category, "module": module,
                     "symbol": symbol, "kind": kind, "status": status,
                     "evidence": evidence, "limitation": limitation})

    for entry in files:
        add("FILE", entry["path"], "<file>", "file",
            limitation="Generated/archive evidence" if entry["generated_area"] else
            "Independent functional execution not established")
    for entry in symbols:
        add("SYMBOL", entry["module"], entry["qualified"], entry["kind"])
    for entry in native:
        add("NATIVE_SYMBOL", entry["module"], entry["name"], entry["language"])
    features = [
        ("vm/__main__.py", "compile/mutate/run encrypted VM pipeline"),
        ("irgen/", "Python-to-IR and transformation pipeline"),
        ("llvmgen/", "LLVM lowering/codegen/pass pipeline"),
        ("encrypt/", "container and native binary encryption"),
        ("obfuscator/core/pipeline.py", "Python/native build and loader pipeline"),
        ("runtime/", "Rust JIT/decryption/integrity/TEE runtime"),
        ("relay/", "Rust remote relay and attestation"),
        ("native/", "C/C++ white-box, SIMD VM, FFI and payload contract"),
        ("scripts/build.py", "native/build CLI"),
        (".github/workflows/", "CI/build/security/release workflows"),
        ("Dockerfile", "container build and test image"),
    ]
    for module, name in features:
        add("FEATURE", module, name, "feature")
    with (OUT / "function-feature-matrix.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({
        "files": len(files), "source_files": inventory["source_file_count"],
        "python_symbols": len(symbols), "native_symbols": len(native),
        "cli_modules": len(cli), "cli_flags": inventory["cli_flags_total"],
        "import_edges": len(edges), "markers": len(markers),
        "parse_errors": parse_errors, "matrix_rows": len(rows),
    }, indent=2))


if __name__ == "__main__":
    main()
