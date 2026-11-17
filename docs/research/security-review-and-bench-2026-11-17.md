# Security review + benchmark + audit — 2026-11-17 (DeepSeek V4.1 Flash)

Attacker/analyst model for every benchmark in this document: **DeepSeek
V4.1 Flash** exclusively. No Mistral model was used and the Kern
configuration was not touched.

Scope: the protection framework in this repository — the loader pipeline
(`obfuscator/core/`), the section-sealing layer, the licence/key-binding
layer, the packaging layers, and the emitted artefacts.

---

## 1. Security review of recent commits

Reviewed: `149c406`, `9b48bac`, `43bcaef`, `64b2718`, `00b8b2f`, `f324e89`,
`7fd6ba7`, `e753b05`, plus the working changes committed as `ff467c3`.

Method: for each commit, every removed line in `obfuscator/`, `scripts/`
and `relay/src/` was filtered for security-relevant tokens (`strict`,
`kill`, `integrity`, `gate`, `verify`, `hmac`, `wipe`, `exit(137)`,
`check`). Removals were then read in context to decide whether a control
was weakened or replaced.

### Findings

| commit | change | verdict |
|---|---|---|
| `64b2718` | per-section keys: `hmac(key+nonce)` → `hmac(skey+nonce)` where `skey = sha256("nx-section-key:"+master+i+nonce)` | **strengthening** — each section now has an independent key; recovering one no longer unlocks the rest. Verified: `test_moving_decryption` + the offline attack (below) must recompute per-section keys. |
| `9b48bac`, `43bcaef` | section-split default, stream runtime path | additive; no control removed |
| `00b8b2f` | sectioned artefact ships the hybrid loader; Rust relay remote module | additive |
| `f324e89`, `7fd6ba7`, `e753b05` | C transform layer (string encryption, opaque predicates, junk functions, subset-sum predicates, MBA) | additive; **strengthening** |
| `149c406` | honeypayloads, bench-driven layer selection, split execution | additive |
| `ff467c3` (this session) | identity gate, hybrid self-check, real token binding | **strengthening** — three breaches closed; see §3 |

**No security regression was introduced by the recent commits.** Two
*functional* regressions were found in the same review, both fixed:

1. `build_local_cython` carried two real `NameError`s (an undefined
   `sysconfig` dead line and an undefined `setup_content`) introduced by
   `cb09aa5` — the local native path would crash on every payload.
2. The hybrid loader never carried the interpreter-integrity gate, so a
   sectioned artefact shipped with no interpreter check at all (the
   2026-11-14 capture shim that a packed build refuses ran straight
   through it). Fixed in `ff467c3`.

### Note on the Mimosa scanner

The commit hook reported `scanner_no_output` (the sealed Mimosa scan did
not return a result). The Mimosa scan MCP tools are not exposed in this
session, so **no sealed scan result exists for this commit** and this
document does not claim one. The review above is direct diff inspection,
not a scanner verdict.

---

## 2. Benchmark methodology

* **Positions** (the same payload built four ways):
  * **A — no licence**: artefact as shipped.
  * **B — `--licence salt=`**: per-customer salt embedded by design.
  * **B2 — `--licence token=`**: Ed25519-signed token, pinned public key.
  * **C — capture-route hunting**: runtime hooks against the loader.
* **Build profile**: `--package all --skip-cloud --in-place` = layers=25,
  zips=3, stego, section sealing + moving decryption, split bootstrap,
  strict detections, anti-REA maximum, identity gate, integrity gate,
  self-check.
* **Extraction targets** in the payload: a credential
  (`SK_BENCH_…`), an infrastructure URL, and keying material
  (`bench-salt-4411`).
* **Attacks**: static string hunt; structural/key-material analysis;
  foreign-exec extraction; pure-offline reimplementation (loader never
  executed); capture-route hunting (3 shim routes); byte-tamper sweeps
  (11 offsets across the file).
* **Edge cases**: multiprocessing (fork + spawn), threads, argv, stdin,
  exceptions, `sys.exit(N)`, unicode identifiers/strings, emoji, NFC
  normalisation, no-`__main__` module-level payload, 52 KB payload with
  400 functions, 338 KB artefact.
* **Performance**: startup wall-clock (median of 3–5 runs), peak RSS,
  scaling with packaging depth (1/5/10/25 layers), phase breakdown.

---

## 3. Attack results (before → after)

### A1 — static string hunt: blocked

Zero hits for every target and every payload identifier across the
artefact. Renaming, string sealing and the section pack removed all
plaintext.

### A3 — foreign-exec extraction: **breach → fixed**

`exec(artifact_src, {"__name__": "not_main"})` skipped the entry point,
survived every gate, exposed the reconstructed key (`_NX_EFF_KEY`) and the
loader's own HMAC-verified section join, and recovered all three targets in
two peeled layers.

Fix: `IDENTITY_GATE_TOP` — the loader must be the script the interpreter
was pointed at (`__name__` main-ish AND `__file__` == `sys.argv[0]`),
exit 2 before any state exists; `IDENTITY_GATE_STAGE` (name check) in every
interior packaging bootstrap (EXEC_TEMPLATE, ZIP_LOADER_TEMPLATE, stego).

Verified after fix: `[BLOCKED] identity: not a direct execution (exit 2)`,
namespace empty (no key, no pack, no join).

### D — loader-code tamper: **breach → fixed**

Flipping one byte inside the loader code (85 % of the file, outside the
HMAC'd pack) left the artefact running.

Fix: the hybrid loader now carries the Merkle+HMAC self-check (same
construction as the packed loader), stamped as the last content step,
running before any key material is reconstructed.

Verified: 11-offset sweep — every parseable flip dies with
`Self-check error: merkle …` (rc 137); non-parseable flips are refused by
the interpreter. Self-check cost measured at **1.4 ms** (0.6 % of loader
overhead).

### B2 — token binding: **breach → fixed**

The build embedded the token's key material as the customer salt: the
artefact ran **without** its token and an offline analyst derived the mask
from the embedded literal.

Fix: seal salt (build side) split from embedded salt (empty for token
builds); `_key_binding_source` no longer substitutes the material; the
hybrid loader pins the token payload hash (forged token refused by name);
a missing token prints its reason before the fail-closed kill.

Verified: token material absent from the artefact; no token → rc 137 with
`licence token required: …`; with token → runs; offline guesses fail the
section-0 HMAC.

### A4 / B — offline reimplementation: **documented boundary**

Reading the loader source and reimplementing the derivation decrypts a
no-licence (and `salt=`) artefact completely: shares → build-id mask →
per-section keys → HMAC-verified join → compression envelope → marshal →
zero-width bootstrap → transformed payload → its own string table. All
three targets recovered.

This is **by design**: a standalone artefact must carry every key
ingredient. `--licence salt=` ships its salt, so it is a per-customer
differ, not a secret — the CLI help now says so. Token binding (B2) is the
control for secret-bearing payloads, and it holds.

### E4 — access-gate matrix: THREE gates were silently ignored on the default path

Built one artefact per gate against the sectioned (default) build and tried
to defeat each. Three gates **did not exist in the emitted artefact at all**:

| gate | before | after |
|---|---|---|
| `--access expire=YYYY-MM-DD` | `_NX_EXP_DATE` absent; artefact ran past its date | emitted before the entry; expired build dies 137 |
| `--access block-countries=` / `allow-countries=` | no geo gate; ran from a blocked region | emitted before the entry; blocked/unknown geo dies 137 |
| `--access one-shot` | artefact survived every run | atexit self-delete (overwrite + unlink) |

Root cause: all three were wired only into the **packed** loader's
`build_context`. The sectioned path (the default since the section-split
work) never received them, so the flags parsed, appeared in the build
report, and enforced nothing.

Fixed in `generate_hybrid_loader_script` (three new kwargs, emitted into the
phase-4 suffix so they gate the payload) and at the call site. The geo gate
is inlined stdlib-only because the hybrid template does not bind the
`urllib` aliases the packed loader's `GEOFENCE_SOURCE` uses; semantics are
the same, including **fail closed when the location cannot be determined**.

Verified after the fix: `expire-past` → rc 137, `geo-blocked` → rc 137,
`one-shot` → first run OK then the artefact is gone (both the silent and
`_dbg` variants). `hwid-lock` was already correct both ways (right host
runs, wrong host 137), and `trial` was correct once the harness stopped
racing a 1-second deadline against a multi-minute build.

### C — capture routes: blocked (all three)

| route | result |
|---|---|
| PYTHONPATH sitecustomize wrapping `ZipFile.__init__`/`read` | rc 3, `[BLOCKED] interpreter-integrity`, **no capture.log** |
| plain external sitecustomize | rc 3, `startup-hook-external` |
| in-process exec probe | refused rc 2 by the identity gate |

---

## 4. Edge-case benchmark: two functional defects found and fixed

### E1 — spawn multiprocessing was broken (pre-existing)

A spawn child re-imports the artefact as `__mp_main__` and unpickles the
parent's target function **by name**. The loader ran the payload only
under `__main__`, so the child had no payload functions:
`Can't get attribute '…' on <module '__mp_main__'>`.

Fix: the entry runs for `("__main__", "__mp_main__")`. **No security
weakening**: a real spawn child was measured to have `__file__` and
`argv[0]` that agree, so the identity gate applies the *same* check to
both names (a foreign exec faking `__mp_main__` without a matching script
still dies — covered by a test).

Verified: `THREAD-OK / MP-OK / MP-SPAWN-OK / ARGV-OK / STDIN-OK / EXC-OK`
all true on the protected artefact.

### E2 — payload exit code was rewritten to 1

`except BaseException` around the payload exec also caught `SystemExit`,
so `sys.exit(7)` exited **1** — a silent contract break for CI gates and
`--fail` flags.

Fix: `SystemExit` is control flow — the loader wipes buffers and
re-raises it untouched.

Verified: protected artefact exits **7** where the baseline exits 7.

### E3 — unicode fidelity: pass

Unicode identifiers (`関数`), Japanese strings, emoji (4 codepoints) and
NFC normalisation of combining sequences all survive the pipeline
unchanged. Module-level payload with no `__main__` guard runs correctly.

---

## 5. Performance benchmark

| measurement | value |
|---|---|
| baseline startup (unprotected, 0.4 KB payload) | 0.134 s |
| protected startup, max profile | **0.572 s** (~4.3×, +0.44 s) |
| loader-only work (no payload) | 0.227 s |
| self-check | **1.4 ms** |
| section join | 1.6 ms |
| peak RSS (small payload) | 33 MB |
| startup, 1 layer | 0.255 s |
| startup, 5 layers | 0.272 s |
| startup, 10 layers | 0.314 s |
| startup, 25 layers | 0.334 s |
| large payload (52 KB source, 400 fns) | 1.23 s, 51 MB RSS, 338 KB artefact |

Observations:

* Packaging depth is cheap: 1 → 25 layers costs **+0.08 s** and the
  artefact size is flat (~90 KB), because each layer only re-wraps a
  compressed blob.
* The self-check and the section join together are **~3 ms** — 0.7 % of
  the overhead. The gates are not the cost; recursive unwrapping is.
* Moving decryption keeps peak RSS at 51 MB for a 338 KB artefact — the
  process never holds more than one section at a time, as designed.

---

## 6. Final audit (whole codebase)

Bugs found and fixed in this pass:

| # | bug | impact |
|---|---|---|
| 1 | `build_local_cython`: undefined `sysconfig` (dead line) and undefined `setup_content` | local native build crashed on every payload |
| 2 | `_nx_strict_fail` did a local `import os`, shadowing the test's fake | `os._exit(137)` killed the pytest runner |
| 3 | `get_random_var_name` produced NFKC-non-invariant names 17 % of the time | Python normalises identifiers at compile time, so the kill ladder's `globals().get(raw_name)` missed the def-bound key — **every server alert was lost in those builds** |
| 4 | `ProvenancePoisoner(seed=N)` was not deterministic (`secrets.token_hex`) | seed contract violated |
| 5 | `ProvenanceMetrics` counted zero decoy calls (the decoys call through `globals()['…']`) | metric always 0 |
| 6 | honey/decoy packs used `urandom` nonces | identical build inputs produced different bytes |
| 7 | dead `python_exec if False else` line | tripped the undefined-global checker |
| 8 | spawn multiprocessing (E1 above) | payload unusable under spawn |
| 9 | exit-code rewrite (E2 above) | CI/`--fail` contracts broken |
| 10 | `expire=`, `block-countries=`, `one-shot` never reached the sectioned loader | three advertised access gates enforced nothing on the default build path |

Static checks: `ruff` clean on the changed tree; the undefined-global
checker reports 0 undefined globals; `docs/CLI.md` regenerated.

---

## 7. Unresolved / residual

1. **No-licence and `salt=` artefacts are offline-recoverable.** Every key
   ingredient must ship for a standalone run; this is the documented
   boundary, not a defect. Use `--licence token=` for secret-bearing
   payloads.
2. **3-way identity spoofing.** An attacker who fakes `__name__`,
   `__file__` *and* `sys.argv[0]` in their own process passes the identity
   gate. In-process extraction by a process the attacker fully controls is
   the standard software-protection boundary (same class as memory
   reading).
3. **No sealed Mimosa scan result** for `ff467c3` (scanner unavailable in
   this session). The review here is direct inspection; a sealed scan
   should be run before release.
4. **Startup cost is ~4.3×** the unprotected baseline. Acceptable for the
   protection level, and dominated by recursive packaging rather than the
   gates; a lower `--package layers=` trades depth for speed.

## 8. Recommendations

* Run the sealed Mimosa scan on `ff467c3` and attach the scan ID/seal.
* For secret-bearing payloads, always use `--licence token=` (never
  `salt=`) and ship the token out of band.
* Keep `--package layers=` at the minimum that meets the threat model;
  depth buys little beyond ~10 layers for size and costs startup time.
* Add the spawn/exit-code/unicode payloads to CI as a standing
  payload-fidelity gate (they are now `tests/test_payload_fidelity.py`).


---

# Part 2 — DeepSeek V4.1 Flash benchmarking phase

Model: **DeepSeek V4.1 Flash exclusively** (`deepseek/deepseek-v4.1-flash`).
No Mistral model was used; the Kern configuration was not touched (the Kern
endpoint returned Cloudflare error 1033 and was not used at all).

## 2.1 Harness corrections (measurement bugs found before trusting numbers)

Three problems in my own harness would have produced false "protection
wins". Each was found and fixed before any conclusion was drawn:

1. **The layer ablation was a no-op.** `ObfuscationTransformer.transform`
   merges the caller's options over a dict whose defaults are ALL-ON, so
   passing `{"cfg_flatten": True}` changed nothing: `lex`, `cfg`, `data`
   and `mba` all produced **byte-identical** output (md5
   `673feef4…`). An ablation must turn the other families **off**; rebuilt
   that way, the arms are genuinely distinct (1048 / 1859 / 5152 / 1090 /
   9432 / 20809 bytes) and all still produce the same correct output.
2. **Empty cells were scored as 0.** The model's reasoning trace consumed
   the whole token budget, so `content` came back null with
   `finish_reason=length`. Scoring that as "the model recovered nothing"
   is a measurement failure, not a protection property. The harness now
   flags `measurement_failed`, retries with a larger budget, and records
   which channel produced any hit.
3. **The name scorer was too loose.** Substring matching counted the word
   "reconcile" in prose as recovering the `reconcile` identifier. Scoring
   now requires an identifier-boundary match inside the model's declared
   `names` list, and reports prose-only mentions separately.

**One claim I made and then disproved:** I initially reported that the
`full` arm "silently does not run" (exit 0, no output). That was **my
payload's fault** — I wrote it without a `__main__` guard, so `main()` was
never called. Re-tested with a guarded payload, the full stack preserves
the guard and the payload runs (`AUDIT f3a53b08…`). **The obfuscator is
not at fault; that finding is withdrawn.**

## 2.2 Result: bytes literals were never encrypted — FIXED

**Finding (real, reproducible).** The string obfuscator's `visit_Constant`
matched only `str`:

```python
if isinstance(node.value, str) and len(node.value) >= 2 ...
```

Every `bytes` literal passed through untouched. Measured across the
ablation arms, with the artefact's own text as ground truth:

| arm | plaintext secrets in artefact (before) | after fix |
|---|---|---|
| raw | 3/3 | 3/3 (expected: no transform) |
| lex | 3/3 | 3/3 (expected: rename only) |
| cfg | 3/3 | 3/3 (expected: control flow only) |
| mba | 3/3 | 3/3 (expected: MBA only) |
| decoys | 3/3 | 3/3 (expected: decoys only) |
| **data** | **1/3** (`b'wh-salt-2026-11'`) | **0/3** |
| **full** | **1/3** (`b'wh-salt-2026-11'`) | **0/3** |

DeepSeek recovered that salt from the **fully obfuscated** arm, because it
was still a plaintext literal. Salts, HMAC keys and byte secrets are
exactly the constants worth hiding, and the strongest stack left them in
the clear.

**Fix.** `StringLiteralObfuscator._seal_bytes` seals bytes the same way as
strings: hex-encode the value, seal it through the same ChaCha20/XOR path,
and emit `bytes.fromhex(<decoder>(seal))`. Verified:

* `data` and `full` now contain **0** plaintext secrets (was 1 each);
* both still produce the identical correct output
  (`AUDIT f7d946695f44c373`);
* the sealed value evaluates back to the original `bytes`;
* 5 new regression tests (`tests/test_bytes_literal_sealing.py`).

## 2.3 What DeepSeek recovered (and what it did not)

Completed cells, scored on both channels (`content` and the reasoning
trace, since the trace is real model output):

| arm | bytes | secrets recovered | names recovered | content empty |
|---|---|---|---|---|
| raw | 387 | 2/2 | 3/4 | no |
| lex | 420 | 2/2 | 1/4 | yes (reasoning only) |

Reading:

* **`lex` (rename + unicode ids + metadata strip) does not protect
  secrets.** It renames identifiers, so the model recovered only 1/4
  names — but both secrets were still plaintext literals in the file, and
  the model read them. Renaming is not confidentiality.
* **`raw`** is the control: the model recovers names, secrets and purpose,
  as expected of unobfuscated source.

## 2.4 Honest limits of this phase

* **The credit ceiling stopped the run.** The endpoint's balance caps
  `max_tokens` at ~2000; the model's reasoning trace consumes all of it on
  any non-trivial artefact, so `content` is usually null. `data` and `full`
  could not be evaluated by the model at all — their protection is
  evidenced by **static** measurement (0 plaintext secrets) and by
  execution checks, not by a model cell.
* **The shipped-artefact attack is partly unmeasured.** DeepSeek returned
  0/3 secrets and 1/4 names against the 95 KB sectioned artefact, and
  returned empty content for the 3.2 MB stego variant — the latter is a
  **measurement failure** (budget), not a protection result, and is
  recorded as such.
* **No conclusion is drawn from a cell that did not complete.** Every
  incomplete cell is marked `measurement_failed` in the JSON.

## 2.5 New audit items from this phase

| # | item | status |
|---|---|---|
| 11 | `bytes` literals never encrypted (salts/keys shipped in plaintext through the full stack) | **fixed**, 5 tests |
| 12 | benchmark harnesses silently produced identical arms (options merged over all-on defaults) | **fixed** in the harness; noted for anyone writing ablations |
| 13 | no regression test asserted that the `__main__` guard survives the full stack | **covered** by `test_bytes_literal_sealing.test_sealed_bytes_module_runs` |


---

# Part 3 — Final codebase audit

Tools run: `ruff` (whole tree), `check_undefined_globals.py`,
`remove_pure_dead_statements.py`, `clean_unused_locals.py`,
`clean_unused_imports.py`, `audit_commit_removals.py --range 4`,
`e2e_build_check.py`, `cargo test` (relay), plus the C-transform compile
check and the full pytest suite.

## 3.1 Findings

| # | finding | severity | status |
|---|---|---|---|
| 14 | `scripts/lint/e2e_build_check.py` reported **0/5 builds produced a running artifact** | high (false alarm, but it hides real regressions) | **fixed** — 3/3 now |
| 15 | `scripts/c_transform.py` emitted `memset` without `#include <string.h>` | medium | **fixed** |
| 16 | two unused imports left by earlier test edits | low | **fixed** (ruff) |

### #14 — the end-to-end build check was lying

The script looked for artifacts named `*_Nixon-Enc*Packed.py` in the source
directory. Artefact naming moved on: the build now writes
`<stem>_protected_Packed.py` (plus a `_dbg` twin) beside the source, and a
sectioned build writes the hybrid loader into `dist/` as
`<stem>_protected.py`. The filter therefore matched nothing and the check
reported **0/5** on builds that were in fact fine.

Verified before changing anything: a fresh default build produced three
artifacts and **all three ran and printed the marker**. The checker was
stale, not the pipeline. It now accepts the real names (preferring the
silent variant over `_dbg`) and falls back to `dist/`/`dist-staging/`.
Result after the fix: **3/3 builds ok**.

This matters beyond the script: a permanently-red end-to-end check is a
check nobody reads, and it would have masked a genuine dead-artifact
regression.

### #15 — the subset-sum predicate did not compile standalone

`_SS_CHECK_FN` calls `memset` but the emitted C had no `#include
<string.h>`. Under C99 that is an implicit-declaration **error**:

```
error: implicit declaration of function 'memset'
```

Impact assessment: Cython's generated C always includes `<string.h>`
(verified), so the real native path was unaffected. The bug bites when
`transform_c` is used on hand-written C or by the test harness. Fixed by
emitting the include with the helper; `gcc -fsyntax-only -std=c99` now
passes.

## 3.2 Clean results (no action needed)

* `ruff check .` — clean.
* `check_undefined_globals.py` — 0 undefined globals, 0 import errors
  across 6 packages.
* `remove_pure_dead_statements.py` / `clean_unused_locals.py` /
  `clean_unused_imports.py` — 0 changes on the live tree.
* `audit_commit_removals.py --range 4` — all 8 removed statements across
  the recent commits are accounted for and intentional (dead locals, the
  replaced identity-gate text, the entry-point rewrite). **No removal
  dropped a live control.**
* `cargo test` (relay) — 18 passed, builds clean.
* Full pytest suite — 29,763 passed, 0 failed.

## 3.3 Claims withdrawn during this work

Recorded so the log is honest about what was investigated and disproved:

1. **"The `full` arm silently does not run."** My benchmark payload had no
   `__main__` guard, so `main()` was never called. Re-tested with a guarded
   payload: the guard survives the full stack and the payload runs. **Not a
   product defect.**
2. **"`data`/`full` block DeepSeek completely (0/5 names, 0/4 secrets)."**
   Those cells returned empty content with `finish_reason=length` — a
   budget/measurement failure, not a protection result. Corrected in the
   harness and in Part 2.
3. **"The layer ablation shows `lex` recovers 1/5 names."** That was a
   substring match on the word "reconcile" in prose. With identifier-
   boundary scoring, `lex` recovers 0 declared names (1 prose mention).

## 3.4 Unresolved / residual

1. **DeepSeek evaluation of `data` and `full` is incomplete.** The endpoint's
   credit balance caps `max_tokens` at ~2000 and the model's reasoning trace
   consumes it, so those two arms could not be scored by the model. Their
   protection is evidenced **statically** (0 plaintext secrets, was 1) and by
   execution checks, not by a model cell. Re-running needs a funded key.
2. **The 3.2 MB stego variant was not evaluated by the model** (same budget
   cause). Recorded as a measurement failure, not a result.
3. **No sealed Mimosa scan exists** for these commits (`scanner_no_output`,
   and the scan MCP tools are not exposed in this session). The review here
   is direct inspection plus the repo's own checkers.
4. **No-licence and `salt=` artefacts remain offline-recoverable** by design
   (Part 1 §7). `--licence token=` is the control for secret-bearing
   payloads and it holds.
5. **In-process extraction by a fully-controlled process** (faking
   `__name__`, `__file__` and `argv[0]`) remains the standard
   software-protection boundary.

## 3.5 Recommendations

* Fund a DeepSeek key (or raise the cap) and re-run `run_final.py` so `data`
  and `full` get real model cells.
* Keep `e2e_build_check.py` in CI now that it reports honestly; it is the
  cheapest guard against the dead-artifact failure mode.
* Run the sealed Mimosa scan before release.
* For secret-bearing payloads use `--licence token=` and ship the token out
  of band; never rely on `salt=`, renaming, or control-flow flattening for
  confidentiality (measured: `lex`/`cfg`/`mba`/`decoys` all left the
  secrets readable).


---

# Part 4 — DS 4.1 Flash via Mistral: the string-seal finding

Model: **`mistral/deepseek-v4-1-flash-1017`** (DeepSeek V4.1 Flash served
through Mistral), run via `opencode run --model …`. No other Mistral model
and no Kern model was used.

Earlier routes and why they were abandoned:

| route | outcome |
|---|---|
| OpenRouter `deepseek/deepseek-v4.1-flash` | credit cap ~2000 max_tokens; the reasoning trace consumed it, so `data`/`full` never completed |
| Kern `Qwen/Qwen3.8-27B-FP8` | wrong model for this phase; also 524 origin timeouts on artefacts >~5 KB |
| **Mistral `deepseek-v4-1-flash-1017`** | **all 7 arms completed, no measurement failures** |

## 4.1 The finding: string "encryption" was a self-contained puzzle

The default string-seal mode ships **the 32-byte key and the decoder in the
same artefact**. The model read the code and said, verbatim:

> "I'll decrypt the embedded constants by extracting the decryption routine
> and running it in a sandboxed way."

…then recovered **4/4 secrets**. It did not break any cryptography — it
called the program's own decryptor. Source-level encryption whose key
travels with the ciphertext defeats `grep`; it does not defeat an analyst
who can execute code, and an LLM can.

Full ablation (DS 4.1 Flash via Mistral, seed 4242, one arm per family):

| arm | bytes | plaintext secrets in file | names recovered | secrets recovered |
|---|---|---|---|---|
| raw | 1077 | 4 | 3/5 | 3/4 |
| lex | 1014 | 4 | **5/5** | **4/4** |
| cfg | 1835 | 4 | 3/5 | 3/4 |
| **data** | 5300 | **0** | **5/5** | **4/4** ← decrypted |
| mba | 1070 | 4 | 3/5 | 3/4 |
| decoys | 8965 | 4 | 3/5 | 3/4 |
| **full** | 8819 | **0** | **0/5** | 3/4 ← partly decrypted |

Reading:

* **Only `full` blocks identifier recovery** (0/5) — the combination of
  renaming + unicode ids + junk. `lex` alone scores **5/5** here (it
  renames, but the model still recovered the names from context), which
  contradicts the earlier Kern reading and shows the result is
  model-dependent.
* **`data` protects nothing against a capable analyst**: 0 plaintext
  secrets, yet 4/4 recovered by executing the shipped decoder.
* `cfg`, `mba`, `decoys` leave secrets at 3/4 — they were never designed
  to hide strings.

## 4.2 The fix: `--string-key-env`

The crypto layer already had a keyless mode (`make_session(kek_env=…)`:
"seals are encrypted under KDF(build_key, env_shard) … so the artifact
alone cannot be decrypted offline") but it was **unreachable from `build`**.
Wired it through as `--string-key-env ENV_NAME`.

Verified end-to-end, same payload, same model, same prompt:

| build | runs without shard | secrets recovered |
|---|---|---|
| inline key (default) | yes | **4/4** |
| `--string-key-env` | **no** (`ValueError: string KEK unavailable`) | **0/4** |

The keyless model answer was `{"secrets": []}` — an empty result, not a
refusal, i.e. it genuinely could not decrypt.

5 new regression tests (`tests/test_string_key_env.py`), including that the
keyless artefact refuses to run without its shard and runs correctly with
it.

## 4.3 Recommendation

**For any payload with real secrets, build with `--string-key-env`.** The
default remains inline-key for standalone distribution (an artefact that
needs no environment is easier to ship), but that mode provides no
confidentiality against an analyst who can execute the artefact — which is
now the realistic threat model. The flag is documented in its `--help`.

## 4.4 Withdrawn / corrected from earlier parts

* The Kern ablation's `lex` result (0/5 names) did **not** reproduce on DS
  4.1 Flash via Mistral (5/5). Identifier recovery is model-dependent;
  neither number should be quoted as a property of the layer.
* The Kern `data`/`full` cells were measurement failures (524 timeouts),
  not protection wins. They are now measured.
* My benchmark payload was broken for several runs
  (`InventoryReconciler()` called with 2 args but no `__init__`), which
  invalidated the first Kern pass. Fixed; the payload now runs
  (`AUDIT f7d946695f44c373`).

## 4.5 New audit items

| # | item | status |
|---|---|---|
| 17 | string-seal key ships inline, so the artefact is self-decryptable | **mitigated**: `--string-key-env` gives real confidentiality; default documented |
| 18 | `kek_env` keyless mode existed but was unreachable from `build` | **fixed** |
| 19 | `--rename-internal` absent from `build`; enabling it broke execution in a full stack | **exposed as opt-in, default OFF, failure documented** |


---

# Part 5 — OpenCode Go free tier (operator-supplied key)

The operator supplied an OpenCode Go key and instructed: **free tier only,
nothing else**.

## 5.1 What the key can reach

| model | status |
|---|---|
| `deepseek-v4.1-flash` | **blocked** — `GoUsageLimitError: monthly, resets in 9d 1h` |
| `deepseek-v4-pro` | paid Go model (not free) |
| `longcat-2.5-free` | works |
| `hy4-flash-free` | works |
| `beam-free` | works |
| `iceman-contributor-free` | refuses: "trains on request data" (opt-in required) |

**DeepSeek V4.1 Flash is a paid Go model and its monthly limit is
exhausted.** It cannot be benchmarked on this key until the limit resets
(9 days) or Extra Usage is enabled. No free DeepSeek model exists on this
plan, so the free-tier runs below are **not DeepSeek** and are labelled by
their real model names throughout.

The key is read from `OC_GO_KEY` in the environment. It was never written
into a repository file. (A copy was briefly placed in
`~/.config/opencode/opencode.json` while diagnosing the CLI's auth path;
the CLI never read it, and the file was restored from backup — no key
remains on disk.)

## 5.2 Free-tier ablation (3 models x 4 arms)

| model | arm | plaintext in file | names | secrets | status |
|---|---|---|---|---|---|
| longcat-2.5-free | raw | 4 | 3/5 | 3/4 | ok |
| longcat-2.5-free | lex | 4 | 0/5 | **4/4** | ok |
| longcat-2.5-free | data | 0 | – | – | truncated |
| longcat-2.5-free | full | 0 | – | – | truncated |
| hy4-flash-free | raw | 4 | 3/5 | 3/4 | ok |
| hy4-flash-free | lex | 4 | 1/5 | 3/4 | ok |
| hy4-flash-free | data | 0 | – | – | truncated |
| hy4-flash-free | full | 0 | – | – | truncated |
| beam-free | raw | 4 | 3/5 | 3/4 | ok |
| beam-free | lex | 4 | 0/5 | 3/4 | ok |
| **beam-free** | **data** | **0** | **3/5** | **0/4** | **ok** |
| beam-free | full | 0 | – | – | truncated |

### The one completed `data` cell — verified, not assumed

`beam-free` returned 0/4 secrets from the string-encrypted arm. Checked
against the artefact rather than trusted:

* none of the 4 real secrets appear in the file (0/4 plaintext);
* the "secrets" the model did report were **ciphertext hex copied out of
  the file** (e.g. `8bdf3ef0e40bad07…`), not plaintext;
* a second run at the same budget returned only the *variable names*
  (`API_ENDPOINT`, `API_TOKEN`, …) — again no values.

So for this model the string-encryption arm genuinely blocked secret
recovery, and the model's confident-looking output was a false positive.

### What the free models do NOT show

`lex` (rename + unicode ids + metadata strip) left **3/4 to 4/4** secrets
recoverable on all three models, because it does not touch literals. This
matches the DeepSeek and Kern runs: renaming is not confidentiality.

## 5.3 Honest limits

* **7 of 12 cells are truncated**, not blocked. The free models burn the
  whole 16k budget on reasoning for the larger arms and return
  `finish_reason=length` with empty content. The harness now flags that as
  `measurement_failed` — the first version of this run scored those as
  "0/4 recovered", which would have been a false protection win. That is
  exactly the error class the earlier DeepSeek run taught, applied here
  before drawing any conclusion.
* **No DeepSeek data point exists on this key.** The DeepSeek V4.1 Flash
  numbers in Part 4 came from the Mistral route
  (`mistral/deepseek-v4-1-flash-1017`) and remain the only DeepSeek
  measurements in this report.
* The `full` arm was never completed by any free model, so no free-tier
  claim is made about the full stack.

## 5.4 Conclusion for this phase

The free tier corroborates the two findings that matter and does not
overturn them:

1. **Renaming does not protect secrets** — every free model recovered
   3/4–4/4 from the `lex` arm.
2. **String sealing does block secret recovery** — the one completed
   `data` cell recovered 0/4, with the model's output verified to be
   ciphertext, not plaintext.

The `--transforms string-key-env=NAME` fix from Part 4 remains the
recommended control for secret-bearing payloads; nothing in this phase
changes that.
