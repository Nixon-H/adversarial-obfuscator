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
  `ast.parse(feature_version=(3, 10))` check cannot see.
* `python3 scripts/lint/check_undefined_globals.py` — resolves every
  global read in the live tree at runtime. This exists because the
  package uses `from .mod import *`, which hides undefined names from
  the linter (F403/F405 are ignored for that reason).

ruff is pinned in `requirements-dev.txt` on purpose: an unpinned linter
can turn a green tree red with no change to the code.

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
For auditors needing a deterministic replay:

1. Set `SEED` (or `NIXON_SEED`) to an integer, e.g. `SEED=42`.
2. Pass `--randomization-seed <int>` (see `scripts/build.py`) so the
   structure-randomization, speculation, and CPU-port phases stop
   drawing fresh entropy (`secrets.randbits` / `token_bytes`).
3. Record the seed alongside the payload hash; re-running with the
   same seed + same toolchain reproduces the same layout.
4. Caveat: some phases still use fresh randomness when the flag is
   absent (JIT seed, ephemeral opcode map, fingerprint seeds), and
   timestamps/paths may differ — compare normalized artifacts.
5. This changes nothing about default builds: without the env/flag,
   every build stays unique by design.
