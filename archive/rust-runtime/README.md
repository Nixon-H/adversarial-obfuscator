# Archived Rust runtime modules

Moved here on **2026-10-23**, and **the source files are no longer in the
tree**. Dead code in a working tree is not an archive — git history is.
This directory keeps the rationale and the recovery path; the code lives
one command away.

```bash
# the ten modules removed on 2026-10-23
git show 589298f:runtime/src/rop.rs

# the five validation phases
git show 7976d2f:scripts/phases/phase20_hpc_detect.py

# the seven "Runtime Evolution" modules removed on 2026-10-27
git show 4d7effe:runtime/src/cfg_mutation.rs
```

To bring one back you must also wire it — `tests/test_no_dead_code.py`
fails if a module is declared and unreachable, which is the state all of
these were in.

## Why they are gone

Each was declared in `runtime/src/lib.rs`, compiled into
`nixon-runtime`, and **unreachable from `init_runtime`** — no
configuration could execute it. A module that cannot run protects
nothing, and in this project it did active harm: the feature report
counted "a module with this name exists" as evidence of a shipped
protection.

Each one has a live implementation elsewhere, or needs hardware the
product does not target.

| Module | What it did | Why archived | Live equivalent |
|---|---|---|---|
| `branch_entangle` | branch entanglement against side channels | no caller; needs a specific microarchitecture | — |
| `cache_bound` | cache-timing-bounded execution | no caller | — |
| `code_genome` | code-genome diversity | no caller | per-build diversity is the Python pipeline's default (`config seed: null`) |
| `hpc_detect` | HPC / emulator detection | no caller; needs HPC hardware | — |
| `hw_entropy` | hardware entropy source | no caller | — |
| `hwid_bind` | hardware-ID binding | no caller | the Python loader's HWID / trial gate |
| `multicore_entangle` | multi-core entanglement | no caller | — |
| `oram` | oblivious RAM engine | no caller; `enable_oram` had no handler in `init_runtime` | the C ORAM in `native/core.cpp` (`ORAM_new` / `ORAM_access`), which the loader calls |
| `rop` | ROP compilation | no caller | `scripts/rop/` (Python) |
| `rop_dispatch` | ROP dispatch | no caller | `scripts/rop/` (Python) |

## The seven "Runtime Evolution" features (archived 2026-10-27)

These were compiled, reachable from `init_runtime`, and gated by a flag
that `RuntimeConfig::default` left `false` while nothing in either crate
set it — so **no configuration could ever run them**. They are the
`GATED-OFF` verdict in the feature report, and the report now says
`DEAD CODE` with the reason instead:

| Module | What it did |
|---|---|
| `variant_pool` | picked a pre-built variant at run time |
| `cfg_mutation` | re-ordered basic blocks per execution |
| `class_dispatch` | dispatched through a per-class variant cache |
| `ssa_mutation` | generated SSA-level variants |
| `state_isa` | state-dependent instruction mapping |
| `per_exec_recompile` | recompiled per execution |
| `self_healing` | background checksum repair |

`mutation_seed` (formerly `cfg_mutation_seed`) survives because
structure randomisation uses it.

## What is NOT here

`jit` and `hydra` were also named as dead in the audit, but they are
still referenced: `jit` from `decrypt::decrypt_and_jit` (a function
`init_runtime` never calls) and `hydra` from `lib.rs`'s re-export and
`timing.rs`'s `ClockBiasResponse` API. Removing them requires removing
those call sites first; they are part of the "trim the gated-off set"
work, not this archive.

## Validation phases that moved with them

Five pipeline phases existed only to run `cargo test` against these
modules:

| Phase | Ran |
|---|---|
| `phase20_hpc_detect` | `hpc_detect::tests::…` |
| `phase21_hw_entropy` | `hw_entropy::tests::…` |
| `phase22_cache_bound` | `cache_bound::tests::…` |
| `phase23_branch_entangle` | `branch_entangle::tests` |
| `phase24_multicore_entangle` | `multicore_entangle::tests` |

After the archive, each filter matched **zero tests**. `cargo test`
exits 0 when nothing matches, so the phase logged "tests passed" — a
vacuous pass, which is the worst kind: green, and proving nothing.
They are in `phases/`, and the CLI flags now log `ARCHIVED` instead of
running them. `tests/test_no_dead_code.py` fails if any of them is
imported again.

## Verification

`tests/test_no_dead_code.py` fails if a module in `runtime/src/` becomes
unreachable again, so this cannot silently regress.
