"""§1 runtime state validation: the pack's declared structure must be real.

The per-section HMAC tags prove the ciphertext is authentic. They do not prove
the loader is interpreting the pack under the same structural claims the
builder sealed it with — count, total length, index ordering, per-section
salts. Editing those changes no authenticated byte; it changes what the
authenticated bytes are taken to mean.

These tests pin the property that matters: a genuine pack is accepted, and an
edited structure is rejected, independently of the outer Merkle anchor.
"""
import copy
import importlib.util
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.pack_state import (  # noqa: E402
    STATE_SCHEMA, emit_state_check_snippet, state_digest,
)


def _pack():
    from obfuscator.section_split import pack_json
    js, key = pack_json(b"BODY" * 400, sections=4, key=range(32))
    return json.loads(js), key


def _checker():
    """Load the emitted snippet as a real module and return its check.

    The file is created with mkstemp, which ALLOCATES the name and returns a
    descriptor -- no path is joined from untrusted parts, and the snippet is
    then imported exactly as an artefact would import it. This avoids the
    exec-of-generated-string pattern while still exercising real emitted code.
    """
    fd, path = tempfile.mkstemp(prefix="statechk-", suffix=".py")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(emit_state_check_snippet())
        spec = importlib.util.spec_from_file_location("emitted_state_check",
                                                      path)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not load the emitted state-check snippet")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod._nx_pack_state_ok
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _mutations():
    return [
        ("total", lambda p: p.update(total=p["total"] + 1)),
        ("count", lambda p: p.update(count=p["count"] + 1)),
        ("salt", lambda p: p["sections"][0].update(salt="0" * 16)),
        ("index", lambda p: p["sections"][0].update(i=99)),
        ("drop-state", lambda p: p.pop("state", None)),
    ]


def test_genuine_pack_is_accepted():
    pack, _key = _pack()
    assert pack["state"] == state_digest(
        pack["sections"], pack["count"], pack["total"])
    assert _checker()(pack) is True


def test_schema_is_shared_between_builder_and_runtime():
    """The digest is only meaningful if both sides hash the same inputs."""
    pack, _key = _pack()
    assert STATE_SCHEMA in emit_state_check_snippet()


def test_every_structural_edit_is_rejected():
    check = _checker()
    for label, mutate in _mutations():
        pack, _key = _pack()
        edited = copy.deepcopy(pack)
        mutate(edited)
        assert check(edited) is False, "%s edit was accepted" % label


def test_missing_state_fails_closed():
    """An old-format pack must not be treated as acceptable.

    "This is an older pack" is exactly what an attacker would claim, so the
    check rejects the absent field rather than skipping the validation.
    """
    pack, _key = _pack()
    old = {k: v for k, v in pack.items() if k != "state"}
    assert _checker()(old) is False


def test_totals_must_match_carried_ciphertext():
    """A re-sliced pack cannot keep a stale declared total."""
    pack, _key = _pack()
    edited = copy.deepcopy(pack)
    edited["sections"][0]["data"] = "00" * 40
    assert _checker()(edited) is False


def test_emitted_snippets_define_and_call_the_check():
    """A snippet that calls the check without defining it would NameError."""
    from obfuscator import section_split as ss

    for name, fn in (("loader", ss.emit_loader_snippet),
                     ("moving", ss.emit_moving_snippet),
                     ("stream", ss.emit_stream_snippet)):
        src = fn()
        assert "_nx_pack_state_ok(pack)" in src, "%s: check not called" % name
        assert "def _nx_pack_state_ok" in src, (
            "%s: check called but not defined; every artefact would "
            "NameError at load" % name)
        compile(src, "<%s>" % name, "exec")
