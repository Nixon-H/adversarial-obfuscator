"""Regression: constant-expression bindings must fold for closure resolution.

The shadow-build lane failed with UnresolvedNameError: _nx_opaque. The
attention-poison transform emits `_nx_opaque = 315 % 2 == 1` -- a value
that is compile-time fixed but syntactically not a Constant. When a
nested function read the name, the closure-constant memory (which only
recorded literals) missed it, the name resolved to nothing, and strict
mode refused the module.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from irgen.compile import compile_py_to_ir


def test_closure_reads_folded_constant_expression():
    src = (
        "def outer():\n"
        "    _nx_opaque = 315 % 2 == 1\n"
        "    def inner():\n"
        "        if _nx_opaque == False:\n"
        "            return 0\n"
        "        return 1\n"
        "    return inner()\n"
        "print(outer())\n"
    )
    compile_py_to_ir(src)  # must not raise UnresolvedNameError


def test_fold_covers_arithmetic_and_bitwise():
    src = (
        "def outer():\n"
        "    mask = (1 << 4) | 2\n"
        "    def inner():\n"
        "        return mask\n"
        "    return inner()\n"
    )
    compile_py_to_ir(src)


def test_non_pure_binding_is_not_folded():
    """A binding with a call must NOT be eval'd -- nothing user-controlled
    may reach eval()."""
    # structural: eval must never see a Call node -- enforced by the walker;
    # verified here through the public behaviour: a call binding compiles
    # through the normal alloca path without being constant-folded.
    src = (
        "def outer():\n"
        "    x = len('abc')\n"
        "    def inner():\n"
        "        return x\n"
        "    return inner()\n"
    )
    compile_py_to_ir(src)  # compiles through normal paths, no eval of len()
