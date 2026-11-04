# Transform Defects Found by Building Payloads the Corpus Never Tried

**2026-11.** Sixteen defects, all found by execution rather than inspection. The ones that
mattered were invisible until a failure was made to **say why**.

## Product defects (12)

| # | defect | how it surfaced |
|---|---|---|
| 1 | dataclass fields deleted whenever the class had a method (`only_annotations` guard) | new `constructs_source.py` payload |
| 2 | dataclass field renamed in its declaration but not in `self.x` | same |
| 3 | encoder encoded `nonlocal` in one place and not the other → `SyntaxError` | same |
| 4 | JIT template replayed closures in a new scope → `no binding for nonlocal` | `[FATAL] Exec failed` |
| 5 | JIT template's assignment landed in a class body → `name _nx_tmpl_N is not defined` | same |
| 6 | `_noise_generator`: 8 threads × 64 MB `os.urandom`, no pause (Linux read a file instead) | hang, `faulthandler` trace |
| 7 | `_spam_rdtsc`: 4 threads unthrottled on arm64; payload succeeded then hung | hang, `faulthandler` trace |
| 8 | inner exec failed silently in the Silent build | `runpy` → `SystemExit: 1` with no message |
| 9 | artefact self-destructed on a false redundancy positive, leaving 0 bytes | four concurrent runs |
| 10 | `--portable` shipped a Linux `.so` inside an "OS-independent" artefact | dist listing |
| 11 | Python ≤3.11 emitted `DeprecationWarning` into the artefact's output | reproduced under 3.11 |
| 12 | `_nx_ftable` undefined — the call-graph table was emitted after its call sites | CI payload job |

## What actually found them

Not reasoning. Four instrumentation changes did all the work:

1. removing the self-destruct (so artefacts stopped deleting themselves)
2. `[FATAL]`/`[BLOCKED]` always reaching stderr, in both build variants
3. `faulthandler.dump_traceback_later` in the CI runner
4. recording the dist directory and the artefact's own stderr on failure

Three rounds were spent on hypotheses — recursion limit, shell quoting, a `.so` dependency that did
not exist. **All three were wrong.** Every fix that survived came from a printed failure.

## Protections that were tuned down, and what happened to them

Making the matrix green by weakening defences was the wrong trade. Four were restored:

- temporal redundancy + self-destruct: back behind `--strict-detections`
- noise intensity (64 MB, no pause): back behind the same flag
- rdtsc unthrottled spin: back behind the same flag
- JIT coverage of methods: **fixed properly** (template is now a local)

**One limitation is genuine:** a function declaring `nonlocal` cannot be re-executed from source in
a fresh scope, because the enclosing cell does not exist there. It is excluded, and that is a limit
of the technique rather than a bug.

## Coverage

`portable-build-matrix.yml`: 26 jobs on every push — 3 OSes × Python 3.10–3.14, two payload types,
audits, crash diagnostics. `portable-deep-matrix.yml`: 30 jobs on demand — 12 configurations, 8
isolated packing flags, 12 isolated ladder transforms. Every job capped at 45 minutes.

**Still not isolated:** 253 of 273 ladder flags. **Not testable here:** `--stego`, whose artefact
is an image carrier this harness does not load.

## Found by isolating single flags (same week, second pass)

Building a flag catalogue (274 flags, generated from `scripts/build.py`) and
running one flag at a time found seven more, all invisible in bundled builds:

| flag | defect |
|---|---|
| `--adaptive` | two `_nx_ftable` assignments, the second silently replacing the first: a call site written for `bytes` resolved through a table whose entry 0 was `sum` → `TypeError: can't concat int to bytes` |
| all flags | JIT templates `exec`'d into an **empty** namespace, so any wrapped function reading a module global raised `NameError` inside `<jit_N>` |
| `--stego` | decoder compared against a double-escaped `"\\u200b"`, so every bit read as 1 and the payload decoded to `0xFF` bytes |
| `--stego` | decoder built `chr()` code points instead of decoding UTF-8, corrupting every non-ASCII identifier |
| `--attention-poison` | junk injected at `body[0]`, ahead of `nonlocal` → `SyntaxError` |
| `--data-obfuscation` | storage virtualizer replaced `count = 0` with a state slot, deleting the cell a nested `nonlocal` needs |
| `--adaptive` (open) | CI-only `NameError: _nx_M`; the transform pipeline is randomised, so some orderings emit a name they never bind |
| `--data-obfuscation` | artefacts imported `scripts.runtime.oram_sim`, so they could not run outside the source tree. The ORAM is stdlib-only and is now inlined; two further bugs surfaced doing it (a renamer split the inheritance chain, and inserting the block statement-by-statement reversed it) |

`--stego` had been written off as "cannot be tested by this harness". It never
was: it was broken, twice.

### Verdict classes, because "FAIL" was overstating

The first sweep reported eighteen failing shards. Most were the harness's fault:
the builder refuses unsound combinations (`[CONFLICT]`), some flags exist only in
the packed-loader path, and some arguments were misread. The runner now reports
PASS, FAIL, CONFLICT, CATALOGUE, NONSTANDALONE and SLOW separately — because a
harness that cannot tell a product defect from its own mistake is worse than no
harness.

## Security posture after the fixes

Four protections were tuned down to make the matrix green. All are back, and the
defaults are now chosen so that a defence cannot destroy the operator's work:

| protection | default | `--strict-detections` |
|---|---|---|
| temporal redundancy | one call, mismatch reported | three calls, compares, **deletes the artefact** and exits 666 |
| entropy noise | 256 KB per 200 ms | **64 MB per iteration, no pause** |
| rdtsc spam | 50 ms pause per iteration | **unthrottled** |
| JIT template transform | covers functions and **methods** | same |

Verified in built artefacts rather than by reading source: a strict build contains
three `if not True` guards, the 64 MB noise buffer, and `__ro.remove`; a default
build contains `if not False`, so those branches cannot be reached.

### Why the defaults differ

- The self-destruct fired on **false positives** and deleted the operator's file,
  leaving a 0-byte artefact that ran silently forever after. A defence that
  destroys work on a wrong guess is worse than the attack it models.
- Unthrottled noise and rdtsc spinning **starved interpreter shutdown** on ARM:
  payloads printed correct output and then hung until killed.

Both are real defences, so they are opt-in rather than removed.

### One genuine limitation

A function declaring `nonlocal` cannot be replayed from source in a fresh scope —
the enclosing cell does not exist there. The JIT transform skips those functions.
That is a limit of the technique, not a defect to fix.
