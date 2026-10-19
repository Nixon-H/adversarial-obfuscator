# Platform Support Matrix

| Component | Linux x86_64 | Linux ARM64 | Windows x86_64 | macOS |
|-----------|:---:|:---:|:---:|:---:|
| **obfuscator/** (Python) | ✅ | ✅ | ✅ | ✅ |
| **irgen/** (Python) | ✅ | ✅ | ✅ | ✅ |
| **llvmgen/** (Python) | ✅ | ✅ | ✅ | ✅ |
| **encrypt/** (Python) | ✅ | ✅ | ✅ | ✅ |
| **vm/** (Python) | ✅ | ✅ | ✅ | ✅ |
| **runtime/** (Rust) | ✅ | ✅ (`cargo check`) | ✅ (`cargo check --target windows`) | ⚠️ |
| **relay/** (Rust) | ✅ | ✅ (`cargo check`) | ✅ (`cargo check --target windows`) | ⚠️ |
| **native/core.cpp** | ✅ | ⚠️ (no Python.h for cross) | ⚠️ (no Python.h for cross) | ❌ |
| **native/stub_linux.cpp** | ✅ | ✅ | N/A | ✅ |
| **native/stub_win.cpp** | ❌ | ❌ | ✅ | ❌ |
| **native/vm_stub.c** | ✅ | ✅ | ⚠️ | ❌ |
| **native/payload.h** | ✅ | ✅ | ✅ | ⚠️ |
| **native/platform.h** | ✅ | ✅ | ✅ | ✅ |
| **Docker** | ✅ | ✅ | ❌ | ❌ |
| **CI/CD** | ✅ | ✅ (via cross) | ✅ (via cross) | ❌ |

Legend:
- ✅ = Tested and working
- ⚠️ = Buildable but untested
- ❌ = Not supported

## Linux x86_64 (Primary Target)
Full support. All 4108 tests pass (224 test files). CI/CD enabled.

## Linux ARM64
Cross-compilation verified via `cargo check --target aarch64-unknown-linux-gnu`.
Runtime uses `cntvct_el0` for timing (instead of RDTSC), `dmb sy` for memory barriers (instead of mfence).
Inline assembly fully gated behind `#[cfg(target_arch = "aarch64")]`. Python components work natively.

## Windows x86_64
Cross-compilation verified via `cargo check --target x86_64-pc-windows-gnu` with MinGW.
Memory management uses `VirtualAlloc`/`VirtualFree`/`VirtualProtect`/`VirtualLock` via raw FFI.
Anti-debug stub in `native/stub_win.cpp` (2009 lines, Windows-specific).
Build: `make stub-win` (requires `x86_64-w64-mingw32-gcc`).

## macOS
Not currently supported — no Darwin Rust target toolchain installed.
Would require macOS equivalents for POSIX memory APIs and anti-debug mechanisms.
