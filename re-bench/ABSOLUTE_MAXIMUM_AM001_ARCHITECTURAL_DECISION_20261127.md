# AM-001 architectural decision record — 2026-11-27

## Decision

AM-001 is **formally accepted as an architectural limitation of client-side execution** for the current artifact generation. No client-side source change is claimed as a complete fix.

## Confirmed boundary

The OpenCode Go DeepSeek benchmark confirmed partial native-material extraction in `maximum-local / legitimate-runtime-secrets`:

- extracted object name in evidence: `native_linux.bin`
- size: 190,024 bytes
- SHA-256: `95388ca4790f9e02718b31a62852ac4f994c2d2446889f7dc59b5a5a024c959e`
- exact hidden master secret recovered in that attempt: no
- independently passing semantic reconstruction in that attempt: no

The same boundary was already documented as AM-001: when a customer-controlled machine legitimately possesses enough key material to execute the payload, a sufficiently privileged operator of that machine can capture or reuse that material. Obfuscation can raise cost; it cannot convert customer-held key material into a server-side secret.

## Alternatives considered

| Alternative | Decision | Reason |
|---|---|---|
| Server-side execution of sensitive operations | **Required when confidentiality matters** | Only architecture that removes the confidential operation/key-material dependency from the hostile customer host. |
| Authenticated remote key release after licence/host/chain/revocation checks | **Recommended where full server-side execution is impossible** | Reduces standing key exposure and enables revocation policy, but cannot prevent capture during a legitimate local execution window. |
| Short-lived per-execution wrapped keys | **Recommended defense-in-depth** | Reduces reuse windows; still exposed during valid execution. |
| Per-customer/per-build key isolation | **Recommended** | Limits blast radius and supports revocation/forensics. |
| Hardware-backed key custody/TEE with remote attestation | **Conditional** | Useful only where deployment platforms actually provide the hardware trust boundary and attestation. |
| Native loader/payload handshake | **Defense-in-depth only** | Can close simple direct-import reuse, but loader and payload both run on the hostile host and can be patched or instrumented. |
| More packing/obfuscation/memory-only loading | **Cost-raising hygiene only** | Does not change the key-possession boundary. |

## Accepted residual risk

Client-side artifacts may be reverse engineered or partially extracted by a customer-machine attacker with legitimate runtime secrets. This residual risk is accepted only for payload logic whose confidentiality loss is tolerable. Genuinely confidential decisions, keys, or algorithms must not rely solely on client-side obfuscation.

## Required product rule

Do not represent any current client-side artifact as providing strong cryptographic confidentiality against the customer-machine attacker. Documentation, sales material, and release notes must describe the protection as cost-raising reverse-engineering resistance, not a server-equivalent confidentiality boundary.

## Implementation consequence

No new artifact build or benchmark campaign is required for this decision because no AM-001 product code fix is being claimed. If a native handshake, memory-only loader, remote key-release system, or server-side execution architecture is implemented later, it must be built as new artifacts and validated in a separate campaign without overwriting the fixed benchmark artifact tree.
