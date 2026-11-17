# What is ON by default — measured, 2026-11-17

Every claim below was **measured** by building a payload and inspecting the
emitted artefact, not inferred from the flag definitions. Three builds were
compared: default (no flags), `--fast`, and `--package all` (max profile).

Payload: a small module with a class, two methods, a function, a string
API token, a bytes salt and a URL. All three builds produced a working
artefact (`AUDIT f3a53b0870bbcf1a`).

---

## 1. Protection layers: measured presence in the artefact

| layer | default | `--fast` | `--package all` | how it was measured |
|---|---|---|---|---|
| identity gate | **ON** | ON | ON | `[BLOCKED] identity` present |
| self-check (Merkle+HMAC) | **ON** | ON | ON | `_nx_self_check` + stamped `_NX_SELF_CK` |
| interpreter-integrity gate | **ON** | ON | ON | `interpreter-integrity` reason strings |
| section pack (sealed payload) | **ON** | ON | ON | `_NX_SECTION_PACK` non-empty |
| moving decryption | **ON** | ON | ON | `_nx_section_stream` helper + call |
| honeypayload (decoy pack) | **ON** | ON | ON | `_NX_HONEY_PACK` present |
| split bootstrap (Shamir) | **ON** | ON | ON | `_NX_SPLIT_BOOTSTRAP_ARMED = True` |
| strict detections (kill vs warn) | **ON** | **OFF** | ON | gate emits `if True:` vs `if False:` |
| expire gate | off | off | off | `_NX_EXP_DATE` absent |
| geo gate | off | off | off | `_NX_GEO` absent |
| one-shot | off | off | off | `_NX_ONE_SHOT` absent |
| hwid-lock | off | off | off | `_NX_HWID_LOCK = 'DISABLED'` |
| watermark | off | off | off | `_NX_WATERMARK_GATE = "DISABLED"` |
| trial gate | ON | ON | ON | `_NX_TRIAL_GATE` present (no-op without `trial=`) |

Plaintext secrets in the artefact: **0/3 in all three builds**. Payload
identifiers left in the artefact: **0/5 in all three builds**.

## 2. The C transformation layer

`scripts/c_transform.py` has seven transforms, **all default-on** when the
layer runs:

| transform | default |
|---|---|
| string encryption | ON |
| opaque predicates | ON |
| junk functions | ON |
| shuffle locals | ON |
| dead blocks (function outlining) | ON |
| **subset-sum opaque predicates (NP-hard)** | ON |
| **multi-round MBA substitution** | ON |

Measured on a real build: the log shows `C transform: [...]` — the layer
runs. It is reached from `build_local_cython`, which is the local native
path.

**Caveat (real):** the call is wrapped in `try/except` that prints
`C transform skipped: …` and *continues the build*. A failure degrades
silently to untransformed C. Verified the transforms themselves work
(`gcc -fsyntax-only -std=c99` passes, 3 subset-sum + 1 MBA applied on a
sample). The silent-skip is a fail-open worth tightening.

## 3. What needs a flag (and why)

| capability | flag | why not default |
|---|---|---|
| expiry | `--access expire=YYYY-MM-DD` | needs a date from the operator |
| geo-fence | `--access block-countries=…` | needs a policy from the operator |
| one-shot | `--access one-shot` | destructive: deletes the artefact |
| HWID lock | `--access hwid=… hwid-lock` | needs a machine id |
| trial | `--access trial=7d` | needs a duration |
| watermark | `--access watermark=…` | per-customer identifier |
| **keyless string sealing** | `--transforms string-key-env=NAME` | needs an env shard at build **and** run time |
| internal method rename | `obfuscate --rename-internal` | breaks execution in a full stack (measured) |
| cloud native compile | `--package native` | needs build-farm credentials |

## 4. Findings from this audit

### 4.1 `--fast` works, and it is the only thing that weakens a gate

`--fast` flips the strict-detection gates from kill (`if True:`) to warn
(`if False:`). Everything else — identity gate, self-check, section pack,
moving decryption, honeypayload, split bootstrap — stays on. The artifact
is 292 bytes smaller and behaves identically on a clean host.

That is a reasonable design, but the `--help` text says "reduced-protection
profile", which undersells how much stays on and oversells how much turns
off. Worth rewording to name the one thing it changes.

### 4.2 `--package all` does not put its artifacts where it says to ship

Measured: `--package all` writes `p_protected_Packed.py` and
`p_protected_Packed_Stego.py` (3.3 MB) into the **source directory**, while
`dist/` receives only the plain hybrid loader. The build then prints:

> Ship only `…/dist` — the source directory is a different trust boundary

So the stego and packed variants land in the directory the operator is told
not to ship. They do run correctly (verified: `AUDIT f3a53b0870bbcf1a`),
but they are easy to miss or to ship by accident from the wrong place.

### 4.3 The C transform fails open

`except Exception: print("C transform skipped")` then continue. A broken
transform ships untransformed C with only a log line. Every other
default-on protection in this project fails **closed**; this one does not.

### 4.4 Default string sealing ships its own key

Covered in the benchmark report (Part 4): the default inline-key mode lets
an analyst — including an LLM — call the shipped decoder. Measured 4/4
secrets recovered. `--transforms string-key-env=NAME` fixes it (0/4), but
it is opt-in because it needs an env shard at run time.

## 5. Recommended maximum-security command

```bash
NX_SEAL_SHARD=$(openssl rand -hex 32)        # keep this out of the artefact

python3 -m obfuscator.core.pipeline build payload.py \
    --skip-cloud --in-place \
    --package all \
    --transforms string-key-env=NX_SEAL_SHARD \
    --access expire=2027-01-01 \
    --access block-countries=RU,KP \
    --access hwid=<machine-id> hwid-lock \
    --access trial=30d \
    --licence token=licence.json
```

What that adds over the default: keyless string sealing, an expiry, a geo
policy, a machine lock, a trial window and token-bound key material. What
it keeps from the default: identity gate, self-check, interpreter gate,
section pack, moving decryption, honeypayload, split bootstrap, strict
detections, and the full C transform layer.

Do **not** add `--fast` for anything you care about: it is the one flag that
turns a kill into a warning.

## 6. Honest limits of this audit

* The marker checks are string presence in the emitted artefact. A marker
  present but unreachable would pass. The E2E tests
  (`test_identity_gate`, `test_access_gates_sectioned`,
  `test_payload_fidelity`) cover reachability for the gates they name.
* `--package native` (cloud Cython) was not exercised: it needs build-farm
  credentials. The local path (`build_local_cython`) was exercised and the
  C transform runs there.
* The C-transform fail-open was found by reading the call site; I did not
  force a transform failure end-to-end to watch it degrade.
