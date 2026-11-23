# Section pack v3 — standalone review bundle

**What this is.** A self-contained description of the construction in
`obfuscator/section_split.py`, written so a cryptographer can review it
**without cloning the repository**. Everything needed to reason about the
design is here; §7 lists the files to request if you want the code itself.

**Status: NOT REVIEWED.** No cryptographer has examined this construction. This
document is what a reviewer would be sent, not a record of a review.

**Companion document.** `CRYPTO_REVIEW_PACKAGE.md` in the same repository is
the longer version, with the threat model, the tamper-matrix mapping and
reproduction commands. This bundle is the extract that stands alone.

Target: `obfuscator/section_split.py` (pack format v3). The exact commit is
recorded in `REVIEW_FINDINGS_FILED.md` MIMOSA-INTAKE-001 and pinned by
`tests/test_section_substitution_finding.py`; no hash is restated here,
because a hand-copied hash in a document goes stale and a *fabricated* one is
worse than none.

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
ctx_i = u32be(v) ‖ u32be(i) ‖ u32be(T) ‖ N_i ‖ pack_id          (28 or 44 bytes)
```

`v` is the PACK's declared version (bound so a pack cannot be downgraded to the
v1 scheme by editing `v`). `T` is bound so the pack cannot be re-pointed at a
different total.

**`pack_id` is new in v3** — see §4.1. It is empty for v2 packs, which makes
the context 28 bytes there and 44 bytes for v3.

```
pack_id = SHA256(b"nx-pack-id:" ‖ K ‖ pack_nonce)[:16]
```

`pack_nonce` is 16 random bytes per build, carried in the pack header and NOT
secret. The key mixing is what gives the id its binding force: an attacker
holding only the pack cannot compute the id another pack would accept.

### 4.1 Why pack_id exists — a defect found and fixed during this work

The v2 context bound `(v, i, T, N_i)` and nothing identifying the pack. Two
packs built with the same session key and the same total length were therefore
**interchangeable section-by-section**. Measured before the fix:

```
splice pack B's sections 0-1 into pack A, recompute the unkeyed digest:
joined  : b'BBBBBBBBBBBBBBBBAAAAAAAAAAAAAAAA'
expected: b'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
```

Every substituted section's MAC verified. The fix binds a per-pack identity.

**Please review this fix as unreviewed maintainer design.** It is our answer to
our own finding, which is precisely the independence gap this review exists to
close. §8 item 8 covers what it does *not* fix.

### 4.2 Encoding of the context — is it canonical?

The context is a bare concatenation with no delimiters, so whether it is an
*injective* encoding is a real question: if two different tuples
`(v, i, T, N, pack_id)` could produce the same bytes, two distinct sections
would share a MAC input.

**It is injective, and the reason is entirely fixed-width fields:**

| field | width | note |
|---|---|---|
| `v` | 4 | always the FIRST field |
| `i` | 4 | |
| `T` | 4 | |
| `N_i` | 16 | fixed by §3.5 |
| `pack_id` | 16 | v3 only; absent (not empty) in v2 |

v2 context = 28 bytes, v3 = 44. Since every field has a fixed width and the
version comes first, the parse is unambiguous for any given version, and the
version itself differs between the two lengths — so a 44-byte v3 context can
never be reinterpreted as a 28-byte v2 one.

**Three things we are NOT claiming, which a reviewer should check:**

1. **The construction has no length prefixes.** It is a bare concatenation
   `ctx_i ‖ plaintext_i`, and `plaintext_i` is variable-length — measured:
   a 10-byte payload over 4 sections gives chunks of 3, 3, 3, 1 bytes. It works
   because `ctx_i` is fixed-width, so the boundary between context and plaintext
   is always exactly byte 44 (v3) or 28 (v2). Two consequences a reviewer should
   confirm:
   - within a section there is no ambiguity: the split point is determined by
     the version alone;
   - across sections there is none either, because `ctx_i` differs in the index
     field, so `ctx_0 ‖ P0` cannot equal `ctx_1 ‖ P1` for any plaintexts.
   We verified both. What we have NOT done is prove that adding a length prefix
   would be unnecessary under refactoring — if `ctx_i` ever becomes
   variable-width, the encoding stops being injective and the tag stops being
   meaningful.
2. **Bounds are enforced in Python, not in the encoding.** `u32be(i)` and
   `u32be(T)` require `0 <= value < 2^32`; the join refuses out-of-range values
   before constructing the context. If that check were removed, `int.to_bytes`
   would raise rather than silently wrap — but a future refactor to a
   fixed-width C integer would wrap instead.
3. **`pack_id` is appended, not substituted for a length.** A v2 pack has no
   `pack_id` at all rather than a zero-length one, which is why the two
   versions have different context lengths rather than a common prefix. §8 item
   8 covers why v2 was kept.

We do not have a proof that this composition is sound — §8 item 1 says so. What
we can state is the narrower fact relevant here: **the encoding is injective
given fixed-width fields, and the version is bound first.** Please confirm or
refute that reading.

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
6. **`salt` is KEYED, and the pack publishes three 64-bit truncations.**
   (Corrected 2026-11-23, finding MIMOSA-INTAKE-003.) An earlier revision of
   this section called `salt` "unkeyed" — that was wrong, and it was wrong in
   the direction that flatters the construction, so it is corrected here rather
   than quietly. `salt = SHA256(K_enc_i ‖ N_i)[:16]` is a truncated hash of the
   *encryption key*, differs per section, and is used in the structural digest.
   The pack therefore publishes three independent 64-bit values derived from
   key material:

   ```
   key_hint = SHA256(K)[:16]                            64 bits per pack
   salt_i   = SHA256(K_enc_i ‖ N_i)[:16]                64 bits per section
   pack_id  = SHA256("nx-pack-id:" ‖ K ‖ pack_nonce)[:16]
   ```

   Each is an offline oracle an attacker can test guesses against. Against a
   256-bit key, a 64-bit truncation is not a practical break (~2^64 per
   target), and we believe they are harmless — but **that is exactly the kind
   of judgement we should not be making about our own construction.** The
   question for you: are these acceptable, and should any of them be removed,
   narrowed, or replaced with an HMAC keyed differently from the encryption
   path?
7. **The v1 legacy path remains** (single key for both roles, no metadata
   binding), kept so older artefacts stay loadable.
8. **v2 packs still carry the splice weakness.** The v3 fix protects v3 packs
   only. A v2 pack has no pack identity in its context and remains
   interchangeable section-by-section under one key and one total. We kept v2
   loadable deliberately, so **the fix does not retroactively protect already
   shipped artefacts** — an operator who wants the property must rebuild. A
   reviewer should say whether that trade is acceptable, and whether v2 should
   be refused at load under a policy flag the way v1 already can be
   (`NIXON_REQUIRE_PACK_V2`).
9. **The v3 fix is maintainer design.** It binds a per-pack identity derived
   from the session key and a header nonce. It was not reviewed by anyone
   independent, and the nonce is attacker-visible, so the security rests
   entirely on the key mixing. That is a question for §9, not a claim.

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

## 11. Worked test vector — check the construction by hand, no code needed

This is the fastest way to satisfy yourself that §3–§5 describe what the
builder actually does. Recompute it with a standard-library-only script; if
every value below matches, the specification and the implementation agree.

Inputs:

```
K           = 000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f
plaintext   = 4142434445464748            ("ABCDEFGH", 8 bytes)
nonce_seed  = 766563746f72                ("vector")
```

Pack-level outputs (v3, 2 sections):

```
pack_nonce  = 5549563aed1e0f84069b3d0dbe9d9cf7
pack_id     = 5b1f3620a4cf5b1cc4979f2d94cf6e4e      (16 bytes)
key_hint    = 630dcd2966c43366
state       = eae758258ea4975adcb4a802d68b5170
v = 3   count = 2   total = 8
```

Section 0 and 1, with every intermediate the reviewer needs to verify:

```
--- section 0 ---
nonce       = f59dcefd82e7c385dae4264e1193c4af
enc_key     = 0129e91768c48513f2ee2aa6fd7eab2daa17fafb5d135ec4c521140b17703cf0
mac_key     = 0f354d91e5242ce78044b22e1b8d5ed013159299d287687386ec52cad9f45224
ctx         = 00000003 00000000 00000008 f59dcefd…c4af 5b1f3620…6e4e   (44 bytes)
salt        = c7401dba1e9fbcdf
plaintext_0 = 41424344                    ("ABCD")
tag         = 3ac5b01ffc3d691ad2a0635d76cc5f2d37ffacc043cb2d284f92d66dbeda9a23

--- section 1 ---
nonce       = bd433f1f970e6ef95f036f9d54e1bf98
enc_key     = bd5b1a54554207be6052ad9791ca9ff8d85beb712eaa39fac118bd8d4a28653d
mac_key     = 75ff1cb8917363f9bc57db1fddce735c84f359fc0b40ba6b69b2e5e300057c65
ctx         = 00000003 00000001 00000008 bd433f1f…bf98 5b1f3620…6e4e   (44 bytes)
salt        = 5e459fe597a2ad2a
plaintext_1 = 45464748                    ("EFGH")
tag         = b2b4a3ffa0e897f00cda84b5dd0b39fb7331b3ba1188b038017580e3a30335ee
```

Verification recipe — nothing beyond `hashlib` and `hmac`:

```python
pack_id = sha256(b"nx-pack-id:" + K + pack_nonce)[:16]
basis   = K + i.to_bytes(4,"big") + nonce
enc_key = sha256(b"nx-section-enc:" + basis)
mac_key = sha256(b"nx-section-mac:" + basis)
ctx     = v.to_bytes(4,"big") + i.to_bytes(4,"big") \
          + total.to_bytes(4,"big") + nonce + pack_id
tag     = hmac.new(mac_key, ctx + plaintext_i, sha256)
salt    = sha256(enc_key + nonce)[:16]
```

**These values were reproduced in a clean interpreter importing nothing from
this project** — only `hashlib` and `hmac` — before being published here.
`scripts/fuzz/gen_crypto_test_vectors.py` regenerates them, and
`tests/test_crypto_test_vectors.py` fails if the implementation drifts from
them. If your recomputation disagrees with any line above, that is a finding:
tell us which one.

## 12. How to check the rest of our measurements

```sh
git clone https://github.com/Nixon-H/adversarial-obfuscator
cd adversarial-obfuscator
export PYTHONPATH="$PWD"
python3 -c 'import sys; from pytest import console_main; sys.exit(console_main())' \
    -q tests/test_section_split.py tests/test_pack_state.py \
       tests/test_reorder_pack.py tests/test_byte_tamper_sweep.py
```

Expected **40 passed** — re-verified on the v3 tree, which is the same count as
under v2 because the v3 work added tests to *other* modules (the pack-identity
and seed-reuse findings), not to this tamper-matrix set. If you get a different
number, the suite moved and §4's table needs re-checking rather than the number
being wrong. Coverage-guided fuzzing of the
pack parser reached `cov: 61 / ft: 185` over 4,075,415 executions with zero
unintended acceptances; `scripts/fuzz/nx_fuzz.py` reproduces it (45 s is enough
to see coverage grow — and `cov: 1` means the harness is not instrumenting, not
that the parser is clean).

## 13. How to return findings

Privately, via
<https://github.com/Nixon-H/adversarial-obfuscator/security/advisories/new>
or to the maintainer directly. Findings are filed as register rows in the
15-field format of `docs/security/REVIEW_FINDINGS_INTAKE.md`; you do not need
to use that format yourself — send what you found, and it will be transcribed.
