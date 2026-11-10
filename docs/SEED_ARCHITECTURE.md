# Seed Architecture and Randomness Audit

**Status:** current audit, 2026-11-10. It distinguishes four things the CLI and
documentation had been conflating: a **reproducibility seed**, a
**randomisation seed**, a **structure pin**, and **cryptographic key
material**. Only the last is security-sensitive.

Scope: `scripts/build.py`, `obfuscator/core/pipeline.py`, and every consumer
reachable from them. The audit is static (parser + consumer tracing) plus the
experiments in §5. It does not claim that every RNG draw in the tree has been
enumerated.

Related: [`MAXIMUM_SECURITY.md`](MAXIMUM_SECURITY.md),
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md), [`TRANSFORMS.md`](TRANSFORMS.md).

---

## 1. The inputs, at a glance

| Input | Parser | Default | What it actually controls | What it does **not** control |
|---|---|---|---|---|
| `--seed N` | `scripts/build.py` only | `None` | Seeds Python's global `random`; threaded into decoy, anti-REA, adversarial, provenance and fingerprint stages | String-encryption keys, blob keys, or `secrets` draws; it is not a cryptographic seed |
| `--randomization-seed N` | `scripts/build.py` only | `None` | Structure randomisation, speculation obfuscation, CPU-port phase | AST transform order, string keys, or the packed loader |
| `SEED` / `NIXON_SEED` | environment | unset | Fallback for `--randomization-seed` only; `NIXON_SEED` is checked first, explicit flag wins | `--seed`; the packed loader |
| `NX_BUILD_SEED` | environment, CI only | unset | `scripts/ci/isolate_flags.py` passes it as `--seed`; `AdaptiveRewriter` uses it as a nonce fallback | The rest of the build; not a CLI flag |
| `--build-id STR` | `scripts/build.py` only | `""` (random per build) | Seeds the **semantic-lowering native kernel** symbol map when `--pytoc` is used; recorded in the manifest/signature sidecar | The rest of the build; it does not make the artefact byte-reproducible |
| `--lock-hwid HWID` | packed loader only | `""` | Registers a licence for a target HWID and seeds the **polymorphic-map / poly-VM RNG** only | The blob key, string keys, or the whole build; the help text's "seeds the build deterministically" is broader than the code |
| `--pin-structure` | packed loader only | off | Pins emitter-only draws: encoding order, slot picks, names, VM op-map, marker token, build timestamp | Key material — the flag's own help says artefacts are not byte-identical |
| `secrets` / `os.urandom` | internal | always | Blob keys, per-string ChaCha20 keys/nonces, salts, nonces, VM seeds | Not user-seeded at all |

The distinction that matters:

- A **seed** selects a reproducible sequence for *structural choices*.
- A **key** is secret material used to encrypt or authenticate.
- A **salt** is public, domain-separating material; it is not a secret.

`--seed`, `--randomization-seed`, `--build-id`, and `--lock-hwid` are seed-like
inputs. None of them is a key.

---

## 2. Why the seeds exist

Builds are deliberately unique: the same payload built twice should not produce
the same artefact, because identical builds let an attacker reuse one analysis
across every customer. Randomisation is the mechanism.

That creates an engineering problem: a CI failure must be reconstructible.
Without a seed, two runs of the same command produce different transform
orders, decoy names, and string keys, so a failure cannot be replayed. The
seeds exist to make **debugging** possible, not to add security.

The implementation history is visible in the code comments:

- `phase09_adversarial.py` records that `hash()` of a string is randomised per
  process, so the same payload produced different adversarial injections and a
  CI failure could never be rebuilt; `--seed` replaced the hash.
- `phase10_provenance.py` records the same defect for provenance poisoning,
  which also carried machine-specific absolute paths into the seed.
- `scripts/build.py` seeds `random` so the transform order is pinned; the
  comment says this is why a flag could pass locally and fail in CI.
- `scripts/phases/phase01_obfuscate.py` threads `--seed` into transform
  options because `decoys` was the only level-3 addition and fell back to
  `secrets.SystemRandom()`.

These are reproducibility fixes. They are not security features.

---

## 3. Generation, initialisation, and propagation

### 3.1 `--seed`: the AST reproducibility seed

```
argparse --seed N
  └─ main(): random.seed(N)                       # global Python RNG
  └─ phase01_obfuscate(extra_options["seed"]=N)
       ├─ SemanticDecoyApiInjector(seed=N)
       ├─ AntiReaInjector(seed=N)
       └─ build_pipeline(source, seed=N, extra_options=...)
  └─ phase09_adversarial: seed = N & 0xFFFFFFFF
  └─ phase10_provenance:  seed = N & 0xFFFFFFFF
  └─ LLMFingerprinter(seed=N)
  └─ ReasoningLoopInjector(seed=_stage_seed(opts))
  └─ FunctionIntentObfuscator(seed=_stage_seed(opts))
```

`_stage_seed(opts)` derives a per-stage value:
`sha256("stage:<N>")[:8]`, so two stages do not share one stream. Without
`--seed` it returns `secrets.randbits(32)`.

**Previously a gap, now fixed.** `phase01_obfuscate.py` called
`build_pipeline(source, mba_validator=..., extra_options=extra_opts)` without
passing `seed=`. `ObfuscationTransformer` therefore had `self.seed is None`, so
its `_patch_secrets()` branch was skipped and string keys stayed random. The
call now passes `seed=getattr(opts, "seed", None)`, so the transformer seeds
its own RNG and patches `secrets` for the duration of the AST transform.

### 3.2 `--randomization-seed`: the structural seed

```
argparse --randomization-seed N
  └─ if flag absent: NIXON_SEED, then SEED
  └─ obfuscate_with_speculation(seed=N)       # only with --speculation-obfuscation
  └─ phase_struct_randomization(seed=N)       # only with --struct-randomization
  └─ phase_cpu_port(seed=N)                   # only with --cpu-port
```

It is passed explicitly to three phases. It does **not** call `random.seed`,
does not reach `ObfuscationTransformer`, and has no effect on a default build
where those three phases are off. The environment fallback is implemented in
`main()` and prefers the explicit flag.

### 3.3 `--build-id`: the lowering-kernel seed

```
argparse --build-id STR
  └─ phase06_package: recorded in the build manifest / signature sidecar
  └─ if --pytoc and --lowering:
         seed = STR.encode() or os.urandom(16)
         build_kernel(..., seed)
```

The kernel generator derives per-build symbol names and its operation map from
this seed, so two builds with the same `--build-id` lower identically **on the
`--pytoc` path**. The rest of the artefact still draws keys and names from
other sources. An empty `--build-id` means fresh entropy, not a stable default.

**Measured.** With `--lowering io --pytoc --build-id bid-test-001`, two builds
(~16 s each) produced the same kernel module name
`_nxk_7f07964c0267.cpython-313-x86_64-linux-gnu.so`; `bid-other-002` produced
`_nxk_709896e7f218…`. The kernel swap had been silently skipped because
`build.py` used `ast.Name` while importing the module as `_ka`; that is fixed,
and the swapped artefact runs with the native `_nxk_*` import (verified).

### 3.4 `--lock-hwid`: not a build seed

Despite the help text ("seeds the build deterministically"), the code uses the
HWID string for two things:

1. `watermark_seed = HWID.encode()`; `sha256(watermark_seed)` seeds
   `generate_polymorphic_map` and the poly-VM context.
2. A licence registration for the target HWID (`deployer.add_license`).

The blob key is still `secrets`/`os.urandom`; per-string keys are still
`secrets`; the build timestamp is still wall-clock. The HWID is usually
low-entropy and often visible to the customer. It is not a secret and is not a
substitute for a cryptographic seed.

**Measured.** Two `--fast --layers 1 --lock-hwid TEST-HWID-001` builds took
25 s and 24 s and produced 3,701,015 and 10,105,871 bytes with different
hashes. Both artefacts ran. The flag seeds the loader map, not the build.

### 3.5 `--pin-structure`: a debugging pin, not a reproducible build

`build_project()` seeds `random` with `0x5EED`, installs a structure RNG, fixes
the marker token and part prefix, regenerates variable names, and fixes the
build timestamp to `1700000000`. Key material is explicitly not pinned. The
flag's help says "artefacts are not byte-identical"; §5 confirms it.

### 3.6 What is **not** seeded

These are drawn from `secrets` or `os.urandom` and are unaffected by any flag:

- the hybrid-loader blob key and its XOR shares;
- per-string ChaCha20 keys and nonces;
- section-split nonces and the effective-key salt;
- VM seeds (`secrets.randbelow(256)`);
- the runtime key (`secrets.token_hex(16)`);
- the random `build_id` used when `--build-id` is absent.

`EMITTER_PIPELINE.md` measures roughly **3,650 `secrets` draws per build**. A
reproducible build needs one RNG threaded through the emitters, not a seeding
patch on top.

---

## 4. Consumers and their seed source

| Consumer | Seed source | Effect |
|---|---|---|
| `random`-based AST transforms (`SymbolRenamer`, `EnhancedJunkInserter`, opaque predicates) | global `random.seed(--seed)` | Same seed → same choices; different seed → different structure |
| `SemanticDecoyApiInjector` | `--seed` via options | Decoy count/names |
| `AntiReaInjector` | `--seed` via options | Chaff and decoy call graph |
| `inject_adversarial_code` (phase09) | `--seed` or `secrets.token_bytes(4)` | Prompt injection / dead code |
| `ProvenancePoisoner` (phase10) | `--seed` or `secrets.token_bytes(4)` | Poisoned provenance |
| `LLMFingerprinter` | `--seed` or `secrets.randbits(32)` | Fingerprint model/placement |
| `ReasoningLoopInjector`, `FunctionIntentObfuscator` | `_stage_seed(--seed)` | Stage-local stream |
| `StringLiteralObfuscator` | `secrets` (unpatched on the CLI path) | **Not reproducible with `--seed`** |
| `obfuscate_with_speculation` | `--randomization-seed` or `0xCAFEBABE` | Speculation shapes |
| `phase_struct_randomization` | `--randomization-seed` | Stack/heap/register randomisation |
| `phase_cpu_port` | `--randomization-seed` | CPU-port variants |
| `build_kernel` | `--build-id` or `os.urandom(16)` | Lowering-kernel symbols |
| `generate_polymorphic_map` / poly-VM | `sha256(--lock-hwid)` or `secrets` | Loader map/VM only |
| Blob key, section keys, runtime key | `secrets` / `os.urandom` | Cryptographic material, never seeded |

---

## 5. Determinism experiments

All builds used `tests/fixtures/portable/constructs_source.py` (2,635 bytes;
dataclass, `match`, closures, generators, descriptors, async). AST-only builds
used `--skip-irgen --skip-llvmgen --skip-encrypt --skip-relay --skip-extras`;
the O4 runs also used `--phase2-only none` to remove the phase-2 default
features. Loader builds used `--skip-cloud --layers 25`.

### 5.1 Same `--seed`, three times (after the wiring fix)

| Run | Bytes | SHA-256 (first 16) |
|---|---|---|
| 1 | 29,802 | `50ad8c8007d95dc4` |
| 2 | 29,802 | `50ad8c8007d95dc4` |
| 3 | 29,802 | `50ad8c8007d95dc4` |

**Byte-identical.** With the phase-2 defaults left on (no
`--phase2-only none`), two runs were also identical: 33,170 bytes,
`afec29a51c5de499…`. A different seed (`43`) produced 32,911 bytes and a
different hash, which is the expected direction.

Before the fix the same experiment gave 29,805 / 29,800 / 29,805 bytes. The
first differing line was the string-encryption key:

```
_nx_k = bytes([142, 235, 0, 31, ...])   # run A
_nx_k = bytes([196, 191, 216, 51, ...]) # run B
```

The cause was §3.1: the transformer had no seed, so its `secrets` patch never
ran. Passing `seed=` into `build_pipeline` removed the difference; no key
material was weakened (keys are still per-build random when no seed is given).

### 5.2 No seed, three times

| Run | Bytes | SHA-256 (first 16) |
|---|---|---|
| 1 | 30,099 | `373da0fd319d1c72` |
| 2 | 30,904 | `cff66d71fbe3a193` |
| 3 | 28,973 | `f5c10ff461e6a576` |

Unseeded builds vary by hundreds of bytes and by transform choices. `--seed`
now makes them reproducible for the same payload, tool version, and flag set;
without it the per-build diversity is preserved.

### 5.3 `--randomization-seed` alone

Two O4 runs with `--randomization-seed 42` produced 35,840 and 37,009 bytes and
different hashes. This is expected: the flag reaches none of the default AST
phases.

### 5.4 `--pin-structure`, two loader builds

Two `--fast --layers 25 --pin-structure` builds took 39 s each and produced
1,882,254 and 1,882,385 bytes with different hashes. Structure is pinned; key
material is not. The flag's help says exactly this.

### 5.5 `--skip-obfuscate` is the true no-op

A `--skip-obfuscate --skip-irgen --skip-llvmgen --skip-encrypt --skip-relay
--skip-extras` build produced 2,635 bytes, byte-identical to the source
(`diff` clean). This — not `--opt-level 0` — is the copy path.

### 5.6 `--opt-level 0` is not a copy

O0 with `--phase2-only none` produced 6,282 bytes from a 2,635-byte source.
Always-on passes renamed symbols (`_nixon_…`), added a checksum table and
`_nx_verify`, and sealed strings. The ladder is off; the pipeline is not.

---

## 6. Security implications

### 6.1 Seeds are not keys

No key is derived from `--seed`, `--randomization-seed`, `--build-id`, or
`--lock-hwid`. Blob keys, string keys, section keys, and the runtime key come
from `secrets`/`os.urandom`. Do not describe a seed as a secret, and do not
derive a key from one.

### 6.2 A fixed seed reduces diversity

A known seed makes the structural choices reproducible: transform order, decoy
placement, rename scheme, dead-code shapes. If an attacker knows the payload,
the tool version, and the seed, they can reproduce the structure without
running the build. That does not reveal the keys, but it removes the
per-build diversity the seed was meant to coordinate.

**Production guidance:** do not ship `--seed` or `--randomization-seed` in the
customer build path. Keep them for a debug/reproducibility channel. If a
release needs both reproducibility and diversity, separate the two: a
reproducible build is a debugging artefact, not the customer artefact.

### 6.3 Seed reuse creates fingerprints

Two customers built with the same `--seed` share the structural fingerprint:
the same rename scheme, decoy templates, and transform order. That lets an
attacker who has one build predict the other's structure. It is a
correlation risk, not a key compromise.

### 6.4 `--build-id` is public

The build id is recorded in the manifest/signature sidecar and embedded in the
loader (`_NX_BUILD_ID`). It salts the effective key (`xor(key,
sha256(build_id))`), but it is **not** secret: an attacker who extracts it
still needs the raw key. Its security function is integrity — a tampered build
id produces the wrong key — not confidentiality. Do not treat it as a secret.

### 6.5 `--lock-hwid` is low-entropy and not a key

A HWID is often derived from visible hardware identifiers. Using it as a PRNG
seed for the polymorphic maps makes those maps reproducible for a known HWID;
it does not protect the payload key. The licence registration is a separate
access-control function.

### 6.6 Environment leakage

`SEED` and `NIXON_SEED` are environment variables. They appear in CI logs,
process listings, container metadata, and crash dumps. They are not secrets.
The same is true of `--seed` on a command line. Do not put a credential in a
seed variable.

### 6.7 What an attacker gains from a known seed

| Capability | With a known seed |
|---|---|
| Reproduce transform order and decoy placement | **Yes**, for the same payload/version |
| Reproduce symbol rename scheme | **Yes** — the transformer patches `secrets` while seeded |
| Derive the blob key | **No** — `secrets`/`os.urandom` |
| Derive string keys | **No** — the seed reproduces the per-string key, it does not reveal a master key |
| Bypass licence binding | **No** — token key material is separate |
| Predict the next build's keys | **No** — not seeded |

---

## 7. Known gaps

- The `--pytoc --build-id` kernel path is traced statically, not measured
  end-to-end in this audit.
- The RNG inventory is not exhaustive. `EMITTER_PIPELINE.md` records ~3,650
  `secrets` draws per build; a full call-site census would be a separate task.
- `--pin-structure` remains partial by design: it pins structure, not key
  material (two builds differed). `--seed` is now fully deterministic for the
  same payload/tool/flag set; see §5.1.

---

## 8. Recommendations

1. **Never use a seed as a key.** Keep key material in `secrets`/`os.urandom`
   or a KMS; the licence/token path already does.
2. **Do not enable seeds in production builds.** Use them only for a
   reproducible debug channel, and label those artefacts as such.
3. **Do not reuse one seed across customers.** If a customer build needs
   structural stability, derive a per-customer structural seed from the
   customer identity and keep it separate from key material.
4. **Treat `--build-id` as public metadata.** Pin it per release, not per
   customer; use `--customer-salt` or `--licence-token` for binding.
5. **Do not rely on `--lock-hwid` as a seed.** It seeds the loader map only and
   its input is low-entropy.
6. **If reproducibility is required**, use `--seed` and record the payload
   hash, tool version, and exact flag set. `--seed` now passes through the
   transformer; `--pin-structure` is still structure-only, and key material is
   never derived from a seed.
