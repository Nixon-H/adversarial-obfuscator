# Semantic lowering — operation registry design (V10 headline adopt)

Status: DESIGN + registry + first families (pure-Python AST form). The
NATIVE kernel half (Cython `.pyd` helpers, per-build renamed symbols) is
future work on the `--pytoc` path — see Phase 5 below.

## What V10 does (vendor claim, unverified)

Call sites for Python builtins replaced with native implementations in
the protection kernel: 14 families, 141 ops, registry-driven, default-ON
families (I/O, scalar, string, container, service, protocol, function,
import, fusion) + opt-in (arithmetic, truth, slice, format, augassign).
Per-build kernel symbols; fusion collapses lowered chains; 0.19x–1.56x
of CPython 3.12 measured.

## Our architecture (additive, staged)

```
source.py
  │  Phase 1 (NOW): AST lowering to _nxk_* kernel-call stubs
  │    obfuscator/lowering.py :: lower_source(source, families) -> str
  │    - registry FAMILIES: name -> {ops, default_on, note}
  │    - rewrites Call/Attribute/Subscript/BinOp nodes per family
  │    - output imports the kernel shim: from _nxk import ... (stub names)
  ▼
obfuscated.py (still Python — runs WITHOUT the native kernel via
  obfuscator/lowering_shim.py, a pure-Python _nxk reference kernel)
  │  Phase 2 (later): --pytoc emits the NATIVE kernel
  │    Cython helpers replacing lowering_shim with per-build renamed
  │    symbols + fusion dispatch (mirrors wrapper_jit class_id convention)
  ▼
protected.pyd (builtins gone from the artifact, as V10 claims)
```

Why this staging is honest: the AST transform is testable TODAY
(semantics preserved, pure Python); the native kernel is a separate
artifact with its own ABI/API/version story. V10's perf numbers
(0.19x–1.56x) only make sense natively — our Phase-1 stubs add call
overhead, documented per family, and families default exactly as V10
specifies (9 on, 5 opt-in).

## Operation registry (14 families)

Default ON (9): io, scalar, string, container, service, protocol,
function, import, fusion.
Opt-in (5): arithmetic, truth, slice, format, augassign.

Each family entry: {ops: [dotted names / node kinds], default_on: bool,
note: str}. `resolve_families(spec)` parses the `--lowering` CSV
("all", "none", "+arithmetic", "-io", explicit lists).

## Phase plan

1. Registry + resolver + pure-Python shim (this doc's companion code).
2. AST lowering pass per family (calls first, then operators).
3. `--lowering` flag already exists in build.py — thread spec through.
4. Cython native kernel on the --pytoc path (per-build renamed symbols,
   fusion dispatch) — replaces the shim import, same call shapes.
5. Perf budget per family (measure against CPython like V10 publishes).
