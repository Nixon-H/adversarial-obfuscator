"""Executed semantic round-trips for the offline ASCII renamer.

The renamer must change spelling, not Python binding behaviour.  These tests
execute the rewritten source so alias, recursion, closure, keyword, and pattern
regressions cannot hide behind a merely parseable AST.
"""
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ai_obfuscator", ROOT / "ai-obfuscator.py")
assert SPEC is not None and SPEC.loader is not None
ai_obfuscator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ai_obfuscator)


def _roundtrip(source):
    rewritten = ai_obfuscator.deobfuscate_offline_ascii(source)
    assert rewritten.isascii(), rewritten
    namespace = {}
    exec(compile(rewritten, "<renamed>", "exec"), namespace)
    return namespace["result"]


def test_import_aliases_and_uses_share_one_replacement():
    source = """\
import math as 数学
from math import sqrt as 开方
result = 数学.sqrt(开方(256))
"""
    assert _roundtrip(source) == 4.0


def test_function_name_is_predeclared_for_recursion():
    source = """\
def 阶乘(n):
    return 1 if n <= 1 else n * 阶乘(n - 1)
result = 阶乘(6)
"""
    assert _roundtrip(source) == 720


def test_generated_names_do_not_capture_existing_bindings():
    source = """\
var01 = "variable"
funDecode01 = "function"
classDecode01 = "class"
λ = 7
def 函数():
    return λ
class 类:
    pass
result = (var01, funDecode01, classDecode01, λ, 函数(), 类.__name__)
"""
    assert _roundtrip(source) == (
        "variable", "function", "class", 7, 7, "classDecode02",
    )


def test_global_declaration_and_assignment_are_renamed_together():
    source = """\
λ = 1
def outer():
    def inner():
        global λ
        λ = 5
    inner()
outer()
result = λ
"""
    assert _roundtrip(source) == 5


def test_nonlocal_closure_and_shadowed_parameter_keep_their_bindings():
    source = """\
def outer():
    λ = 1
    def inner():
        nonlocal λ
        λ += 4
    def shadow(λ):
        return λ + 1
    inner()
    return shadow(λ), λ
result = outer()
"""
    assert _roundtrip(source) == (6, 5)


def test_keyword_names_values_and_annotations_are_visited():
    source = """\
class Marker:
    pass
类型 = Marker
def 函数(参数: 类型) -> 类型:
    return 参数
值 = 3
result = (函数(参数=值), list(函数.__annotations__.values())[0] is Marker,
        list(函数.__annotations__.values())[1] is Marker)
"""
    assert _roundtrip(source) == (3, True, True)


def test_except_and_match_capture_names_are_renamed():
    source = """\
result = []
try:
    raise ValueError("bad")
except ValueError as 错误:
    result.append(str(错误))
match 3:
    case 捕获 if 捕获 > 2:
        result.append(捕获)
"""
    assert _roundtrip(source) == ["bad", 3]


def test_method_attributes_and_keywords_roundtrip():
    source = """\
class 类:
    def 方法(self, 值):
        return 值 + 1
对象 = 类()
result = 对象.方法(值=4)
"""
    assert _roundtrip(source) == 5
