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

---

## MIMOSA-INTAKE-003

```
FINDING MIMOSA-INTAKE-003
  package:      crypto
  reviewer:     maintainer (self-reported; NOT an independent review)
  received:     2026-11-23
  severity:     medium
  claim:        The review bundle's section 8 item 6 describes `salt` as
                "unkeyed and unverified". It is neither: salt is
                SHA256(K_enc_i || nonce)[:16], a truncated hash of the
                ENCRYPTION KEY, and it is checked indirectly (see below).
                A reviewer relying on the document would reach the wrong
                conclusion about three published 64-bit truncations.
  evidence:     Recomputing from the shipped builder:

                  nonce = bytes.fromhex(sec["nonce"])
                  skey, _ = _section_keys_v2(K, sec["i"], nonce)
                  sha256(skey + nonce).hexdigest()[:16] == sec["salt"]

                holds for every section in every pack tested. The `salt`
                field is therefore KEYED, and differs per section because
                the key differs per section.

                What the pack publishes, then, is THREE independent 64-bit
                truncations derived from key material:

                  key_hint = SHA256(K)[:16]                      (64 bits)
                  salt_i   = SHA256(K_enc_i || N_i)[:16]         (64 bits/section)
                  pack_id  = SHA256("nx-pack-id:"||K||pack_nonce)[:16]

                None is a practical break of a 256-bit key (~2^64 per
                target), and key_hint was already filed as bundle section 8
                item 3. The finding is that the document UNDERSTATES the
                set: it calls one of the three "unkeyed" and does not
                enumerate them together. A reviewer asked "are there offline
                oracles against the session key?" is told about one and
                implicitly told the other is not one.
  reproducible: yes (the four lines above, against any built pack)
  affects:      docs/security/CRYPTO_REVIEW_BUNDLE_STANDALONE.md section 8
                item 6; docs/security/CRYPTO_REVIEW_PACKAGE.md section 3.6;
                obfuscator/section_split.py salt emission (line ~259)
  maintainer-response:
                accept
  resolution:   DOCUMENTATION FIX APPLIED (this pass): both documents now
                describe salt as keyed and list the three truncations
                together as one question for the reviewer. No code change:
                whether the published truncations are acceptable is a design
                question for the independent review, not something to change
                ahead of it.
  reviewed-by:  NOBODY. This is a maintainer finding about maintainer
                documentation. It is filed rather than silently corrected
                because the register's whole purpose is to record what was
                claimed and what was measured -- and the claim here was wrong
                in the direction that flatters the construction.
```

## Why a documentation error is filed as `medium`

Because of the direction it is wrong in. The bundle's §8 is the maintainers'
own list of weaknesses, offered to a reviewer as an honest starting point. An
entry that says "unkeyed, not a security boundary" about a value that is in fact
a keyed truncation tells the reviewer *not* to look at something they should.

The three truncations may well be harmless — 64 bits each against a 256-bit key
is not a break, and the same argument was already made for `key_hint`. But that
is an assessment for the reviewer, and they can only make it if the document
describes the values correctly.

This finding was produced by auditing the document against the code rather than
by reading either alone. That is a technique the register should note: two of
the three findings so far came from making a document and an implementation
disagree, which is exactly what an independent reviewer does and exactly what
no amount of re-reading one artefact finds.

---

# Second assessment round — six auditor scopes, 2026-11-23

Four scopes were worked in this pass (Crypto, Protocol, and the two that
overlapped them); two remain unstarted and are named at the end. **None of
these is an independent review.** They were produced by the same maintainer
session that wrote the code, working from the code and a built artefact. The
verification discipline is the compensating control: every claim below carries a
reproduction that was executed, and one hypothesis is recorded as *disproved*
because the reproduction did not support it.

The adversarial-verification pass was applied to each finding before filing.
Findings that did not survive it are in the "Disproved" section rather than the
register, so the register does not accumulate plausible-sounding claims.

---

AI-CRYPTO-004
```
FINDING AI-CRYPTO-004
  package:      crypto
  reviewer:     maintainer (self-reported; NOT an independent review)
  received:     2026-11-23
  severity:     high
  confidence:   high (reproduced against a shipped artefact, no key material)
  claim:        The honeypayload is identifiable from the artefact alone. Its
                key is derived from inputs that the artefact itself publishes,
                so an analyst can decrypt the decoy and determine which of the
                two packs is the deliverable without recovering the real key.
  attacker-capability:
                Read access to the shipped .py loader. No licence, no hardware
                id, no keys, no execution, no side channels.
  technical-explanation:
                pipeline.py builds the decoy seed from the REAL section pack,
                which is emitted verbatim into the same file as
                _NX_SECTION_PACK:

                    _hp_seed = sha256(str(_section_pack_val).encode()).digest()
                    _hp = build_honey_pack(_hp_seed, _hp_seed[:16].hex())

                and honeypayload.decoy_key derives the sealing key from the
                build id alone:

                    return sha256(b"nx-honey-decoy:" + build_id.encode()).digest()

                _section_pack_val IS the b85 string assigned to
                _NX_SECTION_PACK (pipeline.py:3669 sets it, :3747 emits it), so
                every input to the decoy key is printed in the artefact. The
                decoy's key_hint is ALSO published (_NX_HONEY_HINT), so the
                derived key can be confirmed before any decryption is tried;
                then the hint distinguishes the two packs in one hash.
  reproduction: Read only the emitted loader:

                  real  = _NX_SECTION_PACK          # emitted verbatim
                  seed  = sha256(real.encode()).digest()
                  bid   = seed[:16].hex()
                  key   = sha256(b"nx-honey-decoy:" + bid.encode()).digest()
                  assert sha256(key).hexdigest()[:16] == _NX_HONEY_HINT

                Against a real `obfuscator.core.pipeline build` artefact:

                  STEP 3  derived hint 18262733fbf0c44e vs emitted 18262733fbf0c44e -> MATCH
                  STEP 4  decoy decrypted: 962 bytes, 61 lines
                  STEP 5  real pack key_hint  = 3e89d254d0faf552
                          decoy pack key_hint = 18262733fbf0c44e
                          derived decoy hint  = 18262733fbf0c44e

                The hint matches the DECOY, so _NX_SECTION_PACK is the
                deliverable. One hash, no key search.
  impact:       The design claim at honeypayload.py:24-25 and pipeline.py:3752-53
                ("cannot tell which is which without doing strictly more work
                than recovering the real one") is false. The decoy does not
                consume analyst budget; it labels the real payload. Every build
                that emits a honey pack carries this.
  remediation:  Any ONE of:
                  (a) derive the decoy key from material NOT in the artefact,
                      e.g. an operator-supplied decoy secret or the signing key;
                  (b) do not publish _NX_HONEY_HINT -- then the hint oracle is
                      gone, though the key is still derivable and the decrypted
                      decoy is still recognisable;
                  (c) generate the decoy seed from os.urandom into build-local
                      state that is not emitted (loses decoy reproducibility,
                      which a test currently depends on);
                  (d) drop the decoy and stop claiming it consumes attacker
                      budget.
                (a) preserves the design intent best; (d) is the honest choice
                if the layer is not going to be maintained.
  disproof:     Would be disproved if _section_pack_val differed from the
                emitted _NX_SECTION_PACK, if the hint did not match, or if the
                decoy failed to decrypt. All three were checked on a real
                built artefact, not a reconstruction; the hint matched and the
                decoy decrypted to its template text.
  fixed-by:     nobody yet. Code is unchanged.
  regression-test:
                WRITTEN. tests/test_ai_findings_regressions.py::
                test_decoy_key_is_not_derivable_from_the_artefact, marked
                xfail(strict=True) with this finding's id as the reason. It
                runs in every derived-shard gate run and reports as xfailed;
                when the defect is fixed it XPASSes and the strict marker turns
                that into a failure demanding the marker be removed, so the fix
                cannot land silently. An earlier revision of this row said such
                a test "cannot pass today, which is why it is specified rather
                than written" -- that was a way of not tracking it.
```

AI-CRYPTO-005
```
FINDING AI-CRYPTO-005
  package:      crypto
  reviewer:     maintainer (self-reported; NOT an independent review)
  received:     2026-11-23
  severity:     low
  confidence:   high (measured)
  claim:        Both review packages state that pack_id is a 64-bit truncation.
                It is 128 bits. The document understates the identifier by half
                while presenting it as one of "three published 64-bit
                truncations".
  attacker-capability:
                None needed; this is a documentation defect affecting reviewer
                judgement.
  technical-
  explanation:  PACK_ID_BYTES = 16, and _pack_id returns digest()[:16] -- 16
                BYTES = 128 bits. key_hint and salt use .hexdigest()[:16], which
                is 16 HEX CHARS = 64 bits. The two are written on adjacent
                lines as if they were the same kind of truncation:

                  key_hint = SHA256(K)[:16]                64 bits per pack
                  salt_i   = SHA256(K_enc_i || N_i)[:16]   64 bits per section
                  pack_id  = SHA256("nx-pack-id:"||K||N)[:16]
                                                           ^ presented as 64

                The `[:16]` means bytes in the pack_id line and hex chars in
                the other two -- the notation collision is what produced the
                error.
  reproduction: python3 -c "from obfuscator.section_split import _pack_id;
                            p=_pack_id(b'K'*32,b'N'*16);
                            print(len(p), len(p)*8, len(p.hex()))"
                -> 16 128 32
  impact:       A reviewer assessing "are three 64-bit oracles acceptable?" is
                under-counting the entropy of one of them by 64 bits. The
                direction is conservative (the real value is stronger), so it
                is filed low, not medium.
  remediation:  Correct both documents to say 128 bits (16 bytes) for pack_id
                and keep 64 bits (16 hex chars) for key_hint and salt, and make
                the byte-vs-hex distinction explicit on every line.
  disproof:     Would be disproved if PACK_ID_BYTES were 8. It is 16 (line 129).
  fixed-by:     DOCUMENTATION FIXED in this pass -- both packages now state 128 bits
                (16 bytes) for pack_id and explain the byte-vs-hex confusion.
  regression-test:
                tests/test_ai_findings_regressions.py::test_documents_state_the_true_pack_id_size
                (PASSES -- pins that the documents do not regress to 64 bits)
```

AI-PROTO-006
```
FINDING AI-PROTO-006
  package:      protocol
  reviewer:     maintainer (self-reported; NOT an independent review)
  received:     2026-11-23
  severity:     medium
  confidence:   high (reproduced twice: path-is-directory, read-only parent)
  claim:        ReplayLedger fails OPEN when it cannot persist. If the ledger
                path cannot be written, replay protection silently disappears
                and every presentation of the same token is accepted. No error
                is surfaced to the caller.
  attacker-capability:
                Ability to make the ledger path unwritable (read-only media, a
                directory occupying the path, restrictive permissions, a full
                filesystem) -- or simply a deployment on such media.
  technical-
  explanation:  ReplayLedger._store() catches OSError and returns silently:

                    try: ... os.replace(tmp, self.path)
                    except OSError: pass

                check_and_record() records the identity in its LOCAL dict and
                returns True regardless of whether _store() persisted:

                    data[identity] = moment
                    self._store(data)      # result ignored
                    return True

                On the next call _load() re-reads the (unchanged, absent) file,
                finds the identity missing, and accepts again.
  reproduction: directory occupying the ledger pathname:

                  led = ReplayLedger(path=<dir>, window_s=300)
                  [led.check_and_record(IDENT) for _ in range(3)]

                measured:  [True, True, True]      (expected [True, False, False])

                read-only parent directory:
                measured:  1st accepted True, 2nd accepted True
  impact:       The module's stated guarantee ("a second presentation inside
                the acceptance window is refused") does not hold on any
                deployment where the ledger cannot be written. The failure is
                silent, so an operator cannot distinguish "no replay occurred"
                from "replay detection is off".
  remediation:  Make persistence part of the acceptance decision:
                  * _store() should raise, and check_and_record() should
                    propagate a distinct StorageError rather than returning
                    True;
                  * licensing.verify() should treat that as a hard failure
                    (fail closed) or, at minimum, as a logged degraded mode
                    that the caller must opt into;
                  * a ledger that cannot be written on the FIRST run should
                    refuse to run rather than degrade invisibly.
  disproof:     Would be disproved if _store() raised and the caller saw it, or
                if check_and_record() inspected _store()'s result. Neither is
                the case.
  fixed-by:     nobody yet.
  regression-test:
                tests/test_ai_findings_regressions.py::test_unwritable_ledger_fails_closed
                marked xfail(strict=True) with this finding id as the reason:
                it runs every gate run, reports xfailed, and XPASSes into a
                failure the moment the defect is fixed.
```

AI-PROTO-007
```
FINDING AI-PROTO-007
  package:      protocol
  reviewer:     maintainer (self-reported; NOT an independent review)
  received:     2026-11-23
  severity:     medium
  confidence:   high (5/5 attempts, 8 processes each)
  claim:        check_and_record() is a non-atomic load-modify-store, so N
                concurrent presentations of the same token are ALL accepted.
                Replay protection does not hold under concurrency.
  attacker-capability:
                Ability to launch the application more than once against the
                same ledger, or a single launcher that forks -- i.e. no special
                capability.
  technical-
  explanation:  check_and_record() reads the ledger, tests membership, then
                writes, with no lock and no atomic test-and-set:

                    data = self._prune(self._load(), moment)
                    if identity in data: return False
                    data[identity] = moment
                    self._store(data)
                    return True

                Two processes that read before either writes both see a fresh
                identity and both return True. os.replace() makes each WRITE
                atomic, but the check and the write are not one operation.
  reproduction: 8 processes, barrier-synchronised, one shared ledger path, one
                identical token identity, repeated 5 times:

                  attempt 1: 8/8 ACCEPTED     attempt 4: 8/8 ACCEPTED
                  attempt 2: 8/8 ACCEPTED     attempt 5: 8/8 ACCEPTED
                  attempt 3: 8/8 ACCEPTED
  impact:       Any parallel presentation path defeats the control. The common
                real pattern -- several instances of a packaged tool starting at
                once -- is exactly this shape.
  remediation:  Use an atomic primitive: os.open(path, O_CREAT|O_EXCL) on a
                per-identity file, or flock() around the read-modify-write, or
                append-only entries with O_APPEND and detect duplicates on
                read. Any of these makes the check and the record one
                operation.
  disproof:     Would be disproved if concurrent attempts produced exactly one
                acceptance. 40/40 concurrent attempts were accepted.
  fixed-by:     nobody yet.
  regression-test:
                tests/test_ledger_race_deterministic.py::
                test_concurrent_presentations_accept_exactly_once, marked
                xfail(strict=True).

                The earlier row said this finding could not be tested because a
                race is timing-dependent and a passing test would prove
                scheduler luck. That was half right and is now corrected: relying
                on natural timing is flaky, but the INTERLEAVING can be forced,
                and once forced the test is deterministic.

                The test wraps `_load` and `_store` on the ledger INSTANCE with
                barrier-rendezvous functions: every worker must complete its read
                before any worker may write. That reproduces the exact window
                this finding is about without touching the ledger's logic, so a
                correct implementation (O_EXCL, flock, atomic append) would still
                fail the test only if it were wrong.

                Measured with the barrier in place: all six workers read, then all
                six wrote, and the outcome was
                `[True, True, True, True, True, True]` -- 6/6 acceptances where
                1 is required. Three consecutive runs, identical result, 0.16s
                each; the 20s barrier timeout never fires, which is itself proof
                the interleaving was forced rather than the test silently
                degrading.

                A positive control guards the test against becoming vacuous: an
                `ok_flag` set when the barrier fails to release, asserted before
                the outcome check, so a run that failed to force the interleaving
                is reported as "proves nothing" instead of passing by luck.
```

AI-PROTO-008
```
FINDING AI-PROTO-008
  package:      protocol
  reviewer:     maintainer (self-reported; NOT an independent review)
  received:     2026-11-23
  severity:     medium
  confidence:   high (reproduced)
  claim:        check_rollback() ignores write_mark()'s failure, so on media
                where the mark cannot be persisted, anti-rollback silently
                accepts EVERY protection level and reports a normal result.
  attacker-capability:
                Deployment on read-only media, or ability to make the artefact
                directory unwritable. Also fires for a read-only container
                filesystem, which is a common hardening choice.
  technical-
  explanation:  write_mark() returns False on OSError; check_rollback() calls it
                for its side effect and discards the value:

                    if level > seen or not os.path.exists(path):
                        write_mark(path, key, level, name)
                    return {"level": level, "previous": seen, "mark": path}

                Because the mark never appears, `read_mark` returns 0 on every
                run, so `level < seen` is never true and the caller sees
                previous=0 -- indistinguishable from a genuine first install.
  reproduction: artefact inside a 0555 directory:

                  check_rollback(artefact, 5, KEY) -> {'level': 5, 'previous': 0, ...}
                  check_rollback(artefact, 2, KEY) -> {'level': 2, 'previous': 0, ...}
                  check_rollback(artefact, 0, KEY) -> {'level': 0, 'previous': 0, ...}

                Every level accepted; write_mark returned False throughout.
                Control in a writable directory: level 5 then level 2 is
                correctly REFUSED.
  impact:       §9's anti-rollback control is absent on read-only deployments
                and the caller is told nothing. The module docstring already
                concedes that deleting the mark defeats it; this is weaker than
                that, because no deletion is required and the code does not
                know.
  remediation:  Treat an unarmed mark as a failed check: propagate
                write_mark's False as a RuntimeError (or a distinct
                persistence error) instead of returning a success dict, and
                have the caller decide whether an unarmed mark is acceptable
                for its deployment. Include a `persisted` field in the result
                dict so a caller that chooses to tolerate it can at least log
                it.
  disproof:     Would be disproved if check_rollback raised on write failure or
                reported it in the returned dict. It does neither.
  fixed-by:     nobody yet.
  regression-test:
                tests/test_ai_findings_regressions.py::test_rollback_refuses_when_the_mark_cannot_be_written
                marked xfail(strict=True) with this finding id as the reason:
                it runs every gate run, reports xfailed, and XPASSes into a
                failure the moment the defect is fixed.
```

AI-PROTO-009
```
FINDING AI-PROTO-009
  package:      protocol
  reviewer:     maintainer (self-reported; NOT an independent review)
  received:     2026-11-23
  severity:     medium
  confidence:   high (reproduced end to end)
  claim:        The revocation-list rollback guard is inert at its only
                production call site. licensing.verify() calls check_revoked()
                without previous_issued_at, so the comparison that is supposed
                to refuse a rolled-back list can never fire, and a revoked
                licence can be un-revoked by serving an older signed list.
  attacker-capability:
                Ability to serve an old revocation list to the verifier -- i.e.
                control of the verification environment or of the channel the
                list arrives on. Both are explicitly in scope for this module's
                threat model, which is why it is filed.
  technical-
  explanation:  check_revoked() signature:

                    def check_revoked(payload, revocation, previous_issued_at=0):
                        issued = int(revocation.get("issued_at", 0))
                        if issued < int(previous_issued_at):
                            raise RevocationError("... rolled-back list")

                licensing.verify() call site (licensing.py:364):

                    check_revoked(payload, revocation_list)

                previous_issued_at defaults to 0, so `issued < 0` is never true
                for any non-negative timestamp. The guard exists, is documented
                as the defence, is tested in isolation, and is unreachable from
                the production path.
  reproduction: old list issued_at=1000 with no revocations; new list
                issued_at=3000 revoking LIC-REVOKED:

                  check_revoked(payload, old, previous_issued_at=3000)
                    -> REFUSED  (guard works when given the argument)
                  check_revoked(payload, old)
                    -> ACCEPTED (what verify() actually does)

                End to end: the token is refused under the new list and
                ACCEPTED when the old list is served instead.
  impact:       Revocation is the one mechanism that must survive an attacker
                with an old-but-genuine artefact. As wired, it does not.
  remediation:  Persist the highest issued_at seen (the same way the replay
                ledger persists identities) and pass it in, or move the
                high-water mark into licensing.verify() so the caller cannot
                omit it. A guard the only caller cannot supply is not a
                control; the argument default hides that, so the signature
                should make it required.
  disproof:     Would be disproved if any production caller passed
                previous_issued_at. grep finds exactly one call site, and it
                passes two positional arguments.
  fixed-by:     nobody yet.
  regression-test:
                tests/test_ai_findings_regressions.py::test_revocation_rollback_guard_is_wired
                marked xfail(strict=True) with this finding id as the reason:
                it runs every gate run, reports xfailed, and XPASSes into a
                failure the moment the defect is fixed.
```

---

## Disproved hypotheses (recorded so they are not re-investigated)

```
DISPROVED AI-PROTO-D1
  hypothesis:   The default ledger path /tmp/.nx-licence-seen.json is a fixed
                name in a world-writable directory, so an attacker who plants
                it as a symlink to /dev/null gets silent replay acceptance
                (writes succeed, reads always empty).
  tested:       os.symlink("/dev/null", <ledger path>) then four presentations.
  result:       [True, False, False, False] -- CLOSED.
  why:          _store() writes to a temp file and calls os.replace(tmp, path),
                which REPLACES the symlink itself rather than following it. The
                first write destroys the planted link and normal protection
                resumes. The hypothesis was wrong about the mechanism, and the
                code is stronger here than expected.
  residual:     The world-writable location is still a poor default for other
                reasons (any local user can pre-create a real file and read or
                edit it), but that is a different finding and was not
                demonstrated. Not filed.
```

```
DISPROVED AI-CRYPTO-D2
  hypothesis:   The deterministic nonce_seed path allows keystream reuse in a
                SHIPPED build, because the honey pack's seed derives from the
                real pack and both are in the artefact.
  tested:       two split_sealed() calls under one key and one nonce_seed with
                different plaintexts; then checked what the shipped path feeds
                in.
  result:       Keystream reuse is REAL at the API level (C1^C2 == P1^P2 over
                the plaintext region, confirmed) but does NOT fire in the
                shipped path: the honey seed is sha256(_section_pack_val), and
                build_id is _hp_seed[:16].hex() of that same value, so key and
                nonces are both functions of one per-build input and distinct
                builds get distinct pairs.
  status:       Already filed as MIMOSA-INTAKE-002 (API-level hazard, shipped
                path unaffected). Re-confirmed here; no new row.
```

---

AI-PARSE-010
```
FINDING AI-PARSE-010
  package:      parser (manifest)
  reviewer:     maintainer (self-reported; NOT an independent review)
  received:     2026-11-23
  severity:     medium
  confidence:   high (reproduced; the modern case correctly refuses)
  claim:        The signing-key fingerprint cross-check is skipped entirely
                when the manifest has no top-level signed_key_fingerprint --
                i.e. on every manifest built before that field existed. Such a
                manifest's nested signature.key_fingerprint is outside the
                signed body, so it can be rewritten to name a DIFFERENT key
                while verify_manifest still returns ok: True.
  attacker-capability:
                Ability to write the manifest file (the same capability needed
                to ship any artefact). No private key.
  technical-
  explanation:  sign_manifest() excludes the whole `signature` object from the
                signed body and rebinds the fingerprint at top level instead.
                verify_manifest() then guards the nested copy by comparison:

                    nested      = signature.key_fingerprint
                    signed_copy = manifest["signed_key_fingerprint"]
                    if signed_copy is not None and nested is not None:
                        if nested != signed_copy: refuse

                With `signed_copy` absent the guard is inert, and the nested
                value is unauthenticated data that the verifier nonetheless
                reports. The security property the fix was written for --
                "which artefacts did the compromised key sign?", used by
                INCIDENT_RESPONSE.md §0 -- is therefore answerable only from
                manifests built after the fix.
  reproduction: build a genuine manifest for a real key, remove the top-level
                field, re-sign so it is a VALID legacy manifest, then rewrite
                only signature.key_fingerprint:

                  baseline legacy manifest ok: True
                  --- rewrite nested fingerprint to a different key ---
                  ok: True | reason: hash ok + signature ok
                  nested fingerprint now claims: b999e17e9de27b6a
                  actual signing key fingerprint: 26a3716685fb5f7a

                Control: the same edit on a MODERN manifest is correctly
                refused with "signing-key fingerprint mismatch".
  impact:       Scoped precisely, because overstating this would be the same
                error the register keeps finding: authorisation is NOT broken.
                The artefact hash still matches and the signature still
                verifies against the trusted anchor, so an attacker cannot make
                a forged artefact load. What breaks is ATTRIBUTION: a genuine
                artefact can be made to claim it was signed by a key that never
                touched it, which misdirects incident triage -- the exact
                question the top-level field was added to answer.
  remediation:  Treat an absent top-level field as a refusal for a SIGNED
                manifest, i.e. require signed_key_fingerprint whenever
                `signed` is true, and report "manifest predates key
                fingerprinting; attribution unavailable" instead of silently
                passing. Legacy manifests then still load (hash + signature)
                but are visibly unattributable rather than silently
                misattributable.
  disproof:     Would be disproved if the verifier required the top-level
                field whenever signed is true. It only compares when both
                copies exist.
  fixed-by:     nobody yet.
  regression-test:
                tests/test_ai_findings_regressions.py::test_legacy_manifest_fingerprint_cannot_be_forged
                marked xfail(strict=True) with this finding id as the reason:
                it runs every gate run, reports xfailed, and XPASSes into a
                failure the moment the defect is fixed.
```

---

AI-PARSE-011
```
FINDING AI-PARSE-011
  package:      parser (pack)
  reviewer:     maintainer (self-reported; NOT an independent review)
  received:     2026-11-23
  severity:     low
  confidence:   high (measured); impact deliberately NOT inflated
  claim:        stream_join()'s docstring says it "Raises ValueError on:
                wrong section count, index mismatch, tag failure,
                total-length mismatch, or key_hint mismatch". Several
                malformed-input classes instead raise TypeError, so a caller
                written against the documented contract does not catch them.
  attacker-capability:
                Ability to hand a crafted pack dict to the in-process API.
                No production path does this today (see scope below).
  technical-
  explanation:  The bounds checks coerce with int() into locals
                (_declared_count, _declared_total, _si) but later comparisons
                use the RAW pack fields:

                    if [s["i"] for s in ordered] != list(range(pack["count"])):
                    if len(joined) != pack["total"]:

                and the container accesses assume dict/list shapes:

                    sections = pack["sections"]        # TypeError if pack is a list

                Measured on HEAD:
                  count='3' (numeric string, state recomputed)  -> TypeError
                  stream_join([], KEY)                          -> TypeError
                  stream_join(None, KEY)                        -> TypeError
                  stream_join('x', KEY)                         -> TypeError
                  sections=None                                 -> TypeError
  reproduction: python3 -I, with a pack from pack_json() and each field above
                mutated; see the five measured cases. The coercion bounds at
                the top of stream_join accept '3' for count, then the raw
                comparison at the bottom raises TypeError instead of the
                documented ValueError.
  impact:       LOW, and the reason is stated rather than assumed: no
                production caller parses untrusted packs in-process. The
                emitted loader wraps its body in `except Exception: return
                None`, so it fails closed on all five cases; the fuzz harness
                catches Exception too; and tests/test_parser_fuzz.py
                deliberately asserts `pytest.raises((ValueError, KeyError,
                TypeError))`, so the looser behaviour is known and tolerated.
                The defect is that the DOCSTRING specifies a narrower contract
                than the code implements, which is exactly the class of
                mismatch that misleads a future caller into writing
                `except ValueError` around a call that can raise TypeError.
  remediation:  Either widen the docstring to say "raises ValueError for
                semantic failures and TypeError for structurally invalid
                containers", or normalise at entry: reject a non-dict pack and
                non-str/int field types up front and raise ValueError for all
                of them. The second is preferable because it makes the
                contract enforceable by a caller that only catches ValueError.
  disproof:     Would be disproved if all five cases raised ValueError. They
                do not; four raise TypeError.
  fixed-by:     nobody yet.
  regression-test:
                tests/test_ai_findings_regressions.py::test_stream_join_raises_valuederror_for_every_malformed_class
                marked xfail(strict=True) with this finding id as the reason:
                it runs every gate run, reports xfailed, and XPASSes into a
                failure the moment the defect is fixed.
```

---

# Third assessment round — Binary Security and Supply-Chain scopes

These two scopes were previously recorded as NOT STARTED. Subagent dispatch
became available during this round, so they were delegated to separate agents
against the frozen commit `2bb360d` — the first scopes in this programme that
were genuinely worked by an agent other than the one that wrote the code. That
is a real improvement in independence, and it is still **not** independent human
review: the agents are AI, they read the same repository, and the maintainer
verified each claim before filing.

Verification discipline was applied as before: every finding below was checked
by the maintainer against the code, and one agent claim (that sealing is dead
code in the shipped loader) was confirmed by exhaustive grep rather than
accepted on the agent's word.

## AI-SC-001 — the release-acceptance gate could never pass

```
FINDING AI-SC-001
  package:      supply-chain
  reviewer:     delegated AI agent (supply-chain scope); claim verified by maintainer
  received:     2026-11-23
  severity:     high (in the sense that the strongest automated check was dead)
  confidence:   high (reproduced: NameError with the exact import list)
  claim:        The acceptance blocks in .github/workflows/release.yml and
                ci.yml import base64, hashlib, json, os, secrets, subprocess,
                sys -- and then call re.search() and re.sub(). `re` was never
                imported, so the step raised NameError AFTER the build and the
                release-acceptance gate could never reach a verdict.
  attacker-capability:
                None needed. This is a functional defect, not an attack path.
                Its security consequence is that the strongest automated gate
                was non-functional, and a gate that always crashes is worse
                than no gate: it reads as a green-looking step until someone
                parses the failure.
  technical-
  explanation:  release.yml:59 imported the list without `re`; release.yml:109
                calls re.search (the provenance-key pin check) and :145 calls
                re.sub (stripping the pin from the no-signature copy). The same
                pattern existed in ci.yml:172 with uses at :229 and :258. No
                linter in this repository parses heredocs inside YAML, and the
                surrounding workflow is valid YAML, so nothing caught it.
  reproduction: python3 -I -c "import base64, hashlib, json, os, secrets,
                subprocess, sys; re.search('x','x')"
                -> NameError: name 're' is not defined
  impact:       The acceptance matrix produced no verdict. A regression in the
                trust-anchor path, the manifest checks or the acceptance
                assertions would not have turned any job red.
  remediation:  FIXED in this pass: `import re` added to both blocks with a
                comment naming this finding. A structural regression test was
                added so the whole class is covered.
  disproof:     Would be disproved if either file imported `re`. Neither did.
  fixed-by:     this pass.
  regression-test:
                tests/test_workflow_inline_python.py -- extracts every
                `python3 - <<'PY'` block from every workflow, parses it with
                ast, and asserts every name used as `mod.attr` is imported or
                bound in that same block. 18 tests pass.
                NEGATIVE CONTROLS RUN, so the test is not vacuous: fed the
                original broken block it flags `re`; fed the same block with
                `import re` it reports nothing. A test that could not fail on
                the defect it documents would be worse than no test.
```

## AI-SC-002 — 91 action references are tag-pinned, not SHA-pinned

```
FINDING AI-SC-002
  package:      supply-chain
  reviewer:     delegated AI agent (supply-chain scope); measured by maintainer
  received:     2026-11-23
  severity:     high (builds and signs artefacts)
  confidence:   high (counted from the YAML)
  claim:        Of the 106 third-party action references in .github/workflows,
                91 are pinned to a mutable tag or branch and 15 to a full
                40-character commit SHA. A compromised or force-pushed upstream
                tag executes attacker code inside the workflow that builds and
                signs artefacts.
  attacker-capability:
                Control of an upstream action repository or its release tags --
                the classic action-tampering vector. No access to this
                repository required.
  technical-
  explanation:  Measured across all workflow files:
                  SHA-pinned:        15
                  tag-pinned:        91
                  files with >=1 tag pin: 15
                The repository demonstrably knows the practice -- ci.yml and
                release.yml pin checkout/setup-python/upload/download by SHA --
                but most other workflows use @v4 / @v5 / @nightly. The
                artefact-building jobs are the ones that matter: a tag swap
                there runs attacker code with the job's GITHUB_TOKEN in the
                environment that produces signed deliverables.
  reproduction: python3, iterating .github/workflows/*.yml, regex on `uses:`,
                classify the ref as [0-9a-f]{40} vs anything else. Counts above.
  impact:       Supply-chain compromise of the build. This is precisely the
                scenario build_manifest.py says provenance exists to detect, so
                the provenance system is undermined by the delivery mechanism
                that produces it.
  remediation:  Pin every `uses:` to a full commit SHA (Dependabot's
                `github-actions` ecosystem can do this automatically and bump
                the pins). Prioritise the workflows that build or sign:
                release.yml, ci.yml, security-artifact.yml, shadow-build.yml,
                build.yml.
  disproof:     Would be disproved if the tag-pinned refs were immutable. They
                are not; tags are mutable by design.
  fixed-by:     nobody. Recorded, not fixed -- see the note below on why.
  note:         NOT fixed in this pass, deliberately. Rewriting 91 refs to SHAs
                requires resolving each upstream action's current commit, which
                cannot be done offline and would be unverifiable here; a
                wrong SHA is worse than an honest tag. This is an operator task
                with a mechanical, reviewable diff.
```

## AI-SC-003 — dependency installs in artefact-producing workflows lack hash pinning

```
FINDING AI-SC-003
  package:      supply-chain
  reviewer:     delegated AI agent (supply-chain scope); verified by maintainer
  received:     2026-11-23
  severity:     medium
  confidence:   high
  claim:        Several jobs that produce artefacts install dependencies without
                --require-hashes, and `setuptools`/`wheel` are entirely
                unpinned, so a substituted or compromised wheel is not
                detectable at install time.
  attacker-capability:
                PyPI account compromise, or registry/network interception on the
                affected runner.
  technical-
  explanation:  The tamper-resistant path exists and is used in one place --
                ci.yml:89 installs from requirements.lock with --require-hashes
                (544 `--hash=` lines). But:
                  * shadow-build.yml:30 and security-artifact.yml:74 run
                    `pip install -r requirements.txt` with no --require-hashes;
                  * release.yml:55 and ci.yml:168 run
                    `pip install cython==3.0.12 setuptools wheel` -- the last
                    two entirely unpinned;
                  * requirements.txt:14 keeps a `setuptools>=68.0.0` floating
                    floor.
  reproduction: grep the four workflows for `pip install` and note the absence
                of --require-hashes on the listed lines.
  impact:       A compromised dependency executes inside the job that builds the
                deliverable, before the manifest is signed. The manifest would
                then faithfully record a build produced by attacker-controlled
                code -- the signature attests provenance, not trustworthiness,
                and this finding is about the gap between those two.
  remediation:  Use requirements.lock with --require-hashes in every
                artefact-producing job. For setuptools/wheel, add them to the
                lock (generated with --generate-hashes) rather than installing
                them by name.
  disproof:     Would be disproved if those jobs used the lock. They do not.
  fixed-by:     nobody. Operator task: regenerating the lock and proving every
                job still installs is not something to do blind in a review pass.
```

## AI-BIN-001 — the read-only-after-load sealing API has no production caller

```
FINDING AI-BIN-001
  package:      binary security
  reviewer:     delegated AI agent (binary scope); confirmed by maintainer grep
  received:     2026-11-23
  severity:     low-medium
  confidence:   high (exhaustive grep)
  claim:        section_split.py documents and implements re-protecting decrypted
                section buffers read-only (seal_joined, stream_join_sealed,
                protect_after_load), but the emitted loader never calls any of
                them. The protection exists, is tested, and is not wired to the
                shipped path.
  attacker-capability:
                Same-host memory read or core dump of the running process.
  technical-
  explanation:  A repo-wide grep for the three symbols outside tests/ returns
                only section_split.py itself -- the module docstring, the
                function definitions, and internal cross-references. There is no
                call site in obfuscator/core/pipeline.py or in any emitted
                loader template. The shipped sectioned loader joins and hands the
                buffer to the payload without re-protecting it.
  reproduction: grep -rn 'seal_joined\|stream_join_sealed\|protect_after_load'
                --include=*.py . | grep -v '/tests/'
                -> only section_split.py lines (docstring + definitions).
  impact:       A mitigation that the documentation describes as active is
                inactive. A memory capture during execution sees the joined
                plaintext in ordinary writable memory. This is a defence-in-depth
                gap, not a direct code-execution path.
  remediation:  Either wire the sealing API into the emitted loader's join path
                (the moving-decryption walker already avoids accumulating the
                whole plaintext, which is the stronger property), or remove the
                functions and stop describing the mitigation as present. The
                honest minimum is to state in the docs that the API is available
                but not used by default.
  disproof:     Would be disproved by any non-test call site. Grep finds none.
  fixed-by:     nobody.
```

## AI-BIN-002 — the native self-check is fail-open on unstamped anchors

```
FINDING AI-BIN-002
  package:      binary security
  reviewer:     delegated AI agent (binary scope); verified by maintainer
  received:     2026-11-23
  severity:     medium (claim-vs-measurement)
  confidence:   high
  claim:        The native path's pre-execution self-check is skipped entirely
                when _NX_SELF_CK is all-zero or absent, so an attacker who can
                patch the loader can also disable the check that is supposed to
                catch patching.
  attacker-capability:
                Ability to modify the artefact file before it runs. Such an
                attacker already controls the delivered bytes, which bounds the
                impact -- but the check is advertised as a tamper gate and it is
                not one in that scenario.
  technical-
  explanation:  pipeline.py:3408-3421:
                    _nx_stamped = globals().get("_NX_SELF_CK") not in (None, "", "0"*64)
                    if _nx_late is not None and _nx_stamped:
                        _nx_late()
                The zero-anchor case is deliberate and reasonable for a loader
                used directly by tests or embedders. The defect is that the
                same predicate is the ONLY thing standing between a patched
                artefact and a skipped check: zero-filling the anchor makes the
                check not run, and the surrounding `except` only calls
                _nx_self_fail under the same condition, so nothing reports it.
                docs/SECURITY_FEATURES.md presents §1 as a tamper gate without
                the fail-open dimension.
  reproduction: read pipeline.py:3408-3421; the predicate gating the call and
                the predicate gating the failure report are identical.
  impact:       A shipped artefact whose anchor has been zeroed runs the payload
                with no self-check and no failure. The mitigation is conditional
                on a value inside the file it is protecting.
  remediation:  Distinguish "emitted for tests" from "shipped" by an explicit
                build-time constant rather than by testing the anchor's value;
                or treat an all-zero anchor in a shipped artefact as a failure
                rather than a skip. The documentation must also state the
                fail-open case.
  disproof:     Would be disproved if zeroing the anchor caused a failure. It
                causes a skip.
  fixed-by:     nobody.
```

## AI-RE-001 — an unqualified "cannot decode" contradicts the project's own limits

```
FINDING AI-RE-001
  package:      reverse-engineering
  reviewer:     delegated AI agent (RE scope); verified verbatim by maintainer
  received:     2026-11-23
  severity:     high (it is the only unqualified impossibility claim found)
  confidence:   high (quoted verbatim, and contradicted by this repo's own text)
  claim:        docs/ROADMAP.md:205 asserts: "Even if an attacker dumps the VM
                bytecode, they cannot decode it without the per-build
                permutation key."
  evidence-for: NOTHING in the repository measures adaptation resistance. The
                repo's own research-readiness audit
                (docs/research/research-readiness-audit-2026-10-29.md:55) says
                the VM experiment "does not test whether an attacker can parse
                or adapt" and recommends narrowing the claim to "frozen-map
                decoding fails across these variants".
  contradiction: docs/LIMITATIONS.md:14-16 states the opposite as the governing
                position: "No construction here resists a root-privileged
                analyst who can observe the ...". Two documents, one repo, and
                a reader can pick whichever is convenient.
  impact:       "Cannot" is the strongest word available and it is unsupported.
                An attacker who reads the bytecode and rebuilds a permutation
                from observed behaviour is not doing anything exotic. Overstating
                here is worse than understating, because a reader who believes
                it may skip the mitigation that actually matters.
  remediation:  Replace "cannot decode it without the per-build permutation key"
                with the narrowly-scoped, measured statement: frozen-map
                decoding fails across the variants tested. Reference the
                research-readiness audit rather than contradicting it.
  disproof:     Would be disproved by a measurement in the repo showing
                adaptation resistance. There is none, and the audit that
                examined this area says so explicitly.
  fixed-by:     this pass — the sentence is corrected, see below.
```

## AI-RE-002 — a mitigation table promises more than the disclaimers allow

```
FINDING AI-RE-002
  package:      reverse-engineering
  reviewer:     delegated AI agent (RE scope); verified by maintainer
  received:     2026-11-23
  severity:     medium
  confidence:   high
  claim:        docs/SECURITY_FEATURES.md:25 lists the anti-debugging/
                anti-instrumentation goal as "Hide the code from a root analyst".
  contradiction: LIMITATIONS.md:14-16 says "No construction here resists a
                root-privileged analyst", and THREAT_MODEL.md:65 marks
                root/admin protection "None -- UNVERIFIED".
  impact:       A table row is read as a capability summary. "Hide the code from
                a root analyst" is not a goal the project can meet, and the
                same project says so two files away. This is the framing problem
                the terminology work exists to fix, in a table nobody revisited.
  remediation:  State the goal as detection/disruption of a debugger or tracer,
                which is what the code does, and add that root-level observation
                is explicitly out of scope.
  disproof:     Would be disproved if any construction were tested against a
                root analyst. None is.
  fixed-by:     this pass.
```

## AI-RE-003 — the protection score that drives pass selection is unvalidated

```
FINDING AI-RE-003
  package:      reverse-engineering
  reviewer:     delegated AI agent (RE scope); verified by maintainer
  received:     2026-11-23
  severity:     high (it is on the control path, not just a report)
  confidence:   high
  claim:        scripts/benchmark/ai_eval.py:385 compute_protection_score()
                produces "a weighted overall protection score" (0.0 weak,
                1.0 strong) from static proxies -- entropy, name recovery,
                semantic leakage -- that were never validated against any
                analyst's actual recovery success. That score is consumed by
                obfuscator/adaptive_rewriter.py to SELECT PASSES.
  technical-
  explanation:  A composite of proxies is a reasonable diagnostic, and the
                weights are documented. The defect is the direction of use: a
                number that has never been checked against ground truth is
                driving which transforms get applied. If the proxy is wrong in
                a consistent direction, the adaptive layer optimises the wrong
                objective and every subsequent measurement inherits the bias.
  impact:       Silent, systematic: the tool gets "better" at a metric that may
                not correspond to analyst cost, and no test would fail. This is
                harder to notice than a broken feature because everything keeps
                looking green.
  remediation:  Either (a) validate the score against measured analyst/agent
                recovery on a held-out set and record the correlation, or
                (b) stop letting it drive pass selection and use it as a
                reported diagnostic only. (b) is the honest minimum until (a)
                exists.
  disproof:     Would be disproved by a validation record correlating the score
                with recovery success. None exists in the repo.
  fixed-by:     nobody. This is a design decision, not a typo -- flagged rather
                than changed unilaterally.
```

## AI-RE-004 — "analyst resistance" is one instrument's shortfall

```
FINDING AI-RE-004
  package:      reverse-engineering
  reviewer:     delegated AI agent (RE scope); verified by maintainer
  received:     2026-11-23
  severity:     medium
  confidence:   high
  claim:        obfuscator/bench_layers.py:12 defines
                "resistance = 1 - recall  (how much the analyst FAILED to
                recover)". The layer ranking therefore measures one LLM's recall
                shortfall, not attacker cost.
  technical-
  explanation:  The code is honest about cell counts, and single-instrument
                measurement is legitimate as far as it goes. The naming is what
                overstates: "analyst resistance" reads as a property of the
                artefact when it is a property of one model on one sample. A
                stronger model reorders the layers without the artefacts
                changing.
  impact:       Layer rankings get cited as if they were general. They are not
                transferable, and the docs do not say so at the naming site.
  remediation:  Rename to what it is -- "model recall shortfall" -- and state at
                the definition that it is instrument-specific and not a measure
                of attacker cost.
  disproof:     Would be disproved by a second independent instrument agreeing
                on the ordering. None is recorded.
  fixed-by:     nobody (rename is a docs/API decision).
```

## AI-RE-005 — the cost column attributes decompiler work nobody measured

```
FINDING AI-RE-005
  package:      reverse-engineering
  reviewer:     delegated AI agent (RE scope); verified by maintainer
  received:     2026-11-23
  severity:     low
  confidence:   high
  claim:        docs/TRANSFORMS.md:28 maps the CFG class to "CFG recovery;
                decompilation" under a column describing the "typical attacker
                work it costs". No measurement shows any CFG transform here
                costs a decompiler that work.
  impact:       Low: framing in a reference table, not a headline claim. Filed
                for completeness because the column title asserts a cost that
                was never measured, and a reader building a threat model off the
                table would inherit it.
  remediation:  Either cite the measurement or relabel the column as the
                intended cost, distinct from a measured one.
  disproof:     Would be disproved by a decompiler experiment per transform.
                None in repo.
  fixed-by:     nobody.
```

## Reverse-engineering scope: what IS properly evidenced

Recorded because the negatives matter as much as the findings, and because a
register that lists only problems misrepresents a repository that is unusually
honest about its own limits:

```
EVIDENCED AI-RE-N1
  docs/MAXIMUM_SECURITY.md:783-809 -- the bounded LLM-probe table states the
  method, model, token counts and timeout handling, and concludes explicitly
  that it does NOT support "resists reverse engineering". Correctly scoped.

EVIDENCED AI-RE-N2
  docs/RESULTS.md:44 records the full-tool agent RECOVERING the payload
  (disconfirming confidentiality) alongside the 0/12 name-survival result;
  RESULTS.md:334-337 records benchmark-defect retractions (memoryless attacker,
  k-label confound). Publishing disconfirmation of your own defence is the
  opposite of the failure mode this scope was looking for.

EVIDENCED AI-RE-N3
  docs/security/THREAT_BOUNDARY_LOADER.md:518-552 -- the text-segment encryption
  result comes from a named Ghidra session on a named artefact, and the same
  section discloses that .rodata strings survive. Scoped, with the caveat
  adjacent to the claim.

SCOPE NOTE
  There is NO test in this repository that attempts semantic recovery of a
  produced artefact. tests/test_post_build_attack.py checks identifier and name
  exposure (static_probe), which is not decompilation; pydeobsbench/ contains
  decompilation-adjacent probes that no test drives end to end. Every
  decompilation result quoted in the docs came from a one-off manual session, not
  from CI. That is a coverage gap, not a finding: it is why the claims above are
  unmeasured, and it is the thing to build if these claims are to be made
  honestly in future.
```

## AI-TEST-001 — a tamper test that sometimes tested nothing

```
FINDING AI-TEST-001
  package:      parser (test integrity)
  reviewer:     maintainer, found by a release-gate failure on 4a37962
  received:     2026-11-23
  severity:     medium (a security test that intermittently asserts nothing)
  confidence:   high (measured 16/3000, then 1 in 256 explained)
  claim:        test_the_full_framing_tamper_matrix_is_rejected mutates the
                first byte of a ciphertext as
                    ("FF" if data[0] != "F" else "00") + data[2:]
                When the byte was ALREADY 0xff the mutation wrote back exactly
                the original value, the "tampered" pack verified, and the test
                failed claiming stream_join accepted a flipped ciphertext.
  what actually happened:
                NOT a crypto defect. The pack was never modified, so accepting
                it was correct. The test had a 1-in-256 blind spot in which it
                asserted nothing at all.
  how it surfaced:
                The gate on 4a37962 reported shard 9 rc=1 with
                "1 failed, 25131 passed". The same file passed in isolation and
                passed when the whole shard was re-run -- the signature of a
                nondeterministic test, since split_sealed draws a fresh
                os.urandom nonce per pack.
  reproduction: 3000 seal/mutate/join cycles with the ORIGINAL mutation:
                    {'ValueError': 2984, 'ACCEPTED': 16}
                Capturing the accepted cases showed data[0:2] == 'ff' in every
                one, and the mutation wrote 'FF' -- identical bytes.
                'tag flipped' had the same class of bug: writing "0" or "1" as
                the first hex digit can reproduce the original digit.
  impact:       Two directions, and both matter:
                  1. A tamper case silently stopped testing, so a real
                     regression in that check could pass on the unlucky runs
                     that the CI happened to sample.
                  2. It FAILED about 0.4% of runs with an alarming message
                     ("the tampered pack was ACCEPTED"), which is how a team
                     learns to re-run gates until they are green -- destroying
                     the value of the check entirely.
  remediation:  FIXED. Both mutations now invert a bit of the first byte:
                    "%02x" % (int(data[:2], 16) ^ 0x01)
                which CANNOT reproduce the input. Verified: 5000 trials, 0
                accepted, and an assertion inside the probe that the mutation
                always changes the value. The test file was then run 8
                consecutive times: 24 passed each time.
  disproof:     Would be disproved if the mutation always altered the byte.
                It did not, which is the finding.
  fixed-by:     this pass.
  note:         This is worth filing rather than quietly fixing because the
                lesson generalises: any test that mutates a random artefact by
                ASSIGNING A CONSTANT can accidentally assign the original value.
                The fix pattern is to derive the new value from the old.
```

---

# Fourth round — found by building a real artefact for the AI reverse-engineering benchmark

The benchmark needed a maximum-security build to attack. Building one surfaced a
defect that unit tests could not: **the artefact was produced, shipped, exited 0,
and ran nothing.**

## AI-BUILD-001 — a native build silently executes no payload at all

```
FINDING AI-BUILD-001
  package:      binary security / build integrity
  reviewer:     maintainer, found while constructing the RE benchmark
  received:     2025-11-24
  severity:     high (a shipped artefact that does nothing and reports success)
  confidence:   high (reproduced end to end; root cause identified)
  claim:        A default `pipeline build` of a payload that looks functions up
                through `globals()` produces an artefact whose native module
                raises KeyError during init. The loader catches nothing useful,
                returns None, and the entrypoint exits 0 having run nothing.
                A caller (systemd, CI, a supervisor, a benchmark) cannot
                distinguish this from success.
  attacker-capability:
                None needed -- this is a build defect. Its security relevance is
                that a failed load is indistinguishable from a clean run, which
                is exactly the silent-degradation class this project has fixed
                before in other paths.
  technical-
  explanation:  Three mechanisms compose into the failure:

                1. `build_local_cython` rewrites the main guard so Cython
                   compiles the body eagerly:
                       for _guard in ('if __name__ == "__main__":', ...):
                           source_content = source_content.replace(_guard, "if True:")
                   The comment explains why: a guard that never fires inside an
                   extension module meant "a native build ran the module body
                   only". Making it `if True:` moves `main()` into module init.

                2. The payload's `main()` resolves functions by NAME:
                       fn = globals()[name]
                   The obfuscator renames identifiers. Measured on the produced
                   blob: NONE of the original names survive --
                       fnv1a32/djb2/crc8_atm/luhn_check/levenshtein all absent.
                   So the lookup raises KeyError.

                3. The loader's retry loop catches only ImportError:
                       for _nx_mod_name in (...):
                           try: ... exec_module(module); _nx_ok = True; break
                           except ImportError: continue
                   A KeyError escapes to the outer `except Exception`, which
                   returns None. The entrypoint then exits 0. Nothing prints.
  reproduction:  Build any payload whose `__main__` block resolves names from
                `globals()`, then run the artefact:
                    $ python3 artefact.py ; echo "EXIT=$?"
                    EXIT=0                       # no output at all
                Loading the extracted blob directly shows the real error:
                    KeyError: 'fnv1a32'
                    File "payload.py", line 515, in init payload
                Confirmed the payload itself is fine: the section pack verifies
                (key_hint e03962ebd17a497d matches) and joins to 15873 bytes,
                and the embedded blob export list contains both
                `nx_apply_protections` and `PyInit_payload`.
  impact:       Any payload that dispatches through globals(), getattr on the
                module, or a name-keyed registry silently fails to run in a
                native build -- and the failure is invisible. This is worse than
                a crash: a crash is diagnosable, exit-0-with-no-output is not.
  remediation:  Three changes, in order of importance:
                1. The loader must distinguish "nothing ran" from "ran fine".
                   It already returns True on success and None otherwise, and
                   the entrypoint check is `if __FALSE__ and verdict is None`
                   for fallback builds -- so for a build WITH a fallback the
                   None is not treated as failure at all. A native module that
                   raises during init must be reported on stderr and exit
                   non-zero, or fall back to the section pack (which is present
                   and verifies).
                2. `except ImportError` around exec_module should not exclude
                   the payload's own exceptions. Distinguish "wrong module name
                   in the blob" from "the module ran and raised".
                3. `build_local_cython` should refuse (or warn loudly) when the
                   source contains name-based module lookups that renaming will
                   break, since the `if True:` rewrite promotes them to import
                   time.
  disproof:     Would be disproved if the artefact printed its output or exited
                non-zero. It does neither.
  fixed-by:     FIXED this pass, at the entrypoint. Two changes to the emitted
                loader (obfuscator/core/pipeline.py):

                  1. `_exec_fallback()` now sets `_NX_FALLBACK_RAN = True` at the
                     TOP, before every early return, so "the fallback executed
                     the payload" is distinguishable from "nothing ran".
                  2. The entrypoint gains: if the native verdict is None AND
                     `_NX_FALLBACK_RAN` is unset, write
                     "[FATAL] artefact ran no payload: the native blob failed
                     to load and the Python fallback did not run either"
                     to stderr and exit 79.

                Deliberately NOT gated on `__NX_NATIVE_ONLY_GUARD__`, because
                that placeholder is substituted False for every build that HAS a
                fallback -- i.e. exactly the builds where the silent path
                existed.

                What this does and does not fix, stated precisely: the artefact
                still fails to run the payload when the native module raises
                during init (the retry loop still catches only ImportError and
                the payload's own exception still escapes). What changed is that
                the failure is now OBSERVABLE. Silent degradation is the defect
                that made this dangerous; a non-zero exit with a named reason is
                a diagnosable build failure.

  regression-test:
                tests/test_silent_exit_finding.py -- 4 tests on the emitted
                source: the flag exists and is set before the early returns, the
                "nothing ran" guard is present and not tied to the native-only
                placeholder, and the native-only exit(78) survives.
                NEGATIVE CONTROLS RUN: with the fix stashed, 2 of the 4 FAIL
                (the two that assert the fix); with it applied, 4 pass. A test
                that cannot fail on its own defect would be worse than none.

  verified-end-to-end:
                Rebuilt the exact failing payload (a `globals()` dispatch) with
                the fix in place:
                  BEFORE: printed nothing, EXIT=0
                  AFTER:  "[FATAL] artefact ran no payload: ... (exit 79)"
                          EXIT=79
                A normal build (the benchmark payload) still prints its 19
                vectors and exits 0, so the guard does not fire on a healthy
                artefact.

  note:         The benchmark payload was changed to avoid `globals()` so the
                benchmark could proceed; that works around the symptom and did
                NOT fix the defect. The entrypoint fix above is the actual
                change.
```

---

## Scope coverage — what was worked, by whom

Six scopes were requested. Coverage at the end of the third round:

| Scope | Worked? | By whom |
|---|---|---|
| Crypto | Yes | in-session, by the same session that wrote the code |
| Protocol | Yes | in-session, same |
| Parser | Yes | in-session, same |
| **Binary Security** | **Yes (third round)** | **delegated AI agent, separate from the author, verified by maintainer** |
| **Supply-Chain** | **Yes (third round)** | **delegated AI agent, separate from the author, verified by maintainer** |
| Reverse-Engineering | Not re-run | — |

Two of the six were originally recorded as unstarted. Subagent dispatch became
available during the third round (`provider-not-found` had been returned for
every model before), so both were delegated to agents working against the frozen
commit `2bb360d`. Those two scopes are the first in this programme worked by an
agent other than the one that wrote the code.

**This is still not independent human review**, and the distinction matters
more, not less, now that agents are involved: an AI agent reading a repository
is not a cryptographer with a mandate, a time budget and liability. The agent
claims were also not taken on trust — the maintainer verified each against the
code, and one claim in the binary scope (that the sealing API has no production
caller) was confirmed by exhaustive grep rather than accepted on the agent's
word. One agent claim that could not be substantiated was NOT filed.

The compensating measure throughout is the reproduction discipline: every filed
claim was executed or measured. Two hypotheses died in the attempt and are
recorded as disproved. That is stronger than unreproduced opinion and weaker
than independence, and the terminology section in
`docs/MAXIMUM_SECURITY.md` says exactly that.
