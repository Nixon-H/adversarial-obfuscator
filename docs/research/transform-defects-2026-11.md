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

## Determinism: the cause of every "intermittent" failure

Two builds of the same payload produced different artefacts. That is why a flag
passed locally and failed in CI, why each sweep reported a different set of red
shards, and why every theory about the flakiness (recursion limit, shell quoting,
a `.so` dependency, `FUNC_HARD`) was untestable.

Bisected by opt-level, comparing builds with the **encryption key masked** — the
key is random by design and masked comparisons are the only honest test:

| level | two runs |
|---|---|
| 0 | identical |
| 1 | identical |
| 2 | identical |
| 3 | **different** |

`resolve(3) - resolve(2)` is exactly one flag: `decoys`. The seed never reached
it — `phase01_obfuscate.py` built its option dict without `'seed'`, so the decoy
injector fell back to `secrets.SystemRandom()`.

Fixed by threading `--seed` into the transform options. Level-3 builds are now
identical once the per-build key is masked, which is as reproducible as a build
can be.

Three earlier "fixes" (two `hash()` uses and the fingerprinter seed) were real
bugs but downstream of the actual cause. Two of my own reproducibility
measurements were bogus: one checksummed a stale file twice, one diffed paths that
were never written. The masked bisect is what settled it.

**Result: all 29 flag-isolation shards green.**

## Correction: the temporal-redundancy self-destruct never ran

An audit of this session flagged the removal of the redundancy self-destruct as the
most severe security regression. Checked against the tree, that is not what
happened:

`execute_redundant` has **no call sites** -- not now, and not before the change.
`grep` finds one occurrence in `sources.py`, and it is the `def`. The class the
template defines is injected into every artefact and then never invoked, so:

* the three-call comparison never ran,
* the self-destruct never fired,
* and the "hardware fault attack" response was dead code in both modes.

What the change did was stop a *dead* destructive routine from being reachable if
someone later wired it up -- which is worth keeping, but it is not a reduction in
protection that was ever in effect.

The honest positions are: wire it up soundly (only for functions that can be shown
free of side effects, since re-running user code is unsound in general), or delete
it so it stops reading like a defence that exists. It is neither, today, and this
note exists so the next reader does not trust the table above.

## Hardened by default (final state)

The protections were opt-in for most of this work: `--strict-detections` had to be
asked for, so a plain build carried the weaker posture. That is backwards for a
protection tool, and it is now the other way round.

`--strict-detections` defaults to **True**; `--fast` selects the reduced profile.

The one value that changed in the process is the entropy noise, 64 MB per
iteration with no pause -> **16 MB per 100 ms per thread**. That is a correction
rather than a relaxation: the unbounded loop starved payloads on Windows and
macOS, and an artefact that hangs protects nothing. Measured with the hardened
profile: the constructs payload builds and runs in 0.56 s.

The interpreter-integrity verdict blocks on **every** platform, including Windows.
Its three false positives were each traced to a specific check -- a zero module
handle read as tampering, a builtins *repr* comparison, and the paths that
remained -- and each was fixed rather than exempted. The guard now names its
reason (`win-exe-*`, `win-probe-*`, `builtins-*`, `probe-exception-*`), so a
future false positive is one CI run instead of a bisect.

Verified in a real default artefact: three `if not True` branches, the 16 MB noise
buffer, `[BLOCKED] interpreter-integrity` with `exit(3)`, and the rdtsc spammer.

## Counter-REA shields, ported from BLA

`obfuscator/anti_rea.py` ports the source-level half of
[BLA (qybaihe/bla)](https://github.com/qybaihe/bla), a counter-reverse-engineering
tool aimed at AI analysis agents. Its three layers act on what an analyzer
*extracts* rather than on how the code runs, so they transfer to a Python payload:

| layer | what it adds |
|---|---|
| **Poison** | architecture-mirage notes, evidence-contract summaries claiming analysis is complete, and documentation-designated canary credentials |
| **Exhaust** | a decoy call graph (each decoy references three others, so there is no leaf) plus high-salience bait procedures named for licence/key/entitlement checks |
| **Muddle** | chaff tagged per build, so two builds do not present the same inventory |

Defaults: on, with `--anti-rea-level {stealth,balanced,maximum}` and
`--no-anti-rea` to opt out. Measured on the `secure_demo` fixture: 750 KB → 2.5 MB
of artefact, runtime 0.3 s → 1.0 s, audit 12/12 pass.

**What was deliberately not ported:**

* **No compliance/medical bait.** BLA gates fake COPPA/IEC-62304 text behind an
  explicit opt-in because it targets classifier behaviour. Omitted.
* **No URL-parsing exploits.** BLA's canary URLs depend on specific bugs in one
  analyzer's WHATWG parser and its redaction path. Reproducing them here would
  make our protection depend on someone else's defect.
* **No JS/WASM/ASAR/DEX surface.** This project ships Python artefacts.

The shields append only. Nothing existing is rewritten, so a payload cannot change
behaviour because of them — `tests/test_anti_rea.py` asserts the payload produces
identical output with and without them, that no decoy is ever called, and that the
same seed reproduces the same shields.
