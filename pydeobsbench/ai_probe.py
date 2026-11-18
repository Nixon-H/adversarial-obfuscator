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

    # PAYLOAD-algorithm recovery, with the loader's own vocabulary excluded.
    # Measured 2026-11-18: a naive keyword overlap scored 0.33-0.60 while the
    # model had recovered NOTHING of the payload -- it was describing the
    # loader (identity gate, self-check, string seal), whose vocabulary
    # overlaps generic crypto words like "sha", "hash", "key". Counting that
    # as algorithm recovery is exactly the proxy the review warned about, so
    # the loader terms are stripped before scoring.
    loader_vocab = set("""
        identity gate blocked main mp_main argv abspath file name exit
        self check integrity merkle hmac anchor token lines filtered
        constant expected value own source read traceback suppress
        excepthook limit stderr environment detections strict sandbox
        loader stub launcher self-extracting self-decrypting runtime
        packer obfuscator stub engine phase decrypt encrypted decrypt
        whole payload section sections sealed join stream moving buffer
        wipe zero memory key derived build id shares reconstruct xor
        base64 b64 lzma zlib compress envelope backend stream ython
    """.split())
    gt_terms = set(re.findall(r"[a-z0-9_]{4,}", target["algorithms"].lower()))
    algo_terms = set(re.findall(r"[a-z0-9_]{4,}", algo.lower()))

    # also require the specific numeric/structural markers of the payload
    markers = set(re.findall(r"0x[0-9A-Fa-f]{4,}|\b\d{3,}\b", target["algorithms"]))
    marker_hits = [m for m in markers if m.lower() in algo.lower()]

    # A hand-maintained blocklist cannot keep up with the loader's vocabulary.
    # Measured 2026-11-18 on `tiny`: overlap scored 0.75 while the model had
    # recovered NOTHING of the payload -- its whole answer was a line-accurate
    # description of the identity gate and the self-check.  `tiny`'s ground
    # truth is "SHA-256 over (salt || payload), first 16 hex chars", whose
    # words include generic English ("over", "first").  Three of them appear
    # in any description of the loader.  Same defect class as findings 5 and 6.
    #
    # Two guards, both honest:
    #   * generic English words are never evidence of payload recovery; a
    #     model that writes "over" and "first" has recovered nothing;
    #   * a ratio built on fewer than 4 distinctive terms is not reported at
    #     all.  A first attempt shrank the denominator to whatever still
    #     matched, which drove `tiny` from 0.75 to 1.00 -- a metric that
    #     improves when you understand less is worse than no metric.
    _STOPWORDS = set("""
        over first then than that this these those from with into onto
        once each only also just have has had been were was are can could
        will would should must may might shall does did doing done make
        makes made use uses used using gives give given take takes taken
        returns return called call calls writing write writes reads read
        before after while when where which whose what about above below
        both same other another more most less least very much many such
        some any all every either neither other others they them their
        there here where also then thus hence same else once
    """.split())
    payload_terms = {t for t in (gt_terms - loader_vocab)
                     if t not in _STOPWORDS and not t.isdigit()}
    _overlap_basis = sorted(payload_terms)
    if len(payload_terms) < 4:
        # Too few distinctive terms to divide by: report the fact, not a
        # number that will be read as a recovery rate.
        overlap = None
        _overlap_note = ("insufficient distinctive terms (%d: %s); "
                         "ratio not reported"
                         % (len(payload_terms), _overlap_basis))
    else:
        overlap = (len(payload_terms & (algo_terms - loader_vocab))
                   / len(payload_terms))
        _overlap_note = ""

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
        "algorithm_overlap": (round(overlap, 3)
                              if overlap is not None else None),
        "overlap_basis": _overlap_basis,
        "overlap_note": _overlap_note,
        "payload_markers_found": marker_hits,
        "loader_reversed": bool(re.search(
            r"identity gate|self[- ]check|self[- ]integrity", algo, re.I)),
        "algorithm_text": algo[:1200],
        "refused": bool(answer.get("refused", False)),
        "content_head": content[:600],
        "measurement_failed": False,
    }
