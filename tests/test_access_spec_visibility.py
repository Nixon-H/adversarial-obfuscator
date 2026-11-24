"""AI-BUILD-002: an invalid --access sub-option must be VISIBLE and fatal.

The defect: `--access bogus=1` exited 1 with completely empty console output.
The parser did raise the right message --

    SystemExit("--access: unknown sub-option 'bogus'; expected one of: ...")

-- but enable_log_redirect() dup2()s fd 2 onto build.log, so the message went
to a file and never to the terminal. The operator saw a failed build with no
reason. The security consequence is the part that matters: a MISSPELLED gate
name (`--access expiry=` when the field is `expire=`) was silently ignored, so
an operator could believe an expiry or hwid lock was armed when it was not.

The fix routes the spec-parser's SystemExit through UI.fatal, which writes to
the saved console fd and is therefore visible with redirection active.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def test_the_parser_still_raises_for_an_unknown_suboption():
    """The validator contract is unchanged: it raises."""
    from obfuscator.core.pipeline import (
        _ACCESS_BOOLEAN, _ACCESS_SPEC_FIELDS, _parse_unified_spec,
    )
    import pytest
    with pytest.raises(SystemExit) as exc:
        _parse_unified_spec(["bogus=1"], _ACCESS_SPEC_FIELDS,
                            _ACCESS_BOOLEAN, "access")
    assert "unknown sub-option" in str(exc.value)


def test_expiry_is_not_a_valid_field_and_expire_is():
    """Pin the exact trap: the field is 'expire', not 'expiry'.

    This is the spelling a user is most likely to get wrong, and before the fix
    getting it wrong produced a build with no gate and no message.
    """
    from obfuscator.core.pipeline import _ACCESS_SPEC_FIELDS
    assert "expire" in _ACCESS_SPEC_FIELDS
    assert "expiry" not in _ACCESS_SPEC_FIELDS


def test_main_routes_spec_errors_through_the_console():
    """main() must catch the SystemExit and emit it via UI.fatal.

    Asserted on the source because the behavioural check needs a full build.
    The measured behaviour is recorded in the register: `--access bogus=1` now
    prints "[FATAL ERROR] --access: unknown sub-option ..." on the console and
    exits 1, where before it exited 1 silently.
    """
    import inspect
    from obfuscator.core import pipeline
    src = inspect.getsource(pipeline.main)
    assert "apply_unified_specs(args)" in src
    assert "except SystemExit" in src, (
        "main() does not catch the spec parser's SystemExit, so the message "
        "only reaches the redirected log file and the operator sees nothing")
    idx = src.find("apply_unified_specs(args)")
    window = src[max(0, idx - 400):idx + 400]
    assert "UI.fatal" in window, (
        "the caught message is not routed to the console sink (UI.fatal), so "
        "it stays invisible while log redirection is active")
