"""Implicit string concatenation must survive the string-table pass.

The rewriter is line-oriented: it replaces each literal with a table
lookup. Two adjacent literals therefore became two lookups with no `+`,
which is a SyntaxError in the emitted artefact — and one that named
nothing useful, because the build only noticed when it tried to compile
the file.

The fix merges the concatenation first, using tokenizer positions so
everything outside the joined literals is byte-identical.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import _merge_adjacent_string_literals as merge  # noqa: E402


class TestMerges:
    def test_same_line(self):
        assert merge('x = "a" "b"\n') == "x = 'ab'\n"

    def test_across_lines_inside_parens(self):
        src = (
            'raise SystemExit(\n'
            '    "one part of the message "\n'
            '    "and the second part\\n")\n'
        )
        out = merge(src)
        assert "one part of the message and the second part\\n" in out
        # One literal, not two lookups in a row.
        assert out.count('"') + out.count("'") >= 2
        compile(out, "<merged>", "exec")

    def test_mixed_quotes(self):
        out = merge("x = 'a' \"b\"\n")
        compile(out, "<merged>", "exec")
        assert "ab" in out

    def test_full_rewrite_emits_compilable_code(self):
        """The end-to-end property: what the pass emits must compile."""
        from obfuscator.core.pipeline import Nixon_Enc_strings
        src = (
            "def f():\n"
            '    raise SystemExit("first part "\n'
            '                       "second part")\n'
        )
        out = Nixon_Enc_strings(src)
        compile(out, "<emitted>", "exec")


class TestLeavesAlone:
    def test_separate_statements(self):
        src = 'x = "a"\ny = "b"\n'
        assert merge(src) == src

    def test_explicit_concatenation(self):
        src = 'x = "a" + "b"\n'
        assert merge(src) == src

    def test_fstring_is_not_merged(self):
        src = 'x = f"a{1}" "c"\n'
        assert merge(src) == src

    def test_dict_and_triple_quotes(self):
        for src in ('d = {"k": "v"}\n', 'x = """a\nb"""\n'):
            assert merge(src) == src

    def test_invalid_source_is_returned_unchanged(self):
        src = "def (:\n"
        assert merge(src) == src
