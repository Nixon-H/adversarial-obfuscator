# Cryptographic review package — section pack v2

**Purpose.** This is the evidence bundle for the register's P1 row *independent
cryptographic review of the production section encryption*. It is written to
be handed to a reviewer who has not seen this codebase, and it is written to
help them find problems rather than to persuade them there are none.

**Status of the review itself: NOT PERFORMED.** This document is the
commissioning package. No independent cryptographer has examined this
construction. Everything below is the maintainers' own description plus
measured test output, and the register treats it as such.

Target commit: `8b4cb91503e46637295e0046d833b80f3cd42173`
Source file: `obfuscator/section_split.py`
Related: `obfuscator/pack_state.py`, `obfuscator/core/pipeline.py` (loader emission)

---

## 1. What the construction is for, and its threat model

The obfuscator ships a Python payload to a customer as a native-loader
artefact. The payload is split into N sections so that the whole plaintext is
never resident in one buffer, and each section is sealed so a partial dump
yields no complete code object.

**What this construction protects against:** a customer who holds the
artefact and wants the payload plaintext, and who can edit the pack freely.

**What it does NOT protect against, and no claim is made that it does:**

* an attacker who can execute code in the loader's process and read memory
  after the plaintext has been reassembled — the plaintext must exist in
  memory to execute, and this construction only narrows the window;
* an attacker who obtains the session key by other means (the key travels
  via the existing `BLOB_KEY` path, never inside the pack);
* side channels (timing, cache, power). Not modelled, not claimed.

A reviewer should treat "narrows the window" as the entire security claim.
Any finding of the form "an attacker who already has X can do Y" is out of
scope unless X is something this construction was supposed to withhold.

## 2. The primitive set, and why it is not AES-GCM

The loader runs on customer machines that may have no `cryptography` wheel
and no compiler. The section path therefore cannot depend on AES-GCM even
though `obfuscator/core/pipeline.py` has an AEAD helper for other paths
(`seal_aead` / `open_aead`, used where the dependency is available). What is
available unconditionally is `hashlib.sha256` and `hmac`.

So the construction is built from SHA-256 and HMAC-SHA256 only:

```
keystream(key, nonce, n) = SHA256(key ‖ nonce ‖ ctr8) ‖ SHA256(...) ‖ ... truncated to n
```

This is a hash-based stream cipher (SHA-256 in counter mode), not a
standardised one. **A reviewer should say plainly whether they consider this
acceptable for the stated threat model**, and what they would require
instead. Section 7 lists the specific questions.

## 3. The construction, precisely

### 3.1 Key derivation (build and load are the same code)

Master session key `K` (32 bytes) arrives out of band. Per section `i` with
16-byte random nonce `N_i`:

```
basis   = K ‖ u32be(i) ‖ N_i
K_enc_i = SHA256(b"nx-section-enc:" ‖ basis)
K_mac_i = SHA256(b"nx-section-mac:" ‖ basis)
```

Domain separation is by the ASCII personalisation prefix. Section index and
nonce are both inside the derivation, so each section's keys are distinct
even under a repeated nonce — which matters because nonces are random per
build (see 3.5).

### 3.2 Authenticated context (the AAD role)

```
ctx_i = u32be(2) ‖ u32be(i) ‖ u32be(total) ‖ N_i
```

where `2` is the pack format version and `total` is the pack's declared
plaintext length. Version is bound so a pack cannot be downgraded to the v1
scheme by editing the `v` field.

### 3.3 Seal (build side)

```
tag_i  = HMAC-SHA256(K_mac_i, ctx_i ‖ plaintext_i)
body_i = tag_i ‖ plaintext_i                    # 32-byte tag, then data
ct_i   = body_i XOR keystream(K_enc_i, N_i, len(body_i))
```

### 3.4 Open (load side, `stream_join`)

```
tag‖part = ct_i XOR keystream(K_enc_i, N_i, len(ct_i))
assert HMAC-SHA256(K_mac_i, ctx_i ‖ part) == tag        # constant-time compare
plaintext_i = part
```

Then: section count matches, indices are `0..count-1`, and the concatenation
length equals `total`.

### 3.5 Nonce generation

16 random bytes from `os.urandom` per section per build, except when the
caller passes `nonce_seed` (used by the decoy pack, which must be
deterministic for reproducible-build checks — see
`tests/test_reproducible_build.py`). Random nonces are safe here only because
the key is fresh per build; a reviewer should confirm that reasoning holds
and state whether they want a counter instead.

### 3.6 Structural state digest (second, non-cryptographic check)

`state = SHA256(STATE_SCHEMA ‖ count4 ‖ total8 ‖ Σ(i4 ‖ salt))[:32]`, where
`salt = SHA256(K_enc_i ‖ N_i)[:16]`. This is unkeyed and is not a
security boundary — it detects accidental inconsistency and forces an
attacker to make their edit self-consistent. It is checked BEFORE the MACs.
A reviewer should treat it as a debugging aid, not as authentication.

## 4. Properties this construction claims, and how each is tested

| claim | test |
|---|---|
| a section relabelled to another index fails | `test_section_split.py`, `test_reorder_pack.py` |
| sections reordered fail | `test_reorder_pack.py` |
| a section from another pack fails | `test_section_split.py` |
| declared `total` edit fails | `test_section_split.py` |
| `v` downgrade 2→1 fails | `test_section_split.py` |
| truncated section fails | `test_section_split.py` |
| any single-byte flip in a section fails | `test_byte_tamper_sweep.py` |
| corrupted `state` field fails closed | `test_pack_state.py` |
| negative/oversized `count`/`total`/`index` refuse, not crash | `test_parser_fuzz.py` |
| a valid pack still round-trips | `test_section_split.py`, `test_section_split_wiring.py` |

Measured on the target commit: 40 tests across those four suites, all passing.

Coverage-guided fuzzing of the pack parser (review register §5) ran
4,075,415 executions at `cov: 61 / ft: 185` with **zero** unintended
acceptances; see `docs/research/pydeobsbench-2026-11-18.md` §6j.3.

## 5. Known weaknesses, stated by the maintainers

A reviewer should start here rather than rediscovering them.

**5.1 It is MAC-then-encrypt, not an AEAD.** The tag is prepended to the
plaintext and the whole lot is XORed with the keystream. Verification happens
after decryption, before any plaintext is released. Measured by the
maintainers: in `stream_join` the `joined.extend(part)` at source line 80 is
strictly after the `compare_digest` at line 77, and all three emitted loader
templates have the same ordering — no plaintext is accumulated or sunk before
its section's tag verifies. That ordering is correct for a stream cipher.
What remains unproven is that a MAC-then-encrypt composition over a
hash-based keystream is sound at all: it has no reduction to a named security
notion. **This is the single most important thing to review.**

**5.2 The stream cipher is bespoke.** SHA-256 in counter mode with a
key‖nonce‖counter input is a reasonable-looking design, but "reasonable
looking" is not a security argument. No proof, no cryptanalysis, no
independent review. Parallel to 5.1.

**5.3 `key_hint` is an unkeyed oracle.** The pack carries
`key_hint = SHA256(K)[:16]`. It is checked before the MACs. It leaks 16 bytes
of a hash of the session key to anyone holding the pack. Since the session
key is already derived from licence/HWID material the holder may partly know,
a reviewer should assess whether this materially helps an offline attacker,
and whether it should be removed, truncated further, or an HMAC instead.

**5.4 No nonce-reuse protection is enforced at load.** If a build reused a
nonce under the same key, the loader would not notice. Key derivation
includes the index so cross-section reuse is harmless, but same-section reuse
across two packs under one key would XOR two keystreams. Random nonces plus a
fresh key per build make this improbable, not impossible.

**5.5 Section length is implicit.** The length of `ct_i` is the length of the
hex string. The tag covers `part` but not `len(part)` explicitly — length is
bound indirectly via `total` and the final join check. A reviewer should
decide whether that is sufficient or whether the length belongs in `ctx_i`.

**5.6 `salt` is unkeyed and unverified.** It is used only in the state
digest. An attacker can recompute the state digest to match any salt edit.
This is by design (the digest is not a security boundary) but should be
confirmed as understood rather than accidental.

**5.7 The v1 legacy path remains.** Packs with `v` absent or 1 use a single
key for both roles and a MAC over plaintext only, with no metadata binding.
It exists so old artefacts stay loadable. A reviewer should confirm that
binding `2` into `ctx_i` genuinely prevents downgrade (the claim tested in
§4) and say whether the legacy path should be removed outright.

## 6. Specific questions for the reviewer

1. Is MAC-then-encrypt over a SHA-256 counter-mode keystream acceptable for
   the stated threat model, or must this become a standardised AEAD?
2. If a standardised AEAD is required, is a small audited native dependency
   (e.g. a vendored, pinned implementation) operationally acceptable given
   that the loader must run without a compiler on customer machines? Or is
   AES-128-CTR + HMAC-SHA256 (encrypt-then-MAC, both stdlib-feasible) the
   right middle ground?
3. Does `ctx_i` bind everything it needs to? Specifically: should section
   length and/or a pack identifier be added?
4. Is `key_hint` (5.3) a material weakness, and what is the recommended fix?
5. Is the random-nonce-per-build argument (3.5) sound, or should a counter
   be mandatory?
6. Does the state digest's position (before the MACs) create any
   distinguishability or denial-of-service issue worth changing?
7. Is `hmac.compare_digest` used everywhere a tag is compared? **Measured by
   the maintainers: yes — four sites (in-process join at line 292 and the
   three emitted loader templates at 729, 830, 933), each verified by
   inspecting the surrounding block.** Please confirm on your own reading
   rather than trusting this line.
8. Any information leakage from error messages — the loader distinguishes
   "count mismatch", "state invalid", "integrity failure", "length mismatch".

## 7. What the maintainers are NOT claiming

* Not that this is cryptographic security. Passing the tamper matrix means
  specific attacks were rejected; it says nothing about attacks not tried.
* Not that the construction is novel or better than a standard AEAD. It
  exists because of a deployment constraint (no `cryptography` wheel on the
  loader host), not because it was preferred.
* Not that the surrounding code is in scope. This package covers
  `section_split.py` and `pack_state.py` only. Licence derivation, HWID
  binding and the native loader's memory protections are separate surfaces
  and would need their own review.

## 8. How to reproduce the measurements

```
python3 -m pytest -q tests/test_section_split.py tests/test_pack_state.py \
    tests/test_reorder_pack.py tests/test_byte_tamper_sweep.py
```

Fuzzing (needs atheris; 45 s per target is enough to see coverage grow):

```
python3 -m venv /tmp/fv && /tmp/fv/bin/pip install atheris
NX_FUZZ_TARGET=pack NX_FUZZ_SECONDS=45 /tmp/fv/bin/python scripts/fuzz/nx_fuzz.py
```

A build that produces a v2 pack, for inspection:

```
NIXON_ARTEFACT_SIGN_KEY=<hex> NIXON_BUILD_MANIFEST_KEY=<hex> \
NIXON_REQUIRE_PROVENANCE=1 NIXON_PROVENANCE_PUBKEY=<hex> \
python3 -m obfuscator.core.pipeline build tests/fixtures/payload_probe.py \
    --skip-cloud --section-count 4 --package native
```

The pack JSON is embedded in the emitted loader as a sealed literal; to
inspect it, call `obfuscator.section_split.split_sealed(payload, key=K)` in a
REPL and read the returned dict directly.

## 9. Why this package exists

The register's P1 row cannot be closed by the maintainers: an independent
review requires a reviewer. What can be closed is the *commissioning* — a
package complete enough that a cryptographer can start without interviewing
anyone, with the maintainers' own weaknesses named so the review is not spent
rediscovering them. When a reviewer returns findings, the rows they generate
belong in the same register as every other measured item in this project.
