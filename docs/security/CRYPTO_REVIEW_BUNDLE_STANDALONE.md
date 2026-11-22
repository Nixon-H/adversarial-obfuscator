# Section pack v2 — standalone review bundle

**What this is.** A self-contained description of the construction in
`obfuscator/section_split.py`, written so a cryptographer can review it
**without cloning the repository**. Everything needed to reason about the
design is here; §7 lists the files to request if you want the code itself.

**Status: NOT REVIEWED.** No cryptographer has examined this construction. This
document is what a reviewer would be sent, not a record of a review.

**Companion document.** `CRYPTO_REVIEW_PACKAGE.md` in the same repository is
the longer version, with the threat model, the tamper-matrix mapping and
reproduction commands. This bundle is the extract that stands alone.

Target: `obfuscator/section_split.py` (pack format v2), commit
`71eff21081785eb4bf588e7dd8542d0e4c279d79`.

---

## 0. The question we are asking

Is this construction acceptable for the stated threat model, or must it be
replaced with a standardised AEAD? If replacement, is a small audited native
dependency operationally acceptable given the loader must run without a
compiler on customer machines?

We are not claiming it is secure. We are claiming it is **deployed** and we do
not know whether it should be.

## 1. Constraint that produced it

The loader runs on customer machines. The only crypto guaranteed present is the
Python standard library: `hashlib` and `hmac`. `cryptography` (and therefore
AES-GCM, ChaCha20-Poly1305) cannot be assumed. The section path therefore uses
SHA-256 and HMAC-SHA256 only.

This is a deployment constraint, not a preference. §8 of the companion package
records why the standard AEADs are unavailable here, and asks whether vendoring
a small audited implementation would be better.

## 2. Notation

```
K       32-byte master session key, delivered out of band
i       section index, 0..count-1
N_i     16-byte random nonce per section per build
T       total plaintext length, 4-byte encoded
v       pack format version = 2
‖       concatenation
u32be   unsigned 32-bit big-endian
```

All hashes are SHA-256. All MACs are HMAC-SHA256.

## 3. Key derivation

```
basis_i   = K ‖ u32be(i) ‖ N_i
K_enc_i   = SHA256("nx-section-enc:" ‖ basis_i)
K_mac_i   = SHA256("nx-section-mac:" ‖ basis_i)
```

Domain separation is by the ASCII prefix. Index and nonce are both inside the
derivation, so the two keys differ per section even under a repeated nonce.

## 4. Authenticated context (the AAD role)

```
ctx_i = u32be(v) ‖ u32be(i) ‖ u32be(T) ‖ N_i          (28 bytes)
```

`v` is bound so a pack cannot be downgraded to the v1 scheme by editing the
`v` field. `T` is bound so the pack cannot be re-pointed at a different total.

## 5. Seal

```
tag_i  = HMAC(K_mac_i, ctx_i ‖ plaintext_i)           (32 bytes)
body_i = tag_i ‖ plaintext_i
ct_i   = body_i XOR keystream(K_enc_i, N_i, |body_i|)
```

where

```
keystream(key, nonce, n) = SHA256(key ‖ nonce ‖ u64be(0))
                         ‖ SHA256(key ‖ nonce ‖ u64be(1))
                         ‖ … truncated to n
```

## 6. Open

```
tag‖part = ct_i XOR keystream(K_enc_i, N_i, |ct_i|)
require HMAC(K_mac_i, ctx_i ‖ part) == tag          (constant-time compare)
plaintext_i = part
```

Verification precedes use: no plaintext is accumulated or sunk before its
section's tag verifies. Then: section count matches, indices are `0..count-1`,
and the concatenation length equals `T`.

## 7. Structural digest (not a security boundary)

```
state = SHA256("nx-pack-state/v1:" ‖ u32be(count) ‖ u64be(T)
               ‖ Σ over sorted sections ( u32be(i) ‖ salt_i ))[:32]
salt_i = SHA256(K_enc_i ‖ N_i)[:16]
```

Unkeyed, checked before the MACs. It detects accidental inconsistency and
forces an attacker to make an edit self-consistent. **We do not treat it as
authentication**, and a reviewer should confirm that reading is right rather
than assuming the code's ordering implies a security property.

## 8. Weaknesses we already know about

Listed so the review does not spend its budget rediscovering them.

1. **MAC-then-encrypt, no reduction.** Not an AEAD. No proof, no named security
   notion. *This is the main question.*
2. **Bespoke stream cipher.** SHA-256 in counter mode over
   `key ‖ nonce ‖ counter`. Reasonable-looking is not an argument.
3. **`key_hint` is an unkeyed oracle.** The pack carries
   `SHA256(K)[:16]` in the clear, and it is checked **before** the MACs.
   Measured. Assess whether that materially helps an offline attacker, given
   `K` is derived partly from licence/HWID material the holder may know.
4. **No nonce-reuse protection at load.** Index is in the derivation, so
   cross-section reuse is harmless; same-section reuse across two packs under
   one key would XOR two keystreams. Random per build makes it improbable, not
   impossible.
5. **Section length is implicit**, bound only via `T` and the final join check.
   Should `|part|` be in `ctx_i`?
6. **`salt` is unkeyed and unverified**, used only in the structural digest.
7. **The v1 legacy path remains** (single key for both roles, no metadata
   binding), kept so older artefacts stay loadable.

## 9. Questions

1. Is MAC-then-encrypt over this keystream acceptable here, or must it become a
   standardised AEAD?
2. If AEAD: is AES-128-CTR + HMAC-SHA256 (encrypt-then-MAC, both
   stdlib-feasible) the right middle ground, or is vendoring required?
3. Does `ctx_i` bind enough? Specifically: add section length? a pack id?
4. Is `key_hint` a material weakness, and what is the fix?
5. Is the random-nonce-per-build argument sound, or should a counter be
   mandatory?
6. Does the structural digest's position (before the MACs) create a
   distinguishability or DoS issue?
7. Is `hmac.compare_digest` used at every tag comparison? (We measured four
   sites — one in-process join plus three emitted loader templates — all
   constant-time. Please verify independently.)
8. Any information leakage from the error messages distinguishing count
   mismatch / state invalid / integrity failure / length mismatch?

## 10. What we are not claiming

* Not that this is cryptographically secure. Passing the tamper matrix means
  specific attacks were rejected, nothing more.
* Not that it is better than a standard AEAD. It exists because of §1.
* Not that the surrounding code is in scope. This bundle covers
  `section_split.py` and `pack_state.py` only. Licence derivation, HWID
  binding and the loader's memory protections are separate surfaces.

## 11. How to check our measurements

Clone `https://github.com/Nixon-H/adversarial-obfuscator` at commit
`71eff21081785eb4bf588e7dd8542d0e4c279d79`, then:

```sh
export PYTHONPATH="$PWD"
python3 -c 'import sys; from pytest import console_main; sys.exit(console_main())' \
    -q tests/test_section_split.py tests/test_pack_state.py \
       tests/test_reorder_pack.py tests/test_byte_tamper_sweep.py
```

Expected **40 passed** (verified on that commit). Coverage-guided fuzzing of the
pack parser reached `cov: 61 / ft: 185` over 4,075,415 executions with zero
unintended acceptances; `scripts/fuzz/nx_fuzz.py` reproduces it (45 s is enough
to see coverage grow — and `cov: 1` means the harness is not instrumenting, not
that the parser is clean).

## 12. How to return findings

Privately, via
<https://github.com/Nixon-H/adversarial-obfuscator/security/advisories/new>
or to the maintainer directly. Findings are filed as register rows in the
15-field format of `docs/security/REVIEW_FINDINGS_INTAKE.md`; you do not need
to use that format yourself — send what you found, and it will be transcribed.
