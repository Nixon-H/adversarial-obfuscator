# Archived Rust runtime modules

Moved here on **2026-10-23**. These ten modules were declared in
`runtime/src/lib.rs`, compiled into `nixon-runtime`, and **unreachable
from `init_runtime`** — no configuration could execute them. A module
that cannot run protects nothing, and in this project it did active
harm: the feature report counted "a module with this name exists" as
evidence of a shipped protection.

Each one has a live implementation elsewhere, or needs hardware the
product does not target. Nothing was deleted — restore a file and its
`pub mod` line to bring it back.

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

## What is NOT here

`jit` and `hydra` were also named as dead in the audit, but they are
still referenced: `jit` from `decrypt::decrypt_and_jit` (a function
`init_runtime` never calls) and `hydra` from `lib.rs`'s re-export and
`timing.rs`'s `ClockBiasResponse` API. Removing them requires removing
those call sites first; they are part of the "trim the gated-off set"
work, not this archive.

## Verification

`tests/test_no_dead_code.py` fails if a module in `runtime/src/` becomes
unreachable again, so this cannot silently regress.
