"""Safety and scoring tests for the Kern-only read-only agent harness.

The benchmark itself is an external API run, so these tests do not call the
network.  They pin the properties that make its result interpretable: the
sandbox cannot escape, the tools are read-only, and a JSON answer buried in
prose is parsed without accepting a truncated object.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "benchmark"))

from kern_agent_bench import ReadOnlyWorkspace, ToolError, _extract_json


def test_extract_json_skips_prose_brace_and_fenced_block():
    text = 'Analysis {not json} done.\n```json\n{"names": ["alpha"], "purpose": "x"}\n```'
    assert _extract_json(text) == {"names": ["alpha"], "purpose": "x"}


def test_extract_json_does_not_accept_truncated_answer():
    assert _extract_json('{"names": ["alpha"], "purpose": "unterminated') is None


def test_workspace_rejects_path_escape(tmp_path: Path):
    workspace = ReadOnlyWorkspace(tmp_path)
    (tmp_path / "ok.txt").write_text("hello\n", encoding="utf-8")
    with pytest.raises(ToolError):
        workspace.read_file("../etc/passwd")
    with pytest.raises(ToolError):
        workspace.read_file("/etc/passwd")


def test_workspace_read_grep_and_ast_are_read_only(tmp_path: Path):
    target = tmp_path / "sample.py"
    target.write_text("def alpha():\n    return 'needle'\n", encoding="utf-8")
    workspace = ReadOnlyWorkspace(tmp_path, max_output=4000)
    assert "alpha" in workspace.read_file("/work/sample.py")
    assert "needle" in workspace.grep("NEEDLE", "/work/sample.py")
    summary = workspace.ast_summary("/work/sample.py")
    assert "FunctionDef:alpha" in summary
    before = target.read_text(encoding="utf-8")
    assert before == "def alpha():\n    return 'needle'\n"
    assert not hasattr(workspace, "write_file")
    assert not hasattr(workspace, "run_shell")


def test_workspace_output_is_capped(tmp_path: Path):
    target = tmp_path / "large.txt"
    target.write_text("x" * 50000, encoding="utf-8")
    workspace = ReadOnlyWorkspace(tmp_path, max_output=2000)
    assert len(workspace.read_file("/work/large.txt")) <= 2000
