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
require compiler diversity (gcc vs clang vs MSVC backends, §5-B), which is not
available for all three platforms from this machine.

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

## 6. Honest limits of this benchmark
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

