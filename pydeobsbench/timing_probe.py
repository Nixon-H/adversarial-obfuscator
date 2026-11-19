"""Time to successful recovery (§8): wall-clock from handoff to correct answer.

The review's point: *"time to successful recovery — actual attacker effort"*
is the metric to optimise, and it was the one thing this harness never
measured. Every other number here is a rate; this one is a cost.

Definition used, stated up front so the number cannot be re-interpreted later:

  **time_to_recovery_s** = seconds from the moment the artefact text is handed
  to the model, to the moment its answer contains a CORRECT algorithm
  description. If no answer is correct within the budget, the metric is
  ``None`` — not a large number, and not zero.

"Correct" is deliberately narrow. A description counts only when it contains at
least `min_markers` *distinctive* markers from the target's ground truth:
numeric constants (``0x7FEB352D``) and content words that are neither generic
English nor loader vocabulary. Term overlap on its own was already shown to
produce false positives here (§5 finding 18: `tiny` scored 0.75 from a
pure-loader answer), so this probe reuses that lesson rather than repeating it.

A target with too few distinctive markers is reported as
``measurable: False`` with its basis, instead of a ratio that would be read as
recovery.

Attacker-cost accounting: the clock includes the CLI's own start-up and any
retries the model client performs, because an attacker pays those too. It
excludes only the harness's file reads before handoff.

Run standalone:
    python3 -I -m pydeobsbench.timing_probe --target cipher --artefact PATH
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time

from . import ai_probe as _ai

# Generic English + loader vocabulary: neither is evidence of payload recovery.
_NON_EVIDENCE = set("""
    over first then than that this these those from with into onto once each
    only also just have has had been were was are can could will would should
    must may might shall does did doing done make makes made use uses used
    using gives give given take takes taken returns return called call calls
    writing write writes reads read before after while when where which whose
    what about above below both same other another more most less least very
    much many such some any all every either neither they them their there
    here thus hence else payload salt chars sha string bytes
    identity gate blocked main mp_main argv abspath file name exit self check
    integrity merkle hmac anchor token lines filtered constant expected value
    own source read traceback suppress excepthook limit stderr environment
    detections strict sandbox loader stub launcher runtime packer obfuscator
    engine phase decrypt encrypted whole section sections sealed join stream
    moving buffer wipe zero memory key derived build id shares reconstruct xor
    base64 b64 lzma zlib compress envelope backend
""".split())

_WORD = re.compile(r"[a-z0-9_]{4,}")


#: Words that appear in ANY description of a loader, or of crypto in general.
#: They cannot serve as evidence of PAYLOAD recovery, for the same reason the
#: loader blocklist cannot: they are legitimately part of the payload's
#: algorithm too, which is what makes them useless as evidence.
#:
#: Measured 2026-11-19: `tiny`'s marker set had 14 entries of which 7 were
#: generic (`sha256`, `hexdigest`, `concatenate`, `encoded`, `literal`,
#: `module`, `prints`). A model that answered "this is a self-decrypting
#: loader; the payload and key material were stripped, only the guard machinery
#: is recoverable" hit all seven and scored correct: True — a false positive of
#: exactly the kind §5 finding 18 documented for the rate metric.
_GENERIC = set("""
    sha sha1 sha256 sha512 md5 hash hashing digest hexdigest hex
    concatenate concatenation concat encoded encoding encode decode
    literal literals string strings bytes byte character characters
    module modules function functions variable constant value values
    integer int float number numbers salt salting key keys secret secrets
    sign signing signed call calls print prints output input data file files
    array list dict map object class method loop loops iterate iteration
    round rounds step steps return returns store stored read reads write writes
    leading followed marker
""".split())


def distinctive_markers(target):
    """Return the ground-truth markers that can serve as correctness evidence.

    Numbers are strong evidence (a recovered ``0x7FEB352D`` is not a guess);
    content words are weaker and acceptable only when specific. Words any
    loader or crypto description contains are excluded, because a model
    describing the WRAPPER would otherwise score as having recovered the
    PAYLOAD — measured, and exactly the proxy the review warns about.
    """
    algo = str(target.get("algorithms", ""))
    numbers = sorted({m.lower()
                      for m in re.findall(r"0x[0-9A-Fa-f]{4,}", algo)})
    words = sorted({w for w in _WORD.findall(algo.lower())
                    if w not in _NON_EVIDENCE and w not in _GENERIC
                    and not w.isdigit() and len(w) >= 5})
    return numbers, words


def evaluate_answer(target, answer_text, min_markers=2):
    """Is this answer a correct algorithm description? Returns a verdict dict."""
    numbers, words = distinctive_markers(target)
    text = (answer_text or "").lower()
    hit_numbers = [n for n in numbers if n in text]
    hit_words = [w for w in words if re.search(
        r"(?<![a-z0-9_])" + re.escape(w) + r"(?![a-z0-9_])", text)]
    hits = hit_numbers + hit_words
    total = len(numbers) + len(words)
    measurable = total >= max(4, min_markers)
    return {
        "measurable": measurable,
        "markers_total": total,
        "markers_numbers": numbers,
        "markers_words": words,
        "hit_numbers": hit_numbers,
        "hit_words": hit_words,
        "hits": len(hits),
        "min_markers": min_markers,
        "correct": bool(measurable and len(hits) >= min_markers),
        "basis": (numbers + words)[:12],
    }


def time_to_recovery(target, artefact_text, max_chars=60000, budget_s=900):
    """Measure wall-clock from artefact handoff to a correct algorithm answer.

    Returns a structured result. `time_to_recovery_s` is None when the model
    never produced a correct description inside the budget -- that is the
    honest representation of "not recovered", and it is different from a very
    large number.
    """
    surface = artefact_text[:max_chars]
    truncated = len(artefact_text) > max_chars
    prompt = (_ai.PROMPT + "\n\n--- ARTEFACT%s ---\n"
              % (" (truncated)" if truncated else "") + surface)

    started = time.perf_counter()
    raw = _ai.call(prompt, timeout=budget_s)
    elapsed = time.perf_counter() - started

    if raw.get("error"):
        return {
            "probe": "time_to_recovery",
            "model": _ai.MODEL,
            "measured": False,
            "time_to_recovery_s": None,
            "elapsed_s": round(elapsed, 3),
            "error": str(raw.get("detail") or raw.get("error"))[:200],
            "note": "model call failed; NOT a recovery measurement",
        }

    content = raw.get("content") or ""
    answer = _ai.extract_json(content) or {}
    algorithm_text = str(answer.get("algorithm") or "")
    verdict = evaluate_answer(target, algorithm_text or content)

    return {
        "probe": "time_to_recovery",
        "model": _ai.MODEL,
        "measured": True,
        "truncated": truncated,
        "elapsed_s": round(elapsed, 3),
        "time_to_recovery_s": (round(elapsed, 3) if verdict["correct"]
                               else None),
        "verdict": verdict,
        "algorithm_text": algorithm_text[:800],
        "note": ("" if verdict["measurable"] else
                 "too few distinctive ground-truth markers to judge; "
                 "time_to_recovery is not reported"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pydeobsbench.timing_probe")
    ap.add_argument("--target", required=True)
    ap.add_argument("--artefact", required=True)
    ap.add_argument("--budget", type=int, default=900)
    args = ap.parse_args(argv)

    from . import targets as T
    target = T.TARGETS[args.target]
    with open(args.artefact, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    result = time_to_recovery(target, text, budget_s=args.budget)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
