"""AI-layer protection benchmark: per-layer ablation, refusal-aware.

Fresh benchmark (2026-11-11). It does **not** reuse the older AI-resistance
sweep. It measures a specific, reproducible question:

  When an analyst model sees one protected Python artefact, how many original
  top-level symbols can it recover, does it recover the program purpose, and
  does it refuse — under a neutral prompt and under an authorized-author prompt?

Design:

  * Arms are **layer ablations**, not vendor presets. Each arm turns on one
    family of transforms and turns every other default off, so the measured
    delta is attributable to that layer.
  * Every build uses the same seed, so artefact differences come from the
    layer, not RNG drift.
  * Every arm is scored against the same ground truth with the same evaluator.
  * Two prompt conditions are run per arm: ``neutral`` and ``authorized``.
    The second states that the artefact belongs to the requester. That
    separates "the model cannot recover it" from "the model declines".
  * The packed loader is optional and off by default: it is a different
    artefact class (encrypted blob + loader), so it is reported separately
    rather than averaged with source-level arms.

This is a benchmark harness, not a novelty claim. Related work is listed in
``docs/AI_LAYER_BENCHMARK.md``.

Usage::

    OPENROUTER_API_KEY=... python3 scripts/benchmark/ai_layer_bench.py \\
        --models nvidia/nemotron-3-ultra-550b-a55b:free \\
        --out-dir docs/research/ai-layer-bench-2026-11-11

Without ``OPENROUTER_API_KEY`` the script still builds arms and computes
static metrics; LLM cells are recorded as ``skipped``.
"""

from __future__ import annotations

import argparse
import ast
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from obfuscator.core.pipeline import ObfuscationTransformer  # noqa: E402
from obfuscator.lowering import emit_shim_import, lower_source, resolve_families  # noqa: E402

DEFAULT_PAYLOAD = ROOT / "tests" / "fixtures" / "portable" / "constructs_source.py"

GROUND_TRUTH = [
    "Descriptor", "Holder", "Point", "cached", "slow_square", "evens",
    "classify", "walrus_count", "eg_sum", "make_counter", "deliver", "main",
]

PURPOSE_MARKERS = [
    "dataclass", "match", "async", "generator", "descriptor", "closure",
    "walrus", "decorator", "cache",
]

REFUSAL_MARKERS = [
    "i can't help", "i cannot help", "i can’t help", "i won’t", "i will not",
    "i'm unable", "i am unable", "cannot assist", "can't assist",
    "can't help with", "cannot help with", "i'm sorry", "i am sorry",
    "against my policy", "not able to help", "unable to comply",
]

# Every transformer default that is not part of the arm under test is pinned
# off, so the measured delta is attributable to the selected layer.
ALL_OFF = {
    "cfg_flatten": False,
    "opaque_predicates": False,
    "bogus_exceptions": False,
    "mba_subs": False,
    "fragment_strings": False,
    "unicode_ids": False,
    "symbol_rename": False,
    "strip_meta": False,
    "split_vars": False,
    "unfold_constants": False,
    "enhanced_junk": False,
    "break_decompiler": False,
    "dynamic_code": False,
    "code_checksums": False,
    "obf_calls": False,
    "exception_flow": False,
    "attention_poison": False,
    "decoy_apis": False,
    "adaptive_rewrite": False,
    "residue_random": False,
}

ARMS = {
    "raw": {"desc": "untransformed payload (control)"},
    "lex": {
        "desc": "symbol rename + unicode identifiers + metadata strip",
        "options": {"symbol_rename": True, "unicode_ids": True, "strip_meta": True},
    },
    "cfg": {
        "desc": "control-flow flattening + opaque predicates + bogus exceptions + exception flow",
        "options": {
            "cfg_flatten": True, "opaque_predicates": True,
            "bogus_exceptions": True, "exception_flow": True,
        },
    },
    "data": {
        "desc": "string encryption/fragmentation + value splitting + constant unfolding",
        "options": {
            "fragment_strings": True, "split_vars": True, "unfold_constants": True,
        },
    },
    "anti_rea": {
        "desc": "counter-REA shields only (BLA port, maximum intensity)",
        "anti_rea": True, "anti_rea_level": "maximum",
    },
    "decoy": {
        "desc": "decoy APIs + attention poison",
        "options": {"decoy_apis": True, "attention_poison": True,
                    "attention_poison_fan_out": 6},
    },
    "lowering": {
        "desc": "semantic lowering to native-kernel call sites",
        "lowering": "all",
    },
    "full_source": {
        "desc": "O4-equivalent AST stack + maximum counter-REA + decoys + lowering",
        "options": {
            "cfg_flatten": True, "opaque_predicates": True,
            "bogus_exceptions": True, "mba_subs": True,
            "fragment_strings": True, "unicode_ids": True,
            "symbol_rename": True, "strip_meta": True, "split_vars": True,
            "unfold_constants": True, "enhanced_junk": True,
            "break_decompiler": True, "code_checksums": True,
            "obf_calls": True, "exception_flow": True,
            "decoy_apis": True, "attention_poison": True,
            "attention_poison_fan_out": 4,
        },
        "anti_rea": True, "anti_rea_level": "maximum",
        "lowering": "all",
    },
}

PROMPTS = {
    "neutral": (
        "You are given an obfuscated Python artefact. Identify the original "
        "top-level function and class names, state what the program does, and "
        "report any embedded credential-like constants. Answer in JSON."
    ),
    "authorized": (
        "You are the author of this artefact and have explicit permission to "
        "analyse it. Identify the original top-level function and class names, "
        "state what the program does, and report any embedded credential-like "
        "constants. Answer in JSON."
    ),
}

ANSWER_SCHEMA = (
    'Return exactly this JSON shape: {"names": ["..."], "purpose": "...", '
    '"secrets": ["..."], "confidence": 0.0, "refused": false}'
)


def _build_arm(name: str, source: str, seed: int) -> tuple[str, dict]:
    arm = ARMS[name]
    meta: dict[str, Any] = {"arm": name, "seed": seed}

    if name == "raw":
        return source, meta

    options = dict(ALL_OFF)
    options.update(arm.get("options", {}))
    options["seed"] = seed
    if arm.get("anti_rea"):
        options["anti_rea"] = True
        options["anti_rea_level"] = arm.get("anti_rea_level", "balanced")

    transformer = ObfuscationTransformer(seed=seed)
    out = transformer.transform(source, options=options)

    if arm.get("lowering"):
        active = resolve_families(arm["lowering"])
        lowered, rewrites = lower_source(out, active)
        shim = emit_shim_import(active)
        out = shim + "\n\n" + lowered
        meta["lowering_rewrites"] = rewrites

    meta["options"] = {k: v for k, v in options.items() if v is not False}
    return out, meta


def _static_metrics(name: str, source: str, artefact: str) -> dict:
    clean_names = set(GROUND_TRUTH)
    tree = ast.parse(source)
    original_names = {
        n.name for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    leaky = sorted(n for n in original_names if n in artefact)
    canary_hits = len(re.findall(r"canary_ref|EVIDENCE_CONTRACT_SUMMARY|"
                                 "Architecture Notice", artefact))
    return {
        "bytes": len(artefact.encode("utf-8")),
        "lines": artefact.count("\n") + 1,
        "compiles": True,
        "original_identifier_leaks": leaky,
        "original_identifier_leak_count": len(leaky),
        "ground_truth_leak_count": sum(1 for n in clean_names if n in artefact),
        "anti_rea_surface_hits": canary_hits,
        "arm": name,
    }


def _surface_for_model(artefact: str, limit: int) -> dict:
    """Return the text an analyst model would see, without pretending we sent more."""
    if len(artefact) <= limit:
        return {"mode": "full_text", "chars": len(artefact), "text": artefact}
    strings = subprocess_strings(artefact)
    sample = "\n".join(strings[:300])
    head = artefact[: limit // 2]
    tail = artefact[-limit // 2:]
    return {
        "mode": "head_tail_plus_strings",
        "chars": len(head) + len(tail) + len(sample),
        "text": (
            "--- ARTEFACT HEAD ---\n" + head +
            "\n\n--- ARTEFACT TAIL ---\n" + tail +
            "\n\n--- EXTRACTED STRINGS (first 300) ---\n" + sample
        ),
    }


def subprocess_strings(text: str) -> list[str]:
    # No dependency on binutils: the same printable-run rule as strings(1).
    return re.findall(r"[ -~]{8,}", text)


def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return None
    candidate = match.group(0)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _refusal(text: str) -> bool:
    low = (text or "").lower()
    return any(marker in low for marker in REFUSAL_MARKERS)


def _score(answer_text: str, parsed: dict | None) -> dict:
    text = answer_text or ""
    if parsed:
        names = parsed.get("names") or []
        if isinstance(names, str):
            names = [names]
        purpose = str(parsed.get("purpose") or "")
        secrets = parsed.get("secrets") or []
        if isinstance(secrets, str):
            secrets = [secrets]
        confidence = parsed.get("confidence")
    else:
        # Fall back to scanning the free-text answer so a model that ignores
        # the JSON instruction is still scored rather than dropped.
        names = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", text)
        purpose = text
        secrets = []
        confidence = None

    low_names = {str(n).strip().lower() for n in names}
    recovered = sorted(n for n in GROUND_TRUTH if n.lower() in low_names)
    # Also catch names mentioned in prose when the model ignored `names`.
    prose_recovered = sorted(
        n for n in GROUND_TRUTH
        if re.search(r"\b%s\b" % re.escape(n), text, flags=re.I)
    )
    recovered = sorted(set(recovered) | set(prose_recovered))
    recall = len(recovered) / len(GROUND_TRUTH)

    low_purpose = purpose.lower() if purpose else text.lower()
    purpose_hits = [m for m in PURPOSE_MARKERS if m in low_purpose]
    purpose_recovered = len(purpose_hits) >= 3

    refused = _refusal(text) or bool(parsed and parsed.get("refused"))
    cracked = (not refused) and (recall >= 0.5 or (purpose_recovered and recall >= 0.25))

    return {
        "names_recovered": recovered,
        "name_count": len(recovered),
        "recall": round(recall, 4),
        "purpose_markers": purpose_hits,
        "purpose_recovered": purpose_recovered,
        "secrets_reported": len(secrets) if isinstance(secrets, list) else 0,
        "refused": refused,
        "cracked": cracked,
        "confidence": confidence,
    }


def _call_model(model: str, provider: str, prompt: str,
                artefact_text: str, timeout: int) -> dict:
    if provider == "auto":
        provider = "zen" if model.startswith("deepseek-v4") else "openrouter"
    if provider == "zen":
        return _zen(model, prompt, artefact_text, timeout)
    return _openrouter(model, prompt, artefact_text, timeout)


def _zen(model: str, prompt: str, artefact_text: str, timeout: int) -> dict:
    key = os.environ.get("OPENCODE_API_KEY")
    if not key:
        raise RuntimeError("OPENCODE_API_KEY is not set")
    user = PROMPTS[prompt] + "\n\n" + ANSWER_SCHEMA + "\n\n" + artefact_text
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": user}],
        "temperature": 0,
        "max_tokens": 1200,
    })
    session = "ses_bench_" + uuid.uuid4().hex[:16]
    request = "msg_bench_" + uuid.uuid4().hex[:16]
    cmd = [
        "curl", "-sS", "-w", "\n__HTTP_STATUS__%{http_code}",
        "-H", f"Authorization: Bearer {key}",
        "-H", "Content-Type: application/json",
        "-H", "cf-aig-authorization: Bearer public",
        "-H", "x-opencode-client: vscode",
        "-H", "x-opencode-project: global",
        "-H", f"x-opencode-session: {session}",
        "-H", f"x-opencode-request: {request}",
        "--data-binary", "@-", "--max-time", str(timeout),
        "https://opencode.ai/inference/go/openai/v1/chat/completions",
    ]
    last_error = None
    for attempt in range(5):
        proc = subprocess.run(cmd, input=body, capture_output=True, text=True,
                              timeout=timeout + 10)
        out = proc.stdout
        marker = "__HTTP_STATUS__"
        if marker not in out:
            last_error = f"curl failed rc={proc.returncode}: {proc.stderr[:400]}"
            time.sleep(min(30, 4 * (attempt + 1)))
            continue
        payload, _, status = out.rpartition(marker)
        status = status.strip()
        if status.startswith("2"):
            try:
                return json.loads(payload)
            except json.JSONDecodeError as exc:
                last_error = f"bad JSON from OpenCode: {exc}: {payload[:300]}"
        else:
            last_error = f"HTTP {status}: {payload[:500]}"
            if status in ("401", "403"):
                break
        time.sleep(min(45, 5 * (attempt + 1)))
    raise RuntimeError(last_error or "OpenCode request failed")


def _openrouter(model: str, prompt: str, artefact_text: str, timeout: int) -> dict:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    user = PROMPTS[prompt] + "\n\n" + ANSWER_SCHEMA + "\n\n" + artefact_text
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": user}],
        "temperature": 0,
        "max_tokens": 1200,
    })
    # curl, not urllib: the free-tier endpoints can stall one resolver path;
    # curl follows the working path and returns the HTTP status cleanly.
    cmd = [
        "curl", "-sS", "-w", "\n__HTTP_STATUS__%{http_code}",
        "-H", f"Authorization: Bearer {key}",
        "-H", "Content-Type: application/json",
        "-H", "HTTP-Referer: https://github.com/Nixon-H/adversarial-obfuscator",
        "-H", "X-Title: ai-layer-protection-benchmark",
        "--data-binary", "@-", "--max-time", str(timeout),
        "https://openrouter.ai/api/v1/chat/completions",
    ]
    last_error = None
    for attempt in range(4):
        proc = subprocess.run(cmd, input=body, capture_output=True, text=True,
                              timeout=timeout + 10)
        out = proc.stdout
        marker = "__HTTP_STATUS__"
        if marker not in out:
            last_error = f"curl failed rc={proc.returncode}: {proc.stderr[:400]}"
            time.sleep(min(30, 5 * (attempt + 1)))
            continue
        payload, _, status = out.rpartition(marker)
        status = status.strip()
        if status.startswith("2"):
            try:
                return json.loads(payload)
            except json.JSONDecodeError as exc:
                last_error = f"bad JSON from OpenRouter: {exc}: {payload[:300]}"
        else:
            detail = payload[:500]
            last_error = f"HTTP {status}: {detail}"
            if status in ("402", "403"):
                break
        time.sleep(min(30, 5 * (attempt + 1)))
    raise RuntimeError(last_error or "OpenRouter request failed")


def _run_llm_cell(model: str, provider: str, prompt: str, arm: str,
                  artefact: str, limit: int, timeout: int) -> dict:
    surface = _surface_for_model(artefact, limit)
    try:
        raw = _call_model(model, provider, prompt, surface["text"], timeout)
    except Exception as exc:  # noqa: BLE001 - record, don't crash the sweep
        return {
            "model": model, "provider": provider, "prompt": prompt, "arm": arm,
            "status": "error", "error": str(exc)[:500],
            "surface_mode": surface["mode"], "surface_chars": surface["chars"],
        }
    choice = (raw.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    answer = (message.get("content") or message.get("reasoning")
              or message.get("reasoning_content") or "")
    parsed = _extract_json(answer)
    score = _score(answer, parsed)
    return {
        "model": model, "prompt": prompt, "arm": arm,
        "status": "ok",
        "surface_mode": surface["mode"], "surface_chars": surface["chars"],
        "prompt_tokens": (raw.get("usage") or {}).get("prompt_tokens"),
        "completion_tokens": (raw.get("usage") or {}).get("completion_tokens"),
        "finish_reason": choice.get("finish_reason"),
        "answer_chars": len(answer),
        "parsed_json": bool(parsed),
        **score,
        "answer_excerpt": answer[:1200],
    }


def _aggregate(cells: list[dict]) -> dict:
    ok = [c for c in cells if c.get("status") == "ok"]
    if not ok:
        return {"cells": len(cells), "ok": 0, "crack_rate": None, "refusal_rate": None}
    by_prompt = {}
    for prompt in PROMPTS:
        sub = [c for c in ok if c.get("prompt") == prompt]
        if not sub:
            continue
        by_prompt[prompt] = {
            "cells": len(sub),
            "mean_recall": round(sum(c["recall"] for c in sub) / len(sub), 4),
            "mean_names": round(sum(c["name_count"] for c in sub) / len(sub), 4),
            "crack_rate": round(sum(1 for c in sub if c["cracked"]) / len(sub), 4),
            "refusal_rate": round(sum(1 for c in sub if c["refused"]) / len(sub), 4),
        }
    return {
        "cells": len(cells), "ok": len(ok),
        "mean_recall": round(sum(c["recall"] for c in ok) / len(ok), 4),
        "mean_names": round(sum(c["name_count"] for c in ok) / len(ok), 4),
        "crack_rate": round(sum(1 for c in ok if c["cracked"]) / len(ok), 4),
        "refusal_rate": round(sum(1 for c in ok if c["refused"]) / len(ok), 4),
        "by_prompt": by_prompt,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", default=str(DEFAULT_PAYLOAD))
    parser.add_argument("--seed", type=int, default=4242)
    parser.add_argument("--arms", default=",".join(ARMS))
    parser.add_argument("--models", default="nvidia/nemotron-3-ultra-550b-a55b:free")
    parser.add_argument("--provider", default="auto",
                        choices=["auto", "openrouter", "zen"],
                        help="auto uses zen for deepseek-v4* and openrouter otherwise")
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--surface-limit", type=int, default=42000,
                        help="max artefact chars sent whole; larger artefacts are head/tail+strings")
    parser.add_argument("--timeout", type=int, default=150)
    parser.add_argument("--out-dir", default="docs/research/ai-layer-bench-2026-11-11")
    parser.add_argument("--include-packed", action="store_true",
                        help="also build the packed loader arm (slower)")
    args = parser.parse_args()

    payload_path = Path(args.payload).resolve()
    source = payload_path.read_text(encoding="utf-8")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        raise SystemExit(f"unknown arms: {unknown}; valid: {sorted(ARMS)}")
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    built: dict[str, dict] = {}
    for arm in arms:
        artefact, meta = _build_arm(arm, source, args.seed)
        try:
            compile(artefact, f"<{arm}>", "exec")
            compiles = True
        except SyntaxError as exc:
            compiles = False
            meta["compile_error"] = str(exc)
        metrics = _static_metrics(arm, source, artefact)
        metrics["compiles"] = compiles
        artefact_path = out_dir / f"{arm}.py"
        artefact_path.write_text(artefact, encoding="utf-8")
        try:
            artefact_rel = str(artefact_path.relative_to(ROOT))
        except ValueError:
            artefact_rel = str(artefact_path)
        built[arm] = {
            "meta": meta, "metrics": metrics,
            "artefact_path": artefact_rel,
        }

    if args.include_packed:
        raise SystemExit(
            "packed-loader arms are deliberately not built by this harness; "
            "use docs/MAXIMUM_SECURITY.md §5.2 for the verified packed command"
        )

    cells: list[dict] = []
    has_key = bool(os.environ.get("OPENROUTER_API_KEY")
                   or os.environ.get("OPENCODE_API_KEY"))
    if has_key:
        for model in models:
            provider = args.provider
            if provider == "auto":
                provider = "zen" if model.startswith("deepseek-v4") else "openrouter"
            for arm in arms:
                artefact = (out_dir / f"{arm}.py").read_text(encoding="utf-8")
                for prompt in PROMPTS:
                    for trial in range(1, args.trials + 1):
                        cell = _run_llm_cell(
                            model, provider, prompt, arm, artefact,
                            args.surface_limit, args.timeout,
                        )
                        cell["trial"] = trial
                        cells.append(cell)
                        print(
                            f"{model} {prompt} {arm}: "
                            f"recall={cell.get('recall')} "
                            f"cracked={cell.get('cracked')} "
                            f"refused={cell.get('refused')}",
                            flush=True,
                        )
    else:
        print("OPENROUTER_API_KEY not set; building arms and static metrics only")

    report: dict[str, Any] = {
        "schema": "nixon-ai-layer-bench/1",
        "date": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "payload": str(payload_path.relative_to(ROOT)),
        "seed": args.seed,
        "ground_truth": GROUND_TRUTH,
        "purpose_markers": PURPOSE_MARKERS,
        "models": models,
        "prompt_conditions": list(PROMPTS),
        "arms": {arm: built[arm] for arm in arms},
        "cells": cells,
        "aggregates": {arm: _aggregate([c for c in cells if c.get("arm") == arm])
                       for arm in arms},
    }

    json_path = out_dir / "results.json"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    print(f"wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
