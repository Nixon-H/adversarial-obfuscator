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
