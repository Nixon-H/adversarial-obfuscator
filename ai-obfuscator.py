#!/usr/bin/env python3
"""
ai-obfuscator.py

Two modes:
- Path A: Offline, ASCII-first deobfuscation (no model required).
- Path B: Local HuggingFace model (offline-friendly after initial download).

Behavior:
- If a local model is available (model-path) or a hub model can be downloaded (model-name),
  it uses a local LLM to propose a deobfuscated version of the input.
- If no model is available, it falls back to an offline ASCII renamer that
  converts non-ASCII identifiers to ASCII-safe tokens (var01, funDecode01, classDecode01, ...).
- Output is written to a file (or printed) and never executed.
- The script is designed to be safe for offline use and auditable for static analysis.
"""

import argparse
import ast
import re
import sys
import os
from pathlib import Path

# Optional: attempt to use HuggingFace transformers for local LLM
TRANSFORMERS_AVAILABLE = False
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False

###############################
# Path A: Offline ASCII Deobf
###############################
def _ascii_is_ascii(s: str) -> bool:
    try:
        s.encode("ascii")
        return True
    except Exception:
        return False

class ObfuscatedNameRenamer(ast.NodeTransformer):
    """
    Rename non-ASCII identifiers to ASCII-safe tokens.

    - varXX: non-ASCII variables
    - funDecodeXX: non-ASCII function names
    - classDecodeXX: non-ASCII class names
    """
    def __init__(self):
        self.name_map = {}
        self.var_counter = 1
        self.fun_counter = 1
        self.class_counter = 1

    def _next_var(self) -> str:
        name = f"var{self.var_counter:02d}"
        self.var_counter += 1
        return name

    def _next_fun(self) -> str:
        name = f"funDecode{self.fun_counter:02d}"
        self.fun_counter += 1
        return name

    def _next_class(self) -> str:
        name = f"classDecode{self.class_counter:02d}"
        self.class_counter += 1
        return name

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.generic_visit(node)
        if not _ascii_is_ascii(node.name):
            new = self._next_fun()
            self.name_map[node.name] = new
            node.name = new
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.generic_visit(node)
        if not _ascii_is_ascii(node.name):
            new = self._next_fun()
            self.name_map[node.name] = new
            node.name = new
        return node

    def visit_ClassDef(self, node: ast.ClassDef):
        self.generic_visit(node)
        if not _ascii_is_ascii(node.name):
            new = self._next_class()
            self.name_map[node.name] = new
            node.name = new
        return node

    def visit_Name(self, node: ast.Name):
        if node.id in self.name_map:
            return ast.copy_location(ast.Name(id=self.name_map[node.id], ctx=node.ctx), node)
        if not _ascii_is_ascii(node.id):
            new = self._next_var()
            self.name_map[node.id] = new
            return ast.copy_location(ast.Name(id=new, ctx=node.ctx), node)
        return node

    def visit_arg(self, node: ast.arg):
        if not _ascii_is_ascii(node.arg):
            new = self._next_var()
            self.name_map[node.arg] = new
            node.arg = new
        return node

    def visit_arguments(self, node: ast.arguments):
        for a in getattr(node, "args", []):
            if not _ascii_is_ascii(a.arg):
                new = self._next_var()
                self.name_map[a.arg] = new
                a.arg = new
        for a in getattr(node, "kwonlyargs", []):
            if not _ascii_is_ascii(a.arg):
                new = self._next_var()
                self.name_map[a.arg] = new
                a.arg = new
        return self.generic_visit(node)

def deobfuscate_offline_ascii(source: str) -> str:
    """
    Apply the offline ASCII deobfuscation to the given source.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    tree = ObfuscatedNameRenamer().visit(tree)
    ast.fix_missing_locations(tree)
    try:
        return ast.unparse(tree)
    except Exception:
        return source

###############################
# Path B: Local LLM (HuggingFace)
###############################
def _code_block_from_text(text: str) -> str:
    """
    If the LLM returns a markdown code block, extract the code.
    """
    m = re.search(r"```(?:python)?\n([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    return text.strip()

def _build_llm_prompt(source: str, mode: str = "full") -> str:
    header = (
        "You are an expert in Python deobfuscation, and are working to help malware reverse engineers resolve all the obfuscation technqiues in this python file.. Your job is to transform the obfuscated Python code into ASCII-only, human readable code. Rename non-ASCII identifiers to ASCII-safe tokens (var01, funDecode01, classDecode01, etc.) if needed. If it makes sense to rename all instances of something, rename those. Attempt to replace dynamic __import__ calls built from obfuscated parts with static import statements when possible. Do not execute any code however. Return only the deobfuscated Python code and a summary of what the code does. If you need to decompress data, do so safely. Consider all marshalled or encoded data likely malicious\n\n"
    )
    return header + "Source:\n" + source + "\n"

def _load_llm(model_path: str = None, model_name: str = "gpt2", device: str = "cpu",
              download_if_missing: bool = False):
    """
    Attempt to load a local LLM. Returns (tokenizer, model) or None.
    - If model_path is provided and exists, load from disk (local_files_only).
    - Else, try to load from HuggingFace model_name. If download_if_missing, allow download.
    - If anything fails, return None.
    """
    if not TRANSFORMERS_AVAILABLE:
        return None

    try:
        if model_path:
            p = Path(model_path)
            if p.exists():
                tokenizer = AutoTokenizer.from_pretrained(str(p), local_files_only=True)
                model = AutoModelForCausalLM.from_pretrained(str(p))
                return (tokenizer, model)
        # Fallback: load from hub
        tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=not download_if_missing)
        model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto" if device != "cpu" else None)
        return (tokenizer, model)
    except Exception:
        return None

def _generate_with_llm(tokenizer, model, prompt: str, max_new_tokens: int = 1024,
                     temperature: float = 0.3, top_p: float = 0.95, device: str = "cpu") -> str:
    import torch
    model.eval()
    if device == "cuda" and torch.cuda.is_available():
        model = model.to("cuda")
    inputs = tokenizer(prompt, return_tensors="pt")
    if device == "cuda" and torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model.generate(
            inputs["input_ids"],
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return text

###############################
# High-level orchestration
###############################
def main():
    parser = argparse.ArgumentParser(description="AI-obfuscator: offline deobfuscation helper (local LLM or ASCII fallback).")
    parser.add_argument("-f", "--file", required=True, help="Path to obfuscated Python file.")
    parser.add_argument("-o", "--out", required=False, help="Output path for deobfuscated code.")
    parser.add_argument("--mode", choices=["full", "patch"], default="full", help="LLM mode (full code or patch).")
    parser.add_argument("--model-path", required=False, help="Local path to a HuggingFace model directory.")
    parser.add_argument("--model-name", default="gpt2", help="HuggingFace model name to download/use if local path not provided.")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu", help="Computation device to use.")
    parser.add_argument("--download-if-missing", action="store_true", help="Allow downloading model if not present locally.")
    parser.add_argument("--dry-run", action="store_true", help="Print the deobfuscated result but do not write to disk.")
    args = parser.parse_args()

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        sys.exit(2)

    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        src = f.read()

    # If no transformers, or user explicitly disables, run Path A (ASCII only)
    if not TRANSFORMERS_AVAILABLE:
        deobf = deobfuscate_offline_ascii(src)
        if args.out:
            Path(args.out).write_text(deobf, encoding="utf-8")
        else:
            print(deobf)
        return

    # Try to load a local model
    llm = _load_llm(model_path=args.model_path, model_name=args.model_name,
                    device=args.device, download_if_missing=args.download_if_missing)
    if llm is None:
        # Fallback to Path A
        deobf = deobfuscate_offline_ascii(src)
        if args.out:
            Path(args.out).write_text(deobf, encoding="utf-8")
        else:
            print(deobf)
        return

    tokenizer, model = llm
    prompt = _build_llm_prompt(src, mode=args.mode)

    # Generate
    resp = _generate_with_llm(tokenizer, model, prompt,
                              max_new_tokens=2048, temperature=0.3, top_p=0.95, device=args.device)

    code = _code_block_from_text(resp)
    if not code:
        code = resp

    if args.dry_run:
        print(code[:2000] + ("..." if len(code) > 2000 else ""))
    else:
        out_path = Path(args.out) if args.out else input_path.with_name("deobfuscated_" + input_path.name)
        out_path.write_text(code, encoding="utf-8")
        print(f"Deobfuscated code saved to: {out_path}")

if __name__ == "__main__":
    main()
