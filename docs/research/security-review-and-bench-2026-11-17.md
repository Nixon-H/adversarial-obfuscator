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
