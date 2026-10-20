# Changelog

The product's version is **2.0.0** (`obfuscator/version.py` — the single
source of truth; `config/default.json` carries the same value and a test
checks they agree).

> **These are not the vendor's version numbers.** The audit reports
> track a *vendor* matrix labelled `v1.1` … `V10`; those are the
> obfuscation-technique generations the vendor published, not releases
> of this tool. The two numberings are unrelated and must not be
> compared.

## Unreleased

Nothing yet.

## 2.0.0

The current release. What it contains is documented in the audit
reports rather than here, because the reports are dated snapshots and
this file is a summary:

- **Loader gates**: verified TLS for the emitted key fetch (system
  trust store plus an operator CA via `--tls-ca-bundle`; verification is
  never disabled), HWID lock, trial period, kill-on-detect, the
  frozen-stdlib snapshot gate, the stdlib function-audit gate, the
  audit-hook plant detector, the read-only BYOVD driver gate, and the
  kill ladder.
- **Sealed section streaming** (`--section-split` / `--section-count`):
  the payload ships as N independently sealed sections, so no single
  buffer holds the whole encrypted payload. Opt-in.
- **Enforceable lint gate**: `make lint` runs ruff (pinned) and a
  runtime undefined-global check over the live tree.
- **Explicit log redirect**: importing the package no longer creates or
  truncates a file in the caller's working directory.
- **End-to-end gates**: CI builds a payload, RUNS the artifact, and
  asserts its output — on every supported Python version.

### 2.0.0 — security fixes

- The adversarial prompt-injection pass rewrote the emitted ChaCha20
  seal literals, so roughly 80% of default builds produced an artifact
  that died at import with `ValueError: bad string seal`.
- `MemoryGuard` leaked `mlockall(MCL_FUTURE)`: a second monitored call
  locked the process permanently, capping every later page fault at
  `RLIMIT_MEMLOCK`.
- The trial-state file was followed through a symlink (fail-open). It
  is now opened `O_NOFOLLOW` and fails closed, in both the build-time
  helper and the emitted gate.
- The emitted loader compared MACs with `==` instead of
  `hmac.compare_digest`, and ran its self-delete through `shell=True`
  with an interpolated path.
- The emitted loader wrote the **decrypted payload** to a hardcoded
  absolute path at runtime.
- The emitted key fetch used `ssl._create_unverified_context()`.
