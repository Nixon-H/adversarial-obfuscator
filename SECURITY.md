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
  and is wired into the hybrid loader as the opt-in `--no-section-split`
  flag; it is not the default.

## Trust boundaries (who is the attacker)

This is the distinction that decides whether a static "path traversal" or
"SSRF" finding is a defect or a misclassification, so it is stated explicitly.
The machine-readable form is `.mimosa/security-policy.json`
(`threatModel.trustBoundaries`).

**The operator is trusted.** `build_dir`, `--output`, `--payload`, the farm repo
name and the licence-server base URL are supplied by the person running the
builder, on their own machine, under their own account. A path assembled from
them (`os.path.join(build_dir, ...)`, `open(output, "w")`) is not an
attacker-controlled traversal: there is no privilege boundary being crossed,
because the operator already holds the privileges the write requires. Likewise
the Cloudflare and GitHub base URLs come from configuration, not from the
payload or the artefact, so building a request URL from them is not
server-side request forgery — no untrusted party influences the destination.

**The artefact's holder is untrusted.** An attacker who has the shipped file
can read it, run it, patch it, and inspect its memory. Every mechanism aimed at
them lives in the payload: section sealing, the self-check, CFI, memlock, the
kill ladder, licence replay/revocation, anti-rollback.

**The build runner is untrusted.** It executes our build on someone else's
machine, so it must attest what it built (`obfuscator/runner_attest.py`) and the
controller must verify that attestation. A missing attestation is a failure,
not "no objection".

**The network is untrusted.** Farm downloads and update manifests are verified
against hashes and signatures the controller computed itself, never against a
claim made by the responder.

Consequence for reviewers: a report of the form "user-controlled path reaches
`open()`" in `obfuscator/core/pipeline.py` is in scope only if the path can be
influenced by the *artefact's holder* or by a *remote party* — not by the
operator. Findings of that shape in the build CLI are documented here as
out-of-boundary rather than silently suppressed: the scanner keeps reporting
them, and they are triaged against this section instead of ignored.

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
