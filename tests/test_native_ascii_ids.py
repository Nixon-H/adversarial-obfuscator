"""A native build must reach Cython with ASCII identifiers only.

Measured 2026-11-21 on the farm: the Windows runner died inside Cython with

    UnicodeEncodeError: 'latin-1' codec can't encode characters in
    position 118427-118434: ordinal not in range(256)

while the local measurement of the same fix reported 0 non-ASCII. The
difference was the option set. The local measurement exercised a handful of
transforms on a toy payload; the farm compiles with the FULL `_native_ast_opts`
dict, and one emitter in that path had never received the scoped `ascii_ids`
flag: `SymbolRenamer.get_new_name` still called `get_random_var_name(old_name)`
with no `ascii_only`, so every top-level function it renamed became
`_nixon_<babel>` again.

The lesson this file pins: the ASCII guarantee is about the EXACT option dict
the native build ships with, not about whatever subset a test happens to
enable. So the test below uses the real dict (kept in sync by importing the
same shape the pipeline builds), not a hand-picked friendly subset.
"""
import io
import os
import sys
import tokenize

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.sources import apply_ast_mutation  # noqa: E402

#: The `_native_ast_opts` dict from pipeline.py, as the farm run had it
#: (NIXON_VM_DISPATCH unset). Keep in sync with that dict: if the native build
#: gains an option, add it here too — the whole point of this file is that the
#: friendly subset is what hid the leak.
NATIVE_AST_OPTS = {
    "fragment_strings": True, "string_key_env": None,
    "string_crypto": None, "symbol_rename": True, "rename_internal": True,
    "unicode_ids": False, "strip_meta": True, "cfg_flatten": True,
    "opaque_predicates": True, "bogus_exceptions": True, "mba_subs": True,
    "split_vars": True, "unfold_constants": True, "enhanced_junk": True,
    "break_decompiler": True, "code_checksums": True, "obf_calls": True,
    "exception_flow": True, "residue_random": True, "vm_dispatch": None,
    "hwid": "", "trial_seconds": None,
}

PAYLOAD = '''
def mix(values, scale):
    total = 0
    tag = "cfg"
    for value in values:
        total = total + value * scale
    return total, tag


def apply_fn(fn, args):
    return fn(*args)


class Ledger:
    def __init__(self, rows):
        self.rows = rows

    def reconcile(self, other):
        return len(self.rows) + len(other.rows)


if __name__ == "__main__":
    print(mix([1, 2, 3], 4))
'''


def _nonascii_names(code):
    out = set()
    for tok in tokenize.generate_tokens(io.StringIO(code).readline):
        if tok.type == tokenize.NAME and any(ord(c) > 127 for c in tok.string):
            out.add(tok.string)
    return out


def test_native_opts_produce_zero_nonascii_identifiers():
    """The farm's exact compile input: every NAME token is ASCII."""
    applied, _flat = apply_ast_mutation(PAYLOAD, dict(NATIVE_AST_OPTS),
                                        strict=False)
    assert applied, "the AST layer produced nothing"
    leaks = _nonascii_names(applied)
    assert not leaks, (
        "native compile input carries non-ASCII identifiers %r; Cython 3.0.12 "
        "on the runners writes its intermediate stream as latin-1 and dies "
        "with UnicodeEncodeError" % (sorted(leaks)[:5],))


def test_the_leak_site_renames_functions_with_ascii_names():
    """The site the farm run exercised, asserted on its own.

    `SymbolRenamer.get_new_name` is what renamed `mix` into a babel name after
    the scoped flag was first threaded through — the string sealer's generator
    had been fixed and this one had not, which is why the earlier measurement
    (a friendly option subset) showed zero while the farm showed the crash.

    The ASCII name keeps the babel SHAPE (`_nixon_<suffix>`, no stem): an
    earlier variant embedded the original name, and the stem then survives into
    the Cython-generated C as a readable hint about the source name — a
    protection regression this file refuses.
    """
    from obfuscator.core.transforms import SymbolRenamer

    renamer = SymbolRenamer(ascii_ids=True)
    new = renamer.get_new_name("mix")
    assert all(ord(c) < 128 for c in new), new
    assert "mix" not in new, \
        "the native name must not carry a stem hint of the source name: %r" % (new,)


def test_python_mode_still_gets_babel_names():
    """The flag is scoped, not global: the pure-Python path keeps its pool."""
    opts = dict(NATIVE_AST_OPTS)
    opts["unicode_ids"] = True
    applied, _flat = apply_ast_mutation(PAYLOAD, opts, strict=False)
    leaks = _nonascii_names(applied)
    assert leaks, (
        "the pure-Python path should still use the babel pool (that is where "
        "it reaches shipped source and costs something); a global switch "
        "would be a protection regression")
