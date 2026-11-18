"""Anti-patching redundancy probe (§1): does one patch defeat every gate?

The review's adaptive-attacker question: an attacker who can patch
conditional branches. The specific property to measure is *redundancy* -- if
neutralising ONE check disables all of them, the gates are decoration; if
independent checks keep firing, each patch has to be found and removed
separately, which is the cost the architecture is supposed to impose.

Method: for each known gate, produce a patched copy of the artefact that
disables only that gate, then run it and observe whether the payload still
executes. The probe reports, per gate, whether the artefact survived:

  * ``survived``  -- payload ran (that gate alone is not load-bearing), or
  * ``killed``    -- the artefact refused to run (another check caught it), or
  * ``unknown``   -- the patch did not apply / the run was inconclusive.

A gate that reports ``killed`` on its own is evidence of independence, which
is the property being claimed. This probe deliberately does NOT attempt to
defeat the gates: it measures whether they are independent of each other.

Safety: the target is executed with a list argv and no shell, and every
patch is applied to a COPY inside a fresh temp directory -- the shipped
artefact is never modified.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile

# Each entry: (gate name, compiled regex, replacement).
# The replacements are deliberately the minimal edit that disables ONE gate.
# Patterns are matched against the artefact as EMITTED, so they follow the
# real emitted names rather than a guessed convention: `constant_time_compare`
# is the self-check comparison in the shipped loader (verified by grepping a
# built artefact, 2026-11-18), and the trial gate only exists when a trial
# was requested -- on an untimed build `_NX_TRIAL_SECONDS` is None and there
# is no `if` to patch, which the probe reports as "unknown" rather than
# pretending the gate was tested.
_GATE_PATCHES = (
    ("identity-gate",
     re.compile(r'if\s+__name__\s+not\s+in\s+\(\s*"__main__"\s*,\s*'
                r'"__mp_main__"\s*\)\s*:'),
     "if False:"),
    ("self-check-call",
     # Replace the CALL with a no-op that preserves indentation. An earlier
     # version substituted "    pass  # ..." and the resulting IndentationError
     # made every artefact look "killed" -- a false positive: the run died from
     # a syntax error, not from another gate catching the patch. That would
     # have inflated the redundancy result, so the replacement is indented to
     # the matched line and uses the same leading whitespace.
     re.compile(r"^([ \t]*)_nx_self_check\(\)[ \t]*$", re.M),
     r"\1pass  # self-check call removed"),
    ("self-check-compare",
     # The argument list contains nested calls (`root.encode()`), so `[^)]*`
     # cannot match it -- measured: the pattern silently found nothing and the
     # gate was reported "unknown" while the gate was plainly there.
     re.compile(r"if\s+not\s+constant_time_compare\(.*?\)\s*:",
                re.S),
     "if False:"),
    ("trial-gate",
     re.compile(r'if\s+_NX_TRIAL_SECONDS\s+and\s+[^:]+:'),
     "if False:"),
)


def _validated(path):
    if not path:
        raise ValueError("artefact path required")
    full = os.path.realpath(os.path.abspath(path))
    if not os.path.isfile(full):
        raise ValueError("not a regular file: %r" % (path,))
    return full


def _run(copy_path, timeout=120):
    """Run one patched copy; return (returncode, combined output)."""
    try:
        p = subprocess.run([sys.executable, copy_path],
                           cwd=os.path.dirname(copy_path),
                           capture_output=True, text=True, timeout=timeout,
                           env=dict(os.environ, NIXON_LOG_REDIRECT="0"),
                           shell=False)
    except subprocess.TimeoutExpired:
        return None, "timeout"
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def probe_patch_redundancy(artefact_path, baseline_marker=None,
                           timeout=120):
    """Patch each gate in turn and record whether the artefact still runs.

    ``baseline_marker``: a substring that appears in stdout when the payload
    executes (e.g. the target's own output token). When None, survival is
    judged by returncode == 0.
    """
    try:
        full = _validated(artefact_path)
    except ValueError as exc:
        return {"probe": "patch_redundancy", "applicable": False,
                "error": str(exc)}

    with open(full, encoding="utf-8", errors="surrogateescape") as fh:
        base_text = fh.read()

    workdir = tempfile.mkdtemp(prefix="nx-patch-")
    results = []
    try:
        # Control: the unmodified copy must run, or every later result is
        # meaningless (a broken build would look "killed" for every gate).
        control = os.path.join(workdir, "control.py")
        with open(control, "w", encoding="utf-8",
                  errors="surrogateescape") as fh:
            fh.write(base_text)
        rc, out = _run(control, timeout)
        control_ok = (rc == 0)
        if baseline_marker is not None:
            control_ok = control_ok and (baseline_marker in out)
        results.append({"gate": "control", "outcome":
                        "survived" if control_ok else "killed",
                        "returncode": rc})
        if not control_ok:
            return {"probe": "patch_redundancy", "applicable": True,
                    "control_ok": False,
                    "note": "control did not run; patch results would be "
                            "meaningless, so none were taken",
                    "results": results}

        for name, pattern, replacement in _GATE_PATCHES:
            hits = pattern.findall(base_text)
            if not hits:
                results.append({"gate": name, "outcome": "unknown",
                                "note": "gate pattern not present"})
                continue
            patched = pattern.sub(replacement, base_text, count=1)
            if patched == base_text:
                results.append({"gate": name, "outcome": "unknown",
                                "note": "patch produced no change"})
                continue
            path = os.path.join(workdir, "p_%s.py" % name.replace("-", "_"))
            with open(path, "w", encoding="utf-8",
                      errors="surrogateescape") as fh:
                fh.write(patched)
            rc, out = _run(path, timeout)
            survived = (rc == 0)
            if baseline_marker is not None:
                survived = survived and (baseline_marker in out)
            results.append({
                "gate": name,
                "outcome": "survived" if survived else "killed",
                "returncode": rc,
                "tail": out.strip()[-160:].replace("\n", " "),
            })
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    killed = [r for r in results
              if r["outcome"] == "killed" and r["gate"] != "control"]
    survived = [r for r in results
                if r["outcome"] == "survived" and r["gate"] != "control"]
    return {
        "probe": "patch_redundancy",
        "applicable": True,
        "control_ok": True,
        "gates_tested": len(results) - 1,
        "independent_kills": [r["gate"] for r in killed],
        "single_patch_bypasses": [r["gate"] for r in survived],
        "results": results,
        "reading": (
            "a gate in single_patch_bypasses means disabling it ALONE let the "
            "payload run, so that gate is not independently enforced; a gate "
            "in independent_kills means another check still killed the run."),
    }
