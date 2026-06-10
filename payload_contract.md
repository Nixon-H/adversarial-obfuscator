# Payload Contract — `payload.h`

This document specifies every symbol that must be defined in `payload.h` for
`nixon_stub.cpp` to compile. The stub `#include "payload.h"` at line 8.

---

## Symbol Table

| # | Symbol | C Type | Purpose | Constraints |
|---|--------|--------|---------|-------------|
| 1 | `NIXON_OBF_KEY` | `constexpr unsigned char` (or `int`) | XOR byte used at compile-time by `ObfString<N>` to obfuscate string literals (lines 27, 30). | Must be a single byte in `[0, 255]`. |
| 2 | `NIXON_KEY_SALT` | `const unsigned char[16]` | 16-byte salt fed into `DeriveRC4Key()` for hardware-bound key derivation (lines 1257, 1291, 1292). | Exactly **16 bytes**. All three call sites pass `saltLen=16`. |
| 3 | `NIXON_WORD_ARRAY` | `const char* []` (array of `const char*`) | Encoded/obfuscated payload word array. Each string is decoded via `NIXON_DICT` back into one byte by `DecodeStringArray()` (line 1271). | Must contain exactly `NIXON_PAYLOAD_LEN` entries. Each entry is a NUL-terminated C string. |
| 4 | `NIXON_PAYLOAD_LEN` | `const size_t` (or `const int`) | Number of entries in `NIXON_WORD_ARRAY`; also the byte-length of the reconstructed payload (line 1271). | Must equal the array count of `NIXON_WORD_ARRAY`. Must be ≥ 0. |
| 5 | `NIXON_DICT` | `const char* [256]` | 256-entry dictionary mapping each byte value (0–255) to a unique obfuscation string. `DecodeStringArray()` walks `NIXON_DICT[v]` to find which byte `v` matches each `NIXON_WORD_ARRAY[i]` string (lines 1101–1102). | Exactly **256** NUL-terminated strings. Every entry must be **unique** (bijection); otherwise decoding produces wrong bytes or fails. |
| 6 | `NIXON_DLL_COMPRESSED_LEN` | `const size_t` (or `uLong`) | Size in bytes of the zlib-compressed Python DLL stored in `NIXON_PYTHON_DLL` (line 1314). | Must equal the actual byte-length of `NIXON_PYTHON_DLL`. |
| 7 | `NIXON_DLL_ORIGINAL_LEN` | `const size_t` (or `uLong`) | Uncompressed size of the Python DLL after `uncompress()` (lines 1312–1313). | Must equal the actual decompressed size of the DLL. |
| 8 | `NIXON_PYTHON_DLL` | `const unsigned char[]` | Raw zlib-compressed bytes of the embedded Python DLL (line 1314). | Must be at least `NIXON_DLL_COMPRESSED_LEN` bytes. Byte order is the raw compressed stream as produced by `zlib.compress()`. |
| 9 | `SecureVector` | `using SecureVector = std::vector<unsigned char>` | Binary-buffer alias used for payload data, RC4 output, DLL images, etc. throughout the stub. Required members (by usage): default ctor, `reserve(n)`, `push_back(c)`, size-constructor `SecureVector(n)`, iterator-pair ctor `SecureVector(begin, end)`, `.data()`, `.size()`, `operator[]`. | Must be a drop-in for `std::vector<unsigned char>`. No additional constraints. |

---

## Platform / `#ifdef` Notes

- No `#ifdef` guards are needed in `payload.h`. The stub handles `_WIN64`/`_MSC_VER`/`__GNUC__` internally.
- `SecureVector` is needed on all platforms.
- All other symbols are consumed unconditionally (no conditional compilation gates around them).

## Endianness

- `NIXON_PYTHON_DLL` is consumed by `zlib::uncompress()` as an opaque byte stream — no endianness concern.
- `NIXON_WORD_ARRAY` / `NIXON_DICT` are arrays of C strings — no endianness concern.
- `NIXON_KEY_SALT` is an opaque byte array treated as a sequence of `unsigned char` — no endianness concern.

## Minimal `payload.h` Skeleton

```c
// payload.h
#pragma once
#include <vector>
#include <cstddef>

// ---- obfuscation key ----
constexpr unsigned char NIXON_OBF_KEY = 0x??;

// ---- key derivation salt ----
extern const unsigned char NIXON_KEY_SALT[16];

// ---- payload decoding dictionary ----
extern const char* NIXON_DICT[256];

// ---- encoded payload word array ----
extern const char* NIXON_WORD_ARRAY[NIXON_PAYLOAD_LEN];

// ---- payload length ----
constexpr size_t NIXON_PAYLOAD_LEN = ???;

// ---- compressed Python DLL ----
extern const unsigned char NIXON_PYTHON_DLL[];
constexpr size_t NIXON_DLL_COMPRESSED_LEN = ???;
constexpr size_t NIXON_DLL_ORIGINAL_LEN   = ???;

// ---- secure vector alias ----
using SecureVector = std::vector<unsigned char>;
```
