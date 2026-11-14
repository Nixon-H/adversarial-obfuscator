# Audit 2026-11-13 round 2 — extreme line-by-line audit, every file / function / line

Scope: same first-party production scope as round 1 (533 Python files ~227k
lines + Rust/C), read **in full** by 10 reader shards (A1, A2, B1, B2, C1, C2,
S1–S4), each file paged to EOF with `read_file` — no grep skimming. Reader
agents executed their own reproductions; the auditor then re-verified a
cross-shard sample by execution (marked **[exec-me]** below). Findings marked
**[exec-agent]** were reproduced by the reader agent, **[read]** by line-level
reading only.

Verification status legend: **[exec-me]** re-verified by execution in the
current tree · **[exec-agent]** executed by the reader agent · **[read]** read
+ callee trace only.

Class legend: **ARTIFACT** = affects shipped obfuscated/licensed binaries ·
**PROOF** = soundness of the proof/validation tooling itself · **BUILD** =
build/CI/benchmark tooling hygiene.

## Round-2 headline findings (HIGH)

### ARTIFACT — protections that ship broken or self-defeating

- **[HIGH][exec-me] `encrypt/encrypt.py:77-91` + `encrypt/stub.py:161`** —
  Stage-4 "encryption" embeds the full AES-256-CTR keystream verbatim in the
  appended stub (`keystream=all_keystream` confirmed in source). CTR
  ciphertext XOR embedded keystream = plaintext; static extraction needs no
  key. Stage 4 provides zero confidentiality. ARTIFACT.
- **[HIGH][exec-agent] `encrypt/stub.py` (five sites)** —
  shellcode anchor off-by-one (`rbx_anchor = 6`, should be 5) shifts every
  header field read by one byte, and the keystream load uses SIB base `r14`
  (uninitialized) instead of `r8` (`0x0e` vs `0x08`). objdump-verified: the
  decryptor XORs the wrong bytes and jumps to the wrong entry. ARTIFACT.
- **[HIGH][exec-agent] `encrypt/elf.py:234-357`** — `replace_text` splices
  data then writes section headers at the stale `e_shoff`; on a stock gcc
  binary the output has garbage `sh_link`s and segfaults (exit 139).
  ARTIFACT.
- **[HIGH][read] `obfuscator/core/sources.py:2855-2856`** —
  `ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE` on the
  key-shard fetch (TOR client source). MITM can serve key shards. ARTIFACT.
- **[HIGH][exec-me] `obfuscator/llm_resilient.py:204-213`** —
  `ContextCollapseObfuscator` wraps the whole original function body in
  `try/except Exception: pass`; executed: `f(5)` on `raise ValueError`
  returns `None`. Wired into the real pipeline via `phase01_obfuscate.py`.
  ARTIFACT.
- **[HIGH][exec-me] `obfuscator/adaptive_rewriter.py:279-300`** —
  `_encode_strings` base64-corrupts string constants in place with no
  decoder; executed: `f()` returns `'cmVzdWx0LW9r'` instead of `'result-ok'`.
  Reachable via benchmark action `add_string_encoding`. ARTIFACT.
- **[HIGH][exec-agent] `obfuscator/adaptive_rewriter.py:107-127`** —
  homoglyph renaming misses `Attribute.attr`/`keyword.arg` → AttributeError/
  TypeError at runtime. ARTIFACT.
- **[HIGH][exec-agent] `obfuscator/function_intent.py:62,73-78`** — misleading
  rename map has no uniqueness check: two functions renamed to the same name,
  executed caller returned 24 instead of 33 (silent wrong result). ARTIFACT.
- **[HIGH][exec-me] `obfuscator/dataflow.py:520-531,111-152,202-205`** —
  auto-detected "sensitive vars" include function params; executed:
  `NameError: name 'data_enc' is not defined`. AugAssign and self-referencing
  RHS also unhandled. ARTIFACT.
- **[HIGH][exec-agent] `obfuscator/llm_resilient.py:220-226`** — string
  rewriting crashes `ast.unparse` on any f-string with a ≥4-char literal
  (`ValueError: Unexpected node inside JoinedStr`); also kills `__doc__` and
  static `__all__`. ARTIFACT.
- **[HIGH][exec-me] `obfuscator/provenance.py:305-325`** —
  `StringEncoder.visit_Module` never calls `generic_visit`, so
  `encode_sensitive_strings` is a silent no-op (verified: no `generic_visit`
  call in the method); protocol strings stay cleartext in the artifact plus
  dead decode stubs are emitted. ARTIFACT.
- **[HIGH][exec-agent] `obfuscator/core/sources.py:841-858`** —
  `_apply_ast_mutation_inner` returns un-obfuscated source on error. ARTIFACT.
- **[HIGH][read] `obfuscator/core/sources.py:6629`** — FUNC_NET uses
  unauthenticated DNS TXT as key bytes. ARTIFACT.
- **[HIGH][read] `obfuscator/core/sources.py:2882-2910`** — Shamir mod
  2^127−1 does not round-trip 32-byte keys. ARTIFACT.
- **[HIGH][exec-agent] `vm/bytecode_compiler.py` vs `vm/interpreter.py`** —
  encoder writes type-tagged operands, interpreter reads raw bytes; VM cannot
  execute its own bytecode. ARTIFACT.
- **[HIGH][exec-agent] `vm/ephemeral_isa.py:85-86,211-236`** — `remap_bytecode`
  consumes the entire stream after any CALL/RET; reverse remap is
  identity-wrong. ARTIFACT.
- **[HIGH][exec-agent] `vm/__init__.py:188-189,289,309`** — generated C
  interpreter switches on the XOR-obfuscated dispatch table without
  de-XOR (`(void)key;`) → every opcode misdispatches. ARTIFACT.
- **[HIGH][read] `vm/__main__.py:146-147`** — `python -m vm compile` writes
  seed AND derived key into the output JSON next to the encrypted bytecode.
  ARTIFACT.
- **[HIGH][exec-agent] `irgen/bitslice.py:271,274-289,349-361`** — bitsliced
  IR `sub` is deleted (result dangles), `mul` computes `−a` (source confirms:
  loop adds shifted copies of `a` only, `b_bits` unused — **[exec-me] source**;
  agent brute-forced `cmp_lt_ir`: ~51% of signed 8-bit pairs wrong).
  `llvmgen/lower.py` feeds it into `slt`. ARTIFACT.
- **[HIGH][exec-agent] `irgen/compile.py:757-790`** — `assert`/`raise`
  silently dropped (license checks fail open), `while…else` dropped, chained
  comparisons miscompiled. ARTIFACT.
- **[HIGH][exec-agent] `llvmgen/passes.py:381,403,410-411`** — "substitute"
  pass rewrites `a-b` as `a-b-1` (5−3 → 1). ARTIFACT.
- **[HIGH][exec-agent] `irgen/microjit.py:838,865,575,794`** — register
  remap renames RSP/RBP, independent prologue/epilogue shuffle, NOP sled at
  byte granularity (mid-instruction), ModRM-less opcodes edit the next
  instruction's byte. ARTIFACT.
- **[HIGH][exec-agent] `irgen/watermark.py:566,695-702,842,902`** — detector
  cannot distinguish 0/1 (returns all-ones), BCH decode broken, CLI embed
  TypeError. ARTIFACT.
- **[HIGH][exec-agent] `irgen/jit_template.py:244,160-162,110`** — CLI
  `encrypt` defaults to a zero key (blob = zlib plaintext), integrity hash
  covers metadata not payload, `%param` substring replace corrupts slots.
  ARTIFACT.
- **[HIGH][exec-agent] `irgen/rop_compiler.py:706,615` + `irgen/mutation.py:104`**
  — gadget search pattern mismatch, hardcoded non-PIE base, `remap_bytecode`
  maps operands too. ARTIFACT.
- **[HIGH][exec-agent] `irgen/port_entangle.py` (three sites)** — epilogue
  appended after module end (invalid LLVM); opaque predicate true with
  p≈1−2⁻⁶⁴ → `__corrupt_key()` fires on virtually every run. ARTIFACT.
- **[HIGH][exec-agent] `irgen/tee_partition.py:138,150`** — salted builtin
  `hash()` fn ids differ across processes (2173068329 vs 2055449406) → host
  stub never matches enclave dispatcher. ARTIFACT.
- **[HIGH][exec-agent] `irgen/class_specializer.py:173-189`** — full
  Fisher-Yates shuffle of instructions ignoring data dependencies. ARTIFACT.
- **[HIGH][exec-agent] `irgen/variant_pool.py:369-385,358`** — renamer skips
  children (`NameError: name 'M' is not defined`), loop unroll doesn't bind the
  loop var. ARTIFACT.
- **[HIGH][exec-agent] `irgen/fragmentation.py:166,203,243`** — fragments with
  empty entry blocks, coordinator drops 8/8 calls, salted `hash()` names.
  ARTIFACT.
- **[HIGH][exec-agent] `irgen/chaff_circuits.py:~640-760`** — chaff spliced as
  `def` inside a list literal → SyntaxError; opaque routing inverted. ARTIFACT.
- **[HIGH][exec-agent] `llvmgen/lower.py:569,661`** — GEP base always typed
  `i32` (llc type error); `shr`→`lshr`/`div`→`sdiv` breaks negative-operand
  Python semantics. ARTIFACT.
- **[HIGH][exec-agent] `llvmgen/integrity.py:9,19`** — compile-time CRC of IR
  *text* vs runtime CRC of `.text` can never match; check never called. ARTIFACT.
- **[HIGH][exec-agent] `scripts/fragment/micro_fragment.py:186-192`** —
  "wipe" zeroes a copy, `exec` with `_SAFE_BUILTINS` auto-gets real
  `__builtins__`, `assert` vanishes under `python -O`. ARTIFACT.
- **[HIGH][read] `scripts/distributed/remote_unlock.py:305-326`** —
  `_fallback()` on any network/crypto error, cached token honored with a
  +300 s grace past expiry (lines 308/326 confirmed). ARTIFACT.
- **[HIGH][read] `scripts/distributed/challenge_response.py:170-186,98-111`** —
  self-destruct never fires on failures; per-instance secret can't match
  across parties. ARTIFACT.
- **[HIGH][read] `scripts/multi_binary.py:220`** — serialized `cross_keys`
  leak fragment AES keys into the build artifact. ARTIFACT.
- **[HIGH][read] `scripts/phases/phase08_rop.py:104`,
  `phase_rolling_keys.py:66,71`, `phase30_micro_fragment.py:52`** — keys
  written plaintext into `build/*.json`. ARTIFACT.
- **[HIGH][read] `scripts/gpu/hybrid_protection.py`** — non-inverse
  encrypt/decrypt + hardcoded keys. ARTIFACT.

### PROOF — the verification/proof tooling certifies false results

- **[HIGH][read] `scripts/proofs/proof_carrying.py:157-186`** —
  `verify_certificate` re-checks only stored formulas, unsigned: `(assert
  false)` (unsat) verifies as "equivalent". PROOF.
- **[HIGH][read] `scripts/proofs/proof_carrying.py:196-217`** — vacuous
  self-identity certificates `validated=True` per transformation. PROOF.
- **[HIGH][exec-me] `scripts/validation/ast_to_smt.py:229-245,208,176`** —
  executed: `a**b → 1`, `c//d → UDiv`, `e % f → SRem`, `g >> h → LShR`;
  unsupported exprs → 0; if/else output var bug. The "primary validation
  gate" proves false equivalences. PROOF.
- **[HIGH][read] `scripts/validation/ir_to_smt.py:61,237`** — multi-block CFGs
  encode as contradictions (unsat ⇒ "equivalent"); phi nodes unconstrained
  free booleans. PROOF.
- **[HIGH][exec-agent] `scripts/proofs/watermark_survivability.py:169-178,251,329`**
  — free-variable XOR counts as survival (executed: survived=True for
  CFG_FLATTEN); solver unknown/timeout treated as survived. PROOF.
- **[HIGH][exec-agent] `scripts/proofs/vm_correctness.py`** — trace proof
  reuses one symbolic state → vacuous `equivalent=True`. PROOF.
- **[HIGH][exec-agent] `scripts/evaluation/angr_bench.py`,
  `phases/phase_confidence.py:130`** — fabricated constant scores/samples
  (`[85.0,…]`, `values*3`). PROOF.
- **[HIGH][exec-agent] `scripts/artifacts/builder.py:247`** — verification
  report hardcodes `"passed": True` → "ALL PASSED" regardless of metrics.
  BUILD (report integrity).
- **[HIGH][exec-agent] `scripts/phases/phase_artifacts.py:208-224`** — all
  threats hardcoded `"mitigated"`; missing metrics replaced with fabricated
  0.2→0.8. BUILD (report integrity).
- **[HIGH][exec-agent] `scripts/synthesis/optimizer.py:69-71`,
  `synthesis/engine.py:124`, `conflicts/detector.py:85`** — inverted
  prerequisite/REQUIRES checks. BUILD.
- **[HIGH][exec-agent] `scripts/evaluation/ai_proof.py:151,216` +
  `benchmark/llm_api.py:96-98`** — model/API failure scored as max
  resistance (10/10); silent static fallback unmarked; proxy URL with
  password written to logs (`:42-45`). BUILD.
- **[HIGH][exec-agent] `scripts/diversity/generator.py` (one block)** — global
  monkey-patch of `secrets.*` to seeded PRNG during variant generation;
  retry silently changes the pass set. BUILD.

### BUILD — fail-open gates and hygiene

- **[HIGH][read] `obfuscator/core/utils.py:720-740`** —
  `_verify_download_zip` proceeds with only a warning when sidecars are
  absent; callers ignore the return. (Docstring confirms the no-sidecar
  paths "proceed".) BUILD.
- **[HIGH][exec-agent] `obfuscator/core/transforms.py:2210-2222`** —
  `CodeChecksumInjector._nx_verify` swallows its own RuntimeError and is
  never called. ARTIFACT-adjacent.
- **[HIGH][exec-agent] `obfuscator/core/transforms.py:612-640,1588-1605`** —
  `visit_Nonlocal` on a param → SyntaxError (reproduced);
  `BogusExceptionHandler` swallows real exceptions without
  `import builtins` (reproduced). ARTIFACT.
- **[HIGH][read] `obfuscator/core/transforms.py:718-843`** — silent
  ChaCha→XOR downgrade with inline key. ARTIFACT.
- **[HIGH][read] `obfuscator/core/utils.py:1810-1850`** — UPX
  download-and-exec with optional sha256 pin. BUILD.
- **[HIGH][read] `obfuscator/core/utils.py:854,1373`** — unsanitized
  interpolation into GitHub workflow YAML. BUILD.
- **[MED][exec-agent] `obfuscator/replay_poison.py:104-125`** — emits
  `os.urandom` before the module's own `import os` → NameError at load
  (executed). ARTIFACT.
- **[MED][read] `obfuscator/trial_bind.py:651-654`** — emitted gate's
  no-`O_NOFOLLOW` fallback writes through symlinks (Windows), contradicting
  its fail-closed docstring. ARTIFACT.
- **[MED][read] `obfuscator/reorder_pack.py:28-55`** — `randbelow` infinite
  loop for n > 65536 → build hangs on > ~268 MB payloads. BUILD.
- **[MED][exec-agent] `obfuscator/rep_diversify.py:66-160`** — f-string
  literal rewrite crashes `ast.unparse` for 144/300 seeds (48%). ARTIFACT.
- ~60 further MEDIUM and ~70 LOW findings are itemized per-file in the shard
  reports; the recurring MED themes are: fail-open defaults in gates/scorers
  (zero-baseline ⇒ pass, missing report ⇒ 1.0/0.5, `is not None` vs bool,
  `except Exception: pass` fallbacks), salted builtin `hash()` in generated
  code (non-reproducible + cross-process breakage), plaintext seeds/keys in
  `build/*.json` configs, length-extension SHA-256 "MACs" instead of HMAC,
  non-constant-time compares, path traversal in `os.path.join` ids, HTML/MD/
  DOT/YAML injection in generated reports, symlink TOCTOU in unlink/lock
  helpers, and API keys in argv/logs.

## Fix status (2026-11-13, rounds 3-5)

All HIGH/MEDIUM findings from this round are fixed, with regression tests in
`tests/test_audit_round2.py` (19 tests), `tests/test_audit_round3.py` (25),
`tests/test_audit_fixes.py` (10), plus the shard-specific suites
(`test_bitslice.py` 8192 differential cases, `test_irgen_semantics.py`,
`test_jit_template.py`, `test_llvmgen_integrity.py`, `test_multi_binary.py`,
`test_challenge_response.py`, `test_download_zip_gate.py`,
`test_artifact_passed.py`, `test_ast_prologue.py`,
`test_audit_round2_vm.py`, `test_crypto_fallback.py`,
`test_no_self_destruct.py`).

An independent OpenCode verification session found 13 regressions in the
first fix pass (phase_confidence `_skipped` crash, dataflow AugAssign
non-linear ops, two `__future__` insertion breaks, adaptive homoglyph
external-attribute renames, ast_to_smt string constants, builder passed
schema, transforms nonlocal scope leak, proof_carrying constant inputs,
llm_resilient docstring, BogusExceptionHandler nested import, licensing
tmp mode) plus two ineffective fixes (utils zip callers ignoring the
return, vm_correctness hmac_tag not exported) and one missed key leak
(phase12 chain_secret). All are fixed in rounds 3-5 with the
`ast_prologue.py` helper insertion (after docstring + `__future__`) as the
systemic fix for the insertion-order class.

## Runtime key source closed (2026-11-14)

The last asterisk — encrypt.py's embedded keystream — is now fixed with a
**run-time key source**: the embedded keystream is XOR-masked with a
32-byte key stored in a 0600 sidecar (`<output>.key`), the stub reads it
from the embedded path at run time, and exits(1) without it. Verified by
execution: the artifact decrypts and runs (returns 42) only with the key
file; without it exit(1); static extraction (ciphertext XOR embedded
masked keystream) yields garbage. `NIXON_ENC_RUNTIME_KEY` pins the key by
hex env instead of urandom. Regression tests:
`tests/test_encrypt_runtime_key.py` (4).

Also closed: challenge_response now supports `shared_secret` (two parties
agree), self-destruct gates every path, and the challenge signature check
is constant-time (`hmac.compare_digest`). multi_binary's master index
serializes **zero** cross keys (holders re-derive from their own secret).

## Server-side detection wired (2026-11-14)

The real licence/chain gates now report violations to the operator's
webhook (`--access webhook=URL`) — previously only the decoy gates fired
alerts and a real licence violation died silently:

- `_nx_licence_alert(reason)` emitted in the licence helpers; fires
  `licence-pin-mismatch`, `licence-chain-failed`,
  `licence-chain-owner-mismatch` and `licence-missing` through the same
  renamed relay the loader body defines (`FUNC_TRIGGER_ALERT`), using the
  deterministic VARS rename (an apply_vars-based rename randomized per
  call and would have referenced a name nothing defines — caught by the
  execution test).
- Best-effort: at bootstrap time the relay is not defined yet, so the
  alert skips silently — the refusal itself never depends on the alert.
- Regression tests: `test_licence_gate_reports_pin_tamper_to_webhook`,
  `test_licence_gate_reports_missing_token_to_webhook`,
  `test_alert_is_best_effort_without_the_relay`.
- The receiver side is the operator's webhook endpoint: log
  `licence-*` events per HWID to detect one licence used from many
  machines (cloning) — that is the server-side detection layer.
- **Extended to every kill path (2026-11-14):** `_nx_kill` now reports
  `kill:<reason>` and `_nx_strict_fail` reports `strict:<reason>` to the
  same relay BEFORE the wipe/exit — so every armed gate (trial, watermark,
  integrity, stdlib, snapshot, geo, kod, licence) produces a server-side
  event, not just the licence helpers. The report is bounded by the
  relay's 3 s timeout and can never prevent the wipe+exit. Verified: the
  emitted kill alerts before `_exit(137)` and the wipe still zeroes the
  key material (`tests/test_audit_round2.py::test_kill_ladder_reports_to_alert_before_wipe`).
- **Extended to the direct-exit kill sites (2026-11-14):** the four
  payload-execution kill sites that bypass `_nx_kill` (payload MAC
  mismatch, MAC check error, merkle self-integrity failure, loader
  state-machine crash) now report `kill:payload-mac-mismatch`,
  `kill:payload-mac-error`, `kill:self-integrity` and
  `kill:state-machine-crash` through the same relay before their
  `_exit(137)`. Verified: tampering a loader string fires
  `kill:self-integrity` to the webhook and the artifact still dies with
  the merkle evidence.
- Coverage is now complete: every termination path in the loader (kill
  ladder, strict detections, direct exits, licence helpers, decoys)
  reports server-side. The only silent terminations left are the native
  encrypt stub (no Python at that stage — cannot webhook) and the
  bootstrap-time licence failures (the alert relay is not yet defined;
  the refusal itself is unaffected).

Remaining open: the dormant vm/irgen cross-stage differential test suite
(the modules themselves now have their specific bugs fixed and tested),
and the encrypt-stub `key_path` distribution model (key file must be
delivered to the runtime host out of band).

## Verified clean this round (full read + execution where applicable)

- `obfuscator/chacha20.py` — RFC 8439 vector, AEAD verify-before-decrypt,
  `compare_digest` (re-confirmed this round).
- `encrypt/aes.py` — FIPS-197 vector match; CTR roundtrip.
- `obfuscator/section_split.py`, `watermark_gate.py`, `vm_dispatch.py`
  (240/240 differential tests), `name_gate.py`, `opt_levels.py`,
  `residue_random.py`, `string_crypto.py`, `key_emit.py`, `kill_ladder.py`,
  `audit_hook.py`, `frozen_snapshot.py`, `py_matrix.py`, `nyser.py`,
  `split_bootstrap.py` combine math, `trial_bind.py` build-time gate
  (ok/expired/tampered/rollback all correct), `lowering.py`/`lowering_shim.py`,
  `adversarial.py`, `anti_rea.py`, `attention_poison.py`,
  `classification.py`, `clock_bias.py`, `hwid.py`, `secure_temp.py` core.
- `llvmgen/assemble.py`, `llvmgen/codegen.py`, `irgen/__init__.py`,
  `irgen/__main__.py`, `llvmgen/__main__.py`, `encrypt/__main__.py`,
  plus ~60 scripts files listed clean in shards S2/S4.

## Themes / systemic causes

1. **Each pipeline stage was written against a different contract than its
   neighbors** — VM encoder vs interpreter operand formats, stub anchor
   offsets vs emitted bytes, compile-time CRC vs runtime CRC, GEP type table
   key mismatch. Cross-stage integration tests are the missing control.
2. **Fail-open is the default posture** in gates, scorers, verifiers and
   report generators (empty ⇒ pass, unknown ⇒ survived, missing ⇒ 1.0,
   exception ⇒ proceed). Round 1 fixed the six worst gate emitters; the long
   tail is here.
3. **Key material co-located with ciphertext** — embedded CTR keystream, seed
   + key in VM JSON, plaintext seeds in `build/*.json` configs, cross_keys in
   multi_binary output, proxy/API keys in logs and argv.
4. **Salted builtin `hash()` in generated code** — non-reproducible builds and
   cross-process ID mismatches (tee_partition, fragment_compiler,
   poly_engine, provenance poisoner, vm bytecode_compiler).
5. **Transform passes that break semantics while claiming to preserve them**
   (llm_resilient swallow, bitslice mul/lt, dataflow NameErrors, adaptive
   string corruption, optimizer inverted prereqs, sub→a−b−1). A differential
   semantics test over every transform would catch this class.

## Fix status (2026-11-13, same day)

| Finding | Status |
|---|---|
| CERT_NONE on key-shard/auth TLS (HIGH) | **Fixed** — both TLS client copies (TOR_CLIENT + GC_MANIPULATION) use the verifying default context. |
| Shamir mod 2^127-1 no round-trip (HIGH) | **Fixed** — chunked 3x(<=15-byte) Shamir over GF(2^127-1); round-trips every 32-byte key (regression-tested incl. 0x00*/0xff*/high-bit). Two real bugs found while fixing: chunk coefficients must be drawn once (not per share) and chunk size must respect the field. |
| Public DNS-TXT key shortcut (HIGH) | **Fixed** — both FUNC_NET copies no longer key off "key.nixon.auth" (a public constant). |
| `_apply_ast_mutation` returns un-obfuscated source (HIGH) | **Fixed** — strict mode: production callers (`pipeline.py`, 6 sites) now raise instead of returning the input. Non-strict warn-and-return kept for test call sites. |
| llm_resilient except-pass swallow (HIGH) | **Fixed** — the decoy handler re-raises; executed: `raise` propagates. f-string crash fixed (JoinedStr parts skipped); docstrings and `__all__` stay cleartext. |
| adaptive_rewriter string corruption (HIGH) | **Fixed** — string encoding is reversible (module-level decoder injected AFTER encoding so its own literals are not re-encoded); executed end-to-end. |
| adaptive homoglyph misses Attribute/keyword (HIGH) | **Fixed** — two-pass renaming: def/arg names decide the map, then Name/Attribute.attr/keyword.arg are rewritten only for mapped identifiers (external attrs untouched). |
| function_intent rename collisions (HIGH) | **Fixed** — collision-free map (suffix until unique); executed. |
| dataflow params-as-sensitive + AugAssign (HIGH) | **Fixed** — parameters are not candidates; AugAssign keeps the affine invariant (`enc += A*v` — the first attempt used `encode(v)` which added a spurious +b and was caught by the execution test); non-numeric values now raise an explicit TypeError instead of a cryptic OverflowError. Also: standalone `AffineStateEncoder` A values forced odd (invertible mod 2^64). |
| provenance StringEncoder no-op (HIGH) | **Fixed** — visit_Module recurses; executed: protocol string is fragmented+decoded, not cleartext. |
| VM CLI seed+key JSON (HIGH) | **Fixed** — key material goes to a 0600 sidecar, container JSON carries bytecode only. |
| Research sidecar keys in build/*.json (HIGH) | **Fixed** — phase08_rop `enc_key`, phase_rolling_keys `chain_secret`/`rolling_key`, phase30_micro_fragment `master_key` are `<withheld>`. |
| gpu hybrid hardcoded key (HIGH) | **Fixed** — the dead DEFAULT_ENCRYPT_KEY constant removed (per-fragment keys already derive from the run seed); encrypt/decrypt verified as proper inverses. |
| ast_to_smt false mappings (HIGH/PROOF) | **Fixed** — `/`, `//`, `%`, `**` are UNSUPPORTED (the proof declines instead of mapping to 1/UDiv); `>>` uses arithmetic shift; missing-else keeps the previous value instead of 0. |
| ir_to_smt multi-block contradiction (HIGH/PROOF) | **Fixed** — only single-block CFGs are proven; multi-block DECLINES. |
| proof_carrying tamper (HIGH/PROOF) | **Fixed** — verification is expr-bound: the certificate stores the original/transformed S-EXPRESSIONS and the verifier rebuilds the difference query; `(assert false)` JSON now verifies as NOT equivalent. Legacy certs fail closed. |
| watermark_survivability unknown=survived (HIGH/PROOF) | **Fixed** — only a definitive sat counts as survived. |
| vm_correctness certificate tamper (HIGH/PROOF) | **Fixed** — certificates carry an HMAC tag (NIXON_PROOF_HMAC_KEY). |
| builder.py / report_generator / phase_artifacts fabrication (HIGH) | **Fixed** — "passed" computed from metrics (missing = not passed); threats are "declared" not "mitigated"; missing metric reports stay missing (no fabricated 0.2->0.8). |
| phase_confidence single-sample fabrication (HIGH) | **Fixed** — insufficient samples are skipped and reported, not tripled. |
| ai_proof failure=10/10 + llm_api proxy creds in logs (HIGH) | **Fixed** — model failure scores 0; static fallback results are marked "static_estimate"; proxy logs redact credentials. |
| remote_unlock +300 s grace (HIGH) | **Fixed** — expired tokens are expired (both sites). |
| utils zip unverified proceed (HIGH) | **Fixed** — signatures present without a key REFUSES extraction. |
| UPX unpinned download-and-exec (HIGH) | **Fixed** — a sha256 pin is mandatory; unpinned downloads are refused and deleted. |
| utils workflow YAML/python injection (HIGH) | **Fixed** — payload filename and python-version are validated in both workflow builders. |
| rep_diversify / replay_poison / reorder_pack (MED) | **Fixed** — f-string guard (JoinedStr depth); replay_poison's import-order NameError was already fixed in the current tree; reorder_pack's randbelow now has the two-byte path (n>256) with the >65535 case handled by rejection sampling over multi-byte reads. |
| challenge_response self-destruct/secret (HIGH) | **Fixed (round 3)** — the threshold was checked on the *success* path, so a peer that failed N times and then answered correctly still tripped the lock. Failures now go through `_record_failure`, which counts and locks at the threshold. The demo is still inert (result JSON is never read back). |
| encrypt.py keystream embedding + stub shellcode + elf.py segfault (HIGH) | **Fixed (round 3)** — stub rewritten (correct disp32 header loads, SIB base r8, mprotect RWX→RX, `push rdx`/`pop rdx` around the ELF entry, `cpuid` serialisation); `replace_text` shifts `e_shoff`/`e_phoff` and all program headers past the splice; the stub now lives in a new executable `PT_LOAD` appended at EOF so no existing vaddr moves. Verified by execution: `gcc hello.c` → `encrypt_binary` → the output prints the original text and returns the original exit code. Output file now keeps the source's permission bits (it was written 0644 and could not be run). Round 5 adds the runtime key sidecar (see below), so the keystream is no longer usable from the stub alone. |
| vm/irgen/llvmgen dormant research modules | **Fixed (round 3)** — see the round-3 table below. |
| multi_binary cross_keys in master_index (HIGH) | **Fixed (round 3)** — cross keys are no longer serialized (they are the fragment encryption keys; anyone holding the index could decrypt every share). Derivation is now symmetric, so the ring key for the last binary matches. Round-trip verified. |
| FUNC_NET DNS TXT keying / transforms checksum wiring / smell inventory | **Fixed (round 4)** — FUNC_NET's success and failure branches both returned 32 zero bytes; a valid response now returns the 32-byte key from the response body. `CodeChecksumInjector` rewritten (see round 4). Smell inventory filed as `docs/SMELL-INVENTORY.md`. |

Regression tests: `tests/test_audit_round2.py` (18 tests) + `tests/test_audit_fixes.py` (round 1) + `tests/test_audit_round3.py` (19 tests) + `tests/test_bitslice.py` (24,576 exhaustive cases) + `tests/test_audit_round2_vm.py` (11 tests).

## Round 3 (2026-11-13, later the same day)

Every item below was reproduced before the fix and re-checked after it.

| Finding | Status |
|---|---|
| `irgen/bitslice.py` `_bitwise_sub_ir` returned `[0]` (one bit) | **Fixed** — returns the full two's-complement result. |
| `_bitwise_mul_ir` ignored `b_bits` (computed `a * (2**n - 1)`) | **Fixed** — each shifted copy is gated by `b[i]`. |
| `_bitwise_cmp_lt_ir` compared the wrong way and lost the first differing bit | **Fixed** — sign bits decide when they differ; the magnitude chain latches the first bit where `b` has the 1 while all higher bits are equal. Exhaustive 6-bit test: 24,576 cases. |
| `shl`/`shr` by a non-constant silently became a no-op | **Fixed** — the instruction is left intact instead of being replaced by a wrong constant shift. |
| `llvmgen/passes.py` `sub` substitution computed `a - b - 1` | **Fixed** — `a + (~b + 1)`. |
| `llvmgen/lower.py` GEP `ptr_type` looked up `lstrip("%")` against a `%`-keyed dict | **Fixed** — every GEP base was typed `i32`. |
| `llvmgen/integrity.py` CRC of the IR text compared against a runtime memory region, never called | **Fixed** — the module text is embedded as a blob, the check CRCs that blob, and `@llvm.global_ctors` runs it at startup. Verified: clean build exits 3, tampered blob exits 255. |
| `vm` encoder wrote type-tagged operands, both interpreters read raw bytes | **Fixed** — the wire format carries no type tags; widths come from the opcode. Compile → encode → interpret now returns the expected value. |
| `vm/ephemeral_isa.remap_bytecode` consumed the rest of the stream after CALL/RET | **Fixed** — fixed per-opcode widths (CALL 4, RET 0, FUSED_CMP_JMP 9). |
| `vm/__init__.py` C dispatch ignored the XOR key | **Fixed** — `VM_DISPATCH_KEY` is emitted and applied; generated C compiles clean. |
| `vm/__main__.py` `with os.open(...)` (raw fd is not a context manager) | **Fixed** — explicit `os.open`/`os.write`/`os.fsync`/`os.close`. |
| `irgen/jit_template.py` zero-key default and silent key padding | **Fixed** — `--key` is required and must be 32 bytes; `encrypt_template` rejects short keys. |
| `irgen/microjit.py` shuffled RSP/RBP, rewrote SIB/RIP-relative `rm`, inserted REX bytes mid-stream, inserted NOPs inside instructions | **Fixed** — stack pointers pinned, SIB/RIP-relative operands skipped, instruction length never changes, NOPs land only on instruction boundaries. |
| `irgen/watermark.py` P0 blocks contained arithmetic (every bit decoded as 1), watermark block was its own successor, `ret` carried a type operand | **Fixed** — round-trip verified: `ABCD` embeds and detects as `abcd`. |
| `irgen/port_entangle.py` epilogue appended outside the function, hex integer literals, prologue before the entry label | **Fixed** — epilogue lands before the terminator, prologue after the first block label, packed seed emitted in decimal. `llc` accepts the output. |
| `irgen/tee_partition.py`, `fragmentation.py`, `rop_compiler.py` used salted `hash()` | **Fixed** — stable BLAKE2b ids. |
| `irgen/class_specializer.py` shuffled definitions past their uses | **Fixed** — only runs of independent instructions are reordered. |
| `irgen/variant_pool.py` renamed builtins and left parameters unbound | **Fixed** — only bound names are renamed, parameters are renamed at `arg` and at every use; the renamed function still runs. |
| `irgen/fragmentation.py` coordinator XORed indices and dropped most calls | **Fixed** — the permuted sequence is used as-is; every fragment is called. |
| `irgen/chaff_circuits.py` rotate emitted a shift by the full width | **Fixed** — complement is `(0 - s) & mask`. |
| `irgen/rop_compiler.py` stub parked the cookie in RSI instead of pushing it | **Fixed** — `mov rax, imm64; push rax`. |
| `scripts/fragment/micro_fragment.py` wiped a copy, `assert` under `-O` | **Fixed** — decrypts into a `bytearray`, zeroes it in `finally`, length mismatch returns an error. |
| `scripts/conflicts/known_conflicts.py` 14 `REQUIRES` entries encoded backwards | **Fixed** — converted to `INCOMPATIBLE`. This was aborting every build that used `--skip-llvmgen` or `--skip-irgen` with a blocking conflict. |
| `scripts/runtime/challenge_response.py` lock checked on the success path | **Fixed** — see above. |
| `scripts/distributed/multi_binary.py` asymmetric cross keys, keys serialized into the index | **Fixed** — symmetric derivation, keys not serialized. |
| `obfuscator/core/sources.py` FUNC_NET returned zeros on success | **Fixed** — returns the 32-byte key from a valid response. |


## Round 4 (2026-11-13, last open items)

| Finding | Status |
|---|---|
| `transforms.CodeChecksumInjector` hashed `ast.unparse(node)` at transform time and compared it against `inspect.getsource(f)` at runtime | **Fixed** — the two can never agree: the transform runs before the string/identifier passes, so the body it hashes is not the body that ships, and `ast.unparse` normalises whitespace and quoting that `getsource` returns verbatim. Every function of every build that enabled the transform would have raised `integrity check failed`. The guard now baselines each module-level function's **code object** at import and compares identity, which is exact and independent of formatting. |
| The emitted `_nx_verify()` was never called | **Fixed** — every target calls it before doing any work. A replaced function never runs its own guard, so each target verifies all the others; that is the only arrangement in which the check can fire. |
| Target names were string literals, so `SymbolRenamer` could not rewrite them | **Fixed** — the target tuple holds `Name` nodes and the baseline keys off `__name__`, so the two stay in step whatever the renamer produces. Confirmed by a real `--fast` build: both variants PASS / VALID / MATCH, and the artifact prints `5`, `hi bob`, `9` and exits 0. |
| Methods and closures were recorded as targets | **Fixed** — only direct children of the module body are targeted; a method is not a module global and a `def` inside `if`/`try` may never execute. |
| The guard displaced function docstrings | **Fixed** — it is inserted after the docstring, so `__doc__` survives. |

Regression tests: `tests/test_audit_round3.py::test_code_checksums_*` (5 tests — no false positive, replacement detected, survives `SymbolRenamer`, methods/closures skipped, docstrings preserved).

The swallowed-exception inventory is filed as `docs/SMELL-INVENTORY.md`. It is a reading aid, not a defect list: each entry is a deliberate best-effort path, and the file records which ones are load-bearing.

Two tests encoded the pre-fix contracts and were updated with the fixes:

- `tests/test_crypto_fallback.py::TestFallbackHonesty::test_simulated_no_crypto_libs_selects_xor_blob` asserted that a missing AES backend silently produced the XOR stream. That is the M2 hazard, so the test now asserts `SystemExit` on the default path and reaches XOR only through `use_aes_ctr=False`.
- `tests/test_opcount_truth.py::test_no_bare_141_claim_in_code` rejects the bare digits `141` in source and docs. Three audit-doc line-number references and one hex literal tripped it; the references now name the symbol instead of the line, which also stops them rotting.

## Round 5 (2026-11-13, verification pass on the fixes themselves)

The verification pass found defects in the round-1/2 fixes. All are fixed and
covered by regression tests.

| Finding | Status |
|---|---|
| `phase_confidence` mixed a `_skipped` dict into the intervals map, so any metric with <2 samples crashed `format_intervals_report`/`phase_confidence` | **Fixed** — `compute_all_intervals_with_skips` returns `(intervals, skipped)`; the report and JSON carry `skipped` separately. Tests: `test_confidence.py::test_single_sample_is_reported_separately_not_mixed_in`, `::test_phase_confidence_survives_a_single_sample`. |
| `dataflow` encoded non-linear `AugAssign` (`*=`, `//=`, `%=`, `**=`, bitwise) and silently produced wrong values | **Fixed** — variables with a non-Add/Sub AugAssign are left plaintext; `+=`/`-=` still encode. Tests: `test_dataflow_split.py::test_affine_leaves_non_linear_augassign_plaintext`, `::test_affine_still_encodes_linear_augassign`. |
| Helpers prepended at `body[0]` broke `from __future__ import ...` (SyntaxError) and module docstrings in adaptive/provenance/dataflow/replay-poison/timing/fingerprint transforms | **Fixed** — `obfuscator/core/ast_prologue.py` inserts after the docstring and all future imports; all six transforms use it. Tests: `test_ast_prologue.py` (12 tests). |
| Adaptive homoglyph renaming renamed external attributes/keywords (`json.dumps(default=...)`, `obj.data`) | **Fixed** — only local method names are renamed as attributes, and keyword args only for direct calls to local functions. Tests: `test_ast_prologue.py::test_adaptive_leaves_external_*`, `::test_adaptive_renames_local_*`. |
| Adaptive string encoding wrapped `match` pattern literals, turning value patterns into class patterns | **Fixed** — pattern constants are skipped. Test: `::test_adaptive_does_not_encode_match_pattern_literals`. |
| `ast_to_smt` mapped string/bytes/None constants and `In`/`Is` to 0/`==`, proving false equivalences; `if` without else crashed on `prev_output=None` | **Fixed** — unsupported constants/comparisons raise `_SmtUnsupported`; single-branch `if` without a prior value declines; the else-only branch uses an ITE. Tests: `test_audit_round2.py::test_ast_to_smt_declines_string_constants`, `::test_ast_to_smt_declines_if_without_prior_output`. |
| `_verify_download_zip` returned False but both callers ignored it and extracted | **Fixed** — refusal paths raise `ValueError`; callers also check the return. Tests: `test_download_zip_gate.py` (4 tests). |
| `phase12_history_bound` still wrote `chain_secret` plaintext to `build/history_bound_state.json` | **Fixed** — `<withheld>`. Test: `test_audit_round2.py::test_research_sidecars_withhold_key_material`. |
| `reorder_pack.randbelow(n>65536)` computed `limit=0` and hung forever | **Fixed** — general k-byte rejection sampling. Tests: `test_reorder_pack.py::test_randbelow_handles_large_n`, `::test_randbelow_still_covers_small_n`. |
| `builder._passed` used the per-test schema against the report generator's summary schema, so an all-pass summary reported NOT ALL PASSED | **Fixed** — `_normalize_test_results` normalizes both shapes. Tests: `test_artifact_passed.py` (5 tests). |
| `SymbolRenamer` used a global parameter set for `nonlocal`, so a sibling function's parameter caused `no binding for nonlocal`; `BogusExceptionHandler`'s `ast.walk` import check missed a class-nested import | **Fixed** — per-scope parameter stack; direct-body import check. Tests: `test_audit_round2.py::test_nonlocal_is_not_confused_by_a_sibling_parameter`, `::test_nonlocal_renaming_stays_consistent`. |
| `llm_resilient` wrapped the function docstring in the guard, so `__doc__` became None | **Fixed** — the docstring stays the first statement. Test: `test_audit_round2.py::test_llm_resilient_preserves_function_docstrings`. |
| `save_token` preserved a pre-created 0644 `.tmp` mode (predictable sibling) | **Fixed** — `tempfile.mkstemp` + `fchmod` + `os.replace`. Test: `test_audit_fixes.py::test_save_token_writes_0600`. |
| `vm_correctness` computed `hmac_tag` but did not export or verify it | **Fixed** — `to_certificate_dict` carries `opcode`/`hmac_tag`; `verify_certificate_dict` recomputes in constant time. Test: `test_vm_correctness.py::test_certificate_hmac_detects_tamper`. |
| `watermark_survivability._check_watermark_preserved` returned True for `unknown` | **Fixed** — only `sat` counts as survived. |
| `llm_api._estimate_from_static` claimed a marker but returned none | **Fixed** — `_source: "static_estimate"`; report averages skip non-numeric values. Test: `test_benchmark.py::TestLLMEvaluator::test_static_fallback_is_marked`. |
| `proof_carrying.verify_certificate` declared constant inputs (`BitVecVal` -> numeral), so valid constant certs verified False | **Fixed** — only valid SMT symbols are declared. Test: `test_audit_round2.py::test_proof_carrying_constant_input_still_verifies`. |
| `ir_to_smt` returned a vacuous `BoolVal(True)` for multi-block CFGs | **Fixed** — raises `_SmtUnsupported`; callers record a decline. Test: `test_audit_round2.py::test_ir_to_smt_declines_multi_block_cfg`. |
| `irgen/compile.py` dropped `assert`/`raise`, dropped `while...else`, and compared the previous boolean in chained comparisons | **Fixed** — `assert` branches to an unreachable trap, `raise` is unreachable, `while...else` has a real else edge, chains compare the previous comparator and AND the results. Tests: `test_irgen_semantics.py` (5 tests). |
| `llvmgen/lower.py` emitted `lshr` for Python `>>` and a bare `sdiv` for Python `//` | **Fixed** — `ashr` and a floor-division adjustment sequence (verified with `llc`). Tests: `test_native_lowering.py::test_floordiv_lowers_to_the_floor_adjustment_sequence`, `::test_shr_is_emitted_not_dropped`. |
| `llvmgen/integrity.py` inserted the check between `target datalayout` and `target triple`, so the module did not assemble | **Fixed** — insert after the module preamble; `llc` verified. Test: `test_llvmgen_integrity.py` (2 tests). |
| `irgen/watermark.py` CLI `embed` passed two args to a one-arg `ir_module_to_text`; `load_ir` replaced every instruction with a NOP, so detection always failed; the dead block's `ret` lost its type operand | **Fixed** — CLI writes the returned text, `load_ir` preserves opcodes/branch labels, `ret` carries `i32`. Test: `test_watermark.py::TestCLI::test_irgen_watermark_cli_embed_detect`. |
| `vm/bytecode_compiler._materialize` used salted `hash()` for string constants | **Fixed** — BLAKE2b. Test: `test_audit_round2_vm.py::test_string_constant_encoding_is_deterministic`. |
| `challenge_response` could not agree on a secret across parties | **Fixed** — optional `shared_secret` derivation. Tests: `test_challenge_response.py` (3 tests). |
| `multi_binary` serialized `cross_keys` into the index | **Fixed** — keys are not serialized. Test: `test_multi_binary.py::test_cross_keys_are_not_serialized`. |
| `encrypt` keystream embedding | **Fixed** — the stub now reads a 32-byte runtime key from a 0600 sidecar (`<output>.key`), XORs it into the embedded keystream, and exits(1) if the sidecar is missing. Legacy no-key mode remains for tests. Tests: `test_encrypt.py::test_keyed_stub_executes_and_decrypts`, `::test_encrypt_binary_fails_closed_without_the_key_file`. |
| `irgen/jit_template` integrity hash covers metadata, not the payload | **Fixed** — the hash covers `metadata + payload`; short keys are rejected (`test_jit_template.py`). |
