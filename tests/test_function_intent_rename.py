"""FunctionIntentObfuscator must not rename anything it cannot rewrite.

Regression for the 2026-11-15 bench finding. ``obfuscate_intent`` collected
every ``FunctionDef`` in the tree -- methods included -- and renamed each one
to a misleading ``_nx_op_<hex>`` name. Only ``ast.Name`` uses were rewritten,
so a method reached through attribute access kept its old spelling at the call
site while the definition moved:

    class Point:            ->   class _nx_e42ca7:
        def norm(self): ...      def _nx_op_81174899(self): ...

    Point(3, 4).norm()      ->   _nx_e42ca7(3, 4).norm()
                                 AttributeError: no attribute 'norm'

The payload died at import on the first method call. Three related defects
came out of the same code path:

* dunder methods were renamed too, which breaks every protocol hook
  (``__init__``, ``__eq__``, ``__enter__``, ...);
* ``_name_map`` was keyed by bare name, so a method and a module-level
  function sharing a name collided and both definitions got one new name;
* ``visit_Name`` rewrote parameters that shadowed a renamed global, so
  ``def f(f)`` lost its parameter.

These tests pin the fix: rename module-level functions only, skip dunders,
and never rewrite a name that a parameter shadows.
"""
import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.function_intent import FunctionIntentObfuscator


def _run(source):
    """Obfuscate ``source``, execute it, return its stdout."""
    tree = FunctionIntentObfuscator(seed=11).obfuscate_intent(ast.parse(source))
    code = ast.unparse(tree)
    namespace = {"__name__": "__main__"}
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(code, "<fi>", "exec"), namespace)
    return buf.getvalue(), code


def test_method_call_survives_rename():
    out, _ = _run(
        "import dataclasses\n"
        "@dataclasses.dataclass\n"
        "class Point:\n"
        "    x: int\n"
        "    y: int\n"
        "    def norm(self):\n"
        "        return (self.x ** 2 + self.y ** 2) ** 0.5\n"
        "print(Point(3, 4).norm())\n"
    )
    assert out.strip() == "5.0"


def test_method_definition_keeps_its_name():
    _, code = _run(
        "class C:\n"
        "    def helper(self):\n"
        "        return 1\n"
        "print(C().helper())\n"
    )
    assert "def helper(self):" in code


def test_dunder_methods_are_never_renamed():
    out, code = _run(
        "class C:\n"
        "    def __init__(self, v):\n"
        "        self.v = v\n"
        "    def __eq__(self, other):\n"
        "        return self.v == other.v\n"
        "    def __enter__(self):\n"
        "        return self\n"
        "    def __exit__(self, *a):\n"
        "        return False\n"
        "with C(1) as a, C(1) as b:\n"
        "    print(a == b)\n"
    )
    assert out.strip() == "True"
    for dunder in ("__init__", "__eq__", "__enter__", "__exit__"):
        assert "def %s(" % dunder in code


def test_module_level_function_is_renamed_and_call_sites_follow():
    out, code = _run(
        "def compute(x):\n"
        "    return x + 1\n"
        "print(compute(41))\n"
    )
    assert out.strip() == "42"
    assert "def compute(" not in code


def test_method_and_module_function_with_same_name_do_not_collide():
    out, _ = _run(
        "def helper():\n"
        "    return 'module'\n"
        "class C:\n"
        "    def helper(self):\n"
        "        return 'method'\n"
        "print(helper(), C().helper())\n"
    )
    assert out.strip() == "module method"


def test_parameter_shadowing_a_renamed_global_is_not_rewritten():
    out, _ = _run(
        "def compute(x):\n"
        "    return x * 2\n"
        "def apply(compute):\n"
        "    return compute(3)\n"
        "print(apply(lambda n: n + 100))\n"
    )
    assert out.strip() == "103"


def test_lambda_parameter_shadowing_a_renamed_global_is_not_rewritten():
    out, _ = _run(
        "def compute(x):\n"
        "    return x + 1\n"
        "print((lambda compute: compute * 3)(5))\n"
    )
    assert out.strip() == "15"


def test_nested_function_keeps_its_name():
    out, code = _run(
        "def outer():\n"
        "    def inner():\n"
        "        return 7\n"
        "    return inner()\n"
        "print(outer())\n"
    )
    assert out.strip() == "7"
    assert "def inner(" in code
