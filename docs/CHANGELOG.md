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

- **Editing the artifact's self-check disabled it.** The check excluded
  the lines it hashes by a MARKER string — and the marker's own line was
  excluded from the hash too, so editing the marker was invisible to
  the check. And an exception inside the check was logged and ignored,
  so breaking the check's own code (a `NameError`, a damaged Merkle
  helper) turned the anti-tamper control off: the artifact carried on
  and exited 0. A scan of ~6900 byte positions across three builds
  found 12 offsets that were not caught — every one of them in the
  check's own code. The excluded lines are now identified by their
  VALUES, the check's code is hashed like everything else, a check that
  cannot run fails the artifact, and the build verifies that the two
  filters select the same lines.
- **The artifact bundler extracted with no confinement.**
  `verify_bundle` unpacked a bundle with a bare `extractall`, so a
  member named `../x` could write outside the extraction directory —
  the same ZipSlip family the build-farm paths were fixed for, in a
  file the test missed because the test only scanned one module. The
  check now lives in one shared module
  (`obfuscator/core/archive_safety.py`) and the test scans the whole
  tree.
- **The build spawned workers with `fork`.** Forking a multi-threaded
  process is deprecated (Python 3.12+ warns) and can deadlock in the
  child, and Python 3.14 changes the default on Linux. The distributed
  modules now spawn with "spawn" explicitly.
- **The test suite had warnings.** All of them are gone: the
  `tarfile` extraction without an explicit filter (a behaviour change
  in Python 3.14, not just noise), `datetime.utcnow()`, and the
  deprecated `pkg_resources` import.
- **Nineteen tests skipped in CI.** They need a compiled artefact —
  the C shared libraries, the Rust relay, the microjit shared object —
  and each skips itself when the artefact is absent. CI built those
  artefacts *after* the tests, so CI skipped all nineteen too, and a
  skipped test proves nothing. The artefacts are now built first, and
  `NIXON_REQUIRE_ARTEFACTS=1` turns a missing artefact into a failed
  build rather than a quiet skip. The suite's skips are down to four,
  all of them deliberate (a retired C simulation, a Cython block that
  is not Python, the 3.14 goldens that run on the 3.14 CI leg, and a
  platform-conditional `mprotect` case).

- **The native build path did not build.** It was recorded as an
  environmental limitation because it failed identically on the
  unmodified tree. It was not environmental: twenty-two defects in the
  IR → LLVM path, each hiding the next. The right shift (`shr`) and the
  pointer arithmetic (`gep`) were not lowered — and an instruction the
  lowering did not recognise was emitted as a **comment**, so its
  result stayed undefined; the GEP dropped its indices, computing the
  wrong address; a constant captured by a nested function resolved to
  `0`, so `x & _nx_M` compiled to `x & 0`; the IR carries pointers as
  `i32` and the GEP did not convert the base; LLVM requires unnamed
  values to be numbered consecutively and the IR numbering has gaps;
  the comparison opcodes were not lowered and the tokenizer split
  string constants containing spaces; a float constant in an integer
  operation is not valid LLVM; a call with no arguments lost its
  parentheses; a `try` block was dropped whole; the boolean operators
  produced a block with no terminator and the wrong short-circuit
  value; the dead-code pass deleted values a phi still reads; and the
  OLLVM passes broke the module they obfuscated (the BCF pass failed
  on roughly half its runs). The lowering now **fails loudly** on an
  instruction it does not recognise instead of dropping it, the IR
  generator resolves closures, imports, module-level bindings and
  literals instead of turning them into zeros, and it **fails** on a
  name it cannot represent rather than shipping a zero. The
  encryption stage runs the `encrypt` package CLI (the script form
  could never work — it uses a relative import), and
  `scripts/build.py` completes the native path and produces a valid
  ELF object.
- **Every verifier of an artifact was also a forger.** The artifact
  sidecar was signed with one shared HMAC key, so any verifier that
  held the key could mint a sidecar for any farm id. The farm now
  holds an **Ed25519 private key** and the operator pins the farm's
  **public** key: a verifier can check an artifact and cannot mint
  one. A sidecar signed by an unpinned key is rejected at the download
  gate, and the farm identity is the pinned key rather than a claimed
  string. The HMAC path is unchanged and still verifies.
- **The environment snapshot could hang the build.**
  `platform.processor()` and `platform.machine()` each run an untimed
  `uname` subprocess; one of them blocked a build for five minutes
  under load. The snapshot reads `os.uname()` instead.

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
