# Threat boundary: what the loader can and cannot hide

**Status: accepted.** This file records a limit that was *measured*, not
assumed, and the decision that follows from it. It exists so the next person to
open "the loader is readable" does not spend a week renaming symbols.

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
3. **Accept and price it.** Which is what this document does: the payload holds,
   the wrapper is transparent, and both are measured.

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

* pinning the public key in the CLIENT (or in the licence token) is what makes
  the signature meaningful — an artefact that carries its own trust anchor can
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

**State: NOT POSSIBLE HERE.** `signtool` exists but is the NSS build and fails
with `SEC_ERROR_BAD_DATABASE`; there is no certificate store on a POSIX host.

A self-signed certificate *can* be generated (OpenSSL 3.5 and `cryptography`'s
PKCS#7 builder are present). It is deliberately not used: Windows does not trust
a self-signed Authenticode signature, so the artefact would carry a signature
that verifies to anyone who checks only the format and to no OS that enforces
it. That is the "looks protected, enforces nothing" failure this project has had
to retract four times, and producing it would be a fifth.

**Missing capability:** a CA-issued code-signing certificate and a working
Authenticode tool (`osslsigncode`, or `signtool` on Windows).
**Verification that would follow:** `native_harden.verify_pe_bytes` reports
`authenticode: True` (security directory non-empty), plus an out-of-band
`signtool verify /pa` on Windows.

### 3. macOS Hardened Runtime, code signing, library validation

**State: NOT POSSIBLE HERE.** `codesign`, `rcodesign` and `ldid` are all absent.
Hardened Runtime and library validation live in the CodeDirectory of a signature,
not in compiler flags, so `verify_macho_bytes` correctly reports
`hardened_runtime: False, library_validation: False` for anything built here.

**Missing capability:** `codesign` (macOS) or `rcodesign` (cross-platform), plus
an Apple Developer ID certificate.
**Verification that would follow:** a Mach-O with an `LC_CODE_SIGNATURE` whose
CodeDirectory has `CS_RUNTIME | CS_RESTRICT`; the parser already reads exactly
that and is tested against synthetic CodeDirectories, so again the check is
ready and the toolchain is the gap.

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


