# Security Features, Objectives, and Wiring

**Status:** current audit, 2026-11-10. It classifies what the CLI options are
*for*, whether they reach the build, and what evidence exists. It deliberately
separates **IP protection** from **licensing**, **provenance**, **anti-analysis**,
and **runtime integrity**, because those are different objectives and a flag in
one category does not buy the others.

Companion documents:

- [`FLAG_AUDIT.md`](FLAG_AUDIT.md) — every flag, its parser, default, and
  primary objective, generated from the live parsers.
- [`SEED_ARCHITECTURE.md`](SEED_ARCHITECTURE.md) — seeds vs key material.
- [`MAXIMUM_SECURITY.md`](MAXIMUM_SECURITY.md) — measured configuration matrix.
- [`../THREAT_MODEL.md`](../THREAT_MODEL.md) — attacker-by-attacker evidence.

---

## 1. The objectives

| Objective | What it tries to achieve | What it does **not** do |
|---|---|---|
| **Static code obfuscation** | Make source harder to read: names, literals, expression shape, encoding | Stop execution or prove equivalence |
| **Control-flow / data-flow protection** | Make the CFG or data flow harder to reconstruct | Resist a determined dynamic analyst |
| **Anti-debugging / anti-instrumentation** | Detect or disrupt a debugger, tracer, VM, or audit hook | Hide the code from a root analyst |
| **Counter-REA / deception** | Waste an automated or human analyst's time with decoys and false leads | Provide a measured cost reduction — no study here |
| **Runtime integrity / anti-tamper** | Detect modified code, sections, stdlib, or loader state | Encrypt the code or prevent reading |
| **Cryptographic protection** | Keep payload/strings/sections confidential under a key | Protect against a client that must decrypt; keys are in the client |
| **Payload fragmentation / execution** | Avoid one contiguous plaintext buffer; split loader/sections/VM | Make the plaintext unobservable at run time |
| **Licensing / access gates** | Bind use to a customer, machine, or date | Increase reverse-engineering resistance |
| **Watermarking / provenance** | Mark a build for leak tracing; attribute a copy | Prevent analysis or modification |
| **Packaging / native compilation** | Change the delivered form (native extension, executable, stubs) | A measured obfuscation effect |
| **Verification / formal assurance** | Check that transformations preserve behaviour; produce evidence | Protect the artefact at run time |
| **Research / experimental** | Explore a mechanism; produce measurements | A supported protection claim |

A licensing gate is not obfuscation. A watermark is not obfuscation. A
verification report is not protection. Stated plainly because the CLI surface
invites the opposite reading.

---

## 2. What the audit found

Method: parse both parsers, trace each option's `dest` through the
implementation (regex over `opts.<dest>`, `args.<dest>`, `getattr(...)`,
`options/config.get(...)`), and run representative builds. The full table is
[`FLAG_AUDIT.md`](FLAG_AUDIT.md).

| Finding | Evidence |
|---|---|
| **324 unique flags** across the two parsers (270 build, 79 loader, 25 shared names) | [`FLAG_AUDIT.md`](FLAG_AUDIT.md) |
| Every option except `--version`/`--help` has at least one static consumer | consumer trace; see table |
| **6 flags are metadata-only**: their phase writes a config file that no runtime component reads | `class_dispatch_config.json`, `ssa_mutation_variants.json`, `state_isa_config.json`, `per_exec_recompile_config.json`, `self_healing_config.json`; the Rust modules were archived |
| **2 flags are inert**: `--temporal-keys` (metadata nothing reads, ~24 s) and `--crypto-binding` (build-time validation only) | phase logs; CLI notes |
| **9 loader-only flags are accepted and ignored by `build.py`**: trial, hwid, hwid-lock, hostguard, kod, no-snapshot, no-stdlib-audit, vm-threshold, customer-salt (refused) | parser help and consumer trace |
| **`--watermark` means two different things** | build.py: IR watermark; loader: loader HMAC watermark gate |
| **Loader output is next to the payload**, not in `./dist` | `/tmp/hello.py` → `/tmp/dist/hello_protected.py` (verified) |
| **`--opt-level 0` is not a byte-identical copy** | 2,635-byte payload → 6,282 bytes; rename/checksums/string sealing still run |
| **`--skip-obfuscate` is the true copy path** | 2,635 → 2,635 bytes, `diff` clean |
| **`--fast` and `--strict-detections` share one dest** | last flag on the command line wins; order-dependent |
| **`--hwid-lock` without `--hwid` is silently disabled** | `pipeline.py` passes `hwid_lock=(flag and bool(hwid))` |
| **`--licence-token` overrides `--customer-salt`** | the token's `key_material` becomes the customer salt |
| **`--section-count` has no effect with `--native-only`** | section split needs a fallback payload; code skips it |

---

## 3. Protection-relevant flags

This is the short list a protection decision should actually consider.
Everything else is verification, reporting, research, or operational.

### 3.1 Static and semantic obfuscation

`--opt-level 0..5` · `--lowering` · `--phase2` · `--phase2-only` ·
`--advanced-protection` · `--advanced-protection-only` · `--data-obfuscation` ·
`--data-obf-level` · `--speculation-obfuscation` · `--struct-randomization` ·
`--randomization-level` · `--ssa-variants` · `--cfg-mutation-variants` ·
`--class-dispatch-count` · `--function-intent` · `--poly-engine` ·
`--no-cfg-flatten` · `--no-opaque-predicates` · `--no-bogus-exceptions` ·
`--no-mba-subs` · `--no-fragment-strings` · `--no-unicode-ids` ·
`--seed` · `--randomization-seed` · `--build-id`

**Wiring.** The ladder and lowering are live and run. `--ssa-variants`,
`--cfg-mutation-variants`, `--class-dispatch-count`, `--state-isa`,
`--per-exec-recompile`, `--self-healing` are metadata-only: the phase writes a
JSON file and no runtime component reads it. `--function-intent` and
`--poly-engine` are experimental.

**Evidence.** Build and run verified on the representative payload. Semantic
lowering parity is tested (`tests/test_lowering_parity_141.py`); shim overhead
is measured at 1.46×–3.84×. **No measurement of reverse-engineering resistance
exists for any of these.**

### 3.2 Anti-analysis, counter-REA, and deception

`--anti-rea` · `--anti-rea-level` · `--no-anti-rea` · `--exclude-rea` ·
`--exclude-rea-compliance` · `--exclude-rea-cognitive` · `--exclude-rea-bio` ·
`--poison-*` · `--decoy-apis` · `--decoy-api-count` · `--honey-functions` ·
`--reasoning-traps` · `--trap-depth` · `--prompt-resistance` ·
`--attention-poison` · `--llm-resilient*` · `--multi-agent-deception` ·
`--storyline-count` · `--manipulation-detector` · `--false-confidence-audit` ·
`--self-critique` · `--red-team` · `--adversarial-injection` ·
`--adversarial-level` · `--adaptive-adversarial`

**Wiring.** The base shields and classifier bait are on by default in the
**packed loader** (`anti_rea=True`, level `balanced`). `build.py` does not
expose `--anti-rea`/`--anti-rea-level`; its `--adversarial-injection` runs a
different phase. `--no-anti-rea` overrides the level regardless of order.

**Evidence.** Builds and runs. The effect on an analyst is **not measured**. The
BLA paper's numbers do not transfer automatically; no study here reproduces
them.

### 3.3 Runtime integrity and anti-tamper

`--strict-detections` · `--fast` · `--no-snapshot` · `--no-stdlib-audit` ·
`--no-audit-hook-plant` · `--attestation` · `--challenge-response` ·
`--rolling-keys` · `--history-bound-decryption` · `--state-isa` ·
`--invariant-engine` · `--self-destruct`/`--one-shot` · `--kod` ·
`--hostguard` · `--driver-check` · `--temporal-keys` · `--crypto-binding` ·
`--section-split` · `--section-count`

**Wiring.** Frozen-stdlib snapshot, stdlib audit, audit-hook detector and
traceback suppression are on by default in the loader. `--fast` flips
detections to warn-only and lowers noise; it is a reduced posture. `--kod`
arms kill-on-detect. `--driver-check` is read-only enumeration.
`--temporal-keys` is inert; `--crypto-binding` is build-time only.
`--section-split` is on by default in the loader but needs a fallback payload;
it is skipped under `--native-only`.

**Evidence.** Unit and adversarial tests exist; hosted artifact probes cover
strip/tamper cases. No independent evaluation of bypass resistance.

### 3.4 Cryptographic protection and key handling

`--sign-key-env` · `--customer-salt` · `--licence-token` · `--section-split` ·
`--shards` (loader) · encrypted payload/string paths (no user flag)

**Wiring.** Blob encryption uses AES-CTR when `cryptography` is available and
fast-XOR as a fallback; string encryption uses ChaCha20+HMAC; section seals use
HMAC. Keys come from `secrets`/`os.urandom`. The build id salts the effective
key but is public; the customer salt/licence key material is a capability, not
a server secret.

**Evidence.** Execution verified (default, sectioned, licence-bound). The
sealed-section tag was changed from an unkeyed digest to HMAC after an audit
finding. No independent cryptographic review is recorded here; do not describe
the scheme as "secure" beyond "the client can decrypt it".

### 3.5 Licensing, hardware binding, and access gates

`--licence-token` · `--customer-salt` · `--trial` · `--expire` · `--hwid` ·
`--hwid-lock` · `--lock-hwid` · `--name-gate` · `--rename-internal` ·
`--bind-mac` · `--allow-countries` · `--block-countries` ·
`--allow-regions` · `--block-regions` · `--webhook` · `--remote-unlock` ·
`--one-shot` · `--kod` · `--hostguard` · `--driver-check`

**Wiring.** These are loader-only (or loader-first). `build.py` accepts several
but ignores them; `--customer-salt` is refused with a message.
`--hwid-lock` requires `--hwid` or is silently disabled.
`--licence-token` subsumes `--customer-salt`.

**Evidence.** The licence gate was verified: an artefact built with
`--licence-token` exits 1 without the token and 0 with it. This is access
control, **not** reverse-engineering resistance: the code is still readable.

**Measured defect.** `--trial 1s` and `--hwid … --hwid-lock` did **not** reach
the standard packed-loader artefact: both builds still ran past expiry / on the
wrong identity, and the gate symbols were absent
([`MAXIMUM_SECURITY.md`](MAXIMUM_SECURITY.md) §6.9). Treat trial/HWID as wired
into the hybrid-loader path only until that is fixed.

### 3.6 Watermarking and provenance

`--watermark` · `--verify-watermark` · `--verify-watermark-survivability` ·
`--dist-watermark` · `--dist-watermark-shares` · `--provenance-poison` ·
`--provenance-replace` · `--poison-level` · `--llm-fingerprint` ·
`--fingerprint-model` · `--uarch-watermark`

**Wiring.** `--watermark` on `build.py` embeds an IR watermark; with
`--skip-irgen` it logs a conflict and the string is **not** present in the
artifact (verified: `grep` count 0). On the loader it is an HMAC-tagged runtime
gate. `--provenance-poison` is provenance obfuscation, not a watermark.

**Evidence.** Watermark gate tests and hosted strip/tamper probes exist.
Survivability is a research instrument, not a guarantee.

### 3.7 Packaging and native compilation

`--pytoc` · `--pyinstaller-spec` · `--native` · `--native-only` · `--compile` ·
`--auto` · `--cross` · `--layers` · `--zips` · `--stego` · `--rust-exe` ·
`--python-dll` · `--generate-payload-h` · `--simd-vm` · `--portable`

**Wiring.** `--pytoc` and `--pyinstaller-spec` are best-effort and never fail
the build. `--native-only` requires the cloud farm and disables the fallback and
section split. `--layers` is the dominant build-time cost (100 default;
25 makes a hardened build practical).

**Evidence.** Builds and runs; no measurement that native packaging resists
analysis better than source obfuscation.

### 3.8 Verification and formal assurance

`--validate` · `--validate-fail` · `--verify-preservation` ·
`--verify-preservation-formal` · `--verify-mutations` · `--verify-jit` ·
`--verify-mba` · `--prove-vm` · `--prove-fragments` · `--proof-coverage` ·
`--proof-soundness` · `--verification-bundle` · `--evidence-ledger` ·
`--confidence-interval` · `--security-gates` · `--require-live-features` ·
`--claim-audit` · `--self-audit` · `--independent-audit` · `--red-team`

**Wiring.** Live. These check the build or produce evidence.

**Evidence.** They are not runtime protections. A green proof means the
transform preserved the tested property; it does not mean the artefact is hard
to reverse.

### 3.9 Research-only and experimental

`--fhe-vm` · `--oram` · `--sgx` · `--tee` · `--gpu` · `--hpc` ·
`--kernel-assist` · `--cpu-port` · `--uarch-diversity` · `--code-genome` ·
`--synthesis` · `--diversity` · `--adversarial-bench` · `--adversarial-loop` ·
`--adaptive-classifier-loop` · `--classify` · `--io-research`

**Wiring.** Flags exist and some phases run, but they are not on the default
path and have no security evaluation. `--code-genome` is real but expensive
(1,500 evaluations at defaults; did not finish in 300 s on a three-line file).

---

## 4. Cross-pipeline audit

The two parsers share 25 flag names. Shared name does **not** mean shared
behaviour.

| Flag | `build.py` | Packed loader | Difference that matters |
|---|---|---|---|
| `--cfg-flatten`, `--opaque-predicates`, `--bogus-exceptions`, `--mba-subs`, `--fragment-strings`, `--unicode-ids` | default **True**; bare flag is a no-op, use `--no-*` | default **None**; resolved from `--opt-level` (full set if absent) | Same name, different default and switch polarity |
| `--opt-level` | default **4** | default **None** = full set (O5-equivalent) | `--opt-level 5` is redundant on the loader; meaningful on `build.py` |
| `--watermark` | IR watermark; needs IR | HMAC-tagged loader watermark gate | Different mechanism, different failure mode |
| `--trial` | accepted, **ignored** | trial gate | Loader only |
| `--hwid`, `--hwid-lock` | accepted, **ignored** | HWID binding; lock requires `--hwid` | Loader only; lock silently disabled without hwid |
| `--hostguard`, `--kod` | accepted, **ignored** | hostguard snippet / kill-on-detect | Loader only |
| `--no-snapshot`, `--no-stdlib-audit` | accepted, **ignored** | disarm the loader gates | Loader only |
| `--vm-threshold` | accepted, **ignored** | VM-score verdict threshold | Loader only |
| `--customer-salt` | **refused** with guidance | per-customer key mask | Build.py has no payload key |
| `--licence-token` | **not accepted** (unrecognized) | key bound to token | Packed loader only |
| `--driver-check` | emits read-only BYOVD gate | loader gate | Both, different emission |
| `--split-bootstrap` | emits split bootstrap | loader path | Both |
| `--lowering` | source lowering; shim required | loader lowering | Both; deployment requirement |
| `--name-gate`, `--rename-internal` | emits | loader path | Both |
| `--output` | staging path; final `build/<name>_obfuscated.py` | output next to source: `<dirname(source)>/dist/` | Different conventions |
| `--payload` | payload flag | `build` subcommand takes a positional `source` | Parser-level name collision |

The full per-flag table is [`FLAG_AUDIT.md`](FLAG_AUDIT.md).

---

## 5. Evidence classification

`scripts/classify_features.py` reports **122 `LIVE (unverified)`** and **7
`DEAD CODE`** features (the seven archived Rust modules). "LIVE (unverified)"
means the call graph reaches the code; it is **not** artefact evidence and
**not** a security result.

| Feature group | Implemented | Reachable in build | Tested | Experimentally evaluated | Independently verified | Status |
|---|---|---|---|---|---|---|
| AST ladder | Yes | Yes | Yes | Build + run only | No | **Implemented** |
| Semantic lowering | Yes | Yes (`--lowering`) | Parity tests | Performance 1.46×–3.84× | No | **Implemented; performance measured, resistance not** |
| Counter-REA / deception | Yes | Loader | Build/run | No analyst study | No | **Implemented hypothesis** |
| Runtime gates | Yes | Loader | Unit + adversarial | Artifact probes | No | **Implemented; bypass resistance unverified** |
| Payload/string encryption | Yes | Both | Tests | Build/run | No crypto review | **Implemented; client-side by construction** |
| Section splitting | Yes | Loader | Tests | Build/run | No | **Implemented** |
| Licensing / HWID / trial | Yes | Loader | Tests | Token gate verified | No | **Implemented; access control only** |
| Watermark | Yes | Both | Tests | Strip/tamper probes | No | **Implemented; survivability research** |
| Packaging / native | Yes | Best-effort | Tests | Build/run | No | **Implemented, best-effort** |
| Metadata-only mutation flags | Phase writes JSON | **No runtime consumer** | Build only | No | No | **Inert / metadata-only** |
| `--temporal-keys`, `--crypto-binding` | Yes | Build | Build only | No runtime effect | No | **Inert / build-time only** |
| Seeds / reproducibility | Yes | Build | Unit | Measured | No | **Source emitter deterministic with `--seed`; loader partial** |
| Verification / proofs | Yes | Build | Yes | N/A | No | **Assurance, not protection** |

The 7 dead-code features: variant pool, CFG mutation, class dispatch, SSA
mutation, state ISA, per-exec recompile, self-healing. The variant pool is a
phase-2 config feature, not a CLI flag; the other six are the flags listed
above. Their phases still run and write metadata; their runtime modules were
archived and no consumer reads the metadata. Treat the flags as build-time
diagnostics, not protections.

---

## 6. What does not increase reverse-engineering resistance

- **Licensing, trial, HWID, expiry.** These decide whether the program may run;
  they do not make the code harder to read. A cracker reads the same code and
  patches the gate.
- **Watermarking and provenance.** These attribute a copy. They do not impede
  analysis.
- **Verification, proofs, coverage, evidence ledgers.** These assure the builder
  that a transformation preserved behaviour. They do not execute on the target.
- **Report-only flags** (`--metrics`, `--survivability`, `--protection-roi`,
  `--claim-audit`). They produce evidence, not protection.
- **Inert and metadata-only flags.** They produce files nothing reads.
- **Packaging alone**, without a measured attacker study. A native form is a
  different artefact class, not a demonstrated resistance gain.
- **Enabling every flag.** It increases build time, size, and failure surface;
  the measured maximum-flag build did not complete in 600 s.

---

## 7. Evidence gaps

1. **Attack measurement is bounded, not a study.** A deterministic-probe +
   single-LLM probe exists in [`MAXIMUM_SECURITY.md`](MAXIMUM_SECURITY.md) §7;
   no frontier-analyst study exists.
2. **No independent cryptographic review.** [`CRYPTO_REVIEW.md`](CRYPTO_REVIEW.md)
   is first-party.
3. **No measurement of counter-REA/deception effect** beyond the bounded probe.
4. **Trial/HWID gates did not reach the standard packed-loader artefact.**
   Measured in [`MAXIMUM_SECURITY.md`](MAXIMUM_SECURITY.md) §6.9: `--trial 1s`
   and `--hwid … --hwid-lock` builds still ran past expiry / on the wrong
   identity, and the gate symbols were absent from the artefact.
5. **Size is not a proxy for protection**: repeated builds of the same config
   varied from 1.46 MB to 8.25 MB.
6. **The seven dead-code features are still in `--help`**; a reader can mistake
   their metadata for runtime protection.
