# Archived native (C/C++) sources

Moved here on **2026-10-23**. None of these was in the shipped
artefact: most were compile-tests that `make native-test` built into
throwaway objects, and the rest were never linked at all. Each one
either duplicates a live Python/Rust implementation or is the
payload-evasion category that is out of scope for this product.

Nothing was deleted — the files and their git history are intact.

## Out of scope by product decision

| File | What it did | Why archived |
|---|---|---|
| `stub_win.cpp` (1,957 lines) | Windows reflective loader: manual PE mapping, **AMSI / ETW patching**, HWID keying, BYOVD driver gate | **The purpose of this product is IP protection, not defeating security products.** Reflective loading and AMSI/ETW bypass exist to hide a payload from the defender's own tooling. That is the half that gets a commercial protector quarantined by the EDR its customers run, and it protects no algorithm. It was never in `make all` and never shipped. |
| `stub_linux.cpp` | Linux analogue of the above | same; compile-test only |
| `CompileToMarshal` (in `stub_win.cpp`) | Win32 import resolution for the reflective loader | same |

## Duplicates of a live implementation

| File | What it did | Live equivalent |
|---|---|---|
| `cross_process.c/.h` | cross-process fragment binding | `scripts/distributed/cross_process.py` |
| `distributed_vm.c/.h` | distributed VM execution | `scripts/distributed/vm_cluster.py` |
| `self_healing.c/.h` | self-healing simulation | `scripts/phases/phase15_self_healing.py` |
| `rop`-related C headers | ROP dispatch helpers | `scripts/rop/` (Python) |
| `struct_random.c/.h` | structural randomisation | per-build diversity is the Python pipeline's default |
| `oram` Rust module | ORAM engine | `native/core.cpp` (`ORAM_new` / `ORAM_access`) — kept, and called by the loader |
| `WBC_*` / `WBE_*` (whitebox) | whitebox crypto | `native/whitebox_feistel.cpp` is the whitebox that is actually compiled into `nixon_core.so`; the `WBC_*`/`WBE_*` symbols had no caller |

## Never wired

| File | What it did | Why archived |
|---|---|---|
| `microjit.c/.h` | polymorphic micro-JIT | compiled into `build/microjit.o` by `--fragment`; nothing linked or loaded it. The CI step `make microjit-so` built a `.so` nothing opened. |
| `vm_stub.c` | bytecode VM stub | compile-test only |
| `crypto_chain.c/.h` | chained key evolution | compiled into `crypto_chain.so`, which nothing loaded |
| `key_evolution.c/.h` | key evolution store | same |
| `gpu_stub.c` | GPU offload experiment | behind `-DNIXON_EXPERIMENTAL`, never enabled |
| `struct_random.c/.h` | structure randomisation | compile-test only |
| `fragment_migration.c/.h` | fragment migration | referenced by nothing anywhere in the repo |

## What remains in `native/`

Only what the product actually uses:

- `core.cpp` + `whitebox_feistel.cpp` → compiled into `nixon_core.so`
  (`obfuscator/core/c_core_build.py`), which the loader loads. This is
  the live FHE/ORAM backend.
- `simd_vm.c` → linked by the Rust relay.
- `payload.h` (generated), `platform.h`, `crash_suppress.h`,
  `rop_exec.h`, `PAYLOAD_CONTRACT.md`.

`make native-test` now builds only `core-cpp` and `simd-vm-c`.

## Tests that moved with the code

`tests/self_healing_native.py` and `tests/struct_random_native.py` are
in `archive/native/tests/`. Their subjects are here, so their tests are
here too — a test for code that does not ship proves nothing and keeps
the dead corpus alive. `tests/test_native_compile.py` now covers only
`core.cpp` and `simd_vm.c`, and asserts the archived Makefile targets
stay gone.

`tests/test_stub_win_contract.py` followed `stub_win.cpp` here on
2026-10-26. It had stayed behind and failed every CI run with
`FileNotFoundError` for the archived source; a contract test for a stub
that does not ship is not a regression signal. Two other groups kept
their tests in place, skipping while the subject is archived and
returning the moment it comes back:

- `tests/test_vm_ephemeral_isa.py` — the six `test_vm_stub_*` /
  `test_c_*` compile-contract tests skip while `vm_stub.c` is absent.
- `tests/test_crash_suppression.py` — the two `test_stub_*` wiring tests
  do the same for `stub_linux.cpp` / `stub_win.cpp`.

## Verification

`tests/test_no_dead_code.py` fails if a source in `native/` is not
referenced by the build (or is not on the small keep-list), so the
corpus cannot quietly grow back.
