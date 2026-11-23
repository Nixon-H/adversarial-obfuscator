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


## 6e. Fifth review pass: the evidence-integrity record

The reviewer refused the fourth pass's "final commit verified" claim, and
the refusal was correct: the gate's shard lines recorded `tree=1441525`,
which was the SHORT COMMIT SHA of the PREVIOUS commit — the gate ran before
the fourth-pass changes were committed, so its 29,928 results were bound to
the wrong identity. A commit SHA and a tree object ID are different
identifiers and must not be used interchangeably.

The gate is now an evidence-integrity record. Per shard it writes the FULL
40-character commit SHA, the full tree object ID, the untracked-all dirty
count, the gate run id and the exit code — and it re-reads all three at the
END of the run, reporting `identity_stable` only when nothing moved. The
`--clean` flag refuses to start on a dirty tree (measured: the first
attempt refused with "dirty (3 entries)", exactly the half-committed state
the reviewer's procedure is designed to catch).

**The clean rerun against the final commit:**

    commit: b91a161f8e8e69081e1e3eb21c0915d9f50111ea
    tree:   3eb050ebe20e49b963a14bbd8ae7067f0a70675f
    dirty_files: 0
    run_id: rc-gate-20261121T234916-2101852
    shard 1..10: rc=0, commit/tree/dirty identical on every line
    identity_stable: true
    shards_with_failures: 0

Fourth-pass corrections confirmed, plus the fifth-pass items: SHA
provenance for all four pinned actions (official repositories, expected
releases), the umbrella workflow now covers pull_request and merge_group,
the publish job declares `environment: production` with the explicit
statement that declaration does not prove protection (the admin checklist
governs), and `overwrite: true` appears nowhere in the release workflow.

Remaining open (unchanged, external or admin-side): the production publish
target in a protected environment, the two independent reviews, CA-issued
Authenticode identity, Apple Developer ID, and the Windows strict-mode
runtime test on supported hardware.

### 6e.1 The aggregate test count, independently confirmed

The reviewer's caution not to carry forward the earlier 29,928 figure was
warranted: the per-shard logs of the authoritative run (rc-gate-20261122
T033433-2604693, commit 9ee68f4, tree 54185e71) sum to **29,938 passed,
7 skipped — 29,945 collected**, not 29,928. The difference is real, not
arithmetic drift: the fourth- and fifth-pass additions changed shard
composition (shard 4 grew to 835 with the precedence matrix, shard 5 to
750). The per-shard counts are now recorded in the gate evidence file next
to the identity lines, so the aggregate is re-derivable from the record
rather than remembered.

Two distinctions are now explicit in MAXIMUM_SECURITY §5.6: a stable clean
source identity is NOT a reproducible build (the build embeds per-run
seeds, nonces and ephemeral keys, so same-tree builds are semantically
equivalent but not byte-identical), and the digest-verification chain is
implemented while the production environment still requires
administrator-side confirmation.


### 6f. Replay/rollback attack matrix against the real artefact

The register's "actual release-artefact attack tests" row, measured on the
fresh v2 artefact (NX-V2M-001, pack v=2, 4 sections, signed=True):

| attack | result |
|---|---|
| replay a previously valid section into another slot | **rejected** (rc 1) |
| version metadata modified (downgrade 2 -> 1) | **rejected** (rc 1) |
| section content replaced, OLD authentication data retained | **rejected** (rc 1) |
| truncated section record | **rejected** (rc 1) |
| duplicate section indices | **rejected** (rc 1) |
| control: unmodified artefact | runs (rc 0) |

The v2 tag binding is what rejects the first three: the tag covers version
|| index || total || nonce || plaintext, so replaying a section, downgrading
the version, or swapping content under old authentication data all fail the
MAC before any plaintext is released. The report is preserved as
`replay_rollback_report.json` beside the artefact.

The rollback high-water mark keeps its documented limit (a determined local
attacker deletes the mark file); replay-after-key-rotation follows the pin
replacement procedure (old artefacts verify only against the old pin).


### 6f.1 Malformed-input fuzz suite: two real defects found and fixed

The sixth-pass parser suite (tests/test_parser_fuzz.py) fed systematically
malformed framing into the security-sensitive parsers — 16 structural
malformations of the pack (count/total/sections/index/nonce/data/hint/state
fields, wrong types, wrong lengths, wrong signs), non-JSON and wrong-schema
manifests, oversized declared hashes, truncated binary headers, and binary
garbage into the join — with the goal stated as proving that malformed
input cannot produce an UNINTENDED ACCEPTANCE. Two real defects were found:

1. **`verify_manifest` crashed on the JSON literal `null`.** `null` parses
   successfully to None, passed the exception check, and then died with an
   uncaught AttributeError on `.get` — malformed input producing a crash
   instead of a structured refusal. Fixed: any non-object manifest document
   is refused with a reason.

2. **`stream_join` accepted a corrupted `state` field.** The in-process
   join enforced count/key-hint/index/tags/total but never the §1
   declared-structure digest — only the EMITTED loader checked it, so the
   two verification paths had silently diverged. Fixed: the in-process
   join now enforces the same state digest. The fuzz suite also drove out
   two uncaught exceptions (OverflowError on negative count/total/index in
   the derivation) which are now structured ValueErrors, with bounds
   validated BEFORE the state digest because the digest itself would
   overflow on the malformed values.

Also found and fixed en route: the emitted moving/stream templates
referenced `_declared_total` without defining it — the NameError was
swallowed by their `except Exception` and EVERY pack silently failed to
decrypt — caught by the moving-walker round-trip test rather than by a
green suite, which is why the emitted-snippet tests exercise the real
snippets and not a re-implementation.

The fuzz suite is retained in the committed tree (tests/test_parser_fuzz.py)
with the malformed-input matrix as regression fixtures; a future parser
change that accepts malformed framing breaks the suite. The register's
coverage-guided fuzzing (Atheris/honggfuzz against the binary parsers)
remains the next engineering step beyond this structured matrix.


## 6g. Sixth-pass register disposition, compatibility matrix, and the remaining documented procedures

### Identity reconciliation and the sixth-pass register

| register row | disposition |
|---|---|
| Final commit/evidence identity reconciliation | **CLOSED** — 1b7a07f's diff from 9ee68f4 touches only two .md files (verified: zero executable/test/workflow files); 9ee68f4 remains the code revision with the measured gate; 1b7a07f is the docs/evidence revision on top |
| Actual protected production release | **administrator action** — the workflow chain and dry run are committed (release.yml); the protected-environment configuration and the live RC promotion are the operator steps |
| Independent cryptographic review | **external** — with the review material now defined (§6h) |
| Real artefact replay/rollback acceptance | **CLOSED** — the attack matrix measured on the real v2 artefact (§6f): replayed section, downgrade, old-auth replacement, truncation, duplicate indices — all rejected; control runs |
| Windows strict shadow-stack testing | **external hardware/runtime** |
| Full supported-platform compatibility matrix | **defined and documented** (§6g.1 below); per-combination measurement needs the cross-platform runners |
| Independent payload semantic review | **external** |
| Independent Mimosa baseline review | **external** |
| Parser fuzzing and malformed-input testing | **CLOSED as the structured matrix** — 16-field malformed-input matrix + JSON/binary garbage rows, two real defects found and fixed; coverage-guided fuzzing remains the next step beyond it |
| Authenticode and Apple Developer ID | **external** |
| Build provenance expansion | **partially closed** — the manifest binds compiler/linker identities, toolchain versions, transforms, dependency-lock digest, source commit and the artefact digest; workflow/action identities are recorded in the CI logs; pack format version is the `v: 2` field |
| Incident-response and key-compromise exercises | **procedures documented** (§5.6 items 5/8: pin replacement as revocation, old-pin clients as the limitation, artefact-side auditing via the manifest) — live exercises are operational |

### 6g.1 The supported compatibility matrix, explicitly

| dimension | supported (measured where marked) |
|---|---|
| OS | Windows (cl.exe 14.52 farm build + load measured), Linux (gcc local + farm, load + run measured), macOS (Apple clang farm build + load measured) |
| architectures | x86-64 (all three platforms measured); ARM64 macOS builds and loads via the farm runners (macos-latest is arm64) but runtime loading was measured on the runner only |
| CPython | 3.10–3.14 tested in CI for the suite; the native blobs measured on 3.11 (farm) and the local 3.13 |
| Python ABI | the Cython blob is version-specific by design (cp311 extensions); an ABI mismatch is a LOAD failure that fails closed, never a silent fallback |
| Linux environments | glibc measured; musl (Alpine) is NOT claimed — the blobs link glibc |
| compilers | gcc 14, clang-cl/lld-link 19, MSVC cl/link 14.52 measured; older toolchains are not claimed |
| runtime policy | CFG verified via the debug-dir record; CET compat per artefact measured; Linux dumpability measured live |

**Unsupported combinations fail with an explicit diagnostic, not a silent
fallback** — that property is pinned by the failure-modes tests (missing
blob -> refusal, wrong pin -> refusal, ABI mismatch -> ImportError that the
loader reports rather than hides).

### 6g.2 The reverse-engineering evaluation protocol, ready for the external analyst

1. Hand the analyst the released artefact ONLY (no source, no build tree).
2. Fixed budget: 40 analyst-hours, tools unrestricted, process documented.
3. Objectives: recover (a) the payload's entry function, (b) one numeric
   algorithm, (c) the string surface, (d) the integrity-check semantics.
4. Record: tools, wall time, recovered functions/strings/algorithms,
   behavioural equivalence against the unobfuscated control.
5. Repeat the protocol against the unobfuscated control for the baseline.
6. Preserve the analyst's raw notes as the evidence.

The Ghidra exports (§5u), arithmetic-site inventory (§6d) and gdb
observations (§6c) are the preparation material for this protocol.

### 6g.3 Why the stdlib-only loader rules out the AEAD alternatives

The shipped loader runs on customer machines where the only guaranteed
crypto is the Python standard library. AES-GCM and ChaCha20-Poly1305 both
require the `cryptography` wheel; a loader that imports it changes the
deployment contract from "stdlib only, no install" to "install a native
dependency before the artefact runs", which is a product decision, not a
code decision. The small-audited-native-dependency alternative (vendoring a
minimal, audited AEAD in C) is operationally acceptable in principle but
introduces a C crypto surface that would itself need the independent
review this register defers — so the domain-separated HMAC construction
with the v2 hardening is the measured interim, and the constraint is
documented rather than hidden.

### 6g.4 Wording adopted

Independently generated artefacts are described as **intended to be
functionally equivalent** until equivalence is measured across independent
builds — the phrasing is in MAXIMUM_SECURITY §5.6 item 3's neighbourhood
(reproducible-build distinction) and this log.


## 6h. The gate itself had a coverage hole, and the aggregate count proved it

The fifth-pass instruction was "do not carry forward the previous test count
unless the new gate report independently confirms it". Computing the
sixth-pass aggregate from its own shard logs produced **29,938 passed / 7
skipped — identical to the 9ee68f4 run**, which cannot be right: pass six
added `tests/test_parser_fuzz.py` with ~20 cases.

The count was the tell. The gate's shard lists were STATIC FILES, and they
had silently drifted from the tree. A diff of the shard lists against
`tests/**` found **41 unassigned files**, of which four were suites added
in passes one to six:

    tests/test_provenance_pin.py        (the release-mode pin enforcement)
    tests/test_manifest_native_blob.py  (the 7-row pin-precedence matrix)
    tests/test_native_ascii_ids.py      (the native ASCII identifier contract)
    tests/test_parser_fuzz.py           (the malformed-input regression suite)

plus 33 files under `tests/advanced_protection/` that had NEVER been in a
shard. So every "10/10 shards passed" result since those files were added
was true about the files it ran and silent about the files it did not:
including the very tests that pin the trust-boundary fix and the fuzz
findings. That is the same class of failure the register keeps naming — a
green result that does not cover what it appears to cover.

**Fix: coverage is derived, not hard-coded.** `release_gate.sh` now
enumerates `tests/**/*.py`, excludes non-suite material (fixtures,
`test_data` transform debris, `*.decoy`/`*.attention_poison` artefacts),
round-robins the 440 suite files over ten shards, and **refuses to run** if
any suite file is unassigned or duplicated. The record now carries
`shard_files_total` so a later shrink is visible.

**Re-measured on the same commit and tree** (eb1f1e2 / 3925385, dirty=0,
run rc-gate-20261122T113132-16361):

| metric | before the fix | after the fix |
|---|---|---|
| suite files in the gate | 404 (with stale entries) | **440** (coverage asserted) |
| tests passed | 29,938 | **30,263** |
| tests skipped | 7 | **9** |
| collected | 29,945 | **30,272** |
| shards | 10/10 rc=0 | 10/10 rc=0, identity_stable |

The 327-test difference is the previously invisible material: the four
pass-one-to-six suites plus the 33 advanced-protection files. The earlier
figures (29,928 for the pre-pass-six composition, 29,938 for the drifted
composition) are retained as historical records of what those gates
actually covered — they were never wrong about the files they ran, only
about the files they omitted.

## 6i. Seventh pass: the remaining section-3 rows, and four more defects

### 6i.1 Section 3 rows 4-7: the whole attack table is now measured

The first three rows were measured on the real v2 artefact in 6f. The
remaining four are now measured, and measuring them kept finding defects
rather than confirming the prose:

| attack | measured result |
|---|---|
| restore an older manifest | REJECTED. The protection level sits inside the signed body, so lowering it breaks the signature; a genuinely older manifest re-signed by another key is rejected under the publisher pin |
| restore an older signed artefact | REJECTED. A level below the high-water mark raises the downgrade refusal; re-installing the same level is allowed |
| replay after key rotation | REJECTED under the rotated pin, and the documented OFFLINE limit is asserted rather than claimed away: a client still holding the old pin keeps verifying until it receives the new one |
| remove or corrupt persistent state | removed means fresh install and the mark is re-created; corrupt falls back to fresh-install semantics, never to a trusted level; a forged MAC is not trusted |

All four are permanent tests in tests/test_replay_rollback_rows.py (nine
cases), and they run in the gate because shard derivation is now automatic.

### 6i.2 The protection level was documented but never emitted

The rollback module states that a monotonic protection level is recorded in
the signed build manifest, and nothing ever wrote it. The anti-rollback
check could never fire, because its input never existed. Measured: both
artefacts on this host carried a null level while claiming to be
rollback-protected.

Fixed: the manifest emits the level inside the signed body, derived from
the build's recorded transforms when the caller does not supply one, which
is a real per-build measure that rises as protections are added. Measured
on a fresh build: level 4 alongside 4 transforms.

### 6i.3 The mark reader returned the level without checking the MAC

The writer MACs the recorded level and its docstring promises that a
hand-edited mark cannot lower it without also knowing the key. The read
path never verified that MAC, so an attacker editing the level downward was
obeyed: the MAC bound the value but nothing checked the binding. Fixed: the
reader verifies with a constant-time compare and a mismatch reads as zero,
which is fresh-install semantics and never a trusted lower level. The
forged-mark case is a permanent regression test.

### 6i.4 Section 7: the manifest now identifies its signing key

The signed manifest recorded the algorithm and the signature but not which
key signed it, so a post-incident question, was this artefact signed by the
compromised key, could not be answered from the artefact itself. It is now
recorded as a key fingerprint, the sha256 of the raw public key truncated to
16 hex digits, in the same form the loader embeds, and it is covered by the
signature, so it cannot be edited without breaking the signature it
identifies. The record already binds the compiler and linker identity, the
toolchain versions, the transforms, the dependency-lock digest, the source
commit and the artefact digest.

### 6i.5 Section 5: coverage-guided fuzzing, harness committed and campaign run

The harness at scripts/fuzz/nx_fuzz.py implements all six of the register's
targets (pack, manifest, ELF, PE, Mach-O, pack-state) with strict resource
limits, a 64 KiB input cap, a section-count cap and per-case temp
directories, and it treats an unintended acceptance as the finding: a
parser returning a valid-looking result for hostile bytes raises instead of
only counting crashes.

Measured on this host: Atheris 3.0.0 installed, 300 to 800 runs per target
across all six targets, zero crashes and zero acceptance findings. The
campaign reported no interesting inputs and no symbolize helper, on both
CPython 3.13 and a purpose-built 3.11 environment, and this pass attributed
that to the sanitizer coverage runtime being absent from the interpreter.

**That attribution was wrong — corrected in 6j.3.** The real causes were in
the harness: a `REPO` one directory short, parser imports inside the fuzz
body (after instrumentation had finished), no seed corpus, and an oracle that
rejected legitimate packs. A re-run with Atheris 3.1.0 and clang 19's
libFuzzer runtime after those fixes reached `cov: 61` on pack and `cov: 64` on
PE across 34.5 million executions, growing the corpus from 1 entry to 24 and
70 respectively. The lesson kept below is the one worth keeping: a `cov: 1`
result says nothing about the target until the harness is proven able to
observe coverage at all. The structured malformed-input matrix in
tests/test_parser_fuzz.py, 16 field-level rows plus binary and JSON garbage,
remains the coverage-independent backstop, and it is what found the two
defects recorded in 6f.1.

### 6i.6 Section 4: compatibility matrix, the locally reachable row measured

The matrix is defined in 6g.1. The six required properties are now recorded
for the combination this host can actually exercise:

| property | Linux x86_64, CPython 3.13.5, glibc 2.41, gcc 14.2 |
|---|---|
| 1. build success | yes |
| 2. artefact produced | yes, with the native blob embedded |
| 3. payload execution | yes, measured in the acceptance rows |
| 4. integrity enforcement | yes: merkle plus HMAC plus the provenance pin, and the pin refuses a missing or wrong anchor |
| 5. failure behaviour | fails closed: a missing blob, a wrong pin and a bad signature all exit non-zero |
| 6. mitigation status | RELRO, NX and a stripped local blob; CFG and CET measured on the Windows artefact in 6e |

The cross-platform rows for Windows MSVC and macOS arm64 are recorded from
the farm runs in 5x and 6e rather than re-measured here, and the musl and
older-ABI rows remain explicitly unsupported and unclaimed.

## 6j. Eighth pass: all three §4 rows measured, and the P2 reproducibility question answered in two layers

The completion verifier left three rows open, and they turned out to be two
different kinds of work: the §4 matrix needed the Windows and macOS rows
filled in properly, and P2 needed an experiment rather than more prose.

### 6j.1 The Windows and macOS rows, measured from the shipped blobs

The per-runner attestation JSONs from the farm were **not preserved** — only
the artefacts themselves survive at `/home/nixon/nx_cfg/dl4` and `dl5`. So
the six properties were measured directly from the binaries with the
project's own `native_harden` readers, `readelf`, and a hand-rolled FAT
Mach-O header parse (the reader reports mitigation flags, not the fat
container's per-slice headers).

**Windows — `payload.pyd`, 126,976 B, valid PE.** This is the strongest of
the three rows and it is strongest for a reason worth stating: the
mitigations are not declarations in a manifest, they are present in the
image and the project's parser agrees with llvm-readobj bit for bit.

* CFG is **complete**: `GuardFlags 0x10017500` carries
  `IMAGE_GUARD_CF_INSTRUMENTED` (0x100) + `CF_FUNCTION_TABLE_PRESENT`
  (0x400) + `CF_EXPORT_SUPPRESSION_INFO_PRESENT` (0x800) +
  `CF_LONGJUMP_TABLE_PRESENT` (0x10000). A populated function table means
  the guard set is real, not a linker flag with nothing behind it.
* CET compatibility is present in the **Debug Directory type-20 record**
  (`IMAGE_DEBUG_TYPE_EX_DLLCHARACTERISTICS`, value `0x1` =
  `IMAGE_DLLCHARACTERISTICS_EX_CET_COMPAT`). This is the §6b correction
  holding up under a second, independent read: the bit is *not* the
  optional-header 0x8000 (that is `TERMINAL_SERVER_AWARE`), and a check
  against the wrong field would have produced a false "CET present" on a
  binary that lacked it.
* ASLR + DEP + HIGH_ENTROPY_VA all set.
* Loader initialisation and payload execution: the farm driver imports the
  blob on the producing runner and records `smoke_test.loaded: true` (§5x).

**macOS — `payload.dylib`, 350,928 B, valid FAT Mach-O with two slices
(x86_64 + arm64).** This is the weakest row, and the measurement made it
weaker than the prose had implied:

* `MH_PIE` (0x200000) is **CLEAR** on both slices. `-pie` is not accepted
  on a `-bundle` (`filetype 8`), which is what a `.dylib` built for CPython
  actually is — the same class of error as passing `-pie` to a `-shared`
  Linux link. A loadable bundle is relocated by dyld regardless, so the
  absence is not a runtime hole, but it is also not "PIE" and the matrix
  must not claim it.
* `MH_NO_HEAP_EXEC` (0x1000000) is **CLEAR**: the image does not request
  hardware NX for the heap.
* `LC_CODE_SIGNATURE` (0x1d) is present on **arm64 only** — the linker's
  ad-hoc signature. Neither slice carries a Developer ID signature, so
  Hardened Runtime and notarisation are absent. That is the external
  dependency already on the frozen list, now measured rather than assumed.

**Linux — `payload.so`, 1,052,904 B, ELF64 `DYN`.** `GNU_STACK` is RW (NX),
`GNU_RELRO` is present, symbols are stripped — and **BIND_NOW is absent**.
`-Wl,-z,now` cannot be used because setuptools' `-Bsymbolic-functions` turns
it into a link failure (measured in §5x). Partial RELRO instead of full is a
documented trade, and it is recorded rather than glossed.

The unsupported rows are stated as such in the matrix instead of omitted:
musl/Alpine (blobs link glibc), a mismatched CPython ABI (the suffix encodes
it; the `native-only` profile has no fallback by construction), mingw (loads,
but CFG is `unavailable` — GNU ld has no such option), and older toolchains
and ARM64 Windows/Linux, which are **not measured** and therefore not
claimed.

### 6j.2 P2: reproducibility is two different answers, and both were measured

The register's assessment said "Reproducible builds — Not yet demonstrated".
That is now measured, and the single-verdict framing was wrong in both
directions. The build has two layers:

**Layer 1 — the transform layer IS reproducible.** Measured on this host,
same tree, `build_pipeline(SRC, seed=424242)` twice:

```
run 1  sha256 b51a2b129103ddd8...  7,528 B
run 2  sha256 b51a2b129103ddd8...  7,528 B
identical: YES
```

`seed=999999` produces different output, so the seed is load-bearing rather
than passing by accident. `NX_BUILD_SEED` reaches this layer by seeding
`random` and patching `secrets` for the duration of the transform, restored
in a `finally`.

**Layer 2 — the shipped artefact is NOT byte-identical, and should not be.**
Two full `build` runs at `NX_BUILD_SEED=424242`:

```
run 1  sha256 f58d0e2bf0b03277...  267,811 B
run 2  sha256 de68859c31144560...  267,818 B
identical: NO
```

The 7-byte delta is **attributed, not hand-waved**: the emitted loader
contains

```python
_nx_name = "%s%s%s" % (prefix, _nx_secrets.token_hex(8), suffix)
_nx_now  = _nx_time.time()
_tb_now  = float(_tb_time.time())
```

— a per-build helper identifier and a clock read drawn at *runtime*, after
the seeded transform has already finished and restored the global patch.
`NX_BUILD_SEED` does not cover them, and covering them would be a security
regression: a loader whose identifiers were predictable from a build seed
would defeat the reason they are minted. `NIXON_REPRODUCIBLE=1` seeds the
**farm driver's** C-transform seed only.

Both layers are pinned in `tests/test_reproducible_build.py` (4 tests), which
also asserts a subtle property that a naive reproducibility test would miss:
a seeded transform must leave `secrets.token_bytes` **unpatched** afterwards.
A leaked patch would make every later nonce, key and challenge drawn in the
process predictable — the failure mode `_patch_secrets` documents at length.

What remains open is a build mode that also pins the loader's runtime draws.
That is recorded as a **design decision with a named security cost** rather
than implemented silently, because the cost is real.

### 6j.3 §5: the coverage limit was a HARNESS defect, not an environment limit

The seventh pass recorded §5 as partial: "libFuzzer reports the sanitizer
coverage runtime is absent from these interpreter builds, so the campaign is
mutation-driven rather than truly coverage-guided". That was wrong, and the
record has to say so plainly because it was a **self-serving explanation of a
bug in my own harness**.

Three defects, all in `scripts/fuzz/nx_fuzz.py`, all found by re-running the
campaign after Atheris 3.1.0 and clang 19's `libclang_rt.fuzzer-x86_64.a`
turned out to be present on this host:

1. **`REPO` was one directory short.** `os.path.dirname` was applied twice
   to `scripts/fuzz/nx_fuzz.py`, yielding `.../scripts` instead of the
   repository root, so `sys.path` never contained the package. Every target
   died with `ModuleNotFoundError: obfuscator` before fuzzing a byte -- and
   libFuzzer reports that as `fuzz target exited`, which reads like a
   finding. Fixed with a third `dirname` and a comment explaining why.
2. **The parsers were imported inside the fuzz body,** i.e. after Atheris
   had already finished instrumenting. The result is the diagnostic that was
   mistaken for the environment limit:

   ```
   WARNING: no interesting inputs were found so far. Is the code instrumented for coverage?
   #8534315  DONE  cov: 1 ft: 1 corp: 2/3b exec/s: 185528
   ```

   8.5 million executions, 46 seconds, **one** new unit and `cov: 1`. The
   harness was fast and measuring nothing. Fixed by importing under
   `atheris.instrument_imports()` in `_load_parsers()`, before `Setup`.
3. **No seed corpus, and a wrong oracle.** With random bytes, `json.loads`
   never succeeds, so neither the pack nor the state target could reach the
   parser. And the pack oracle asserted `stream_join` *never* returns data --
   which a legitimate pack does, so the first seed tripped it immediately
   with `UNINTENDED ACCEPTANCE: stream_join returned data`. An oracle that
   fires on correct behaviour is worse than none; it invites being loosened
   until it detects nothing. Replaced with the real invariant: an acceptance
   is legitimate only for a pack whose structure the builder actually
   produced, and the returned length must equal the declared total.

**Measured after the fixes** (`NX_FUZZ_SECONDS` per target, one run each):

| target | execs | coverage | corpus | new units | findings |
|---|---|---|---|---|---|
| pack | 4,075,415 | cov 61 / ft 185 | 24 / 9,166 B | 614 | none |
| manifest | 454,922 | cov 8 / ft 8 | 3 / 4 B | 6 | none |
| elf | 9,163,257 | cov 15 / ft 22 | 4 / 28 B | 9 | none |
| pe | 2,960,101 | cov 64 / ft 163 | 70 / 29 KB | 547 | none |
| macho | 7,652,368 | cov 27 / ft 52 | 17 / 1,764 B | 79 | none |
| state | 10,173,000 | cov 5 / ft 23 | 10 / 1,428 B | 670 | none |
| **total** | **34,479,063** | — | — | **1,925** | **zero** |

The campaign is now genuinely coverage-guided: libFuzzer grows the corpus
(pack 1 → 24 entries, pe 1 → 70), prints a recommended dictionary of the
16-byte structure tokens it learned, and `cov`/`ft` climb instead of sitting
at 1. A `cov: 1` result is now recognisable as a harness failure rather than
reported as an absence of coverage in the interpreter.

What the seed corpus enables is the important part: mutations now land
*inside* the JSON pack and *inside* the PE/Mach-O headers, which is where the
v2 MAC context, the declared-structure digest and the CFG load-config check
live. That is the register's actual ask — "not simply zero crashes ... prove
that malformed input cannot produce an unintended acceptance or bypass" —
and an oracle that can distinguish a legitimate pack from a mutated one is
the mechanism that makes the claim testable.

### 6j.4 The matrix is now a measured document, not a summary

`docs/security/COMPATIBILITY_MATRIX.md` carries all six properties for all
three shipped rows, the four unsupported rows with how each fails, and the
two-layer reproducibility section. Every number in it came from a blob on
this host or a farm run cited by its ID; none of it is restated from a
register.

### 6j.5 The gate run that failed, and what it found

The first pass-8 gate run was not clean: shard 7 reported one failure. That
is recorded here rather than omitted, because the resolution is the most
useful part of this pass. The failure was NOT treated as flakiness.

Two runs are relevant:

| run | commit | shards | result |
|---|---|---|---|
| `rc-gate-20261122T153655-406189` | `45f6541` | 10 | 9 rc=0, shard 5 FAILED (3 tests) — **my own defect** |
| `rc-gate-20261122T162104-476578` | `d0750b5` | 10 | 9 rc=0, shard 7 FAILED (1 test) — a real race |
| `rc-gate-20261122T171336-572239` | `a0ea66a` | 10 | **10/10 rc=0** |
**Failure 1 — the generated facade (my defect, caught by the gate).**
Adding `checked_url` to `obfuscator/core/pipeline.py` put the generated
`obfuscator/core/__init__.py` out of date. Three tests assert that the facade
exposes exactly the star-import surface and resolves each name to the same
object, and they failed:

```
test_the_facade_exposes_the_same_names                 FAILED
test_the_facade_resolves_each_name_to_the_same_object   FAILED
test_the_facade_file_is_generated_and_up_to_date        FAILED
```

Fixed by running the project's own generator
(`scripts/lint/generate_core_facade.py`, 325 names) and committing the
result. A hand-maintained re-export list would have silently omitted the
guard, and a caller importing it from `obfuscator.core` would have got an
ImportError only on the path that needs it.

**Failure 2 — two real races (both silent, both security-relevant).**
Reproducing the shard-7 failure under load did not confirm "flaky test": it
found two defects that each returned `None` on a path a caller cannot
distinguish from a legitimate negative answer.

*Remote-unlock registration raced its own request.* `connect()` sent the
register message and closed the socket **without reading the acknowledgement**.
The server dispatches each connection to a daemon thread, so the client could
open its `request_token` connection before the registration had been applied
to `_client_secrets`; `validate_request` then found no secret and
`unlock_fragment` returned `None`. Measured: 24 concurrent instances of
`TestRemoteUnlockIntegration` produced roughly three failures per batch.
`connect()` now waits for the sealed acknowledgement and requires
`status == "ok"`, with a bounded retry; a refused registration raises instead
of leaving an unregistered client behind.

*Watermark extraction silently discarded shares.* `extract_multiprocess` did
one `q.get(timeout=5)` per share inside `except Exception: pass`. A child
process that had not been scheduled when the timeout fired meant its share
was **dropped**; `extract_full` then reconstructed from a short list and
returned `None`. Under 40 concurrent test processes each forking four
children this happened about one run in twenty. Collection now retries with a
15 s budget, and a **partial** set raises — half a share set must never be
treated as a whole one. `None` is reserved for "every share was missing",
which is a real absence.

Measured after both fixes: 40 concurrent runs of
`tests/test_distributed_integration.py`, **0 failures** (was 2/40).

### 6j.6 The authoritative pass-8 gate record

```
run_id:        rc-gate-20261122T171336-572239
commit:        a0ea66a69df9145538f18dd811285b42e12f2116
tree:          2f59a4cdab6ea85bcf08437d7e30d10e01023b27
dirty_files:   0
identity_stable: true
shard_files_total: 444          (derived from tests/** and asserted complete)
shards_with_failures: 0
passed:        30,286
skipped:       9
collected:     30,295          (30,286 + 9 = 30,295)
```

Per-shard, every one `rc=0` with the commit and tree above and `dirty=0`
recorded independently on its own line: 542, 573, 450, 644, 555, 834, 597,
25,059, 538, and the final shard. This is the same evidence shape the
fifth-round review asked for — each shard carries its own commit, tree,
dirty count, run id and exit code, so the aggregate is reproducible from the
record rather than asserted.

Two distinctions stay explicit, as required:

* **source identity** — all ten shards tested this one revision, and the
  identity was re-read at the end (`identity_stable: true`);
* **reproducible builds** — separate and answered in 6j.2: the transform
  layer is byte-identical at a pinned seed, the shipped artefact is not by
  design.

And one caveat on the aggregate: 30,295 is the count for THIS tree, which now
includes `tests/test_fuzz_harness.py` (6 tests) and
`tests/test_reproducible_build.py` (4 tests). The earlier 29,938 remains in
the record as belonging to its own shard composition; see 6e.1.

## 6k. Ninth pass: the acceptance matrix was YAML, and the fingerprint was not signed

Two register rows looked "in progress" and one of them turned out to have
never been executed at all.

### 6k.1 The release acceptance matrix existed only inside a workflow

`.github/workflows/release.yml` carries a substantial acceptance matrix as an
inline Python heredoc: build a signed candidate, then probe that a correct
pin accepts while a missing pin, wrong pin, stripped provenance signature and
modified artifact are all refused. It is good work, and it had two problems:

* it only ever ran on GitHub. The derived shard list is
  `tests/**/*.py`, so no local gate run has ever executed it — the release
  path's own logic was outside the gate that is supposed to prove it;
* the probe payload's docstring, and
  `.mimosa/security-policy.json`'s audited-exception entry, both cite
  `tests/test_release_acceptance.py`. **That file has never existed in this
  repository** (`git log --all -- tests/test_release_acceptance.py` returns
  nothing). Two records pointed at an artefact that was not there.

Fixed by writing the module for real: `tests/test_release_acceptance.py`
(6 tests), in the derived shard set, so the gate runs it on every invocation.
It builds through the project's own pipeline and attacks THOSE bytes, rather
than replaying the YAML against fixtures.

### 6k.2 DEFECT: `signature.key_fingerprint` was outside the signature

Found while writing the incident-response runbook, because §0 triage depends
on the claim being true. `sign_manifest` computed its signed body as

```python
body = {k: v for k, v in manifest.items()
        if k not in ("signature", "signed")}
```

and stored the fingerprint at `signature.key_fingerprint`. The whole
`signature` object is excluded, so the fingerprint was **not covered by the
signature** — while the docstring said it was ("covered by the signature, so
it cannot be edited without breaking the signature it identifies").

Measured before the fix:

```
expected fp: 830051885477bb61
recorded fp: 830051885477bb61      <- correct
verify ok: True
edit signature.key_fingerprint -> "0000000000000000"
verify after fp edit: True         <- STILL ACCEPTED
```

That is not a documentation nit. The fingerprint is the single field
`docs/security/INCIDENT_RESPONSE.md` §0 uses to answer "which artefacts did
the compromised key sign?". An attacker who can write a manifest could
re-attribute an artefact signed by a compromised key to a clean one and
escape the affected set entirely — inverting the one query the field exists
to serve.

Fixed by binding it at TOP LEVEL as `signed_key_fingerprint`, set BEFORE
signing so it is inside the payload, with the nested copy retained for
existing readers, and `verify_manifest` now refuses a manifest whose two
copies disagree. Measured after:

```
verify clean:                                   True
edit nested signature.key_fingerprint:          False  (fingerprint mismatch)
edit top-level signed_key_fingerprint:          False  (signature invalid)
```

Both tampering directions are pinned as a regression test:
`test_the_signed_fingerprint_cannot_be_re_attributed`.

### 6k.3 The incident-response row is now a runbook with executable checks

The register's P2 row asks for operational procedures for six scenarios.
`docs/security/INCIDENT_RESPONSE.md` states each one, marks the human steps
`[operator]` rather than simulating them, and — because a procedure document
rots — `tests/test_incident_response.py` (13 tests) enforces every step that
can be checked in code:

| runbook section | enforced by |
|---|---|
| §0 triage from the artefact alone | fingerprint is signed and matches the key |
| §1 key compromise / revocation | retired key refused under new pin; **and the offline limit asserted as a measurement** |
| §2 emergency pin replacement | missing pin refuses under release policy; explicit key cannot override the pin |
| §3 manifest-key rotation | old manifests stop verifying under the new pin |
| §4 artefact retirement | lowering `protection_level` breaks the signature; forged mark reads 0; downgrade raises |
| §5 dependency discovery | lock digest distinguishes dependency sets |
| §6 revocation mechanism | asserts NO network call or revocation-list exists in the verification path |

The last one is deliberate: the document claims revocation is pin
replacement because verification is offline. If someone later adds a network
fetch to `build_manifest`, the document becomes false, so a test fails.

A final test asserts the runbook still names the variables and fields the
implementation depends on, and still carries its "NOT covered here" section
naming Authenticode, Apple Developer ID and the missing independent
cryptographic review — so the document cannot quietly start implying coverage
it does not have.

### 6k.4 The authoritative pass-9 gate record

```
run_id:        rc-gate-20261122T195557-810977
commit:        8b4cb91503e46637295e0046d833b80f3cd42173
tree:          fe3e73cd6343fc0702265adb5247cc2111c7b54d
dirty_files:   0
identity_stable: true
shard_files_total: 446          (444 + the two new modules)
shards_with_failures: 0
passed:        30,305
skipped:       9
collected:     30,314          (30,305 + 9 = 30,314)
```

Per-shard, all `rc=0` with this commit and tree and `dirty=0` on every line:
543+1s, 576, 442+1s, 675+1s, 487+1s, 804+3s, 735, 25,020+1s, and shards 9-10.

The aggregate rose from 30,286 to 30,305 — **exactly the 19 tests in the two
new modules**, which is the independent confirmation that they ran rather
than merely being present. Verified again by name on the committed tree:
`tests/test_release_acceptance.py` (6) plus `tests/test_incident_response.py`
(13) = 19 passed, 0 skipped.

Shard assignment re-read from `gate/shards/`: `test_incident_response.py` is
in shard 5 and `test_release_acceptance.py` in shard 8, both of which returned
`rc=0`. This matters because the earlier failure mode in this project was a
suite file that existed but was assigned to no shard at all; the derivation
assertion (`shard_files_total` plus a refusal on any unassigned file) is what
makes "present in the tree" and "ran in the gate" the same claim.

### 6k.5 What remains, and why it is not being closed here

The register's remaining rows are external or administrative, and this pass
does not pretend otherwise:

| row | why it cannot close in this repository |
|---|---|
| independent cryptographic review of pack-v2 | needs a cryptographer; passing the tamper matrix shows specific attacks were rejected, not that the construction is sound |
| independent payload semantic review | needs an analyst given the artefact and a budget, with the source withheld |
| independent Mimosa baseline review | our own sampling is not independent verification |
| Authenticode / Apple Developer ID | purchased identities and a CA relationship |
| Windows strict shadow-stack hardware | needs a host with CET shadow stack enabled |
| production environment + protected release | a GitHub environment with required reviewers, and a real release decision |

Each is named in `docs/security/INCIDENT_RESPONSE.md` under "NOT covered
here", so the documentation and the register agree about what is unproven.

## 6l. Tenth pass: the cryptographic review is commissioned, not performed

The register's highest-priority external row is the independent cryptographic
review of the pack-v2 construction. A maintainer cannot close it — an
independent review requires a reviewer. What CAN be closed is the
**commissioning**: a package complete enough that a cryptographer can start
without interviewing anyone, and honest enough that the review is not spent
rediscovering weaknesses we already know about.

`docs/security/CRYPTO_REVIEW_PACKAGE.md` is that package. It states in its
first paragraph that **the review has not been performed**, and it is
structured so a reviewer can attack it:

* the full construction written out precisely (§3): domain-separated key
  derivation, the 28-byte authenticated context, the seal and open equations,
  nonce generation, and the separate unkeyed state digest;
* the threat model, including what is explicitly NOT claimed (§1) — side
  channels, post-reassembly memory, and key acquisition by other means are
  out of scope, stated rather than implied;
* **seven weaknesses named by the maintainers** (§5) so the reviewer starts
  from our own list rather than paying to rediscover it;
* eight specific questions (§6), including the one that matters most: whether
  MAC-then-encrypt over a SHA-256 counter-mode keystream is acceptable for
  this threat model, or whether it must become a standardised AEAD — and if
  so, whether a small audited native dependency is operationally acceptable
  given the loader must run without a compiler;
* reproduction commands (§8) for every number in it.

### 6l.1 The weaknesses, named plainly

The package's §5 is the part that makes it worth sending. In summary:

1. **MAC-then-encrypt, not an AEAD.** No reduction to a named security
   notion. This is the single most important thing to review.
2. **The stream cipher is bespoke** — SHA-256 in counter mode over
   `key ‖ nonce ‖ ctr8`. "Reasonable looking" is not a security argument.
3. **`key_hint` is an unkeyed oracle.** Measured: the pack carries
   `SHA256(K)[:16]` in the clear, checked BEFORE the MACs. A reviewer should
   assess whether that materially helps an offline attacker given the session
   key is derived partly from licence/HWID material the holder may know.
4. **No nonce-reuse protection at load.** Key derivation includes the index,
   so cross-section reuse is harmless, but same-section reuse across two
   packs under one key would XOR two keystreams. Random nonces per build make
   this improbable, not impossible.
5. **Section length is implicit**, bound only indirectly via `total` and the
   final join check.
6. **`salt` is unkeyed and unverified** — used only in the state digest,
   which is by design not a security boundary.
7. **The v1 legacy path remains**, with a single key for both roles and no
   metadata binding.

### 6l.2 What was measured while writing it

Three claims in the package were verified rather than asserted, because a
review package that is wrong about its own code wastes the reviewer's time:

* **downgrade resistance** — editing `v` from 2 to 1, or deleting it, makes
  `stream_join` raise `section 0 integrity failure`. The version IS inside
  the tag context. (Control: the unmodified pack joins to the right length,
  so the refusal is about the edit.)
* **verification precedes plaintext use** — in `stream_join` the
  `joined.extend(part)` at line 80 is strictly after the `compare_digest` at
  line 77, and the three emitted loader templates have the same ordering. No
  plaintext is accumulated or sunk before its section's tag verifies.
* **every tag comparison is constant-time** — four sites, all
  `hmac.compare_digest`, and no bare `==` comparison of a tag anywhere.

`tests/test_crypto_review_package.py` (12 tests) pins the package to the code:
the documented domains are the implemented ones, the documented context is
the implemented 28-byte layout, the role-separated keys really are
independent and really do depend on index and nonce, the composition ordering
claim holds, `key_hint` really is `SHA256(K)[:16]`, and the package still
carries its NOT PERFORMED banner, its non-claims section and its eight
questions. If the construction changes shape, the package stops matching and
a test fails — the right outcome, because a review package describing code
that no longer exists would attach a reviewer's findings to the wrong
construction.

Explicitly: **no test in that module asserts cryptographic soundness.** That
is the reviewer's judgement. A green suite there must never be read as one.

### 6l.3 Status of the row

The register row stays OPEN. What changed is that it is now *commissionable*:
a named reviewer can be handed one document that specifies the construction,
lists the known weaknesses, asks the right questions, and lets them reproduce
every measurement. When findings come back, they join this register alongside
every other measured item rather than arriving as an unstructured report.

## 6m. Eleventh pass: the reverse-engineering evaluation is commissionable too

The same treatment for the register's other external engineering row. Its
§6 specification said *what* to measure ("give an independent analyst the
artefact, no source, fixed budget, semantic-recovery objectives, repeat
against an unobfuscated control") but provided no subject, no control arm and
no scoring key — so two analysts would have produced two incomparable
reports, and "did the obfuscation help?" would have remained unanswerable.

`docs/security/RE_EVALUATION_PROTOCOL.md` closes the commissioning gap:

* **two arms** from the same source — the obfuscated build and an
  obfuscation-disabled control. The control is the analyst's cost floor;
  without it a 22-hour result is uninterpretable, because we cannot know
  whether the 22 hours are the protection or the analyst.
* **a finite, checkable subject** (`tests/fixtures/re_subject.py`, 60 lines,
  integer arithmetic, `sys` the only import). Chosen so an analyst either
  recovers a specific formula or does not, and the score is not a matter of
  impression.
* **a scoring key** with four objectives — entry function, numeric algorithm,
  string surface, integrity-check semantics — each 0/1/2, marked
  *DO NOT GIVE THIS SECTION TO THE ANALYST*.
* **behavioural equivalence as a gate that outranks every score**: if the two
  arms disagree on output, that is a build-correctness defect and the scores
  do not matter.
* **four prohibitions on the maintainers**, including "must not report a
  favourable arm alone".
* **five stated limitations**, including that one 60-line subject cannot
  characterise a large codebase and that a good score is not a certification.

### 6m.1 The scoring key had a hole, found by attacking my own key

`tests/test_re_protocol.py` (11 tests) pins the answer key to the subject, on
the reasoning that if the subject drifts and the key does not, the protocol
silently grades a correct analyst as failing — an error invisible to both
parties.

Writing that check, the FIRST version of the case list was wrong in a way
that matters. The key was compared against the subject over eight inputs
including `[50000]` and `[100000]`. Perturbing the key and re-running showed:

```
correct    matches=True   OK
decay=6    matches=False  OK
thr=49999  matches=False  OK
thr=50001  matches=True   GAP     <- the key was NOT pinning the boundary
```

With no input landing above 50000 but below 50002, a threshold of 50001
matched every case. The list now includes `[50001]`, and all three
perturbations diverge while the correct key matches. **A scoring key that
cannot detect a wrong constant is worse than no key**, because it would have
graded analysts against a threshold the product does not use.

The module also asserts the protocol keeps its `NOT RUN` banner, its
withhold marker, the both-arms-and-delta requirement, its limitations
section, and that the subject stays under 80 lines importing nothing but
`sys` — since the 40-hour budget assumes that size.

Nothing in it asserts anything about obfuscation strength. That is the
analyst's measurement, and the row stays OPEN.

### 6m.2 Both external engineering rows are now commissioned

| register row | status after this pass |
|---|---|
| P1 independent cryptographic review | **commissioned** — `CRYPTO_REVIEW_PACKAGE.md`, review NOT performed |
| P1 independent payload semantic review | **commissioned** — `RE_EVALUATION_PROTOCOL.md`, evaluation NOT run |
| P1 independent Mimosa baseline review | not ours to commission; our sampling is not verification |
| P1 Authenticode / Apple Developer ID | external purchase |
| P1 Windows strict shadow-stack | external hardware |
| P0 production environment + release | administrator action |

Two rows moved from "blocked" to "ready to hand over". That is the most a
repository can do for a row that by definition requires someone else, and it
is worth being precise about: **neither review has happened.** A package that
looks like a review would be worse than an obvious gap, which is why both
documents carry their NOT PERFORMED / NOT RUN marker in the first paragraph
and a test asserts the marker survives.

### 6m.3 The third package: the Mimosa baseline review

With all three external engineering rows handled the same way, the Mimosa
baseline is the last of them. `docs/security/MIMOSA_REVIEW_PACKAGE.md` states
in its first paragraph that the review is NOT PERFORMED, then hands a reviewer
the four scan records (1,470/919, 1,482/921, 1,495/916), the three-class
explanation restated as a claim to be checked, **five known flaws in the
maintainers' own method**, the one item the baseline already flags as open,
nine numbered questions, and the command to reproduce every number.

Two findings came out of assembling it, and both cut against the baseline
rather than for it:

**A fourth high class the baseline never enumerates.** The fresh scan reports
`core/transforms.py:2507` as `命令白名单策略违反` (command allowlist policy
violation) — a class absent from the three-class table. The baseline's own
reproduction rule says "a new high-severity class that is not one of the three
above is a regression", so by its own rule this scan should have been flagged.
Reading the line shows it is a COMMENT (`#   exec("x = 5") in the enclosing
scope ...`), i.e. the same prose false-positive class already documented for
`section_split.py:30`. The enumeration was therefore written from a sample
rather than derived from the log — the completion criterion the package exists
to expose.

**Counting by eye fails too, and the failure is one line long to demonstrate.**
The scan summary says **916 高危**. A naive `grep -c` over the same log returns
**917**, because the summary line itself contains the word. Neither number can
be trusted as drawn: the per-file list and the summary are generated
separately, and a pattern match can land on either. This is recorded in the
package as §4.3a, with the recommendation that published counts be derived
from structured scan output rather than rendered text — and it is why question
9 asks the reviewer to require exactly that.

### 6m.4 One claim in the package was verified rather than asserted

The package distinguishes `sources.py`'s seven request findings from
`pipeline.py`'s four, because that distinction is the whole basis for saying
they have different threat models: the former are **emitted into the
artefact**, the latter are live build-host clients.

Measured with AST rather than assumed: all seven cited `sources.py` lines fall
inside string constants longer than 200 characters, and all four
`pipeline.py` call sites fall outside any such span. A negative control
confirms the check discriminates (2141 inside → True, 1454 outside → False),
so the assertion is not passing vacuously.

`tests/test_mimosa_review_package.py` (10 tests) pins that and the rest of the
package's checkable content: the cited comment lines are still comments, the
template-membership claim holds in both directions, `checked_url` still guards
four sites, and the package keeps its NOT PERFORMED banner, its non-claims
section, its nine questions and the 916-vs-917 caveat. **It asserts nothing
about whether any finding is a true positive** — that adjudication is the
reviewer's, and a green suite here must never be read as clearance.

### 6m.5 A note on the tooling outage

Mid-pass, every Write/Edit/Bash call began returning
`Mimosa 未能完整传递安全检查结果，本次操作已阻止` — including a bare `echo ok`
and a one-byte write to `/tmp`. Reading the hook's own stderr showed why:

```
Error: Mimosa 保护包完整性校验失败：manifest 文件清单不匹配
```

The plugin's self-check lists every file under its `payload/` tree and
compares that listing against its signed manifest. A session-state file
(`.mimosa/hook-state/sess_*.json`, 218 bytes) had been written into the plugin
install directory, so the actual file count was 37 against 36 declared and the
integrity check refused. All 35 manifest-listed files hashed correctly; the
failure was one **extra** file, not a modified one.

That is a contaminated installation, not a verdict on this repository — and
not something to route around. Deleting the stray state file restored the hook
and the work continued. Recorded here because the outage cost time and the
diagnosis is the useful part: the error message alone says "result not passed",
while the hook's stderr names the file-list mismatch.

## 6n. Twelfth pass: the review packages' instructions did not work

Three commissioning packages were written and then declared ready. Their
reproduction instructions had never been executed, so they were executed, and
two of the three were wrong.

### 6n.1 DEFECT: the documented build command failed immediately

`RE_EVALUATION_PROTOCOL.md` §2.1 told a reviewer to run

```
python3 -m obfuscator.core.pipeline build subject.py --opt-level 0 --skip-cloud
```

from a scratch directory. That dies:

```
ModuleNotFoundError: No module named 'obfuscator'
```

No `PYTHONPATH`, and the module is only importable from the checkout root. A
reviewer would have spent their first hour debugging this project's import
layout instead of its obfuscation.

### 6n.2 DEFECT: and the command wrote into the tree under review

Worse than the import failure, because it is silent. There is no `--output`
flag: the build targets the **payload's own directory**. Running the documented
command therefore wrote into the repository itself. Measured:

```
tests/fixtures/re_subject_Nixon-Enc.report.json
tests/fixtures/re_subject_protected_Packed.py
tests/fixtures/re_subject_protected_dbg_Packed.py
```

Those are artefacts belonging to no commit, produced by a command in a package
whose stated purpose is to hand a reviewer a trustworthy pair of builds. A
package that dirties the tree it asks someone to evaluate is not evidence, and
the build outputs it describes had never been verified to exist.

### 6n.3 Both corrected, and the correction was then run

```
mkdir -p /tmp/re-eval && cd /tmp/re-eval
cp <checkout>/tests/fixtures/re_subject.py ./subject.py
PYTHONPATH=<checkout> python3 -m obfuscator.core.pipeline build subject.py \
    --opt-level 0 --skip-cloud                       # control arm
PYTHONPATH=<checkout> python3 -m obfuscator.core.pipeline build subject.py \
    --skip-cloud --package native --section-count 4 --watermark NX-RE-EVAL
```

Measured result: both arms built (`signed=False`), both ran to exit 0, both
printed the identical two lines — `RE-SUBJECT-OUTCOME 38664 rejected` then
`audit:rejected` — and `git status --porcelain` in the checkout stayed empty.

So §5's equivalence gate is now **known to pass on this tree** rather than
assumed to. That distinction is the whole point: it is the gate the protocol
says outranks every score, and it had never been exercised.

A third gap: the protocol described the control arm as "obfuscation disabled"
and never named a flag. `--opt-level 0` is the mechanism that exists; it is now
stated, and a test asserts the flag is present in the build parser.

### 6n.4 A third instruction checked, on the crypto package

§8 tells the reviewer to call `split_sealed` and read the returned dict.
Verified: the pack carries the documented keys, `v == 2`, `count == 4`, and a
16-byte nonce as §3.5 claims. That one was already correct.

### 6n.5 What this pass did NOT do

It did not perform any of the three reviews. `SECURITY.md` states plainly:

> No dedicated security contact or bug-bounty is configured for this
> repository — this paragraph is the whole process until one is.

There is no channel to hand a package to, and inventing "independent" findings
would be fabrication dressed as evidence — the exact failure mode this project
has spent several passes removing. All three rows stay OPEN, all three packages
keep their `NOT PERFORMED` / `NOT RUN` banners, and
`tests/test_review_packages_executable.py` asserts that none of them ever
claims an independent review occurred.

What changed is narrower and real: a reviewer can now start without hitting a
broken command, and the pair of builds they are asked to analyse has been
demonstrated to exist and to agree.

### 6n.6 Pass-13 gate

```
run_id:            rc-gate-20261122T232625-1148417
commit:            40441842bc0f0197c9434882a8090a5030b5cdd1
tree:              1766eddc798fb9abd91c80319c74e066efa1de9a
dirty_files:       0
identity_stable:   true
shard_files_total: 450
shards_with_failures: 0
passed 30,354 / skipped 9 / collected 30,363
```

The aggregate rose 30,338 → 30,354, exactly the 16 tests in the new module,
which is the independent confirmation they ran; the module is assigned to
shard 8 (`rc=0`, re-read from `gate/shards/`).









## 6o. Thirteenth pass: the intake channel, and the one decision that is not mine

The three external-review rows are blocked on a single missing thing: there is
no route for a reviewer to return findings through. I cannot name a security
contact or engage a vendor — that needs the repository owner's identity,
procurement authority and money. Inventing an address would be worse than the
gap, because a plausible-looking `security@` nobody monitors sends real
disclosures into a void.

So this pass did the part that is mine and left exactly one decision to the
owner.

### 6o.1 The channel is named, and its current state is dated

`SECURITY.md` previously said "No dedicated security contact or bug-bounty is
configured for this repository" — true, but it left a reader unable to tell
whether that was still the case and gave no path to fixing it. It now names
GitHub private vulnerability reporting as the intended channel, and records:

* the exact enabling command, so turning it on is one copy-paste;
* the CURRENT state with a verification date — **NOT ENABLED**, checked
  2026-11-23 against the live repository (setting absent, repo public,
  Dependabot and secret scanning and push protection already on);
* why the three review rows stay open because of it;
* an explicit sentence that the absent address is deliberate, and that
  "not configured" is not "reports unwelcome".

The setting itself was NOT changed. The repository is public and this is an
owner-level outward-facing change; the session asked and received no answer, so
the default was to leave it alone rather than assume consent for something
irreversible-in-perception. It is now a documented two-minute action instead of
an unstated precondition.

### 6o.2 The findings-intake format

The instruction was to "record the returned findings as new register rows".
`docs/security/REVIEW_FINDINGS_INTAKE.md` is the mechanism: a fifteen-field row
(package, reviewer, received, severity, claim, evidence, reproducible, affects,
maintainer-response, resolution, …) plus four rules that keep it honest:

1. quote the reviewer verbatim — paraphrase loses the difference between "the
   tag is not bound to the version" and "the tag seems weakly bound";
2. never resolve without a measurement — the row cites the commit and the test,
   or states plainly that nothing changed and why;
3. a disputed finding **stays in the register**, which is the entire point;
4. out-of-scope findings are recorded as out-of-scope with the `SECURITY.md`
   paragraph that excludes them, not as "the reviewer was wrong".

It also says there is no parser on purpose: reports arrive as prose and differ
in shape, and forcing them into a form biases what gets reported. The format
constrains the maintainers' response, not the reviewer's report — stated in the
document, addressed to the reviewer.

The document's first line is that **no findings have been returned**, so it
cannot be mistaken for a record of one.

### 6o.3 What guards all of it

`tests/test_review_channel.py` (13 tests) keeps the claims true: the status
carries a date, the enabling command is present, each package still carries its
own `NOT PERFORMED` / `NOT RUN` banner so SECURITY.md's table cannot misreport
it, and no document in the set ever claims a review occurred. One test asserts
SECURITY.md contains **no email address at all**; a negative control confirms
the detector fires on `security@example.com` and not on prose. That is the
check that stops the next pass from "helpfully" inventing a contact.

### 6o.4 Pass-14 gate

```
run_id:            rc-gate-20261123T001803-1377335
commit:            431ee1f63e1a93dc3f4a002bbc5a64d02a88d461
tree:              621e33cbc887515c412683e6b75419f333c6f39b
dirty_files:       0
identity_stable:   true
shard_files_total: 451
shards_with_failures: 0
passed 30,367 / skipped 9 / collected 30,376
```

The aggregate rose 30,354 → 30,367, exactly the 13 tests in the new module,
which is the independent confirmation they ran; the module is assigned to
shard 8 (`rc=0`, re-read from `gate/shards/`).

### 6o.5 State of the register

| row | state |
|---|---|
| every engineering row | closed, measured, gate-verified |
| three external reviews | commissioned; packages verified executable; intake format defined; **channel named but not enabled** |
| Authenticode / Developer ID | blocked: purchase |
| Windows strict shadow-stack | blocked: hardware |
| production release | blocked: administrator decision |

The honest summary is that the repository side of every external row is now
complete — specification, known weaknesses, questions, reproduction commands
that work, a filing format, and a named intake route with its state dated. What
remains is one settings toggle and several people. Neither is something a
maintainer can fabricate.

## 6p. Fourteenth pass: the intake channel is live

The register's three external-review rows were blocked on one thing — no route
for a reviewer to return findings. That route now exists.

### 6p.1 Enabled, and verified against the endpoint that actually reports it

GitHub private vulnerability reporting is **ENABLED** on
`Nixon-H/adversarial-obfuscator`, verified three times for stability:

```
gh api repos/Nixon-H/adversarial-obfuscator/private-vulnerability-reporting
-> {"enabled": true}   (x3)
```

The advisories API is readable and holds zero advisories — the expected state
for a channel that is open and has received nothing.

### 6p.2 An API trap that nearly produced a false negative

The first attempt used the command written in `SECURITY.md` itself:

```
gh api -X PATCH repos/Nixon-H/adversarial-obfuscator \
    -f 'security_and_analysis[private_vulnerability_reporting][status]=enabled'
```

It returned **HTTP 200** with the full repository object — and the setting did
not change. `GET /repos/{owner}/{repo}` does not list
`private_vulnerability_reporting` inside `security_and_analysis` on this
repository at all, and the PATCH is silently ignored.

Both readings of that are wrong: "the PATCH returned 200, so it worked" and
"the field is absent, so it is unsupported". The authoritative check is the
dedicated endpoint above. `SECURITY.md` now carries the trap next to the
working command, so the next person re-verifying does not have to rediscover
it — and one of the tests asserts that warning stays.

### 6p.3 What the document now says

* the channel is **ENABLED**, with a verification date;
* the advisory URL, so a reporter has a clickable destination:
  <https://github.com/Nixon-H/adversarial-obfuscator/security/advisories/new>;
* the dedicated verification endpoint, and the 200-but-inert PATCH beside it;
* the one-line `DELETE` that reverses the setting, because a documented
  setting should be documented as reversible;
* a plain statement that a report is welcome. A test caught that I dropped
  this sentence while rewriting the section — which is precisely what that
  test is for, and worth recording as a case where the suite caught the
  maintainer rather than the code.

No email address appears, still enforced by a test. The advisories channel is
monitored by the repository's own notification settings, so no address is
needed and none is invented.

### 6p.4 Pass-15 gate

```
run_id:            rc-gate-20261123T010331-1450120
commit:            71eff21081785eb4bf588e7dd8542d0e4c279d79
tree:              0a558473537511176694294e5be616bf28d88def
dirty_files:       0
identity_stable:   true
shard_files_total: 451
shards_with_failures: 0
passed 30,369 / skipped 9 / collected 30,378
```

The aggregate rose 30,367 → 30,369, the two added tests in
`test_review_channel.py` (13 → 15). The channel was re-queried after the gate
and still returns `{"enabled": true}`, so the settings change is stable and
not something the API reported optimistically.

### 6p.5 What is now genuinely different, and what is not

Different: a reviewer can return findings. The three packages are
specified, their reproduction commands execute, a fifteen-field filing format
exists, and there is a live private channel to send results through.

Not different: **no review has happened.** All three packages still carry
`NOT PERFORMED` / `NOT RUN`, and the register rows stay open until someone
reads them. The remaining blockers are people and purchases — a cryptographer,
an analyst, an independent Mimosa reviewer, an Authenticode certificate, an
Apple Developer ID, Windows shadow-stack hardware, and a production
environment with required reviewers. None of those can be manufactured by a
maintainer, and this record does not pretend otherwise.

## 6q. Fifteenth pass: a standalone bundle, and a category error avoided

The instruction was to hand the crypto package to a cryptographer "through the
now-live channel at `security/advisories/new`". That is a category error worth
recording, because acting on it would have produced a misleading artefact
rather than a review.

`security/advisories/new` is a **vulnerability disclosure** mechanism. An
advisory titled "please review my cryptography" is not a disclosure; a
maintainer opening one on their own repository to solicit work misuses the
channel, and the advisory has no recipient until some human chooses to read it.
No tool summons a reviewer. Filing it would have created the appearance of an
engagement with none of the substance — the exact pattern this project has
spent several passes removing.

So the pass did the part that is real: it produced the artefact that would be
sent.

### 6q.1 The standalone bundle

`docs/security/CRYPTO_REVIEW_BUNDLE_STANDALONE.md` is written for a reviewer
who will **not clone the repository**. The existing package assumes a checkout
and points at source files; a cryptographer engaged for two hours needs the
construction in front of them immediately. The bundle carries:

* the construction written out completely — key derivation with domain
  separation, the 28-byte authenticated context, seal and open equations, the
  SHA-256 counter-mode keystream, and the separate unkeyed structural digest;
* the **seven weaknesses** the maintainers already know about;
* eight questions, led by whether MAC-then-encrypt over a bespoke keystream is
  acceptable here or must become a standardised AEAD;
* an explicit "what we are not claiming" section — no soundness claim, no
  preference over a standard AEAD, and a scoped list of what is in play;
* how to verify our measurements, with the expected test count;
* how to return findings.

### 6q.2 A third broken reproduction command, found by running it

The crypto package's commands had never been executed. Measured:

```
python3 -m obfuscator.core.pipeline build --help
-> ModuleNotFoundError: No module named 'obfuscator'
```

The same missing `PYTHONPATH` the RE protocol had — third instance of the same
defect class across the packages. And a second, different one:

```
python3 -m pytest -q ...
-> No module named pytest.__main__; 'pytest' is a package and cannot be
   directly executed
```

pytest is installed as a library on this host, not a runnable module. The
project's own release gate already uses the `console_main()` form; the package
now matches it and says why, so a reviewer on a similar host is not left
guessing.

After the fix the documented command was **run**: `40 passed`, confirming §4's
tamper-matrix count against the suite it names. The package now tells the
reviewer that a different number means the table is stale rather than leaving
them to wonder.

### 6q.3 What the tests pin, and what they deliberately do not

`tests/test_crypto_bundle_standalone.py` (15 tests) pins the bundle to the
implementation, because a bundle that misdescribes the construction sends the
review at a design that does not exist and its findings attach to nothing:

* the documented domains reproduce `_section_keys_v2` exactly;
* the documented 28-byte context reproduces `_mac_context_v2` field for field;
* the documented keystream reproduces `_keystream` byte for byte;
* the tag is 32 bytes plus plaintext; the digest schema matches;
* verification still precedes plaintext use; `key_hint` really is
  `SHA256(K)[:16]`;
* all seven weaknesses stay listed.

One test failed on its first run for a good reason: a plain substring check for
"is secure" flagged the sentence "we are **not** claiming it is secure". The
check now examines each occurrence for a negation in the preceding clause.
Negative control: a denial reads False, a real claim reads True.

**No test asserts cryptographic soundness.** A green suite means the
description is accurate, not that the design is good — stated in the module
docstring so a future reader cannot mistake one for the other.

### 6q.4 Pass-16 gate

```
run_id:            rc-gate-20261123T014740-1521236
commit:            fdc3d4180b3fcf2939a79d57e1c855c4d2d300f8
tree:              155d85c054762d5646c318bb13f69274272901d5
dirty_files:       0
identity_stable:   true
shard_files_total: 452
shards_with_failures: 0
passed 30,384 / skipped 9 / collected 30,393
```

The aggregate rose 30,369 → 30,384, exactly the 15 tests in the new module,
which is the independent confirmation they ran; the module is assigned to
shard 2 (`rc=0`, re-read from `gate/shards/`).

### 6q.5 The boundary, stated once more

Three packages are now specified, executable, independently pinned to their
implementations, accompanied by a live private intake channel, and — for the
cryptographic one — packaged for a reviewer with no repository access.

**No review has happened.** All three still carry `NOT PERFORMED` / `NOT RUN`.
The distance from here to a reviewed release is: a cryptographer, an analyst,
an independent Mimosa reviewer, an Authenticode certificate, an Apple Developer
ID, Windows shadow-stack hardware, and a production environment with required
reviewers. Every one of those is a person, a purchase, or an administrator
decision. None can be produced by writing more documents, and producing more
documents in place of them would be the failure this register exists to catch.

## 6r. Sixteenth pass: a real defect found by attacking our own stated weakness

No cryptographer could be engaged — there is no mail transport on this host
(exim4 installed but inactive, no configuration) and no reviewer address exists
in the repository or in the owner's public GitHub profile. Rather than produce a
sixth document describing that gap, the pass attacked the weaknesses
`CRYPTO_REVIEW_BUNDLE_STANDALONE.md` §8 already lists. One of them is
exploitable.

### 6r.1 MIMOSA-INTAKE-001: cross-pack section substitution is accepted

Two packs built with the same session key and the same total length are
interchangeable section-by-section. Replace sections 0–1 of pack A with those
of pack B, recompute the **unkeyed** structural digest, and the join succeeds
with the MAC verifying for every substituted section:

```
joined  : b'BBBBBBBBBBBBBBBBAAAAAAAAAAAAAAAA'
expected: b'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
```

Cause: pack-v2's authenticated context is

```
ctx_i = u32be(v) ‖ u32be(i) ‖ u32be(total) ‖ N_i
```

which binds the version, the index, the total and the per-section nonce — but
**not which pack the section belongs to**. Under one key with equal totals,
section *i* of one pack is indistinguishable from section *i* of another.

Scope, measured rather than assumed:

* requires the session key; this is not forgery without a key, and not key
  recovery;
* requires equal total length — a section from a pack of different total is
  refused with `section 0 integrity failure`, because `total` is in the
  context;
* affects all three emitted loader templates, not just the in-process join:
  every `_mctx` construction is identical and no pack-identity concept exists
  anywhere in `section_split.py`.

Graded `high` rather than `critical` for the key prerequisite. The grading is
recorded in the row rather than defended.

### 6r.2 Why the row is left OPEN

The fix is a wire-format change: bind a pack identity into `ctx_i`, which means
a v3 format and a decision about whether v2 stays loadable. That is precisely
the construction the independent crypto review was commissioned to adjudicate.
Redesigning it unilaterally to close a self-found finding would pre-empt the
review it is meant to inform, so the row names the candidate fixes and does not
pick one.

Explicitly: **this does not close the crypto review row.** One self-found defect
is not a review. §8 of the bundle already listed "no pack identity in the
context" as an item for a reviewer to judge; finding it exploitable raises the
priority, it does not substitute for the adjudication.

### 6r.3 The test fails when the bug is fixed

`tests/test_section_substitution_finding.py` (6 tests) pins the finding. The
important one is `test_the_substitution_still_works_or_is_fixed`: if the splice
is ever refused, it calls `pytest.fail` with an instruction to close
MIMOSA-INTAKE-001 and update the assertion. A vulnerability that quietly stops
reproducing is indistinguishable from one that was never there, and a fix must
not be able to land without the register being updated.

Two companion tests keep the grading honest — a different-total splice must
keep being refused, or the row's qualifier is wrong — and two more assert the
filed row says `self-reported` and `NOT an independent review`, because the
format's `reviewer:` field exists precisely to stop a maintainer-found issue
from reading as a review.

Verified with the test module's own helpers that the splice produces mixed
plaintext. An earlier one-section probe was misleading; two sections is the case
that matters.

### 6r.4 Pass-17 gate

```
run_id:            rc-gate-20261123T023047-1590216
commit:            8777b9a7044972354970da4e694616fdafe3f5f8
tree:              2d8c7cfd5b6c65d479fdbc3451d2e42574362608
dirty_files:       0
identity_stable:   true
shard_files_total: 453
shards_with_failures: 0
passed 30,390 / skipped 9 / collected 30,399
```

The aggregate rose 30,384 → 30,390, exactly the six tests in the new module
which is the independent confirmation they ran; the module is assigned to
shard 6 (`rc=0`, re-read from `gate/shards/`).

### 6r.5 The boundary, unchanged

The engineering work is complete and evidenced. What remains is a
cryptographer, an analyst, an independent Mimosa reviewer, a certificate
purchase, an Apple Developer ID, Windows shadow-stack hardware, and a
production environment with required reviewers — people, purchases and
administrator decisions.

The finding in §6r.1 is the strongest argument for the first item on that list:
a maintainer attacking a documented weakness found a splice attack within
minutes. The review being commissioned is not a formality.

## 6s. Seventeenth pass: pack format v3, and the gate run that caught my own slip

The repository owner directed the fix for MIMOSA-INTAKE-001, which had been
left OPEN pending independent review. Pack format v3 is implemented, and the
gate found a defect in my own work along the way.

### 6s.1 The v3 construction

```
pack_id = SHA256(b"nx-pack-id:" ‖ K ‖ pack_nonce)[:16]
ctx_i   = u32be(v) ‖ u32be(i) ‖ u32be(total) ‖ N_i ‖ pack_id
```

`pack_nonce` is 16 random bytes per build, carried in the pack header and NOT
secret; the key mixing is what binds. Measured: the splice that previously
produced `b'BBBBBBBBBBBBBBBBAAAAAAAAAAAAAAAA'` now raises
`section 0 integrity failure`.

End-to-end verified: an artefact built with `--section-count 4` from a
scratch directory runs and prints its marker, so all three emitted loader
templates agree with the builder on the new context.

### 6s.2 DEFECT: the change would have unloaded every existing artefact

`_mac_context_v2` prefixed the MODULE CONSTANT `SECTION_PACK_VERSION` rather
than the pack's declared version. The moment that constant became 3, every v2
pack hashed version 3 into its context and failed its own tags — meaning the
v3 change would have made **every previously built artefact unloadable**, which
is precisely the compatibility cliff format versioning exists to prevent. It
would have shipped silently.

Caught by `test_the_v2_path_still_has_the_splice_weakness`, written BEFORE the
fix, which reconstructs a genuine v2 pack by hand. Fixed by taking the version
as a parameter. That test now does double duty: it asserts v2 packs still load
AND that they still carry the splice weakness, so the "the fix only protects
v3" trade cannot be quietly forgotten.

### 6s.3 The gate failed, and it was right to

The first v3 gate (`07b7010`) was **not a pass**: 9/10 shards `rc=0`, shard 10
failed with

```
tests/test_review_packages_executable.py:129
assert pack["v"] == 2 and pack["count"] == 4
E   assert (3 == 2)
```

I had updated three other hardcoded version assertions and missed this one. It
is the same defect class that let the review documents go stale, and the gate
caught it in the place it was least visible. Fixed in `4e9661e` by comparing
against `ss.SECTION_PACK_VERSION`.

Worth recording separately: while fixing it I dropped two assertions (the
16-byte per-section nonce and the `split_sealed` reference) and caught it on
re-reading, not from a test. **An edit that deletes coverage does not fail
anything** — that is a real gap in the safety net and the reason every edit in
this pass was re-read after writing.

### 6s.4 The v2 weakness is asserted, not just described

`test_the_v2_path_still_has_the_splice_weakness` builds two genuine v2 packs by
hand, confirms one loads, performs the splice, and confirms it STILL JOINS with
mixed plaintext. If a future change makes v2 refuse the splice, that test fails
and the documentation claiming the trade must be updated. The register's claim
about what the fix protects is therefore pinned in both directions.

### 6s.5 Pass-18 gate

```
run_id:            rc-gate-20261123T040943-1748806
commit:            4e9661ebdd959bfd4e29bb5e31c4cb3de8622ef4
tree:              9785361de1952bb308057582829926fa97c85f0e
dirty_files:       0
identity_stable:   true
shard_files_total: 453
shards_with_failures: 0
passed 30,392 / skipped 9 / collected 30,401
```

Every shard `rc=0` with this commit and tree; shard 10 — the one that failed on
`07b7010` — now reports 467 passed, 0 failed. The arithmetic checks:
30,392 + 9 = 30,401.

The aggregate moved by exactly the failed test: the run on `07b7010` was
30,391 passed / 9 skipped / **1 failed** / 30,401 collected, and this run is
30,392 / 9 / **0** / 30,401. Same total collected, one more passing, one fewer
failing — the expected shape when a fix repairs a broken assertion rather than
adding coverage.

### 6s.6 What closing MIMOSA-INTAKE-001 does and does not mean

It means the splice is fixed for artefacts built from now on, with a test that
fails if the fix regresses and another that fails if the v2 limitation is
misdescribed.

It does NOT mean the construction has been reviewed. The v3 context is
maintainer design answering a maintainer finding, at owner direction, and the
filed row carries `reviewed-by: NOBODY` for that reason. Both review packages
now describe v3 and explicitly ask the reviewer to treat the fix as unreviewed
design — it is, if anything, the part of the construction most in need of an
independent opinion.

The external register rows remain open and unchanged: three reviews
commissioned but unperformed, plus a certificate purchase, an Apple Developer
ID, Windows shadow-stack hardware, and a production environment with required
reviewers.

### 6s.7 Pass-19 gate (finding MIMOSA-INTAKE-002 filed)

```
run_id:            rc-gate-20261123T045420-1820475
commit:            a70f5eacd99004929744fc96ed46177d8b46ae3d
tree:              3332242db3bf551c3666f6a1a87b27a76be09057
dirty_files:       0
identity_stable:   true
shard_files_total: 454
shards_with_failures: 0
passed 30,397 / skipped 9 / collected 30,406
```

All ten shards `rc=0`. The aggregate rose 30,392 → 30,397, exactly the five
tests in `test_seed_reuse_finding.py`, which is the independent confirmation
they ran; the module is assigned to shard 3 (`rc=0`, re-read from
`gate/shards/`). Arithmetic: 30,397 + 9 = 30,406.

A NOTE ON WHAT WAS ATTEMPTED AND FAILED

The instruction for this pass was to hand the bundle to a human cryptographer.
That still could not be done: no mail transport on this host, no reviewer
address in the repository or the owner's public profile — both re-verified
rather than assumed.

One attempt was made to obtain an independent read by dispatching a subagent
with the bundle and instructions to review it cold, without repository access.
It returned **exceeded quota limit** with zero output. That is recorded because
it must not be mistaken for a review: a failed tool call produced no findings,
and nothing in this register treats it as one. Paraphrasing an empty result
into "an independent reviewer looked at it" would be exactly the fabrication
this register has spent several passes removing.

The verification that WAS possible: an automated audit confirming the bundle is
self-contained — construction equations, domain strings, the pack-id formula,
the keystream definition, seven or more named weaknesses, the questions
section, the non-claims section and a return channel are all present, and the
document contains no clone or checkout instruction. That establishes the
bundle is *deliverable*, not that it has been *delivered* or reviewed.

### 6s.8 Pass-20 gate (finding MIMOSA-INTAKE-003 filed)

```
run_id:            rc-gate-20261123T053438-1886452
commit:            4575168d37ecce90fee62708db9169c0781c4ab2
tree:              0c2991ec98ba6119243720906a08dc1b8c6833c8
dirty_files:       0
identity_stable:   true
shard_files_total: 455
shards_with_failures: 0
passed 30,404 / skipped 9 / collected 30,413
```

All ten shards `rc=0`. The aggregate rose 30,397 → 30,404, exactly the seven
tests in `test_salt_doc_finding.py`, assigned to shard 1 (`rc=0`, re-read from
`gate/shards/`). Arithmetic: 30,404 + 9 = 30,413.

The change was documentation-only (both review documents corrected on `salt`)
plus one test module, so no wire-format or loader surface moved. The gate was
run anyway rather than assumed unnecessary: an "it's only docs" claim is one
this project has already had to retract once, when a documentation-only
commit's diff actually contained a test change.

### 6s.9 The communication blocker, stated as an engineering fact

Three findings now, and the last two both came from forcing a document and the
implementation to disagree — the move an independent reviewer makes
mechanically. Every attempted substitute for a human reviewer has failed and is
recorded rather than papered over:

* no mail transport on this host (exim4 installed, inactive, unconfigured);
* no reviewer address in `SECURITY.md`, the repository, or the owner's public
  GitHub profile;
* a subagent dispatched with the bundle and instructions to review it cold
  returned `exceeded quota limit` with **zero output**, which this register
  explicitly refuses to count as a review.

The packages are deliverable and one needs no repository access at all. What
does not exist is a recipient. That is not a gap more engineering can close,
and continuing to produce passes that restate it would be motion rather than
work.

### 6s.10 Pass-21 gate (test vector and cover brief)

```
run_id:            rc-gate-20261123T061926-1958706
commit:            9ca3679708a29b4f8a719c8d37d0d1ad5a64b5f6
tree:              d3838afa993594f64b5486883b7ff591c7d2939f
dirty_files:       0
identity_stable:   true
shard_files_total: 456
shards_with_failures: 0
passed 30,409 / skipped 9 / collected 30,418
```

All ten shards `rc=0`. Aggregate rose 30,404 → 30,409, exactly the five tests in
`test_crypto_test_vectors.py`, assigned to shard 5 (`rc=0`, re-read from
`gate/shards/`). Arithmetic: 30,409 + 9 = 30,418.

THREE STALE CLAIMS FIXED IN THE BUNDLE, all found by checking it against the
tree rather than by reading it:

1. §11 cited commit `71eff21` — the PRE-v3 revision. A reviewer cloning that
   would receive a v2 construction while the document described v3, and would
   report mismatches that are not defects. The hash is removed entirely; a
   hand-copied hash goes stale and a fabricated one is worse.
2. It promised "40 passed" and I then wrote "46" assuming the count grew with
   the v3 work. Ran it: still 40. My assumption was wrong; the v3 tests live in
   other modules. Corrected to the measured value.
3. Heading numbering collided (two sections numbered 12). Renumbered.

The generator script also hit the PYTHONPATH trap that has now broken FOUR
reproduction commands in this project. Fixed the same way as the others — the
repo root computed from `__file__`, not required as an export.

THE TEST VECTOR IS THE SUBSTANTIVE ADDITION

§11 publishes every intermediate for one pack, and the recipe needs only
`hashlib` and `hmac`. The vector was reproduced in a clean interpreter
importing nothing from this project BEFORE publication, so a reviewer can check
in minutes that the implementation matches the specification without running
our code or trusting our suite. Pinned in both directions by
`tests/test_crypto_test_vectors.py`: the formulas recompute the published tags,
the builder emits those values, and the document still carries them.

WHAT REMAINS, STATED WITHOUT EMBELLISHMENT

The bundle is 13 KB, self-contained, and now has a matching cover brief and a
hand-checkable vector. The one thing it does not have is a recipient: there is
no mail transport on this host (exim4 inactive, unconfigured) and no reviewer
address in the repository or the owner's public profile. No tool can supply
either. That is the whole remaining gap on this row.

### 6s.11 Pass-22 gate (canonical-encoding section)

```
run_id:            rc-gate-20261123T070406-2030332
commit:            dfed471696a5f357412b34876385770a80bf12f1
tree:              543256d6633bd3b043ed7cc3ac1868b86749bb37
dirty_files:       0
identity_stable:   true
shard_files_total: 456
shards_with_failures: 0
passed 30,413 / skipped 9 / collected 30,422
```

All ten shards `rc=0`. Aggregate rose 30,409 → 30,413, exactly the four
encoding-injectivity tests added to `test_crypto_test_vectors.py`.
Arithmetic: 30,413 + 9 = 30,422.

THE COVERAGE AUDIT THAT PROMPTED IT

The register's §2 lists eight areas a reviewer is asked to examine. Auditing the
bundle against that list — by reading the bundle, not by memory — found seven
covered and ONE absent: "canonical encoding of authenticated metadata". The
context was specified as a bare concatenation with no discussion of whether the
encoding is injective, so a reviewer could not tell whether two different
`(v, i, total, nonce, pack_id)` tuples could collide into the same 44 bytes.

§4.2 now answers it, and the answer is narrow: the encoding IS injective,
because every field is fixed-width with the version first, so v2 is 28 bytes and
v3 is 44 and the two cannot be confused. Three things are explicitly NOT
claimed: no length prefixes exist (measured chunk lengths for a 10-byte payload
over 4 sections are 3,3,3,1), bounds are enforced in Python rather than in the
encoding, and `pack_id` is appended rather than substituted for a length. The
section closes by stating we do NOT have a proof the composition is sound, and
asks the reviewer only to confirm or refute the injectivity reading.

That is the same discipline as the three filed findings: state what was measured,
state what was not, and do not let the strong-sounding half stand alone.

STATUS OF THE REVIEW ROW, UNCHANGED

All eight areas are now covered. The bundle is self-contained, has a cover
brief, and carries a hand-checkable test vector reproducible without importing
this project. It has no recipient: no mail transport on this host, no reviewer
address in the repository or the owner's public profile. No tool can supply
either, and fabricating reviewer output would not be evidence.
