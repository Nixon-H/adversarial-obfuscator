# AM-001 architectural decision record — 2026-11-27

## Update — opt-in server-side remediation implemented

Later on 2026-11-27, the architectural remediation path was implemented for
functions explicitly marked `@remote`: split/server-side execution removes
those implementations before native compilation and packing. Validation is in
`ABSOLUTE_MAXIMUM_AM001_REMOTE_SPLIT_VALIDATION_20261127.md` and the matching
JSON evidence file. This supersedes the original "accepted only" outcome for
logic the developer explicitly moves server-side. It does not alter the fixed
benchmark artifacts and does not protect unmarked client-side logic.

## Update — Cloudflare serverless target and dual-TOTP gate implemented

Also on 2026-11-27, the server-side remediation gained a Cloudflare Python
Worker deployment target. `remote-cloudflare=DIR` generates an operator-side
Worker project that verifies the same protocol-v1 HMAC envelope, requires two
independent TOTP factors server-side, and uses a SQLite-backed Durable Object
for replay rejection. Local Worker-runtime validation is in
`ABSOLUTE_MAXIMUM_AM001_CLOUDFLARE_TOTP_VALIDATION_20261127.md` and its JSON
companion. This is a deployment/access-control improvement, not a change to
the fundamental boundary: TOTP is not host attestation, Cloudflare is inside
the operator trust boundary, oracle abuse remains possible where valid client
configuration and fresh factors are available, and unmarked client-side logic
remains extractable.

## Original decision

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

The original decision required no new artifact build because no product code fix was then being claimed. The implemented split-execution remediation has now been validated separately without overwriting the fixed benchmark artifact tree; see the update above. Any future native handshake, memory-only loader, or remote key-release system still requires its own artifact-level validation campaign.
