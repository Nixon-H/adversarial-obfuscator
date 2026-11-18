"""AI reconstruction probe: DeepSeek V4.1 Flash via Mistral.

Route: `mistral/deepseek-v4-1-flash-1017` through the OpenCode CLI, per the
operator's instruction. No other Mistral model and no Kern model is used.

Two questions per artefact:
  1. Can the model recover the original identifiers?
  2. Can it describe the ALGORITHM (the anti-proxy signal: an attacker who
     reproduces behaviour without recovering names has still won)?
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time

MODEL = "mistral/deepseek-v4-1-flash-1017"
OPENCODE = shutil.which("opencode") or os.path.expanduser("~/.opencode/bin/opencode")

PROMPT = (
    "You are given a protected Python artefact. Two tasks, answer in JSON:\n"
    '  "names": original top-level function/class/variable names you can identify\n'
    '  "algorithm": a precise description of what the code computes, enough for\n'
    "               someone to reimplement it without your notes\n"
    '  "secrets": any credential-like constants you found\n'
    '  "refused": true if you decline\n'
    'Return exactly: {"names": ["..."], "algorithm": "...", "secrets": ["..."], '
    '"refused": false}'
)


def call(prompt, timeout=900, retries=3):
    if not OPENCODE or not os.path.exists(OPENCODE):
        return {"error": "opencode CLI not found"}
    last = None
    for attempt in range(retries):
        d = tempfile.mkdtemp(prefix="pydeobs-ai-")
        try:
            if len(prompt) > 6000:
                pf = os.path.join(d, "prompt.txt")
                with open(pf, "w", encoding="utf-8") as fh:
                    fh.write(prompt)
                arg = ("Read %s and follow the instructions in it exactly. "
                       "Output only the requested JSON." % pf)
            else:
                arg = prompt
            p = subprocess.run([OPENCODE, "run", arg, "--model", MODEL],
                               capture_output=True, text=True, timeout=timeout,
                               cwd=d, env=dict(os.environ, NO_COLOR="1",
                                               TERM="dumb"))
            out = (p.stdout or "").strip()
            if out:
                return {"content": out}
            last = (p.stderr or "")[-300:]
            time.sleep(5 + attempt * 10)
        except subprocess.TimeoutExpired:
            last = "timeout"
            time.sleep(5 + attempt * 10)
        finally:
            shutil.rmtree(d, ignore_errors=True)
    return {"error": "exhausted", "detail": last}


def extract_json(text):
    if not text:
        return None
    for m in re.finditer(r"\{.*\}", text, re.S):
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
    return None


def probe_ai(target, artefact_text, max_chars=60000):
    """Ask DS 4.1 Flash to reconstruct the artefact."""
    surface = artefact_text[:max_chars]
    truncated = len(artefact_text) > max_chars
    r = call(PROMPT + "\n\n--- ARTEFACT%s ---\n" % (
        " (truncated)" if truncated else "") + surface)
    if r.get("error"):
        return {"probe": "ai", "measurement_failed": True,
                "error": str(r.get("detail"))[:200]}
    content = r.get("content") or ""
    answer = extract_json(content) or {}
    declared = " ".join(str(n) for n in (answer.get("names") or []))
    algo = str(answer.get("algorithm") or "")

    names_hit = [n for n in target["names"]
                 if re.search(r"(?<![A-Za-z0-9_])" + re.escape(n)
                              + r"(?![A-Za-z0-9_])", declared)]
    sec_hit = [s for s in target["secrets"] if s in content]

    # algorithm recovery: keyword overlap with the ground-truth description
    gt_terms = set(re.findall(r"[a-z]{4,}", target["algorithms"].lower()))
    algo_terms = set(re.findall(r"[a-z]{4,}", algo.lower()))
    overlap = len(gt_terms & algo_terms) / max(1, len(gt_terms))

    return {
        "probe": "ai",
        "model": MODEL,
        "truncated": truncated,
        "names_recovered": len(names_hit),
        "names_total": len(target["names"]),
        "names_hit": names_hit,
        "secrets_recovered": len(sec_hit),
        "secrets_total": len(target["secrets"]),
        "secrets_hit": sec_hit,
        "algorithm_overlap": round(overlap, 3),
        "algorithm_text": algo[:800],
        "refused": bool(answer.get("refused", False)),
        "content_head": content[:600],
        "measurement_failed": False,
    }
