#!/usr/bin/env python3
"""
test_deobf_models.py — tests all 4 free LLM models on deobfuscation.
Runs models concurrently, saves results, reports scores.
"""

import json, logging, os, secrets, sys, time, uuid
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("deobf_test")

_ZEN_URL = "https://opencode.ai/zen/v1/chat/completions"
_current_proxy_url: Optional[str] = None

def _rotate_identity() -> str:
    global _current_proxy_url
    u, p = uuid.uuid4().hex[:8], uuid.uuid4().hex[:8]
    _current_proxy_url = f"socks5://{u}:{p}@127.0.0.1:9050"
    return _current_proxy_url

def _get_proxy():
    global _current_proxy_url
    if not _current_proxy_url:
        return _rotate_identity()
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

FREE_MODELS = ["nemotron-3-ultra-free", "north-mini-code-free",
               "deepseek-v4-flash-free", "mimo-v2.5-free"]

DEOBF_PROMPT = """You are a Python deobfuscation expert. Analyze this obfuscated code and:

1. Rename all non-ASCII identifiers to ASCII names (var01, func_decode, ...)
2. Decode any base64/marshal/zlib payloads and inline the content
3. Replace dynamic __import__() with static imports
4. Explain what the code does in a comment header

Return ONLY deobfuscated Python code with explanation. No markdown.

```python
{code}
```"""

def call_model(model: str, code: str, timeout_s: int = 180, max_tokens: int = 4096) -> Optional[str]:
    prompt = DEOBF_PROMPT.format(code=code)
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.1, "max_tokens": max_tokens}

    for attempt in range(3):
        proxy = _get_proxy()
        try:
            with httpx.Client(proxy=proxy, timeout=timeout_s) as client:
                resp = client.post(_ZEN_URL, headers=_headers(), json=payload)
                if resp.status_code in (403, 429, 502, 503):
                    _rotate_identity()
                    continue
                resp.raise_for_status()
                data = resp.json()
                msg = data["choices"][0]["message"]
                text = msg.get("content") or msg.get("reasoning") or ""
                total = data.get("usage", {}).get("total_tokens", 0)
                logger.info("  %s: %d tokens in %.1fs", model, total, timeout_s)
                return text
        except Exception as exc:
            logger.warning("  %s attempt %d: %s", model, attempt + 1, exc)
            _rotate_identity()
    return None

def score_deobfuscation(original: str, deobf: str) -> dict:
    if not deobf:
        return {"score": 0, "reason": "no response"}
    s, d = 0, []
    na_before = sum(1 for c in original if ord(c) > 127)
    na_after = sum(1 for c in deobf if ord(c) > 127)
    if na_after < na_before:
        s += 2; d.append(f"ascii_rename:{na_before}->{na_after}")
    for kw in ["exec(", "marshal", "base64", "zlib", "__import__"]:
        if kw in original and kw not in deobf:
            s += 1; d.append(f"removed_{kw.rstrip('((')}")
    if "#" in deobf[:300]:
        s += 1; d.append("has_explanation")
    ratio = len(deobf) / max(len(original), 1)
    if ratio < 0.7:
        s += 2; d.append(f"compressed:{ratio:.2f}x")
    import ast
    try:
        ast.parse(deobf)
        s += 1; d.append("valid_python")
    except SyntaxError:
        s -= 1; d.append("syntax_error")
    return {"score": s, "details": d}

SAMPLE_1 = r"""
import base64, marshal, zlib
def よろしく():
    _x = "eJx1kU9PwzAMxb9K5HNKJ7pN7I8AQgIhTZw4cUCKSpZ4a9Q4VZNu2rdH3cSBH3CxZOf5/ey8vN0fDq/7l+d5e6qKEMJrvp6nw+NhOwnz/D5Ntzeb+93tcrmYb+t7jNXHx9s0Lu76+jofT5fL6bh+S8NwOkzTdJyGt8sQwjAMh8Nhu32P08u8rPP7er3ebl/e0rqu3+tleZ2Xz9MY11dVz/M6LV/red2M43pY3uYwTdNpmr7W4zAMx+06nYfTfJjm4/k4D+tzGMfx9eUwLMM4DMP8+Pj4+rqO63L4WsZ5foz381uM6/s4H4b1PIzrYTqcz4fD8LGOw3QM43Yeh+M4vw3D8rV3xfD5MG7Hw+FwOA2394fvH4ZhGL8Bp8rOPg=="
    _y = base64.b64decode(_x)
    _z = zlib.decompress(_y)
    code = marshal.loads(_z)
    exec(code)
def 変換():
    __import__('os').system('echo hello')
    __import__('sys').exit(0)
よろしく()
変換()
"""

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--model")
    parser.add_argument("--output-dir", default="deobf_results")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(exist_ok=True)

    samples = {"marshal_exec": SAMPLE_1}
    models = [args.model] if args.model else FREE_MODELS
    results = {}

    def test_one(model, name, code):
        t0 = time.time()
        resp = call_model(model, code, args.timeout, args.max_tokens)
        el = time.time() - t0
        if resp:
            (out_dir / f"{model}_{name}.py").write_text(resp)
            sc = score_deobfuscation(code, resp)
            logger.info("  %s/%s: score=%d/10 %.1fs %s", model, name, sc["score"], el, sc["details"])
            return {"elapsed": round(el, 1), "response_len": len(resp), **sc}
        return {"error": "no response"}

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(test_one, m, n, c): m for m in models for n, c in samples.items()}
        for fut in as_completed(futures):
            model = futures[fut]
            results.setdefault(model, {})
            for n in samples:
                if model not in results or n not in results.get(model, {}):
                    try:
                        results[model][n] = fut.result() if model in str(fut) else None
                    except Exception as e:
                        results.setdefault(model, {})[n] = {"error": str(e)}

    print("\n" + "=" * 60)
    print(f"{'Model':<30} {'Score':<8} {'Time':<8} {'Chars':<8}")
    print("-" * 60)
    for m in models:
        for n, r in results.get(m, {}).items():
            print(f"{m:<30} {r.get('score','ERR'):<8} {r.get('elapsed','-'):<8} {r.get('response_len','-'):<8}")
    (out_dir / "report.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\nReport: {out_dir / 'report.json'}")

if __name__ == "__main__":
    main()
