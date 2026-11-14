# Maximum Security Configuration

**Status:** current investigation, 2026-11-10. The title is a question, not a
claim: this document establishes the **strongest configuration whose relevant
protections were actually built and run**, and states what remains unmeasured.

The short answer: **enabling every flag is not maximum security.** It is a
build-time and size explosion, it includes inert and metadata-only options, and
the strongest combination we could verify under a two-minute build budget is a
packed-loader build with **anti-REA at maximum, section count 6, a licence
token, a trial gate, a watermark, and 25 packaging layers**. At the default 100
packaging layers, the same configuration **did not finish in 600 s**.

Companion documents: [`SECURITY_FEATURES.md`](SECURITY_FEATURES.md),
[`SEED_ARCHITECTURE.md`](SEED_ARCHITECTURE.md),
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).

---

## 1. Method

Every measurement below was run on this host:

| Item | Value |
|---|---|
| Host | Linux x86_64 |
| Interpreter | CPython 3.13.5 |
| Payload | `tests/fixtures/portable/constructs_source.py`, 2,635 bytes |
| Payload constructs | dataclass, `match`, closures, generators, descriptors, async, decorators |
| AST-only builds | `--skip-irgen --skip-llvmgen --skip-encrypt --skip-relay --skip-extras` |
| Loader builds | `python3 -m obfuscator.core.pipeline build … --skip-cloud` |
| Timing | wall clock around the whole process, `date +%s` |
| Output check | run the artefact and compare the final line to `OK` |

The payload is deliberately richer than a `print()` demo. A configuration that
breaks dataclasses, `match`, closures, or async is not a usable maximum.

**What "verified" means here:** the build completed, the artefact ran, and the
protection was observable (a licence-bound artefact refuses without its token;
a sectioned artefact is built by the section path; a `--fast` build warns that
detections are reduced). It does **not** mean the protection was tested against
an analyst. No such test exists.

---

## 2. Measured configuration matrix

Sizes for loader builds are **not stable** across runs; the range is reported
where more than one sample exists. Do not use size as a proxy for strength.

| Configuration | Enabled protections | Compatibility / result | Performance impact | Security assessment |
|---|---|---|---|---|
| **Default (source emitter)** | O4 ladder (14/17), phase-2 defaults from `config/default.json`, always-on rename/checksums/string sealing | Runs standalone; no toolchain with the five skips | **1.9–2.3 s**, **34.2 KB** (2 runs) | Basic static obfuscation. No loader gates. No measured resistance |
| **Balanced (source + lowering)** | O5 ladder (17/17), phase-2 defaults, 20-family semantic lowering | Runs **only** with `obfuscator/lowering_shim.py` on `PYTHONPATH`; otherwise `ModuleNotFoundError` | **1.9 s**, **37.3–37.5 KB**; shim overhead 1.46×–3.84× per family (documented measurement) | Stronger static surface; deployment cost; no measured resistance |
| **High (packed loader defaults)** | O5 full set, section split on (4 sections), anti-REA **balanced**, strict detections, frozen-stdlib snapshot, stdlib audit, audit-hook detector, 100 packaging layers | Runs; 3.55 MB artefact; no cloud | **387 s** (one run), **3,554,107 bytes** | Strongest **default** posture; all controls client-side; no measured resistance |
| **Maximum practical (verified)** | High + anti-REA **maximum**, section count 6, watermark, trial 7 d, licence token, **25 packaging layers** | Runs **with token**; exits 1 without it; no cloud | **69–99 s** (4 runs), **1.46–8.25 MB** (high variance) | Strongest combination verified under a ~2-min budget. Anti-REA effect unmeasured; 25 layers is less packaging depth than default |
| **Maximum flags, 100 layers (negative)** | Maximum practical with default 100 layers | **Did not finish in 600 s**; stopped during packaging layer 61 | >600 s, no artefact | Not practical on this payload/host |
| **Reduced (`--fast`) (negative control)** | Loader defaults but detections warn only, lower noise/rdtsc | Runs; warning printed twice | **48 s**, **2.20 MB** | Weaker by design; useful only as a control |

### 2.1 Source-emitter measurements

| Config | Build time | Size | Runs? |
|---|---|---|---|
| Default O4, run 1 / 2 | 2.3 s / 1.9 s | 34,174 / 34,192 B | Yes (`OK`) |
| O5, run 1 / 2 | 1.9 s / 1.9 s | 34,076 / 33,797 B | Yes (`OK`) |
| O5 + `--lowering all`, run 1 / 2 | 1.9 s / 1.9 s | 37,280 / 37,505 B | Yes with `PYTHONPATH=obfuscator`; no without |
| O0 + `--phase2-only none` | 1.8 s | 6,282 B | Yes — **not** a copy |
| `--skip-obfuscate` | 1.8 s | 2,635 B | Yes — byte-identical copy |

The O5 build is not consistently larger or smaller than O4. Output size is a
poor proxy for transformation strength.

### 2.2 Loader measurements

| Config | Layers | Time | Size | Token required | Runs |
|---|---|---|---|---|---|
| Loader defaults | 100 | 387 s | 3,554,107 B | No | Yes |
| Balanced + section 6 + watermark + trial + licence | 100 | 551 s | 4,445,127 B | **Yes** | Yes with token; exit 1 without |
| Anti-REA max + all bindings | 25 | 69 s | 8,254,521 B | Yes | Yes |
| Anti-REA max + all bindings | 25 | 71 s | 1,456,853 B | Yes | Yes |
| Anti-REA max + all bindings | 25 | 75 s | 3,526,544 B | Yes | Yes; no-token exit 1 |
| Anti-REA max, no bindings | 25 | 60 s | 2,156,478 B | No | Yes |
| Anti-REA max, no bindings | 25 | 69 s | 5,704,174 B | No | Yes |
| Balanced + all bindings | 25 | 72 s | 1,357,259 B | Yes | Yes |
| Default, no bindings | 25 | 51 s | 2,916,591 B | No | Yes |
| Watermark + trial only | 25 | 51 s | 2,744,524 B | No | Yes |
| Licence only | 25 | 80 s | 4,395,199 B | Yes | Yes with token |
| `--fast` | 25 | 48 s | 2,195,694 B | No | Yes |
| Maximum flags | 100 | **>600 s (timeout)** | **none** | — | No |

The size spread at 25 layers — 1.46 MB to 8.25 MB for the same configuration —
is larger than the difference between most configurations. The packaging
pipeline's recursive layers and random representation choices dominate size.
**Do not rank configurations by binary size.**

---

## 3. What the experiments establish

### 3.1 The loader defaults are already strong

The packed loader defaults are not a minimal configuration. They already
include:

- the full 17-transform ladder (no `--opt-level` means full set);
- section splitting, on by default, 4 sections;
- counter-REA shields at `balanced`;
- strict detections (sandbox, emulator, debugger frame, geo-fence, licence);
- frozen-stdlib snapshot, stdlib audit, audit-hook plant detector;
- traceback suppression;
- 100 recursive packaging layers.

`--opt-level 5` and `--section-split` in the old "maximum-security" recipe were
therefore **redundant**: both are already the default on this path. The recipe's
real additions were `--section-count 6`, `--anti-rea-level maximum`,
`--access trial=7d`, and `--watermark`. It did not mention the licence gate, which is
the strongest key binding.

### 3.2 Licensing is not obfuscation

The licence-bound artefact is a useful, verified control:

```
$ python3 dist/constructs_source_protected.py
licence token required: set NIXON_LICENCE or place licence.json beside the artefact
$ echo $?
1

$ NIXON_LICENCE=/tmp/nx_max.licence python3 dist/constructs_source_protected.py
OK
```

That is **access control**. The code is still in the artefact and still
readable. It does not increase reverse-engineering resistance, and the
documentation must not imply that it does.

### 3.3 Packaging layers dominate build time

| Layers | Typical time (25-layer configs) | 100-layer configs |
|---|---|---|
| 25 | 48–80 s | — |
| 100 | — | 387–551 s |
| 100 + anti-REA max | — | **>600 s (timeout)** |

Reducing `--layers` from 100 to 25 is the difference between a practical build
and a nine-minute build (or a timeout). The security value of the extra 75
layers is **not measured**. This is a trade-off, not a free win.

### 3.4 Anti-REA maximum adds size, not measured resistance

At 25 layers, anti-REA maximum builds completed in 60–69 s (without bindings)
and 69–99 s (with bindings), versus 51 s for the balanced default. Size varied
from 1.46 MB to 8.25 MB, overlapping the balanced range. The **effect on an
analyst is not measured**; the flag's name is not evidence.

### 3.5 Enabling everything fails

The maximum-flags build with 100 layers did not complete in 600 s. It was still
in recursive packaging at layer 61 when the timeout fired. This is the clearest
negative result of the investigation: **more flags is not more security, and it
can be less availability.**

---

## 4. Interactions, conflicts, and redundant options

| Combination | Result | Evidence |
|---|---|---|
| `--opt-level 5` on the loader | **Redundant**; loader defaults to full set when `--opt-level` is absent | parser default `None`; `_loader_level` resolves full set |
| `--section-split` on the loader | **Redundant**; default is on | parser `default=True` |
| `--section-count N` without `--section-split` | Works, because split is on by default | parser test |
| `--section-split` + `--native-only` | **Silently skipped**; sections need a fallback payload | code: `if section_split and _plain and not native_only` |
| `--fast` + `--strict-detections` | **Order-dependent**; both write the same dest; last wins | parser test: fast→strict = True, strict→fast = False |
| `--anti-rea-level maximum` + `--no-anti-rea` | **`--no-anti-rea` wins**; level is ignored | parser test; `anti_rea` false |
| `--hwid-lock` without `--hwid` | **Silently disabled** | `hwid_lock=(flag and bool(hwid))` |
| `--licence token=` + `--licence salt=` | **Token wins**; its `key_material` becomes the salt | pipeline: `_customer_salt = _lic_key_material` |
| `--access trial=7d expire=DATE` | Two time gates; prefer one | both parsed; no conflict check |
| `--watermark` + `--skip-irgen` (build.py) | **Watermark not embedded**; conflict report; build succeeds | `grep` count 0 in artifact |
| `--temporal-keys` | **Inert**; ~24 s of hashing, metadata nothing reads | phase log; CLI note |
| `--crypto-binding` | **Build-time only**; nothing decrypts at run time | CLI note; phase log |
| `--cfg-mutation`, `--class-dispatch`, `--ssa-mutation`, `--state-isa`, `--per-exec-recompile`, `--self-healing` | **Metadata-only**; phase writes JSON, no runtime consumer | config files have no readers |
| `--code-genome` (defaults) | Real but expensive: 1,500 evaluations; did not finish in 300 s on a 3-line file | `--genome-generations 2 --genome-population 4` takes 2 s |
| `--pin-structure` | Pins structure, **not keys**; two builds differed | 1,882,254 / 1,882,385 bytes |
| `--seed` | **Source emitter deterministic** for same payload/tool/flags; packed loader still random | three builds 29,802 bytes each (`50ad8c80…`) |
| `--randomization-seed` | **No effect** on default AST path | two runs 35,840 / 37,009 bytes |
| `--lock-hwid` | Seeds map/VM RNG, registers licence; **not** a whole-build seed | code path |

---

## 5. The strongest practical configuration

### 5.1 Recommendation by objective

| Objective | Configuration | Why |
|---|---|---|
| **Source-only IP protection** | `scripts/build.py --opt-level 5` (or the default O4) | Runs standalone; no loader; low build cost. Add `--lowering` only if the shim can be deployed |
| **Strongest default delivery** | Packed loader defaults (`--skip-cloud`) | Full ladder, sections, balanced anti-REA, strict detections, integrity gates |
| **Maximum practical under ~2 min** | Loader defaults + `--anti-rea-level maximum --section-count 6 --watermark … --access trial=7d --licence token=… --package layers=25 stego` | Verified to build and run; licence gate verified; 69–99 s |
| **Customer binding** | Add `--licence token=` (and optionally `--access hwid=`/`hwid-lock`) | Access control, not obfuscation; token required at run time |
| **Leak tracing** | Add `--watermark` | HMAC-tagged loader gate; not a reverse-engineering barrier |
| **Reproducibility / debugging** | `--seed` / `--randomization-seed` in a debug channel | **Partial** determinism; not for customer builds |

### 5.2 The verified maximum command

```bash
# One-time: generate an issuer seed and keep it out of the repository.
ISSUER_SEED=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

# Issue a token for one customer.
python3 -m obfuscator.licensing issue --key-hex "$ISSUER_SEED" \
  --customer acme --days 30 --features pro --out acme.licence

# Build. Output goes next to the payload: <dirname(payload)>/dist/
NIXON_LOG_REDIRECT=0 PYTHONPATH=$PWD \
python3 -m obfuscator.core.pipeline build payload.py \
  --skip-cloud \
  --anti-rea-level maximum \
  --section-count 6 \
  --watermark NX-MAX-001 \
  --access trial=7d \
  --licence token=acme.licence env-only bootstrap-encrypted chain \
  --package layers=25 stego

# CLOUD maximum (adds the Cython/Nuitka compile on the GitHub build farm).
# Needs build-farm credentials (pipeline config or --cf-token) and network.
# NOTE: stego conflicts with the cloud build (enforced, exit 1) — drop it
# from --package when cloud is present.
NIXON_LOG_REDIRECT=0 PYTHONPATH=$PWD \
python3 -m obfuscator.core.pipeline build payload.py \
  --section-count 6 \
  --watermark NX-001 \
  --access trial=7d \
  --licence token=acme.licence env-only bootstrap-encrypted chain \
  --package native compile cloud platform=github layers=25 zips=3

# ABSOLUTE maximum — every namespace, every gate, one command. Everything
# below resolves (parse-verified); defaults not shown are already on
# (all six transforms, anti-REA maximum, advanced protection,
# split-bootstrap, sectioned sealing, strict detections, integrity gates).
NIXON_LOG_REDIRECT=0 PYTHONPATH=$PWD \
python3 -m obfuscator.core.pipeline build payload.py \
  --section-count 8 \
  --watermark NX-001 \
  --lowering io,scalar,string,container,service,protocol,function,import,fusion,arithmetic,truth,slice,format,augassign \
  --transforms data function-intent speculation \
  --access trial=7d expire=2027-12-31 hwid=<machine-hwid> hwid-lock kod driver-check \
           name-gate rename-internal bind-mac webhook=https://alerts.example/hook \
           vm-threshold=65 \
  --licence token=acme.licence env-only bootstrap-encrypted chain \
  --tls-ca-bundle /etc/ssl/certs/ca.pem \
  --package native compile cloud platform=github layers=25 zips=3

# Run. Without the token the artefact exits 1.
NIXON_LICENCE=acme.licence python3 dist/payload_protected.py
```

Every remaining loader flag is either in this command or deliberately
excluded: `--access one-shot` (self-destruct after the first run — breaks
re-runs, add only for burn-after-use payloads), `--package native-only`
(removes the bytecode fallback entirely — stronger, but hwid-lock then has
no fallback blob to lock and a farm compile failure bricks the artifact),
`--exclude …` (nothing: every shield family is on), `--fast` / `--public` /
`--debug-dump-raw` / `--pin-structure` (weaken or debug — never in a max
build), `--tor`/`--tor-proxy` (build-host privacy, not artifact security),
`--resume`/`--exclude-android`/`--python` (farm ops).

Measured on the 2,635-byte payload: **69–99 s**, **1.46–8.25 MB**, runs with
the token, exits 1 without it. Do not add `--opt-level 5` (the ladder is already at its
maximum on this path) or `--section-split` (sectioned sealing is now the
default; `--no-section-split` is the opt-out).

## Already ON by default (2026-11-12 consolidation)

The CLI is now ~50 flags because protections became defaults. Nothing was
dropped; these run in every normal build without a flag:

- Six AST transforms: CFG flattening, opaque predicates, bogus exceptions,
  MBA substitution, string fragmentation, Unicode identifiers (opt out per
  family: `--exclude transforms.mba-subs`, …).
- Counter-REA shields at **maximum** (opt out: `--exclude rea`), including
  adversarial dead-code/prompt injection (family `rea.adversarial`).
- Advanced protection; split-bootstrap key (Shamir n=3,k=2); sectioned
  payload sealing; strict detections; audit-hook plant, frozen-stdlib
  snapshot and stdlib function-audit gates
  (opt out: `--exclude integrity.audit-hook|integrity.snapshot|integrity.stdlib-audit`).
- Post-build verification suite (PHASE 3) on the native path.

**Native path (`scripts/build.py`) maximum additions:** the opt-in passes
`--transforms data function-intent speculation struct`, `--validate fail`,
and the packaging options `--package pytoc pyinstaller cross=TARGETS`.
**Loader path maximum additions:** `--package layers=25 stego`, the access
gates (`--access trial=7d expire=… hwid=…`), the licence gate
(`--licence token=… env-only bootstrap-encrypted chain`), and assurance
reports (`--audit all` — reports do not change the artefact).

**One-flag maximum:** `--package all` (alias `everything`) means "package
with everything else". On the native path it expands to `pytoc pyinstaller
cross=win,linux,macos,linux-arm` plus every opt-in `--transforms` pass and
`--validate fail`. On the loader path it expands to `layers=25 zips=3 stego`
on top of the protections that are already on by default. Everything else
above still applies as documented.

`--licence` is the unified spelling: its sub-options (`token=`, `env-only`,
`bootstrap-encrypted`, `chain`) are the whole licence interface — the former
per-knob `--licence-*` spellings were removed 2026-11-12. The same holds for
`--web3`, which is now the only spelling of the Web3 sub-options (rpc,
explorer, contract, shards, deploy, deploy-rpc). The licence identity gate is
`--licence … chain`, not any Web3 sub-option.

`--licence-env-only` is the hardening default for AI-facing distribution: the
emitted loader reads the token only from `NIXON_LICENCE` and no longer searches
for `licence.json` / `licence.licence` beside the artefact. Verified on a small
build and on the maximum build: a token file placed beside the artefact is
ignored, the environment token runs the payload, a forged 64-hex token fails
with `[FATAL] Magic Mismatch (Decryption Failed)`, and the token's
`key_material` does not appear in the artefact. Do not ship the token in
`dist/`; put it in the licensee's secret store or launch environment.

`--licence-bootstrap-encrypted` goes one layer earlier: the loader string table
is encrypted with a token-derived key, so the artefact cannot decode its own
bootstrap strings without the token. Verified on a 502 KB build: no token, a
local token file, and a forged token all fail; the environment token runs the
payload. This does not make the loader code unreadable, but it removes the
route names, gate strings, and embedded-key clues from static analysis.

`--licence-chain` adds an optional on-chain identity gate. The licence token
carries signed chain metadata (`rpc`, `contract`, `token_id`, `owner`,
`chain_id`), issued with `obfuscator.licensing issue --chain ...`. The loader
performs a read-only `eth_call` to verify that the token's owner still matches
the signed `owner` field. No transaction is sent, no testnet is required, and
the RPC endpoint is signed into the token so a runtime caller cannot point the
check at a fake node. The build rejects `--licence-chain` without signed chain
metadata. Because the artefact needs network access to verify the owner, a
build with `--licence-chain` fails unless the chain and token are reachable.
This is identity gating at licence issuance; it does not create a server-side
trust boundary.

The runtime also pins the exact signed licence payload with SHA-256. The token
signature is verified during the build; the loader then refuses any token file
whose canonical payload does not match the pinned hash. A forged token that
changes metadata but keeps the same `key_material` therefore fails with
`licence token does not match the pinned token`. The build requires
`NIXON_LICENCE_PUBLIC_KEY` to contain the issuer public key.

The forged-token check found a real defect in the first version of this
binding: the loader checked that a token existed but did not mix its material
into the `k_dec` payload stream key, so a forged token still decrypted the
payload. The fix mixes the token mask into `k_dec` at pack time and after the
runtime VM-chain derivation. `tests/test_licence_binding.py` now asserts that
a forged token fails.

### 5.3 Why not "all flags"

- Six flags write metadata no runtime reads.
- `--temporal-keys` is inert and costs ~24 s.
- `--crypto-binding` does not decrypt at run time.
- `--code-genome` at defaults is 1,500 evaluations and can stall a build.
- `--opt-level 5`, `--section-split` are redundant on the loader.
- `--fast` and `--strict-detections` fight over one dest.
- At 100 layers, the maximum-flags build exceeded 600 s.
- Licensing/trial/watermark do not make the code harder to read.

---

## 6. Negative results and failed combinations

Recorded because they are evidence:

1. **Maximum flags + 100 layers did not finish in 600 s.** The build was in
   recursive packaging at layer 61. No artefact was produced.
2. **`--opt-level 5` and `--section-split` are redundant on the loader.** They
   were in the old maximum-security recipe as if they added protection; they do
   not.
3. **`--watermark` with `--skip-irgen` does not watermark the AST artefact.**
   The log says "Watermarking" and writes `program_wm.ir`, but `grep` finds no
   watermark string in the emitted artefact.
4. **`--temporal-keys` adds 24 s and no runtime effect.**
5. **`--class-dispatch`, `--ssa-mutation`, `--state-isa`,
   `--per-exec-recompile`, `--self-healing` write configs that no runtime
   component reads.**
6. **`--seed` used to be partial; the wiring is fixed.** Before the fix, three
   same-seed O4 builds gave 29,805 / 29,800 / 29,805 bytes and the first
   difference was the string key. `phase01_obfuscate.py` now passes `seed=`
   into `build_pipeline`; three builds are byte-identical at 29,802 bytes. The
   packed loader is still not reproducible (random keys/packaging).
7. **`--pin-structure` does not reproduce a build.** 1,882,254 / 1,882,385
   bytes.
8. **`--fast` is a reduced profile**, not a faster maximum. It warns, twice.
9. **`--access trial=` and `--access hwid-lock` did not reach the standard packed-loader
   artefact.** Builds with `--trial 1s` (default and `--fast` profiles) still
   ran after expiry, and builds with `--hwid TEST-HWID-001 --hwid-lock` still
   ran on a different identity; neither build emitted the `_nx_kill` /
   trial/HWID gate symbols. The gates are wired into the hybrid-loader path,
   not the standard packed-loader path that `--skip-cloud` produces. Recorded
   as an open defect, not a supported gate.

---

## 7. Bounded attack measurement (2026-11-10, extended 2026-11-11)

This is **not** a frontier-analyst study. It is a reproducible, bounded probe
of the surface an automated analyst sees, recorded because "no measurement"
was worse than a scoped one.

| Artefact | Surface probed | Method | Result |
|---|---|---|---|
| Maximum practical loader (2,748,710 B) | Head/tail + 500 extracted strings | Deterministic probes + one LLM probe (`nvidia/nemotron-3-ultra-550b-a55b:free`, 20,016 prompt / 700 completion tokens) | **No payload plaintext or original identifier recovered.** Probes for `hello-nixon`, `slow_square`, `classify`, `make_counter`, `Point`, `Holder`, the docstring and `"OK"` all returned false (one `deliver` hit is loader runtime text, not the payload). The model identified the **loader's** purpose (zip load, HMAC integrity, anti-dump, secure delete) and mapped loader imports; it did not identify the payload |
| Source-level O4 artefact (33,184 B) | Full AST text | Same LLM probe | **Payload recoverable in principle.** The model identified the ChaCha20 string-cipher, the embedded `_nx_k` key, the integrity checker, anti-VM checks, and decoy functions, and concluded the encrypted strings are decryptable from the artefact alone |
| Maximum practical loader (2,748,710 B) | Full file, full tool surface | OpenCode 2.2.2 + Kern Qwen3.8-27B, `reverse-engineer-anything` skill, bash/edit/write, no step cap; 61 tool calls | **Payload fully recovered.** Static chain reconstructed; 242,049-byte source recovered; HMAC-SHA256 verified; 57 sealed strings decoded; 10 credential-like items; 88 top-level obfuscated names. **0/12 original names** — symbol renaming survived. No refusal |

Limits, stated plainly:

- The first two rows are one model, one prompt, no tool use, no dynamic
  execution, no decompiler. The third row is one model, one full-tool run, one
  payload.
- The packed-loader head/tail probe saw 16 KB of a 2.7 MB artefact plus its
  string table; its negative result is surface-limited.
- The full-tool run hit a 30-minute wall-clock timeout at step 43 and was
  continued in the same session for 140 s. No step cap was used.
- No claim is made about a determined human analyst with a debugger.

**What this supports:** on the no-tool surface, the packed configuration hides
payload semantics from string/LLM recovery. On a full-tool surface, the packed
layer is reversible: the payload, its HMAC, and its sealed strings were
recovered. What survived was the inner symbol transformation, not the loader.
This does **not** support "resists reverse engineering".

---

## 8. Multi-version and multi-payload coverage

| Check | Result |
|---|---|
| Source emitter, Python 3.10/3.11/3.12/3.13/3.14 | Built and ran on all five (`OK`) |
| Packed loader, cross-version | Version-locked: a 3.13-built artefact refuses 3.10/3.11/3.12/3.14 with `Incompatible Python Version` and runs on 3.13 |
| Payloads | `hello.py`, `constructs_source.py`, `stress.py` all built; loader artefacts 2.2–4.2 MB depending on payload/profile |

## 9. What remains unverified

- **No full attacker study** of any configuration. §7 is a bounded probe, not
  a study.
- **No independent cryptographic review** of payload, string, or section
  encryption. An internal review exists in
  [`CRYPTO_REVIEW.md`](CRYPTO_REVIEW.md); it is not independent.
- **No measurement of anti-REA maximum's effect** beyond the bounded LLM probe.
- **`--native-only` was exercised locally** (24 s, artefact produced), but the
  cloud-farm path was not; the artefact produced protects the loader itself.
- **Trial/HWID gates did not reach the standard packed-loader artefact** (§6.9).
- Loader sizes vary by several megabytes between runs; times will vary on other
  hardware.
- **100-layer builds are 6–9 minutes** on this host; real payloads will be
  worse.

The honest summary: **the strongest configuration we can verify builds and runs
is the maximum practical command in §5.2, but "strongest" here means "most
protections enabled without breaking execution or the build budget". It does
not mean "measured to resist reverse engineering".**
