# Protection map — what is on, by default and at ABSOLUTE maximum

Measured 2026-11-18. Every "ON" below was verified by building a payload and
grepping the emitted loader for the gate's marker, or by reading the CLI's
resolved arguments — not inferred from flag names.

---

## 1. Default build (`build payload.py`, no flags)

### Always ON — no flag needed

| # | protection | how it works | marker |
|---|---|---|---|
| 1 | **Identity gate** | refuses to init unless the artefact is the script the interpreter was pointed at (`__name__` + `__file__` == `argv[0]`) | `[BLOCKED] identity` |
| 2 | **Self-check** | Merkle root + per-build HMAC over its own bytes; dies 137 if any byte changed | `_NX_SELF_CK` |
| 3 | **Interpreter-integrity gate** | detects hooked builtins, wrapped `zipfile`, external `sitecustomize` | `interpreter-integrity` |
| 4 | **Section pack** | payload split into N independently-keyed sealed sections | `_NX_SECTION_PACK` |
| 5 | **Moving decryption** | decrypts one section at a time, zeroes the buffer before the next | `_nx_section_stream` |
| 6 | **Honeypayload** | plausible decoy pack sealed alongside the real one | `_NX_HONEY_PACK` |
| 7 | **Split bootstrap** | Shamir n=3,k=2 key split with a fragmented decoder | `_NX_SPLIT_BOOTSTRAP_ARMED` |
| 8 | **Strict detections** | env detections **kill** rather than warn (`--fast` disables this one thing) | `if True:` |
| 9 | **Trial gate scaffold** | emitted and enforced; no-op unless `trial=` given | `_NX_TRIAL_GATE` |

### AST transforms — all ON by default

| transform | what it does |
|---|---|
| `cfg_flatten` | control-flow flattening |
| `opaque_predicates` | always-true/false branches |
| `bogus_exceptions` | unreachable exception paths |
| `mba_subs` | mixed boolean-arithmetic substitution |
| `fragment_strings` | ChaCha20 string sealing (inline key by default) |
| `unicode_ids` | identifiers to Unicode babel names |
| `symbol_rename` | symbol renaming |
| `strip_meta` | strips docstrings/metadata |
| `split_vars` | variable splitting |
| `unfold_constants` | constant unfolding |
| `enhanced_junk` | junk code |
| `break_decompiler` | decompiler-hostile constructs |
| `code_checksums` | per-function checksums |
| `obf_calls` | obfuscated call indirection |
| `exception_flow` | exception-based control flow |
| `residue_random` | randomised literal residue |
| `dynamic_code` | dynamic code generation |
| `temporal_redundancy` | 3-call check on provably pure functions |
| `reflection` | reflection-based dispatch |
| `func_transform` | function-level transforms |

### Counter-REA — ON by default at **maximum**

| layer | default |
|---|---|
| `anti_rea` | ON |
| `anti_rea_level` | **maximum** |
| `anti_rea_compliance_bait` | ON |
| `anti_rea_cognitive_armor` | ON |
| `anti_rea_classifier_bait` | ON |

### The Cython + custom-C layer (native path) — ON by default

This is the layer that sits *between* Python and the machine code, and it is
the one that makes the artefact expensive to reverse. It runs in three
stages, and stage 2 is the custom layer this project built.

```
payload.py
   │
   │  1. CYTHON  (python -m cython -3)
   │     language_level=3, embedsignature=False, emit_code_comments=False
   ▼
payload.c                       <- Cython-generated C
   │
   │  2. C TRANSFORM LAYER  (scripts/c_transform.py)  ** custom **
   │     7 transforms, polymorphic per build, all ON
   ▼
payload.c  (transformed)
   │
   │  3. gcc -shared -O3 -flto -fvisibility=hidden
   │     -fvisibility-inlines-hidden -fno-semantic-interposition
   ▼
payload_module.so / .pyd / .dylib
```

**Stage 2 is the important one.** An analyst who decompiles the `.so` finds
*transformed* C, not Cython's output: the Cython idioms they would
pattern-match against are gone.

| # | C transform | what it does to the C | measured on a default build |
|---|---|---|---|
| 1 | **string encryption** | XOR-seals every `__pyx_k_*` string array and emits a decrypt loop; skipped cleanly if the file has no Cython string table | applied |
| 2 | **opaque predicates** | wraps selected `if` conditions with an always-true algebraic expression (e.g. `((x*x+3*x+7) & 1) == 0` with `x` fixed even), AND-ed with the real condition so semantics are unchanged | **45** predicates |
| 3 | **junk functions** | injects static C functions that look real, are never called, and must each be reversed to prove dead — they appear alongside real code in Ghidra/IDA | **3** |
| 4 | **shuffle locals** | renames Cython's `locals_N` declarations to per-build names, breaking cross-build pattern matching | applied |
| 5 | **dead blocks** | inserts self-contained computation blocks inside function bodies that feed nothing — **function outlining / interprocedural obfuscation**, so real block boundaries are indistinguishable | **3** |
| 6 | **subset-sum predicates (NP-hard)** | embeds a random subset-sum instance; the C verifies it at run time via a 4096-entry DP table. Proving the branch is always-taken requires **solving the subset-sum instance** | **3** |
| 7 | **multi-round MBA** | replaces integer constants with nested mixed-boolean-arithmetic expressions that expand exponentially to simplify | **3** |

Measured output on a real default build:

```
C transform: ['junk-functions(3)', 'opaque-predicates(45)', 'dead-blocks(3)',
              'subset-sum(3)', 'mba-substitution(3)']
```

On the ABSOLUTE build: `opaque-predicates(83), mba-substitution(4)` — the
counts vary per build because the transforms are **polymorphic by seed**.

**Fails closed** (audit 2026-11-17): the C transform used to swallow its own
exceptions and continue, shipping untransformed C with only a log line. It
now aborts the build on either a transform failure or an empty transform
list, so an artefact never ships with this layer silently missing.

**The same layer runs on the farm.** `scripts/c_transform.py` is uploaded to
each runner, and the generated driver does `cythonize` -> `transform_file`
-> `setup(build_ext)`, seeded from the payload hash so all three OSes apply
the *same* transform. Verified live: the Windows runner reported
`opaque-predicates(62)`, macOS `opaque-predicates(59)`.

### Native packaging — default

| | default |
|---|---|
| Cython compile | **ON** (sectioned build arms it) |
| output | current-OS blob only: `.so` on Linux, `.pyd` on Windows, `.dylib` stored/loaded-as-`.so` on macOS |
| fallback | bytecode blob kept |

### OFF by default (needs a flag)

| capability | flag |
|---|---|
| expiry | `--access expire=YYYY-MM-DD` |
| geo-fence | `--access block-countries=…` |
| HWID lock | `--access hwid=… hwid-lock` |
| trial duration | `--access trial=7d` |
| one-shot | `--access one-shot` |
| watermark | `--access watermark=…` |
| driver check | `--access driver-check` |
| name gate | `--access name-gate` |
| bind-mac | `--access bind-mac` |
| hostguard | `--access hostguard` |
| kod | `--access kod` |
| licence token | `--licence token=FILE` |
| **keyless string sealing** | `--transforms string-key-env=NAME` |
| stego | `--package stego` |
| deep packaging | `--package layers=N zips=N` |
| cross-OS blobs | `--package native platform=github` |
| lowering families | `--lowering …` |
| data / function-intent / speculation | `--transforms data function-intent speculation` |

---

## 2. ABSOLUTE maximum — what it adds to the default

Measured on a real build with the farm (run `44218449500`). **19 settings
change; nothing is turned off.**

| setting | default | ABSOLUTE |
|---|---|---|
| `section_count` | 4 | **8** |
| `layers` | none | **25** |
| `zips` | none | **3** |
| `native` | False | **True** |
| `platform` | auto | **github** (3-OS farm) |
| `lowering` | none | **all 14 families** |
| `tx_data` | False | **True** |
| `tx_function_intent` | False | **True** |
| `tx_speculation` | False | **True** |
| `tx_string_key_env` | None | **NX_SEAL_SHARD** |
| `trial` | — | **7d** |
| `expire` | — | **2027-12-31** |
| `hwid` + `hwid_lock` | off | **on** |
| `kod` | off | **on** |
| `driver_check` | off | **on** |
| `name_gate` | off | **on** |
| `bind_mac` | off | **on** |
| `webhook` | — | alerts URL |
| `block_countries` | — | **RU,KP** |
| `vm_threshold` | 50.0 | **65.0** |
| `watermark` | — | **NX-001** |
| `licence` | none | **token + env-only + bootstrap-encrypted + chain** |

### Gate markers measured in the resulting artefact

| gate | default | ABSOLUTE |
|---|---|---|
| identity | ON | ON |
| self-check | ON | ON |
| interpreter-integrity | ON | ON |
| section pack | ON | ON |
| moving decryption | ON | ON |
| honeypayload | ON | ON |
| split bootstrap | ON | ON |
| trial gate | ON (no-op) | ON (**7d**) |
| expiry gate | off | **ON** |
| HWID lock | off | **ON** |
| geo gate | off | **ON** |
| watermark | off | **ON** |
| licence token gate | off | **ON** |
| one-shot | off | off (deliberately excluded) |
| native blobs | current OS | **win + mac + linux** |
| C transform | all 7, per-OS | **all 7, on all 3 OS runners** |

---

## 3. What ABSOLUTE still does NOT turn on, and why

| item | why excluded |
|---|---|
| `--access one-shot` | self-destructs the artefact after one run — breaks re-runs. Add it only for burn-after-use payloads. |
| `--package native-only` | removes the bytecode fallback entirely. Stronger, but a farm failure then bricks the artefact for that OS. |
| `--fast` | **weakens** — turns every kill into a warning. Never in a max build. |
| `--public` | nukes the build repo after building (Flash Mode). Operational, not a protection. |
| `--debug-dump-raw` | writes the rename log — the exact leak found in the 2026-11-14 benchmark. |
| `--pin-structure` | debugging aid: pins emitter draws so two builds match. Reduces per-build polymorphism. |
| `--exclude …` | nothing is excluded at ABSOLUTE; every shield family is on. |
| `--tor` / `--tor-proxy` | build-host privacy only, not artefact security. |
| `allow-countries` | mutually exclusive with `block-countries` in practice; ABSOLUTE uses block. |

---

## 4. The one asymmetry worth knowing

`--transforms string-key-env=NAME` seals the **fallback payload's** strings
with a key derived from an env shard, so the artefact alone cannot decrypt
them. Measured against a model: **4/4 secrets recovered with the inline key,
0/4 with the shard.**

But the **farm driver** still seals with the inline key — the shard is not
threaded through the cross-OS build. So on ABSOLUTE:

* the local blob and the fallback source: **shard-protected**
* the farm blobs (win/mac): **inline-key protected** (C transform + inline seal)

That is the remaining gap to a fully uniform maximum.
