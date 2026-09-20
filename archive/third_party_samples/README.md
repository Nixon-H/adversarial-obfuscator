# Third-party samples (not project code)

Quarantined from repo root on 2026-09-20. Nothing here is produced or
consumed by the obfuscator pipeline.

- `obf-test.py` / `obf-test-analysis.py` — byte-identical (md5
  `7ba46b06c1404539d2ac005fbfdefcaf`), 2.9 MB each. Third-party
  `discord.nyami.cc | nyami.cc` protected builds targeting
  CPython 3.14 / Windows AMD64 (`_nyk_z_req = (3, 14, 'nt', 64, 'AMD64')`).
  External reference samples only; no test, script, Makefile target, CI
  job, or doc references them.
- `nyami-changelogs.md` — Discord `#announcements` changelogs v1.1–9.0
  (pasted verbatim 2026-09-20), incl. the v6.0/v9.0 entries that explain
  this sample's internals (white-box Feistel, anti-memory-dump,
  namespace-isolated executor, custom code serializer = NYSER1,
  per-build randomized kernel exports, IAT verification, `_verify_eval`,
  bind-once host dict replacing `_nyk_host_g`, native watchdog, HWID
  commitment in kernel).
- `nyami-docs-summary.md` — summary of nyami.cc + GitBook docs as
  fetched 2026-09-20 (macros, pipeline, API, version deltas).
- `capability-audit-2026-09-20.md` — **current authoritative audit**
  (evening session): live Rust/C/Python read with per-component benefit
  analysis, property-level comparison matrix (C1–C39), preserve-list,
  threat-model gate per Nyami idea, beyond-Nyami scan, decision matrix,
  phased roadmap (Preserve/Improve/Add/Replace/Validate). Supersedes
  `ours-vs-nyami-plan.md` §2–§4 where they differ (corrections in §7).

## Feature-gap analysis (2026-09-20, static only — sample never executed)

Decoded `obf-test.py` loader + stage2 as pure data (outer b85/XOR/sub/lzma
→ 235,691-char stage2; outer SHA256 `8399d59a…`). It is a two-stage
native loader: env gate → outer container → stage2 (reorder `[0,4,3,2,1]`
+ 85-char substitution + b85 + sha256 → zlib → 297 KB Cython `.pyd` via
`memfd` else `mkdtemp` → `ExtensionFileLoader.exec_module` → 28 natives
into `globals()`, `host_g=globals()`, detached self-delete waiter) →
`_MF` (4322 chunks) + `_ITB` (256 B) into native staged decrypt.

### Gaps worth adopting (not yet implemented)
- **A — fail-closed env gate**: pin version/os/arch, `os._exit` on
  mismatch. We only warn, and `NIXON_VERIFY_SKIP_VERSION_CHECK` bypasses.
- **B — secure temp delivery**: stale-prefix purge, `O_EXCL`+`0600`,
  atexit close, detached urandom-overwrite + retry-rmtree waiter. Ours is
  plain `mkstemp` + `exec_module`.
- **C — reorder+substitution container packing**: `MULTIDIM`+`ISR_ENCODER`
  exist as primitives but aren't wired as a loader container.

### Rejected (we already do better)
Int-list string hiding, `__import__` indirection, `settrace` hygiene
(no-op vs our real `gettrace` detection), single-sha integrity (vs our
`runtime/` CRC+ledger), in-file XOR keys, `IsDebuggerPresent`/QPC
(import-only, use unconfirmed — ours actually calls it + `CheckRemote` +
`NtQuery` + hw-bp scan + HW binding: machine-id/UUID/inode/serial).

## Deep dig (2026-09-20, static only — native never executed)

All values below were re-derived independently (Python PE parser +
`llvm-objdump`), not copied from the `.txt` notes. Extraction scripts
were one-off; artifacts (`/tmp/stage2_nyami.py`, `/tmp/nyami_native.pyd`,
`/tmp/nyami_table.bin`) are regenerable from `obf-test.py` alone.

### Inner native blob (re-extracted, hashes match the notes)
- Stage2 5-tuple lens `[38675,103332,100,7165,2070]`, joined in order
  `[0,4,3,2,1]` → 151,342 chars → 256 B translate table (85 live) →
  b85 → 121,073 B, sha256 `f5c82a82…` verified → zlib → **297,472 B MZ
  PE32+** (`0x8664`, ImageBase `0x180000000`, entry `0x3e1ec`,
  Subsystem 2/Windows-GUI, `HIGH_ENTROPY_VA|DYNAMIC_BASE|NX_COMPAT`,
  timestamp Sun Aug 30 03:18:29 2026), sha256 `43689660…`.
- 1 export: `PyInit__6976a7f8f71b4023a6cc`; DLL
  `_6976a7f8f71b4023a6cc.cp314-win_amd64.pyd` (Cython 3.2.8,
  source `_6976a7f8f71b4023a6cc.pyx`).
- 235 imports: 206 `python314.dll` + 13 `KERNEL32` + 6 `VCRUNTIME140` +
  9 CRT + `remove`. 3,713 strings, zero VM/sandbox/network/AES strings.
- Builder leak: `C:/Users/karma/AppData/Local/Temp/aiUilne7z6v\…c`.

### IAT call-graph (new evidence — corrects the notes)
Resolved all 3,753 indirect `callq *disp(%rip)` sites to IAT slots:
- `IsDebuggerPresent` and `QueryPerformanceCounter` are **CALLED
  (1 site each)**, not import-only. QPC site (`0x18003e285`) reads two
  timers and folds them through `xor/and/cmp/cmov` against a stored
  48-bit reference (`0x2b992ddfa233`) — an integrity/timing check on the
  comparison result, not a bare timestamp. IDP site (`0x18003e773`)
  feeds its BOOL into a 3-call follow-up chain with two early exits.
- Dynamic execution inside native is **confirmed active, not candidate**:
  `PyEval_EvalCode` ×5, `Py_CompileStringExFlags` ×3 (with `<frozen>`
  filename), `PyMarshal_ReadObjectFromString` ×2, `PyCode_NewEmpty` /
  `PyUnstable_Code_NewWithPosOnlyArgs` / `PyFrame_New` ×1, `PyNumber_Xor`
  ×6 + `InPlaceXor` ×4, `remove` ×1. Each compile+eval pair sits in its
  own Cython function next to that wrapper's qualified-name string
  (`_37523a…`, `_af3e…`, `_aad4…`, `_f800…`, `_a4f7…`) — i.e. every
  staged wrapper compiles/evals its own code at runtime.
- 2,170/3,753 calls are `_Py_Dealloc` (refcount noise); top real calls
  are `VectorcallMethod`, `Err_Format`, `Dict_SetItem` — ordinary Cython.
- 51 qualified names enumerate the full native API: `nyser_loads` +
  readers (`r_u32/r_blob/r_str/r_strtuple/r_int/r_value/r_code` +
  genexpr scopes), `_reconstruct`/`_reconstruct_parts`/`_verify_eval`,
  13 `_nyk_*` wrappers, `_1a88…` staged dispatcher (6 xrefs, all via the
  same `lea <name>; mov $0x322…; call __pyx_pw_…` + `_verify_eval`-style
  dispatch pattern), 9 hash-named stage functions, `_40ca…` cleanup,
  `_63b0…`, `_fail_pf`.

### NYSER1 (custom code serializer — genuinely novel, adoptable)
- Docstring verbatim: code objects rebuilt via `Code.replace` from a
  template captured from a freshly-defined lambda ("unhookable via
  attribute rebinding"); readers for u32/blob/str/strtuple/int/value/
  code; `_verify_eval` gate. A serialized u32-run blob sits directly
  after the docstring in `.rdata` (`0x18004207f`).
- Nothing like it in our pipeline: our VM interprets bytecode, our
  `encrypt/` is AES-CTR on blocks — nobody serializes live `Code`
  objects through a self-contained lambda-template reconstructor.
- Offline `_MF` decode was **not achieved**: `_MF` = 4,322 elements
  (73–999 chars, avg 653, total 2,823,972; sha256 `9738be07…`), one
  85-char alphabet (with latin-1 high bytes, so outside std-b85 —
  needs its own table); `_ITB` = 256 B, 86 unique, rows 0/4 all-zero.
  No 256 B permutation table exists in `.rdata` (scanned all windows),
  so the MF table/key is built at runtime (seeded shuffle like our
  `ISR_ENCODER`, or per-stage keys via `_get_stage_key`/`_layer_key`) —
  only recoverable by executing the native.

### Dynamic-execution verdict (stays static)
Cannot run here: PE32+ Windows DLL needing `python314.dll` + CPython
3.14 + Win32 loader; host is Linux/py3.13, `wine` absent
(`qemu-x86_64` is user-mode ELF-only, can't load PE). Only path is an
isolated Windows 11 x64 VM, py3.14, snapshot, offline, copies only —
hook `exec`/`exec_module` to dump stage2+native, wrap `_nyk_*` to log
`(_MF` index, key, plaintext) during the `_1a88` call, `dis` the NYSER1
output, stub the destructive waiter first.

### Updated adopt-list (supersedes the 2026-09-20-morning list)
1. **D — NYSER1-style code-object serializer** (new, highest value):
   self-contained lambda-template `Code.replace` reconstructor; kills
   marshal-based pipelines and survives `marshal` format changes.
2. **A — fail-closed env gate** (unchanged).
3. **B — secure temp delivery** (unchanged).
4. **E — QPC folded-check pattern** (new, small): dual-timer read
   folded via xor/and/cmp/cmov against a stored reference instead of a
   bare threshold compare.
5. **C — reorder+substitution container packing** (unchanged, bigger).
6. **F — per-wrapper compile+eval** (new, note only): each staged
   function compiling its own `<frozen>` source at runtime rather than
   one central loader — matches our fragmentation direction.
