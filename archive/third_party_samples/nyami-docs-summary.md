# Nyami docs summary (fetched 2026-09-20)

Sources: `https://nyami.cc/` (home, pricing), `https://nyami.cc/features`,
`https://nyami.cc/how-it-works`, `https://nyami.cc/docs/quickstart`,
`https://documentation.nyami.cc/` (= GitBook `https://nyami.gitbook.io/nyami/`,
index at `llms.txt`). All describe the **commercial third-party obfuscator**;
kept here as reference for the `obf-test.py` sample. Quotes are paraphrased
unless marked verbatim.

## Product shape
- Current version **v9.0**, **40+ protection modules**. Pricing: €1 per
  obfuscation (pay-as-you-go), €19/mo dashboard (1000 obfs/mo), €29/mo API
  (500 req/mo); 5 free tokens on signup. Contact: `projectnyami@proton.me`,
  Discord `discord.nyami.cc`.
- Input: single `.py` ≤ 10 MB; target interpreters 3.10–3.14 (default 3.14);
  30 submits/min/IP, 3 concurrent jobs, 5 API keys, 1 h download URLs.
- Positioning quotes (verbatim): "Polymorphic multi-layered obfuscation",
  "HWID encryption, integrity checks, anti-debugger detection and anti-tamper
  mechanisms", "Decompiler breaker and anti-monkey-patcher stop analysis
  tools", "Maximizes security while keeping runtime overhead minimal".

## User-facing macros (source-level, stripped at build)
| Macro | Meaning (per GitBook) |
|---|---|
| `IS_OBFUSCATED` | bool, True only in obfuscated output |
| `GET_HWID()` | returns runner's HWID string |
| `VM_CONFIDENCE` | int 0–100; ≥50 recommended as VM verdict; only with anti-debug High/Extreme. 13 weighted signals: CPUID vendor 30, VM processes 30, hypervisor bit 20–25, registry 25, MAC prefixes 25, WMI BIOS 25, drivers 25, FS artifacts 20, NICs 20, services 20, timing 15, sysinfo 10–15, hw constraints 10 |
| `CRASH()` | terminates single-threaded scripts |
| `SELF_DELETE()` | plain delete (fast) |
| `SECURE_DELETE()` | multi-pass random-pattern overwrite (permanent) |
| `__all__` | preserved through pipeline → obfuscated modules stay importable ("Script Interconnectivity") |
| `DETECT_FILE_TYPE(path)` | `binary_executable`/`python_script`/`shell_script`/`text_file`/`unknown` |
| Anti-Monkey-Patcher config (top-of-file, deleted after build) | `PROTECTED_MODULES`, `VERIFY_FREQUENCY`, `ENABLE_TRACE`, `STRICT_MODE`, `PROTECTION_LEVEL` [0,3], `PREVENT_RELOAD`/`ALLOW_RELOAD`, `HASH_BYTECODE`, `STRICT_INITIAL_CHECK`, `PROTECT_CTYPES`, `PROTECT_GC`, `CRITICAL_BUILTINS`, `SETATTR_WHITELIST` |
| `KOD` | Kill-On-Detection: kills process when VM_CONFIDENCE > 50% (needs anti-debug High/Extreme; normal Win10/11 ≈ 45% with Hyper-V on) |
| Trial | expiry strings: `1s/1m/1hr/1h/1d/1w/1mo`, combinable (`1mo1hr`); also `trial_time` API field (`1h/1d/1w/1mo`) |
| `WIF` | Wrap-In-Function: whole module into one function scope |
| Optimization 0–5 | 0 none; 1 safe; 2 aggressive (may break); 3 = 1 + remove decoys; 4 = 1 + decoys + junk (dashboard default); 5 = 2 + decoys + junk |

## Pipeline (per /how-it-works — 5 phases, paraphrased)
1. **Parse & Prepare**: AST parse → seeded random renamer → minifier →
   number conversion → `__all__` preservation → multi-layer encoding
   (zlib+base64+base32+scramble+reverse).
2. **Obfuscation**: XOR per-session string encryption; per-function
   encrypt-at-call-time; lite-function (best of zlib/bz2/lzma/pyzstd +
   Decompiler Breaker); CFF state-dispatch; MBA (4 levels); opaque
   predicates; junk code; WIF; **Bytecode Transformation** (abstract ISA +
   embedded interpreter = same idea as our VM); bytecode NOPs.
3. **Hardening**: EXTENDED_ARG-corrupting Decompiler Breaker (pylingual/
   pycdc/uncompyle6); 11-method anti-debug; co_code zeroing (Anti-Dump);
   VirtualProtect/mprotect page protection; **Hydra Anti-Tamper**
   (3 cross-verifying daemon threads, kill via ExitProcess/_exit/segfault);
   HMAC-SHA256 anti-monkey-patch challenge-response on exec/eval/compile/
   __import__; **marshal-level integrity via
   ctypes.PyMarshal_ReadObjectFromString with no marshal.loads fallback**;
   8-method anti-VM; audit-hook protection; caller frame validation;
   trace/profile polling every 2 s.
4. **Encryption & Packaging**: AES-256-GCM per-build key/nonce; 8-round
   Feistel white-box (S-box embedded key); 5-scheme polymorphic KDF
   (PBKDF2-HMAC-SHA256, dual-SHA-256, reversed-seed-multi-hash,
   XOR-rotated, seed-split-HMAC); 5 polymorphic stub variants; custom
   **NYCO** code serialization format; pyzstd compression; watermark
   (RuntimeError if removed).
5. **Compile & Distribute (optional)**: PYTOC (via Cython, true in-memory
   exec Win/Linux); PyInstaller spec automation; **HWID lock =
   UUID+MAC+disk-serial → PBKDF2 → AES-GCM AAD**; trial expiry in payload;
   3-pass secure cleanup of build artifacts; version-locked bootstrap
   (version check + audit hooks + env validation).

## API (`POST /api/obfuscate`, header `X-API-Key: nyami_…`)
Multipart `file` (.py) + `settings` JSON: `optimization` 0–5,
`python_version`, `anti_debug` None/Medium/High/Extreme, bools
(`debug/wif/lite_fobf/no_console/func_obf/var_renaming/kod/pyinstaller/
pytoc`), `hwid`, `trial_time`. Returns `jobId`; poll
`GET /api/obfuscate/{jobId}` → `COMPLETED` + 1 h signed `downloadUrl`.

## Version deltas worth noting (from `nyami-changelogs.md`)
- v2.x: VM_CONFIDENCE/KOD, Import Protection, presets, trials.
- v3.1: junk moved OFF the visible outer layer (AI/malware false-positive
  complaints) — matches our sample: outer layer is clean loader glue.
- v3.2: per-function compression, AES-256/**SHA-512**/XOR/ChaCha20/Custom,
  polymorphic key derivation, py3.14.
- v3.3: PYTOC beta (py→pyx→C→machine code, first layer only).
- v3.4: memory protection (keys never in one place), 783 KB → 282 KB.
- v4.5: Anti-Monkey-Patcher replaces Import Protection; HWID re-encrypted.
- v6.0: white-box Feistel, marshal-only deserialization, page protection,
  namespace-isolated executor, **custom CodeType serializer (= NYSER1)**,
  bootstrap XOR-stream+b85+salt, HMAC bytecode integrity, PBKDF2 HWID,
  30 s → 3 s startup, multi-path exec (no single `__nyami__` choke).
- v9.0: per-build randomized kernel exports, IAT vs GetProcAddress
  verification, `_verify_eval` DLL-range checks, scrambled byte-list keys,
  bind-once frame-walk host dict (replaces `_nyk_host_g`), native
  watchdog thread, in-kernel HWID commitment, `_nyk_kill` removed,
  backdoor `NYAMI_*_*` plaintext-dump removed (author: "left by accident…
  forgot to delete it up on releasing"), kernel driver detection beta.

## Cross-reference to our deep dig
- Our sample predates v9.0 (fixed `_nyk_*` exports, settable `_nyk_host_g`,
  `_nyk_kill` present) → v8.x-era build, consistent with its Aug-2026
  timestamp.
- v9.0's "removed NYAMI_*_* plaintext-dump backdoor" is a reminder that
  this vendor ships fast and retracts: treat every versioned claim above
  as point-in-time.
- Highest-value ideas for us (unchanged): NYSER1-style serializer (D),
  env gate (A), secure temp delivery (B), folded QPC check (E).
