# Semantic lowering — operation registry design (V10 headline adopt)

Status: DESIGN + registry + first families (pure-Python AST form) +
verified-140 native kernel (Cython `.pyx` helpers, per-build renamed
symbols) on the `--pytoc` path — see Phase 5 below.

## What V10 does (vendor claim, now VERIFIED at 140 in this repo)

Call sites for Python builtins replaced with native implementations in
the protection kernel: 20 families / 140 ops (VERIFIED — enforced by
tests/test_opcount_truth.py + tests/test_lowering_parity_141.py),
registry-driven, default-ON
families (I/O, scalar, string, container, service, protocol, function,
import, fusion, list, dict, set, tuple, bytes, range) + opt-in
(arithmetic, truth, slice, format, augassign).
Per-build kernel symbols; fusion collapses lowered chains; 0.19x–1.56x
of CPython 3.12 measured.

Audited truth (2026-09, enforced by tests/test_opcount_truth.py): the
verified-140 count holds (was 141 before str.decode was removed —
Python 3 has no str.decode, only bytes.decode). 20 families hold 148
registry entries (147 unique names): 139 callable ops + 8 AST node-kind
markers (BinOp, Compare, BoolOp, Not, Subscript, JoinedStr,
FormattedValue, AugAssign — Phase-2 only, no runtime function yet).
The native kernel implements verified-140 ops (``NATIVE_OPS`` in
obfuscator/kernel_gen.py): those 139 callable ops + the ``fuse``
dispatch, with identical call shapes in ``obfuscator/lowering_shim.py``.
Every one of the verified-140 ops routes at least one real call site
through the kernel — proven by behavioral parity tests
(tests/test_lowering_parity_141.py: each lowered call == the same plain
call; file name kept for stable references). The original 51 op
names/shapes are untouched; growth is purely additive.

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
specifies (15 on, 5 opt-in).

## Cipher hierarchy (which XOR/ChaCha20 goes where)

Three cipher helpers exist; they are LAYERED, not duplicated:

- `obfuscator/core/utils.py::fast_xor_bytes` — the WIRED blob cipher.
  Build-time payload encryption (`pipeline.py` fallback/native blobs)
  + key-split derivation. Per-build key, transport-grade.
- `obfuscator/chacha20.py` — RFC 8439 ChaCha20 + HMAC-SHA256 AEAD for
  STRING literals (`string_crypto.py` sessions, `transforms.py`
  `StringLiteralObfuscator(mode="chacha20")`, default OFF, opt-in).
  The SAME core is emitted verbatim as the runtime stub
  (`STUB_TEMPLATE`), so build-time and artifact share one audited
  implementation. Use for string confidentiality; not for blobs.
- `pipeline.py::_xor_decrypt` (loader template) — the artifact-side
  mirror of `fast_xor_bytes` (decrypt-then-exec own payload only).
- `cryptography` (AES-CTR, declared in requirements.txt) is tried
  FIRST at build time (`pipeline.py::_check_aes_ctr`); XOR is the
  graceful fallback, never the preference.

Rule of thumb: strings → ChaCha20 (AEAD, allowlisted); blobs →
AES-CTR preferred, fast-XOR fallback; never swap the layers.

## Operation registry (20 families)

Default ON (15): io, scalar, string, container, service, protocol,
function, import, fusion, list, dict, set, tuple, bytes, range.
Opt-in (5): arithmetic, truth, slice, format, augassign.

Each family entry: {ops: [dotted names / node kinds], default_on: bool,
note: str}. `resolve_families(spec)` parses the `--lowering` CSV
("all", "none", "+arithmetic", "-io", bare names which ADD to defaults).

### Method-call routing (receiver handling)

Bare builtins (`len(x)`) rewrite to `_nxk_len(x)`. Explicit dotted
roots (`str.join(sep, it)`, `dict.fromkeys("ab")`) rewrite with no
prepend — the source already names the class. Object method calls
(`s.split(",")`, `xs.append(1)`, `d.get("k")`) route through the
matching dotted op by PREPENDING the receiver AST
(`_nxk_str_split(s, ",")`), but ONLY when the (receiver-name,
method) pair resolves to exactly one registry op
(`_recv_class()` in obfuscator/lowering.py maps receiver naming
conventions to kernel classes). Same-named methods shared by several
classes (`clear`/`copy`/`count`/`decode`/`hex`/`index`/`pop`/`remove`)
resolve per receiver (`lst.clear()` -> `_nxk_list_clear`,
`d.clear()` -> `_nxk_dict_clear`, `st.clear()` -> `_nxk_set_clear`);
unknown receivers (`obj.len()`, `foo.bar()`, `q.clear()`) are NEVER
rewritten. The receiver AST is prepended once, first — evaluation
order preserved, shims take `(recv, *a, **k)` and delegate to the
exact unbound method, so semantics are identical.

## Phase plan

1. Registry + resolver + pure-Python shim (this doc's companion code).
2. AST lowering pass per family (calls first, then operators).
3. `--lowering` flag already exists in build.py — thread spec through.
4. Cython native kernel on the --pytoc path (per-build renamed symbols,
   fusion dispatch) — replaces the shim import, same call shapes.
5. Perf budget per family (measure against CPython like V10 publishes).

## Measured Phase-1 shim overhead (host evidence, NOT vendor numbers)

Vendor claim (archive/third_party_samples/nyami-v10.md:39-40,131-132):
native kernel at 0.19x-1.56x of plain CPython 3.12 (import 0.37x,
container 0.86x-0.94x, scalar 0.81x-0.82x); pure-compute families
dropped from 2x-6x to 1.2x-1.6x overhead natively. Sub-1.0x figures
only make sense for a NATIVE kernel — our Phase-1 pure-Python shim
adds one extra Python call frame per op, so it can never beat plain
CPython on microbenchmarks. Measured here instead (same method V10
publishes: per-family timing vs plain CPython).

Measured (host=nixon, Linux x86_64, CPython 3.13.5, 2026-09-22):
`NIXON_LOG_REDIRECT=0 python3 scripts/benchmark/lowering_perf.py`
(N=20000 timed iterations per op per arm, best-of-5
time.perf_counter, warmup included; ratio = shim/plain per call;
family figure = geometric mean of its op ratios; `input`/`open`
interactive, async `aiter`/`anext`, site-interactive
`breakpoint`/`help`/`copyright`/`credits`/`license`, and Phase-2
node-kind families excluded — see script header).

| family | ops timed | geomean shim/plain | min op | max op |
|---|---|---|---|---|
| io | 1 | 1.46x | 1.46x | 1.46x |
| scalar | 17 | 2.41x | 1.12x | 3.56x |
| string | 30 | 2.62x | 1.21x | 4.11x |
| container | 9 | 2.02x | 1.54x | 3.37x |
| protocol | 4 | 2.11x | 1.79x | 2.64x |
| service | 16 | 2.02x | 0.96x | 4.68x |
| range | 4 | 2.04x | 1.69x | 2.80x |
| function | 10 | 2.08x | 1.68x | 2.51x |
| import | 1 | 2.42x | 2.42x | 2.42x |
| fusion | 1 | 2.68x | 2.68x | 2.68x |
| list | 11 | 2.49x | 1.50x | 3.91x |
| dict | 11 | 1.77x | 1.15x | 4.29x |
| set | 12 | 1.76x | 1.07x | 2.75x |
| tuple | 2 | 3.84x | 3.81x | 3.88x |
| bytes | 3 | 2.06x | 1.52x | 3.28x |

Overall per-op range: 0.96x (`exec`, noise around parity on a ~6.5us
op) to 4.68x (`globals`, two extra frame hops on a ~50ns op).
Per-family geomeans: 1.46x-3.84x — i.e. Phase-1 shim overhead sits
at roughly 1.5x-3.8x per family on this host, ABOVE the vendor's
native 0.19x-1.56x band, as expected for a pure-Python reference
kernel. Every timed op also passed behavioral parity
(shim result == plain result) under the timing loop.

## Measured NATIVE kernel overhead (same host, --native build)

Same benchmark, third arm added (`--native build` renders a fresh
per-build-symbols kernel and cythonizes it, then times the COMPILED
`.so` on the same thunks). Bare builtins only (49/132 ops — method
style ops take `(recv, *args)` and report n/a; same shapes, different
thunk plumbing).

Measured (host=nixon, Linux x86_64, CPython 3.13.5, 2026-09-23):
`NIXON_LOG_REDIRECT=0 python3 scripts/benchmark/lowering_perf.py
--native build --iterations 3000 --repeats 2` (N=3000 best-of-2;
smaller N than the shim table above — ratios are N-independent past
warmup, verified stable across runs).

| family | native ops | geomean native/plain | min | max | parity |
|---|---|---|---|---|---|
| container | 9 | 2.48x | 1.43x | 4.30x | ok |
| function | 10 | 2.76x | 2.13x | 3.81x | ok |
| protocol | 3 | 3.14x | 2.56x | 4.00x | ok |
| range | 4 | 2.61x | 1.91x | 3.97x | ok |
| scalar | 12 | 4.02x | 1.81x | 5.55x | ok |
| service | 11 | 2.64x | 1.05x | 5.16x | ok |

Overall native: geomean **2.95x**, range 1.05x–5.55x, 49/49 parity ok.
Honest reading: our Cython kernel is thin passthroughs
(`def impl(*a, **k): return _bi.op(*a, **k)` — one compiled frame +
one Python call), NOT a hand-optimized C kernel, so it sits ABOVE the
shim on microbenchmarks (extra import + dispatch layers) and far above
the vendor's 0.19x–1.56x native band. The vendor numbers remain
NOT-reproduced in-repo; what IS proven here is behavioral parity
(native result == plain result on all 49 timed ops) and per-build
symbol uniqueness — the obfuscation properties, not speed. Speed is
the documented tradeoff of lowering depth (see --lowering opt-outs).

Reproduce: `NIXON_LOG_REDIRECT=0 timeout 550 python3
scripts/benchmark/lowering_perf.py [--iterations N] [--repeats R]
[--families CSV] [--json PATH] [--native build|.pyx|.so]`. Full per-op table prints as
markdown to stdout. Smoke lock: tests/test_lowering_perf.py runs the
same harness at N=200 asserting finite positive ratios + parity
(no absolute perf assertions — numbers vary by machine).
