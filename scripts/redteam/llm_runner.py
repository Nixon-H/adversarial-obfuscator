"""
llm_runner.py

Purpose:
Uses LLM-based deobfuscation (OpenAI, Anthropic, DeepSeek) to assess
whether an obfuscated source's original algorithm intent can be
recovered by AI analysis.

Architectural Role:
Red-team attack runner that probes semantic obfuscation effectiveness.
Attempts each configured LLM provider in priority order (OpenAI >
Anthropic > DeepSeek). Falls back to static AST analysis when no API
keys are available. Produces a JSON result with intent_recovered flag
and confidence level.

Execution Context:
Called from unified_attack.run_redteam_attack(). Requires API keys
via environment variables (OPENAI_API_KEY, ANTHROPIC_API_KEY,
DEEPSEEK_API_KEY). Falls back to AST-based function name extraction
when no keys are available.

Dependencies:
- openai (optional), anthropic (optional), httpx (optional, for DeepSeek)
- Standard library (json, logging, os, re, time, ast)

Security Relevance:
LLM-based deobfuscation is an emerging threat to code obfuscation.
If an LLM can recover the original algorithm intent, the obfuscation
is considered semantically broken. This is the only runner that
operates on source code rather than binaries.

Maintenance Notes:
- Provider priority: OpenAI > Anthropic > DeepSeek. The first provider
  with a configured API key that returns a result is used.
- The source excerpt is limited to 4000 characters to stay within
  LLM context windows.
- Each LLM call uses temperature=0.1 for deterministic responses.
- The JSON response is extracted with a regex fallback; malformed
  responses result in a default "intent not recovered" result.
"""

import json
import logging
import os
import re
import time

log = logging.getLogger(__name__)


def _try_openai(source_excerpt, api_key):
    try:
        import openai
    except ImportError:
        return None
    try:
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a deobfuscation analyst. Analyze the following obfuscated code. "
                        "Identify the original algorithm, recover the intent, and suggest deobfuscation strategies. "
                        "Respond in JSON with keys: intent_recovered (bool), confidence_level (0-1), "
                        "original_algorithm_guessed (str), deobfuscation_suggestions (list of str)."
                    ),
                },
                {"role": "user", "content": f"Obfuscated code:\n```python\n{source_excerpt[:4000]}\n```"},
            ],
            temperature=0.1,
            max_tokens=500,
        )
        content = resp.choices[0].message.content
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return {"intent_recovered": False, "confidence_level": 0.0, "original_algorithm_guessed": "unknown", "deobfuscation_suggestions": []}
    except Exception as e:
        log.warning(f"OpenAI API call failed: {e}")
        return None


def _try_anthropic(source_excerpt, api_key):
    try:
        import anthropic
    except ImportError:
        return None
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=500,
            system="You are a deobfuscation analyst. Respond in JSON with keys: intent_recovered, confidence_level, original_algorithm_guessed, deobfuscation_suggestions.",
            messages=[{"role": "user", "content": f"Analyze this obfuscated code:\n```python\n{source_excerpt[:4000]}\n```"}],
        )
        content = resp.content[0].text
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return {"intent_recovered": False, "confidence_level": 0.0, "original_algorithm_guessed": "unknown", "deobfuscation_suggestions": []}
    except Exception as e:
        log.warning(f"Anthropic API call failed: {e}")
        return None


def _try_deepseek(source_excerpt, api_key):
    try:
        import httpx
    except ImportError:
        return None
    try:
        resp = httpx.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are a deobfuscation analyst. Respond in JSON with keys: intent_recovered, confidence_level, original_algorithm_guessed, deobfuscation_suggestions."},
                    {"role": "user", "content": f"Analyze this obfuscated code:\n```python\n{source_excerpt[:4000]}\n```"},
                ],
                "temperature": 0.1,
                "max_tokens": 500,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return {"intent_recovered": False, "confidence_level": 0.0, "original_algorithm_guessed": "unknown", "deobfuscation_suggestions": []}
    except Exception as e:
        log.warning(f"DeepSeek API call failed: {e}")
        return None


def run_llm_attack(source_path, output_dir):
    start = time.time()

    result = {
        "intent_recovered": False,
        "confidence_level": 0.0,
        "original_algorithm_guessed": "unknown",
        "deobfuscation_suggestions": [],
        "provider_used": None,
        "analysis_time_ms": 0.0,
        "attack": "llm",
        "status": "completed",
        "error": None,
    }

    try:
        with open(source_path, "r") as f:
            source = f.read()
    except Exception as e:
        result["error"] = f"Cannot read source: {e}"
        result["status"] = "failed"
        result["analysis_time_ms"] = (time.time() - start) * 1000
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "llm_results.json")
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2, default=str)
        return result

    excerpt = source[:4000]

    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")

    response_data = None

    if openai_key:
        response_data = _try_openai(excerpt, openai_key)
        if response_data:
            result["provider_used"] = "openai"
    if response_data is None and anthropic_key:
        response_data = _try_anthropic(excerpt, anthropic_key)
        if response_data:
            result["provider_used"] = "anthropic"
    if response_data is None and deepseek_key:
        response_data = _try_deepseek(excerpt, deepseek_key)
        if response_data:
            result["provider_used"] = "deepseek"

    if response_data:
        result["intent_recovered"] = response_data.get("intent_recovered", False)
        result["confidence_level"] = response_data.get("confidence_level", 0.0)
        result["original_algorithm_guessed"] = response_data.get("original_algorithm_guessed", "unknown")
        result["deobfuscation_suggestions"] = response_data.get("deobfuscation_suggestions", [])
    else:
        import ast
        try:
            tree = ast.parse(source)
            functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            result["original_algorithm_guessed"] = ", ".join(functions[:5]) if functions else "unknown"
            result["deobfuscation_suggestions"] = [
                "No LLM provider available; use static analysis results",
                f"Detected {len(functions)} functions in source",
            ]
            result["confidence_level"] = 0.1
        except Exception as e:
            result["deobfuscation_suggestions"] = [f"Static analysis fallback: {e}"]
            result["confidence_level"] = 0.0

    result["analysis_time_ms"] = (time.time() - start) * 1000

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "llm_results.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    return result
