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

## AI-CRYPTO-004

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
  regression-test-wanted:
                a test that asserts the decoy key is NOT derivable from the
                emitted source. It cannot pass today, which is why it is
                specified rather than written.
```

## AI-CRYPTO-005

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
  fixed-by:     nobody yet.
```

## AI-PROTO-006

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
```

## AI-PROTO-007

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
```

## AI-PROTO-008

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
```

## AI-PROTO-009

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

## AI-PARSE-010

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
```

---

## AI-PARSE-011

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
```

---

## Scopes not worked in this round

Two of the six requested scopes were not started: **Binary Security** (native
loader, memory protections, CFG/CET, ABI) and **Supply-Chain** (provenance,
signing keys, CI, publication). The Reverse-Engineering scope was not re-run
either. Recording them as unstarted rather than implying coverage: a register
that lists four scopes and reads as six is the same failure mode this file
criticises in the documents.

Also recorded plainly: **these findings are not an independent review.** The
requested programme was six independent agents against a frozen snapshot.
Subagent dispatch is unavailable in this environment (the provider returns
`provider-not-found` for every model), so the scopes were worked in-session by
the same assistant that wrote much of the code under review. The compensating
measure is the reproduction discipline above -- every filed claim was executed,
and two hypotheses died in the attempt. That is stronger than unreproduced
opinion and weaker than independence, and the distinction is the whole point of
the terminology change in the next section.
