# Cryptographic Review — payload, string, and section schemes

**Status:** internal review, 2026-11-10. **Not independent.** The author of the
code and this document are the same party. It is recorded because "no review"
was worse than a scoped one; an external review remains open.

Scope: the hybrid loader's payload encryption, the string cipher, section
sealing, licence binding, and the key-material paths that touch them.

---

## 1. Scheme inventory

| Layer | Primitive | Key source | Authentication |
|---|---|---|---|
| Payload blob | AES-256-CTR when `cryptography` is importable; fast-XOR fallback | Per-build blob key from `os.urandom`, split into two XOR shares and salted with `sha256(build_id)` | Loader integrity check on `nixon_core.so`; payload tag depends on path |
| String literals | ChaCha20 + HMAC-SHA256 (truncated 16-byte tag) | Per-string key from `secrets`, embedded in the artefact | HMAC tag verified before decrypt |
| Section split | AES/CTR-equivalent seal with per-section nonce | Same effective loader key | `HMAC(key||nonce, part)` per section; `compare_digest` both sides |
| Licence binding | Ed25519 signature at issue/verify; `key_material` masks payload key | Token `key_material` (issuer-derived, shipped in signed token) | Signature verified outside the artefact; loader uses material as capability |
| Relay attestation | HMAC-SHA256 challenge/response (fixed this pass) | Per-responder secret | Constant-time tag compare |
| TEE software fallback | AES-CTR + HMAC-SHA256 tag (fixed this pass) | External `software_seal_key`; none by default | Tag verified on unseal |

---

## 2. Findings

### 2.1 The client holds every key it needs (by design, and still the ceiling)

Every scheme above decrypts on a machine the attacker controls. This is the
project's stated threat model: raise cost, do not create a trust boundary. No
change here is a "fix"; the only structural answer is moving the secret and the
trust decision server-side.

### 2.2 Payload blob confidentiality is obfuscation, not secrecy

The blob key is in the artefact as XOR shares plus a public `build_id` salt.
An attacker who extracts both shares reconstructs the key; the salt is public.
This is fine for "harder to grep", not for "confidential". Documented; no
change.

### 2.3 String cipher is key-beside-ciphertext

`_nx_k` is embedded with the ciphertexts it decrypts. The bounded LLM probe
identified this in the O4 artefact and concluded the strings are recoverable.
The scheme's value is hiding literals from `strings`/grep, not confidentiality.
Documented; no change.

A 2026-11-11 full-tool agent run made this concrete: it recovered the payload
stream key, nonce, `SWIZZLE_KEY`, loader session token, and payload HMAC key
from the artefact, reconstructed the 242,049-byte payload, and verified its
HMAC. No cryptographic primitive was broken. This is the client-side-key
ceiling in operation; it is recorded in
[`research/ai-layer-bench-2026-11-11/RESULTS.md`](research/ai-layer-bench-2026-11-11/RESULTS.md).

### 2.4 Section sealing now authenticates (fixed)

Sections were sealed with an unkeyed SHA-256 tag; anyone who could touch the
ciphertext could re-seal modified bytes. The tag is now
`HMAC(key||nonce, part)` on both pack and loader sides, with `compare_digest`.
Regression test forges the old scheme and asserts rejection.

### 2.5 TEE software fallback required an external key (fixed)

The fallback derived the seal key from the measurement that is prepended to
every blob, and had no authentication. It now requires an external
`software_seal_key`, uses a per-seal IV, appends an HMAC-SHA256 tag, and fails
closed without a key.

### 2.6 Licence binding is a capability check, not signature verification

The loader does not verify Ed25519; it re-derives the payload key from the
token's `key_material`. A forged token with different material derives a key
that does not match the ciphertext. This stops decryption, not re-issuing.

**Correction (2026-11-11).** The first licence-bound standard build did not
actually mix the token into `k_dec`; it only checked that a token was present,
so a forged `00`-material token still ran the payload. The pack-time and
runtime `k_dec` paths now apply the token mask, and a forged token fails with
`Magic Mismatch`. This is a binding fix, not a cryptographic break; the token
remains a client-side capability.

The loader also pins the canonical signed payload hash, so metadata tampering
is rejected even when `key_material` is unchanged. The signature itself is
verified during the build; the loader does not reimplement Ed25519.

### 2.7 Chain secret no longer touches disk (fixed)

`--crypto-binding` wrote `build/chain_secret.bin`; the only reader used it to
decide whether to log that it was withholding it. The secret now stays in the
builder's memory.

### 2.8 Multi-binary master secret no longer ships in the index (fixed)

`MasterIndex.serialize` included `master_secret` beside the shares it decrypts.
The field is removed; reconstruction uses the holder's own secret.

### 2.9 Open items

- **No independent review.** This document is first-party.
- **No formal analysis** of the CTR IV discipline across blob/string/section
  paths; per-build keys reduce reuse risk but a proof is not recorded here.
- **No side-channel review** of the pure-Python ciphers (timing, memory
  retention beyond `scrub_memory`).
- **Remote unlock now encrypts and authenticates (fixed).** Network messages
  use AES-256-GCM under a configured transport key, and registration requires
  an HMAC proof over the enrollment token. It still lacks forward secrecy and
  a public-key enrollment story; the shared keys must come from configuration.
- **`encrypt/encrypt.py` is a self-decrypting packer by design.** It no longer
  stores the 32-byte seed in `.shadorenc` metadata, but the decryptor stub
  still embeds the bulk keystream. That is what makes the artefact
  self-decrypting; it is also why the scheme cannot be confidential against
  the artefact holder. Treat it as obfuscation, not encryption, until a
  run-time key source exists.

---

## 3. What this review does not claim

- No claim that any scheme resists a client-side attacker.
- No claim of cryptographic strength beyond "the primitives are standard and
  the tagged paths authenticate what they decrypt".
- No claim that this substitutes for an external review.
