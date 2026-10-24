# -*- coding: utf-8 -*-
"""Per-build names for the loader's fixed runtime markers.

Every build used to ship the same identifier vocabulary.  An analyst who
never ran anything could therefore locate, in any artifact:

* ``_nx_kill`` -- the single choke point every enforcement gate funnels
  through, i.e. the exact function to patch, stub or trace;
* ``_NX_AUDIT_WRAPPED`` / ``_NX_AUDIT_ADDED`` / ``_NX_AUDIT_SEEN`` /
  ``_NX_AUDIT_T0`` / ``_NX_AUDIT_BASE_MEAN`` / ``_NX_AUDIT_WRAPPER_ID`` /
  ``_NX_AUDIT_OPT_OUT`` -- the audit-hook state, which names the observer
  and lets a reader check whether the plant succeeded without running it;
* ``_nx_addaudithook`` / ``_nx_audit_verify`` / ``_nx_audit_baseline`` --
  the wrapper and the periodic re-check entry points.

Those names are replaced once per build, on the assembled loader source,
immediately before the string pass.  Doing it in one place is deliberate:

* the emitters in :mod:`obfuscator.kill_ladder`, :mod:`obfuscator.audit_hook`
  and the gate snippets keep their readable names, so their unit tests keep
  asserting on ``_nx_kill`` and the code stays greppable *in the repo*;
* there is exactly one substitution table, so a partial rename (which would
  produce ``NameError`` at runtime instead of exit 137) is impossible.

Replacement covers both identifier uses and the handful of
``globals().get("<name>")`` string literals, because it is a plain
name-boundary regex over the source text, not an AST pass.

The token is ASCII and underscore-prefixed: underscore so the renamer's
guard leaves the names alone, ASCII so nothing downstream (string tables,
``repr``, bytecode) has to cope with a non-ASCII identifier.
"""
import re
import secrets

#: The kill ladder name.  Kept out of :data:`_RENAMED` because callers
#: need to address it directly (see :func:`kill_name`).
KILL_MARKER = "_nx_kill"

#: Fixed marker -> short suffix for the per-build replacement.  Suffixes are
#: distinct so two markers can never collapse onto the same build name.
_RENAMED = (
    # audit-hook closure / module state
    ("_nx_orig_addaudithook", "oah"),
    ("_nx_addaudithook", "ah"),
    ("_nx_is_site_path", "isp"),
    ("_nx_audit_canary", "ac"),
    ("_nx_audit_baseline", "abl"),
    ("_nx_audit_verify", "av"),
    ("_nx_entry_file", "ef"),
    # audit-hook globals (persisted across calls, read by the canary and
    # by the periodic re-check)
    ("_NX_AUDIT_OPT_OUT", "AO"),
    ("_NX_AUDIT_WRAPPED", "AW"),
    ("_NX_AUDIT_ADDED", "AD"),
    ("_NX_AUDIT_WRAPPER_ID", "AI"),
    ("_NX_AUDIT_SEEN", "AS"),
    ("_NX_AUDIT_T0", "AT"),
    ("_NX_AUDIT_BASE_MEAN", "AM"),
)


def new_token():
    # type: () -> str
    """Return a fresh per-build token (10 hex chars, no leading underscore)."""
    return secrets.token_hex(5)


def kill_name(token):
    # type: (str) -> str
    """Return the per-build name of the kill ladder entry point."""
    return "_%s_k" % (token,)


def marker_map(token):
    # type: (str) -> dict
    """Return ``{fixed_name: build_name}`` for one build token."""
    mapping = {KILL_MARKER: kill_name(token)}
    for fixed, suffix in _RENAMED:
        mapping[fixed] = "_%s_%s" % (token, suffix)
    return mapping


def _pattern(mapping):
    # Longest first so a shorter key can never pre-empt a longer one; the
    # lookarounds are name boundaries, which is what keeps ``_nx_kill`` from
    # matching inside ``_nx_killer`` while still matching the quoted
    # ``'_nx_kill'`` form used by ``globals().get``.
    keys = sorted(mapping, key=len, reverse=True)
    return re.compile(r"(?<!\w)(?:%s)(?!\w)"
                      % "|".join(re.escape(k) for k in keys))


def rename_markers(script, token):
    # type: (str, str) -> str
    """Rewrite every fixed marker in *script* to its per-build name.

    Non-string input is returned unchanged; an empty token is a programming
    error and raises rather than silently disabling the hardening.
    """
    if not isinstance(script, str) or not script:
        return script
    if not isinstance(token, str) or not token:
        raise ValueError("marker token must be a non-empty string")
    mapping = marker_map(token)
    return _pattern(mapping).sub(lambda m: mapping[m.group(0)], script)


def leftover_markers(script, token):
    # type: (str, str) -> list
    """Return the fixed markers still present in *script* (should be empty)."""
    if not isinstance(script, str) or not script:
        return []
    mapping = marker_map(token)
    pat = _pattern(mapping)
    return sorted({m.group(0) for m in pat.finditer(script)})


def assert_markers_renamed(script, token):
    # type: (str, str) -> None
    """Fail the build if any fixed marker survived the rename."""
    left = leftover_markers(script, token)
    if left:
        raise RuntimeError(
            "marker rename incomplete; still shipping fixed names %r -- "
            "a partial rename can leave a name defined under one spelling "
            "and called under another" % (left,))


def assert_kill_wired(script, token):
    # type: (str, str) -> None
    """Fail the build when a gate calls the ladder that was never defined.

    That state is invisible at build time and fatal at run time: the gate
    raises ``NameError`` instead of exiting 137, so a tampered artifact
    keeps running.  ``emit_kill_snippet`` is emitted inside a best-effort
    ``try`` in the pipeline, which is exactly how such a build could ship.
    """
    if not isinstance(script, str) or not script:
        return
    name = kill_name(token)
    esc = re.escape(name)
    calls = len(re.findall(r"(?<![\w.])%s\s*\(" % esc, script))
    defs = len(re.findall(r"def\s+%s\s*\(" % esc, script))
    if calls and not defs:
        raise RuntimeError(
            "kill ladder referenced but never defined: %d call site(s) for "
            "%r and no 'def %s(' in the assembled loader; every gate would "
            "raise NameError instead of exiting 137"
            % (calls, name, name))
