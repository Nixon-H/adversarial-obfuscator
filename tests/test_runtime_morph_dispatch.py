"""The runtime-morph dispatch table must have a consumer and stay correct.

Regression for the 2026-11-15 audit. ``SELF_MORPH_GRAPH_SOURCE`` was emitted
into every artefact and nothing ever registered into it or called it, so the
"runtime metamorphism" flag was metadata only.

Wiring it up exposed a second problem: the class permuted ``_dispatch``
itself, swapping two state ids' functions. Calling it from the state machine
would have re-pointed a state at the wrong stage function -- a real behaviour
change. The fix permutes ``_order`` instead, which keeps every lookup correct
while still mutating the table on every call.

These tests pin both halves: the class is wired in, and the wiring cannot
change which function a state resolves to.
"""
import os
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core import sources


def _morph_class():
    """Build the emitted class with the real randomised names.

    The name is a unicode identifier, and Python normalises those (NFKC) on
    compile, so the scope key is not byte-identical to ``VARS``. Look the
    class up by type instead of by name.
    """
    namespace = dict(sources.VARS)
    namespace["SELF_MORPH_CLS"] = sources.VARS["SELF_MORPH_CLS"]
    namespace["METHOD_MORPH_DISPATCH"] = sources.VARS["METHOD_MORPH_DISPATCH"]
    code = sources.SELF_MORPH_GRAPH_SOURCE.format(**namespace)
    scope: dict = {}
    exec(compile(code, "<self_morph>", "exec"), scope)
    classes = [v for v in scope.values() if isinstance(v, type)]
    assert len(classes) == 1, "expected exactly one class in the template"
    return classes[0]


def _dispatch(cls):
    """The dispatch method, looked up by its NFKC-normalised name.

    Python normalises unicode identifiers on compile, so the attribute name
    is not byte-identical to the ``VARS`` entry.
    """
    wanted = unicodedata.normalize("NFKC", sources.VARS["METHOD_MORPH_DISPATCH"])
    return getattr(cls, wanted)


def test_dispatch_returns_the_registered_function_result():
    cls = _morph_class()
    cls.register("a", lambda: "A")
    cls.register("b", lambda: "B")
    assert cls.resolve("a")() == "A"
    assert _dispatch(cls)("b") == "B"


def test_unknown_id_returns_none_rather_than_raising():
    """The state machine falls back to its own dict on None."""
    cls = _morph_class()
    assert _dispatch(cls)("nope") is None


def test_repeated_dispatch_never_repoints_a_state():
    """The old implementation swapped _dispatch entries; this must not.

    Ten calls is enough for the LCG to pick several distinct index pairs.
    """
    cls = _morph_class()
    fns = {f"s{i}": (lambda i=i: i) for i in range(6)}
    for fid, fn in fns.items():
        cls.register(fid, fn)
    for _ in range(10):
        for fid, fn in fns.items():
            assert cls.resolve(fid) is fn, (
                "dispatch table re-pointed %s at a different function" % fid)


def test_the_table_actually_mutates_at_runtime():
    """A consumer that never mutates is still inert."""
    cls = _morph_class()
    for i in range(6):
        cls.register(f"s{i}", lambda: None)
    before = list(cls._order)
    for _ in range(10):
        _dispatch(cls)("s0")
    assert cls._order != before, "the order table never changed"
    assert sorted(cls._order) == sorted(before), "the order table lost entries"


def test_state_machine_registers_and_dispatches_through_it():
    """The loader must register its stages and route the step through it."""
    template = sources.LOADER_HEAD + "\n" + sources.LOADER_BODY
    assert "{SELF_MORPH_CLS}.register(_nx_fid, _nx_fn)" in template
    assert "{SELF_MORPH_CLS}.{METHOD_MORPH_DISPATCH}(curr)" in template
    # The fallback keeps the state machine working if registration is skipped.
    assert "_nx_step = dispatcher[curr]()" in template
