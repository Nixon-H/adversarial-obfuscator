# Review findings — filed register rows

**Status: one finding filed, self-reported; now RESOLVED in code, still
unreviewed.** No independent reviewer has returned anything; the channel is
live and empty. The row below was found by the maintainer while testing the
weaknesses documented in `CRYPTO_REVIEW_BUNDLE_STANDALONE.md` §8, filed in
this format so the first real returned finding has a worked example to sit
beside, and then fixed at the repository owner's explicit direction.

The `reviewer:` field says so plainly, and the resolution records a second
field for the same reason: `reviewed-by: NOBODY`. A maintainer finding closed
by maintainer design is not an independent review, and the register must not
let the format blur that. The fix is exactly the thing a cryptographer should
now look at hardest.

---

## MIMOSA-INTAKE-001

```
FINDING MIMOSA-INTAKE-001
  package:      crypto
  reviewer:     maintainer (self-reported; NOT an independent review)
  received:     2026-11-23
  severity:     high
  claim:        A section from one pack is accepted into another pack built
                with the same session key and the same total length, because
                the authenticated context does not bind a pack identity.
  evidence:     Two packs built with the same key, same section count (4) and
                same total (32 bytes) differ only in plaintext and nonces.
                Replacing sections 0-1 of pack A with sections 0-1 of pack B,
                then recomputing the UNKEYED structural digest, joins without
                error and yields mixed plaintext:

                  ACCEPTED, plaintext: b'BBBBBBBBBBBBBBBBAAAAAAAAAAAAAAAA'
                  expected A         : b'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'

                The MAC verified for each substituted section: ctx_i binds
                (v, i, total, nonce) but not which pack the section came from.
                Same-key packs of equal total are therefore interchangeable
                section-by-section.

                Scope is bounded by the total: substituting a section from a
                pack of DIFFERENT total is refused with "section 0 integrity
                failure", because total is in ctx_i.

                All three emitted loader templates (_mctx construction in
                section_split.py) share the same context, and no pack-id
                concept exists anywhere in the module.
  reproducible: yes
                python3 -c "import sys,copy; sys.path.insert(0,'.');
                from obfuscator.section_split import split_sealed, stream_join;
                from obfuscator.pack_state import state_digest;
                K=b'\x11'*32;
                a=split_sealed(b'A'*32,sections=4,key=K,nonce_seed=b'aaa');
                b=split_sealed(b'B'*32,sections=4,key=K,nonce_seed=b'bbb');
                f=copy.deepcopy(a); f['sections'][0]=copy.deepcopy(b['sections'][0]);
                f['state']=state_digest(f['sections'],f['count'],f['total']);
                print(bytes(stream_join(f,K))[:40])"
  affects:      obfuscator/section_split.py — _mac_context_v2 (§4 of the
                bundle) and the three emitted loader templates that reproduce
                it inline
  maintainer-response:
                accept
  resolution:   RESOLVED in pack format v3, at the repository owner's explicit
                direction (not a unilateral maintainer call). v3 appends a
                16-byte per-pack identity to every section's MAC context:

                  pack_id = SHA256(b"nx-pack-id:" || K || pack_nonce)[:16]

                where pack_nonce is 16 random bytes per build carried in the
                pack header. A section spliced from another pack now fails
                its tag even under the same key and the same total.

                MEASURED AFTER: the same splice that produced
                b'BBBBBBBBBBBBBBBBAAAAAAAAAAAAAAAA' now raises
                "section 0 integrity failure".

                COMPATIBILITY: v2 packs remain loadable and STILL CARRY the
                weakness -- the fix protects v3 artefacts, not already-shipped
                ones. That trade is recorded in the bundle's section 8 item 8
                and asserted by
                test_the_v2_path_still_has_the_splice_weakness, so it cannot
                be quietly forgotten.

                DEFECT FOUND WHILE IMPLEMENTING: `_mac_context_v2` prefixed
                the module constant SECTION_PACK_VERSION rather than the
                PACK's declared version, so the moment the constant became 3
                every v2 pack hashed version 3 into its context and failed its
                own tags -- i.e. the change would have made every previously
                built artefact unloadable, the exact compatibility cliff
                versioning exists to avoid. Fixed by taking the version as a
                parameter; caught by the v2-compatibility test, which was
                written before the fix specifically to catch it.

  reviewed-by:  NOBODY. This is a maintainer finding closed by maintainer
                design at owner direction. The v3 context is UNREVIEWED and
                the bundle asks a reviewer to treat it as such (section 8 item
                9, section 4.1). Closing this row does not close the crypto
                review row.
```

## Why this row is severity `high` and not `critical`

The attack needs the attacker to hold the session key: without `K` the
substituted section's MAC cannot verify, so this is not a key-recovery or
forgery-without-key issue. What it defeats is a property the design implies —
that a pack is a self-contained unit whose sections cannot be spliced. An
attacker who has `K` (a customer who extracted it from their own deployment, or
anyone who obtains it) can now build a mixed artefact that executes with
sections from two different payloads.

That is a real loss of integrity, but it requires prior key compromise, so
`high` rather than `critical`. A reviewer may disagree with that grading; the
field is recorded rather than defended.

## What this does NOT change

* It does not close the crypto review row. One self-found defect is not a
  review, and the bundle's §8 already listed the underlying design choice
  ("no pack identity in the context") as something for a reviewer to judge.
  Finding it exploitable raises its priority; it does not substitute for the
  adjudication.
* It does not change the three packages' `NOT PERFORMED` / `NOT RUN` banners.
* The mitigation is deliberately left OPEN rather than patched in a hurry,
  because a wire-format change made to close a self-found finding — without the
  independent review that was commissioned to judge exactly this construction —
  is the kind of unilateral redesign the register's §2 warns against.

---

## MIMOSA-INTAKE-002

```
FINDING MIMOSA-INTAKE-002
  package:      crypto
  reviewer:     maintainer (self-reported; NOT an independent review)
  received:     2026-11-23
  severity:     low
  claim:        split_sealed() derives section nonces deterministically from
                nonce_seed, so two packs built with the SAME session key AND
                the same nonce_seed reuse the keystream, and the XOR of their
                ciphertexts reveals the XOR of their plaintexts (a two-time
                pad). The API permits this; the shipped call path does not
                currently trigger it.
  evidence:     Two packs, same key, same nonce_seed, different plaintext:

                  a = split_sealed(b'A'*32, sections=4, key=K, nonce_seed=b'reused')
                  b = split_sealed(b'B'*32, sections=4, key=K, nonce_seed=b'reused')
                  ca = bytes.fromhex(a['sections'][0]['data'])
                  cb = bytes.fromhex(b['sections'][0]['data'])
                  xor = bytes(p^q for p,q in zip(ca, cb))
                  xor[-4:] == b'\x03\x03\x03\x03'

                The trailing 4 bytes equal A^B for the plaintext. The 32-byte
                prefix is the tag difference (the tags differ because their
                contexts differ), so the tag does NOT prevent plaintext
                recovery from the body. pack_nonce and per-section nonces are
                byte-identical across the two packs.

                SCOPE, measured rather than assumed: in the shipped path
                (pipeline.py:3763) the honey pack derives its seed from
                _section_pack_val, and build_id is _hp_seed[:16].hex() -- i.e.
                the key and the nonces are BOTH functions of the same per-build
                input. Distinct builds therefore give distinct (key, nonce)
                pairs and the hazard does not fire in normal operation.

                The hazard is API-level: nonce_seed exists so the decoy pack is
                reproducible across builds of the SAME inputs, and any caller
                that reuses a seed across two DIFFERENT payloads under one key
                gets keystream reuse. Nothing in split_sealed refuses that.
  reproducible: yes (the two lines above; no repository state needed)
  affects:      obfuscator/section_split.py — split_sealed() nonce_seed path;
                obfuscator/honeypayload.py build_honey_pack()
  maintainer-response:
                accept
  resolution:   OPEN. Two candidate fixes, neither chosen unilaterally:
                  (a) refuse a nonce_seed that repeats for a different payload
                      (requires build-level state, which split_sealed does not
                      have and should not acquire);
                  (b) derive the per-section nonces from
                      SHA256(key ‖ nonce_seed ‖ i) rather than
                      SHA256(nonce_seed ‖ i), so the same seed under a
                      different key cannot collide -- this is the surgical fix
                      and does not change what a caller must supply.
                Candidate (b) is a wire-format change again (v2/v3 nonce
                derivation), so it belongs with the independent review that is
                already looking at this construction, not ahead of it.
  reviewed-by:  NOBODY. Maintainer-found, maintainer-graded `low` on the
                argument that the shipped path cannot trigger it. A reviewer
                should check that argument specifically: it rests on
                build_id = f(seed), and if any future caller passes a seed and
                a build_id that are not so related, the exposure becomes real.
```

## Why this one is `low` and not higher

The shipped path cannot reach it: `build_id` is derived from the same
`_section_pack_val` that seeds the nonces, so a colliding nonce implies a
colliding key (and therefore a colliding pack, which is the same artefact).

It is filed anyway, for two reasons:

1. **The API is public surface.** `split_sealed(payload, key=..., nonce_seed=...)`
   is called by `build_honey_pack`, exported through `pack_json`, and used by
   tests. A future caller — including the decoy path after a refactor — can
   satisfy the collision condition without noticing.
2. **It is the same class as `key_hint`** in the bundle's §8 item 3: a
   hazard that is currently unreachable but that a reviewer should judge rather
   than accept on the maintainer's say-so. That is exactly what the register's
   §6 means by "your own sampling is not independent verification".
