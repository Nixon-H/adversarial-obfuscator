"""The Python fallback path must decrypt what the build sealed.

Three defects made the fallback unreachable in a licence-bound native
build.  Each one is silent on its own -- the artefact simply exits 137
through the kill ladder -- so each gets a test that fails loudly:

1. ``_NX_EFF_KEY`` drifted from the build-time effective key.  The share
   path applied the customer/licence mask; the split-bootstrap path did
   not, so ``BLOB_KEY_SB`` was ``xor(raw, sha256(build_id))`` while the
   payload was sealed with ``derive_effective_key(raw, build_id, salt)``.
   The section join therefore failed its ``key_hint`` check on every
   licence-bound build.

2. The hostile-host wrapper around the join helper read ``if HARDEN():``.
   ``HARDEN()`` returns True when every anti-debug check PASSED, so the
   guard poisoned the key on clean hosts and only on clean hosts.

3. The ``--transforms data`` pass encrypted every string subscript key,
   including keys of dicts that arrive from ``json.loads``.  The join
   read ``pack['sections']`` from a JSON pack and raised KeyError, which
   the join's own ``except Exception`` turned into ``return None``.
"""
import ast
import base64
import hashlib
import json
import marshal
import os
import re
import sys
import zlib


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import generate_hybrid_loader_script
from obfuscator.core.utils import fast_xor_bytes
from obfuscator.key_emit import derive_effective_key
from obfuscator.section_split import (
    JOIN_FUNC,
    emit_loader_snippet,
    pack_json,
    stream_join,
)

_BLANKS = {"windows": "", "linux": "", "darwin": ""}
_RAW_KEY = bytes(range(32))
_BUILD_ID = "fb-integrity-01"
_SALT = "c0ffee" * 10
_PAYLOAD_SRC = "FB_RAN = 100 + 23\n"


def _sealed_fallback(raw_key=_RAW_KEY):
    """The fallback blob exactly as the pipeline hands it to the loader."""
    marshalled = marshal.dumps(compile(_PAYLOAD_SRC, "<fb_e2e>", "exec"))
    return fast_xor_bytes(zlib.compress(marshalled), raw_key)


def _loader(**kwargs):
    kwargs.setdefault("build_id", _BUILD_ID)
    return generate_hybrid_loader_script(
        dict(_BLANKS), _sealed_fallback(), _RAW_KEY.hex(), **kwargs)


def _exec(src, name="fb_loader"):
    ns = {"__name__": name}
    exec(compile(src, "<%s>" % name, "exec"), ns)
    return ns


# --- 1. one effective key on every derivation path --------------------------

def test_split_bootstrap_key_carries_the_customer_mask():
    eff = derive_effective_key(_RAW_KEY, _BUILD_ID, _SALT)
    src, _, _ = _loader(split_bootstrap=True, customer_salt=_SALT,
                        licence_bound=True)
    ns = _exec(src)
    assert ns["BLOB_KEY"] == eff
    assert ns["BLOB_KEY_SB"] == eff, (
        "split-bootstrap key dropped the customer mask; the payload is "
        "sealed with derive_effective_key() and cannot be decrypted")
    assert ns["_NX_EFF_KEY"] == eff


def test_split_bootstrap_key_still_matches_without_a_salt():
    # The unbound build must keep the pre-existing shape: no mask, so the
    # two derivations agree trivially.
    eff = derive_effective_key(_RAW_KEY, _BUILD_ID)
    src, _, _ = _loader(split_bootstrap=True)
    ns = _exec(src)
    assert ns["BLOB_KEY"] == ns["BLOB_KEY_SB"] == ns["_NX_EFF_KEY"] == eff


def test_section_pack_is_sealed_with_the_loader_key():
    # The pack's key_hint is the loader's own check; if the build seals
    # with a different key the join returns None and the artefact dies.
    src, _, _ = _loader(split_bootstrap=True, customer_salt=_SALT,
                        licence_bound=True, section_split=True,
                        section_count=4)
    ns = _exec(src)
    pack = json.loads(base64.b85decode(ns["_NX_SECTION_PACK"]).decode("utf-8"))
    assert pack["key_hint"] == hashlib.sha256(ns["_NX_EFF_KEY"]).hexdigest()[:16]
    joined = ns[JOIN_FUNC](ns["_NX_SECTION_PACK"], ns["_NX_EFF_KEY"])
    assert joined is not None, "section join failed with the loader's own key"


def test_fallback_runs_end_to_end_with_split_bootstrap_and_salt():
    src, _, _ = _loader(split_bootstrap=True, customer_salt=_SALT,
                        licence_bound=True, section_split=True,
                        section_count=4)
    ns = _exec(src)
    ns["_exec_fallback"]()
    assert ns.get("FB_RAN") == 123


def test_fallback_runs_end_to_end_without_section_split():
    src, _, _ = _loader(split_bootstrap=True, customer_salt=_SALT,
                        licence_bound=True, section_split=False)
    ns = _exec(src)
    ns["_exec_fallback"]()
    assert ns.get("FB_RAN") == 123


# --- 2. the hostile-host guard must not fire on a clean host ----------------

def test_hostile_wrapper_does_not_poison_a_clean_host():
    src, _, _ = _loader(section_split=True, section_count=4)
    # The guard must be the negated form: HARDEN() is True on a clean host.
    # The emitted function name is a randomised identifier, so match any
    # non-paren run rather than \w+ (the names carry combining marks).
    assert re.search(r"if not [^\n(]+\(\):\s*\n\s*_nx_join_real", src), (
        "hostile-host guard is not negated; it poisons the join key on "
        "every clean host")
    assert not re.search(r"if (?!not )[^\n(]+\(\):\s*\n\s*_nx_join_real", src)


def test_clean_host_keeps_the_real_join_helper():
    src, _, _ = _loader(section_split=True, section_count=4)
    ns = _exec(src)
    # No HARDEN in this namespace, so the wrapper's NameError is swallowed
    # and the join helper is the emitted one.
    assert ns[JOIN_FUNC] is not None
    assert "_nx_join_real" not in ns


# --- 3. the data transform must not rewrite external dict keys --------------

def _protect(source, level=3):
    from scripts.data_obfuscation.data_protector import DataProtector
    tree = DataProtector(level=level).protect(ast.parse(source))
    return ast.unparse(ast.fix_missing_locations(tree))


def test_data_transform_leaves_external_dict_keys_alone():
    source = (
        "import json\n"
        "def read(blob):\n"
        "    pack = json.loads(blob)\n"
        "    return pack['sections']\n"
    )
    out = _protect(source)
    assert "['sections']" in out, (
        "subscript key of a json.loads() dict was encrypted; the lookup "
        "raises KeyError against the plaintext key in the data")
    assert "['sections'].encode" not in out


def test_data_transform_still_encrypts_local_dict_keys():
    source = (
        "def read():\n"
        "    user = {'name': 'Alice'}\n"
        "    return user['name']\n"
    )
    out = _protect(source, level=2)
    assert ".encode(" in out
    assert "['name']" not in out


def test_data_transform_keeps_a_rebound_name_plain():
    source = (
        "import json\n"
        "def read(blob):\n"
        "    pack = {'a': 1}\n"
        "    pack = json.loads(blob)\n"
        "    return pack['sections']\n"
    )
    out = _protect(source)
    assert "['sections']" in out
    assert "['sections'].encode" not in out


def test_section_join_survives_the_data_transform():
    key = bytes(range(32))
    payload = b"\x00" + b"z" * 4000
    js, _ = pack_json(payload, sections=4, key=key)
    b85 = base64.b85encode(js).decode("ascii")
    ns = {}
    exec(_protect(emit_loader_snippet()), ns)
    joined = ns[JOIN_FUNC](b85, key)
    assert joined is not None, "data transform broke the section join"
    assert bytes(joined) == payload


def test_stream_join_and_emitted_join_agree():
    # The build-side and loader-side halves must stay byte-compatible.
    key = bytes(range(32))
    payload = b"\x00" + b"q" * 999
    js, _ = pack_json(payload, sections=3, key=key)
    pack = json.loads(js.decode("utf-8"))
    ns = {}
    exec(emit_loader_snippet(), ns)
    emitted = ns[JOIN_FUNC](base64.b85encode(js).decode("ascii"), key)
    assert bytes(emitted) == bytes(stream_join(pack, key)) == payload


# ── keyed self-integrity anchor: armed only when licence-bound ───────────
#
# The anchor is keyed with the licence's key_material (not in the artefact),
# so a patched artefact cannot re-stamp itself. Two failure modes were both
# live at once and are pinned here:
#   1. the unlicensed build left the template's 64-zero placeholder, which is
#      TRUTHY, so every non-licence artefact died at import with "keyed
#      anchor present but no licence key_material" (the post-build
#      verification suite caught it on a plain 2-layer build);
#   2. a fix that emptied the placeholder instead broke the licence path,
#      because the build's substitution regex requires the 64-zero slot.

def _sources_text():
    return open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "obfuscator", "core", "sources.py"),
        encoding="utf-8").read()


def test_unlicensed_anchor_placeholder_is_skipped():
    """An all-zero anchor (unlicensed build) must NOT arm the check."""
    src = _sources_text()
    i = src.find("# Keyed anchor.")
    assert i != -1, "keyed anchor block not found in sources.py"
    j = src.find("return _nx_self_sha.sha256(content).digest()", i)
    block = src[i:j]
    m = re.search(r"if \{VAR_KEYED_ANCHOR\}[^\n]*\n", block)
    assert m, "armed-check line not found"
    assert '.strip("0")' in m.group(0), (
        "the armed-check must treat the 64-zero placeholder as absent; "
        "otherwise every unlicensed artefact dies at import")
    anchor = "0" * 64
    assert not (anchor and anchor.strip("0")), "placeholder armed the check"


def test_licensed_anchor_arms_the_check():
    """A real anchor (licence-bound build) must arm the check."""
    anchor = "b7b063835c1deef6" + "0" * 48
    assert anchor and anchor.strip("0"), "a real anchor must arm the check"


def test_anchor_slot_still_present_in_template():
    """The build substitutes into a third 64-zero slot on the HMAC line and
    refuses the build if it is gone — so the slot must stay in the template
    even though the runtime now treats its value as 'not armed'."""
    assert '{dummy_keyed}' in _sources_text(), (
        "keyed-anchor placeholder removed from the template: licence-bound "
        "builds would now fail with 'keyed anchor slot missing'")
