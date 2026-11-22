# Compatibility matrix — measured per combination

Review register, §4: "For every supported combination, record: 1. Build
success. 2. Native loader initialization. 3. Payload execution.
4. Integrity enforcement. 5. Failure behaviour. 6. Relevant mitigation
status."

Each row below is a SHIPPED blob from an actual farm build, parsed with the
project's own `native_harden` readers (and `readelf` / raw Mach-O header
parsing for the fields the reader does not report). "Not supported" is
stated as such rather than omitted — the register asks that unsupported
combinations fail with an explicit diagnostic, and the failure-flood tests
pin that they do.

## The three measured rows

| property | Windows x86-64 | macOS (fat, x86_64 + arm64) | Linux x86-64 |
|---|---|---|---|
| **toolchain that built it** | MSVC `cl.exe` 14.52.37025 + `link.exe` (farm, windows-latest) | Apple `clang` (farm, macos-latest) | `gcc` 14.2.0 (farm ubuntu-22.04) |
| **1. build success** | yes — `payload.pyd`, 126,976 B, valid PE | yes — `payload.dylib`, 350,928 B, valid FAT Mach-O (2 slices) | yes — `payload.so`, 1,052,904 B, valid ELF64 `DYN` |
| **2. native loader initialization** | yes — the driver imports the blob on the producing runner and records `smoke_test.loaded: true` (farm §5x) | yes — same step; `payload.cpython-311-darwin.so loads on Darwin` measured (farm run 44866777087) | yes — same step; `payload.cpython-311-x86_64-linux-gnu.so loads on Linux` |
| **3. payload execution** | the blob's module init runs under the loader after enforcement (§5x) | same, measured on the runner (0.01 s) | same, measured on the runner (0.08 s) |
| **4. integrity enforcement** | merkle + HMAC + provenance pin in the loader; `nx_apply_protections()` inside the blob | same | same |
| **5. failure behaviour** | fails closed — missing blob / wrong pin / bad signature all exit non-zero (§6c) | same | same |
| **6. mitigation status** | **CFG complete** (`GuardFlags 0x10017500`: INSTRUMENTED + FUNCTION_TABLE_PRESENT + export-suppression + longjump), **CET compat present** (debug-dir type-20 record `0x1`), ASLR + DEP + HIGH_ENTROPY_VA | `MH_PIE` **clear**, `MH_NO_HEAP_EXEC` **clear**, `LC_CODE_SIGNATURE` present on arm64 only, **unsigned** (`LC_CODE_SIGNATURE` exists but no valid signature without a Developer ID) — Hardened Runtime absent | `GNU_STACK` RW (NX), `GNU_RELRO` present, **no BIND_NOW**, symbols stripped |

## What each row's mitigation column actually demonstrates

**Windows — the strongest row.** CFG is not a declaration: the guard
function table is populated and `CF_FUNCTION_TABLE_PRESENT` is set, verified
with llvm-readobj and by the project's own parser agreeing bit for bit.
CET compatibility is present in the extended-characteristics record. That is
the complete set a PE can carry for an extension module.

**macOS — the weakest row, and honestly so.** Two facts are now measured
rather than assumed:

* `MH_PIE` is CLEAR on both slices. `-pie` is not accepted on a `-bundle`
  (`filetype 8`), which is what a `.dylib` produced for a CPython extension
  actually is — the same class of mistake as passing `-pie` to a `-shared`
  Linux link (§5x). PIE is an executable property; a loadable bundle is
  relocated by dyld regardless, so its absence is not a runtime hole, but it
  is also not "PIE", and the matrix must not claim it.
* `MH_NO_HEAP_EXEC` is CLEAR: the bundle carries no `MH_NO_HEAP_EXECUTION`
  flag, so hardware NX for the heap is not requested by the image.
* No `LC_CODE_SIGNATURE` on the x86_64 slice; present on arm64 (the
  linker's ad-hoc signature). Neither is a Developer ID signature, so
  Hardened Runtime and notarisation are absent — the external dependency
  the register already records.

**Linux — solid, with one measured gap.** Non-exec stack and RELRO are
present, the object is `DYN`, and the symbol table is stripped. **BIND_NOW
is absent**: `-Wl,-z,now` cannot be used here because setuptools'
`-Bsymbolic-functions` turns it into a link failure (measured in §5x and in
`build_local_cython`). That is a documented, deliberate trade — partial
RELRO instead of full — and it is recorded rather than glossed.

## Fuzzing status — coverage-guided, measured

Review register §5, "Use coverage-guided fuzzing ... retain crash-inducing
inputs as regression fixtures, and apply strict resource limits ... the goal
is not simply zero crashes. It is proving that malformed input cannot
produce an unintended acceptance or bypass."

The seventh pass recorded this row as partial: "the sanitizer coverage
runtime is absent from these interpreter builds, so the campaign is
mutation-driven rather than truly coverage-guided". **That attribution was
wrong.** The cause was three defects in the harness itself (a `REPO` path one
directory short; parser imports inside the fuzz body, after instrumentation
had finished; no seed corpus), each of which produced `cov: 1` across
millions of executions — and `cov: 1` looks the same whether the interpreter
lacks coverage or the harness never asked for it. Corrected and re-measured
in `docs/research/pydeobsbench-2026-11-18.md` §6j.3.

Measured after the fix (Atheris 3.1.0, clang 19 `libclang_rt.fuzzer`):

| target | executions | coverage | corpus grown to | findings |
|---|---|---|---|---|
| pack | 4,075,415 | cov 61 / ft 185 | 24 entries / 9,166 B | none |
| manifest | 454,922 | cov 8 / ft 8 | 3 / 4 B | none |
| elf | 9,163,257 | cov 15 / ft 22 | 4 / 28 B | none |
| pe | 2,960,101 | cov 64 / ft 163 | 70 / 29 KB | none |
| macho | 7,652,368 | cov 27 / ft 52 | 17 / 1,764 B | none |
| state | 10,173,000 | cov 5 / ft 23 | 10 / 1,428 B | none |
| **total** | **34,479,063** | — | 1,925 new units | **zero crashes, zero unintended acceptances** |

The distinguishing signal is that the corpus GROWS (pack 1 → 24, pe 1 → 70)
and `cov`/`ft` climb. The failing shape is `cov: 1 ft: 1` across millions of
executions, which is what the register's earlier "environment limit" looked
like. `tests/test_fuzz_harness.py` pins the three defects that produced it,
because all three are silent: the campaign exits 0 and prints impressive
execution counts either way.

The oracle is the part that matters for the register's wording. An earlier
version asserted that `stream_join` *never* returns data — which a
legitimate pack does — so it fired on correct behaviour on the seventh unit.
The current oracle accepts a join only when the pack's declared total
matches the returned length AND the pack's structure is one the seed builder
actually produced; anything else that decrypts is the bypass being hunted.

## Rows that are NOT supported, and how they fail

| combination | status |
|---|---|
| Linux on musl (Alpine) | **not supported** — the blobs link glibc; a musl host gives `ImportError`/undefined symbol at load, which the loader reports rather than silently falling back to bytecode |
| a CPython ABI different from the build's | **not supported** — the extension suffix encodes the ABI (`cp311`); a mismatch is a load failure, and the `native-only` profile has nothing to fall back to (fail-closed by construction) |
| Windows built with mingw instead of MSVC | supported for loading, but **CFG is unavailable** (GNU ld has no such option) and the verdict reports `unavailable`, not `present` |
| older toolchains (gcc < 14, cl < 14.5, clang < 19) | **not measured**; no claim made |
| ARM64 Windows / ARM64 Linux | **not measured**; the farm matrix builds x86-64 for Windows and Linux and both slices for macOS |

## Reproducibility — measured in two layers, and they differ

This section used to say "not demonstrated". It has now been measured, and
the answer is not one answer: the build has two layers that behave
differently, and collapsing them into a single verdict would be false in
both directions.

### Layer 1 — the AST/transform layer IS reproducible (**measured**)

`NX_BUILD_SEED` seeds `random` and patches `secrets` for the duration of the
transform, restoring both in a `finally`. Measured on this host, same tree,
`obfuscator.core.pipeline.build_pipeline(SRC, seed=424242)` twice:

```
run 1  sha256 b51a2b129103ddd8...  7,528 B
run 2  sha256 b51a2b129103ddd8...  7,528 B
identical: YES
```

and with `seed=999999` the output differs — so the seed is load-bearing
rather than a constant that happens to match. Both facts are pinned in
`tests/test_reproducible_build.py`, together with the assertion that a
seeded transform leaves `secrets.token_bytes` unpatched afterwards (a
leaked patch would make every later nonce in the process predictable).

### Layer 2 — the shipped artefact is NOT byte-identical (**measured, by design**)

Two full `build` runs at `NX_BUILD_SEED=424242` on this host:

```
run 1  sha256 f58d0e2bf0b03277...  267,811 B
run 2  sha256 de68859c31144560...  267,818 B
identical: NO   (7 bytes apart, same size class)
```

Attribution, not speculation: the emitted loader contains

```python
_nx_name = "%s%s%s" % (prefix, _nx_secrets.token_hex(8), suffix)
_nx_now  = _nx_time.time()
_tb_now  = float(_tb_time.time())
```

— a per-build helper identifier minted with `secrets.token_hex(8)` and a
clock read for the trial gate, both drawn at **runtime**, after the seeded
transform has already finished and restored the global patch. `NX_BUILD_SEED`
does not and should not cover them: a loader whose identifiers were
predictable from a build seed would defeat the purpose of minting them.
`NIXON_REPRODUCIBLE=1` seeds the **farm driver's** C-transform seed only and
has no effect on these draws.

### What this means for the register's P2 row

The row asked for "reproducibility experiments", not for a specific verdict.
What has been established:

* same tree + same seed ⇒ **identical transformed source** (proven, twice);
* same tree + same seed ⇒ **non-identical shipped blob**, with the delta
  attributed to two named runtime draws rather than left as "differs";
* "source identity" (the same commit builds) and "reproducible builds" (the
  same commit builds *the same bytes*) remain two distinct claims, as the
  sixth-round review required.

What would close the remaining half is a build mode that also pins the
loader's runtime draws (a build-time nonce substituted into the template
instead of `secrets.token_hex(8)` at load). That is a feature change with a
security cost — predictable loader identifiers — and is therefore recorded
as an open design decision rather than implemented silently here.
