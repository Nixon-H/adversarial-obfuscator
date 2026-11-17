# AI-layer benchmark — GLM 5.3 Flash, 2026-11-17

Attacker: **GLM 5.3 Flash** (the session model itself; no Kern, no Mistral).
Target: max-profile local build (`--package all --skip-cloud --in-place`):
layers=25 + zips=3 + stego, section sealing + moving decryption, split
bootstrap, strict detections, anti-REA at maximum, identity gate,
interpreter-integrity gate, self-check.

Payload (`harvest.py`): three extraction targets an analyst wants —

| target | value |
|---|---|
| credential | `SK_BENCH_9c04d1f3-bench-secret` |
| infrastructure | `https://api.bench-target.example/v2/exfil` |
| keying material | `bench-salt-4411` |

## Positions

* **A — no licence**: artefact as shipped.
* **B — `--licence salt=`**: per-customer salt embedded by design.
* **B2 — `--licence token=`**: Ed25519-signed token, pinned public key.
* **C — capture-route hunting**: runtime hooks against the loader.

## Attack log

### A1 — static string hunt: FAIL (defender wins)

`grep` for every target and every payload identifier across the 89 KB
artefact: **zero hits**. Renaming, string sealing and the section pack
removed all plaintext.

### A2 — structural analysis: key material visible (expected)

Both XOR shares (`_BLOB_S0`/`_BLOB_S1`), the build id and the pack
literal are visible in the artefact. For a no-licence build this is by
design: the artefact must run standalone, so every key ingredient ships.

### A3 — foreign-exec extraction: SUCCESS → FIXED

`exec(artifact_src, {"__name__": "not_main_loader"})` skipped the entry
point, survived every gate, exposed the reconstructed key (`_NX_EFF_KEY`)
and the loader's own HMAC-verified section join in the namespace. Peeling
two layers (section pack → marshal → zero-width bootstrap) reached the
payload stage and harvested all three targets from its globals.

**Root cause**: everything except the `if __name__ == "__main__"` entry
initialised on import; no gate refused a foreign exec.

**Fix (shipped)**:
* `IDENTITY_GATE_TOP` in the shipped loaders: `__name__` must be
  main-ish AND `__file__` must match `sys.argv[0]` — a foreign exec has
  neither. Kill: exit 2 before any state exists.
* `IDENTITY_GATE_STAGE` in every interior packaging bootstrap
  (EXEC_TEMPLATE, ZIP_LOADER_TEMPLATE, stego): name-only check (those
  stages run exec'd/runpy'd inside the artefact's own globals, where a
  file/argv check is impossible), still fatal at every layer.

**Verified**: exec now dies with `[BLOCKED] identity: not a direct
execution (exit 2)`; the namespace holds nothing (no key, no pack, no
join). Fake `__name__="__main__"` also dies (no `__file__`/argv match).

### A4 — pure-offline decryption (loader never exec'd): SUCCESS on A/B, FAIL on B2

Reading the loader source (allowed) and reimplementing the derivation in
the attacker's own code: shares → build-id mask → per-section keys
(`sha256("nx-section-key:" + master + i₄ + nonce)`), keystream HMACs
verified offline, pack joined, compression envelope + marshal + zero-width
layers peeled, transformed payload exec'd, its own string-table decrypt
runs, all three targets harvested.

* Position A: **expected** — no-licence builds derive keys locally by
  design; the honest boundary is documented in MAXIMUM_SECURITY.md.
* Position B (`salt=`): **finding** — the salt ships in the artefact, so
  the customer mask (`sha256("nx-customer:" + salt)`) is derivable
  offline. `salt=` is a per-customer **differ**, not a secret; the CLI
  help now says so explicitly.
* Position B2 (`token=`): **finding → FIXED** — the build embedded the
  token's key material as the "customer salt", making the token
  decorative (the artefact ran without it; an offline analyst derived the
  mask from the embedded literal). The build now splits **seal salt**
  (build side: the token's key material) from **embedded salt** (loader
  side: empty), and `_key_binding_source` no longer substitutes the
  material into the emitted source in licence mode (it leaked as a dead
  string literal).

**Verified on the fixed B2**: token material absent from the artefact;
without the token the artefact dies (rc 137) after printing
`licence token required: set NIXON_LICENCE or place licence.json beside
the artefact`; with the token it runs; offline guesses (no mask /
empty-salt mask) fail the section-0 HMAC — **decryption impossible
without the token**. A forged token is now pinned and refused with
`licence token does not match the pinned token` (the hybrid loader pins
the token payload hash the same way the packed loader always did).

### C — capture routes: BLOCKED (all)

| route | result |
|---|---|
| PYTHONPATH sitecustomize wrapping `ZipFile.__init__`/`read` | rc 3, `[BLOCKED] interpreter-integrity`, **no capture.log** |
| plain external sitecustomize (dodges zipfile) | rc 3, `startup-hook-external` |
| in-process exec probe | refused rc 2 by the identity gate; loader's excepthook poisoning never installs |

### D — loader-code tamper: SUCCESS → FIXED

Before the fix: flipping one byte **inside the loader code** (85% of the
file, outside the HMAC'd section pack) left the artefact running
normally — only the pack was verified.

**Fix (shipped)**: the hybrid loader now carries a Merkle+HMAC self-check
(the same construction the packed loader always had): the build stamps
the Merkle root, an HMAC (per-build secret) and — for bound builds — the
licence-keyed anchor into the final bytes; the runtime re-hashes every
line except the value lines and the token pin **before any key material
is reconstructed**. Stamping is the last content step (variant writer),
idempotent, and a stamping failure fails the build loudly (a half-stamped
artefact is worse than no artefact).

**Verified**: 11-offset tamper sweep — every parseable flip dies with
`Self-check error: merkle …` (rc 137) before the payload runs; the
non-parseable flips are refused by the interpreter.

## Scorecard

| position | attack | before | after |
|---|---|---|---|
| A | static strings | blocked | blocked |
| A | foreign-exec extraction | **breach** | blocked (exit 2) |
| A | loader-code tamper | **breach** | blocked (137) |
| A | offline reimplementation | breach | breach — **documented boundary** (keys ship by design) |
| B | offline w/ embedded salt | breach | breach — documented: `salt=` is a differ, not a secret |
| B2 | offline w/o token | **breach** (token decorative) | **blocked** (HMAC mismatch) |
| B2 | run w/o token | ran | dies (137) with reason |
| B2 | forged token | silent 137 | refused with pin mismatch |
| C | capture routes | blocked | blocked |

## Residual boundaries (documented, not hidden)

1. **No-licence builds**: every key ingredient ships; an offline analyst
   can always reimplement the crypto. The defence for secret-bearing
   payloads is token binding.
2. **`salt=` mode**: per-customer differentiation only.
3. **Exec with 3-way spoofing**: an attacker who deliberately fakes
   `__name__`, `__file__` AND `sys.argv[0]` in their own process passes
   the identity gate; the self-check then still runs and the payload
   runs — in the attacker's process, where they could hook anything.
   In-process extraction by a process the attacker fully controls is the
   standard software-protection boundary (same class as memory-reading).
