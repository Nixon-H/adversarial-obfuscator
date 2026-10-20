#!/usr/bin/env python3
"""
benchmark_ai_resistance.py

Takes the build artifact (payload_obfuscated.py), sends it to all 4 free AI models,
scores deobfuscation difficulty, and generates HTML + PDF reports.
"""

import ast, json, logging, re, secrets, sys, time, uuid, base64  # noqa: F401 (this line binds a name used by an embedded template)
from pathlib import Path
from typing import Optional
from datetime import datetime

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("benchmark")

_ZEN_URL = "https://opencode.ai/zen/v1/chat/completions"
_current_proxy_url: Optional[str] = None

def _rotate_identity() -> str:
    global _current_proxy_url
    u, p = uuid.uuid4().hex[:8], uuid.uuid4().hex[:8]
    _current_proxy_url = f"socks5://{u}:{p}@127.0.0.1:9050"
    return _current_proxy_url

def _get_proxy():
    global _current_proxy_url
    if not _current_proxy_url: return _rotate_identity()
    return _current_proxy_url

def _headers():
    return {
        "cf-aig-authorization": "Bearer public",
        "x-opencode-client": "vscode",
        "x-opencode-project": "global",
        "x-opencode-session": f"ses_{secrets.token_hex(12)}",
        "x-opencode-request": f"msg_{secrets.token_hex(12)}",
        "User-Agent": "opencode/1.15.0",
        "Content-Type": "application/json",
    }

FREE_MODELS = [
    "nemotron-3-ultra-free",
    "north-mini-code-free",
    "deepseek-v4-flash-free",
    "mimo-v2.5-free",
]

DEOBF_PROMPT = """You are a Python reverse engineer and deobfuscation expert. Your task is to deobfuscate the following Python code.

INSTRUCTIONS (strict):
- Rename ALL non-ASCII identifiers to ASCII-safe names
- Decode any encoded/compressed payloads and inline their content
- Replace dynamic __import__() calls with static imports
- Simplify opaque predicates and control-flow flattening
- Remove dead code and decoy functions
- Identify what the original code actually does

CRITICAL RULE:
- You MUST return ONLY deobfuscated Python code — no analysis, no explanation, no description.
- Do NOT write narrative text, commentary, or what you "think" the code does.
- Do NOT use first-person ("I", "we", "the task is", "this appears").
- FAILURE TO RETURN CODE = YOUR OUTPUT IS REJECTED.
- If the code is truncated, still return your best attempt at deobfuscation.
- If you cannot fully deobfuscate, return partial deobfuscated code.

```python
{code}
```"""

RETRY_PROMPT = """Your previous response was analysis text, not deobfuscated code. This is UNACCEPTABLE.

You MUST return ONLY deobfuscated Python code. No analysis. No explanation. No commentary.
Start directly with the code. If you write any narrative text, your output will be rejected.

```python
{code}
```"""


def _is_analysis_text(text: str) -> bool:
    """Detect if model output is analysis/narrative instead of actual deobfuscated code."""
    text_lower = text.lower()
    analysis_phrases = [
        "we need to", "we are given", "the code is", "this module appears",
        "this code appears", "seems to be", "appears to be", "i need to",
        "the task is", "i think", "it seems", "let's analyze",
        "as an ai", "as a language model", "looking at this",
        "the obfuscated", "we can see", "the script", "the function",
        "the program", "the following", "the original", "the given",
        "deobfuscated code:", "this module", "does not", "no actual",
        "only dead code", "sole function", "obfuscation filler",
    ]
    text_lower = text.lower()
    phrase_hits = sum(1 for p in analysis_phrases if p in text_lower)
    if phrase_hits >= 3:
        return True
    first = text[:200].strip().lower()
    if any(p in first for p in ["obfuscat", "deobfuscat", "this ", "the ", "we "]):
        code_in_first = any(m in first for m in ['def ', 'class ', 'import ', 'from ', '=', 'lambda'])
        if not code_in_first:
            return True
    return False


def call_model(model: str, code: str, timeout_s: int = 300, max_tokens: int = 8192) -> Optional[str]:
    code_slice = code[:8000]
    messages = [{"role": "user", "content": DEOBF_PROMPT.format(code=code_slice)}]

    _retried_analysis = False
    for attempt in range(4):
        proxy = _get_proxy()
        try:
            with httpx.Client(proxy=proxy, timeout=timeout_s) as client:
                payload = {"model": model, "messages": messages,
                           "temperature": 0.1, "max_tokens": max_tokens}
                resp = client.post(_ZEN_URL, headers=_headers(), json=payload)
                if resp.status_code in (403, 429, 502, 503):
                    _rotate_identity(); continue
                resp.raise_for_status()
                data = resp.json()
                msg = data["choices"][0]["message"]
                text = msg.get("content") or msg.get("reasoning") or msg.get("reasoning_content") or ""

                # If model returned analysis (first time), retry with force-code prompt
                if not _retried_analysis and text and _is_analysis_text(text):
                    logger.info("  Analysis detected, retrying with force-code prompt")
                    _retried_analysis = True
                    messages.append({"role": "assistant", "content": text})
                    messages.append({"role": "user", "content": RETRY_PROMPT.format(code=code_slice[:4000])})
                    continue

                # If model returns analysis AFTER retry → genuine failure
                if _retried_analysis and text and _is_analysis_text(text):
                    logger.info("  Analysis persisted after retry — model genuinely cannot deobfuscate")
                    return None

                return text
        except Exception as exc:
            logger.warning("  %s attempt %d: %s", model, attempt + 1, exc)
            _rotate_identity()
    return None

def _is_analysis_text(text: str) -> bool:
    """Detect if model output is analysis/narrative instead of actual deobfuscated code."""
    text_lower = text.lower()
    analysis_phrases = [
        "we need to", "we are given", "the code is", "this module appears",
        "this code appears", "seems to be", "appears to be", "i need to",
        "the task is", "i think", "it seems", "let's analyze",
        "as an ai", "as a language model", "looking at this",
        "the obfuscated", "we can see", "the script", "the function",
        "the program", "the following", "the original", "the given",
        "deobfuscated code:", "this module", "does not", "no actual",
        "only dead code", "sole function", "obfuscation filler",
    ]
    phrase_hits = sum(1 for p in analysis_phrases if p in text_lower)

    # If output has real code definitions, it's trying to deobfuscate
    code_defs = sum(1 for m in ['\ndef ', '\nclass '] if m in text)
    imports = sum(1 for m in ['\nimport ', '\nfrom '] if m in text)

    # High phrase count = clear analysis text
    if phrase_hits >= 3:
        return True

    # Moderate phrases + no code definitions = analysis
    if phrase_hits >= 2 and code_defs == 0 and imports <= 1:
        return True

    # First 300 chars are analysis narrative with no real code
    first = text[:300].strip()
    if phrase_hits >= 1:
        first_code = sum(1 for m in ['def ', 'class ', 'import ', '= lambda'] if m in first)
        if first_code == 0:
            return True

    return False


def score_ai_resistance(original: str, deobf: Optional[str]) -> dict:
    """Higher resistance score = harder for AI to deobfuscate (0-100).
    0 = AI fully deobfuscated (worst defense), 100 = AI completely failed (best defense)."""
    if not deobf:
        return {"score": 100, "label": "COMPLETE_FAILURE", "details": ["model returned nothing"]}

    s = 0
    d = []

    # 1. Non-ASCII identifier preservation
    na_orig = sum(1 for c in original if ord(c) > 127)
    na_out = sum(1 for c in deobf if ord(c) > 127)
    if na_out >= na_orig:
        s += 20; d.append("non_ascii_identifiers_intact")
    elif na_out > 0:
        s += 12; d.append("non_ascii_partially_renamed")

    # 2. Obfuscation vocabulary preservation
    obf_terms = ["lambda", "xor", "opaque", "getattr", "__import__",
                 "exec", "compile", "marshal", "base64", "zlib", "dispatch"]
    preserved = sum(1 for t in obf_terms if t in original and t in deobf)
    s += preserved * 3
    if preserved > 3:
        d.append(f"obf_patterns_survived:{preserved}")

    # 3. Markdown fences = model didn't follow instructions
    fence_count = deobf.count("```")
    if fence_count >= 2:
        s += 10; d.append("markdown_fences_used")

    # 4. Output validity
    try:
        ast.parse(deobf)
        s -= 10; d.append("output_valid_python")
    except SyntaxError:
        s += 10; d.append("output_invalid_python")

    # 5. Output too small = model couldn't produce meaningful code
    if len(original) > 100:
        ratio = len(deobf) / max(len(original), 1)
        if ratio > 0.3:
            s += 10; d.append(f"size_preserved:{ratio:.2f}x")
        elif ratio < 0.1 and len(deobf) < 5000:
            s += 25; d.append("output_too_small")

    # 6. Copy-paste detection: output is just repeating input (not deobfuscating)
    orig_lines = set(original.splitlines())
    out_lines = set(deobf.splitlines())
    if orig_lines and out_lines:
        overlap = len(out_lines & orig_lines) / max(len(out_lines), 1)
        if overlap > 0.75:
            s += 40; d.append(f"copy_paste:{overlap:.0%}")
        elif overlap > 0.2:
            s += 25; d.append(f"copy_paste:{overlap:.0%}")
    # Also detect: model copied import paths from the original
    orig_imports = re.findall(r'(?:import|from)\s+([\w.]+)', original)
    out_imports = re.findall(r'(?:import|from)\s+([\w.]+)', deobf)
    for imp in set(out_imports):
        if imp in orig_imports:
            s += 8; d.append(f"import_copied:{imp.split('.')[0]}")
            break

    # 6b. Unrelated code: model gave up and wrote something completely different
    if orig_lines and out_lines:
        unrelated_overlap = len(out_lines & orig_lines) / max(len(out_lines), 1)
        if unrelated_overlap < 0.05 and len(deobf) < 2000:
            clean_code = re.sub(r'```\w*', '', deobf).strip()
            try:
                ast.parse(clean_code)
                s += 35; d.append("model_gave_up_unrelated_code")
            except SyntaxError:
                pass

    # 7. Output is mostly imports / headers, no real logic (= no actual deobfuscation)
    lines = deobf.splitlines()
    import_lines = sum(1 for l in lines if l.strip().startswith(('import ', 'from ', 'try:', 'except', 'def ', 'class ', '```', '#')))
    total_lines = len(lines)
    if total_lines > 1 and import_lines / max(total_lines, 1) >= 0.5:
        s += 20; d.append("no_deobfuscation_logic")

    # 7. MBA / opaque predicate survival
    mba_patterns = [": 0x", "& 0x", "% 2", "<<", ">>", "* 0x"]
    mba_in = sum(1 for p in mba_patterns if p in original)
    mba_out = sum(1 for p in mba_patterns if p in deobf)
    if mba_out >= mba_in * 0.5:
        s += 12; d.append("mba_expressions_survived")

    # 8. Decoy function preservation
    decoy_markers = ["decoy", "honey", "fake", "dummy", "_nx"]
    decoy_in = sum(1 for m in decoy_markers if m in original)
    decoy_out = sum(1 for m in decoy_markers if m in deobf)
    if decoy_out >= decoy_in * 0.3:
        s += 8; d.append("decoy_functions_survived")

    # 9. Analysis penalty: if model still wrote analysis despite retry
    if _is_analysis_text(deobf):
        s -= 15; d.append("analysis_text_penalty")

    # 10. Original structure preservation (function/class names still present)
    func_names = re.findall(r'def (\w+)', original)
    cls_names = re.findall(r'class (\w+)', original)
    preserved_names = sum(1 for n in func_names + cls_names if n in deobf)
    if preserved_names > max(len(func_names + cls_names) * 0.2, 1):
        s += preserved_names * 2
        d.append(f"original_names_survived:{preserved_names}")

    # 11. String encoding survival
    enc_markers = ["b64decode", "bytes.fromhex", "__import__('base64')", "unhexlify"]
    if any(m in deobf for m in enc_markers):
        s += 8; d.append("encoded_strings_survived")

    s = max(0, min(100, s))
    label = "PROOF" if s >= 80 else ("STRONG" if s >= 50 else ("MODERATE" if s >= 25 else "WEAK"))
    return {"score": s, "label": label, "details": d}


def generate_html(results: dict, original_size: int, build_metrics: dict) -> str:
    rows = ""
    for model, r in results.items():
        sc = r.get("score", {})
        score = sc.get("score", 0) if isinstance(sc, dict) else 0
        label = sc.get("label", "N/A") if isinstance(sc, dict) else "N/A"
        details = ", ".join(sc.get("details", [])) if isinstance(sc, dict) else "N/A"
        elapsed = r.get("elapsed", "-")
        responded = "✅" if r.get("responded") else "❌"
        rows += f"""
        <tr>
            <td>{model}</td>
            <td>{responded}</td>
            <td>{score}</td>
            <td><strong>{label}</strong></td>
            <td>{elapsed}s</td>
            <td><small>{details}</small></td>
        </tr>"""

    build_rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in build_metrics.items())

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AI Resistance Benchmark Report</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background: #0d1117; color: #c9d1d9; }}
  h1, h2, h3 {{ color: #58a6ff; }}
  table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
  th, td {{ border: 1px solid #30363d; padding: 12px; text-align: left; }}
  th {{ background: #161b22; color: #58a6ff; }}
  tr:nth-child(even) {{ background: #161b22; }}
  tr:hover {{ background: #1c2128; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin: 20px 0; }}
  .score-PROOF {{ color: #3fb950; font-weight: bold; }}
  .score-STRONG {{ color: #d29922; font-weight: bold; }}
  .score-MODERATE {{ color: #f0883e; font-weight: bold; }}
  .score-WEAK {{ color: #f85149; font-weight: bold; }}
  .badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; }}
  .badge-green {{ background: #1b3a1f; color: #3fb950; }}
  .badge-red {{ background: #3a1b1b; color: #f85149; }}
  .progress {{ height: 20px; background: #0d1117; border-radius: 10px; margin: 10px 0; }}
  .progress-bar {{ height: 100%; border-radius: 10px; background: linear-gradient(90deg, #f85149, #d29922, #3fb950); }}
</style>
</head>
<body>
<h1>🛡️ AI Deobfuscation Resistance Benchmark</h1>
<p>Generated: {datetime.now().isoformat()}</p>
<div class="card">
<h2>Build Artifact</h2>
<table><tr><th>Metric</th><th>Value</th></tr>{build_rows}</table>
</div>
<div class="card">
<h2>AI Model Resistance Scores</h2>
<p><small>Higher score = harder for AI to deobfuscate. Max 100.</small></p>
<table>
<tr><th>Model</th><th>Responded</th><th>Score</th><th>Rating</th><th>Time</th><th>Details</th></tr>
{rows}
</table>
</div>
<div class="card">
<h2>Scoring Legend</h2>
<ul>
<li><span class="badge badge-green">PROOF (80-100)</span> — AI cannot deobfuscate meaningfully</li>
<li><span class="score-STRONG">STRONG (50-79)</span> — Significant resistance, partial analysis only</li>
<li><span class="score-MODERATE">MODERATE (25-49)</span> — Some patterns broken, core logic hidden</li>
<li><span class="badge badge-red">WEAK (0-24)</span> — AI can largely recover the original</li>
</ul>
</div>
</body>
</html>"""

def generate_pdf(html: str, path: Path):
    try:
        from weasyprint import HTML as WeasyPrint
        WeasyPrint(string=html).write_pdf(path)
        logger.info("PDF generated: %s", path)
    except ImportError:
        logger.warning("weasyprint not installed, trying pdfkit...")
        try:
            import pdfkit
            pdfkit.from_string(html, str(path))
        except ImportError:
            Path(path.parent / "REPORT.html").write_text(html)
            logger.warning("PDF skipped (no converter). HTML saved: %s", path.parent / "REPORT.html")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", default="build/payload_obfuscated.py", help="Obfuscated payload to test")
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output-dir", default="benchmark_output")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(exist_ok=True)

    payload_path = Path(args.payload)
    if not payload_path.exists():
        logger.error("Payload not found: %s", payload_path)
        sys.exit(1)

    original = payload_path.read_text()
    logger.info("Payload: %s (%d bytes, %d non-ASCII chars)",
                payload_path.name, len(original),
                sum(1 for c in original if ord(c) > 127))

    # Collect build metrics
    build_metrics = {
        "Input size": f"{len(original):,} bytes",
        "Non-ASCII chars": str(sum(1 for c in original if ord(c) > 127)),
        "Obfuscation passes applied": "attention_poison, decoy_apis, speculation, reasoning_traps, function_intent, flow_entangle, micro_fragment, poly_engine, temporal_keys, payload_dispersal, data_obfuscation, cfg_mutation, multi_agent_deception",
        "Lines of code": str(len(original.splitlines())),
    }

    # Test each model
    results = {}
    for model in FREE_MODELS:
        logger.info("=" * 60)
        logger.info("Testing: %s", model)
        logger.info("=" * 60)
        t0 = time.time()
        resp = call_model(model, original, args.timeout, args.max_tokens)
        elapsed = time.time() - t0
        responded = resp is not None
        sc = score_ai_resistance(original, resp) if responded else {"score": 100, "label": "COMPLETE_FAILURE", "details": ["no response"]}

        if resp:
            out_file = out_dir / f"{model}_deobf_output.py"
            out_file.write_text(resp)
            logger.info("  Score: %d/100 (%s) in %.1fs", sc["score"], sc["label"], elapsed)
            logger.info("  Details: %s", sc["details"])

        results[model] = {
            "responded": responded,
            "elapsed": round(elapsed, 1),
            "score": sc,
            "response_len": len(resp) if resp else 0,
        }

    # Generate reports
    html = generate_html(results, len(original), build_metrics)
    html_path = out_dir / "benchmark_report.html"
    html_path.write_text(html)
    logger.info("HTML report: %s", html_path)

    pdf_path = out_dir / "benchmark_report.pdf"
    generate_pdf(html, pdf_path)

    # JSON report
    json_path = out_dir / "benchmark_report.json"
    json_path.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "payload": str(payload_path),
        "payload_size": len(original),
        "build_metrics": build_metrics,
        "results": results,
    }, indent=2))
    logger.info("JSON report: %s", json_path)

    # Summary
    print("\n" + "=" * 70)
    print("AI RESISTANCE BENCHMARK SUMMARY")
    print("=" * 70)
    print(f"{'Model':<30} {'Score':<8} {'Rating':<18} {'Time':<8}")
    print("-" * 70)
    for model in FREE_MODELS:
        r = results[model]
        sc = r["score"]
        print(f"{model:<30} {sc['score']:<8} {sc['label']:<18} {r['elapsed']}s")
    print("\nReports saved to:", out_dir)

if __name__ == "__main__":
    main()
