"""§1 anti-patching redundancy, measured rather than asserted.

The property the architecture claims is that neutralising one gate does not
disable the others. These tests pin the probe that measures it, using a
synthetic artefact whose gates are known -- so a change in the probe itself is
caught without needing a 30-second real build.

Note on scope: this does NOT prove the gates are unbypassable. It proves they
are *independent*, which is the specific claim ("one patched check must not
disable all checks"). An attacker who patches every gate still wins; that is
the irreducible client-side boundary and is stated as such in the report.
"""
import os
import sys
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pydeobsbench.patch_probe import probe_patch_redundancy  # noqa: E402

# A stand-in that models the REAL mechanism: the self-check HASHES ITS OWN
# FILE, so any patch is detected by the hash rather than by comparing a
# constant that a patch would leave untouched. This is what makes the gates
# independent -- editing one trips the other. Mirrors measured behaviour on a
# shipped artefact (2026-11-18): patching the merkle comparison produced an
# HMAC failure, i.e. a second anchor over the same content.
#
# The expected hash is stamped at test time by `_stamp()`.
SYNTH = textwrap.dedent('''
    import hashlib, hmac, sys

    _NX_SELF_CK = "__STAMP__"
    # A SECOND, independent anchor with its OWN key material, exactly as the
    # shipped loader carries (merkle root + keyed HMAC over the same content).
    # Without a second net, removing the self-check CALL leaves nothing behind
    # to notice -- measured: a single-anchor fixture let the payload run with
    # the whole check deleted, while the real artefact died (rc 1).
    # Its expected tag is __TAG__, stamped alongside the merkle root.
    _NX_SELF_HK = b"anchor-key"
    _NX_SELF_HM = "__TAG__"

    def constant_time_compare(a, b):
        return a == b

    def _nx_body_lines():
        with open(__file__, "rb") as fh:
            data = fh.read()
        # Filter by VALUE, as the shipped loader does.
        return [ln for ln in data.split(b"\\n")
                if _NX_SELF_CK.encode() not in ln
                and _NX_SELF_HM.encode() not in ln]

    def _nx_self_check():
        body = b"\\n".join(_nx_body_lines())
        merkle = hashlib.sha256(body).hexdigest()
        if not constant_time_compare(merkle, _NX_SELF_CK):
            sys.stderr.write("Self-check error: merkle\\n")
            sys.exit(137)
        tag = hmac.new(_NX_SELF_HK, body, hashlib.sha256).hexdigest()
        if not constant_time_compare(tag, _NX_SELF_HM):
            sys.stderr.write("Self-check error: hmac\\n")
            sys.exit(137)

    if __name__ not in ("__main__", "__mp_main__"):
        sys.stderr.write("BLOCKED identity\\n")
        sys.exit(2)

    _nx_self_check()
    print("PAYLOAD-RAN")
''')


def _stamp(body):
    """Fill __STAMP__ (merkle) and __TAG__ (keyed HMAC) as the file is written.

    Both are computed over the same value-filtered body the runtime checks, so
    the stamp and the check agree; otherwise the control cannot even run and
    every patch result would be meaningless.
    """
    import hashlib
    import hmac

    stamp = "0" * 64
    tag = "0" * 64
    probe = body.replace("__STAMP__", stamp).replace("__TAG__", tag)
    lines = [ln for ln in probe.encode().split(b"\n")
             if stamp.encode() not in ln and tag.encode() not in ln]
    body_bytes = b"\n".join(lines)
    digest = hashlib.sha256(body_bytes).hexdigest()
    tagval = hmac.new(b"anchor-key", body_bytes, hashlib.sha256).hexdigest()
    return body.replace("__STAMP__", digest).replace("__TAG__", tagval)


def _write(tmp_path, body):
    p = tmp_path / "art.py"
    p.write_text(_stamp(body), encoding="utf-8")
    return str(p)


def test_control_runs_and_payload_marker_present(tmp_path):
    art = _write(tmp_path, SYNTH)
    r = probe_patch_redundancy(art, baseline_marker="PAYLOAD-RAN")
    assert r["control_ok"] is True, r["results"]


def test_no_single_patch_bypasses_both_gates(tmp_path):
    """Patching one gate must still be caught by the other."""
    art = _write(tmp_path, SYNTH)
    r = probe_patch_redundancy(art, baseline_marker="PAYLOAD-RAN")
    assert r["single_patch_bypasses"] == [], (
        "a single patch let the payload run: %r"
        % (r["single_patch_bypasses"],))


def test_probe_reports_absent_gate_as_unknown_not_killed(tmp_path):
    """An absent gate must not be scored as enforced.

    A gate the build never emitted cannot have been 'killed' -- reporting it
    as such would inflate the redundancy result.
    """
    art = _write(tmp_path, 'print("PAYLOAD-RAN")\n')
    r = probe_patch_redundancy(art, baseline_marker="PAYLOAD-RAN")
    outcomes = {x["gate"]: x["outcome"] for x in r["results"]}
    assert outcomes.get("identity-gate") == "unknown", outcomes
    assert r["independent_kills"] == [], outcomes


def test_broken_control_invalidates_the_measurement(tmp_path):
    """If the unmodified artefact does not run, no patch results are taken."""
    art = _write(tmp_path, 'raise SystemExit(9)\n')
    r = probe_patch_redundancy(art, baseline_marker="PAYLOAD-RAN")
    assert r["control_ok"] is False
    assert len(r["results"]) == 1, "probe took patch results from a dead control"
