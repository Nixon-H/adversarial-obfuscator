"""Execution regressions for binding-sensitive offline renamer behavior."""

import ast
import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ai_obfuscator_semantic_regressions", ROOT / "ai-obfuscator.py"
)
assert SPEC is not None and SPEC.loader is not None
ai_obfuscator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ai_obfuscator)


def _rewrite(source):
    return ai_obfuscator.deobfuscate_offline_ascii(source)


def _roundtrip(source, initial=None):
    namespace = {} if initial is None else dict(initial)
    rewritten = _rewrite(source)
    exec(compile(rewritten, "<renamed>", "exec"), namespace)
    return namespace["result"]


def test_internal_keyword_label_tracks_renamed_parameter():
    source = """\
def 函数(参数):
    return 参数 + 1
result = 函数(参数=4)
"""
    assert _roundtrip(source) == 5


def test_internal_lambda_keyword_label_tracks_renamed_parameter():
    source = """\
result = (lambda 参数: 参数 + 1)(参数=4)
"""
    assert _roundtrip(source) == 5


def test_dict_keyword_labels_remain_data_keys():
    source = """\
关键字 = 9
result = dict(关键字=关键字)
"""
    assert _roundtrip(source) == {"关键字": 9}


def test_external_callback_keyword_label_is_preserved():
    source = """\
def 调用(函数):
    return 函数(关键字=3)
result = 调用(dict)
"""
    assert _roundtrip(source) == {"关键字": 3}


def test_kwargs_keyword_labels_remain_data_keys():
    source = """\
def 收集(**选项):
    return 选项
result = 收集(关键字=3)
"""
    assert _roundtrip(source) == {"关键字": 3}


def test_rebound_function_keyword_label_is_preserved():
    source = """\
def 函数(关键字):
    return 关键字
函数 = dict
result = 函数(关键字=3)
"""
    assert _roundtrip(source) == {"关键字": 3}


def test_recursive_internal_keyword_call_roundtrips():
    source = """\
def 递归(值):
    if 值 <= 1:
        return 1
    return 值 * 递归(值=值 - 1)
result = 递归(值=5)
"""
    assert _roundtrip(source) == 120


def test_global_binding_and_dict_keyword_label_are_independent():
    source = """\
关键字 = 1
def 设置():
    global 关键字
    关键字 = 2
    return dict(关键字=关键字)
result = (设置(), 关键字)
"""
    assert _roundtrip(source) == ({"关键字": 2}, 2)


def test_nonlocal_binding_and_dict_keyword_label_are_independent():
    source = """\
def 外层():
    关键字 = 1
    def 内层():
        nonlocal 关键字
        关键字 = 2
        return dict(关键字=关键字)
    return 内层(), 关键字
result = 外层()
"""
    assert _roundtrip(source) == ({"关键字": 2}, 2)


def test_unaliased_unicode_import_preserves_source_and_adds_mapped_asname(
        monkeypatch):
    module = types.ModuleType("数学")
    module.sqrt = lambda value: value ** 0.5
    monkeypatch.setitem(sys.modules, "数学", module)
    source = """\
import 数学
result = 数学.sqrt(16)
"""
    assert _roundtrip(source) == 4.0
    alias = ast.parse(_rewrite(source)).body[0].names[0]
    assert alias.name == "数学"
    assert alias.asname is not None and alias.asname.isascii()
    assert alias.asname != "数学"


def test_unaliased_unicode_from_import_preserves_source_and_adds_mapped_asname(
        monkeypatch):
    module = types.ModuleType("数学")
    module.开方 = lambda value: value ** 0.5
    monkeypatch.setitem(sys.modules, "数学", module)
    source = """\
from 数学 import 开方
result = 开方(25)
"""
    assert _roundtrip(source) == 5.0
    alias = ast.parse(_rewrite(source)).body[0].names[0]
    assert alias.name == "开方"
    assert alias.asname is not None and alias.asname.isascii()
    assert alias.asname != "开方"


def test_unaliased_dotted_unicode_import_keeps_top_level_binding(monkeypatch):
    package = types.ModuleType("数学")
    package.__path__ = []
    submodule = types.ModuleType("数学.util")
    submodule.sqrt = lambda value: value ** 0.5
    package.util = submodule
    monkeypatch.setitem(sys.modules, "数学", package)
    monkeypatch.setitem(sys.modules, "数学.util", submodule)
    source = """\
import 数学.util
result = (数学.__name__, 数学.util.sqrt(36))
"""
    assert _roundtrip(source) == ("数学", 6.0)
    rewritten = ast.parse(_rewrite(source))
    import_names = [alias.name for node in rewritten.body
                    if isinstance(node, ast.Import) for alias in node.names]
    assert "数学.util" in import_names
    assert any(alias.asname and alias.asname.isascii()
               for node in rewritten.body if isinstance(node, ast.Import)
               for alias in node.names)


def test_match_mapping_rest_capture_is_renamed_with_its_uses():
    source = """\
def 提取(数据):
    match 数据:
        case {"项目": [首项, *剩余], **额外} if 首项 > 0:
            return 首项, 剩余, 额外
result = 提取({"项目": [1, 2, 3], "键": 4})
"""
    assert _roundtrip(source) == (1, [2, 3], {"键": 4})


def test_internal_class_attributes_and_methods_are_renamed():
    source = """\
class 类:
    属性 = 5
    def 方法(self, 值):
        return self.属性 + 值
对象 = 类()
result = (对象.属性, 对象.方法(值=3), 类.属性)
"""
    assert _roundtrip(source) == (5, 8, 5)


def test_dynamic_external_attribute_is_preserved():
    source = """\
import types
对象 = types.SimpleNamespace()
setattr(对象, "属性", 7)
result = 对象.属性
"""
    assert _roundtrip(source) == 7


def test_external_attribute_with_internal_spelling_is_preserved_per_receiver():
    source = """\
import types
class 类:
    属性 = 5
对象 = 类()
外部 = types.SimpleNamespace()
setattr(外部, "属性", 9)
result = (对象.属性, 外部.属性)
"""
    assert _roundtrip(source) == (5, 9)


def test_unproven_receiver_attribute_is_preserved():
    source = """\
import types
class 类:
    属性 = 5
def 读取(对象):
    return 对象.属性
外部 = types.SimpleNamespace()
setattr(外部, "属性", 11)
result = 读取(外部)
"""
    assert _roundtrip(source) == 11


def test_internal_instance_attribute_assignment_and_load_are_renamed():
    source = """\
class 类:
    def __init__(self):
        self.属性 = 7
    def 读取(self):
        return self.属性
result = 类().读取()
"""
    assert _roundtrip(source) == 7


def test_direct_internal_instance_attribute_creation_is_renamed():
    source = """\
class 类:
    pass
对象 = 类()
对象.属性 = 8
result = 对象.属性
"""
    assert _roundtrip(source) == 8


def test_inherited_internal_method_attribute_is_renamed():
    source = """\
class 基类:
    def 方法(self, 值):
        return 值 + 1
class 子类(基类):
    pass
result = 子类().方法(值=4)
"""
    assert _roundtrip(source) == 5
