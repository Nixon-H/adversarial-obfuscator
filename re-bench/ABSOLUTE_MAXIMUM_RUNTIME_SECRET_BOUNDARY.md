# ABSOLUTE MAXIMUM customer-controlled runtime-secret boundary

Date: 2026-11-26
Scope: authoritative artifact pair and the current continuation source. This document explains what is and is not protected when the attacker controls the customer machine.

## Measured boundary

The decisive evidence is AM-001:

- `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/native_final_lowering/direct_import_boundary.json`
- `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/runtime_probe_final_native_lowering_absolute-native-only.json`
- `re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/runtime_probe_final_native_lowering_absolute.json`

Both authoritative artifacts execute correctly with legitimate runtime secrets. Once the native object is extracted using those secrets, direct import with only `NX_SEAL_SHARD` executes the payload and prints:

```text
SEALED 8771940273853809a401795ec7699cdc
```

That direct import bypasses loader-mediated licence, chain, host, provenance, expiry, and HWID enforcement because the loader is no longer in the execution path.

## Secrets and values exposed to the customer environment

| Value | Where present | Role | Confidentiality consequence |
|---|---|---|---|
| `runtime.licence` / licence token | file path named by `NIXON_LICENCE` | pinned licence payload, expiry, HWID/chain metadata, `key_material` | readable by the customer-machine attacker |
| licence `key_material` | inside the signed licence payload | customer/blob key derivation input | reusable while that token and artifact remain valid |
| `NX_SEAL_SHARD` | process environment | string/blob key shard; sufficient for direct import of an extracted object in measured builds | directly exposed to the customer-machine attacker |
| `NX_TABLE_SHARD` | environment in later operator-shard-masked source paths | additional table/blob key shard | same exposure class when used |
| `NIXON_PROVENANCE_PUBKEY` | environment | out-of-band provenance verification pin | not a secret; integrity trust anchor only |
| HWID/MAC binding material | machine-derived or token-bound | machine binding | not a cryptographic confidentiality boundary on the customer machine |
| chain RPC/contract/token/owner data | signed licence payload | chain ownership verification | mostly public metadata; not a confidentiality control |

## Extraction channels available to a customer-machine attacker

A customer-controlled environment can obtain these values through any of:

1. reading the licence file and shard files supplied to the application;
2. reading process environment through `/proc`, debugging interfaces, process managers, or crash reports;
3. inspecting process memory while the loader derives keys;
4. instrumenting Python or native library calls;
5. patching or replacing the loader;
6. tracing file, memory, or dynamic-loader operations;
7. executing the artifact once and capturing generated temporary or memory-resident native code.

The benchmark does not need to prove every one of these channels. They share the same architectural cause: legitimate execution requires the customer machine to possess enough key material to execute the payload.

## Reusability and customer isolation

The measured licence token contains static `key_material`; it is reusable across executions until expiry or replacement. Chain burn/transfer or later revocation can prevent future loader-mediated execution, but it cannot rotate key material already used to extract a native object.

The current pinned-token design supports per-customer artifacts because the artifact pins one exact licence payload. If the operator actually builds and distributes a distinct artifact/licence pair per customer, compromise of one customer does not automatically disclose another customer's distinct key material. If the same artifact, licence, or shard is reused across customers, compromise is correspondingly reusable. The evidence does not prove a production per-customer distribution process.

## Why this is not merely an implementation bug

The current design uses obfuscation and loader-mediated enforcement to raise analysis cost. It does not provide cryptographic confidentiality against the machine that must execute the payload. Once the machine has the key material necessary for legitimate execution, a sufficiently privileged operator of that machine can use the same material outside the intended loader path.

Therefore the following statement must remain explicit:

> An executable running on a customer-controlled machine cannot guarantee confidentiality of its embedded computation against an attacker who controls that machine.

## Feasible architectural improvements

### 1. Server-side execution for true confidentiality

Keep sensitive operations and secrets on an operator-controlled service. The customer artifact becomes an authenticated client. This is the only architecture in the current threat model that can provide real cryptographic confidentiality for server-held secrets.

Cost: network dependency, service availability, latency, account/authentication design, abuse controls, and server-side revocation infrastructure.

### 2. Authenticated remote execution or remote key release

Use a remote attestation/licensing service that releases short-lived execution keys only after validating licence, machine, chain, revocation, and operational policy. This reduces the lifetime and reuse of extracted keys but still cannot prevent capture during legitimate execution on the customer machine.

### 3. Short-lived per-execution keys

Replace static licence `key_material` with short-lived wrapped keys. This limits replay and reuse windows. It does not solve extraction during a valid execution window.

### 4. Per-customer and per-build isolation

Mandate distinct licence key material and distinct operator shards per customer/build, recorded in release procedure. This limits cross-customer impact but not compromise of the affected customer.

### 5. Hardware-backed key custody where available

Use TPM/TEE/platform key custody for unwrap operations when the deployment platform can actually support it. This can raise the cost of key extraction, but availability is platform-specific and does not generalize to ordinary Python/native artifacts. It also does not guarantee secrecy of plaintext computation once executed outside the hardware boundary.

### 6. Move enforcement into native code with authenticated loader/native handshake

This can close the specific measured direct-import bypass if designed carefully: the native payload would refuse initialization unless it receives a fresh authenticated handshake from the loader after licence/chain/host checks. It is a meaningful improvement against simple object reuse, but it is still software enforcement on a hostile host and is not cryptographic confidentiality against a customer-machine attacker who can instrument or patch both sides.

### 7. Reduce the sensitive client-side computation

The most robust product design is often architectural minimization: ship only non-sensitive orchestration to the customer and keep valuable algorithms, keys, and decision logic server-side.

## Recommended product position

1. Preserve the existing artifact as a high-friction software-protection product, not a confidentiality guarantee against the host operator.
2. Document AM-001 as an inherent client-side execution boundary.
3. For genuinely confidential computation, require server-side execution or remote key release.
4. Implement per-customer key isolation and short-lived keys where operationally feasible.
5. Consider native enforcement/handshake hardening as defense-in-depth, but do not represent it as solving the customer-controlled-machine boundary.

## Current implementation verdict

- Loader-mediated controls are meaningful against casual copying, offline licence misuse, and many automated attacks.
- They are not a boundary against a customer-machine attacker with legitimate runtime secrets.
- No source change in this continuation has solved AM-001.
- The correct completion state for this item is therefore **documented architectural limitation with defined remediation paths**, not “fixed.”

## OpenCode Go DeepSeek confirmation, 2026-11-26 continuation

The credential-isolated `opencode-go/deepseek-v4.1-flash` benchmark reproduced the boundary in the current artifact set. In `maximum-local / legitimate-runtime-secrets`, the agent recovered a native payload object as `native_linux.bin`:

- size: 190,024 bytes
- SHA-256: `95388ca4790f9e02718b31a62852ac4f994c2d2446889f7dc59b5a5a024c959e`
- scenario: customer-machine attacker with legitimate runtime secrets
- exact hidden master secret recovered in that attempt: no
- independently passing semantic reconstruction in that attempt: no

This is partial native-material recovery, not a full semantic break. It confirms the same boundary using an independent model lane and the final validated artifacts.

The same benchmark found no fix-requiring recovery in non-source external-attacker scenarios. Full semantic recovery occurred mainly in source-assisted control scenarios, where `original_source.py` was intentionally supplied and recovery is expected by construction.

## Practical remediation decision

The direct customer-machine confidentiality weakness cannot be completely fixed in a client-side executable. A mitigation that merely hides the temporary `.so` better, moves it into memory, or adds more obfuscation can raise cost but cannot change the underlying key-possession problem: the customer machine must already possess enough key material to run the payload.

The correct remediation order is therefore:

1. **Architectural fix when confidentiality matters:** move the sensitive operation or decision server-side. The client should receive only an authenticated result. This is the real fix.
2. **Remote key-release / short-lived wrapped keys:** reduce reuse and exposure windows where server-side execution of the whole operation is impossible. This does not prevent capture during a valid local execution window.
3. **Per-customer/per-build isolation:** make extracted material affect only the compromised customer/build. Do not reuse licence key material, shards, or native payload images across customers.
4. **Native loader/payload handshake:** close simple direct-import reuse of an extracted object by requiring a fresh loader-mediated handshake after licence, provenance, host, and rollback checks. This is valuable defense-in-depth, but because both loader and native object run on the hostile host it remains patchable/instrumentable and is not cryptographic confidentiality.
5. **Hardware-backed key custody or TEE execution:** use only where the target platform genuinely supports it. Without remote attestation and a hardware trust boundary this is not a general solution.
6. **Memfd/in-memory native loading and faster plaintext wiping:** useful hygiene against casual disk capture, but not a fix for static key-derived extraction or a privileged debugger.

The benchmark does not justify claiming that more packing, more section splitting, or more obfuscation can solve this boundary. The product can raise attack cost substantially; it cannot convert customer-held key material into a server-side secret.

## Current fix status

No client-side source change is claimed as a complete fix for this boundary. The confirmed required action is architectural: use server-side execution or remote key release for genuinely confidential operations. Native handshake hardening and memory-loading hygiene may be implemented as defense-in-depth in a future change, but must be documented as cost-raising measures rather than boundary fixes.
