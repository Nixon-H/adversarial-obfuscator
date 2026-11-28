#!/usr/bin/env python3
"""Exercise the real CLI entry points and their subcommands.

The generated inventory records every module that calls
``argparse.add_argument``; many of those are library helpers or
``*_parser()`` factories, not executables.  This verifier separates true
entry points (``__main__.py`` or a ``__main__`` guard plus
``parse_args``) from library helpers, runs ``--help`` for the entry point
and every subcommand discovered in source, and checks which declared
flags are actually advertised.

Statuses:
  OK            every invocation exited 0 and every declared flag appeared
                in the entry point or one of its subcommand help texts.
  FLAG_MISSING  invocation worked but some declared flag was never shown.
  FAIL          an invocation exited non-zero.
  TIMEOUT       an invocation exceeded its deadline.
  LIBRARY_ONLY  not an executable entry point (classified, not a failure).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
INVENTORY = OUT / "repository-inventory.json"
RESULT = OUT / "cli-help-results.json"
SUB_RE = re.compile(r"""add_parser\(\s*["']([^"']+)["']""")
CHOICE_RE = re.compile(r"\{([A-Za-z0-9_,\- ]{3,})\}")
PER_CALL_TIMEOUT = 60


def source_text(module: str) -> str:
    try:
        return (ROOT / module).read_text(encoding="utf-8")
    except OSError:
        return ""


def is_entrypoint(module: str, text: str) -> bool:
    if module.endswith("__main__.py"):
        return True
    guard = re.search(r"""if\s+__name__\s*==\s*["']__main__["']""", text)
    parse = "parse_args(" in text or "parse_known_args(" in text
    return bool(guard and parse)


def invocation(module: str, extra: list[str]) -> list[str] | None:
    path = Path(module)
    if path.suffix != ".py":
        return None
    parts = list(path.with_suffix("").parts)
    if parts[-1] == "__main__":
        parts = parts[:-1]
    if not parts:
        return None
    package = True
    for index in range(len(parts) - 1):
        parent = ROOT / Path(*parts[: index + 1])
        if not (parent / "__init__.py").exists():
            package = False
            break
    if package:
        return [sys.executable, "-m", ".".join(parts), *extra]
    return [sys.executable, module, *extra]


def run(command: list[str], env: dict[str, str]) -> tuple[int | None, str]:
    try:
        proc = subprocess.run(
            command, cwd=ROOT, env=env, capture_output=True, text=True,
            timeout=PER_CALL_TIMEOUT,
        )
        return proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired:
        return None, ""


def _positional_choice_groups(help_text: str):
    in_positional_section = False
    for line in help_text.splitlines():
        stripped = line.strip()
        heading = stripped.lower()
        if heading == "positional arguments:":
            in_positional_section = True
            continue
        if heading in {"options:", "optional arguments:"}:
            in_positional_section = False
            continue
        if in_positional_section and stripped.startswith("{"):
            match = CHOICE_RE.match(stripped)
            if match:
                yield match.group(1)


def discover_subcommands(text: str, help_text: str) -> list[str]:
    names = list(SUB_RE.findall(text))
    for group in _positional_choice_groups(help_text):
        names.extend(part.strip() for part in group.split(","))
    skip = {"true", "false", "none", "auto"}
    seen, ordered = set(), []
    for name in names:
        if name and name not in seen and name.lower() not in skip and " " not in name:
            seen.add(name)
            ordered.append(name)
    return ordered


def main() -> int:
    inventory = json.loads(INVENTORY.read_text())
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.setdefault("TMPDIR", "/tmp/opencode")
    results = []
    for entry in inventory["cli_commands"]:
        module = entry["module"]
        declared = [flag for flag in entry["flags"] if flag not in ("-h", "--help")]
        text = source_text(module)
        if not is_entrypoint(module, text):
            results.append({
                "module": module, "status": "LIBRARY_ONLY",
                "declared_flags": len(declared), "advertised_flags": 0,
                "commands": [], "missing_flags": [], "detail": "",
            })
            continue
        command = invocation(module, ["--help"])
        if command is None:
            continue
        rc, help_text = run(command, env)
        invocations = [{"args": command[1:], "returncode": rc}]
        if rc != 0:
            results.append({
                "module": module, "status": "TIMEOUT" if rc is None else "FAIL",
                "declared_flags": len(declared), "advertised_flags": 0,
                "commands": invocations, "missing_flags": declared,
                "detail": help_text[-1000:] if rc not in (0, None) else "",
            })
            continue
        merged = help_text
        for sub in discover_subcommands(text, help_text)[:25]:
            sub_command = invocation(module, [sub, "--help"])
            if not sub_command:
                continue
            sub_rc, sub_help = run(sub_command, env)
            invocations.append({"args": sub_command[1:], "returncode": sub_rc})
            merged += "\n" + sub_help
        failed_calls = [c for c in invocations if c["returncode"] != 0]
        missing = [flag for flag in declared if flag not in merged]
        advertised = len(declared) - len(missing)
        if failed_calls:
            status = "TIMEOUT" if any(c["returncode"] is None for c in failed_calls) else "FAIL"
        elif missing:
            status = "FLAG_MISSING"
        else:
            status = "OK"
        results.append({
            "module": module, "status": status,
            "declared_flags": len(declared), "advertised_flags": advertised,
            "commands": invocations, "missing_flags": missing,
            "detail": "" if status == "OK" else json.dumps(failed_calls)[:500],
        })
    RESULT.write_text(json.dumps(results, indent=2))
    entrypoints = [r for r in results if r["status"] != "LIBRARY_ONLY"]
    bad = [r for r in entrypoints if r["status"] != "OK"]
    print(f"argparse_modules={len(results)} entrypoints={len(entrypoints)} "
          f"library_only={len(results) - len(entrypoints)} ok={len(entrypoints) - len(bad)} "
          f"problems={len(bad)}")
    for row in bad:
        print(f"  {row['status']}: {row['module']} missing={row['missing_flags'][:10]}")
        if row["detail"]:
            print("   ", row["detail"].replace("\n", " ")[:300])
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
