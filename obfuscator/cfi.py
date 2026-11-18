"""§1 control-flow integrity: execution must pass expected checkpoints in order.

The loader already verifies *content* (Merkle + HMAC) and *state* (pack
structure). Neither notices a change in **which code runs**: an attacker who
replaces a check with `pass`, or jumps past it, leaves every hash intact.

CFI here is a checkpoint chain. Each checkpoint folds a fixed tag into a
running digest; the final digest is compared against a value stamped at build
time, immediately before the payload is handed to the interpreter. A skipped,
duplicated or reordered checkpoint changes the chain and the loader dies before
`exec`.

Design constraints, and why each matters:

  * ONE source of truth for the tag sequence. The build computes the expected
    chain from ``CFI_TAGS``; the emitted code marks exactly those tags. If the
    two ever drift, every artefact fails to start -- so they are defined once
    here and both sides read the same tuple.
  * The expected value lives in its own slot, excluded from the file hash (the
    same treatment ``_NX_SELF_CK`` gets). A value cannot be part of what
    describes it.
  * The chain is seeded from the per-build HMAC key, so the expected value
    differs per build rather than being a constant an attacker can memorise
    from another artefact.
  * Marks sit on the COMMON path only. Native and fallback execution converge
    on the same three checkpoints, so one expected value covers both; a
    per-branch tag would require two values and two ways to be wrong.

HONEST LIMIT: an attacker who reads the file can see the tags and the expected
digest, and can therefore forge a chain that matches while skipping real work.
This raises the number of coordinated edits from one to several and catches
naive removal; it is not a wall. The §1 table says the same thing: these
mechanisms increase attack complexity, they do not guarantee anything.
"""
from __future__ import annotations

import hashlib

#: Bumped only when the tag set or the folding rule changes.
CFI_SCHEMA = "nx-cfi/v1"

#: The checkpoint sequence, in execution order. Common to both execution
#: paths by construction: `id` after the identity gate, `enter` at the top of
#: _load_native, `use` immediately before the payload is executed.
CFI_TAGS = ("id", "enter", "use")


def expected_chain(hmac_secret_hex: str, tags=CFI_TAGS,
                   schema: str = CFI_SCHEMA) -> str:
    """Return the digest the chain must hold after ``tags`` were marked.

    Pure function of the per-build key and the tag sequence, so the build can
    compute it without running anything.
    """
    chain = hashlib.sha256((schema + ":" + str(hmac_secret_hex)).encode()).digest()
    for tag in tags:
        chain = hashlib.sha256(chain + str(tag).encode("utf-8")).digest()
    return chain.hex()


def emit_snippet(slot_name: str = "_NX_CFI_SEQ",
                 tags=CFI_TAGS, schema: str = CFI_SCHEMA) -> str:
    """Return the runtime side: `_nx_cfi_mark` plus `_nx_cfi_verify`.

    Both are ordinary module-level functions. `_nx_cfi_verify` fails closed:
    a chain that does not match, or that was never started, kills the process
    through the loader's existing `_nx_self_fail` so the exit path and message
    format stay consistent with the other gates.
    """
    tag_list = ", ".join('"%s"' % t for t in tags)
    return r'''
# ── §1 control-flow integrity ────────────────────────────────────────────
_NX_CFI_SEED = None
_NX_CFI_STATE = None
_NX_CFI_MARKS = 0


def _nx_cfi_mark(_tag):
    """Fold one checkpoint tag into the running chain.

    Impure by design: the whole point is that the value depends on having
    executed. A mark that never runs leaves the chain short.
    """
    global _NX_CFI_STATE, _NX_CFI_MARKS
    try:
        import hashlib as _c_sh
        if _NX_CFI_STATE is None:
            _seed = (_NX_CFI_SEED or "") + _NX_SELF_HK
            _NX_CFI_STATE = _c_sh.sha256(
                ("__CFI_SCHEMA__:" + _seed).encode()).digest()
        _NX_CFI_STATE = _c_sh.sha256(
            _NX_CFI_STATE + str(_tag).encode("utf-8")).digest()
        _NX_CFI_MARKS += 1
    except Exception:
        # A mark that cannot run leaves the chain unmatchable, which the
        # verify step turns into a failure rather than a silent pass.
        _NX_CFI_STATE = None


def _nx_cfi_verify():
    """Kill the process unless every checkpoint was marked in order."""
    try:
        _want = globals().get("__CFI_SLOT__")
        if not _want or _NX_CFI_STATE is None:
            _nx_self_fail("control-flow: chain not established")
        if _NX_CFI_MARKS != __CFI_COUNT__:
            _nx_self_fail(
                "control-flow: %d checkpoints, expected %d"
                % (_NX_CFI_MARKS, __CFI_COUNT__))
        if _NX_CFI_STATE.hex() != str(_want):
            _nx_self_fail("control-flow: chain mismatch")
        return True
    except SystemExit:
        raise
    except Exception:
        _nx_self_fail("control-flow: verification error")
'''.replace("__CFI_SCHEMA__", schema) \
   .replace("__CFI_SLOT__", slot_name) \
   .replace("__CFI_COUNT__", str(len(tags))) \
   .replace('"""', '"""', 1)


def mark_call(tag: str) -> str:
    """Return the one-line call the loader template embeds for ``tag``."""
    return '_nx_cfi_mark("%s")\n' % tag
