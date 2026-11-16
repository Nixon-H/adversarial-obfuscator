"""Post-build mini-attack: score a fresh artefact, feed the result back.

The layer selector (``bench_layers``) ranks layers from *historical* campaign
data.  This module closes the loop: after a build, it runs a small attack
against the artefact just produced, records the result in the same campaign
JSON shape, and re-ranks.  A build therefore scores itself, and the next
build's recommendation is based on measurements that include it.

Design:

* **Local by default.**  The default attacker is a deterministic static
  probe (no network, no model): it greps for the ground-truth names, the
  payload's distinctive constants and any plaintext markers.  That is enough
  to catch the regressions that matter (a leak that reappears) and costs
  milliseconds.
* **Optional model attack.**  With ``--model`` and ``KERN_API_KEY`` set it
  delegates to the existing ``kern_agent_bench`` harness, so the same code
  path produces both cheap and expensive cells.
* **Same cell shape as the campaigns**, so ``bench_layers`` consumes the
  result without special-casing.
* **Never fails the build.**  A scoring run that errors records an error
  cell; it does not turn a good build into a failed one.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Iterable, Optional

#: Names a payload is expected to hide.  The caller supplies the real list;
#: this is the fallback used by the CLI when none is given.
DEFAULT_NAMES = (
    "Descriptor", "Holder", "Point", "cached", "slow_square", "evens",
    "classify", "walrus_count", "eg_sum", "make_counter", "deliver", "main",
)


@dataclass
class AttackCell:
    """One measurement, in the shape the campaigns use."""

    arm: str
    model: str
    recall: float
    cracked: bool
    names_recovered: list = field(default_factory=list)
    surface_chars: int = 0
    secrets_reported: list = field(default_factory=list)
    status: str = "ok"
    error: str = ""

    def as_dict(self) -> dict:
        return {
            "arm": self.arm,
            "model": self.model,
            "recall": round(self.recall, 4),
            "cracked": self.cracked,
            "names_recovered": list(self.names_recovered),
            "surface_chars": self.surface_chars,
            "secrets_reported": list(self.secrets_reported),
            "status": self.status,
            "error": self.error,
        }


def _read_text(path: str, limit: int = 40 * 1024 * 1024) -> str:
    try:
        with open(path, "rb") as handle:
            return handle.read(limit).decode("utf-8", errors="replace")
    except OSError:
        return ""


def static_probe(artifact: str, names: Iterable[str],
                 markers: Iterable[str] = ()) -> AttackCell:
    """Deterministic local attack: what can a reader see without running it?

    This is the cheap gate.  It answers "did the build leak the names or the
    payload text", which is exactly the class of regression that cost this
    project its symbol table twice.
    """
    started = time.perf_counter()
    text = _read_text(artifact)
    surface = len(text)
    found = [n for n in names if re.search(r"\b%s\b" % re.escape(n), text)]
    leaked_markers = [m for m in markers if m and m in text]
    recall = (len(found) / len(list(names))) if names else 0.0
    cell = AttackCell(
        arm="static_probe",
        model="local-static",
        recall=recall,
        cracked=bool(found) or bool(leaked_markers),
        names_recovered=found,
        surface_chars=surface,
        secrets_reported=leaked_markers,
    )
    cell.error = ""
    _ = time.perf_counter() - started
    return cell


def model_probe(artifact: str, names: Iterable[str],
                model: Optional[str] = None,
                timeout: int = 900) -> AttackCell:
    """Delegate to the existing Kern harness (needs KERN_API_KEY)."""
    if not os.environ.get("KERN_API_KEY"):
        return AttackCell(arm="model_probe", model="unavailable", recall=0.0,
                          cracked=False, status="error",
                          error="KERN_API_KEY is not set")
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    harness = os.path.join(root, "scripts", "benchmark", "kern_agent_bench.py")
    if not os.path.isfile(harness):
        return AttackCell(arm="model_probe", model="unavailable", recall=0.0,
                          cracked=False, status="error",
                          error="kern_agent_bench.py not found")
    cmd = [sys.executable, harness, "--artifact", artifact,
           "--condition", "neutral"]
    if model:
        cmd += ["--model", model]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        return AttackCell(arm="model_probe", model=model or "kern",
                          recall=0.0, cracked=False, status="error",
                          error="harness timed out")
    if proc.returncode != 0:
        return AttackCell(arm="model_probe", model=model or "kern",
                          recall=0.0, cracked=False, status="error",
                          error=(proc.stderr or "")[-300:])
    try:
        doc = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return AttackCell(arm="model_probe", model=model or "kern",
                          recall=0.0, cracked=False, status="error",
                          error="harness output was not JSON")
    recovered = doc.get("names", []) or []
    wanted = list(names)
    hits = [n for n in recovered if n in wanted]
    return AttackCell(
        arm="model_probe",
        model=str(doc.get("model") or model or "kern"),
        recall=(len(hits) / len(wanted)) if wanted else 0.0,
        cracked=bool(hits),
        names_recovered=hits,
        surface_chars=len(_read_text(artifact)),
        secrets_reported=list(doc.get("secrets", []) or []),
    )


def score_artifact(artifact: str, names: Iterable[str] = DEFAULT_NAMES,
                   markers: Iterable[str] = (), *,
                   model: Optional[str] = None,
                   out: Optional[str] = None) -> dict:
    """Run the mini-attack and (optionally) append it to a campaign file.

    Returns ``{"cells": [...], "artifact": ..., "sha256": ..., "when": ...}``.
    """
    names = list(names)
    cells = [static_probe(artifact, names, markers)]
    if model:
        cells.append(model_probe(artifact, names, model=model))
    digest = ""
    try:
        with open(artifact, "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        pass
    report = {
        "artifact": artifact,
        "sha256": digest,
        "when": int(time.time()),
        "cells": [c.as_dict() for c in cells],
    }
    if out:
        _append_campaign(out, report)
    return report


def _append_campaign(path: str, report: dict) -> None:
    """Append the cells to a campaign file, preserving any existing ones."""
    doc = {"cells": []}
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as handle:
                doc = json.load(handle)
            if not isinstance(doc, dict):
                doc = {"cells": []}
        except (OSError, ValueError):
            doc = {"cells": []}
    doc.setdefault("cells", []).extend(report["cells"])
    doc.setdefault("source", "post-build mini-attack")
    doc["updated"] = report["when"]
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(doc, handle, indent=2)
    except OSError:
        pass


def main(argv: Optional[list] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python3 -m obfuscator.post_build_attack",
        description="Score a freshly built artefact with a mini-attack and "
                    "append the result to the campaign data.")
    parser.add_argument("artifact", help="the built artefact")
    parser.add_argument("--names", default="",
                        help="comma-separated ground-truth names")
    parser.add_argument("--markers", default="",
                        help="comma-separated plaintext markers that must "
                             "not appear")
    parser.add_argument("--model", default="",
                        help="also run the model attack (needs KERN_API_KEY)")
    parser.add_argument("--out", default="",
                        help="campaign JSON to append the cells to")
    parser.add_argument("--json", action="store_true")
    opts = parser.parse_args(argv)

    names = ([n.strip() for n in opts.names.split(",") if n.strip()]
             or list(DEFAULT_NAMES))
    markers = [m.strip() for m in opts.markers.split(",") if m.strip()]
    report = score_artifact(opts.artifact, names, markers,
                            model=opts.model or None,
                            out=opts.out or None)
    if opts.json:
        print(json.dumps(report, indent=2))
    else:
        for cell in report["cells"]:
            print("%-14s recall=%.2f cracked=%s names=%d"
                  % (cell["arm"], cell["recall"], cell["cracked"],
                     len(cell["names_recovered"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
