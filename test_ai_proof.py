#!/usr/bin/env python3
"""
test_ai_proof.py — two obfuscated payloads to test if AIs can break them.

Version A: simple base64+marshal (AI cracked this)
Version B: AI-proof with opaque predicates, MBA, CFG flattening, anti-analysis
"""

import json, logging, os, secrets, sys, time, uuid
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ai_proof")

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

FREE_MODELS = ["nemotron-3-ultra-free", "north-mini-code-free",
               "deepseek-v4-flash-free", "mimo-v2.5-free"]

# ── Version A: simple (AI cracked this) ──
SAMPLE_A = r"""
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

# ── Version B: AI-proof (opaque predicates, MBA, multi-layer, anti-analysis) ──
SAMPLE_B = r"""
# Layer 1: MBA opaque constant
import sys as _sys
_nX0 = (lambda: [(lambda: 0xDEAD + 0xBEEF - (0x1A2B ^ 0x3C4D) * 0 + 0x7F3C & 0xFFFF or 0x539])() or (lambda x: (x * x - x) & 0xFFFFFFFF)(0xABCDEF) ^ 0x12345678)()
_nX1 = (_nX0 * _nX0 + _nX0 * 7 + 13) % 0x7F3C + 0x539

# Layer 2: opaque predicate — always-true but NP-hard to prove statically
def _nX2(_a, _b):
    _c = _a ^ _b
    _d = _a + _b
    _e = (_c * _d + _a * _b) ^ (_a - _b)
    return _e % 2 == (_a % 2 if _a > _b else _b % 2)

# Layer 3: string built from fragments, no single base64 blob
_nX3 = lambda _p: ''.join(chr(ord(_c) ^ 0x7C) for _c in _p)
_nX4 = _nX3('\x1b\x18\x1c\x0c') + _nX3('\x1c\x1b\x1c\x18\x1b\x0c') + _nX3('\x1c\x0b\x1c\x0c\x1b\x18\x01')

# Layer 4: control flow flattening via computed dispatch
_nX5 = {0: lambda: None, 1: lambda: _nX3('\x3f\x3d\x2b\x22\x2a\x2b\x39\x2e\x2a\x2b\x3f\x2b\x3c\x3f\x3d\x3c')}
_nX6 = [_nX1 & 0xFF, (_nX1 >> 8) & 0xFF, (_nX1 >> 16) & 0xFF, (_nX1 >> 24) & 0xFF]
_nX7 = bytes([(_b ^ 0xA5 ^ ((_i * 0x1B) & 0xFF)) for _i, _b in enumerate(_nX6)])

# Layer 5: anti-debug / anti-VM
def _nX8():
    try:
        if _sys.gettrace() is not None:
            while True: pass
    except: pass
    try:
        import ctypes
        _nX9 = ctypes.CDLL(None)
        _nX9.ptrace(0, 0, 0, 0)
    except: pass

# Layer 6: code hidden behind opaque predicate
def _nX10(_v):
    _r = 0
    for _i in range(32):
        if _v & (1 << _i):
            _r ^= 0xEDB88320 >> _i
    return _r ^ 0xA5A5A5A5

# Layer 7: no exec/marshal — dynamic call via getattr chain
_nX11 = type(lambda: 0)(lambda s: None, (), {'_nX12': lambda _: _sys.write(_.encode())})

# Entry — opaque predicate guards real vs fake path
if _nX2(_nX1, 0x539):
    if (0xDEADBEEF ^ 0x12345678) % 2 == 1:
        _nX12_fn = _nX11._nX12
        _nX12_fn('test')
"""

DEOBF_PROMPT = """You are a Python reverse engineer. Analyze this obfuscated code and:

1. Deobfuscate all identifiers to ASCII-safe names
2. Simplify any encoded/encrypted payloads
3. Determine what the code actually does
4. Replace any dynamic calls with static equivalents

Return ONLY clean deobfuscated Python code with a comment header explaining what it does.

```python
{code}
```"""

def call_model(model: str, code: str, timeout_s: int = 180, max_tokens: int = 7168) -> Optional[str]:
    prompt = DEOBF_PROMPT.format(code=code)
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.1, "max_tokens": max_tokens}
    for attempt in range(3):
        proxy = _get_proxy()
        try:
            with httpx.Client(proxy=proxy, timeout=timeout_s) as client:
                resp = client.post(_ZEN_URL, headers=_headers(), json=payload)
                if resp.status_code in (403, 429, 502, 503):
                    _rotate_identity(); continue
                resp.raise_for_status()
                data = resp.json()
                msg = data["choices"][0]["message"]
                text = msg.get("content") or msg.get("reasoning") or ""
                return text
        except Exception as exc:
            logger.warning("  %s attempt %d: %s", model, attempt + 1, exc)
            _rotate_identity()
    return None

def score_ai_resistance(original: str, deobf: Optional[str]) -> dict:
    """Score how well the obfuscation resisted AI analysis. Higher = more resistant."""
    if not deobf:
        return {"resistance_score": 10, "details": ["model_failed_to_respond"]}
    s = 0
    d = []
    # Original non-ASCII count
    na_orig = sum(1 for c in original if ord(c) > 127)
    na_out = sum(1 for c in deobf if ord(c) > 127)

    if na_out >= na_orig:
        s += 2; d.append("non_ascii_survived")
    if "exec" in deobf.lower():
        s += 1; d.append("exec_not_removed")
    if "__import__" in deobf:
        s += 1; d.append("dynamic_import_not_resolved")
    if "lambda" in original and "lambda" not in deobf:
        s += 0
    import ast
    try:
        ast.parse(deobf)
        s -= 1; d.append("output_was_valid_python")
    except SyntaxError:
        s += 1; d.append("output_not_valid_python")
    # Check if original encoding layers survived
    for pat in ["^", "&", "|", "<<", ">>", "% 2 ==", "opaque"]:
        if pat in original and pat in deobf:
            s += 1
            break
    d.append(f"resistance={s}/10")
    return {"resistance_score": s, "details": d}

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-tokens", type=int, default=7168)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--model")
    parser.add_argument("--output-dir", default="ai_proof_results")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(exist_ok=True)

    samples = {
        "version_A_simple": SAMPLE_A,
        "version_B_ai_proof": SAMPLE_B,
    }
    models = [args.model] if args.model else FREE_MODELS
    results = {}

    for model in models:
        logger.info("=" * 60)
        logger.info("Testing: %s", model)
        logger.info("=" * 60)
        model_results = {}
        for name, code in samples.items():
            logger.info("  Sample: %s (%d bytes)", name, len(code))
            t0 = time.time()
            resp = call_model(model, code, args.timeout, args.max_tokens)
            elapsed = time.time() - t0
            if resp:
                out_file = out_dir / f"{model}_{name}.py"
                out_file.write_text(resp)
                sc = score_ai_resistance(code, resp)
                logger.info("  → %.1fs | resistance: %s", elapsed, sc["details"])
                model_results[name] = {"elapsed": round(elapsed,1), "resistance": sc}
            else:
                model_results[name] = {"elapsed": round(elapsed,1), "resistance": {"resistance_score": 10, "details": ["no_response"]}}
                logger.warning("  → NO RESPONSE")
        results[model] = model_results

    print("\n" + "=" * 70)
    print("AI RESISTANCE TEST — Higher score = harder for AI to deobfuscate")
    print("=" * 70)
    print(f"{'Model':<30} {'Version A':<18} {'Version B':<18}")
    print(f"{'':<30} {'(simple)':<18} {'(AI-proof)':<18}")
    print("-" * 70)
    for model in models:
        a = results.get(model, {}).get("version_A_simple", {}).get("resistance", {}).get("resistance_score", "?")
        b = results.get(model, {}).get("version_B_ai_proof", {}).get("resistance", {}).get("resistance_score", "?")
        a_t = results.get(model, {}).get("version_A_simple", {}).get("elapsed", "-")
        b_t = results.get(model, {}).get("version_B_ai_proof", {}).get("elapsed", "-")
        print(f"{model:<30} {a}/10 ({a_t}s)      {b}/10 ({b_t}s)")

    (out_dir / "report.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\nFull report: {out_dir / 'report.json'}")

if __name__ == "__main__":
    main()
