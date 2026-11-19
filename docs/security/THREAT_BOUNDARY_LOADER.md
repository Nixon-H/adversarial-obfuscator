# Threat boundary: what the loader can and cannot hide

**Status: ACCEPTED BY OPERATOR DECISION (2026-11-19).** This file records a
limit that was *measured*, not assumed, and the decision that follows from it.
It exists so the next person to open "the loader is readable" does not spend a
week renaming symbols.

The operator reviewed the §5l measurement (DS 4.1 Flash reconstructed the
entire enforcement layer; renaming all 187 symbols hid none of it) and chose to
accept the boundary rather than fund the two alternatives that could change it
(native-blob enforcement, or off-device attestation — both architecture
changes, both named below with their costs). Re-opening this decision requires
new evidence, not a restatement of the old limit.

## What was measured

PyDeObsBench §5l gave DeepSeek V4.1 Flash the text of a real `max`-profile
artefact (280 KB, built in 14.5 s). The model reconstructed the enforcement
layer completely, with no debugger and no execution:

* `prctl(PR_SET_DUMPABLE=0)` and `RLIMIT_CORE=(0,-1)`
* the identity gate and its exit path
* `constant_time_compare`'s OR-accumulate-of-XOR construction
* `_nx_self_fail` → `os._exit(137)` and its message format
* `_nx_mlock`'s `addressof` / page-alignment construction

Then the obvious remedy was tested rather than assumed. The loader's **187
symbols** were renamed to opaque identifiers — the strongest symbol-level
obfuscation available. Afterwards, every behaviour-bearing constant was still
present:

| marker | survives total symbol renaming |
|---|---|
| `prctl` | yes |
| `137` | yes |
| `RLIMIT_CORE` | yes |
| `mlock` | yes |
| `0o600` | yes |
| the `self-check error:` string | yes |

**Renaming symbols does not hide behaviour.** The model did not recover
`_nx_self_fail` — it recovered *"writes to stderr and calls `os._exit(137)`"*.
Those are syscall numbers and constants, and they are what the code must do to
work. An obfuscation pass that changes only names cannot touch them.

## The decision

The protection is therefore split into two claims, and they are graded
separately:

| layer | measured outcome | stands or falls |
|---|---|---|
| **Payload** (what the customer ships: source, algorithms, secrets) | 0/4 names, 0/2 secrets static; 0/2 secrets and 0/4 names in memory across 14 samples; semantic equivalent matches at 0.00 identifier overlap | **holds** |
| **Wrapper** (how integrity, licensing and anti-dump are enforced) | fully reconstructed from artefact text | **does not hold — accepted** |

This is the "payload-vs-wrapper boundary" as the target threat model. It is a
deliberate scope statement, not a workaround:

* Hiding the *payload* is achievable, because the payload is data and data can
  be sealed under keys the attacker does not have.
* Hiding the *enforcement mechanism* is not achievable in client-side Python.
  The mechanism must execute on the attacker's machine, so its behaviour is
  necessarily observable; and because the artefact is text they can read, its
  structure is necessarily readable. This is the same class of limit the review
  itself names — *"absolute irreversibility isn't a realistic guarantee for
  client-side software"*.

## What this costs, concretely

An attacker who reads the wrapper learns:

* exactly which guards run, and in what order,
* that the integrity check is a Merkle root plus an HMAC over the artefact,
* where the anti-dump calls are, and therefore how to avoid them (`mlock` a
  buffer instead, or patch `prctl` before the loader runs).

An attacker who reads the wrapper does **not** learn:

* the payload's identifiers, literals or algorithm,
* the sealing key material (the loader derives it; the shares in the artefact
  reconstruct it only with the customer mask),
* anything that makes 0/4 and 0/2 become non-zero.

§1's five measured attack routes all still end at `rc 137` **after** the loader
was fully read — including tamper + re-stamp, which the second HMAC layer
caught. Reading the mechanism is not the same as defeating it, and the
difference is why this boundary is acceptable rather than fatal.

## What would change the answer

Not more symbol obfuscation. The only approaches that could hide the *mechanism*
are ones where the mechanism is not in the artefact at all:

1. **Move enforcement into the native blob.** The C transform already emits C;
   the guards could be C functions rather than Python. That raises the cost from
   "read the file" to "reverse the .so" — a real increase, though the blob is
   itself extractable (the loader carries its key).
2. **Move enforcement off-device.** A licensing/attestation service that the
   artefact must reach; the mechanism then lives on infrastructure the attacker
   does not control. This changes the deployment model, not just the code.
3. **Accept and price it.** Which is what this document does — and what the
   operator decided on 2026-11-19: the payload holds, the wrapper is
   transparent, and both are measured.

Options 1 and 2 are recorded as future work because neither is a tuning change
and both have costs the current design deliberately avoids (option 2 requires
network availability at runtime; option 1 requires the guards to be reimplemented
in C, including the Cython boundary).

## Measured 2026-11-19: the integrity check is internally consistent, not authentic

This is the sharper version of the same boundary, and it is the one that
matters operationally. §5m reported that re-stamping the Merkle root alone is
insufficient — the HMAC layer caught it. That raised the obvious question, and
`scripts/attack_chain.py` now answers it.

| attack | result |
|---|---|
| control | rc 0, payload ran |
| tamper pack only | **rc 137** — merkle mismatch |
| bypass the self-check call only | **rc 137** — the late check caught it |
| bypass + tamper | **rc 137** |
| re-stamp the Merkle root, no edit | rc 0, payload ran (correct: nothing changed) |
| tamper + re-stamp **CK only** | **rc 137** — `hmac expected=ceeb9900… got=984ac5e…` |
| **tamper + re-stamp BOTH CK and HM** | **rc 0, payload ran** |

The last row is the finding. The HMAC key `_NX_SELF_HK` is a plaintext literal
in the same file the HMAC covers, so an attacker who reads the artefact can
recompute both layers and their tampered payload runs.

**What the integrity check therefore establishes:** the file is internally
consistent — self-check, anchors and content agree with each other.

**What it does not establish:** that the file came from the publisher. Both
layers are derivable from the artefact by anyone holding it, so the control
distinguishes accidental corruption from nothing at all. It does not
distinguish a deliberate edit by someone who read the construction.

This does not make the check useless: it still blocks the naive tamper, the
single-line bypass, and the bypass+tamper chain — three of the five routes in
the table above. It does mean the honest description is "tamper *detection* for
non-adaptive edits", not "anti-patching", and the report says so rather than
quoting the five-route result as if all five failed.

### What would actually bind the artefact to the publisher

The check needs a secret the attacker does not have. Concretely:

1. **Verify against something the attacker cannot forge** — an Ed25519 signature
   over the artefact, with only the public key embedded. **Implemented** in
   `obfuscator/attestation.py` (inline RFC 8032 verifier, no dependencies in the
   artefact) and `obfuscator/ed25519_verify.py` (the reference it is
   cross-checked against). Wired into the loader by `emit_snippet()`; a build
   that signs produces an artefact that refuses to run when edited. **Not yet
   enabled by default** — signing needs a key, and a build without one emits an
   artefact whose provenance check is absent rather than fake.
2. **Derive the key from the licence token** — `_NX_SELF_HK` is present in every
   build, so it is not a secret. If it were derived from token material the
   customer holds and the artefact does not, recomputing the HMAC would require
   the token. The licence path already does this for the payload key
   (`_nx_licence_key`); the self-check key was not moved onto it.
3. **Move the check off-device** — an attestation service, as above.

Option 1 is the smallest change with a real security effect and is now
implemented as a module. The remaining work is operational: an operator supplies
a signing key, and the build stamps the artefact. Until then the artefact's
integrity check remains the internally-consistent kind measured above.

### Honest limit of the signature fix

The public key travels IN the artefact, so an attacker who re-signs a modified
file with their OWN key produces something self-consistent. Two things follow,
and both are stated rather than implied:

* pinning the public key in the CLIENT is what makes the signature meaningful.
  Out-of-band pinning via `NIXON_PROVENANCE_PUBKEY` is implemented and
  **measured**: a correct pin runs (rc 0), a wrong pin is refused (rc 137).
  Pinning via the LICENCE TOKEN is **not** available: `_nx_licence_key()`
  returns the token's sealing salt, not a public key, so comparing against it
  made every legitimately bound artefact die. Measured and reverted; the token
  schema would have to carry a signing key before that path can exist. — an artefact that carries its own trust anchor can
  only prove it agrees with itself;
* an attacker who controls the interpreter can patch the verification call out,
  exactly as they can patch any check. §1's answer to that is the point-of-use
  redundancy elsewhere (CFI, the late self-check, the kill ladder), not the
  signature.

---

## Environment-limited items, recorded so they are not mistaken for done

Three §3 requirements cannot be satisfied on this host. Each is listed with the
exact missing capability and the verification that would follow, because "we
could not" and "we did not" have different remedies and a boundary document that
blurs them is useless.

### 1. CFG function table (`IMAGE_GUARD_CF_FUNCTION_TABLE_PRESENT`)

**State: PARTIAL.** Measured 2026-11-19 on a real MSVC-ABI object:

| object | load config | GuardFlags | instrumented | function table |
|---|---|---|---|---|
| `-guard:cf` only | empty | — | — | — |
| + `native/pe_load_config.c` | 288 B | `0x100` | **yes** | **no** |

`0x100` is `CF_INSTRUMENTED`: indirect call sites verify against the guard
check pointer, which is real protection. `0x400`
(`CF_FUNCTION_TABLE_PRESENT`) requires the compiler to emit a guard function
table, which needs `clang-cl` with the MSVC headers — not present here.

**Missing capability:** MSVC headers / a Windows SDK.
**Verification that would follow:** a PE with `GuardFlags & 0x400` set and a
non-zero `GuardCFFunctionCount`; `native_harden.check` already reports
`partial: []` in that case, so the check is ready and only the toolchain is
absent.

### 2. Authenticode

**State: IMPLEMENTED, gated on an operator-supplied certificate.**

The earlier entry said "not possible here", which was correct about the
CERTIFICATE and wrong to leave the MECHANISM unimplemented. That distinction is
now closed: `obfuscator/authenticode.py` produces a real Authenticode signature,
and the farm driver applies it when the operator supplies credentials.

    NIXON_AUTHENTICODE_CERT   path to a PEM/DER certificate (+ chain)
    NIXON_AUTHENTICODE_KEY    path to the matching private key
    NIXON_AUTHENTICODE_PASS   optional passphrase

With those set, the Windows runner signs `payload.pyd` before the attestation is
written, and `native_harden.verify_pe_bytes` reports `authenticode: True` from
the resulting security directory. Without them the artefact is reported
unsigned — never "signed" on the strength of a flag.

What was measured on this host, 2026-11-19, against a real PE:

| property | result |
|---|---|
| digest identical before and after signing | **yes** — the property that makes a signature verifiable |
| security directory populated | 1360 bytes at the appended offset |
| WIN_CERTIFICATE header | `dwLength=0x550, wRevision=0x0200, wType=0x0002` |
| PKCS#7 payload parses | yes, carrying the signer's certificate |
| 8-byte alignment | 6 bytes of zero padding, as the spec requires |

Two defects were found by the digest-identity assertion, and both would have
produced a signature no verifier accepts:

* writing `SizeOfImage` during signing — it is **not** one of the three excluded
  regions (checksum, security directory entry, certificate table), so changing
  it invalidated the digest;
* **zeroing** the certificate table instead of **skipping** it — the table is
  appended past the original EOF, so hashing its zeroed length added 1360 bytes
  the original image never had.

**What remains the operator's:** a certificate Windows will trust. A self-signed
one is still deliberately not used — it would verify to anyone checking only the
format and to no OS that enforces it, which is the "looks protected, enforces
nothing" failure this project has already had to retract four times. The
mechanism is ready; the supply chain is not something a build tool can supply.

**Also not implemented, and stated rather than implied:** RFC 3161 timestamping.
An un-timestamped signature stops validating when the certificate expires. That
is an out-of-band step for the operator.

**Verification that would follow a real certificate:** `signtool verify /pa` on
Windows, plus the `authenticode: True` this module already reports.

### 3. macOS Hardened Runtime, code signing, library validation

**State: BLOCKED ON A macOS RUNNER — not "verified", and not something this host
can produce.**

`codesign`, `rcodesign` and `ldid` are all absent. Hardened Runtime and library
validation live in the CodeDirectory of a signature, not in compiler flags, so
`verify_macho_bytes` correctly reports `hardened_runtime: False,
library_validation: False` for anything built here: there is no signature for it
to find.

This is a different kind of entry from the CFG one. There, the mechanism was
implemented and measured with a weaker result (no function table). Here the
**parser is complete and tested** — it walks `LC_CODE_SIGNATURE`, parses the
CodeDirectory superblob and reads `CS_RUNTIME` / `CS_RESTRICT` — but no signed
Mach-O object exists on this host to point it at, so the parser has only ever
been exercised against synthetic blobs. That is a weaker evidence class and it is
recorded as such rather than as "verified".

**Unblock step, named precisely:** a macOS runner (or `rcodesign` on any host)
plus an **Apple Developer ID Application certificate**, then

    codesign --options runtime --timestamp --sign "Developer ID Application: …" payload.dylib

`--options runtime` is what sets `CS_RUNTIME`; `--timestamp` is what keeps the
signature valid past certificate expiry. Library validation is `CS_RESTRICT`,
enabled by the same Hardened Runtime option set.

**Verification that would follow, and is already implemented:** the parser
reports `hardened_runtime: True`, `library_validation: True`, and the
CodeDirectory's hash type and flags; a negative control (signed without
`--options runtime`) must report both `False`. Both directions are already
asserted against synthetic CodeDirectories in `tests/test_native_harden.py`, so
the only missing link is a real signed object.

**Why no workaround:** there is no way to produce a Mach-O CodeDirectory that
Gatekeeper accepts without a Developer ID, and a synthetic one would make the
artefact look signed to a format check while being rejected by every macOS host
that enforces it — the failure mode this document exists to prevent.

### Why these are recorded rather than worked around

The review's §3 instruction is explicit: *"Don't blindly enable every flag.
Verify the resulting binary using platform-native inspection tools."* For these
three, the platform-native tool does not exist on this machine, which means any
result produced here would be verified by nothing. Writing that down is the
honest form of "not done"; emitting a flag and calling it hardened is not.

The farm runners have the tools for items 2 and 3 (a Windows runner can hold a
certificate; a macOS runner has `codesign`). Their attestation records
`hardening_verdict`, so when those builds happen the result is checked rather
than assumed — which is the same arrangement §7.9 uses for runner integrity.



---

## §9 audit (2026-11-19): three "never verified" items audited, two wired

The review's §9 names function-level virtualisation, instruction-set
diversification and crash-forensics protection as items to "still consider
adding". The audit found all three ALREADY IMPLEMENTED — and two of them
unreachable in every real build, which is the same "tested but unreachable"
defect the crash-suppress header had.

### 1. Function-level virtualisation — EXISTED, WAS UNREACHABLE, NOW REACHABLE

`obfuscator/vm_dispatch.py` (756 lines) compiles eligible Python functions to a
per-seed stack VM with TWO dispatcher families (VM-A switch chain, VM-B threaded
handler table), opcode numbering shuffled per seed. 12 tests cover correctness
(fib/gcd/factorial through the VM), range/edge cases, and per-seed variety.

**Audit finding: nothing set `options['vm_dispatch']`** — the only reference
was `sources.py`'s gate, and the sole setter was the transfer-experiment
harness. So the VM never ran in any real build; it was reachable only by
writing an experiment script by hand.

**Fixed:** `NIXON_VM_DISPATCH=a|b|alternate` reaches the native path's option
dict (pipeline.py), fails closed on an unknown value, and stays off by default
because the allowlist only virtualises simple numeric functions — an operator
enables it per artefact rather than the build silently transforming everything.

### 2. Instruction-set diversification — WIRED, and layered three ways

`scripts/phases/phase_state_isa.py` was already called from `build.py`
(state-dependent opcode configuration for the emitted VM). Added to it:

  * VM-A vs VM-B dispatcher family per build (`--vm-dispatch alternate`);
  * per-seed opcode renumbering inside each family;
  * §5's compiler diversity (gcc / clang / MSVC ABI) at the native level.

Three independent layers, each measured: VM opcode map differs per seed
(`test_encoding_differs_per_seed`), dispatcher family differs per build
(`test_determinism_and_variety`), and native instruction mix differs per
backend (§5-B: trigram Jaccard 0.277).

### 3. Crash-forensics protection — EXISTED, WAS UNLINKED, NOW WIRED

`native/crash_suppress.h` suppresses the Windows crash dialog / abort prompt
(`SetErrorMode`, `_set_abort_behavior`) and routes POSIX fatal signals
(SIGABRT/SIGSEGV/SIGILL/SIGFPE/SIGBUS) to a silent `_exit(137)` — matching the
kill ladder's code. 27 tests covered the header.

**Audit finding: no native source included it.** The header was compiled by
nothing, so every native hard failure raised an OS dialog handing the analyst
a register state and backtrace — the exact leak §4's core-dump policy exists to
prevent.

**Fixed:** `native/core.cpp` includes the header and calls
`nixon_suppress_crash_dialogs()` at `CompileToMarshal`, the entry the loader
actually calls. Verified: compiles clean with `-DCORE_HAVE_PYTHON_H`
(126 KB object). `tests/test_crash_suppression.py` (27 tests) already covered
the handler semantics.

### Honest scope of all three

None of the three hides the WRAPPER (see the loader boundary above). The VM
hides payload *function bodies* behind a bytecode interpreter — the recovered
loader description in §5l did not include any VM internals because the VM only
runs on opt-in functions. Crash suppression prevents *forensic leakage* from
native failures; it does not stop an attacker from setting their own handlers
after load. ISA diversification raises disassembly cost; it does not make
static analysis impossible. All three are measured contributions to analyst
cost, and all three are recorded here with their limits rather than as
unqualified wins.

## Boundary push, measured 2026-11-20: enforcement moves native, split by build type

The accepted boundary listed "move the enforcement into the native blob" as
the boundary-push option. It is now implemented and measured.

### What changed

1. `native/enforcement.c` (new): `nx_apply_protections()` — prctl
   PR_SET_DUMPABLE=0 + RLIMIT_CORE=0 on Linux; setrlimit + PT_DENY_ATTACH on
   macOS (ADDITIVE: the old Python block was a silent no-op on macOS, so
   macOS artefacts previously shipped dump-limit only); silent `_exit(137)`
   fatal-signal handlers matching crash_suppress.h. Compiles clean under
   `-std=c99 -fvisibility=hidden`, self-contained (no header to copy into
   blob build dirs). Exported with default visibility so the dynamic table
   carries it after `strip -x`.
2. Every locally-built blob compiles it in (`payload.c + enforcement.c` in
   one gcc invocation, same hardening flags). Both blob producers are wired;
   a producer that cannot find the source refuses to build (fail closed).
3. The loader dlopens the blob WITHOUT running its init, calls
   `nx_apply_protections()`, records its return bitmask (1 = dumpable off,
   2 = core limit zero, 4 = deny-attach) for the NIXON_MEM_REPORT diagnostic,
   and ONLY THEN lets PyInit execute payload code. Fail-closed: a blob
   without the entry is refused (`_nx_self_fail`) — not one of ours.
4. The loader's top-of-file ctypes prctl block is now emitted ONLY for
   builds that can reach payload plaintext through Python (sectioned or
   bytecode fallback). A `native_only=True` loader emits no syscalls at all
   — measured: zero occurrences of prctl/setrlimit/RLIMIT_CORE/
   PR_SET_DUMPABLE/PT_DENY_ATTACH in the generated text.
5. memguard's second readable prctl site switches form for native-only
   builds: report-only, reading the enforcement bitmask instead of naming
   syscalls. NIXON_MEM_REPORT stays meaningful.
6. Pre-existing defect found on the way (measured 2026-11-20): the
   Output-Generation pack block classified GENERATOR-PACKED blob bytes and
   refused EVERY `--package native-only` build ("not an object file"). The
   classification now runs while the blobs are still plaintext ELF, and the
   pack block skips an already-packed dict. NOTE: the `--package native-only`
   CLI route produces a DIFFERENT 19 MB packaging (the maximum-security
   pipeline) with its own pre-existing loader defects — out of scope here;
   this fix unblocks the build, it does not repair that wrapper.

### What was measured

* Blob probe (real `build_local_cython` blob, dlopen'd in a subprocess):
  `mask=3, CoreDumping: 0` — both syscalls applied by the real artefact
  object, before any payload init.
* The real max-profile artefact: runs rc 0 (`OK verify:14`); all six
  attack_chain routes rc 137 (control rc 0).
* DS 4.1 Flash re-probe on the rebuilt max artefact: recovered the
  ENFORCEMENT MECHANISM in full (dlopen → `nx_apply_protections()` →
  refuse-if-missing → bitmask) but NOT the native-layer semantics — the
  answer contains no description of what the native entry does internally.
  The Python prctl block is still recovered because the max profile's
  sectioned fallback keeps it BY DESIGN (see below).
* `py.test tests/test_native_enforcement.py`: 6 tests pin the contract
  (emission rule, fail-closed call, memguard form, source, blob probe).

### The split, stated plainly

* A build whose ONLY payload path is the native module (fallback DISABLED)
  now carries NO anti-dump syscalls in text. The wrapper's enforcement layer
  is machine code.
* The max profile (sectioned fallback + native blob) keeps the Python block
  because the sectioned fallback is production-reachable — dropping it
  would be a §4 regression on that path, not a boundary push. On those
  artefacts the enforcement is LAYERED (Python block + native entry, the
  syscalls idempotent), and the readable block remains the honest residual.
* Client-side software still cannot reach full immunity: an attacker with
  execution can trace the native entry, and the blob is extractable. What
  changed is where the semantics live — text vs stripped machine code — and
  the measured DS probe confirms the difference.
