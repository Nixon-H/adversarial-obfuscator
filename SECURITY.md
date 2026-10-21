# Security Policy — shadow-compiler

## Scope

In scope: the builder (`scripts/build.py`, `obfuscator/`, `irgen/`,
`llvmgen/`, `native/`, `scripts/`), the artifacts it emits, and the
runtime loader gates baked into those artifacts (kill ladder, VM score,
trial/HWID, watermark, frozen-stdlib snapshot, stdlib-audit, audit-hook
plant detector, BYOVD driver gate). See `THREAT_MODEL.md` for the
attacker-by-attacker breakdown.

Out of scope: research/experimental flags (FHE-VM, iO, ZK, GPU/TEE/SGX,
distributed execution, red-team harnesses) — present in `--help` but not
covered by this policy or the test-suite.

## Supported versions

Builder and payloads: Python **3.10–3.14**
(`obfuscator/nyser.py:50` `SUPPORTED_MINORS`,
`obfuscator/py_matrix.py:29` `SUPPORTED`, floor check
`sys.version_info < (3, 10)` in `scripts/build.py`). CI exercises the
full matrix 3.10/3.11/3.12/3.13/3.14 (`.github/workflows/ci.yml`).
Only the latest commit on `master` receives fixes; older checkouts are
unsupported.

## Reporting

Do not open a public issue for a suspected vulnerability. Contact the
repository maintainer privately with: affected commit, reproduction
steps, and impact assessment. Allow reasonable time for a fix before
any public disclosure. (No dedicated security contact or bug-bounty is
configured for this repository — this paragraph is the whole process
until one is.)

## Hardcoded-secret policy

- **No secrets in source.** Signing keys, chain secrets, and tokens are
  passed via environment (`NIXON_SIGN_KEY`, `--sign-key-env VAR`,
  `scripts/artifact_sign.py:51`) or explicit testing-only flags
  (`--key-hex`, marked "testing only" in `--help`). Never commit a key,
  token, or hex secret to the tree, docs, or tests.
- **Artifact signing keys.** Three environment variables are
  recognised, in this order of preference:
  - `NIXON_ARTIFACT_ED25519_KEY` — the farm's **Ed25519 private key**
    (hex 32-byte seed). Used for signing when present.
  - `NIXON_ARTIFACT_ED25519_PUBKEY` — a pinned **Ed25519 public key**
    (hex 32 bytes) the verifier trusts.
  - `NIXON_ARTIFACT_ED25519_KEYS` — a JSON map of farm id → hex public
    key, for a verifier that trusts several farms.
  The verifier holds **no secret**: it can check an artifact and cannot
  mint one. The legacy shared-HMAC key (`NIXON_ARTIFACT_KEY_HEX`,
  `NIXON_SIGN_KEY`) still works and is used only when no Ed25519 key is
  configured. See `docs/adr/0005-artifact-authenticity.md`.
- Build keys are generated per build (`os.urandom` /
  `secrets.token_bytes`, e.g. `obfuscator/watermark_gate.py:build_watermark_context`)
  and embedded only in the artifact that needs them — never logged, never
  written to shared sidecars. The section-split module
  (`obfuscator/section_split.py`) mints per-section nonces the same way
  and is wired into the hybrid loader as the opt-in `--section-split`
  flag; it is not the default.

## Enforceable rules (security invariants)

These are encoded as tests in `tests/test_security_invariants.py` and
must hold on every commit. CI runs them like any other test file.

1. **Untrusted input never selects an executable path.** Emitted loader
   snippets (`vm_score`, `driver_blocklist`, `audit_hook`, `trial_bind`,
   `watermark_gate`, `frozen_snapshot`) contain no `exec(`/`eval(` calls
   over input-derived names. Test (a).
2. **No driver loading / IOCTL anywhere.** `NtLoadDriver`,
   `CreateService`, `DeviceIoControl` are absent from all non-test
   sources (Python + native). Detection is read-only enumeration plus
   blocklist compare. Test (b).
3. **Failed integrity never downgrades.** Tampered snapshot or stdlib
   fingerprints yield `mismatch` (fail-closed via `_nx_kill`), never a
   pass. Test (c).
4. **Missing signal is not safety.** Empty findings / names / tokens /
   markers never produce an `ok`/`True` trust verdict from the real
   gate functions. Test (d).
5. **Detection has no privilege-escalation side effects.**
   `SeDebugPrivilege`, `AdjustToken`, `setuid`/`seteuid` appear nowhere
   in `obfuscator/` or emitted snippets. Test (e).
6. **The kill path is silent 137.** `_nx_kill` with no holders exits
   `137` via `os._exit` with empty stdout/stderr. Test (f).
