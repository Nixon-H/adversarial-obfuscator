# ADR 0005 — Artifact Authenticity (Farm Sign/Verify Protocol)

## Context

`docs/failure-modes.md:43` (D26) records the highest-severity deferred
item: `download_artifacts` extracted farm zips with no integrity check
beyond the TLS channel. Timeouts, status enforcement, and ZipSlip
confinement were since added on the `GitHubBuildFarm` path
(`obfuscator/core/utils.py`, `download_artifacts`), but end-to-end
authenticity was explicitly deferred for "a protocol decision": who
signs, with what key, what is bound into the signature, and what the
download side does when keys or signatures are absent. The repo already
had a bytes-only HMAC primitive (`scripts/artifact_sign.py:21`
`sign_file`, `:31` `verify_file`) wired opportunistically into the
package step (`scripts/phases/phase06_package.py:50-70`, `--sign-key-env
VAR`), and nothing wired it into the farm download path. This ADR is
that protocol decision; the mechanism implements it.

## Decision

**Scheme: operator-provisioned shared-secret HMAC-SHA256.** No PKI, no
per-farm identities, no transparency log — deliberately. The threat is
a network/artifact swap between the farm and the operator's build
machine (corrupted download, swapped payload, patched loader), not a
multi-party non-repudiation problem, and every participant that needs
to verify already shares the operator's trust domain.

Concretely:

- **Key ownership / storage.** The signing key is owned by the
  operator who runs the build and holds the farm token. It lives ONLY
  in the environment as hex: `NIXON_ARTIFACT_KEY_HEX` (explicit farm
  name, checked first) falling back to the pre-existing `NIXON_SIGN_KEY`
  (CLI default, `SECURITY.md`, `scripts/artifact_sign.py:50`). Never in
  source, docs, tests, or sidecars (`resolve_key`,
  `scripts/artifact_sign.py`). Malformed hex is treated as absent, never
  as fatal.
- **What is signed.** `sign_artifact` MACs
  `file bytes + 0x00 + canonical-JSON(metadata)` under tag
  `hmac-sha256-binding-v1`. The bound metadata is at minimum
  repo / commit / build-id / platform / python
  (`default_metadata`: `GITHUB_REPOSITORY`, `GITHUB_SHA`,
  `NIXON_BUILD_ID`, `sys.platform`, `platform.python_version()`); the
  package step additionally binds `--build-id` and the file basename.
  The old bytes-only format is unchanged and still verifies (legacy
  path in `verify_artifact`) — weaker, documented below.
- **Package/upload side (opportunistic, never fails the build).** The
  package step signs when `--sign-key-env` names a populated var and
  writes `<file>.sig.json` including the metadata. Farm `upload_file`
  paths (both farm classes) attach `<remote>.sig.json` the same way
  when a key resolves; absent key → one logged line + proceed unsigned.
- **Download side (fail closed where enforceable).** Each downloaded
  zip is checked BEFORE `extractall` (`_verify_download_zip`,
  `obfuscator/core/utils.py`): sidecars present + key configured →
  `verify_zip_sidecars`, mismatch raises `ValueError` (zip deleted, no
  extract — fail closed, and the Nuitka path aborts without retry on
  tamper). The policy matrix is total — no silent downgrade:

  | key configured | sidecar present | behavior |
  |---|---|---|
  | yes | yes | verify; mismatch → raise, no extract |
  | yes | no | `info` note + proceed (farm-runner binaries are unsigned by design, see below) |
  | no | yes | loud `WARNING` (log + console) + proceed unverified |
  | no | no | explicit `WARNING` (auditable downgrade) + proceed |

  `enforce_dir_sidecars` (`scripts/artifact_sign.py`) applies the same
  policy to sidecars already on disk (package-dir checks); it is NOT
  run over the farm output tree because that path renames artifacts on
  layout, which intentionally breaks sibling pairing.

- **CI-vs-service signing.** CI (GitHub-hosted runners) NEVER signs:
  shipping the shared secret to a runner would expose it in logs,
  forks, and artifact caches. Consequence, stated plainly: binaries
  compiled on farm runners carry NO HMAC; their integrity rests on the
  authenticated-TLS channel plus Actions provenance (same as before —
  this ADR does not weaken that claim, it stops pretending otherwise).
  Signatures authenticate operator-side artifacts (packaged payloads,
  uploaded sources/sidecars) and any future producer that holds the key.

## Alternatives considered

- **Asymmetric signing (Ed25519, per-farm keypairs).** Rejected for
  v1: no `cryptography`/`PyNaCl` hard dependency exists on the
  verify path (stdlib-only `hmac` works everywhere including the
  3.10 floor), and per-farm identities are deferred (below). The sig
  format reserves an `algo` tag so a v2 asymmetric scheme can coexist.
  → **Superseded by the 2026-10-21 amendment below: implemented.**
- **Shipping the key to the workflow for runner-side signing.**
  Rejected: secret would transit workflow YAML / runner env / caches;
  a tampered runner could sign its own malware anyway (signing oracle
  problem). Runners stay keyless.
- **Fail-closed when no key is configured.** Rejected: would brick
  every existing keyless farm user on upgrade. The no-key path warns
  loudly (grep-able `ARTIFACT-AUTH` log lines) instead — fail-open by
  operator choice, auditable, never silent.
- **SHA256 manifest instead of HMAC.** Weaker against a channel
  attacker who can rewrite both artifact and manifest; HMAC was
  already in-tree and costs nothing extra.

## Consequences

- Package signing stays opt-in (`--sign-key-env`); download
  enforcement only bites where sidecars exist AND a key is configured.
  Default posture is unchanged (warn, don't break).
- New behavior is purely additive: `sign_file`/`verify_file` API,
  sidecar filename, `download_artifacts(run_id, output_dir)`
  positional signature, and the no-key download flow all keep working.
- Honest limitations (residual risk, not coverage):
  1. **Shared secret:** every verifier can also forge. No
     non-repudiation, no per-farm blame. **CLOSED 2026-10-21** by the
     amendment above: the verifier now holds only a public key, so it
     can check an artifact and cannot mint one; the farm identity is
     the pinned public key rather than a claimed string. The HMAC path
     remains available for compatibility, and a deployment that still
     uses it keeps the old property — that is why the asymmetric path
     is preferred automatically when a private key is configured.
  2. **Runner binaries unsigned:** a farm-runner compromise is NOT
     detected by this mechanism — TLS + provenance is the only story
     there, as before. **Partly closed 2026-10-21:** a farm that holds
     an Ed25519 private key signs what it stages, so a runner whose key
     is not pinned is rejected at the gate. A runner with no key at all
     still stages unsigned artifacts, and the gate says so loudly.
  3. **Rotation versioning:** rotation is manual (set new env,
     re-sign); old-key artifacts fail after rotation (expected).
     **Replay protection closed 2026-10-20:** the signed metadata now
     carries `issued_at` and `expires_at` (`NIXON_ARTIFACT_TTL`,
     default 30 days), the MAC covers both, and a sidecar past its
     window no longer verifies. Key *versioning* (a `kid` identifying
     which key signed it) is still deferred.
  4. **Binding is only as truthful as the signer env:** the MAC
     authenticates the metadata *claim*; a liar holding the key can
     bind false repo/commit values.
  5. **Upload sidecars are audit trail, not runner enforcement:**
     runners cannot verify them (keyless); they let the key-holder
     detect repo-content tampering after the fact.
  6. **Nuitka download path still lacks ZipSlip confinement** — CLOSED
     2026-10-20: all three extraction paths (both farm download paths
     and the tool download) now go through the shared
     `_extract_zip_confined()` / `_extract_tar_confined()` helpers,
     which check the RESOLVED destination of every member
     (`tests/test_archive_confinement.py`).
  7. The `utils.py` glue (upload/download wiring) is covered by
     `py_compile` + review, not unit tests (importing
     `obfuscator.core.utils` has log-redirect/UI side effects); all
     policy logic tested at the helper level.

## Amendment (2026-10-21) — per-farm Ed25519 keys

**This amendment supersedes the shared-secret decision above.** The
reason it was originally deferred was that the choice of who holds
which key is a deployment question. The property that actually
mattered, however, is a property of the *key*:

> A verifier must not be able to mint an artifact it will later accept.

A shared HMAC key cannot provide that: every verifier that holds the
key is also a forger, for any farm id. An asymmetric key pair can.

**Decision: per-farm Ed25519 key pairs, with the public half pinned by
the operator.**

- **Who holds what.** The farm holds the **private** key
  (`NIXON_ARTIFACT_ED25519_KEY`, hex 32-byte seed). The operator holds
  the **public** key — either one
  (`NIXON_ARTIFACT_ED25519_PUBKEY`, hex) or a map of farm id → public
  key (`NIXON_ARTIFACT_ED25519_KEYS`, JSON). The verifier holds no
  secret and cannot sign.
- **What is signed.** The same material as the HMAC path:
  `file bytes + 0x00 + canonical-JSON(metadata)`, so `farm`,
  `issued_at` and `expires_at` stay bound in. The signature is
  Ed25519 over that message; the sidecar is
  `{"algo": "ed25519-binding-v1", "sig": base64, "key_id", "metadata",
  "file"}`. `key_id` is a SHA-256 fingerprint of the public key, so
  the sidecar names the key that signed it.
- **Which key is used.** `sign_artifact_auto` prefers Ed25519 whenever
  a private key is configured and falls back to the HMAC path
  otherwise. The HMAC path is unchanged and still verifies; it is
  compatibility, not the preferred scheme.
- **Download side.** `verify_zip_sidecars` and `enforce_dir_sidecars`
  verify an Ed25519 sidecar against the pinned public keys. A sidecar
  signed by a key the operator does not pin is a **mismatch**, not a
  pass. The `algo` tag selects the path, so a public key can never be
  checked with HMAC semantics.
- **Farm-runner binaries.** The farm signs what it stages, so the
  "runners are unsigned by design" limitation falls away for farms
  that hold a key. A runner that does not hold the key produces no
  valid sidecar; a runner whose key is not pinned is rejected at the
  gate.
- **Dependency.** `cryptography` is already a pinned dependency
  (`requirements.txt`, `requirements.lock`); the import is lazy, so
  the module stays importable without it and the HMAC path keeps
  working.

**What this does NOT change.** The CI-vs-service rule stands: a
GitHub-hosted runner is not given a key, because shipping a secret to
a runner exposes it in logs, forks and caches. A runner with no key
stages unsigned artifacts, and the gate says so out loud rather than
pretending otherwise.

### Amendment evidence

- `scripts/artifact_sign.py`: `sign_artifact_ed25519`,
  `verify_artifact_ed25519`, `verify_ed25519_bytes`,
  `resolve_ed25519_private_key`, `resolve_ed25519_public_keys`,
  `ed25519_key_id`, `sign_artifact_auto`.
- `tests/test_artifact_signing_ed25519.py`: roundtrip with the public
  key only, **forgery with a different private key is rejected**,
  metadata tamper, byte tamper, expiry, metadata pin, malformed
  signature, key resolution (single + map), HMAC fallback, zip gate
  accepts a pinned key and rejects an unpinned one.
- `docs/AUDIT-2026-10-20.md` §8.2c.

## Evidence

- Bound sign/verify: `scripts/artifact_sign.py` (`sign_artifact`,
  `verify_artifact`, `verify_zip_sidecars`, `enforce_dir_sidecars`,
  `resolve_key`, `default_metadata`); legacy compat preserved
  (`sign_file`, `verify_file` untouched).
- Package binding: `scripts/phases/phase06_package.py` (metadata-bound
  sidecar, best-effort).
- Upload/download wiring: `obfuscator/core/utils.py`
  (`_artifact_sign_key`, `_verify_download_zip`, both `upload_file`
  sidecars, both `download_artifacts` verify-before-extract gates).
- Tests: `tests/test_artifact_signing.py` (roundtrip, byte-tamper,
  metadata-tamper, legacy-compat, wrong-key, key-precedence,
  zip-gate incl. tamper-closed, no-key warnings via `caplog`,
  package-step sidecar with metadata).
- Threat-model row: `THREAT_MODEL.md` (tampered-binaries row evidence
  extended; status stays `ADVERSARIAL_TESTED` — hosted-runner unit
  execution is testing, not deployment validation, per the taxonomy).
