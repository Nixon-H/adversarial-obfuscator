"""Focused regressions for the core transforms/utils audit (shard A3).

These tests build no artifacts. Each one compiles or executes a small source
fragment that demonstrated the original semantic defect.
"""

import ast
import email.utils
import os
import subprocess
import sys
import tarfile
import time

import pytest

from obfuscator.core.transforms import (
    ASTMutator,
    BogusExceptionHandler,
    BuiltinAliaser,
    CallGraphObfuscator,
    ConstantUnfolder,
    ControlFlowFlattener,
    DynamicCodeGenerator,
    ExtendedArgBreaker,
    FStringLowering,
    OpaquePredicateInjector,
    SymbolRenamer,
    TemporalRedundancyWrapper,
    TypeHintStripper,
    UnicodeIdentifierEncoder,
    VariableSplitter,
    is_pure_function,
)
from obfuscator.core import utils as core_utils


def _transformed(transformer, source):
    tree = transformer.visit(ast.parse(source))
    ast.fix_missing_locations(tree)
    return tree, ast.unparse(tree)


def _exec_ok(tree_or_source):
    if isinstance(tree_or_source, ast.AST):
        code = compile(tree_or_source, "<audit-a3>", "exec")
    else:
        code = compile(tree_or_source, "<audit-a3>", "exec")
    ns = {}
    exec(code, ns)
    return ns


def test_type_hint_stripper_preserves_valued_dataclass_fields():
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass\n"
        "class C:\n"
        "    x: int = 1\n"
        "    y: int = 2\n"
        "assert C(3, 4).x == 3\n"
        "assert C(3, 4).y == 4\n"
    )
    tree, _ = _transformed(TypeHintStripper(), src)
    _exec_ok(tree)


def test_fstring_lowering_uses_empty_format_spec_not_str():
    src = (
        "class X:\n"
        "    def __str__(self): return 'str'\n"
        "    def __format__(self, spec): return 'fmt:' + spec\n"
        "assert f'{X()}' == 'fmt:'\n"
    )
    tree, _ = _transformed(FStringLowering(), src)
    assert any(isinstance(n, ast.JoinedStr) for n in ast.walk(tree))
    _exec_ok(tree)


def test_fstring_lowering_does_not_resolve_shadowed_format_name():
    src = (
        "format = lambda value, spec: 'shadowed'\n"
        "assert f'{1}' == '1'\n"
    )
    tree, _ = _transformed(FStringLowering(), src)
    _exec_ok(tree)


def test_symbol_renamer_reserves_import_used_by_earlier_function():
    src = (
        "def f():\n"
        "    return hexversion\n"
        "from sys import hexversion\n"
        "assert f() == hexversion\n"
    )
    tree, _ = _transformed(SymbolRenamer(), src)
    _exec_ok(tree)


def test_symbol_renamer_nonlocal_builtin_shadow_stays_bound():
    src = (
        "def outer():\n"
        "    copyright = 1\n"
        "    def inner():\n"
        "        nonlocal copyright\n"
        "        copyright += 1\n"
        "        return copyright\n"
        "    assert inner() == 2\n"
        "outer()\n"
    )
    tree, _ = _transformed(SymbolRenamer(), src)
    _exec_ok(tree)


def test_symbol_renamer_global_builtin_shadow_follows_module_binding():
    src = (
        "copyright = 1\n"
        "def bump():\n"
        "    global copyright\n"
        "    copyright += 1\n"
        "bump()\n"
        "assert copyright == 2\n"
    )
    tree, _ = _transformed(SymbolRenamer(), src)
    _exec_ok(tree)


def test_symbol_renamer_global_builtin_read_without_module_binding():
    src = (
        "def f():\n"
        "    global copyright\n"
        "    return type(copyright).__name__\n"
        "assert f() == type(copyright).__name__\n"
    )
    tree, _ = _transformed(SymbolRenamer(), src)
    _exec_ok(tree)


def test_unicode_encoder_reserves_import_used_by_earlier_function():
    src = (
        "def f():\n"
        "    return hexversion\n"
        "from sys import hexversion\n"
        "assert f() == hexversion\n"
    )
    tree, _ = _transformed(UnicodeIdentifierEncoder(), src)
    _exec_ok(tree)


def test_unicode_encoder_except_target_colliding_with_parameter():
    src = (
        "def f(x):\n"
        "    try:\n"
        "        raise ValueError('bad')\n"
        "    except ValueError as x:\n"
        "        return str(x)\n"
        "assert f('param') == 'bad'\n"
    )
    tree, _ = _transformed(UnicodeIdentifierEncoder(), src)
    _exec_ok(tree)


def test_unicode_encoder_nested_match_capture_survives_parameter_collision():
    src = (
        "def f(y, val):\n"
        "    match val:\n"
        "        case [x] as y:\n"
        "            return x\n"
        "    return None\n"
        "assert f([], [42]) == 42\n"
    )
    tree, _ = _transformed(UnicodeIdentifierEncoder(), src)
    _exec_ok(tree)


def test_opaque_predicates_do_not_resolve_shadowable_pow():
    injector = OpaquePredicateInjector()

    def bad_pow(*args, **kwargs):
        raise RuntimeError("shadowed pow must not be used")

    for make_predicate in injector.predicates:
        expr = ast.fix_missing_locations(ast.Expression(make_predicate()))
        assert eval(compile(expr, "<predicate>", "eval"), {"pow": bad_pow}) is True


def test_constant_unfolder_leaves_match_literal_patterns_alone(monkeypatch):
    monkeypatch.setattr("obfuscator.core.transforms.random.random", lambda: 0.0)
    src = (
        "def f(x):\n"
        "    match x:\n"
        "        case 2:\n"
        "            return 1\n"
        "    return 0\n"
        "assert f(2) == 1\n"
    )
    tree, out = _transformed(ConstantUnfolder(), src)
    assert "case 2" in out
    _exec_ok(tree)


def test_constant_unfolder_sum_form_does_not_resolve_shadowable_sum(monkeypatch):
    monkeypatch.setattr("obfuscator.core.transforms.random.random", lambda: 0.0)
    monkeypatch.setattr("obfuscator.core.transforms.random.choice", lambda seq: "sum")
    tree, out = _transformed(ConstantUnfolder(), "x = 5\nassert x == 5\n")
    assert "sum(" not in out
    ns = {"sum": lambda values: 999}
    exec(compile(tree, "<audit-a3>", "exec"), ns)


def test_control_flow_flattener_emits_compilable_list_ast_and_preserves_order():
    src = (
        "def f(x):\n"
        "    a = 1\n"
        "    if x:\n"
        "        a = 2\n"
        "    b = 3\n"
        "    return a + b\n"
        "assert f(False) == 4\n"
        "assert f(True) == 5\n"
    )
    tree, out = _transformed(ControlFlowFlattener(), src)
    assert "_nx_cfi_lut" in out
    _exec_ok(tree)


def test_control_flow_flattener_skips_dispatcher_name_collision():
    src = (
        "_nx_state = 99\n"
        "def f(x):\n"
        "    a = _nx_state\n"
        "    if x:\n"
        "        a += 1\n"
        "    b = 3\n"
        "    return a + b\n"
        "assert f(False) == 102\n"
        "assert f(True) == 103\n"
    )
    tree, out = _transformed(ControlFlowFlattener(), src)
    assert "_nx_cfi_lut" not in out
    _exec_ok(tree)


def test_extended_arg_breaker_skips_throwaway_name_collision():
    src = (
        "_nx_fake_expr = 99\n"
        "def f():\n"
        "    a = 1\n"
        "    b = 2\n"
        "    c = 3\n"
        "    return _nx_fake_expr + a + b + c\n"
        "assert f() == 105\n"
    )
    tree, out = _transformed(ExtendedArgBreaker(), src)
    # No new in-function assignment to the colliding name was inserted.
    assert "_nx_cfi" not in out
    _exec_ok(tree)


def test_dynamic_codegen_skips_mutable_default_arguments(monkeypatch):
    monkeypatch.setattr("obfuscator.core.transforms.random.random", lambda: 0.0)
    src = (
        "def f(x, acc=[]):\n"
        "    acc.append(x)\n"
        "    total = len(acc)\n"
        "    return total\n"
        "assert f(1) == 1\n"
        "assert f(2) == 2\n"
    )
    tree, out = _transformed(DynamicCodeGenerator(), src)
    assert "def f(*args, **kwargs)" not in out
    _exec_ok(tree)


def test_dynamic_codegen_skips_zero_argument_super_in_methods(monkeypatch):
    monkeypatch.setattr("obfuscator.core.transforms.random.random", lambda: 0.0)
    src = (
        "class Base:\n"
        "    def value(self):\n"
        "        return 7\n"
        "class C(Base):\n"
        "    def f(self):\n"
        "        a = 1\n"
        "        b = 2\n"
        "        c = 3\n"
        "        return super().value() + a + b + c\n"
        "assert C().f() == 13\n"
    )
    tree, out = _transformed(DynamicCodeGenerator(), src)
    assert "def f(*args, **kwargs)" not in out
    _exec_ok(tree)


def test_temporal_purity_rejects_dynamic_attribute_and_global_operator_paths():
    assert not is_pure_function(ast.parse("def f():\n    return some.x\n").body[0])
    assert not is_pure_function(ast.parse("def f():\n    return some + 1\n").body[0])
    assert not is_pure_function(ast.parse("def f():\n    return enumerate([])\n").body[0])
    assert is_pure_function(ast.parse("def total():\n    x = 2\n    return x + 3\n").body[0])


def test_temporal_wrapper_does_not_wrap_module_shadowed_builtin_call():
    src = (
        "def len(x):\n"
        "    return 99\n"
        "def f():\n"
        "    return len((1, 2))\n"
    )
    tree = TemporalRedundancyWrapper().visit(ast.parse(src))
    assert "f_impl" not in ast.unparse(tree)


def test_builtin_aliaser_does_not_alias_shadowed_builtin():
    src = "str = lambda value: 'shadow'\nassert str(1) == 'shadow'\n"
    tree, _ = _transformed(BuiltinAliaser(), src)
    _exec_ok(tree)


def test_callgraph_does_not_indirect_shadowed_builtin(monkeypatch):
    monkeypatch.setattr("obfuscator.core.transforms.random.random", lambda: 0.0)
    src = "sum = lambda values: 99\nassert sum([1]) == 99\n"
    tree, out = _transformed(CallGraphObfuscator(), src)
    assert "_nx_ftable" not in out
    _exec_ok(tree)


def test_ast_mutator_sandbox_check_does_not_rebind_module_names(monkeypatch):
    monkeypatch.setattr("obfuscator.core.transforms.random.random", lambda: 0.9)
    monkeypatch.setattr("uuid.getnode", lambda: 0)
    monkeypatch.setattr("multiprocessing.cpu_count", lambda: 8)
    src = "uuid = 'sentinel'\nx = 1\nassert uuid == 'sentinel'\n"
    tree, out = _transformed(ASTMutator(junk_enabled=True), src)
    assert "import uuid, sys, multiprocessing" not in out
    _exec_ok(tree)


def test_bogus_exception_handler_does_not_rebind_builtins_name(monkeypatch):
    monkeypatch.setattr("obfuscator.core.transforms.random.random", lambda: 0.0)
    src = (
        "builtins = 'sentinel'\n"
        "def f():\n"
        "    a = 1\n"
        "    b = 2\n"
        "    return builtins\n"
        "assert f() == 'sentinel'\n"
    )
    tree, _ = _transformed(BogusExceptionHandler(), src)
    _exec_ok(tree)


def test_variable_splitter_leaves_reflectively_read_binding_intact(monkeypatch):
    monkeypatch.setattr("obfuscator.core.transforms.random.random", lambda: 0.0)
    src = "x = 5\nassert eval('x') == 5\n"
    tree, out = _transformed(VariableSplitter(), src)
    assert "_nx_s0a" not in out
    _exec_ok(tree)


def test_variable_splitter_skips_generated_name_collision(monkeypatch):
    monkeypatch.setattr("obfuscator.core.transforms.random.random", lambda: 0.0)
    src = (
        "_nx_s0a = 7\n"
        "x = 5\n"
        "assert x + _nx_s0a == 12\n"
    )
    tree, out = _transformed(VariableSplitter(), src)
    assert out.count("_nx_s0a") == 2  # original binding + original use only
    _exec_ok(tree)


def test_retry_after_accepts_http_date():
    class Response:
        headers = {"Retry-After": email.utils.formatdate(time.time() + 20, usegmt=True)}

    delay = core_utils._github_retry_after(Response(), default=2.0)
    assert 5.0 < delay <= 20.0


def test_github_nested_timestamp_parser_returns_epoch_seconds():
    module = ast.parse(open(core_utils.__file__, encoding="utf-8").read())
    cls = next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == "GitHubBuildFarm")
    trigger = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "trigger_and_wait")
    parse_ts = next(
        n for n in ast.walk(trigger)
        if isinstance(n, ast.FunctionDef) and n.name == "parse_ts")
    wrapper = ast.fix_missing_locations(ast.Module(body=[parse_ts], type_ignores=[]))
    ns = {}
    exec(compile(wrapper, "<parse-ts>", "exec"), ns)
    assert ns["parse_ts"]("1970-01-01T00:00:01+00:00") == pytest.approx(1.0)


def test_optimize_and_pack_accepts_standard_farm_artifact_names(tmp_path, monkeypatch):
    for name in ("payload.pyd", "payload.so", "payload.dylib"):
        (tmp_path / name).write_bytes(b"binary-" + name.encode())
    monkeypatch.setattr(core_utils, "strip_binary", lambda path: False)
    monkeypatch.setattr(core_utils, "ensure_upx_installed", lambda: False)

    tar_path = core_utils.optimize_and_pack_binaries(str(tmp_path))
    assert tar_path is not None
    with tarfile.open(tar_path, "r") as tar:
        assert set(tar.getnames()) == {
            "payload.windows.exe", "payload.linux.bin", "payload.darwin.bin"}


def test_generated_xz_loader_extracts_and_runs_standard_linux_member(tmp_path):
    shell_payload = b"#!/bin/sh\nprintf loader-ok > \"$1\"\n"
    tar_path = tmp_path / "binaries.tar"
    payload_file = tmp_path / "payload.linux.bin"
    payload_file.write_bytes(shell_payload)
    with tarfile.open(tar_path, "w") as tar:
        tar.add(payload_file, arcname="payload.linux.bin")

    loader_path = tmp_path / "loader.py"
    core_utils.generate_xz_loader_file(str(tar_path), str(loader_path))
    marker = tmp_path / "marker.txt"
    result = subprocess.run(
        [sys.executable, str(loader_path), str(marker)],
        cwd=str(tmp_path), capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert marker.read_text() == "loader-ok"
