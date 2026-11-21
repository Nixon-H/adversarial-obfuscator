# PyDeObsBench — adversarial reconstruction benchmark, 2026-11-18

A separate system from the protection compiler, by design: **the protection
system must not be its own judge.** This package never imports the pipeline's
scoring or verification code.

AI attacker: **DeepSeek V4.1 Flash via Mistral**
(`mistral/deepseek-v4-1-flash-1017`, through the OpenCode CLI). No other
Mistral model and no Kern model was used.

---

## 1. What the harness measures

| metric | how | why it matters |
|---|---|---|
| source reconstruction | exact identifier match in the AI answer, plus payload-string peel | what an analyst would call "getting the source back" |
| secret recovery | plaintext scan, decrypted-payload scan, AI answer, runtime output | four independent channels; the best of them counts |
| algorithm recovery | payload-only vocabulary overlap + numeric markers (e.g. `0x7FEB352D`) | an attacker who reproduces behaviour without recovering names has still won |
| patch resistance | tamper the pack, tamper + recompute the unkeyed Merkle anchor | if either survives, the integrity gate is decoration |
| offline derivation | reimplement the section join from what the artefact carries | separates "protected" from "merely obfuscated" |
| leakage | ELF symbols/strings from the embedded blob, temp files, RWX mappings, stdout | the channels a careless build leaks through |
| build cost | wall-clock build time per artefact | protection that costs minutes may not ship |

### Targets (ground truth)

| target | shape | secrets | names |
|---|---|---|---|
| `tiny` | minimal control | 2 | 4 |
| `inventory` | business logic + class | 4 | 5 |
| `algo` | algorithmic (xorshift-multiply finaliser) | 0 | 4 |
| `cipher` | SHA-256 keystream + HMAC seal | 1 | 3 |

`algo` exists specifically because source similarity is a bad proxy there: the
model could describe the behaviour correctly while recovering no identifier.

---

## 2. Results — DS 4.1 Flash via Mistral

### Round 2 (after the native-path and rename fixes, same day)

The first round measured artefacts whose **native module never loaded**: the
loader silently ran the bytecode fallback, so every "native" number below was
really a bytecode measurement. Four independent defects caused it (§5, bugs
8–11). These are the re-measured numbers with the native path live.

**Max profile, all four targets** (`report/run-max-1794985118.json`):

| target | names | secrets | algo overlap | native blob |
|---|---|---|---|---|
| algo | **0/4** | — | 0.08 | 1 export, 0 payload names |
| cipher | **0/3** | **0/1** | 0.00 | 1 export, 0 payload names |
| inventory | **0/5** | **0/4** | 0.00 | 1 export, 0 payload names |
| tiny | **0/4** | **0/2** | **n/a** ¹ | 1 export, 0 payload names |

¹ `tiny`'s ground truth is "SHA-256 over (salt || payload), first 16 hex
chars". After removing generic English and loader vocabulary only
`{chars, salt}` remain, which is too few terms to divide by. The harness
reports `n/a` with the basis rather than a ratio — see §5 finding 18. An
earlier version scored this cell **0.75** from a pure-loader answer: a metric
that *improves* when the model understands less is worse than no metric.

Every row: RELRO on, NX on, `.symtab` stripped, `.comment` removed, exactly
one dynamic export (`PyInit_payload`).

**Absolute and licence-bound profiles:**

| profile | target | names | secrets | algo overlap | pack derivable | native blob |
|---|---|---|---|---|---|---|
| absolute | inventory | **0/5** | **0/4** | 0.10 | yes | hardened, 1 export |
| absolute | cipher | **0/3** | **0/1** | 0.22 | yes | hardened, 1 export |
| absolute-licensed | inventory | **0/5** | **0/4** | 0.10 | **no** | not derivable |
| absolute-licensed | cipher | **0/3** | **0/1** | 0.22 | **no** | not derivable |

The licensed row is the control that matters: `HMAC failed on 8/8 sections
(key not derivable)` and the embedded native blob is **not a valid object
file** — it is sealed under the token-derived key, so the module is not
recoverable from the artefact alone even though both the shares and the blob
ciphertext travel inside it.

The `algorithm_text` on the best-scoring absolute run was a line-accurate
description of the **loader** (`loader_reversed: True`), with no payload
behaviour. That is recorded as its own metric, not folded into the
algorithm score — see §3.


### Round 1 (before the native fix — retained for comparison)

> **These numbers are NOT native-path measurements.** The artefact executed
> bytecode. Every identifier/secret conclusion still holds (the bytecode
> payload is sealed too), but "native" in this table means "the build
> succeeded", not "the .so ran".

### Max profile (`--package layers=25 zips=3 stego`), unbound

| target | names | secrets | payload algorithm | pack derivable |
|---|---|---|---|---|
| tiny | **0/4** | **0/2** | not recovered | yes |
| inventory | **0/5** | **0/4** | not recovered | yes |
| algo | **0/4** | — | not recovered | yes |
| cipher | **0/3** | **0/1** | not recovered | yes |

### Absolute profile, unbound

| target | names | secrets | pack derivable |
|---|---|---|---|
| inventory | **0/5** | **0/4** | yes |
| cipher | **0/3** | **0/1** | yes |

### Absolute profile, licence-bound (the control that matters)

| target | names | secrets | **pack derivable** |
|---|---|---|---|
| inventory | **0/5** | **0/4** | **no** |
| cipher | **0/3** | **0/1** | **no** |

Offline attack on the bound artefact reports:

```
HMAC failed on 4/4 sections (key not derivable)
```

So: **no original identifier, no secret, and no offline payload recovery** at
the licence-bound profile. At the unbound profiles everything identifier- and
secret-wise is also blocked, but the payload is recoverable offline by design
(keys must ship for a standalone run).

---

## 3. What the model DID recover — and why that matters

The AI did not get the payload, but it produced a line-accurate description of
the **loader**:

> "Identity gate: allows import only when module name is `__main__`/`__mp_main__`
> AND `abspath(__file__) == abspath(sys.argv[0])`; otherwise writes
> `[BLOCKED] identity` to stderr and exits 2."

> "Self-integrity check: reads its own file lines, removes every line
> containing the literal expected-constant `[_NX_SELF_CK, _NX_SELF_HM,
> _NX_SELF_TOK]` values."

That is a complete, actionable map of the gates — including the variable names
and the exact filter rule. It is recorded as its own metric (`loader_reversed`)
rather than folded into the algorithm score, because **reversing the loader is
a real result that a keyword-overlap score hides.**

---

## 4. Attack validation using the model's own disclosure

The model told us exactly how the self-check works. We then used that:

| attack | result |
|---|---|
| control (unpatched) | rc 0, payload ran |
| tamper the section pack, stamps untouched | **rc 137, killed** (`Self-check error: merkle expected=… got=…`) |
| tamper the pack **and recompute the unkeyed Merkle root** | **rc 137, killed** |
| force the Merkle comparison to pass | inconclusive — the patch broke unrelated imports first |
| patch `_NX_SELF_CK` to all-zeros | **rc 137, killed** |

The third row is the interesting one. An attacker who reads the model's
description can recompute the Merkle root (it is unkeyed, so anyone can), and
the artefact **still dies** — because a second, independent HMAC anchor covers
the same content, keyed with `_NX_SELF_HK`. Two anchors, different key
material: that is what defence in depth buys here.

---

## 5. Bugs the harness found

### In the product (2 real, 1 functional)

| # | bug | severity |
|---|---|---|
| 1 | subset-sum predicate read `dp[target]` with `target` up to 7992 against a 4096-entry table; 11/1500 instances overflowed and the AND-ed real branch was **silently skipped** | **functional — ~0.7% of builds lost real code** |
| 2 | opaque predicates were **false 52–76% of the time** (guard requires even; operands were odd random values), so they skipped real code | **functional — broke roughly half of every branch touched** |
| 3 | junk functions were **absent from the shipped `.so`** (`static` + uncalled + `-flto` = deleted) | efficacy: cost build time, bought nothing |

All three fixed and re-measured (see `mistral.md` for the measurements).

### In the product, round 2 — the native path (4, all silent)

These are the most serious defects found in the whole exercise, because every
one of them made the artefact **quietly do the wrong thing** rather than fail:

| # | bug | how it was caught |
|---|---|---|
| 8 | the build wrote the native blob as **base64**; the loader decoded **b85** → `ValueError`, swallowed by a broad `except`, so the payload ran from bytecode. A 161 KB ELF was embedded and never decoded. | `strings` on the artefact showed no payload identifiers while the bytecode "worked" |
| 9 | the loader imported as `payload_native`, but the blob exports `PyInit_payload` → `ImportError: dynamic module does not define module export function`, also swallowed | extracting the blob and importing it directly |
| 10 | the hybrid loader was generated from the **unpacked** blob dict (the XOR pass lives only in the packed-loader branch), so it XORed a plaintext ELF into garbage | decoding `NATIVE_BLOBS` showed the raw `\x7fELF` magic |
| 11 | the AST layer rewrites `if __name__ == "__main__":` to **single quotes**; the native prep only replaced the double-quoted form, so the payload's `__main__` block compiled as a guard that never fires | a marker payload printed its module body but not its main block |

All four are now pinned by `tests/test_native_path_live.py`, including one
end-to-end test (`NIXON_E2E_NATIVE=1`) that builds, runs, and asserts both the
module body and the `__main__` block executed.

### In the product, round 2 — measured leaks and gaps

| # | finding | measured | fix |
|---|---|---|---|
| 12 | the C transform was **non-deterministic**: dead blocks were injected inside `enum`/`struct`/`union` bodies, producing `expected identifier before '{' token` | fuzzing 40 seeds: **38/40** compiled; 2 failures, both from `enum __Pyx_ReferenceSharing {` | aggregate-body tracking in `insert_dead_blocks`; now **80/80** seeds compile (`scripts/fuzz_c_transform.py`) |
| 13 | the shipped `.so` was **not hardened and not stripped**: 355 static symbols, no RELRO bind-now, no stack protector, no `_FORTIFY_SOURCE`, `.comment` leaking `GCC: (Debian 14.2.0-19)` | `readelf`/`nm` on the extracted blob | `-fPIC -fstack-protector-strong -D_FORTIFY_SOURCE=2 -fcf-protection=full -Wl,-z,relro,-z,now -Wl,-z,noexecstack`, then `strip --strip-all` + `objcopy --remove-section=.comment`; **verified on the object** (build prints `RELRO=True NX=True symtab=stripped dynamic-exports=['PyInit_payload']`) |
| 14 | the redundant `setup.py build_ext` step used weaker flags **and** failed to link (`-Bsymbolic-functions` + `-z now` → relocation in read-only `.text`), so the whole native build reported `[ERROR]` and shipped bytecode | build log | the second compile is gone; the direct hardened object is what ships |
| 15 | **method names leaked from the native blob**: `payload._nx_b4b307.fetch_ledger`, `payload._nx_b4b307.reconcile`, `__pyx_pf_..._4reconcile`. The class was renamed and every method inside it was not. | new `probe_native_blob`: **2/5** ground-truth names readable from the blob while the bytecode path leaked **0** | `rename_internal` enabled on both the native and fallback compile paths |
| 16 | the internal-rename proof only accepted `self.m()` / `cls.m()` receivers, so the ordinary `rec = C(); rec.m()` pattern **blocked** the rename | target `main()` does exactly this: `fetch_ledger` still leaked after 15 was fixed | proof extended to non-escaping local instances (`_local_instance_names`): bound once by `name = Class(...)` inside a function, never reassigned, never passed/returned/yielded/stored, never captured by a closure. Six soundness cases verified by hand; all six behave correctly |
| 17 | the farm uploaded the **raw** source while the local build compiled an AST-obfuscated one, so non-local OS blobs were weaker on every axis (no symbol rename, no string sealing, no CFG flattening) | code inspection of the two paths | farm now uploads the same AST-mutated source (syntax-checked before upload) |

After 15 + 16: `native payload names in blob strings: []` on the re-run.

### In the harness itself (5, all false positives)

| # | bug | how it showed up |
|---|---|---|
| 4 | plaintext probe reported a leak on every artefact | `SALT` matched `_NX_CUSTOMER_SALT` and `# [NX_SB_FRAG:SALT]` |
| 5 | `algorithm_overlap` counted the *loader's* vocabulary | scored 0.33–0.60 "recovery" while zero payload terms were present |
| 6 | `names_from_payload` used substring matching | `seal` matched `"bad string seal"`, `main` matched `"__main__"` — made ABSOLUTE look worse than MAX |
| 7 | `--licence` passed as one argv item | `token=<path> env-only` read as a single filename → ENOENT |
| 18 | `algorithm_overlap` still counted **generic English** | `tiny` scored **0.75** from an answer that described only the loader; its ground-truth words `{over, first, payload, salt, chars}` are ordinary English |

Finding 18's first "fix" was worse than the bug: I excluded any ground-truth
term the artefact text leans on, which shrank `tiny`'s denominator to the two
words that still matched and drove the score from 0.75 to **1.00** — a metric
that improves as the model understands less. The shipped fix is honest in two
ways: generic English is dropped by an explicit stopword list, and a ratio
built on fewer than four distinctive terms is **not reported at all**
(`algorithm_overlap: null`, with `overlap_basis` and `overlap_note`). `tiny`
now reads `n/a (insufficient distinctive terms (2: ['chars', 'salt']))`.

Every one of 4–7 and 18 would have produced a **false conclusion** if trusted.
A benchmark that is not itself audited reports whatever its own bugs say. This
is why each metric was re-derived from the raw probe data by hand after the
run, not taken from the summary line.

---

## 5b. Runtime memory extraction — the first dynamic result, and it is a failure

Every number above is **static**: it measures what an analyst can read off the
artefact file. The review's actual claim is about an attacker who *executes*
the artefact and dumps its memory. That was not measured until now, and it is
the metric that decides whether "nothing is recoverable" is true.

`pydeobsbench/memory_probe.py` executes the artefact and, as its parent
process, reads every readable private mapping of the live process through
`/proc/<pid>/mem` — the same content `gcore` would capture. It samples
repeatedly, because a moving-decryption scheme is plaintext only briefly and a
single snapshot would score it clean by accident. It reports the **max**
recovery across samples, plus the sample count so a weak measurement is
visible.

**Positive control first.** A 3-line plain payload with a module-level secret
produced `samples=1` and *missed* its own secret (the process exited first).
Held open for 2 s it reported `secrets_recovered=1, names_recovered=1`. The
probe is therefore able to see a secret when one is genuinely resident — a
clean result from it means something.

**Result on the protected artefact (cipher target, `layers=25 zips=3`,
native path):**

| measurement | value |
|---|---|
| samples | 40–42 |
| secret recovered | **`cipher-master-K_77`** — the target's `KEY` constant |
| names recovered | **`main`, `seal`** |
| where | one `rw-p [anon]` page — a live Python object in the interpreter heap |
| readable fraction of process lifetime | **91%** (first hit at t=0.395 s) |
| reproduced | yes, on two independent builds |

**Second target (`inventory`, 4 secrets) — all four recovered:**

| measurement | value |
|---|---|
| secrets recovered | **4/4** |
| — | `pg_prod_INV_SuperSecret_9911` (production DB password) |
| — | `wt_live_INV_9c04d1f3` (live API token) |
| — | `inv-salt-2026-11`, `https://warehouse.internal.example/api/v3/reconcile` |
| names recovered | 2/5 (`main`, `reconcile`) |


The protections that were supposed to prevent this — section sealing, moving
decryption with buffer wiping, 25 packaging layers — do not prevent it,
because the payload must eventually hold its own constants as ordinary Python
objects in order to run. That is the irreducible boundary the review warned
about, now measured rather than assumed.

**What this does and does not say.** It says a local attacker who can read the
process memory of their own running copy recovers the payload's secrets in
under a second. It does not say the *artefact file* is weak — §2's static
numbers stand (0 names, 0 secrets, licence-bound derivation fails 8/8). Both
are true at once, and only the first one answers "nothing is recoverable".

**Consequence for the stopping condition.** "Nothing is recoverable" is
**false** as stated. The honest claim is narrower: *offline reconstruction from
the artefact is blocked; in-process memory extraction is not, and cannot be
made absolutely safe in CPython.* Reducing the window (shorter plaintext
lifetime, avoiding long-lived secret objects, `mlock`/no-core-dump policy) is
mitigation, not prevention.

**The mitigation that was added, its measured limit — and a retraction.**

The emitted loader applies `PR_SET_DUMPABLE=0` and `RLIMIT_CORE=0`
(`obfuscator/memguard.py`; the prctl is verified to make `/proc/<pid>/mem`
return EACCES even to the parent, `scripts/verify_dumpable.py`). A first
measurement reported:

| run | bytes read | secrets |
|---|---|---|
| before | 2,184,265,728 | 1/1 |
| after | 129,351,680 | **0/1** |

**That "0/1" was wrong, and it was wrong for the reason this document keeps
warning about.** The probe's mapping filter still admitted read-only
file-backed pages, so it was scoring `python3.13`'s own strings as recovered
payload data:

```
"can't make main interpreter"
"3.13.5 (main, Aug 10 2026, 12:06:59) [GCC 14.2.0]"     (version banner)
"<main program>"                                        (ld-linux)
```

Every one of those is mapped in any Python process before the artefact starts.
With the filter corrected (read-only mappings excluded, identifier-boundary
matching), the *same* "after" build recovered the secret:
`cipher-master-K_77`, found in `[stack]`, `rw-p`. The previous clean result was
a measurement artifact, not a defence.

What is true, re-measured after also moving the prctl to the loader's first
line (was ~900 lines down):

| build | bytes readable | names | secrets |
|---|---|---|---|
| prctl mid-loader | 13,594,624 | 1 (`seal`) | **1** (`cipher-master-K_77`) |
| prctl first line | 1,228,800 | **0** | **0** |

`seal` was genuinely recoverable before and is not now, so the ~11× window
reduction does real work. The readable window was measured at **~225 ms**, and
that remainder is the interpreter's own start-up before the loader runs at
all — not something this code controls.

Combined with the plaintext-lifetime fix (wipe after unmarshal instead of after
`exec`), the fully-fixed build measures:

| build | bytes readable | names | secrets |
|---|---|---|---|
| plaintext live until exec returns | 74,539,008 | 1 (`seal`) | **1** |
| + wipe after unmarshal | 9,629,696 | 1 (`seal`) | **0** |
| + prctl as the first loader line | **1,318,912** | **0** | **0** |

The lifetime fix also held up under the corrected probe (1 → 0 secrets), so
that one was not an artifact. The 1.32 MB that remains is the interpreter's
own start-up; no loader change can shorten it.

Two honesty notes. `main` is reported as `unmeasurable_names`: a byte scan
cannot distinguish it from the interpreter strings above, so it is neither
proven present nor proven absent. And a pre-opened `/proc/<pid>/mem` handle
does **not** survive the prctl (`EIO` on read, verified) — the channel closes
for late attach; only the start-up window remains.

---

## 5c. Binary-level diversity (§5-D) — measured, and the answer is nuanced

The review's point: counting transform counters is not the same as the machine
code differing. Two independent builds of the same target
(`cipher`, `layers=25 zips=3`, native path) were extracted from their
artefacts and compared at the instruction level:

| metric | value | reading |
|---|---|---|
| blob size | 189,632 vs 181,472 bytes (Δ 8,160) | layouts differ |
| sha256 | different | not a reproducible rebuild |
| instruction count | 32,988 vs 29,303 | different code volume |
| **opcode-distribution cosine** | **0.9987** | the instruction MIX is nearly identical |
| trigram Jaccard | 0.6794 | sequence arrangement genuinely differs |

So: diversification is real at the *arrangement* level (a third of 3-gram
sequences are unique to one build) but almost nil at the *opcode-mix* level.
An analyst who models the target as "this distribution of instructions with
this call structure" transfers that model across builds; one who needs exact
offsets does not. This is the honest reading of "binary-level diversity" and
it is weaker than a transform-count would suggest.

Cause: the polymorphism comes from the C transform (opaque predicates,
subset-sum blocks, MBA), which changes *which* instructions run but not the
compiler's overall lowering of Cython's generated code. Changing the mix would
require compiler diversity (gcc vs clang vs MSVC backends, §5-B).

### §5-B follow-up: clang backend added, and it barely helps — with the reason

clang 19.1.7 is installed here, so the backend was added
(`NIXON_NATIVE_CC=gcc|clang`; otherwise the build alternates off the build id so
successive releases differ; falls back loudly when one backend is absent). Both
backends build the same target and produce **identical output**
(`SEALED 8771940273853809a401795ec7699cdc`), so correctness is preserved.

Measured on two full protected artefacts, one per backend:

| metric | two gcc builds | gcc vs clang |
|---|---|---|
| instruction count | 32,988 / 29,303 | 33,201 / 32,898 |
| opcode-distribution cosine | 0.9987 | **0.9869** |
| trigram Jaccard | 0.6794 | **0.2772** |

Trigram Jaccard more than halves — sequence arrangement genuinely diverges. The
opcode cosine barely moves, and per-function analysis explains why:

* **135** functions appear in both binaries;
* the median function's cosine is **1.0000** — identical instruction mix;
* almost all code is inside a single `PyInit_payload` symbol with **30,100**
  instructions, cosine 0.986.

Cython inlines the payload into one module-init function, so there is no
per-function surface for the backends to differ on. The only functions that
diverge at all are 2–3 instruction PLT stubs. On a small hand-written C probe
the same two compilers gave cosine 0.9296 / Jaccard 0.1667 — the diversity is
real, but Cython's code shape keeps the payload concentrated in one place.

**What this means for the objective.** Compiler diversity is implemented and
measurable, and it halves structural similarity. It does not move the opcode
mix on this code shape, and no amount of adding MSVC or more flags would
change that, because the limitation is Cython's single-symbol output, not the
compiler choice. Moving the mix would require compiling the payload as
separate translation units — a restructuring, not a backend flag.

### §5-B addendum: a third backend was added and measured (MSVC ABI)

Added 2026-11-19. `cl.exe` does not exist on Linux, but the **MSVC ABI is
reachable** through `clang --target=x86_64-pc-windows-msvc` plus `lld-link`,
which is the same linker MSVC uses. A real COFF object and a real PE were
produced on this host:

```
clang --target=x86_64-pc-windows-msvc -c -O2 -Xclang -cfguard probe.c
lld-link -dll -noentry -dynamicbase -nxcompat -guard:cf probe.obj
  -> DllCharacteristics = 0x4160   (ASLR | DEP | CFG | HIGH_ENTROPY_VA)
```

So §5's "GCC, Clang and MSVC as independent backends" now has three names with
real evidence behind them rather than two:

| backend | how it is selected | verified on |
|---|---|---|
| gcc | `NIXON_NATIVE_CC=gcc` or auto-alternate | real payload builds |
| clang | `NIXON_NATIVE_CC=clang` or auto-alternate | real payload builds |
| MSVC ABI (`clang -target …-windows-msvc` + `lld-link`) | Windows farm runner; proven on this host | real PE, header-verified |

Two honest qualifications, because the word "MSVC" would otherwise carry more
than the measurement supports:

* this is the MSVC **ABI and linker**, not `cl.exe`. Codegen differs from what
  a Windows runner's MSVC would emit, so the diversity result for that backend
  is not a prediction of the Windows runner's output;
* the CFG flag it produces is **inert** on this toolchain (empty load config —
  see §5g). The backend is real; the hardening it declares is not yet backed by
  metadata, and `native_harden.check` now fails that case rather than accepting
  the bit.

The diversification claim is unchanged and still bounded by the finding above:
backend choice halves structural similarity on hand-written C and barely
touches the opcode mix on Cython output, because Cython inlines everything into
one `PyInit_payload` symbol. Adding a third backend does not change that, and
the report does not pretend it does.

---

## 5d. The integrity system was bypassable with one line — CRITICAL

The review's §1 asked for anti-patching redundancy: *"one patched check must
not disable all checks."* Building a probe for that question found the
opposite of what the architecture assumed.

**The defect.** The loader called its self-check as a bare statement:

```python
_nx_self_check()
```

Replacing that single line with `pass` removed the entire Merkle + HMAC
integrity gate, and the payload ran normally. Nothing verified that the check
had executed. Independently reproduced (`scripts/reproduce_bypass.py`):
identical output, rc 0, every integrity check disabled.

**The full chain** (`scripts/attack_chain.py`, real artefact):

| step | result |
|---|---|
| control | rc 0, payload ran |
| tamper the section pack only | **rc 137** — caught by the Merkle self-check |
| bypass the self-check only | **rc 0, payload ran** |
| bypass + tamper | **rc 0, payload ran** |

So section-pack integrity was enforced *only* by the check a one-line edit
removes. Tampering the payload used to be caught; after one edit it is not.

**Partial mitigation (measured, incomplete).** The call now binds and consumes
its result, and returns the verified digest:

```python
_NX_SELF_OK = _nx_self_check()
if not _NX_SELF_OK:
    _nx_self_fail("self-check did not return a digest")
```

**Root cause, found while retesting.** Binding the result was not enough: the
native path — the one that actually ships — returned from `_load_native()`
*without any point-of-use verification*. The early self-check was the only
check it ever performed, and that check is one removable line. A late check
added to `_exec_fallback` was dead code on native builds. The architecture's
integrity verification guarded the fallback and not the shipped path.

**The fix.** A second invocation of the same check is now emitted immediately
before the native module is executed, and before `exec` on the fallback path.
Two independent invocation sites over the same anchors is the redundancy §1
asks for: patching the early call no longer helps, because the payload cannot
run without reaching the second.

Re-measured against all four attacker variants *and* the full chain:

| variant / step | before fix | after fix |
|---|---|---|
| A — delete the call | blocked (NameError) | **blocked** |
| B — substitute a constant | **payload ran** | **blocked** (merkle) |
| C — neuter the comparison | blocked (HMAC) | **blocked** (HMAC) |
| D — neuter the failure path | blocked (HMAC) | **blocked** (HMAC) |
| chain: bypass + tamper | **payload ran** | **blocked** (merkle) |

`No single-edit bypass found` / `No chain: the tampered payload did not run.`

**What this does not claim.** An attacker who patches *both* call sites, or who
edits the anchors to match a tampered file, still wins — the file is the trust
root and it is in their hands. Verification raises the number of coordinated
edits from one to several and removes the free pass; it does not make a
client-side artefact tamper-proof. That boundary is the same one §4's memory
finding runs into, and it is stated here rather than glossed.

### 5d-bis. §1 control-flow integrity — implemented, and it catches deviations

Content hashes and pack-structure checks both miss one thing: a change in
**which code runs**. Replacing a check with `pass`, or jumping past it, leaves
every hash intact.

`obfuscator/cfi.py` adds a checkpoint chain. Three marks — `id` after the
identity gate and self-check, `enter` at `_load_native`'s entry, `use`
immediately before the payload executes — fold fixed tags into a digest seeded
from the per-build HMAC key. The final value is compared against one stamped at
build time, in its own slot excluded from the file hash.

Measured on the real stamped values from a built artefact, with the hash
anchors out of the picture so CFI is tested on its own:

| deviation | result |
|---|---|
| in order | **accepted** |
| one mark missing | rejected — `2 checkpoints, expected 3` |
| two marks reordered | rejected — `chain mismatch` |
| one mark duplicated | rejected — `4 checkpoints, expected 3` |
| no marks | rejected — `chain not established` |
| zeroed slot (unstamped) | rejected — fails **closed** |

**Two silent-failure bugs found while building it**, both the same class this
document keeps recording:

1. The schema constant was substituted *without quotes*, producing a
   `NameError` inside `_nx_cfi_mark` that its broad `except` swallowed. Every
   mark was a no-op and every chain unmatchable — the gate looked installed and
   did nothing. Caught only because the test asserts the in-order case
   **accepts**; a test that only checked rejections would have passed.
2. The first wiring emitted `_nx_cfi_mark(...)` calls while defining the
   helpers only in the self-check branch, so a build with the self-check
   disarmed would have `NameError`'d. The definition now rides with the call
   block and its absence raises at *build* time.

**Honest limit, recorded in the module and the tests.** An attacker who reads
the file sees the tags and the expected digest, so a forged chain that skips
real work still matches. This raises the number of coordinated edits from one
to several and catches naive removal; it is not a wall. On a full artefact
these edits are *also* caught by the Merkle anchor — CFI's independent value is
that it still fires when the anchor is patched away, which is exactly what the
isolated test demonstrates.

---

## 5e. Cross-build correlation (§8) — measured

The metric asks: does analysis of build A transfer to build B? Two independent
builds of the `tiny` target were compared structurally:

| property | build A | build B | transfers? |
|---|---|---|---|
| section count | 4 | 4 | **yes** |
| top-level functions | 51 | 51 | **yes** |
| line count | 2,197 | 2,165 | 98.5% identical |
| payload key (`key_hint`) | `34bc9453…` | `75120907…` | **no** |

**Reading.** The *loader's* structure correlates almost perfectly across
builds: an analyst who maps build A knows where the gates are, how many
sections to expect, and what the module layout looks like in build B. What does
not transfer is the payload key — each build re-keys, so a decryption obtained
for A is useless on B.

This is the same pattern as §5-D: per-build polymorphism changes *which*
instructions run and *which* key is used, but not the overall shape of the
loader. For an adaptive attacker the cost is therefore "map once, apply
everywhere" for the wrapper, and "recover per build" only for the payload.

That is a real and measurable weakness in the diversification story, and it is
the argument for the §5-B work (compiler diversity) that has not been done.

---

## 5e-bis. Time to successful recovery (§8) — measured on all four targets

The review's stated optimisation target was *"time to successful recovery —
actual attacker effort"*. Every other metric in this harness is a rate; this is
a cost, and it was the last named metric still unmeasured.

**Definition, fixed before the run** so the number cannot be reinterpreted
later: seconds from handing the artefact text to the model, to the model
producing a **correct** algorithm description. "Correct" means at least two
*distinctive* ground-truth markers — numeric constants (`0x7FEB352D`) or
specific content words — with generic English and loader vocabulary excluded.
The gate was sanity-checked first: the exact ground truth scores correct
(13 hits), a loader-only description scores **not correct (0 hits)**. That
second case is the false-positive class from §5 finding 18, so it is excluded
by construction rather than by hope.

| target | model | elapsed | time to recovery | verdict |
|---|---|---|---|---|
| tiny (max) | DS 4.1 Flash via Mistral | **22.14 s** | **22.14 s** | 6/14 markers, **correct** |
| algo (max) | DS 4.1 Flash via Mistral | **28.65 s** | null | 1/13 markers |
| inventory (max) | DS 4.1 Flash via Mistral | **34.51 s** | null | 1/7 markers |
| cipher (max) | DS 4.1 Flash via Mistral | **105.80 s** | null | 0/5 markers |

**All four targets measured, 2026-11-19.** One recovers, three do not, and the
one that recovers is the smallest program in the set — which is the right shape
for the result: protection cost scales with program complexity in the direction
it should.

`null` is deliberate, not a placeholder: it means *no correct description inside
the budget*, which is a different result from "recovered slowly". A number here
would conflate the two. The verdict block
(`time_to_recovery_verdict`) carries the marker counts next to each `null`, so
"not recovered" and "the probe could not judge" stay distinguishable.

**The tiny target recovered in 22 s, and that is a real finding.** `tiny` is the
control — 4 functions, one hash — and the model got its algorithm: the salt, the
truncation width, the marker, and even the expected digest
`9e8b029a65070dbd`. Reporting this as a protection success would be wrong. It
is the floor of what the benchmark can measure, and it says the harness detects
recovery when recovery happens rather than scoring everything as resistance.

**A false positive was caught while getting this list right.** The first run
returned `correct: True, time_to_recovery_s: 22.141` for `tiny` while the
model's own answer said *"the payload and key material were stripped from the
excerpt … only the guard/runtime machinery is recoverable"*. It scored correct
because 7 of the 14 markers were generic words any loader description contains
(`sha256`, `hexdigest`, `concatenate`, `encoded`, `literal`, `module`,
`prints`). Those are now excluded from the marker set, and `tiny`'s spec was
made **more specific** rather than the bar being lowered — it now names the
exact digest. Verified both ways: a loader-only answer scores 0 hits,
`correct: False`; a real algorithm description scores 4 hits, `correct: True`.

**What the model produced for the three non-recovering targets.** Each returned
a detailed, line-accurate description of the **loader** — identity gate, Merkle
self-check, HMAC anchor, anti-dump calls — and nothing about the payload's
algorithm. The `algo` target's content (xorshift-multiply finaliser,
`0x7FEB352D`/`0x846CA68B`) appears nowhere in any answer.

**What this establishes.** For this attacker model — a capable LLM given the
artefact text, no execution — recovery cost is **22 seconds on the smallest
program and unbounded within the budget on the other three**. That is the
strongest positive result this benchmark has produced, and it is also the
narrowest: the model was never allowed to *run* the artefact, and a local
attacker can (see §5b, where an executing process yielded its secrets).

Cost of the measurement: ~3.2 minutes of model time for four targets. That is
what makes it worth running on every release — it is the one metric whose unit
is the attacker's minutes rather than the defender's gate count.

### 5e-ter. Performance overhead (§8) — measured: ~16× fixed, payload-independent

The last named metric. Everything above measures what protection *buys*; this
measures what it *costs*, and the two only mean something together.

Method: the unprotected source and the protected artefact are each run 5–7
times after a discarded warmup, from their own directory, and the **median**
wall-clock is compared (a single scheduler hiccup would otherwise dominate). A
failed run is reported as a failure, never as a timing.

| target | baseline | protected | ratio | size |
|---|---|---|---|---|
| tiny | 0.021 s | 0.327 s | 15.6× | 249 B → 282 KB |
| algo | 0.018 s | 0.366 s | 19.8× | 501 B → 338 KB |
| inventory | 0.030 s | 0.338 s | 11.4× | 1,016 B → 338 KB |

**The protected time is ~0.33–0.37 s for all three, regardless of payload.**
That is the finding: the cost is *fixed loader work* — identity gate,
self-check over ~2,400 lines, section walk, native module import — not
per-workload overhead. The 11×–20× spread comes entirely from the *baseline*
varying (18–30 ms), not from the protected path. So on real work the overhead
amortises away and only dominates trivial payloads; quoting a single ratio
would misrepresent it.

Absolute numbers are one machine and one interpreter; the fixed-cost shape is
the portable part. The size multiplier (1,130× on `tiny`) is the same effect:
a ~280 KB loader over a 249-byte payload is a fixed cost, not a proportional
one.

**Harness gap, stated rather than hidden.** `probe_performance_overhead` was
implemented and these numbers were produced by running its logic directly, but
a repository hook rejects any new `subprocess.run` in the probe modules as a
command-injection pattern (it flags `[sys.executable, <variable>]` even when
the value is a validated path and `shell=False` is set). The measurement is
reproducible; it is not yet callable from `run.py`, and the hook is why.

---

## 5f. Can an environment variable rescue a modified artefact? Measured: no

The review warns that "an environment variable is not a secure secret boundary
when the attacker controls the execution environment". The loader has a CI
shortcut (`NIXON_VERIFY_SKIP_VERSION_CHECK` + `NIXON_CI`/`NIXON_ALLOW_SKIP`)
that permits the bytecode fallback. If that shortcut could run a *modified*
artefact, it would be a provenance hole; if the integrity check fires first, it
cannot.

Measured on a real artefact, three states:

| artefact state | env vars | result |
|---|---|---|
| intact | none | rc 0, payload ran (native) |
| intact | both CI vars set | rc 0, payload ran |
| linux blob replaced with `AAAA` | none | **rc 137**, merkle mismatch |
| linux blob replaced with `AAAA` | both CI vars set | **rc 137**, merkle mismatch |
| linux blob emptied (`''`) | none | **rc 137**, merkle mismatch |
| linux blob emptied (`''`) | both CI vars set | **rc 137**, merkle mismatch |

**Conclusion.** The CI shortcut cannot be used to run a tampered artefact: the
self-check runs before the fallback gate is consulted, and it covers the blob
literal. The ordering is correct and it is now verified rather than assumed.

**What remains a design concern.** The shortcut still lets an *unmodified*
artefact skip the native path on an attacker-supplied env var. That does not
expose anything the attacker did not already have (they can run their own copy
of the bytecode fallback), but it means "did the native module load?" is not a
property the artefact can assert about itself — which is why §8 measures it
externally, from the shipped blob, instead of trusting a runtime claim.

---

## 5g. §3 platform hardening — a real PE was compiled, and it refuted the flag list

The review's constraint for §3 is explicit: *"Don't blindly enable every flag.
Verify the resulting binary using platform-native inspection tools."* That
rules out the obvious approach (emit flags, print "hardened"), and on a Linux
host it also rules out the comfortable one (claim the Windows path is fine).

What was done instead, in three parts.

**1. A parser for the produced object, not for the intention.**
`obfuscator/native_harden.py` reads the actual header: PE
`OptionalHeader.DllCharacteristics` for ASLR/DEP/CFG/HIGH_ENTROPY_VA, the
security and debug directories, and the Mach-O header flags plus the
`LC_CODE_SIGNATURE` CodeDirectory for Hardened Runtime and library validation.
It reports booleans and `valid: False` on anything it cannot parse. There is no
"assume hardened" branch: an unreadable blob fails its own check.

**2. A real cross-compiled PE, because a synthetic header proves nothing about
a compiler.** This host has `x86_64-w64-mingw32-gcc`, so an actual object could
be built and read. That is what produced the finding below.

**3. The runner records the verdict in the attestation**, and the controller
now gates on it (`require_hardening=True`), rather than logging it.

### The finding: the emitted flag list would have broken the Windows build

Two defects, both found by compiling rather than reasoning.

```
$ x86_64-w64-mingw32-gcc -shared -O2 -o x.dll t.c -NXCOMPAT
gcc: error: unrecognized command-line option '-NXCOMPAT'
```

The driver selected the prefix by detecting MSVC and then applied `"-"` to the
MSVC flag names for everything else. On a mingw runner that is not weak
hardening — it is a **compile failure**, so "harden the Windows build" would
have become "the Windows build does not exist". Fixed: the MSVC branch emits
`/DYNAMICBASE /NXCOMPAT /GUARD:CF /CETCOMPAT /HIGHENTROPYVA /GS`, and the mingw
branch emits what a gcc front end accepts:
`-Wl,--dynamicbase -Wl,--high-entropy-va -Wl,--nxcompat`.

Second defect: **CFG is not reachable from a mingw toolchain at all.** GNU ld
2.44 has no such option (`--guard:cf` is lld-link's; `-Wl,/guard:cf` is read as
a file name: `cannot find /guard:cf`). Requiring it would fail every mingw
build forever, so `check()` now takes the toolchain and reports CFG as
`unavailable` for gcc/mingw — named in the result, not silently satisfied —
while still failing an MSVC build that omits it.

### What a real mingw object actually carries

| object | DllCharacteristics | ASLR | DEP | HEPA | CFG |
|---|---|---|---|---|---|
| `-shared` only (defaults) | `0x160` | yes | yes | yes | **no** |
| with the §3 link flags | `0x160` | yes | yes | yes | **no** |

This is worth stating plainly instead of quoting the flag list: **on mingw,
64-bit ASLR, DEP and high-entropy VA are already on by default, and our flags
change the header by nothing.** The measured contribution of §3 on that
toolchain is zero bits, and CFG needs MSVC or lld-link. Recording this is the
point — the earlier architecture's failure mode was a confident log line that
no one had checked against an object.

### Honest status

Updated 2026-11-19 after building a real MSVC-ABI object on this host.

| claim | status |
|---|---|
| PE parser reads ASLR/DEP/CFG/HEPA/signature/debug dirs | **verified** on real mingw AND MSVC-ABI objects |
| Mach-O parser reads PIE / heap-exec / stack-exec / CodeDirectory flags | **verified** on synthetic headers — no macOS host or cross-toolchain here |
| mingw link flags are accepted and the build succeeds | **verified** |
| mingw PE carries CFG | **no**, and cannot: GNU ld has no CFG option |
| **MSVC-compatible path exercised** | **YES** — `clang --target=x86_64-pc-windows-msvc` + `lld-link 19` produced a real PE, `DllCharacteristics = 0x4160` (ASLR\|DEP\|CFG\|HEPA), and `check(windows, "msvc")` passes |
| **CFG is a real mechanism, not just a bit** | **PARTIAL** — load config present (288 B, GuardFlags 0x100 = CF_INSTRUMENTED) but no function table: `partial: [cfg_no_function_table]` |
| **CET** (`/CETCOMPAT`) | **COMPAT-MARKED on the lld-link probe, ABSENT on the farm .pyd** — CET's opt-in is DllCharacteristics 0x8000 (the lld-link probe measured 0xC160, the farm .pyd 0x4160); the GuardFlags "CET bits" this row used to cite were export-suppression/longjump metadata, renamed 2026-11-21 (see the correction under "Windows CET") |
| **PE import/export inspection** | **verified** — export table names and the full import surface (DLLs + symbols) enumerated from real objects (`KERNEL32.dll`, `msvcrt.dll`) |
| macOS Hardened Runtime | **not verified**; it lives in the CodeDirectory and a freshly compiled object is unsigned |
| Authenticode | **IMPLEMENTED and measured** on a real PE: digest identical before/after signing, WIN_CERTIFICATE rev 2.0 / type 0x0002, PKCS#7 parses with the signer cert. Gated on an operator-supplied certificate. |

### The MSVC path works — and CFG was fixed after measuring it inert

`cl.exe` does not exist on Linux, but the **MSVC ABI does**: `clang
--target=x86_64-pc-windows-msvc` emits COFF and `lld-link` is the same linker
MSVC uses, including its `/GUARD:CF` option. A real object was built:

```
clang --target=x86_64-pc-windows-msvc -c -O2 -Xclang -cfguard probe.c
lld-link -dll -noentry -dynamicbase -nxcompat -guard:cf probe.obj
  -> DllCharacteristics = 0x4160  (ASLR|DEP|CFG|HIGH_ENTROPY_VA)
```

That is a genuine advance over the mingw finding: CFG **is** reachable here,
where GNU ld could not emit it at all.

But the linker also printed this, and it mattered more than the bit:

```
warning: Control Flow Guard is enabled but '_load_config_used' is missing
```

Parsing all 16 data directories showed the **load-config directory was empty**
(`size = 0`): no guard flags, nothing for the Windows loader to enforce. The
`DllCharacteristics` bit was a **declaration, not a mechanism** — the "don't
blindly enable every flag" failure the review names, caught by parsing the
object rather than by reading a flag list.

**The fix was then implemented and measured**, not just recommended. Supplying
a `IMAGE_LOAD_CONFIG_DIRECTORY64` as `_load_config_used` makes lld-link emit
the directory with guard flags set:

| object | DllCharacteristics | load config | GuardFlags | instrumented | function table |
|---|---|---|---|---|---|
| `-guard:cf` alone | `0x4160` | **empty** | — | — | — |
| + `_load_config_used` | `0x4160` | **288 bytes** | **`0x100`** | **yes** | **no** |

Two measurement defects were found while getting that number right, and both
would have produced a plausible lie:

* the `GuardFlags` field is at offset **0x90** in the 64-bit load config, not
  `0x70` (0x70 is `GuardCFCheckFunctionPointer`); reading 0x70 returns zero and
  would have reported every object as having no guard flags at all;
* the section header gives `(vsize, vaddr)` at `+8` and `(raw_size, raw_ptr)` at
  `+16` — reading `+20` returns `(raw_ptr, 0)`, which lands every RVA lookup at
  file offset 0 and produced a garbage `0xE020B` that looked like a real flag
  set.

`native_harden.check` now reports three CFG states rather than two:

| state | verdict |
|---|---|
| bit set, load config empty | `ok: False`, `inert: ["cfg"]` |
| bit set, load config present, instrumented, **no function table** | `ok: True`, `partial: ["cfg_no_function_table"]` |
| bit set, load config present, instrumented + table | `ok: True`, `partial: []` |

The middle state is the honest one for this toolchain: CFG checks **are**
compiled in, so indirect call sites verify against the guard check pointer —
real protection — but with no function table, calls to addresses that are not
statically valid targets cannot be rejected at load time. Collapsing that into a
single boolean would either overstate the protection or discard a real one, so
the weaker fact is named.

Producing the function table itself needs `clang-cl` with the MSVC headers,
which this host does not have. That is a farm-runner job, and the runner records
`hardening_verdict` so its answer is checked rather than assumed.

### Authenticode and Hardened Runtime: signature properties, not flags

Both are properties of a **signature**, and a signature is only worth anything
if the platform trusts its issuer. Measured on this host 2026-11-19:

| platform | signing tool | trusted issuer possible |
|---|---|---|
| Windows | `signtool` present (NSS build, `SEC_ERROR_BAD_DATABASE`) | **no** — no certificate store on POSIX |
| macOS | none (`codesign`, `rcodesign`, `ldid` all absent) | **no** |
| Linux | n/a | ELF has no code-signing model |

OpenSSL 3.5 and `cryptography`'s PKCS#7 builder are present, so a
**self-signed** Authenticode signature could be produced here. It would not be
trusted by Windows, and a self-signed Mach-O signature is not accepted by
Gatekeeper — so producing one would make the artefact *look* signed while
changing nothing an OS or an attacker cares about. That is precisely the class
of reassurance this report has had to retract four times already.

`native_harden.signing_readiness(platform)` now reports, per platform, which
tool exists and whether a **trusted** issuer is possible, with the reason. The
build uses it to state the truth instead of claiming a signature it does not
have or silently skipping one it was asked for.

The honest summary for §3 is therefore:

* **Linux**: fully implemented and verified on real objects.
* **Windows**: flags and parser verified on a real PE; **CFG is inert on this
  toolchain** and is now reported as such; Authenticode is an operator step
  requiring a CA-issued certificate and a working signing tool.
* **macOS**: parser verified against synthetic headers only; Hardened Runtime
  and library validation require `codesign` plus an Apple Developer ID, neither
  of which exists here.

The report deliberately does not claim "Windows/macOS hardening verified": the
parser, the flag emission and the *inert-flag detection* are verified, and the
real objects have not been built on those platforms from this machine. That last
measurement is what the farm runners are for, and their answer now travels in
the attestation instead of being assumed.

---

## 5h. §9 remote attestation and secure update — what they do and do not prove

Two mechanisms were missing entirely. Both are decision logic over bytes the
caller already holds: no network, no auto-execution. That is deliberate — an
updater that fetches and runs code is a remote-code-execution surface by
design, and this benchmark cannot measure a claim the code does not make.

### Remote attestation (`obfuscator/remote_attest.py`)

Challenge-response, not "signed blob". The verifier issues a nonce; the artefact
returns a signed statement containing that nonce, its build id, and the sha256
of the bytes it is running. Refusals, each tested:

| attack | refused because |
|---|---|
| replay a recorded response from an earlier session | nonce mismatch |
| present a response minted by a different build | build_id + artefact digest are inside the signature |
| re-point a response at a different verifier | verifier_id inside the signature |
| serve a response captured long ago | `responded_at` outside ±300 s |
| edit any field after signing | signature does not verify |
| hand over an unverified statement | no key supplied is a refusal |

**Honest limit, and it is the important part of this section:** this is not
hardware attestation. There is no TPM or enclave and no measured boot. The
signing key ships inside the artefact, so an attacker who can run code in the
process can forge any statement. What this buys is that impersonating a build
you do not possess costs work; it cannot make a compromised host honest.

### Secure update (`obfuscator/secure_update.py`)

A signature check alone stops none of the attacks that matter in an updater,
because a downgrade is validly signed. Refusals, each tested:

| attack | refused because |
|---|---|
| downgrade to the previous, vulnerable release | monotonic `sequence` vs the client's installed value |
| publisher retires a bad release without rotating keys | signed `minimum_sequence` floor |
| transplant a signed update for another product/channel | product/channel/artefact are inside the signature |
| serve an update signed by a retired key | `key_id` checked against the accepted set |
| swap the payload after signing | digest + size of the bytes actually handed over |
| schedule an update far in the future | `published_at` beyond +900 s |
| crash mid-install leaves a truncated binary | verify before staging; temp file in the SAME directory, then `os.replace` |

Two behaviours are reported as **warnings** rather than passes, because a check
that did not run must not read as one that succeeded: a client that supplies no
`current_sequence` gets "the installed-version downgrade check did not run", and
an absent `max_age_seconds` gets a freeze-attack warning.

**Honest limit.** Freeze resistance needs a trusted clock; a client without one
cannot use `max_age_seconds`, and the module says so instead of implying
protection. There is no update *server* here and no key distribution — those are
deployment, not code.

Both modules: 41 tests, all built around refusals.

---

## 5i. §8 semantic reconstruction — the last unmeasured metric, now measured

Every earlier section measured SOURCE recovery: strings, names, algorithm
overlap. The review asks for **semantic** reconstruction as a separate thing,
and until now nothing in the harness could tell them apart. Any comparison ran
against the original, so a perfect behavioural copy written in a different style
scored as a failure and a verbatim copy of the comments scored as a success.

`pydeobsbench/equivalents.py` closes that. Each target's `algorithms` spec
string was reimplemented from the SPEC, not from the source, and each
implementation deliberately uses different naming and control flow:

| target | equivalent | target output | match | identifier Jaccard |
|---|---|---|---|---|
| tiny | `tiny_sign()` | `TINY 9e8b029a65070dbd` | **yes** | 0.00 |
| inventory | `inventory_reconcile()` + `inventory_audit_signature()` | `AUDIT 19487c7b06691c76` | **yes** | 0.00 |
| algo | `_avalanche()` / `_rotate_left()` / `algo_derive()` | `DERIVE 3249269004` | **yes** | 0.00 |
| cipher | `_stream()` / `cipher_seal()` | `SEALED 8771940273853809a401795ec7699cdc` | **yes** | 0.00 |

The two columns matter together. **Behaviour reproduced exactly, identifiers
shared not at all** — that is semantic equivalence established independently of
text, and it is the only form in which the claim means anything. The overlap is
part of the score block (`algorithm_recovery.semantic.source_overlap`) so the
report cannot show the match without also showing that the comparison was not
textual.

What this establishes and what it does not:

* **Establishes** that all four ground-truth specs determine their target's
  observable behaviour. If a spec had been vague or incomplete, an independent
  implementation could not have reproduced the output, and the finding would
  have been in the benchmark's ground truth rather than in the protection.
* **Does not establish** that a *recovered* implementation would match. The
  equivalent is written by someone with the spec in hand; the attacker has only
  the artefact. Semantic reconstruction of the shipped artefact remains
  unmeasured for the same reason §5e-bis records: the model recovered no
  algorithm to compare.

The `equivalent_matches_target` field is `None` when no equivalent exists rather
than `False`, because "unmeasured" and "measured and different" are different
results and a boolean would collapse them.

---

## 5j. §2 authenticated encryption — what was already there, and what was added

The review asks for *"authenticated encryption using AES-256-GCM or
ChaCha20-Poly1305"*. Checking before adding anything turned up two different
answers depending on which path is meant, and the distinction matters.

**In the shipped artefact path: authentication was already present.** The
section pack (`obfuscator/section_split.py`) seals each section under its own
derived key and prefixes an **HMAC-SHA256 tag over the plaintext**, verified with
`hmac.compare_digest` before the bytes are used (`section_split.py:122`,
`:175`). That is encrypt-then-MAC with per-section keys — the property the
requirement names, achieved without a dependency the stdlib-only loader cannot
import. What was missing was not authentication; it was a *record* that this is
what the artefact does, and a GCM primitive for callers outside the artefact.

**What was genuinely absent: an AEAD primitive.** `encrypt_payload` offered
AES-**CTR** (confidential, unauthenticated) or the XOR stream, and nothing else.
It was reachable only through `use_aes_ctr=True`, which no artefact path uses —
the artefact deliberately forces the XOR/CTR stream because the loader must stay
stdlib-only. So the module had no way to seal data with a checked tag in any
context that could afford the dependency.

Added `seal_aead` / `open_aead` (`pipeline.py`), AES-256-GCM with two design
decisions that are the whole point:

| property | why |
|---|---|
| the nonce is stored **inside** the envelope | GCM nonce reuse leaks the authentication key, so the public API must have no caller-supplied nonce to reuse. `nonce=` exists only for seeded reproducible builds. |
| AAD binds context | a ciphertext sealed for `section-3` does not open as `section-4`; verified by test. |
| the AEAD key uses its own KDF label | the GCM key and the CTR/XOR stream key are different values from the same build secret, which is the "cryptographic separation between build-time and runtime secrets" the review asks for. |
| every failure is `ValueError` | `cryptography` raises `InvalidTag` (not a `ValueError`) while pycryptodome raises `ValueError`; a caller catching the documented type would otherwise silently miss one backend's tamper signal. |

Measured on this host (CPython 3.13, `cryptography` backend):

| case | result |
|---|---|
| round trip | plaintext recovered exactly |
| ciphertext bit flipped | **rejected** |
| nonce bit flipped | **rejected** |
| tag truncated | **rejected** |
| wrong key | **rejected** |
| wrong AAD / AAD missing / AAD added | **rejected** |
| 50 consecutive seals | 50 distinct nonces; identical plaintexts produce different ciphertexts |

**Honest limit.** This primitive is not on the artefact's load path — the loader
is stdlib-only by design, and moving it to GCM would mean shipping a crypto
dependency into every artefact. The artefact's authentication remains the
per-section HMAC described above. `seal_aead` is for tooling (licence envelopes,
dispersal, update manifests) where `cryptography` is available at build time.

---

## 5k. §6 adversarial solver validation — all three claims refuted, measured

The review sets the bar explicitly:

> "I would not count a transform as a successful security mechanism until it
> survives automated simplification and adversarial recovery attempts."
>
> "NP-hardness of a general problem does not automatically make an individual
> generated instance difficult."

`pydeobsbench/transform_solvers.py` implements the adversarial half. It is
separate from the emitter on purpose (§10): a transform that grades itself is
the self-judging failure the review warns about.

Measured 2026-11-19, CPython 3.13, gcc 14.2, sympy 1.14, this host:

| claim | measured | verdict |
|---|---|---|
| subset-sum "NP-hard", 4096-entry DP | at the shipped n=8: 256 subsets, 200/200 solved in **0.000114 s**. At any n: the answer is a compile-time constant | **NOT A PROTECTION — pass removed from the default pipeline** |
| multi-round MBA "exponential" | **re-measured on the SHIPPED form** (volatile slots): the expression is a function of runtime values, z3 proves it varies (sat, 0.04 s), so there is no constant to fold | **SURVIVES — the earlier "WHOLLY INEFFECTIVE" verdict measured the slot-free emitter** |
| fixed-even opaque predicate at `-O3` | **re-measured on the EMITTED form**: helper branches 1→1, `__nx_opa` operands present in asm, 502→854 bytes | **SURVIVES — the earlier "FOLDED AWAY" verdict was a benchmark defect** |

### Why the 4096-entry table measures nothing

The table sizes the **run-time verifier**. The attack is the subset lattice:
`n = 8` means **256** subsets, which a script enumerates in microseconds. The
review's distinction is exact — the difficulty of the class says nothing about a
generated instance, and here the instance is trivially small. A 4096-entry
table attached to a 256-element search space is inverted effort.

### Why MBA length is not difficulty

`_mba_substitute_constant` emits a genuinely nested, exact expression: the
identity `x + y == (x ^ y) + 2 * (x & y)` is wrapped round after round, and
every round is arithmetically correct. The `volatile` slots stop **gcc** folding
it. They do not stop a **reader** or a **symbolic solver**, which see the same
arithmetic with no secrets in it. sympy's generic `simplify` returned `12345`
from a 2,073-character expression in under 4 ms — including the 5-round case.
The transform costs bytes and buys no time.

### The opaque predicate: my first verdict was WRONG, and this is the retraction

The original row in this section said **FOLDED AWAY**, based on compiling
`((x*x - x) % 2) == 0` and observing 3 branches at `-O0` and 0 at `-O3`.

**That was a benchmark defect, not a transform defect.** The fixture I compiled
was a hand-written predicate. The transform does not emit that: it loads its
operands through `static volatile int __nx_opa_*`, which gcc cannot fold. I
measured a program the transform never produces and reported the result against
the transform.

Re-measured on the ACTUAL emitted form, compiled with `-O3 -fno-inline` into a
non-inlined helper so the branch is not elided by inlining:

| | helper branches | `__nx_opa` in asm | asm size |
|---|---|---|---|
| baseline fixture | 1 | no | 502 B |
| after `insert_opaque_predicates` | 1 | **yes** | 854 B |

**The predicate survives `-O3`.** `__nx_opa` operands are read from volatile
slots in the generated assembly, so nothing is folded, and the artefact grows by
352 bytes of real code.

What this does and does not establish:

* **Establishes** the transform defeats constant folding at `-O3`. The earlier
  anti-fold change (volatile operands, audit 2026-11-18) works.
* **Does not establish** the predicate is hard to *analyse*. A reader sees
  `((__nx_opa_1 * (__nx_opa_1 + 1)) & 1) == 0` and a trivial parity argument
  resolves it — the same class of weakness as the MBA row. Survival of the
  optimiser is not survival of a reader, and this report should not conflate
  them a second time.

The lesson worth recording: **a benchmark that measures the wrong input is
indistinguishable from a benchmark that measures nothing**, and it is worse,
because it produces a confident verdict. Two of the three §6 probes had this
defect in some form — this one outright, and the subset-sum probe measured
`n=8` while the code under test had moved on.

### What this changes

Of the three claims, **two hold and one does not**, and the score moved twice as
my own measurement errors were corrected (0/3 → 1/3 → 2/3). Both moves were
fixes to the BENCHMARK, not to the transforms:

| claim | verdict |
|---|---|
| subset-sum "NP-hard" | **does not survive** — the answer is a compile-time constant |
| MBA "exponential" | **survives** — the shipped form carries `volatile` slots, so it is a function of runtime values and cannot fold to a constant (z3: varies, sat in 0.04 s) |
| opaque predicate survives `-O3` | **survives** — volatile operands reach the assembly |

**What "2/3" does and does not mean** (reviewer, 2026-11-20 — the label was
being read as a security score, and it is not one). Each row above is a
*property of the emitted form*, measured:

| property | evidence status |
|---|---|
| the emitted form survives the tested compiler optimisation | **measured** |
| the expression depends on runtime slot values (not a constant) | **measured** |
| a symbolic solver cannot simplify it within the tested budget | **measured for the probes run** |
| a human analyst or a symbolic tool cannot understand it | **not established** |
| it meaningfully increases real analyst effort | **not established** |

The familiar identity `x + y = (x ⊕ y) + 2(x ∧ y)` does not become
computationally difficult because its operands live in volatile slots; it
becomes *unfoldable at compile time*, which is a different claim. Likewise an
opaque predicate surviving `-O3` proves the compiler did not eliminate it, not
that a person cannot read it. The score is therefore a measure of **transform
robustness under optimisation and constant folding**, and must not be quoted as
reverse-engineering resistance. The subset-sum transform left the default
pipeline for exactly this reason: its weakness is structural, not a tuning
problem.

The MBA correction is worth spelling out because it was the same class of error
as the opaque-predicate one. The probe sampled `_mba_substitute_constant`, which
emits **bare constants**; sympy folded that in 0.003 s and the report said
"WHOLLY INEFFECTIVE". But the transformer routes through
`_mba_expression_with_slot`, which replaces one operand per identity with a
`static volatile` slot. With free slot operands there is no constant to recover
— an analyst must obtain the runtime values first. Measuring the wrong emitter
produced a confident wrong verdict, exactly as measuring a hand-written
predicate did for the opaque row.

What "survives" still does not mean, stated so it cannot be read as more: a
reader sees `((__nx_opa_1 * (__nx_opa_1 + 1)) & 1) == 0` and settles it with a
parity argument, and sees the MBA identity `x + y == (x ^ y) + 2(x & y)` and
recognises it. These transforms defeat the COMPILER and the generic SOLVER.
They do not hide their construction from someone reading the code, and the
wrapper boundary (§5n) is where that limit is recorded.

The lesson, now demonstrated three times in one section: **a benchmark that
measures the wrong input is worse than a benchmark that measures nothing**,
because it produces a confident verdict. Every probe in this file now samples
the emitted form and reports `sampled_form` so the distinction is visible in the
output rather than only in the source.

**The subset-sum pass was removed from the default pipeline.** Raising `n` was
attempted first, and it does not work — the measurement says why, and the
reason is structural rather than a matter of tuning:

| n | defender's verify cost | attacker's MITM cost | protection gained |
|---|---|---|---|
| 8 | 0.0001 s | 0.0001 s | none |
| 24 | 0.006 s | 0.02 s | none |
| 32 | 0.13 s | 0.05 s | none |
| 40 | 2.8 s | 1.3 s | none |
| 48 | **60 s** | > 5 s | none (build unusable) |

Two facts make width-tuning futile. First, the **defender pays the same
meet-in-the-middle work on every build** that the attacker pays once — raising
`n` taxes the build. Second, and decisively, **the answer is a compile-time
constant**: the set and the target are emitted into the C in plaintext, so
`check(...) == 1` is true by inspection. An analyst does not need a solver at
any `n`. The `answer_predetermined` field in the probe records exactly this,
and `summarise()` refuses to mark the claim as holding even when the MITM
times out.

So `do_subset_sum` defaults to **False**. The pass is kept, tested, and
available by explicit opt-in — a reflectively honest "this is volume, not
hardness" — but it is not part of a default build, because a transform that
provably fails the review's bar while costing build time is the anti-pattern
the review names.

The verifier itself was rewritten while checking the widths: a DP indexed by a
40-bit target is not emittable, so it is now meet-in-the-middle, and the table
is **heap-allocated and freed** rather than a static array (a static 2²⁴ table
would have added 128 MB to every linked binary and made the first call a
page-fault stall). Verified end to end: the transformed C compiles at `-O2` and
returns the same exit status as the original across three seeds.

For the other two transforms the honest description is unchanged: they provide
**volume**, measured in bytes, not difficulty, measured in solver time — and
the solver time is still negligible. What the transforms cost the attacker is
the number of things they must look at, and that is a different claim from the
one the documentation made.

The probes are wired so a future change to the emitter moves the numbers, and
`summarise()` reports `UNMEASURED` rather than a pass when a probe could not
run. Three verdicts, three failures, no exemptions.

---

## 5l. §8 what DS 4.1 Flash actually recovered — the loader falls, the payload holds

The §8 AI probe is routed to DeepSeek V4.1 Flash via Mistral
(`mistral/deepseek-v4-1-flash-1017`) through the OpenCode CLI, per the
operator's instruction. Measured 2026-11-19 on a real `max`-profile artefact
(280,469 bytes, built in 14.5 s), twice, same result both times.

### The finding, stated first

**The protection loader was reconstructed in full.** Given only the artefact
text, the model returned a step-by-step map of the layer wrapping the payload:

| component | recovered |
|---|---|
| `prctl(PR_SET_DUMPABLE=0)` anti-dump | yes, named explicitly |
| `RLIMIT_CORE=(0,-1)` core-dump disable | yes |
| identity gate (`__name__` in `__main__`/`__mp_main__`) and its exit code | yes |
| `constant_time_compare` (length check + OR-accumulate of XOR pairs) | yes |
| `_nx_self_fail` writing to stderr and `os._exit(137)` | yes |
| `_nx_mlock` with `addressof`/page-alignment | yes |

`loader_reversed: True` is now recorded in the score block under
`algorithm_recovery.model_reconstruction`. It is not new information about the
attacker — anyone holding the artefact can read that code — but this is the
first time the harness MEASURED it, and the answer is that the enforcement
layer is fully transparent to a model with no debugger and no execution.

### What did NOT fall

| metric | result | what it means |
|---|---|---|
| payload names | **0/4** | original identifiers are absent from the artefact |
| payload secrets | **0/2** | literals are absent from the artefact |
| in-memory secrets, 14 samples | **0/2** | no plaintext secret observed in the live process |
| in-memory names | **0/4** | no payload identifier observed in memory |
| native payload names in strings | **[]** | nothing payload-specific in the extracted blob |
| dynamic exports | `['PyInit_payload']` only | no per-function symbol surface |

### The honest reading, and the trap avoided

`algorithm_overlap` reported **"n/a — insufficient distinctive terms"**. The
tiny target's ground-truth spec yields only two scorable words (`chars`,
`salt`), so the ratio is not computable. **That is a metric failure, not a
protection success**, and it is recorded as `None` rather than `0.0` so the
report cannot present it as a clean result. A pattern this project has had to
retract before is exactly this: showing "algo overlap: n/a" beside "0 names"
and letting a reader conclude the artefact was opaque. It is not — it is a
loader the model read in full, around a payload it did not reach.

The correct summary is narrow and specific: **the payload survived static and
dynamic recovery; the wrapper did not survive static reading.** Those are
different components with different outcomes, and only the second needs work.
The loader's structure is discoverable because it is plain Python emitted into
the artefact — the model broke no cipher, it read the launcher. Whether that
matters is a threat-model question: a customer who needs the *payload* hidden is
served; a customer who needs the *enforcement mechanism* hidden is not.

### Two harness defects this measurement exposed

1. `score()` accepted `(target, probes)` while the semantic block referenced a
   variable `name` that was not in scope. The §8 semantic metric had therefore
   never executed inside a harness run — its unit test passed because it called
   the helper directly. Fixed; verified end to end on a real artefact
   (`equivalent_output == target_output`, `source_overlap 0.00`).
2. `probe_ai` computed `loader_reversed` and `algorithm_text`, and `score()`
   dropped both. The single most informative result of the run was being
   discarded between the probe and the report. Fixed: both are carried in
   `model_reconstruction`, with `overlap_note` beside them so the "n/a" is
   visible next to the loader finding instead of buried.

---

## 5m. §1 re-tested against a re-stamping attacker — the check holds

The §8 run above showed the model can read the loader completely. That raised a
sharper question than "can it read?": **can it read the check and then get
around it?**

The self-check is a Merkle root over the artefact's own lines, so an attacker
who knows the construction can recompute the stamp. `scripts/attack_chain.py`
now measures exactly that, and it distinguishes two very different outcomes:

* recomputing the stamp is enough → the integrity check is bound to the file's
  TEXT, and §1's anti-patching redundancy reduces to "recompute one hash";
* recomputing is not enough → something else in the chain is doing the work,
  and that is worth knowing precisely.

Measured on the same real artefact (`tiny`, `max` profile):

| attack | result |
|---|---|
| control | rc 0, payload ran |
| tamper pack only | **rc 137**, merkle mismatch |
| bypass the self-check call only | **rc 137** — the LATE check caught it |
| bypass + tamper | **rc 137** |
| re-stamp the Merkle root, no edit | rc 0, payload ran (correct: nothing changed) |
| **tamper + re-stamp** | **rc 137** — `hmac expected=d7551a8a… got=71a9d0e…` |

The last row is the finding. Recomputing the Merkle root is **not sufficient**,
because `_NX_SELF_HM` is a separate HMAC over the same content: an attacker who
only reproduces the Merkle layer fails the HMAC layer. Two independent
constructions over one artefact is precisely the "anti-patching redundancy" §1
asked for, and it now has a measured refusal behind it rather than a design
claim.

Two honest qualifications:

* **Both layers are still derivable from the artefact**, because both are
  unkeyed-from-the-attacker's-view text transforms and the key material ships
  inside it. The measured result is that recomputing ONE layer is insufficient;
  it is not that a determined attacker who reimplements BOTH layers is blocked.
  The next probe would be to supply `_NX_SELF_HM` consistently as well and see
  what happens — that is the honest boundary of what this measurement covers.
* **The "bypass only" row changed outcome since §5d.** Before the late
  point-of-use check, patching the single call line let the payload run. It now
  fails at 137, which is the §5d fix verified from the outside rather than
  asserted from the source.

---

## 5n. The loader boundary — measured, then accepted

§5l showed the model reconstructing the whole enforcement layer. The obvious
next step was to obfuscate it. That step was **tried and measured**, and the
measurement says not to bother.

The loader's **187 symbols were all renamed** to opaque identifiers — the
strongest symbol-level obfuscation applicable without changing behaviour — and
afterwards every behaviour-bearing constant was still present:

| marker | survives total symbol renaming |
|---|---|
| `prctl` | yes |
| `137` (exit code) | yes |
| `RLIMIT_CORE` | yes |
| `mlock` | yes |
| `0o600` (temp-file mode) | yes |
| `self-check error:` string | yes |

The model did not recover `_nx_self_fail`. It recovered **"writes to stderr and
calls `os._exit(137)`"** — a syscall and a constant, which the code must contain
to function and which no renaming pass can touch.

So the split is recorded as the accepted threat model, in
`docs/security/THREAT_BOUNDARY_LOADER.md` and pinned by
`tests/test_loader_boundary.py`:

| layer | measured | stands |
|---|---|---|
| **payload** — source, algorithms, secrets | 0/4 names · 0/2 secrets static · 0/2 secrets and 0/4 names in memory over 14 samples · semantic equivalent at 0.00 identifier overlap | **holds** |
| **wrapper** — how integrity, licensing and anti-dump are enforced | fully reconstructed from artefact text | **does not hold — accepted** |

This is a scope statement, and it is defensible because the halves are different
kinds of thing: the payload is *data*, and data can be sealed under keys the
attacker lacks; the wrapper is *mechanism*, and mechanism must execute on the
attacker's machine, so its behaviour is necessarily observable and — the artefact
being text they can read — its structure is necessarily readable. The review says
the same in its own words: *"absolute irreversibility isn't a realistic guarantee
for client-side software"*.

Two facts keep this from being fatal. First, §1's five attack routes all still
end at `rc 137` **after** the loader was fully read, including tamper + re-stamp
which the second HMAC layer caught — reading the mechanism is not defeating it.
Second, `test_renaming_every_symbol_does_not_remove_the_behaviour` would fail if
symbol obfuscation ever *did* hide the behaviour, which is the signal to reopen
the decision.

The document names the only two approaches that could change the answer, neither
a tuning change: move the guards into the native blob (cost: reimplementing them
in C across the Cython boundary, and the blob is itself extractable), or move
them off-device into an attestation service (cost: the artefact then requires
network availability at runtime).

---

## 5n-bis. §9 audit — all three "never verified" items existed, two were unreachable

The review lists function-level virtualisation, instruction-set diversification
and crash-forensics protection as §9 items to "still consider adding". The audit
found all three ALREADY IMPLEMENTED — and two of them unreachable in every real
build, which is the "tested but unreachable" defect class this session keeps
finding.

| §9 item | module | audit finding | action |
|---|---|---|---|
| Function-level virtualisation | `vm_dispatch.py` (756 lines, 2 dispatcher families, per-seed opcode shuffling, 12 tests) | **nothing set `options['vm_dispatch']`** — reachable only by hand-writing an experiment script | `NIXON_VM_DISPATCH=a\|b\|alternate` now reaches the native option dict; off by default (conservative allowlist) |
| Instruction-set diversification | `phase_state_isa.py` + VM-A/B families + §5 backends | **wired** (called from build.py line 2328) | recorded; three layers measured (per-seed opcode map, per-build dispatcher family, per-backend native mix) |
| Crash-forensics protection | `native/crash_suppress.h` (106 lines, 27 tests) | **no native source included it** — every native hard failure raised an OS dialog | `native/core.cpp` includes it and calls `nixon_suppress_crash_dialogs()` at `CompileToMarshal`; compiles clean with `-DCORE_HAVE_PYTHON_H` (126 KB object) |

The crash-suppression finding is the operationally important one. §4's core-dump
policy prevents *dumping*; without this header, a native hard failure still
raised a Windows crash dialog or a POSIX SIGSEGV notice, handing the analyst a
register state and a backtrace. Both defences are now in the same native module.

Honest scope: none of the three hides the WRAPPER (§5n). The VM hides payload
function bodies behind a bytecode interpreter; crash suppression prevents
forensic leakage from native failures; ISA diversification raises disassembly
cost. All three are measured contributions to analyst cost with recorded limits,
not unqualified wins. Full detail in `docs/security/THREAT_BOUNDARY_LOADER.md`
§"§9 audit".

---


## 6. Honest limits of this benchmark

1. **The AI was given the artefact text only.** No debugger, no Frida, no
   Ghidra, no angr (not installed). This measures static + LLM reconstruction,
   not the full adaptive attacker the review describes.
2. **An unsuccessful reconstruction is not proof of security.** The model
   recovered no payload behaviour, but it was never asked to *execute* the
   artefact and observe. An attacker who runs it can always reproduce
   behaviour — that is the irreducible client-side boundary.
3. **`pack derivable = yes` on unbound profiles is by design.** A standalone
   artefact must carry its keys. The licence-bound profile is the control that
   proves the difference (`False`), and it is the profile to quote.
4. **~~The ELF symbol probe found no embedded ELF~~ — fixed in round 2.**
   `probe_native_blob` now performs the loader's own derivation (shares →
   build-id salt → customer mask → XOR), so the blob is extracted on every
   unbound build and its exports/strings/hardening are measured directly.
   This is what exposed finding 15. The old probe's `found_elf: False` was a
   probe gap, not a clean result.
5. **One artefact per (target, profile).** No repeated draws, so no
   confidence interval on the AI's recovery rate. The numbers are
   deterministic for a fixed target but the model is not: a rerun could differ
   by a name or two.
6. **"The blob is derivable" is not a failure of the design.** The loader
   must carry its key to run standalone, so an unbound artefact's blob is
   always extractable. What matters is what it exposes once extracted — and
   after findings 13/15/16 that is: one `PyInit_` export, no `.symtab`, no
   `.comment`, RELRO+NX on, and zero ground-truth payload identifiers in its
   strings.
7. **The native path is Linux-only in this round.** Windows `.pyd` and macOS
   `.so` blobs come from the Cython matrix farm, which cannot be exercised
   from this machine. The farm path now shares the local build's AST and C
   transform layer (finding 17), but its artefacts have not been measured.


---

## 7. Reproducing

```bash
# unbound, max profile, with the AI probe
python3 -m pydeobsbench.run --profile max --targets all --ai

# the control: licence-bound, offline derivation must fail
python3 -m pydeobsbench.run --profile absolute-licensed --targets inventory cipher --ai

# reports land in pydeobsbench/report/run-<profile>-<epoch>.json
```

Probes can be run standalone against any artefact:

```python
from pydeobsbench.static_probes import probe_section_decrypt, probe_native_blob
probe_section_decrypt("dist/payload_protected.py")
# {'derived': False, 'reason': 'HMAC failed on 8/8 sections (key not derivable)'}

probe_native_blob("dist/payload_protected.py", target)
# {'found': True, 'derived': True, 'valid_object': True, 'elf_bytes': 139360,
#  'dynamic_exports': ['PyInit_payload'], 'symtab_present': False,
#  'comment_present': False, 'relro': True, 'nx_stack': True,
#  'payload_names_in_strings': []}
```

The blob can also be extracted from the command line, which is what the
`native_blob` probe automates:

```bash
python3 pydeobsbench/extract_blob.py dist/inventory_protected.py /tmp/blob
# linux: 139360 bytes, magic=b'\x7fELF' -> /tmp/blob/linux.so
#   exported symbols: ['PyInit_payload']
```

The C transform has its own fuzz harness — the transform is randomised per
build, so "it compiled" is a single sample unless you sweep seeds:

```bash
python3 -I scripts/fuzz_c_transform.py payload.py 80
# 80/80 seeds produced compilable C
```


---

## 8. Where the next measurement should go

Ranked by expected information gain:

1. **Dynamic probe with execution** — spawn the artefact under a tracer,
   dump memory after the section walk, and measure whether plaintext is
   recoverable. This is the only way to test the moving-decryption claim.
   Still the biggest gap: every number in §2 is static.
2. **Native symbol probe against the section pack** — ~~done in round 2~~
   (`probe_native_blob`, finding 15). Superseded by:
2b. **Run the same blob probe against a licence-bound artefact that has its
   token.** Right now the licensed row reports "not derivable" and stops.
   An attacker who *has* the licence (a paying customer) is the realistic
   threat, and nothing measures what the blob leaks in that case.
3. **Repeated draws per cell** for a recovery-rate distribution rather than a
   point estimate. With `algo overlap` varying 0.10 → 0.22 for the same
   target across builds, the variance is measurable and worth reporting.
4. **Cross-build correlation** — build the same target twice, give the model
   analysis of build A plus the binary of build B, measure transfer. The
   review called this out and nothing measures it yet.
5. **Timed attack** — record wall-clock from "given artefact" to "algorithm
   described", which is the metric the review actually recommends optimising.


---

## 5o. §5l follow-up: enforcement moves native — what DS 4.1 Flash can still reconstruct

The operator asked whether the §5l finding ("DS 4.1 Flash reconstructed the
entire enforcement layer from artefact text") could be fixed. The boundary
document's boundary-push option — enforcement into the native blob — is now
implemented and re-measured with the same instrument (DS 4.1 Flash via
Mistral, `mistral/deepseek-v4-1-flash-1017`, through the OpenCode CLI, per
the operator's instruction; probe on the rebuilt max-profile artefact,
2026-11-20).

### What the model recovered on the rebuilt artefact

| component | §5l (before) | §5o (after) |
|---|---|---|
| top-of-loader `prctl`/`RLIMIT_CORE` block | recovered in full | still recovered — BY DESIGN: the max profile's sectioned fallback is production-reachable, so the Python block stays (dropping it would be a §4 regression on that path) |
| identity gate + exit code | yes | yes (unchanged — it must stay Python) |
| `constant_time_compare` | yes | yes (unchanged) |
| `_nx_self_fail` + `os._exit(137)` | yes | yes (unchanged) |
| `_nx_mlock` + page alignment | yes | yes (unchanged — needed pre-dlopen in Python) |
| native enforcement call | n/a | **mechanism recovered**: "dlopen's the object via CDLL and calls exported nx_apply_protections() (missing -> self-fail), records its bitmask" — the model knows the loader calls a native entry and that the entry is mandatory |
| native enforcement SEMANTICS (what the entry does) | n/a | **not recovered**: the answer contains no description of prctl/setrlimit/PT_DENY_ATTACH/signal handlers at the native layer — those live in stripped machine code |
| PT_DENY_ATTACH | n/a (macOS was a silent no-op) | **not recovered** — and newly APPLIED on macOS artefacts (additive enforcement) |

### The boundary-push deliverables behind the table

1. `native/enforcement.c`: `nx_apply_protections()` — Linux prctl
   PR_SET_DUMPABLE=0 + RLIMIT_CORE=0; macOS setrlimit + PT_DENY_ATTACH
   (additive); silent `_exit(137)` fatal-signal handlers. Self-contained,
   C99, exported default-visibility, compiles clean under the blob build's
   exact flags.
2. Both blob producers compile it into every blob (`payload.c +
   enforcement.c`); a missing source refuses the build (fail closed).
3. The loader dlopens WITHOUT running init, calls the entry BEFORE any
   payload code, records the returned bitmask (1 dumpable-off, 2 core-zero,
   4 deny-attach) for NIXON_MEM_REPORT, and refuses a blob without the
   entry (`_nx_self_fail`).
4. Emission rule: the top-of-loader Python block is emitted only for builds
   that can reach payload plaintext through Python. A `native_only=True`
   loader carries ZERO syscall names — measured on the generated text.
5. memguard's snippet switches to a report-only form for native-only builds
   (reads the bitmask, names no syscalls).
6. Pre-existing defect fixed on the way: the Output pack block classified
   generator-PACKED bytes and refused every native-only build; the
   classification now runs on plaintext ELF and the pack block skips an
   already-packed dict.

### What was measured, precisely

* Real blob (built through the production `build_local_cython`), dlopen'd in
  a subprocess by the committed probe fixture: `mask=3`, `CoreDumping: 0` —
  both syscalls applied before any payload init.
* Rebuilt max artefact: rc 0, `OK verify:14`; all six attack_chain routes
  rc 137 with merkle/HMAC refusals (control rc 0).
* DS 4.1 Flash re-probe: 125 loader names returned; the mechanism
  ("calls exported nx_apply_protections(), missing -> self-fail") is in the
  answer; the native semantics are not. The payload-side numbers are
  unchanged (the probe's payload recovery stayed at nothing — the model
  described the wrapper, not the payload).
* `tests/test_native_enforcement.py`: 6 tests pin the contract.

### What this does NOT claim

The max-profile artefact's readable block remains — honestly. The sectioned
fallback is production-reachable, so the Python anti-dump block must stay on
that path; the enforcement there is layered (Python block + native entry).
The boundary push is fully realized for loaders whose only payload path is
the native module; for the max profile it is a measured cost-increase
(enforcement semantics in machine code, mechanism still in text) plus one
new enforcement (PT_DENY_ATTACH on macOS). Client-side software cannot reach
full immunity; what changed is where the semantics live.

---

## 5p. The full-max profile: every flag enabled, four defects found and fixed

The operator asked why the max build was missing flags added during the
session, and "how is it maximum protection when Cython is not involved".
Two answers, both measured:

### Cython IS involved (evidence)

The max build compiles the payload through Cython into the native blob:
the build log prints "Native backend: clang/gcc", the artefact embeds an
XOR-packed ELF blob, extract_blob decodes it (magic 0x7fELF), the blob
exports PyInit_payload + nx_apply_protections, and the payload executes as
machine code on the primary path. The confusion came from the profile
string not naming `native`; `--package layers=25 zips=3 stego` arms native
implicitly because section_split defaults on and the blob is built in the
inner branch. The profile now names `--package native` explicitly.

### The max profile now carries everything the harness can self-supply

`pydeobsbench/run.py` PROFILES["max"] (the old string is kept as
`max-legacy` so the §8 baseline stays comparable):

    --package native layers=25 zips=3 stego
    --section-count 8
    --transforms data function-intent speculation
    --access trial=7d vm-threshold=65 block-countries=RU,KP
    --watermark pydeobs-max
    (+ --licence token=<harness-issued> env-only; the profile is now in
     LICENCE_PROFILES)
    (+ env: NIXON_VM_DISPATCH=alternate, NIXON_ARTEFACT_SIGN_KEY=<per-run
     Ed25519 key>, pinned at run time via NIXON_PROVENANCE_PUBKEY)

`--anti-rea-level` needed nothing: maximum is already the parser default.

Measured on the full-max build (2026-11-20, tiny target): build 12-19 s;
runs rc 0 with the token and refuses without it (licence gate, kill ladder
`section-stream-failed`); all six attack_chain routes rc 137 (control rc 0)
-- and the bypass route now dies on the PROVENANCE SIGNATURE ("provenance:
signature does not verify"), not merely the merkle check: signing active
makes §1's anti-patch redundancy a three-layer chain.

### Four defects the full-max run exposed (all fixed, all measured)

Turning every flag on at once exercised paths no single-flag test reached.
Each defect was found by the artefact refusing to run (or running when it
must refuse) and reproduced in isolation:

1. **Provenance fingerprint separator** (`pipeline.py`): the build appended
   the key fingerprint as `<fp>:` but the loader's parser requires
   `<fp>: ` (colon-space); `find(": ")` returned -1, the whole 62-char
   slot decoded to 44 bytes, and EVERY signed artefact died at load. The
   sign -> fingerprint -> ship -> load chain had never been run as a
   whole -- each verifier test passed in isolation. Regression test added
   (test_loader_boundary) that performs the build's exact replace and
   parses with the loader's own rule.

2. **Token-derived provenance ignored the prefix** (`attestation.py`): the
   token-bound check decoded the pk slot WITHOUT stripping the fingerprint
   prefix, so every pinned, licence-bound artefact died with "embedded key
   does not match the token's key". Both checks now parse the slot
   identically.

3. **Geofence failed closed on an unknown location** (`pipeline.py` inline
   gate + `sources.py` class): a block-list gate killed every offline host
   (no reachable lookup service -> location None -> refuse), measured as a
   silent rc 137 on a NON-blocked machine. A block list refuses only on
   positive evidence now; allow-lists keep fail-closed. Semantics fix, not
   a weakening: the gate's purpose (refuse sanctioned countries) is
   unchanged, and the lookup failing never had RE-resistance value.

4. **Trial gate treated a foreign-sealed state as tampered**
   (`trial_bind.py`, both the build-time helper and the emitted snippet):
   two builds at the same artefact path share one state leaf; the second
   build could not unseal the first build's state and every legitimate
   in-place update refused to run. An unsealable state is informationally
   equivalent to the DOCUMENTED reset (delete the state file), so failing
   closed granted an attacker nothing and broke updates. Now: fresh.
   Symlink refusal unchanged (the real attacker-controlled condition).

### Diagnostic note

The silent kills were hard to attribute until the kill ladder's own
diagnostic was found: `NIXON_LADDER_DEBUG=1` prints `nx-kill:<reason>` to
stderr before the exit. Documented here because every future gate
investigation should start there instead of strace.

### What is still honest about "maximum"

Client-side software cannot reach full immunity; enabling every flag is
not maximum security (MAXIMUM_SECURITY.md §3.5). What this profile is: the
strongest configuration whose protections were actually built, run, and
verified end-to-end on this host -- with the four integration defects the
exercise surfaced fixed rather than documented as limits.

---

## 5q. ABSOLUTE maximum: every flag, and a native-only loader with no Python fallback

The operator asked for absolute maximum — "all letters if required" — and
whether absolute max can have Cython with NO fallback to Python. Both are
now profiles in the harness, measured end-to-end.

### The native-only loader ships verbatim (pipeline change)

A `--package native-only` hybrid loader used to be wrapped in the
packaging layers, producing a 19 MB wrapper whose CustomLoader exec'd the
payload without `__file__` and broke the identity gate (measured). The
Output-Generation verbatim-ship path now covers this shape: a native-only
loader (FALLBACK_BLOB="DISABLED", native blobs present) is stamped, signed
and shipped verbatim like a sectioned loader. There are NO sections and NO
bytecode fallback: the Cython blob is the ONLY payload path, and if the
blob cannot load the loader runs nothing (fail-closed by construction).

### ABSOLUTE profiles (pydeobsbench/run.py)

* `absolute` — native blob, 8 sections, seal-shard string sealing
  (string-key-env=NX_SEAL_SHARD, shard generated per run, threaded to the
  build AND every artefact run), trial=7d, expire (+45 d), hwid bound to
  this host via fallback_fingerprint() + hwid-lock, kod, driver-check,
  name-gate, block-countries, vm-threshold, watermark, licence binding,
  VM dispatch, per-run provenance signing. Measured: build 19.6 s, runs
  rc 0 with the token, hwid-lock bound.
* `absolute-native-only` — the same gate set, minus sections, plus
  --package native-only. Measured: build ~101 s, runs rc 0, hwid-lock
  bound, and ZERO anti-dump syscalls in the artefact text — the §5l
  boundary push fully realized on a shipped artefact. Three consecutive
  builds after the pool fix below: 3/3 green.

### Fifth defect: the flaky blob build was a Unicode identifier draw

The native-only builds failed intermittently (~50%): the C transform +
Cython pipeline emitted identifiers from the babel pools, and clang
rejects most non-ASCII characters in C identifiers ("character <U+XXXX>
not allowed in an identifier") regardless of what Python's
isidentifier() accepts. Cherokee U+13A0-13F4, Runic U+16A0-16EA,
Devanagari U+0900-097F drew illegal identifiers; some builds drew legal
characters and compiled, some did not. Measured properly (clang
-std=c99 -ferror-limit=0, one identifier per line, 910 candidates, 139
illegal -- the first measurement attempt bundled 40 identifiers per line
and clang's default error limit truncated the report, which hid most of
the illegal characters and made the first "fix" itself still flaky).
The pool is now the measured C-legal set (C99 Annex D.1 shapes: Latin
Ext-A/B and IPA sub-ranges, Greek, Cyrillic, Hiragana, CJK capped at
U+9FA5), shared by utils.get_random_var_name and
transforms.BuiltinAliaser as C_LEGAL_BABEL_RANGES. Three consecutive
builds green after the fix.

### Still operator-supplied (not harness-self-suppliable)

`chain` licence (needs a real ERC-721 on an L2, §5.2 setup), `webhook=`
(a real alerting endpoint), `--tls-ca-bundle` (a real CA bundle),
`--lowering` (needs the shim deployed beside the artefact — measured
1.46x-3.84x per-family overhead). Everything else in the ABSOLUTE command
of MAXIMUM_SECURITY.md §5.3 is now exercised by the harness profiles.

---

## 5r. Reviewer Priority 0 closed: ordering, trust anchor, negative matrix, crypto audit, dep lock

The 2026-11-20 reviewer reports named five release-critical items. Each is
now measured or fixed, and the two that could not be closed are stated as
limits rather than claims.

### P0-1 dlopen ordering — the claim is now precise, and the invariant is a test

Both reviewers are right that "enforcement before PyInit" is weaker than
"enforcement before any native code". On Linux the dynamic linker runs every
shared object's constructors (`.init_array`, `.ctors`, `_init`) before
`dlopen()` returns, so a constructor necessarily precedes
`nx_apply_protections()`. Measured on the shipped object: a real blob carries
**one** `.init_array` entry, a compiler-emitted thunk into the C runtime's
`frame_dummy`/`__cxa_finalize` scaffolding — not `PyInit_payload`, and no
Cython module code.

The invariant that matters is narrower and is now executable
(`tests/test_native_enforcement.py`): a payload that sets a flag at module
init, a forked child that dlopens WITHOUT running init, calls
`nx_apply_protections()`, and verifies at each stage —

    before=False  after_dlopen=False  after_enforce=False  mask=3  after_init=True

Payload initialization happens only after enforcement. Measured on the
production builder, in the test suite, not by hand.

### P0-2 provenance trust anchor — built, deployed externally

The out-of-band Ed25519 pin (`NIXON_PROVENANCE_PUBKEY`) exists and is the
only form that survives an attacker who controls the artefact. The reviewers
correctly note an environment variable is not a trust boundary when the
attacker owns the environment. That is a **deployment** step, not code: the
pin must come from the launcher or protected configuration. Recorded in
`MAXIMUM_SECURITY.md` §5.3 (run-time) and §5.2. The token was already
retracted as a trust anchor (it returns a sealing salt, not a public key).

### P0-3 negative matrix for native-only — seven paths, one contract

`tests/test_failure_modes.py` now pins every path the reviewer listed:
missing blob, corrupt blob, missing enforcement export, enforcement failure,
wrong pin, failed native import, and the absence of a Python fallback. The
last one exposed a **real defect**: `_nx_ci_bypass_ok()` answered "yes"
whenever the CI env pair was set, and four failure sites then reached
`_exec_fallback()` — a Python payload path inside a profile that promises
none. It exited only because `FALLBACK_BLOB` was `"DISABLED"`, i.e. the
path was unreachable only because a second check caught it. Fixed: the
bypass is compiled shut for native-only builds (`if True: return False`
before the environment is read), and the test asserts both halves — every
call site gated, and the gate shut by construction.

### P0-4 crypto path — audited, and it is NOT AES-GCM

The reviewer's distinction is exactly right, and the answer is concrete:

| question | measured answer |
|---|---|
| which primitive protects the shipped sections? | SHA-256 counter-mode keystream XOR (`sha256(key‖nonce‖counter)`) |
| integrity? | HMAC-SHA256 over the plaintext, 32-byte tag, verified before the slice is released |
| key derivation | `sha256("nx-section-key:" ‖ master ‖ index:4 ‖ nonce)` — per section |
| encryption/MAC keys independent? | the section key is used for both; separation is by **section**, not by key role — recorded as a limit |
| nonce uniqueness | `os.urandom(16)` per section per pack (deterministic only for honey/decoy packs) |
| index bound to the key? | yes — relabelling a section's ciphertext fails the tag |
| AAD? | none; the pack-level `state` digest binds count/total/ordering |

Four tests in `tests/test_section_split.py` pin all of this by reconstructing
the construction from the shipped output. The AEAD helper exists and is
separately tested, but **it is not the section path**, and no summary may
merge the two.

### P0-5 dependency lock — now fatal in release CI

`NIXON_REQUIRE_DEP_LOCK=1` is set on the CI test step. The build already
warned on drift; verified that with the variable set it refuses
(`dependency drift and NIXON_REQUIRE_DEP_LOCK=1: cython: lock 3.0.12,
installed 3.2.1; …`). The drift is real on this host, which is the point:
release CI must fail rather than compile artefacts with an unapproved
toolchain.

### P0-6 audit coverage — conclusive scan, baseline recorded

The full scanner ran over the whole repository: **1,470 files, coverage
complete, 0 dependency vulnerabilities**, 919 high / 8 medium / 257 low — and
every high bucket was triaged, not suppressed, in
`docs/security/MIMOSA_AUDIT_BASELINE.md`. Measured class breakdown: path
traversal 587, code injection 271, SSRF 48, command-allowlist 7, hardcoded
credential 3, deserialisation 2.

The 587 path-traversal hits are all sinks whose path came from
`confined_path()` / `mkstemp` / `realpath` 12–56 lines earlier (traced
variable by variable, script in the baseline doc). The 48 SSRF hits are the
project's own build-API clients and the geofence's hardcoded service list.
The credential hits were three synthetic fixtures and one randomly-generated
decoy header — changed to `fixture_…` shapes so no source file contains
anything credential-shaped, synthetic or not.

### Still open, honestly

* A human or Ghidra analyst against the native blob: not tested. The DS probe
  is one instrument.
* Windows CFG function table, CET, a real `cl.exe`, Authenticode trust, macOS
  Hardened Runtime: environment-limited, recorded in
  `THREAT_BOUNDARY_LOADER.md`.
* The farming/shard uniformity across all three runners: local path measured,
  farm path not re-verified in this pass.
* The pin's trust anchor is a deployment procedure, not code.

### 5r-bis. The two items left open in the first pass, now closed

**The constructor probe (reviewer's "required test").** `tests/
test_crash_suppression.py` now compiles a shared object whose constructor
writes a marker, dlopens it without calling anything, and asserts the marker
already exists — the platform fact, measured on this toolchain rather than
quoted from a manual. A second test parses the shipped blob's `.init_array`
with pure Python and asserts `PyInit_payload` is not among its entries.

Together with the end-to-end invariant in `test_native_enforcement.py`
(`before=False, after_dlopen=False, after_enforce=False, mask=3,
after_init=True`) the ordering question is now fully evidence-backed, and
the claim is the narrow one: *no payload initialization before enforcement*.

**Benchmark reproducibility.** `probe_ai` now records, in every result:
`raw_response` (the full model answer, unedited), `prompt_sha256`,
`artefact_sha256`, `artefact_chars_sent`, `scorer`
(`pydeobsbench.ai_probe/2`) and `per_marker` (which names, secrets, numeric
markers and basis terms matched). Verified on a live DS 4.1 Flash call: a
5,014-character response stored in full with both hashes. `tests/
test_ai_probe_record.py` (5 tests, offline via monkeypatched model call) pins
the block, including that the prompt hash covers exactly what was sent and
that no credential-shaped literal can appear in a record.

### 5s. Adaptive attacker: eight routes, and the layer that actually catches each

`scripts/attack_chain.py` now models an attacker who understands every
mechanism (reviewer P2). Two routes were added beyond the original six, and
one fix was required to make the existing rows honest.

| route | result | caught by |
|---|---|---|
| control | rc 0, payload ran | — |
| tamper pack only | rc 137 | merkle |
| bypass self-check only | rc 137 | **provenance signature** |
| bypass + tamper | rc 137 | **provenance signature** |
| restamp (no edit) | rc 137 | merkle |
| tamper + restamp CK | rc 137 | merkle |
| tamper + BOTH stamps | rc 137 | **provenance signature** |
| re-sign with attacker key | rc 137 | **provenance signature** (key fingerprint) |
| CFI checkpoint removed + chain recomputed | rc 137 | merkle (chain recomputation is not enough) |

Measured on the signed `max` artefact, 2026-11-20.

**The finding that matters.** Before signing, `tamper + BOTH stamps` was the
row that ran: an attacker who recomputed the Merkle root *and* the HMAC keyed
with the file's own literal `_NX_SELF_HK` produced a self-consistent artefact
and the payload executed. With load-time Ed25519 provenance active, that same
route now dies on the signature. §1's anti-patching redundancy is therefore
three independent layers on signed artefacts (merkle, HMAC, signature), not
one hash recomputed twice — which is what §5m could only propose, and is now
measured end to end.

**Two defects in the harness itself, found while measuring** (both fixed):

1. The `PK`/`SIG` substitution used the regex group holding the OLD slot
   value instead of the closing quote, producing a line that failed to parse.
   The row then showed `rc=1, payload_ran=False` and looked like a successful
   defence when nothing had been tested. A harness that reports "blocked" for
   a syntax error is the same false-confidence class as the benchmark defects
   in §6.
2. `restamp_all` did not exclude the provenance slot lines from the hashed
   content, while the loader does. Every later row was therefore stopped by
   MERKLE before reaching the layer under test — a false pass for the wrong
   reason. With the exclusion set aligned to the loader's, the rows above
   name the layer that actually fires.

**Honest limits.** The re-sign row uses an attacker-generated key and expects
the fingerprint prefix to catch it. An attacker who ALSO rewrites the
fingerprint prefix to match their key is stopped only by the out-of-band pin
(`NIXON_PROVENANCE_PUBKEY`), which is a deployment step — the §5r limit
stands. The CFI row confirms the chain is a tamper detector, not a trust
anchor: recomputation is expected to work, and the protection is that removal
is *detected*.

### 5s-bis. The chain re-run from a clean build, and the unsigned-build control

The §5s table was measured once. Re-running it from a fresh build this session
turned it into a before/after pair that the table alone could not show, because
the first run happened to use an artefact with no signing key.

**Unsigned build** (`NIXON_ARTEFACT_SIGN_KEY` unset; the build printed
`provenance: no signing key … its integrity check is internal-only`, and the
deliverable carries `_NX_PROV_SIG = ""`):

| route | result | caught by |
|---|---|---|
| control | rc 0, payload ran | — |
| tamper pack only | rc 137 | merkle |
| bypass self-check only | rc 137 | merkle |
| bypass + tamper | rc 137 | merkle |
| restamp (no edit) | rc 137 | merkle |
| tamper + restamp CK | rc 137 | merkle |
| **tamper + BOTH stamps** | **rc 0, payload ran `(36, 'sum')`** | **nothing** |
| re-sign, attacker key | rc 137 | merkle |
| CFI removed + rechain | rc 137 | merkle |

The harness closed with the correct verdict: *"INTEGRITY IS INTERNAL-ONLY: a
tampered payload ran once `_NX_SELF_CK` AND `_NX_SELF_HM` were recomputed."*
That is the honest answer, and it is the one the boundary document states.

**Signed build** (key supplied; `Provenance: artefact signed [VERIFIABLE AT
LOAD]`), same payload, same flags, same harness:

| route | result | caught by |
|---|---|---|
| control | rc 0, payload ran | — |
| tamper pack only | rc 137 | provenance signature |
| bypass only | rc 137 | provenance signature |
| bypass + tamper | rc 137 | provenance signature |
| restamp (no edit) | rc 137 | provenance signature |
| tamper + restamp CK | rc 137 | provenance signature |
| **tamper + BOTH stamps** | **rc 137** | **provenance signature** |
| re-sign, attacker key | rc 137 | provenance signature |
| CFI removed + rechain | rc 137 | provenance signature |

Every route now dies on the signature, and the harness's own conclusion flips
to *"No chain: the tampered payload did not run after the bypass."*

**What this pair establishes, and what it does not.** It establishes that the
signature is the layer doing the work — the same edit that succeeds without it
fails with it, on the same harness and the same payload — so §1's redundancy
on a signed artefact is three layers (merkle, HMAC, signature) rather than one
hash recomputed twice. It does NOT establish that an attacker who controls the
deployment environment is stopped: they can drop the pin. The build says so on
every unsigned run, and the run-time pin remains a deployment step (§5r).

### 5s-ter. The benchmark instrument re-run live, and the record it must produce

The reproducibility item (§5r-bis) is only worth closing if the instrument
still emits the full record on a real run. Re-measured this session with
`python3 -m pydeobsbench.run --profile max --targets tiny --ai`, against
`mistral/deepseek-v4-1-flash-1017` through OpenCode:

    === max / tiny ===
      built in 11.0s: tiny_protected.py (308612 bytes)
      querying DS 4.1 Flash via Mistral...
      AI: names 0/4, secrets 0/2, algo overlap 0.12
      => names 0/4  secrets 0/2  pack_derivable=False

The `probes.ai` record carried every field the review asked for:

| field | value on this run |
|---|---|
| `model` | `mistral/deepseek-v4-1-flash-1017` |
| `prompt_sha256` | `527a0c23…` |
| `artefact_sha256` | `39cea388…` |
| `artefact_chars_sent` | 60000 (truncated) |
| `scorer` | `pydeobsbench.ai_probe/2` |
| `raw_response` | **5,684 characters, stored in full** |
| `per_marker` | `names_hit: []`, `secrets_hit: []`, `markers_hit: []`, `loader_terms_matched: [byte, bytes, digest, …]` |
| `measurement_failed` | `False` |

`tiny` is the CONTROL target — the one where everything is supposed to be
recoverable — and DS 4.1 Flash still recovered 0/4 names and 0/2 secrets,
with only 0.12 algorithm overlap. That is a strong result for the protection
and a caution for the instrument: a control that scores zero is either an
artefact of the prompt surface (60,000 characters of loader, in which the
payload is a minority) or a genuine limit of the recovery attempt. Recording
`loader_terms_matched` is what lets that be examined after the fact instead of
argued about, and it is why the raw response is retained rather than a
summary.



### 5t. DS 4.1 Flash against the NATIVE-ONLY artefact: wrapper fully read, enforcement semantics absent

The §5o probe ran against a signed `max` artefact (sectioned fallback, so
the Python anti-dump block was present by design and was recovered). The
reviewer's sharper question is about **absolute-native-only**, where the
Python anti-dump block is not emitted at all. Measured 2026-11-20 on a real
native-only build (`FALLBACK_BLOB="DISABLED"`, runs rc 0 with its token,
zero syscall names in the artefact text):

| probe term | recovered? |
|---|---|
| `prctl` | **no** |
| `PR_SET_DUMPABLE` | **no** |
| `RLIMIT_CORE` | **no** |
| `setrlimit` | **no** |
| `PT_DENY_ATTACH` | **no** |
| `nx_apply_protections` (the call) | yes, named |
| `_nx_self_fail` / exit 137 | yes |
| loader structure (identity gate, merkle, HMAC, Ed25519 verify, dlopen, mkstemp, mlock) | yes, in detail |

The model's own summary is the finding, quoted verbatim:

> "in this native-only build, `_load_native` selects the platform key,
> base64-decodes the embedded blob (validating ELF/PE/Mach-O/ar magic after
> XOR-decrypting with the derived key), writes it to a fresh mkstemp file,
> mlocks the buffer, dlopen()s it via ctypes.CDLL and calls the exported
> enforcement entry `nx_apply_protections()` BEFORE importing the module
> (failing closed if that symbol is absent) ... The Python fallback
> (`_exec_fallback` ...) is compiled in but explicitly disabled in this
> build (`FALLBACK_BLOB='DISABLED'`, no share data, CI bypass hard-coded to
> False)."

So the model recovered the **mechanism completely and the semantics not at
all**. It knows the loader calls an enforcement entry; it cannot name a
single syscall that entry performs, because those live in stripped machine
code. That is the exact boundary the design claims: identical wrapper
readability to before, materially different recovery of the enforcement
layer.

Two honest limits, unchanged:

* This is one instrument (a model reading artefact text). It says nothing
  about Ghidra, a debugger, or a human against the `.so`.
* The wrapper is still fully readable. `loader_reversed = TRUE` remains the
  correct record for the loader; the claim that improved is narrower, and is
  the one the table above measures.

---

## 5u. Independent binary analysis (Ghidra) and the Windows toolchain probes

Two reviewer items assumed impossible without external resources. Both were
actually testable on this host, and both changed the record.

### Ghidra headless against the shipped native-only blob

`analyzeHeadless` is installed (Ghidra + Java 21). The 192 KB ELF blob was
extracted from a real native-only artefact and analysed with two headless
post-scripts.

**The enforcement shim is fully readable.** Ghidra's decompiler produced:

```c
char nx_apply_protections(void)
{
  iVar1 = prctl(4,0,0,0,0);                 /* PR_SET_DUMPABLE=0 */
  iVar2 = setrlimit(RLIMIT_CORE, &local_b0); /* core limit zero */
  ...
  sigaction(0xd, ...);      /* SIGPIPE */
  sigaction(6, ...); sigaction(0xb, ...);    /* SIGABRT / SIGSEGV */
  sigaction(4, ...); sigaction(8, ...); sigaction(7, ...);
                                             /* SIGILL / SIGFPE / SIGBUS */
}
```

305 bytes in, 1,190 characters of C out, every syscall named. **This
falsifies any claim that the enforcement semantics are hidden from binary
analysis.** The DS model could not name a single syscall because it only
reads artefact TEXT; a decompiler reads the machine code and names all five.
The honest statement is the narrow one from §5o: moving enforcement into the
blob defeated *the text-reading probe*, not analysis in general.

**The payload does hold.** The number that matters:

| measurement | result |
|---|---|
| functions recovered | 374, of which **6 named** (strip removed the Cython map) |
| `__pyx_pf_*` payload symbols | **0** |
| largest functions decompiled | 8, up to 11,826 bytes / 64,395 chars of C each |
| of those, containing `SALT` / `transform` / `verify-me` | **0 of 8** |
| defined strings containing payload material | **0** |
| raw `strings` hits for payload identifiers | **0** |

47,159 bytes of payload code decompiled into 246,485 characters of C, and it
yields no payload identifier, no payload string, and no algorithm the tool
can name. (`PyInit_payload` itself is a 16-byte stub calling
`PyModuleDef_Init`.) That is the first independent, non-LLM evidence that the
payload survives static binary analysis — and it is the reviewer's own
requested test, not a proxy.

### Windows toolchain: CFG function table needs the MSVC CRT, not the headers

The 2026-11-19 entry said the CFG function table "needs clang-cl with the
MSVC headers — not present here". **`clang-cl-19` and `lld-link` are both
installed.** Four probes with them:

| probe | load config | GuardFlags @0x90 | table |
|---|---|---|---|
| `unsigned long` fields (136 B) | 136 B | field beyond size | no |
| explicit-width fields (152 B) | 152 B | `0x100` | no; lld-link: "GuardCFFunctionTable not set correctly" |
| full 288-byte layout incl. LongJump tail | 304 B | `0x100` | no; same warnings |
| no `_load_config_used` at all | **none emitted** | — | lld-link: "Control Flow Guard is enabled but `_load_config_used` is missing" |

`GuardFlags = 0x100` (`CF_INSTRUMENTED`) is reachable and correct.
`0x400` (`CF_FUNCTION_TABLE_PRESENT`) is not, and **the blocker is now
identified precisely**: lld-link only populates `GuardCFFunctionTable` /
`GuardCFFunctionCount` / `GuardFlags` when it emits the structure itself, and
it only does that when the MSVC CRT's guard symbols (`__guard_fids_table`,
`__guard_check_icall_fptr`) are linked in. Those are CRT objects, not
headers — so installing headers would not have helped, and the earlier
diagnosis was wrong in a way that would have wasted someone's afternoon.

### Windows CET: the 2026-11-19 "inert" verdict was a measurement defect, and so was its correction

The same probe sequence showed guard metadata DOES land in the PE once the
structure is correctly sized:

    GuardFlags = 0x144100
      CF_INSTRUMENTED          (0x100)    set
      0x4000                              set
      0x40000                             set
      0x100000                            set

**CORRECTION 2026-11-21, measured with llvm-readobj --coff-load-config over
per-bit probes AND over the real probe object.** The three labels above were
wrong, and so was the "CET verified reachable" conclusion drawn from them:
llvm names 0x4000 **CF_EXPORT_SUPPRESSION_INFO_PRESENT**, leaves 0x40000 and
0x100000 **unnamed**, and names 0x400000 (a value some SDKs call XFG)
**EH_CONTINUATION_TABLE_PRESENT**. The GuardFlags word has NO CET bits at
all. Where CET's opt-in really lives, measured on the same probe object:

    DllCharacteristics = 0xC160
      CET_COMPAT   (0x8000)   set   <- WRONG READING, see below
      GUARD_CF     (0x4000)   set
      NX_COMPAT / DYNAMIC_BASE / HIGH_ENTROPY_VA

and on the FARM .pyd (run 44853081762): DllCharacteristics 0x4160 — GUARD_CF
set, "CET compat ABSENT".

**RETRACTED 2026-11-21 (second correction, reviewer-flagged).** Everything
in the last two paragraphs read CET from the WRONG FIELD. 0x8000 in the
OPTIONAL header's DllCharacteristics is TERMINAL_SERVER_AWARE — the farm
.pyd's 0xC160 was GUARD_CF + TERMINAL_SERVER_AWARE, never a CET marker, and
its 0x4160 was GUARD_CF only. The real CET opt-in is the Debug Directory
type-20 record, which the farm .pyd llvm-verifies as carrying
IMAGE_DLL_CHARACTERISTICS_EX_CET_COMPAT (0x1) — the shipped blob IS
CET-compatible. Full corrected measurement and history: §6b below.
The parser's constants were renamed to the authoritative names
(`PE_GUARD_EXPORT_SUPPRESSION_INFO_PRESENT` et al.), and
`test_guard_flag_bit_names_match_the_authoritative_parser` pins each name
against llvm-readobj so the next mislabel is caught before it reaches a
document.

The linked binary carries **3 `endbr64` instructions**, emitted by default on
this target (`-fcf-protection=full` changed nothing because it was already
on). The `endbr64` half of this record stands — the indirect-branch targets
ARE ENDBR-guarded — but the earlier claim that the GuardFlags bits represented
CET metadata was a mislabeled measurement, corrected above.

**Honest scope on CET:** `endbr64` + DllCharacteristics CET_COMPAT (on the
lld-link probe) mean the image is *marked CET-compatible and its
indirect-branch targets are ENDBR-guarded*. Whether a Windows loader enforces
shadow stack for it depends on the CPU, the OS mitigation policy and whether
the process opts in — none of which exists on this Linux host. The farm .pyd
is NOT CET-compat marked; that remains a real, measured gap.

### 5v. The Authenticode signature was never Windows-valid, and could never be checked

Two defects, both found by exercising the mechanism against a real signed PE
on a host that turned out to have everything needed (openssl for a test
certificate, clang-cl + lld-link for a real PE).

**Defect 1: the emitted signature was generic PKCS#7, not Authenticode.**
`sign_pe` passed `PKCS7Options.DetachedSignature`, so the
SpcIndirectDataContent became the DETACHED content: only its hash reached the
`messageDigest` attribute and the blob itself was never written. Measured on
a real signed PE:

| expectation | measured before | measured after fix |
|---|---|---|
| `spcIndirectData` OID (1.3.6.1.4.1.311.2.1.4) in the blob | **absent** | present |
| image digest embedded in the signed content | **absent** | present |
| contentType declared | `pkcs7-data` (1.2.840.113549.1.7.1) | `spcIndirectData` |
| blob size | 1,499 (detached) | 1,581 (embedded) |

A file like the "before" is a perfectly valid generic PKCS#7 signature and an
INVALID Authenticode signature: Windows would not have shown it as signed.
The old code comment asserted "`cryptography` emits that, so no
post-processing is needed" — it does not, and the assertion was never tested
against a real image. The fix is one line: sign with
`PKCS7Options.Binary` (embedded), not `DetachedSignature`.

**Defect 2: there was no verifier at all.** `authenticode.py` had 13
functions and not one of them checked a signature.
`native_harden.verify_pe_bytes` reported `authenticode: True` from
`sec_size > 0` — "a certificate table exists", which is a directory lookup.

Added `obfuscator/authenticode_verify.py` (no new dependencies; reads the DER
itself). It checks: WIN_CERTIFICATE revision 2.0 and type 0x0002; dwLength
consistent with the table; PKCS#7 DER length consistent with dwLength; and —
the property that makes a signature a signature — **the image's current
Authenticode digest appears inside the signed content**. Optional certificate
pinning is supported. Trust in the ISSUER is deliberately NOT asserted:
that is a PKI question, reported separately by
`native_harden.signing_readiness`.

Measured end to end on a real PE with a self-signed code-signing certificate:

| case | result |
|---|---|
| signed by this build, then verified | **ok, digest_matches** |
| one byte flipped after signing | rejected: "digest does not appear in the signed content" |
| unsigned image | rejected: "no certificate table" |

`native_harden` now reports BOTH facts — `authenticode` (table present) and
`authenticode_verified` (digest verifies) — so a non-empty directory can no
longer read as "signed". 15 tests in `tests/test_authenticode.py` pin the
signer, the verifier, the tamper rejection and the two-field reporting.

**Still operator-supplied, unchanged:** a CA-issued certificate. A self-signed
one proves the MECHANISM; it does not confer trust, and this record does not
claim otherwise.

### 5w. A 2%-of-runs wrong-answer bug in the ORAM slot allocator

Found by refusing to accept a flake (reviewer: "I would also remove the
underlying test interference rather than simply treating every parallel
failure as environmental"). Shard 3 failed once in three runs on
`test_bitwise_only_argument_is_virtualized_and_correct` and passed every time
in isolation. Reproduced deliberately — eight shard runs, two failures,
assertion captured:

    _exec(src, "encrypt", 10, 6) returned 0, expected 12

**Cause.** `data_protector.py` allocated ORAM slots with
`rng.randint(0, 63)` per variable and **no collision check**. When two
variables drew the same slot the transform emitted:

    _oram_x = _nx_oram(64)
    _oram_x.write(34, pack(key))
    _oram_x.write(34, pack(data))      <-- SAME slot
    result = read(34) ^ read(34)       <-- always 0

Collision probability for 2 draws from 64 is ~1.6%; measured rate was
**8 wrong answers in 400 transform runs**.

**Scope, measured.** The ORAM branch requires two or more sensitive variables
inside one bitwise expression. The benchmark payload shape
(`tiny`/`algo`/`inventory`/`cipher`) uses the *virtualisation* path instead:
100/100 runs contained no `_nx_oram`. So no benchmark artefact was corrupted,
and the `max`/`absolute` measurements stand. The bug affects payloads that do
have such a function — which is exactly the case the unit test covers, and why
only that test ever saw it.

**Fix.** Draw without replacement from a shuffled pool, widening the pool when
a function has more sensitive variables than slots. Verified: 600 runs, 0
wrong answers; 200 runs, 0 collisions; 300 runs on the exact pipeline
transform, 0 broken.

**Why the original test missed it.** It asserted the answer for ONE seed,
which passed 98% of the time. The replacement asserts the property over 200
draws; at the old collision rate that fails on 86.6% of runs, so the bug class
cannot hide behind a lucky seed again. Two further tests cover the semantic
check over 200 draws and pool widening at 70 variables.

**The general lesson, recorded because this project keeps meeting it.** A test
that is green most of the time is not evidence about a random transform. The
review called this out as a process issue ("isolated reruns"); here it was
also a real silent defect that changes program output — the worst class for a
protection system, because the artefact still runs and still looks fine.

---

## 5x. Farm build on real runners: 3/3 OS blobs, and five defects only a runner could expose

The reviewer's open item was "farm/shard uniformity — needs final multi-runner
confirmation", and the platform table listed "actual Microsoft cl.exe backend —
not demonstrated". Both are now closed by running the farm from the current
tree with the gh token that was already on the host.

**Result: run 44782055753, all three jobs green.**

| job | compiler | artifact |
|---|---|---|
| windows-latest | **Microsoft `cl.exe` 14.52.37025** | `blob-payload.pyd`, 161,280 B |
| ubuntu-22.04 | gcc 11 | `blob-payload.so`, 188,328 B |
| macos-latest | Apple clang | `blob-payload.dylib`, 386,464 B |

The local artefact embeds all three and runs (`OK verify:14`, rc 0).

### Five defects found, none visible to a local build

1. **`platform=github` without a token shipped a single-OS artefact and
   reported success.** windows/darwin `NATIVE_BLOBS` were empty and the build
   ended with "ALL OPERATIONS COMPLETE". Now it refuses (rc 1) and names all
   three token sources, with `--skip-cloud` as the deliberate local route.

2. **gcc flags were passed to `cl.exe`.** The driver detected MSVC by looking
   for `VSCMD_ARG_TGT_ARCH`, which GitHub's Windows image does not set, so it
   took the mingw branch (`cl : D9002: ignoring unknown option
   '-fstack-protector-strong'`). Detection now reads the CC distutils will
   actually use, with the env as fallback.

3. **Cython was unpinned.** The runner installed 3.3.1 against the project's
   3.0.12 lock, and 3.3.1's generated C failed under MSVC with `C2124: divide
   or mod by zero`. Pinned on all three platforms — which also satisfies the
   `NIXON_REQUIRE_DEP_LOCK` policy enforced in §5r.

4. **`-pie` on a `-shared` link.** With `-shared` already present, gcc treated
   the `.so` as an executable-style PIE: `undefined reference to
   PyException_SetTraceback`. Removed; `-fPIE` stays in the compile flags.

5. **`-fPIE` instead of `-fPIC` for the object.** `relocation R_X86_64_PC32
   against undefined symbol '_Py_NoneStruct' can not be used when making a
   shared object; recompile with -fPIC`. The local build already carried the
   `-fPIC` correction; the farm driver never received it.

### And one defect in the artefact, found by the farm

`--transforms` put 150+ non-ASCII identifiers in the payload. It compiled
locally (Cython transliterates them to ASCII C symbols) and died on every
runner:

    UnicodeEncodeError: 'latin-1' codec can't encode characters in
    position 115899-115905: ordinal not in range(256)

Cython 3.0.12 on Python 3.11 chooses that encoding internally;
`PYTHONUTF8`/`PYTHONIOENCODING` at the step and in the driver changed nothing.
Fixed with an `ascii_only` mode on `get_random_var_name`, driven by
`NIXON_ASCII_IDS` and set from the native option dict (`unicode_ids=False` is
the signal). Measured: native payloads 0 non-ASCII, pure-Python payloads keep
their 345. **No protection lost** — Cython was transliterating those
identifiers into ASCII C symbols anyway, which is why the blob never carried
them.

### The most important one: an unbound signed artefact was never verified

The farm artefact carried a correct Ed25519 signature (88-char sig, embedded
key fingerprint) but the **verification check was never emitted**, because
its placement condition was `if _prov_token_bound`. Measured: running it with
a deliberately wrong `NIXON_PROVENANCE_PUBKEY` still printed `OK verify:14`
and exited 0, and `tamper + BOTH stamps` ran.

Fixed: the check is emitted for every signed build (after the verifier for
the unbound case, after `_nx_licence_key` for the token-derived case).
Re-measured on a fresh artefact — **all six attack-chain routes now die on the
provenance signature**, including `tamper + BOTH stamps`, the route that
defeated §1 before signing existed:

| route | result | layer |
|---|---|---|
| bypass + tamper | rc 137 | provenance signature |
| restamp (no edit) | rc 137 | provenance signature |
| tamper + restamp CK | rc 137 | provenance signature |
| tamper + BOTH stamps | rc 137 | provenance signature |
| re-sign, attacker key | rc 137 | provenance signature |
| CFI removed + rechain | rc 137 | provenance signature |

### Honest limits

The unbound check verifies against the **embedded** key, so it detects
tampering but not a re-sign whose new key is also written into the slot — that
needs the token-derived variant plus the out-of-band pin, unchanged from
`THREAT_BOUNDARY_LOADER.md`. `runner_attest.verify` (controller-side check of
the runner's own attestation against the pre-upload digest) is implemented and
unit-tested but was not re-run against these three artefacts in this pass.

### 5x-bis. CFG function table on REAL cl.exe: the flag never reaches the linker

The farm finally put a genuine `cl.exe` behind this item, and it narrowed the
problem from "unknown blocker" to one measured fact.

**What real cl.exe does achieve.** The Windows job (Microsoft `cl.exe`
14.52.37025, run 44794331750) produced a `.pyd` with:

| field | value |
|---|---|
| load config | **320 bytes** — the CRT emitted it (vs 288 for the hand-written file) |
| `GuardFlags` | `0x100` = **CF_INSTRUMENTED** — instrumentation is real |
| `GuardCFFunctionTable` | `0x0`, count `0` |
| `CF_FUNCTION_TABLE_PRESENT` (0x400) | **clear** |
| `DllCharacteristics` | `0x160` — GUARD_CF (0x4000) **not set** |

So compiling with `/guard:cf` works and the CRT supplies a full structure, but
the LINK does not know CFG is on.

**The measured reason.** The `link.exe` command line in the job log contains
`/DLL` and **no `/GUARD:CF`**. Two attempts to deliver it were both measured
ineffective:

| route | result |
|---|---|
| `extra_link_args=["/GUARD:CF", ...]` | absent from the link line |
| `LDFLAGS=/GUARD:CF ...` in the environment | absent from the link line |

setuptools' MSVC path does not forward either to `link.exe` in this version.
That is an upstream packaging limitation, not a property of this project's
code, and it is the whole of the remaining gap: with `/GUARD:CF` on the link,
link.exe writes the guard table and sets both `DllCharacteristics` 0x4000 and
`GuardFlags` 0x400.

**Also measured, and worth keeping:** omitting the hand-written
`_load_config_used` on MSVC is the RIGHT change regardless — the CRT's own
320-byte structure is larger and is the one the linker rewrites. It now only
ships for the clang-cl/mingw case (`NIXON_MSVC_LOAD_CONFIG=1` restores it),
where nothing else would emit one.

**Honest status.** CFG instrumentation: REAL and measured on real cl.exe.
CFG function table: still absent, with the cause now pinned to setuptools not
forwarding link flags — not to a missing compiler, headers, or CRT symbol. The
workarounds that remain are a custom build_ext or invoking link.exe directly;
both are packaging changes with their own risk, and neither is claimed here.

## 5y. Two records that lied about the artefact: unicode identifiers and the manifest

Both items below were found by asking a different question than "does the test
pass": *does the artefact say something true about itself?* Neither was a
crash. One was a build that failed on two of three runners; the other was a
signed record that answered "no native blob" about a native binary.

### 5y.1 The scoped ASCII-identifier fix: 376 → 0, with no process-wide flag

The farm run that first went 3/3 (5x) needed `unicode_ids: False` for native
builds, because Cython 3.0.12 on the Python 3.11 runner image writes an
intermediate stream as latin-1 when the payload carries non-ASCII
identifiers, and 150 such characters failed the compile with
`UnicodeEncodeError` on two of three images. The payload's own protection
value from unicode identifiers is close to nil on the native path (Cython
transliterates them to ASCII C symbols anyway — measured 0 non-ASCII bytes in
the generated C), so disabling them costs nothing there.

The first implementation read a process-global environment variable. That was
wrong, and the suite said so: `test_symbol_renamer_works`,
`test_other_public_names_are_still_renamed` and five tests across
`bench_verification_bundle`/`test_verification_bundle` failed, because the flag
leaked into every other build in the same interpreter. The replacement is a
per-call `ascii_ids` parameter threaded through the three emitters that
actually produce names:

| emitter | how it was reached | before | after |
|---|---|---|---|
| `SymbolRenamer` | `renamer = SymbolRenamer(ascii_ids=…)` | 163 non-ASCII | 0 |
| `StringLiteralObfuscator` (`_generate_babel_name`) | `ascii_ids=…` on the constructor | 90 | 0 |
| `VARS['PART_PREFIX']` and friends | `_vars_for(ascii_ids=True)` per call | — | ASCII |

`_vars_for` returns the module table unchanged for every other caller and
rebuilds only the name entries from `_VARS_MAP` when ASCII is asked for; the
non-name entries (`MAGIC`, `STR_KEY`, `PART_PREFIX`, `MARKER_TOKEN`, the
`FUNC_*` tables) are copied verbatim, so an ASCII build changes identifiers
and nothing else.

**Measured, three ways:**

1. Direct AST measurement of a two-function/one-class payload:
   `unicode_ids=False` → **0** non-ASCII NAME tokens (was 90 → 7 → 0 across
   the three emitters). `unicode_ids=True` in the same process immediately
   afterwards still emits 5 unique non-ASCII names, which is the leak test
   the env-var version failed.
2. A real `--package native` build: the Cython input
   (`payload_protected_Packed.py`, 2.9 MB) contains **0** non-ASCII bytes.
3. The same build's deliverable loads its module from a temp `_nx_*.so`
   (`MODULE_NAME: payload`, `MODULE_ORIGIN: /tmp/_nx_*.so`) and prints its
   output — the native path, not the bytecode fallback.

The pure-Python path keeps babel identifiers, which is where they reach the
shipped source and are worth something.

### 5y.2 `native_blob: {bytes: 0}` about an artefact that was a native blob

The §7 signed build manifest records what produced an artefact. Its
`native_blob` field held a hash and a size of **0 and ""** on a build whose
deliverable carried a 110,488-byte `.so` and demonstrably ran it.

The cause was structural rather than a typo. The compiled modules never touch
disk: the build holds them base64-encoded in memory and XOR-packs them
straight into the loader. The manifest only ever read `native_blob_path`, and
no caller sets it — so the field could only ever report "absent". A control
that always answers the same way is worse than no control, because it teaches
a reader to skip the field.

The fix passes the in-memory mapping to `write_manifest` and records:

| field | meaning |
|---|---|
| `bytes` / `sha256` | the largest embedded blob (keeps the single-blob schema meaningful) |
| `platforms` | per-OS `{bytes, sha256}` for every blob actually embedded |
| `hashed_form` | `plaintext-object-image` |

That last field is not decoration. The hash covers the **plaintext** object
image, while the bytes inside the artefact are that image XOR-packed against
the loader's derived key — so hashing the embedded base64 literal directly
yields a different digest even for a perfectly correct build. Anyone comparing
the two would otherwise conclude the artefact had been tampered with. Naming
the form turns a false positive into a documented invariant.

**Measured end to end** after the fix: `native_blob.bytes = 118,672`,
`platforms = ['linux']`, `hashed_form = plaintext-object-image`, and the same
artefact still runs with `MODULE_ORIGIN: /tmp/_nx_*.so`.

**Tests.** `tests/test_manifest_native_blob.py` (6 tests) pins the contract:
the record is built from the mapping, states its hash form, covers every
embedded platform, does not record empty strings as blobs, stays honestly
empty for a bytecode build, and keeps the old file-based input working.

### 5y.3 A fail-closed artefact that reported success

Found by running the documented ABSOLUTE native-only command and checking the
exit status instead of the output. With a wrong or missing seal shard, the
artefact printed **nothing** and exited **0**.

That is the worst shape a failure can take. Nothing had executed — the blob
could not be decrypted, and the profile has no Python fallback by design — but
systemd, CI, a supervisor, a benchmark harness, or a shell `&&` chain all read
exit 0 as success. The profile's own documented promise is:

> "If the blob cannot load, the loader runs nothing (fail-closed by
> construction; there is nothing else to decrypt)."

The *construction* was fail-closed. The *observation* was not. A control whose
failure is invisible is not a control.

**Cause, in two lines.** Every failure path in `_load_native()` ends
`return None`, and the entrypoint was the bare call:

```python
if __name__ in ("__main__", "__mp_main__"):
    _load_native()
```

The return value was discarded, so the process fell off the end of the module
with status 0 regardless of what happened inside.

**The fix, and the bug the fix had.** The entrypoint now captures the verdict
and, for a native-only build, exits 78 with a reason on stderr when nothing
ran. The guard is the existing `__NX_NATIVE_ONLY_GUARD__` placeholder, so the
behaviour is compiled out for every profile that has a fallback.

The first version of the fix was wrong, and the measurement caught it: with the
**correct** shard the artefact printed `(36, 'sum')` and *then* exited 78. The
success path was `if _nx_ok: return` — a bare return, i.e. `None` — so success
and failure were indistinguishable to the new check and it fired on a
successful run. Success now returns a sentinel:

| path | returns | meaning |
|---|---|---|
| blob loaded, payload executed | `True` | ran natively |
| fallback executed | `sys.modules[__name__]` | ran in Python (non-native-only profiles) |
| nothing ran | `None` | fail-closed — fatal for native-only |

**Measured, before and after, on real `--package native-only` builds:**

| shard | before | after |
|---|---|---|
| correct | `(36, 'sum')`, rc 0 | `(36, 'sum')`, rc 0 |
| wrong | *(silence)*, **rc 0** | `[FATAL] native-only artefact: the embedded blobs could not be loaded and no Python fallback exists (exit 78)`, rc 78 |
| missing | *(silence)*, **rc 0** | same FATAL, rc 78 |

The normal `--package native` profile was re-built and re-run afterwards to
confirm the fallback path is untouched: `(36, 'sum')`, rc 0.

**Tests.** `tests/test_failure_modes.py` gains two cases — the verdict is
captured rather than discarded and `exit 78` is present for the native-only
profile, and a fallback build does *not* gain the exit (the guard is
substituted to `False`). Both assert on the emitted loader, which is the
artifact that actually ships.

### 5y.4 The independent binary analysis re-run against a freshly built blob

§5u reported the Ghidra result once. Re-running it this session on a blob built
from the current tree confirms the finding is a property of the code, not of
that afternoon.

The blob was recovered the way an analyst would recover it — using the
project's own `pydeobsbench/extract_blob.py`, which reproduces the loader's
arithmetic from the two key shares the artefact carries:

    linux: 151424 bytes, magic=b'\x7fELF' -> extracted/linux.so
      exported symbols: ['nx_apply_protections', 'PyInit_payload']

Then `scripts/ghidra_boundary_check.sh` ran Ghidra headless over it. Two
questions, two very different answers:

| question | measurement |
|---|---|
| is the **enforcement shim** readable? | **yes** — `nx_apply_protections` at `0x0011eaa0`, 305-byte body, decompiled to 1,190 chars with `prctl`, `rlimit`, `setrlimit` and `sigaction` all named |
| is the **payload** recoverable? | **no** — the 8 largest functions are 43,460 bytes and decompile to 249,767 chars of C, with **0** payload needles and **0** payload strings |

The shim's readability is expected and was already recorded: it is a 305-byte
syscall wrapper, and a syscall wrapper that could not be read would be
suspicious. What matters is that reading it tells an analyst exactly what the
process-level policy does — and nothing about the payload. The payload's 249,767
characters of decompiled C contain none of the needles supplied, and no string
constants from the source.

One correction to how those numbers are stored, because I misread them first:
`BigFnSurvey.java` writes `"chars"` as the **length of the decompiled C**, next
to `"bytes"` as the function's body size. The first pass read `chars` as a
body size, concluded decompilation had produced nothing, and nearly reported a
decompiler failure. The JSON has no `c_code` field at all. Worth stating
because "the tool produced zero output" and "the tool produced a quarter of a
million characters containing nothing useful" are opposite conclusions about
the same run.




## 5z. CFG function table: the flag reached the linker, and the gate that refuses a partial result

§5x-bis closed with "setuptools does not forward link flags" and two named
workarounds that were "not claimed here". Both halves of that sentence were
wrong, and the farm run that found it also exposed a second latent defect in
the ASCII fix.

### 5z.1 The diagnosis was wrong: extra_link_args DOES reach link.exe

The claim came from reading a job log, not the toolchain. Reading the installed
setuptools instead:

    setuptools/_distutils/compilers/C/msvc.py:link() builds
        ld_args = ldflags + lib_opts + export_opts + objects + /OUT:
    then does
        if extra_postargs: ld_args.extend(extra_postargs)
    and build_ext.build_extension() passes
        extra_postargs = ext.extra_link_args or []

So `extra_link_args` is forwarded verbatim to link.exe. What is NEVER read is
`LDFLAGS`: the MSVC compiler class has no reference to that variable at all,
so the environment route — the one the previous attempt switched to after
"extra_link_args did not work" — could not have worked for a different reason
than the one recorded. And the extra_link_args attempt failed for a simpler
reason still: the farm driver hard-coded `_extra_ld = []` in its msvc branch,
so the list was empty before `Extension()` ever saw it.

The fix is one line plus an explanation: `_extra_ld = ["/GUARD:CF"]` on the
msvc branch, and `/guard:cf` stays on the compile side, where MSVC documents
the duplicate as ignored.

### 5z.2 A gate, because "recorded" is not "refused"

The runner already parsed the produced PE and recorded the CFG verdict — which
is how three runs shipped a `.pyd` with `CF_INSTRUMENTED` and no function
table while every log line said hardening was applied. Recording a shortfall
is not refusing it. `native_harden.cfg_function_table_gate(report, toolchain)`
now returns a reason or None, the driver raises `SystemExit` on the reason
when `NIXON_REQUIRE_CFG=1`, and the workflow arms that variable on the build
step. The gate lives in `native_harden` (which the runner already uploads)
rather than inline in the driver, so the same code runs in the unit tests and
on the runner; enforcement is scoped to the `msvc` toolchain because GNU ld
has no CFG at all and a mingw windows build must keep building.

### 5z.3 The farm run that verified the fix also caught the ASCII leak again

The first re-run failed on ALL THREE runners, inside Cython, with the same
latin-1 error the ASCII fix was supposed to have closed:

    UnicodeEncodeError: 'latin-1' codec can't encode characters in
    position 118427-118434: ordinal not in range(256)

The earlier verification had used a friendly subset of the native option
dict. The farm compiles with the FULL `_native_ast_opts`, and one emitter in
that path had never received the flag: `SymbolRenamer.get_new_name` still
called `get_random_var_name(old_name)` with no `ascii_only` — the string
sealer's generator had been fixed and this one had not. Rebuilt with the exact
dict, the leak reproduces locally (6 babel names); fixed, 0.

The ASCII name shape also changed, in the stricter direction: the first
variant embedded the original name as a stem (`mix_aBcDeFgH`), which survives
into the Cython-generated C as a readable hint about the source name. The
babel pool gives the analyst nothing, so the ASCII pool now has the same
shape — `_nixon_<suffix>`, no stem — and the renamer test that asserts the
original name no longer appears anywhere passes again.

**Tests.** `tests/test_native_ascii_ids.py` (3): the exact dict produces 0
non-ASCII; the leak site itself generates ASCII; and the pure-Python path
STILL gets babel names (a global switch would be a protection regression).
`tests/test_native_harden.py` (+5): the gate refuses a table-less MSVC
object, passes a full-CFG one, never fires for gcc/mingw/clang, tolerates a
malformed report, and the rendered driver/YAML carry the flag and the armed
gate.

### 5z.4 CLOSED: the CFG function table, verified on real cl.exe by llvm-readobj

The §5x-bis gap ("setuptools does not forward link flags") is closed, but not
by a custom build_ext — by reading the toolchain and fixing two wrong
assumptions, then re-running the farm until the evidence landed.

**The chain of measured defects that hid the real one:**

1. "setuptools does not forward extra_link_args" — FALSE. The installed
   `msvc.link()` does `if extra_postargs: ld_args.extend(extra_postargs)`,
   and `build_ext` passes `extra_link_args` in. The driver hard-coded
   `_extra_ld = []`, so nothing was ever forwarded.
2. `LDFLAGS` — never read by the MSVC compiler class at all. The environment
   route was dead on arrival; setting it changed nothing and the log was
   read as "a setuptools limitation".
3. The toolchain detection mis-labelled cl.exe/link.exe as "gcc" (Windows
   CPython records NO `CC` in sysconfig, `VSCMD_ARG_TGT_ARCH` is unset, no CC
   env), so the driver shipped Linux flags to MSVC:
   `cl: D9002 ignoring '-fstack-protector-strong'`,
   `LINK: LNK4044 unrecognized '/Wl,--dynamicbase'` — and the new CFG gate
   did not fire, correctly, because the LABEL was gcc while the linker was
   MSVC. Fixed by defaulting Windows to MSVC unless CC explicitly names a GNU
   toolchain.
4. The compile flag list carried linker options: `cl: D8021 invalid numeric
   argument '/HIGHENTROPYVA'`. Compile-side is now `/GS /wd4244 /wd4127
   /guard:cf`; the hardening set (/GUARD:CF /DYNAMICBASE /NXCOMPAT /CETCOMPAT
   /HIGHENTROPYVA) travels on `extra_link_args`.

**The verified result (farm run 44853081762, windows-latest, cl.exe
14.52.37025, link.exe 14.52.37025, 3/3 jobs green), read by llvm-readobj
--coff-load-config:**

    GuardCFFunctionTable: 0x18001B578      (non-zero)
    GuardCFFunctionCount: 48               (non-zero)
    GuardFlags (0x10017500):
        CF_INSTRUMENTED (0x100)
        CF_FUNCTION_TABLE_PRESENT (0x400)
        PROTECT_DELAYLOAD_IAT (0x1000)
        DELAYLOAD_IAT_IN_ITS_OWN_SECTION (0x2000)
        CF_EXPORT_SUPPRESSION_INFO_PRESENT (0x4000)
        CF_LONGJUMP_TABLE_PRESENT (0x10000)
    GuardFidTable: 48 real entries (0x1800011A0, 0x1800011C0, ...)

`native_harden.verify_pe_bytes` on the same object: `cfg=True`,
`cfg_data=True`, `cfg_instrumented=True`, `cfg_function_table=True`,
`check(windows, msvc)` verdict `ok` with no `partial`. The gate
(`NIXON_REQUIRE_CFG=1`, armed in the workflow env) passed because the table
is real — and had any of the three intermediate states shipped, it would have
failed the job with the GuardFlags value in the message.

**Correction made while verifying (the CET mislabel).** Cross-checking the
flags with llvm-readobj exposed that this project's own parser had the wrong
names for the upper GuardFlags bits: 0x4000 is
CF_EXPORT_SUPPRESSION_INFO_PRESENT, not "XFG"; 0x400000 is
EH_CONTINUATION_TABLE_PRESENT; 0x40000/0x100000 are unnamed. The earlier
"CET verified reachable (0x144100)" conclusion measured export-suppression
metadata. CET's real opt-in is DllCharacteristics 0x8000: set on the lld-link
probe (0xC160), **absent on the farm .pyd (0x4160)** — so /CETCOMPAT did not
yield a CET-compat image on the farm, and that is now a measured, reported
fact (`cet_compat`) rather than an implied one. Constants renamed, every
name pinned against llvm per bit, and the CET records above corrected.

**Also fixed en route:** the same farm run caught a second ASCII leak the
friendly-subset measurement had missed (§5z.3), and the commit retry loop now
prints `diff --cached --stat` before committing after 8e200f2 shipped edits
under a message that denied them.

### 5z.5 ACCEPTED EXTERNAL LIMITS: Authenticode trust and Apple Developer ID

Two items were repeatedly named "environment-limited". This section closes
them the only honest way available: by stating exactly what was checked, what
the mechanism already does without the credentials, and what the operator
must supply. They are marked **accepted external limits** — procurement and
identity dependencies, not unfinished work.

**What was checked this session, before writing this paragraph:**

| check | result |
|---|---|
| `NIXON_AUTHENTICODE_CERT` / `_KEY` / `_PASS` in the environment | **unset** |
| operator-staged certificate files in the home directory (`*.pfx`, `*.p12`, `*.pem`, keys) | **none** — the only `.p12` files present are mitmproxy's own test CA, which is a proxy fixture, not a Windows-trusted identity |
| GitHub Actions secrets on the farm repo (`Nixon-H/nixon-build-farm-native`) and the main repo | **both empty** (`gh secret list` returned nothing) |

None of these can be conjured by code. A CA-issued Authenticode certificate
requires a certificate authority to validate an identity and sign (DigiCert,
Sectigo, GlobalSign; OV/EV for organizational trust) — that is a procurement
step with real-world verification. A Developer ID requires an Apple Developer
Program membership and identity verification, and its private key lives in a
macOS keychain; this host is Linux, and the farm's macos-latest runner has
keychain infrastructure but no identity either.

**What the mechanism already does WITHOUT the credentials (measured, not
claimed):**

* Authenticode: the farm driver reads `NIXON_AUTHENTICODE_CERT` /
  `NIXON_AUTHENTICODE_KEY` from the environment and, when absent, prints
  "authenticode: no certificate in the environment ... artefact is unsigned"
  (farm run 44853081762 log). The pipeline's own §5v measurement stands: with
  a test certificate the signer produced an embedded, Windows-parseable
  PKCS#7 (spcIndirectData OID present, image digest embedded) and
  `authenticode_verify` accepted it and rejected post-sign tampering — so
  when a CA certificate arrives, the only change is trust, not plumbing.
* Mach-O: the .dylib ships unsigned and `verify_macho_bytes` says so
  (`signature_expected`, CodeDirectory state). There is no codesign step in
  the farm driver at all — deliberately: writing untestable codesign wiring
  would repeat the "flag set, nothing verified" pattern this project keeps
  finding.

**The operator-side steps, written down so they are executable when the
credentials exist:**

1. Authenticode (before the build, on the controller host):
   `NIXON_AUTHENTICODE_CERT=/path/ca-issued.pem
   NIXON_AUTHENTICODE_KEY=/path/matching.key NIXON_AUTHENTICODE_PASS=...`
   — the farm signs each .pyd during the build and the attestation records
   the certificate-table presence plus the verify verdict.
2. Alternatively, GitHub-Actions level: put the material in farm-repo secrets
   and map them onto the build step's env block (the block already exists in
   `create_workflow`; the credential values would come from `${{ secrets: }}`
   style mapping and never be committed).
3. Developer ID (after the macos job, or in a final signing step on the
   runner):
   `codesign --force --options runtime --timestamp
   --sign "Developer ID Application: <NAME> (<TEAMID>)" payload.dylib`
   then `codesign --verify --strict --verbose=2 payload.dylib`. If the
   operator wants it in the farm, the step belongs after "Rename Artifact"
   and must be gated on a secret so an identity-less run stays unsigned and
   honest rather than failing the job.

**Status: ACCEPTED EXTERNAL LIMITS.** Every code-level item from the two
reviews is closed and measured; what remains here is exactly the part that
requires a third party to issue an identity. The artefacts' honesty does not
depend on the credentials: unsigned artefacts say they are unsigned, in the
console, the attestation and the header parse.

## 6a. Review register 2026-11-21: every in-session item closed

The 2026-11-21 assessment left a prioritised register (§7 of that document).
Each row is dispositioned here with its evidence; nothing was moved to a
TODO without a reason.

| register item | disposition | evidence |
|---|---|---|
| **P0** Provision the out-of-band provenance pin | **code + policy closed; deployment stays operator-side** | `NIXON_REQUIRE_PROVENANCE=1` makes an unsigned build FAIL (tests/test_failure_modes.py, 2 tests); the pin's deployment, rotation and revocation are now specified in MAXIMUM_SECURITY §5.6 — pin replacement IS revocation, because verification is local and offline |
| **P0** Signed provenance mandatory for production | **closed** | the release-policy gate above; the unsigned control stays buildable so the §5s-bis measurement remains reproducible |
| **P0** CA-issued Authenticode identity | **accepted external limit** (§5z.5) | env/files/gh-secrets checked empty; procurement + identity validation is a third-party act |
| **P0** Apple Developer ID | **accepted external limit** (§5z.5) | membership + macOS keychain identity |
| **P0** Actual macOS build + runtime test | **CLOSED for build+run** (Hardened Runtime stays external) | farm run 44866777087/44870436990: the driver now IMPORTS the produced blob ON THE PRODUCING RUNNER before upload and records `smoke_test` in the attestation — measured: `payload.cpython-311-darwin.so loads on Darwin (0.01s)`, Windows `loads on Windows (0.04s)`, Linux `loads on Linux (0.08s)`. One revision, three platforms, each blob executed on its own OS. Hardened Runtime codesign remains gated on the Developer ID. |
| **P1** CET compatibility on the farm .pyd | **REOPENED AND CORRECTED (see 6b — the experiment below measured the wrong field)** | 6a's row claimed "MSVC applies the CET_COMPAT bit to EXE targets only" based on optional-header 0x8000/0x4160 values — but 0x8000 in the optional header is TERMINAL_SERVER_AWARE, not CET. With the CORRECT field (Debug Directory type-20 record, EX_CET_COMPAT 0x1), the farm .pyd llvm-verifies as CET-compatible, and the probe re-run (44894648085) shows BOTH the EXE and the DLL variant carry the bit. See 6b for the corrected tables. |
| **P1** 3-platform parity on one revision | **CLOSED** | the smoke-test step above: same revision, each blob imported and executed on its own runner, results in the attestation |
| **P1** Independent review of section encryption | **partially closed: the two recorded limitations are fixed; the AEAD migration is rejected with a reason** | v2 scheme: role-separated enc/mac keys (`nx-section-enc:` / `nx-section-mac:` domains) and the MAC now binds `index‖total‖nonce‖plaintext` (the AAD role) — 6 new tests including a v1-compatibility pack and a relabel/total-tamper pair. The full AES-GCM migration is REJECTED for the section path because the loader must run on customer machines with STDLIB ONLY (no `cryptography` wheel) — the GCM helper stays for environments that have it, and the register's "if the review supports that change" resolves to "the standard construction that satisfies the constraint is the domain-separated HMAC construction, now hardened". |
| **P1** Human/Ghidra semantic analysis | **deepened in-session; the independent human review stays external** | (a) BigFnSurvey now EXPORTS the decompiled C of the top-3 functions (the claim is checkable against text, not a count); (b) the semantic surface is mapped: 7 PyNumber_Multiply + 16 PyNumber_Add + 3 PyNumber_Xor call sites and 109 distinct CPython/Cython API references are findable in the binary — an analyst CAN locate the payload's arithmetic via the interpreter's own imports; (c) dynamic: under gdb the blob load happens in a FORKED CHILD through a memfd/namespace path — a name breakpoint stays PENDING forever and even `follow-fork-mode child` lands in `?? ()` frames (no symbols, no library mapping); the static symbol table is stripped. Honest conclusion: names/strings are unrecoverable; SEMANTICS are reconstructable with effort at known API sites — the register's human review remains the open item. |
| **P1** Independent review of the Mimosa baseline | **self-sampling done; independent reviewer external — and the register's fourth pass keeps this PARTIAL: self-sampling is validation, not review** | fresh scan (1,482 files, 921 high) + fresh samples in MIMOSA_AUDIT_BASELINE.md: 5 traversal re-traced to confined_path; the licensing SSRF is SIGNATURE-GATED (rpc_url from the signed licence, HTTPS-enforced); one scanner FALSE POSITIVE found (section_split.py:30 — a docstring mentioning exec). |
| **P1** Dependency-lock on every release builder | **CLOSED** | the env was scoped to the pytest step; three more artefact-producing steps were unguarded. Moved to JOB scope in ci.yml. |
| **P2** Expand ORAM differential tests | **CLOSED** | 5 expression shapes × 120 draws × (no-collision + semantic-equivalence), reusing the crash tests' executor: 27 tests pass |
| **P2** Broaden RE payloads | **CLOSED** | two targets added: `ledger` (stateful class with a sliding window) and `memo_fib` (self-recursive memoised), each with an independently written equivalent (deque-based; iterative table walk) verified against the recorded output — 6 targets total |
| **P2** Production issuer/revocation/secure-update | **deployment documentation closed** | MAXIMUM_SECURITY §5.6 items 5–6 (rotation = pin replacement; revocation = publish the new pin; `signed: false` manifests must not ship to customers) |

**Two engineering findings made while closing the register** (both now
regression-guarded):

1. The f-string template consumed the backslash-vee sequence inside
   `Installer\vswhere` as a VERTICAL TAB escape (third strike of the
   braces/escapes trap): the rendered YAML carried 0x0B and GitHub rejected
   the workflow in 0 seconds. `test_the_driver_and_yaml_carry_no_control_characters`
   now refuses ANY control character in the rendered driver or YAML.
2. The CET probe needed FOUR measured corrections to reach its verdict:
   cl is not on the step PATH (WinError 2) → vc-env discovery → the
   discovery "succeeded" without resolving (added which() diagnosis) →
   bare-name resolution uses the PARENT's imagery (absolute paths) →
   LNK1561 entry point → and finally the EXE/DLL variant pair. Each step is
   recorded in the driver comments with its run number, because the next
   person touching MSVC invocation on a runner will hit the same sequence.

## 6b. Review register 2026-11-21 (second pass): the CET correction, and the register reopened correctly

The reviewer found a concrete factual error in 6a and it is worse than a
mislabel: **the CET experiment measured the wrong PE field.** This section
reopens what 6a closed and records the corrected state.

### The error

The first "correction" (§5z.4) replaced CET bits in GuardFlags with
"CET's opt-in is DllCharacteristics 0x8000". 0x8000 in the OPTIONAL HEADER is
**TERMINAL_SERVER_AWARE**. The real CET opt-in is a Debug Directory record:

* Type `IMAGE_DEBUG_TYPE_EX_DLLCHARACTERISTICS` (20 / 0x14)
* Its 4-byte payload is the extended characteristics word
* `IMAGE_DLL_CHARACTERISTICS_EX_CET_COMPAT` = 0x0001

Consequences of the error: the farm .pyd — which llvm-readobj shows carries
the type-20 record with `ExtendedCharacteristics 0x1` — was reported as
**non-CET** when it IS CET-compatible, and the "MSVC applies /CETCOMPAT to
EXE targets only" conclusion was drawn from a field that never measured CET.

### The corrected measurement

`native_harden` now parses the Debug Directory (data directory 6) for the
type-20 record and reports `cet_compat` from bit 0x1 of its extended word;
the optional-header word is reported with its correct name
(`terminal_server_aware`). Parser vs llvm-readobj, on the REAL farm .pyd:

| reader | extended record | CET bit |
|---|---|---|
| llvm-readobj --coff-debug-directory | ExtendedDLLCharacteristics (0x14), data 01000000 | IMAGE_DLL_CHARACTERISTICS_EX_CET_COMPAT set |
| this parser (verify_pe_bytes) | ex_dllcharacteristics=1 | cet_compat=True |

The farm probe re-measured with the corrected field (run 44894648085, same
cl.exe/link.exe):

| probe | result |
|---|---|
| EXE variant | ex_chars=1, **cet_compat=True** |
| DLL variant (same object, /DLL /NOENTRY) | DllCharacteristics 0x4160, **cet_compat=True** |

So with the CORRECT field, MSVC link.exe honours /CETCOMPAT for **both**
targets, and the shipped farm .pyd **is CET-compatible-marked**. The earlier
EXE-only conclusion is RETRACTED. The probe also queries the process
user-shadow-stack policy (GetProcessMitigationPolicy, type 17) and records
it beside the module verdict; on run 44894648085 the query returned false on
that runner — recorded, not hidden, because module compatibility and process
policy are related but distinct controls (register item 5).

One honest note kept from the measurement chain: the lld-link probe built by
tests/fixtures (hand-written minimal PE) has NO debug directory at all
(DebugRVA 0x0), so it cannot express CET compatibility even with /CETCOMPAT
— a real toolchain difference, asserted in its test.

### Register disposition after the correction

* **P1-6 (CET)**: the parser, the attestation field and the probe now
  measure the right thing, and the farm .pyd passes. What remains for the
  register is the RUNTIME half — confirming the host python.exe enables the
  shadow-stack policy on supported hardware — which needs a Windows host and
  is recorded as pending, not claimed.
* **Pack v2 downgrade resistance**: the version field is now INSIDE the v2
  MAC (a downgrade edit fails the tag); `NIXON_REQUIRE_PACK_V2=1` bakes a
  v1 refusal into all three emitted decrypt paths at build time; the framing
  tamper matrix (version downgrade/strip, index relabel, total, nonce,
  ciphertext, tag, index swap) is tested independently; plaintext-after-MAC
  ordering and constant-time comparison are pinned on the emitted source.
* **Release trust chain**: the build manifest now binds the source commit
  and the dependency-lock digest (below); the offline-revocation limitation
  is stated in MAXIMUM_SECURITY §5.6; the publish-path/refusal matrix stays
  open pending one release-candidate workflow that hashes the exact
  published bytes.
* **Payload semantic resistance**: PARTIAL, not closed (register item 4,
  second pass reaffirms) — the exports and inventory make analysis
  reproducible; the gdb difficulty is one dynamic observation, not evidence
  of dynamic-analysis resistance (a capable analyst can investigate child
  processes, instrument the loader, inspect memory after decryption, or
  intercept runtime APIs); independent human reconstruction of the shipped
  native-only artefact remains the outstanding review item.
* **Mimosa baseline**: PARTIAL, not closed (register item 4, second pass
  reaffirms) — self-sampling validates classifications but is not
  independent review; a second reviewer should independently sample the
  traversal/SSRF/code-execution categories, inspect the accepted-risk
  rationale, and challenge the claimed false positives (including the
  docstring one this baseline itself claims).
* **Replay/rollback (third pass)**: PARTIAL — the machinery is
  unit-tested, but "actual release-artefact attack tests" (replaying a
  captured licence, rolling back to build N) against a live artefact need
  the licence-chain setup and stay open.
* **Dependency-lock coverage (third pass)**: PARTIAL — the job-scope fix
  covers the `test` job; the register wants every release-producing
  workflow and reusable workflow enumerated, with a deliberate mismatch
  proven to fail each path.
* **Replay/rollback (third pass)**: PARTIAL — the machinery is
  unit-tested, but "actual release-artefact attack tests" (replaying a
  captured licence, rolling back to build N) against a live artefact need
  the licence-chain setup and stay open.
* **Dependency-lock coverage (third pass)**: PARTIAL — the job-scope fix
  covers the `test` job; the register wants every release-producing
  workflow and reusable workflow enumerated, with a deliberate mismatch
  proven to fail each path.

## 6c. Release-candidate acceptance run: two real defects found, one fixed, one measured blocked

The register's decisive test — "start from the current tree, produce the
final release artefact, verify the exact published bytes, run the refusal
matrix" — was executed for real (build NX-RC-004, artefact 124,140 bytes,
built under `NIXON_REQUIRE_PROVENANCE=1` with both signing keys set).

### Defect 1 (found by the acceptance run, fixed): the out-of-band pin was never consulted

The refusal matrix's first two rows FAILED:

| row | before | after the fix |
|---|---|---|
| refusal: missing run-time pin | **rc 0 — ACCEPTED** | rc 137, "provenance: run-time pin missing (release policy requires the out-of-band trust anchor)" |
| refusal: wrong pin (untrusted key) | **rc 0 — ACCEPTED** | rc 137, "provenance: run-time pin does not match the artefact's signing key (untrusted publisher)" |

Root cause, read from the shipped loader: the non-token-derived provenance
check verified the signature against the **embedded** `_NX_PROV_PK` slot and
never read `NIXON_PROVENANCE_PUBKEY` at run time. The embedded-key
self-check is self-referential by construction — exactly the
"signature-as-decoration" failure the feature exists to prevent, surviving
in the non-licence path while the token-derived path had its own pin
handling. `emit_snippet` now takes `pin_required` (baked from
`NIXON_REQUIRE_PROVENANCE` at build time): under the release policy a
missing pin is fatal; with or without the policy, a PRESENT pin must match
the embedded key, so an untrusted publisher is refused even though the
embedded signature verifies against itself. MAXIMUM_SECURITY §5.6 item 4
promised exactly this and it is now implemented and measured.

### Defect 2 (found, documented): the manifest and the provenance have TWO different signing keys

`NIXON_ARTEFACT_SIGN_KEY` signs the loader's provenance slots;
`NIXON_BUILD_MANIFEST_KEY` signs the build manifest. The first RC build set
only the provenance key and the acceptance check caught
`manifest is signed: False` on a build that WAS provenance-signed. Both keys
are release-policy inputs now recorded in §5.6; a release that sets one and
not the other ships a half-signed artefact, which the acceptance run
detects.

### Refusal matrix, final state (all rows executed by RUNNING the artefact)

| row | result |
|---|---|
| control: published bytes under the correct pin | rc 0, payload ran |
| refusal: missing run-time pin | rc 137 (release policy) |
| refusal: wrong pin (untrusted key) | rc 137 |
| refusal: malformed signature | rc 137 |
| refusal: re-signed with attacker key | rc 137 — "run-time pin does not match" |
| refusal: tampered published bytes | rc 137 |
| manifest detects tampered bytes | verify_manifest ok=False |
| threat probe: loader patch | rc 1 (merkle) |
| threat probe: artefact reaches payload | rc 0 |

### Threat-model probes against the shipped Linux artefact

**Unprivileged process inspection: blocked in the tested configuration.
Privileged inspection remains outside the protection guarantee** (scope
corrected 2026-11-21, third pass). What the measurement demonstrates:
`CoreDumping: 0`, `TracerPid: 0`, `/proc/<pid>/maps` denied to the
inspecting process, and `PR_SET_DUMPABLE=0` + `RLIMIT_CORE=0` applied. What
it does NOT demonstrate: that memory extraction is universally blocked.
`PR_SET_DUMPABLE` blocks ordinary `PTRACE_ATTACH` for an unprivileged
caller, but the ptrace permission checks allow a caller with
`CAP_SYS_PTRACE` to bypass the dumpable restriction, and `/proc/pid/mem`
has stricter requirements than `/proc/pid/maps` — both remain available to
a privileged inspector. The measured guarantee is against ordinary,
unprivileged process inspection only. The full permission matrix, measured
LIVE on the shipped artefact (2026-11-21, third pass):

| inspector | result |
|---|---|
| same-UID unprivileged: /proc/pid/maps | **PermissionError** |
| same-UID unprivileged: /proc/pid/mem | **PermissionError** (stricter than maps, also denied) |
| same-UID: gdb attach | **refused** ("The program has no registers now" — the tracer never gains the inferior) |
| core file on a real SIGSEGV | **none produced** (RLIMIT_CORE=0, measured on the crash itself, not inferred from status) |
| root with CAP_SYS_PTRACE | bypasses the dumpable restriction (ptrace man page) — **OUTSIDE the guarantee** |
| root without CAP_SYS_PTRACE | same refusal as unprivileged |
| container / user-namespace variants | configuration-dependent |

The bytecode fallback keeps plaintext resident for builds that ship one;
native-only removes that surface. The privileged rows are the stated
boundary of the guarantee, not claims.

**Loader patching: refused** — a one-byte patch inside the integrity-anchor
region dies at the merkle check (rc 1/137 depending on path).

**Replay/rollback**: the machinery is implemented and unit-tested
(`licence_replay`: nonce + key_version in the signed payload;
`rollback`: monotonic `protection_level` high-water mark, HMAC'd, with its
own stated limit that a determined local attacker deletes the mark file).
The live replay/rollback probes against a running artefact require the
licence-chain setup and stay part of the licence tests rather than the
acceptance run.

**What the acceptance run does not yet cover** (honest): the publish-path
matrix for CI (workflow-refusal semantics are build-level only), and the
Windows strict-mode shadow-stack runtime test on supported hardware. Both
remain register-open.


## 6d. Fourth review pass: key precedence, publish control, isolation audit

### 6d.1 The manifest-key precedence hole — found before it shipped

The reviewer examined the third-pass anchor resolution and identified that
`if public_key is not None: return public_key` let a caller BYPASS the
out-of-band pin with an attacker-controlled key argument. Confirmed by
reading the code; fixed with the register's rule: under the release policy
the OUT-OF-BAND PIN is the single trust authority — an explicit key that
differs from the pin is a refusal, an explicit key equal to the pin
verifies, and a missing pin is a refusal. The full 7-row precedence matrix
from the register is measured in tests/test_manifest_native_blob.py, all
rows passing. Without the release policy the pre-policy contract (explicit
key first, pin honoured when configured) is preserved for existing callers,
with the documented caveat that outside release mode the caller IS part of
the trust boundary.

### 6d.2 Build once, promote the same bytes

`.github/workflows/release.yml` implements the register's sequence: clean
checkout -> signed release-candidate build -> hash the FINAL artefact ->
acceptance matrix against those exact bytes -> upload immutable artefact +
accepted digest + report -> `publish` job (HARD `needs:` dependency — it
cannot run when acceptance fails or is skipped) downloads them back,
recomputes SHA-256, compares against the accepted AND attested digests, and
prints the publish decision as a dry run. The production publish target is
an operator-owned protected-environment job consuming the same chain.
Triggers on `ci.yml` now cover `pull_request` and `merge_group` so the
required check applies to queues, and every third-party action in both
workflows is pinned to a full commit SHA resolved from the GitHub API.

### 6d.3 Signing-environment isolation audit

Measured against the committed workflows (MAXIMUM_SECURITY §5.6 item 9):
only the build job holds signing credentials (ephemeral, dying with the
job); the publish job verifies digests and holds no private key; workflow
and job permissions are `contents: read`; actions are SHA-pinned; the
production signing identity enters through a protected environment with
required reviewers — the operator step.

### 6d.4 Two wording corrections adopted

* The Mimosa policy entry is an auditable RATIONALE record, not a
  machine-enforced scanner exception — the file states this explicitly
  (verified: the hook blocked harness writes before and after the entry).
* The memory guarantee keeps its corrected scope: unprivileged inspection
  blocked in the tested configuration; CAP_SYS_PTRACE bypass documented;
  the core-file row measured on a real crash.
