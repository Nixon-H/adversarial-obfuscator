# Full-codebase audit coverage tracker — started 2026-11-28

Scope: every project source file in C, Rust, Python. Exclusions (generated/
vendored/data, not project code): native/payload.h (generated blob arrays),
scripts/transfer/corpus/ (vendored third-party), re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/builds
(fixed-hash evidence), runtime/target/ (build artifacts), __pycache__, archive
generated obfuscation samples, build/ + build.loop/ (output dirs).

Rules: subagents read every line (no lint-only passes), fix confirmed bugs in
their disjoint shard, write regression tests in tests/test_audit_<shard>.py,
do not commit (orchestrator commits after verification).

| shard | scope | lines | status | findings |
|---|---|---|---|---|
| A1 | obfuscator/core/pipeline.py | 9178 | RUNNING | - |
| A2 | obfuscator/core/sources.py | 7721 | QUEUED | - |
| A3 | obfuscator/core/transforms.py + utils.py | 5952 | QUEUED | - |
| A4 | obfuscator/cloudflare_remote.py + remote_exec.py + webpush.py | ~4400 | QUEUED | - |
| A5 | obfuscator/: section_split, anti_rea, native_harden, driver_blocklist, vm_dispatch | ~4900 | QUEUED | - |
| A6 | obfuscator/: all remaining files | ~31000total-claimed | QUEUED | - |
| C1 | native/*.c *.h (excl payload.h) + encrypt/ | ~3600 | DONE committed | 5 fixed: sa_flags uninit, rlim fail-open, SSE dispatch divergence, key not wiped, platform.h self-containment |
| R1 | runtime/src/*.rs (Rust crate) | 6875 | DONE committed | 15 fixed: broken AES key schedule/shift_rows, keystream-reuse XOR, CTR nonce reuse, dead-store scrub elimination, unsafe fn soundness, JIT machine-code corruption x2, ledger layout mismatch, zero-layout UB, CPUID constants, rdrand #UD, perf syscall, Arc cycle leak, transient erasure |
| R2 | archive/relay_net/*.rs + relay/ | ~4000 | QUEUED | - |
| D1 | irgen/ + llvmgen/ + vm/ | ~15900 | QUEUED | - |
| D2 | pydeobsbench/ + re-bench/tools/ | ~11900 | QUEUED | - |
| D3 | audit/ + examples/ + config | ~900 | QUEUED | - |
| B1 | scripts/phases/ | 8744 | QUEUED | - |
| B2 | scripts/transfer/ (excl corpus) | ~6463 | QUEUED | - |
| B3 | scripts/distributed + benchmark + evaluation | ~10700 | QUEUED | - |
| B4 | scripts/proofs + artifacts + lint + reachability | ~7800 | QUEUED | - |
| B5 | scripts/metrics + validation + ci + remaining subdirs | ~8000 | QUEUED | - |
| B6 | scripts/*.py root files incl build.py | ~45000? | QUEUED | - |
