"""rust_callgraph.py

Purpose:
    Answer, mechanically, whether a Rust runtime module can actually
    run.

Architectural Role:
    ``scripts/classify_features.py`` used to call a feature
    "IMPLEMENTED" if a module with a similar NAME appeared in
    ``runtime/src/lib.rs``.  That is a name match, not a call path: 12
    modules (jit, rop, rop_dispatch, hwid_bind, hw_entropy,
    code_genome, cache_bound, branch_entangle, multicore_entangle,
    hpc_detect, hydra, oram) are declared and compiled and can never be
    reached from ``init_runtime`` — even with every flag true.

    This module walks the real call graph instead:

    * ``module_declarations()`` — the ``pub mod`` names in lib.rs.
    * ``reachable_modules()`` — the modules ``init_runtime`` actually
      references, directly or through one hop inside lib.rs.
    * ``flag_modules()`` — flag name -> modules referenced inside that
      flag's ``if config.enable_x { ... }`` block.
    * ``default_true_flags()`` — the flags that are ``true`` in
      ``Default``.
    * ``flags_set_true_elsewhere()`` — flags any other code sets true.

Security Relevance:
    "Compiled but unreachable" protects nothing.  A feature may only be
    reported as live when the call path exists, the flag is on, and the
    artefact shows it ran.
"""

from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNTIME_SRC = os.path.join(ROOT, "runtime", "src")
RELAY_SRC = os.path.join(ROOT, "relay", "src")

_MOD_DECL = re.compile(r"^\s*pub\s+mod\s+([A-Za-z_][A-Za-z0-9_]*)\s*;", re.M)
_CONFIG_FIELD = re.compile(r"pub\s+(enable_[a-z0-9_]+)\s*:\s*bool")
_DEFAULT_TRUE = re.compile(r"(enable_[a-z0-9_]+)\s*:\s*true")
_MODULE_REF = re.compile(r"\b([a-z_][a-z0-9_]*)\s*::")


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def lib_rs() -> str:
    return _read(os.path.join(RUNTIME_SRC, "lib.rs"))


def module_declarations(lib_text: str | None = None) -> set:
    """The ``pub mod`` names declared in runtime/src/lib.rs."""
    return set(_MOD_DECL.findall(lib_text if lib_text is not None else lib_rs()))


def _block_after(text: str, start: int) -> str:
    """The brace-balanced body starting at the first '{' at/after start."""
    open_at = text.find("{", start)
    if open_at < 0:
        return ""
    depth = 0
    for i in range(open_at, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[open_at + 1:i]
    return text[open_at + 1:]


def init_runtime_body(lib_text: str | None = None) -> str:
    """The body of ``pub fn init_runtime``."""
    text = lib_text if lib_text is not None else lib_rs()
    m = re.search(r"pub\s+fn\s+init_runtime\s*\(", text)
    if not m:
        return ""
    return _block_after(text, m.end())


def _refs(body: str, declared: set) -> set:
    """Module names from ``declared`` that ``body`` references."""
    return {m for m in _MODULE_REF.findall(body) if m in declared}


def _module_source(name: str) -> str:
    """The source of ``runtime/src/<name>.rs`` (or '')."""
    return _read(os.path.join(RUNTIME_SRC, name + ".rs"))


def reachable_modules(lib_text: str | None = None) -> set:
    """The modules ``init_runtime`` reaches, transitively.

    ``init_runtime`` references modules directly; those modules
    reference others (e.g. ``hpc_key`` calls into ``hpc``).  A
    module is reachable only if the closure actually gets there — that
    is the difference between "compiled" and "can run".
    """
    text = lib_text if lib_text is not None else lib_rs()
    declared = module_declarations(text)
    reached = _refs(init_runtime_body(text), declared)
    # One hop through functions DEFINED in lib.rs (private helpers).
    for fn in re.findall(r"\b([a-z_][a-z0-9_]*)\s*\(", init_runtime_body(text)):
        if fn in declared:
            continue
        m = re.search(r"fn\s+%s\s*\(" % re.escape(fn), text)
        if m:
            reached |= _refs(_block_after(text, m.end()), declared)
    # Transitive closure across module files.
    frontier = set(reached)
    while frontier:
        nxt = set()
        for name in frontier:
            nxt |= _refs(_module_source(name), declared) - reached
        reached |= nxt
        frontier = nxt
    return reached


def flag_blocks(lib_text: str | None = None) -> dict:
    """flag name -> modules referenced inside its enable_x block."""
    text = lib_text if lib_text is not None else lib_rs()
    declared = module_declarations(text)
    out = {}
    for m in re.finditer(r"if\s+config\.(enable_[a-z0-9_]+)\s*\{", text):
        out[m.group(1)] = _refs(_block_after(text, m.end()), declared)
    return out


def config_flags(lib_text: str | None = None) -> set:
    """Every ``enable_*: bool`` field on RuntimeConfig."""
    text = lib_text if lib_text is not None else lib_rs()
    return set(_CONFIG_FIELD.findall(text))


def default_true_flags(lib_text: str | None = None) -> set:
    """The flags that are ``true`` in ``RuntimeConfig::default``."""
    text = lib_text if lib_text is not None else lib_rs()
    m = re.search(r"impl\s+Default\s+for\s+RuntimeConfig", text)
    body = _block_after(text, m.end()) if m else ""
    return set(_DEFAULT_TRUE.findall(body))


def _crate_sources(kind: str = "runtime") -> str:
    base = RUNTIME_SRC if kind == "runtime" else RELAY_SRC
    chunks = []
    for name in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        if name.endswith(".rs"):
            chunks.append(_read(os.path.join(base, name)))
    return "\n".join(chunks)


def flags_set_true_elsewhere(lib_text: str | None = None) -> set:
    """Flags set ``true`` anywhere outside ``Default``.

    The relay constructs ``RuntimeConfig`` with ``Default::default()``
    and never overrides a field, so this is normally empty — which is
    exactly the finding: 22 of 27 flags are off and nothing turns them
    on.
    """
    text = lib_text if lib_text is not None else lib_rs()
    default_true = default_true_flags(text)
    everything = text + "\n" + _crate_sources("runtime") + "\n" + _crate_sources("relay")
    set_anywhere = set()
    for m in re.finditer(r"(enable_[a-z0-9_]+)\s*[:=]\s*true", everything):
        set_anywhere.add(m.group(1))
    return set_anywhere - default_true


def unreachable_modules(lib_text: str | None = None) -> set:
    """Declared modules that ``init_runtime`` can never reach."""
    declared = module_declarations(lib_text)
    return declared - reachable_modules(lib_text) - {"platform"}
