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
from pathlib import Path

# Optional: attempt to use HuggingFace transformers for local LLM
TRANSFORMERS_AVAILABLE = False
try:
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

class _NameCollector(ast.NodeVisitor):
    """Collect identifiers in source order before any name is generated."""

    KINDS = {"var": "var", "fun": "funDecode", "class": "classDecode"}

    def __init__(self):
        self.used = set()
        self.originals = {}

    def _add(self, name, kind="var"):
        if not name or not isinstance(name, str):
            return
        self.used.add(name)
        if not _ascii_is_ascii(name):
            self.originals.setdefault(name, kind)

    def visit_FunctionDef(self, node):
        self._add(node.name, "fun")
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self._add(node.name, "class")
        self.generic_visit(node)

    def visit_Name(self, node):
        self._add(node.id)
        self.generic_visit(node)

    def visit_arg(self, node):
        self._add(node.arg)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        self._add(node.attr)
        self.generic_visit(node)

    def visit_keyword(self, node):
        self.generic_visit(node)

    def visit_alias(self, node):
        local = node.asname or node.name.split(".", 1)[0]
        if local != "*":
            self._add(local)
        self.generic_visit(node)

    def visit_Global(self, node):
        for name in node.names:
            self._add(name)

    visit_Nonlocal = visit_Global

    def visit_ExceptHandler(self, node):
        self._add(node.name)
        self.generic_visit(node)

    def visit_MatchAs(self, node):
        self._add(getattr(node, "name", None))
        self.generic_visit(node)

    visit_MatchStar = visit_MatchAs

    def visit_MatchMapping(self, node):
        self._add(node.rest)
        self.generic_visit(node)


class _ScopeInfo:
    def __init__(self, node, parent=None, kind="module", owner_class=None):
        self.node = node
        self.parent = parent
        self.kind = kind
        self.owner_class = owner_class
        self.bindings = {}
        self.assignments = {}
        self.attribute_assignments = []
        self.globals = set()
        self.nonlocals = set()
        self.writes = set()


class _ClassInfo:
    def __init__(self, node, scope, base_names=()):
        self.node = node
        self.scope = scope
        self.base_names = tuple(base_names)
        self.members = set()
        self.methods = {}


class _BindingCollector(ast.NodeVisitor):
    """Collect conservative, lexical proofs for internal call targets."""

    def __init__(self):
        self.root = None
        self.scope = None
        self.scopes = []
        self.classes = {}
        self.signatures = {}
        self.original_names = {}

    def _bind(self, name, value):
        if name:
            self.scope.bindings.setdefault(name, set()).add(value)
            self.scope.writes.add(name)

    def _unknown(self, name):
        self._bind(name, ("unknown", None))

    def _enter(self, node, kind, owner_class=None, params=()):
        parent = self.scope
        self.scope = _ScopeInfo(node, parent, kind, owner_class)
        self.scopes.append(self.scope)
        for param in params:
            self._unknown(param.arg)
        return self.scope

    def visit_Module(self, node):
        self.root = self._enter(node, "module")
        for statement in node.body:
            self.visit(statement)

    def visit_FunctionDef(self, node):
        self._bind(node.name, ("function", node))
        self.signatures[node] = tuple(
            arg.arg for arg in list(node.args.args) +
            list(node.args.kwonlyargs))
        for decorator in node.decorator_list:
            self.visit(decorator)
        self.visit(node.args)
        if node.returns is not None:
            self.visit(node.returns)
        owner_class = self.scope.owner_class
        if self.scope.kind == "class":
            owner_class.members.add(node.name)
            owner_class.methods[node.name] = node
        params = (list(node.args.posonlyargs) + list(node.args.args)
                  + list(node.args.kwonlyargs))
        if node.args.vararg is not None:
            params.append(node.args.vararg)
        if node.args.kwarg is not None:
            params.append(node.args.kwarg)
        self._enter(node, "function", owner_class, params)
        if owner_class is not None and params:
            decorators = {d.id for d in node.decorator_list
                          if isinstance(d, ast.Name)}
            first = params[0].arg
            if "classmethod" in decorators:
                self.scope.bindings[first] = {("class", owner_class.node)}
            elif "staticmethod" not in decorators:
                self.scope.bindings[first] = {("instance", owner_class.node)}
        for statement in node.body:
            self.visit(statement)
        self.scope = self.scope.parent

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        self.signatures[node] = tuple(
            arg.arg for arg in list(node.args.args) +
            list(node.args.kwonlyargs))
        self.visit(node.args)
        params = (list(node.args.posonlyargs) + list(node.args.args)
                  + list(node.args.kwonlyargs))
        if node.args.vararg is not None:
            params.append(node.args.vararg)
        if node.args.kwarg is not None:
            params.append(node.args.kwarg)
        self._enter(node, "lambda", self.scope.owner_class, params)
        self.visit(node.body)
        self.scope = self.scope.parent

    def visit_ClassDef(self, node):
        self._bind(node.name, ("class", node))
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        info = _ClassInfo(
            node, self.scope,
            (base.id for base in node.bases if isinstance(base, ast.Name)))
        self.classes[node] = info
        info.scope = self._enter(node, "class", info)
        for statement in node.body:
            self.visit(statement)
        self.scope = self.scope.parent

    def visit_Name(self, node):
        self.original_names[id(node)] = node.id
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self._unknown(node.id)

    def _assign(self, target, value):
        if isinstance(target, ast.Name):
            if self.scope.kind == "class":
                self.scope.owner_class.members.add(target.id)
            self.scope.assignments.setdefault(target.id, []).append(value)
            self.scope.writes.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                self._assign(element, None)
        elif isinstance(target, ast.Starred):
            self._assign(target.value, None)
        elif isinstance(target, ast.Attribute):
            self.visit(target.value)
            self.scope.attribute_assignments.append((target, value))
        else:
            self.visit(target)

    def visit_Assign(self, node):
        self.visit(node.value)
        for target in node.targets:
            self._assign(target, node.value)

    def visit_AnnAssign(self, node):
        self.visit(node.annotation)
        if node.value is not None:
            self.visit(node.value)
        if isinstance(node.target, ast.Name):
            if self.scope.kind == "class":
                self.scope.owner_class.members.add(node.target.id)
            if node.value is not None:
                self._assign(node.target, node.value)
        elif node.value is not None:
            self._assign(node.target, node.value)
        else:
            self.visit(node.target)

    def visit_NamedExpr(self, node):
        self.visit(node.value)
        self._assign(node.target, node.value)

    def visit_AugAssign(self, node):
        self.visit(node.target)
        self.visit(node.value)

    def visit_For(self, node):
        self.visit(node.iter)
        self.visit(node.target)
        for statement in node.body + node.orelse:
            self.visit(statement)

    visit_AsyncFor = visit_For

    def visit_With(self, node):
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                self.visit(item.optional_vars)
        for statement in node.body:
            self.visit(statement)

    visit_AsyncWith = visit_With

    def visit_alias(self, node):
        local = node.asname or node.name.split(".", 1)[0]
        if local != "*":
            self._unknown(local)

    def visit_Global(self, node):
        self.scope.globals.update(node.names)

    def visit_Nonlocal(self, node):
        self.scope.nonlocals.update(node.names)

    def visit_ExceptHandler(self, node):
        if node.type is not None:
            self.visit(node.type)
        if node.name is not None:
            self._unknown(node.name)
        for statement in node.body:
            self.visit(statement)

    def visit_MatchAs(self, node):
        if node.name is not None:
            self._unknown(node.name)
        self.generic_visit(node)

    visit_MatchStar = visit_MatchAs

    def visit_MatchMapping(self, node):
        if node.rest is not None:
            self._unknown(node.rest)
        self.generic_visit(node)

    def _lookup(self, name, scope):
        origin = scope
        while scope is not None:
            if name in scope.globals:
                return self.root.bindings.get(name, set())
            if name in scope.nonlocals:
                target = scope.parent
                while target is not None and target.kind != "module":
                    if target.kind == "function" and name in target.bindings:
                        return target.bindings[name]
                    target = target.parent
                return set()
            if name in scope.bindings:
                return scope.bindings[name]
            if scope.kind == "class" and origin.kind != "class":
                scope = scope.parent
                continue
            scope = scope.parent
        return set()

    def _value(self, node, scope):
        if isinstance(node, ast.Name):
            name = self.original_names.get(id(node), node.id)
            bindings = self._lookup(name, scope)
            if len(bindings) == 1:
                return next(iter(bindings))
        elif isinstance(node, ast.Call):
            called = self._value(node.func, scope)
            if called is not None and called[0] == "class":
                return ("instance", called[1])
        return None

    def _class_for(self, node, scope):
        value = self._value(node, scope)
        if value is not None and value[0] in {"class", "instance"}:
            return value[1]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and \
                node.func.id == "super" and not node.args and \
                scope.owner_class is not None:
            return scope.owner_class.node
        return None

    def _nonlocal_target(self, name, scope):
        target = scope.parent
        while target is not None and target.kind != "module":
            if target.kind == "function" and name in target.bindings:
                return target
            target = target.parent
        return None

    def finish(self):
        for scope in self.scopes:
            for name in scope.globals & scope.writes:
                self.root.bindings.setdefault(name, set()).add(
                    ("unknown", None))
            for name in scope.nonlocals & scope.writes:
                target = self._nonlocal_target(name, scope)
                if target is not None:
                    target.bindings.setdefault(name, set()).add(
                        ("unknown", None))
        changed = True
        resolved = set()
        while changed:
            changed = False
            for scope in self.scopes:
                for name, values in scope.assignments.items():
                    if len(values) != 1 or name in scope.bindings:
                        continue
                    if name in scope.globals or name in scope.nonlocals:
                        continue
                    value = self._value(values[0], scope)
                    if value is not None:
                        scope.bindings[name] = {value}
                        resolved.add((scope, name))
                        changed = True
        for scope in self.scopes:
            for name, values in scope.assignments.items():
                if (scope, name) not in resolved and \
                        name not in scope.globals and name not in scope.nonlocals:
                    scope.bindings.setdefault(name, set()).add(
                        ("unknown", None))
        for scope in self.scopes:
            for target, _value in scope.attribute_assignments:
                class_node = self._class_for(target.value, scope)
                if class_node in self.classes:
                    self.classes[class_node].members.add(target.attr)
        return self

    def class_lineage(self, node):
        if node in self.classes:
            yield node
        info = self.classes.get(node)
        if info is None:
            return
        for base_name in info.base_names:
            bindings = self._lookup(base_name, info.scope.parent)
            if len(bindings) == 1:
                value = next(iter(bindings))
                if value[0] == "class":
                    yield from self.class_lineage(value[1])

    def has_member(self, class_node, name):
        return any(name in self.classes[candidate].members
                   for candidate in self.class_lineage(class_node))

    def method(self, class_node, name):
        for candidate in self.class_lineage(class_node):
            method = self.classes[candidate].methods.get(name)
            if method is not None:
                return method
        return None


class ObfuscatedNameRenamer(ast.NodeTransformer):
    """Rename every non-ASCII identifier using one precomputed mapping.

    The old implementation allocated ASCII names while walking the tree. That
    made recursive calls resolve before the function was mapped, left
    global/nonlocal declarations and import aliases in non-ASCII form, and let
    generated names shadow existing ASCII bindings. Collecting and assigning all
    names in a first pass removes every one of those ordering failures.
    """

    def __init__(self, tree=None):
        self.name_map = {}
        self.used = set()
        self.analysis = None
        self._scopes = []
        self._classes = []
        if tree is not None:
            self.prepare(tree)

    def prepare(self, tree):
        collector = _NameCollector()
        collector.visit(tree)
        self.used = set(collector.used)
        counters = {"var": 1, "fun": 1, "class": 1}
        for original, kind in collector.originals.items():
            prefix = _NameCollector.KINDS[kind]
            while True:
                candidate = f"{prefix}{counters[kind]:02d}"
                counters[kind] += 1
                if candidate not in self.used:
                    break
            self.name_map[original] = candidate
            self.used.add(candidate)
        self.analysis = _BindingCollector()
        self.analysis.visit(tree)
        self.analysis.finish()
        self._scopes = [self.analysis.root]
        self._classes = []
        return self

    def _map(self, name):
        return self.name_map.get(name, name)

    def _binding(self, node):
        if not isinstance(node, ast.Name):
            return None
        name = self.analysis.original_names.get(id(node), node.id)
        bindings = self.analysis._lookup(name, self._scopes[-1])
        if len(bindings) == 1:
            return next(iter(bindings))
        return None

    def _class_for(self, node):
        value = self.analysis._value(node, self._scopes[-1])
        if value is not None and value[0] in {"class", "instance"}:
            return value[1]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and \
                node.func.id == "super" and not node.args and self._classes:
            return self._classes[-1].node
        return None

    def _signature_preserved(self, node):
        for decorator in getattr(node, "decorator_list", ()):
            if not isinstance(decorator, ast.Name) or decorator.id not in {
                    "classmethod", "staticmethod"} or \
                    self.analysis._lookup(decorator.id, self._scopes[-1]):
                return False
        return True

    def _callable(self, node):
        if isinstance(node, ast.Lambda):
            return node
        value = self._binding(node)
        if value is not None:
            if value[0] == "function":
                return value[1]
            if value[0] == "class":
                return self.analysis.method(value[1], "__init__")
        if isinstance(node, ast.Attribute):
            class_node = self._class_for(node.value)
            if class_node is not None:
                return self.analysis.method(class_node, node.attr)
        return None

    def _rename_keyword(self, call, label):
        if label not in self.name_map:
            return False
        function = self._callable(call.func)
        if function is None or not self._signature_preserved(function):
            return False
        return label in self.analysis.signatures.get(function, ())

    def visit_FunctionDef(self, node):
        node.name = self._map(node.name)
        for decorator in node.decorator_list:
            self.visit(decorator)
        self.visit(node.args)
        if node.returns is not None:
            self.visit(node.returns)
        self._scopes.append(next(
            scope for scope in self.analysis.scopes if scope.node is node))
        for statement in node.body:
            self.visit(statement)
        self._scopes.pop()
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        self.visit(node.args)
        scope = next(scope for scope in self.analysis.scopes
                     if scope.node is node)
        self._scopes.append(scope)
        self.visit(node.body)
        self._scopes.pop()
        return node

    def visit_ClassDef(self, node):
        node.name = self._map(node.name)
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        info = self.analysis.classes[node]
        self._scopes.append(info.scope)
        self._classes.append(info)
        for statement in node.body:
            self.visit(statement)
        self._classes.pop()
        self._scopes.pop()
        return node

    def visit_Name(self, node):
        node.id = self._map(node.id)
        return node

    def visit_arg(self, node):
        node.arg = self._map(node.arg)
        return self.generic_visit(node)

    def visit_Attribute(self, node):
        class_node = self._class_for(node.value)
        rename = class_node is not None and \
            self.analysis.has_member(class_node, node.attr)
        node.value = self.visit(node.value)
        if rename:
            node.attr = self._map(node.attr)
        return node

    def visit_Call(self, node):
        rename_labels = [
            keyword.arg is not None and self._rename_keyword(node, keyword.arg)
            for keyword in node.keywords
        ]
        node.func = self.visit(node.func)
        for argument in node.args:
            self.visit(argument)
        for keyword, rename in zip(node.keywords, rename_labels):
            self.visit(keyword.value)
            if rename:
                keyword.arg = self._map(keyword.arg)
        return node

    def visit_keyword(self, node):
        return self.generic_visit(node)

    def visit_Import(self, node):
        split = any(
            alias.asname is None and "." in alias.name and
            self._map(alias.name.split(".", 1)[0]) != alias.name.split(".", 1)[0]
            for alias in node.names)
        if not split:
            for alias in node.names:
                self.visit(alias)
            return node
        statements = []
        for alias in node.names:
            local = alias.asname or alias.name.split(".", 1)[0]
            mapped = self._map(local)
            if alias.asname is None and "." in alias.name and mapped != local:
                binding = ast.alias(name=local, asname=mapped)
                ast.copy_location(binding, alias)
                statements.append(ast.copy_location(
                    ast.Import(names=[binding]), node))
                statements.append(ast.copy_location(
                    ast.Import(names=[alias]), node))
            else:
                self.visit(alias)
                statements.append(ast.copy_location(
                    ast.Import(names=[alias]), node))
        return statements

    def visit_alias(self, node):
        if node.asname is not None:
            node.asname = self._map(node.asname)
        else:
            local = node.name.split(".", 1)[0]
            mapped = self._map(local)
            if mapped != local:
                node.asname = mapped
        return node

    def visit_Global(self, node):
        node.names = [self._map(name) for name in node.names]
        return node

    visit_Nonlocal = visit_Global

    def visit_ExceptHandler(self, node):
        self.generic_visit(node)
        if node.name is not None:
            node.name = self._map(node.name)
        return node

    def visit_MatchAs(self, node):
        self.generic_visit(node)
        if getattr(node, "name", None) is not None:
            node.name = self._map(node.name)
        return node

    visit_MatchStar = visit_MatchAs

    def visit_MatchMapping(self, node):
        self.generic_visit(node)
        if node.rest is not None:
            node.rest = self._map(node.rest)
        return node


def deobfuscate_offline_ascii(source: str) -> str:
    """
    Apply the offline ASCII deobfuscation to the given source.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    tree = ObfuscatedNameRenamer(tree).visit(tree)
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
    model.eval()
    import torch
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
