# Developer Guide

## Prerequisites

- Python 3.10+ (payloads support 3.10–3.14 per obfuscator/nyser.py; builder floor is 3.10)
- Rust toolchain (rustup)
- g++ (for native C++ extensions)
- LLVM (`llc` for LLVM IR compilation)
- MinGW (for Windows cross-compilation, optional)

## Quick Start

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt   # ruff, pinned (the lint gate)
make all
make test
```

## Lint

```bash
make lint
```

Two gates, both of which must pass:

* `ruff check --no-cache .` — the enforced rule set is in `ruff.toml`.
  The `target-version = "py310"` there is what catches Python 3.12+
  f-string syntax (PEP 701), which the repo's own
  `ast.parse(feature_version=(3, 10))` check cannot see. F403 and F405
  are enforced too: the core package spells out its imports instead of
  using `from .mod import *`, so a name arriving from nowhere fails the
  gate.
* `python3 scripts/lint/check_undefined_globals.py` — resolves every
  global read in the live tree at runtime. It is the second line of
  defence behind the static checks, and it is what caught the
  `datetime` NameError in `build_project` and the `_console` NameError
  in the CLI's usage message.

ruff is pinned in `requirements-dev.txt` on purpose: an unpinned linter
can turn a green tree red with no change to the code. `make lint-upgrade`
prints the current pin and the latest release, so bumping it is a
reviewed act rather than an accident.

## Dependency lock

`requirements.lock` is hash-pinned: every artefact, including the
transitive closure, carries its SHA-256, and CI installs it with
`--require-hashes`. A substituted or tampered artefact fails the
install instead of landing.

`requirements.txt` states the wanted versions. After changing it:

```bash
make lock          # regenerate the lock (needs uv)
make lock-verify   # install it with --require-hashes in a clean venv
```

Review the lock diff — a new lock is a change to what CI is allowed to
install. `tests/test_dependency_lock.py` fails if the two files drift
apart.

## End-to-end checks

```bash
make e2e          # every build must produce an artifact that RUNS
make audit-commit # what the last commit removed, and which removals dropped a call
```

`make e2e` is the check that keeps finding the defects that module-by-
module review misses: it builds a payload and executes the artifact.
`make audit-commit` is for bulk changes — it lists the statements a
commit deleted and isolates the ones whose *call* was the point.

## Project Structure

- `obfuscator/` — Python source obfuscation and pipeline orchestration
- `irgen/` — Intermediate representation and optimization passes
- `llvmgen/` — LLVM IR code generation and OLLVM passes
- `encrypt/` — Binary encryption and AES-256-CTR implementation
- `vm/` — Custom VM ISA, bytecode compiler, and interpreter
- `runtime/` — Rust runtime library (decryption, integrity, anti-debug)
- `relay/` — Rust relay binary (payload execution)
- `native/` — C/C++ native extensions
- `scripts/` — Build pipeline scripts
  - `scripts/phases/` — the ordered build stages
  - `scripts/evaluation/` — measurement and red-team tools (the LLM
    tools need `pip install -r requirements-ai.txt`)
  - `scripts/lint/` — the lint gate and the deterministic cleanup
    scripts (`make lint`, `make audit-commit`)
  - `scripts/validation/`, `scripts/proofs/` — the SMT proof stack
    (optional: `z3-solver`)
- `tests/` — Test suites
- `docs/` — the guides, the ADRs, the audit reports and the CHANGELOG
- `config/` — Build configuration (JSON). `config/default.json` and
  `config/baseline_report.json` are tracked (the build depends on
  them); everything else in that directory is machine-local.

## Adding a Feature

1. Add implementation in the appropriate module
2. Add tests in `tests/`
3. If it's a Phase 2 feature, add to `tests/test_<feature>.py` (and register it in `tests/`)
4. If it needs build integration, add to `scripts/build.py`
5. Run `make test` to verify

## Testing

```bash
make test           # Full test suite (pytest + runtime/relay cargo tests)
pytest tests/test_encrypt.py -v  # Specific test file
cd runtime && cargo test  # Specific Rust crate (relay: cd relay && cargo test)
```

## Cross-Compilation

```bash
make relay-linux-arm   # ARM64 Linux
make relay-win         # Windows x86_64
```

## Build Configuration

See `config/default.json` for all build options.

## Reproducible builds

Builds are intentionally unique per run (random seeds, opcode swizzle,
fragment keys), so identical payloads produce different artifacts.

`--seed` seeds the global `random` module, the AST transformer's own RNG and
its `secrets` patch, and several AST injectors. With a fixed seed the source
emitter now produces **byte-identical** output for the same payload, tool
version, and flag set. Verified: three O4 builds gave 29,802 bytes each; two
builds with phase-2 defaults on gave 33,170 bytes each; a different seed gave
32,911 bytes.

`--transforms seed=N` (or `SEED` / `NIXON_SEED`) is a separate structural
seed: structure randomisation, speculation, and the CPU-port phase. It does not
seed the AST path.

What the flags do **not** buy:

1. Level 0 is not a byte-identical copy through the CLI; always-on rename,
   checksum and string passes still run. `--skip obfuscate` is the copy path.
2. The packed loader is not byte-reproducible: blob keys, string keys, section
   keys, timestamps and packaging draws come from `secrets`/`os.urandom` and
   several values cross the pack/run boundary.
3. `--pin-structure` pins structure and the timestamp, not key material.
4. Some phases still use fresh randomness when no seed is given (JIT seed,
   ephemeral opcode map, fingerprint seeds), and timestamps/paths may differ —
   compare normalised artifacts.

`docs/EMITTER_PIPELINE.md` has the entropy inventory; the current limitations
are in [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) §6.1. The historical entry in
`CHANGELOG.md` saying `--transforms seed=N` was gone is stale; the flag is
still accepted by `scripts/build.py` and now carries a dated correction.
