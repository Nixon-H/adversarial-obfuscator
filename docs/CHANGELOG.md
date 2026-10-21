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

### Fixed

- **The loader CLI dropped 14 of its own flags.** It built a second
  `argparse.Namespace` and passed that to the build instead of the
  parsed one, so any field the copy forgot fell back to its default.
  `--hwid`, `--trial`, `--vm-threshold`, `--kod`, `--hostguard`,
  `--hwid-lock`, `--driver-check`, `--split-bootstrap`,
  `--no-snapshot`, `--no-stdlib-audit`, `--name-gate`, `--lowering`,
  `--rename-internal` and `--no-audit-hook-plant` were accepted, echoed
  in `--help`, and did nothing.
- **`scripts/build.py` accepted 11 loader-only flags and ignored them.**
  It compiles a native binary and emits no hybrid loader, so they
  cannot apply there; it now says so, and points at the loader CLI.
- **The build could hang.** `trigger_and_wait` polled forever, 15 of
  its `requests` calls had no timeout, and `download_artifacts` parsed
  an error page as an artifact list.
- **A rate limit was reported as a broken farm.** `Retry-After` and
  `X-RateLimit-Reset` are now honoured.
- **Concurrent builds clobbered each other.** `atomic_write` used a
  fixed temp-file name.
- **A zip member could escape the extraction directory** on two of the
  three paths that extract one. All three now share one confinement
  helper.
- **The build configuration was not in the repository.**
  `config/default.json` gates every Phase 2 protection; a fresh clone
  built a weaker artifact without it.
- **The lint gate was unpinned**, so a ruff release could turn a green
  tree red with no change to the code.
- **`z3` was a hard import** in 13 modules, making the build CLI
  unimportable without a proof-only dependency.
- **The `--expire` path was dead**: a module-level import had been
  removed, and the `except` around it swallowed the `NameError` and
  reported "Bad --expire date" for every date.
- **The CLI's usage message raised `NameError`** instead of printing
  the usage, because a star import cannot bring `_console` across.

### Fixed

- **A tampered artifact looked like a successful one.** The loader's
  self-integrity check computed a Merkle root and an HMAC over its own
  bytes and then discarded both verdicts; the build filled the anchors
  after the string table had turned them into lookups, so the runtime
  compared the root against a placeholder and the check never matched.
  A byte flipped in the artifact made it run nothing, print nothing and
  **exit 0**. The anchors now stay plain literals, the check runs
  before the state machine, and a mismatch exits 137.
- **A payload that crashed was swallowed.** The importer retried it and
  then discarded the failure, so a broken artifact exited 0. It now
  fails closed, as does the loader's state machine.
- **`--kod` armed nothing.** The flag only wrote a marker; the kill
  needed `NIXON_KOD` in the *target's* environment, so the flag's help
  text was false. The arming is now baked into the loader.
- **The watermark gate was unreachable** from any CLI, while the threat
  model promoted the row to ENVIRONMENT_VALIDATED. It is now reachable
  (`--watermark MSG` on the loader CLI).
- **The hostguard snippet was emitted but never called**, so it checked
  nothing. The loader now binds the host and verifies the builtins are
  unpatched before running the payload.
- **The split-bootstrap (Shamir) key was reconstructed and then
  ignored** — the payload was decrypted with the direct key. It is now
  the key that decrypts the payload.
- **The plaintext-dump debug aid shipped in every release artifact.**
  It is now a build-time opt-in (`--debug-dump-raw`); a normal artifact
  has no such capability.
- **The hybrid loader's gates ran after the payload.** Every gate was
  emitted after the payload entry point, so a trial-expired artifact
  ran its payload and only then died. The entry point is now last.

- **A tamper that disabled the entry point left the artifact exiting
  0.** The loader's integrity check and its "the payload must have
  run" check lived inside functions, so a tamper that broke the
  `__main__` block skipped both. They are now at module level,
  outside that block.
- **The payload was not authenticated.** The loader XOR-encrypts the
  payload and had no MAC over it, so a byte flipped in the payload
  region corrupted the payload silently: the loader ran, the payload
  was garbage, and the artifact exited 0. The build now computes an
  HMAC over the payload and the loader verifies it before extracting
  anything.
- **The loader's environment detections could not be gates.** The
  anti-sandbox, anti-emulator, anti-debug-frame, geo-fence and
  licence checks only perturbed the loader's hash chain. They are now
  armable with `--strict-detections`, which makes a detection terminate
  the artifact.
- **The 11 loader-only flags on `scripts/build.py` were accepted and
  silently ignored.** They now fail loudly, with a pointer to the
  loader CLI that arms them.
- **The artifact sidecar had no farm identity and no replay window.**
  The signed metadata now carries the producing `farm` (pinned on
  download) and `issued_at`/`expires_at` (`NIXON_ARTIFACT_TTL`, default
  30 days); both are covered by the MAC.
- **A failed build left its staging file in the repository root.** It
  now goes to the build directory.

### Changed

- **The core package no longer uses `from .mod import *`.** The
  imports are spelled out, so F403 and F405 are enforced. The
  conversion found a dead `return` referencing two names nobody had
  ever defined.
- **The lint rule set is the whole pyflakes family** (`select =
  ["F"]`), which the tree satisfies. The other families (pycodestyle,
  bugbear, pyupgrade) are style migrations rather than fixes, and are
  recorded as deliberately out of scope in `ruff.toml`.
- **A scheduled CI job reports when a newer ruff exists**, so the pin
  cannot go stale unnoticed.
- **Dependencies are hash-pinned.** `requirements.lock` pins all 23
  artefacts -- the full transitive closure -- with their SHA-256, and
  CI installs with `--require-hashes`.
- **The payload ships as N sealed sections by default**, so the whole
  encrypted payload is never resident in one buffer. `--no-section-split`
  is the escape hatch.
- **`--opt-level` applies to the loader build** too, so all three CLIs
  resolve a protection level the same way.
- `--watermark` on the loader CLI is now `--lock-hwid`; the old
  spelling still works and says that it is deprecated.

### Added

- CI builds a payload, **runs** the artifact, and asserts its output --
  on every supported Python version.
- `docs/CHANGELOG.md` (this file).
- A runtime check that every global read in the live tree resolves, and
  an audit that lists what a commit removed and which removals dropped a
  call.

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
