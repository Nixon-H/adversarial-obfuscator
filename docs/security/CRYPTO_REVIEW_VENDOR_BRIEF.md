# Cryptographic review — vendor engagement brief

**What this is.** The commercial counterpart to `CRYPTO_REVIEW_COVER_BRIEF.md`.
That file holds the message to send; this one holds what to send it to, what to
ask for, and what it will cost in effort.

**Status: NOT ENGAGED.** No vendor has been contacted. The repository owner
must do that — it requires their identity, their organisation's procurement
authority, and a purchase order. See `SECURITY.md` for why no address is
published here, and note that the absence of an address is a statement about
configuration, not about whether reports are welcome.

---

## 1. One verified option, and why only one

The maintainer checked vendor pages directly rather than listing firms from
memory. Result, stated honestly:

| firm | verified | what they say |
|---|---|---|
| **Trail of Bits** | YES — page fetched and read | cryptography practice with PhD cryptographers; explicitly assesses *novel and non-standard designs*, including design reviews before implementation and attempts at "formal proofs or counterexamples" for novel protocols |
| two others attempted | NO — 404 / DNS failure | URLs were guesses. **Not listed**, because a firm named from memory may not offer the service, may no longer exist, or may be the wrong practice area |

That is a one-item shortlist, and it is a weaker deliverable than three verified
options. It is what was actually verified. Anyone extending it should fetch and
read the page first, exactly as was done here.

Trail of Bits is a defensible first approach for this work specifically because
the construction is bespoke: §1 of the bundle says so, and the request is
"is this custom design sound" rather than "is this AES usage correct". A firm
that only audits standard-protocol implementations would not be the right fit,
and their page says explicitly that this is not their only scope.

## 2. What to ask for

Ask for a **cryptographic design assessment** of the construction in
`CRYPTO_REVIEW_BUNDLE_STANDALONE.md`, not a penetration test and not a code
audit of the whole repository. The scope that matters is eight items, and they
are already itemised in the bundle's §9:

1. Is MAC-then-encrypt over a SHA-256 counter-mode keystream acceptable for this
   threat model, or must it become a standardised AEAD?
2. If AEAD: is AES-128-CTR + HMAC-SHA256 the right middle ground, or is vendoring
   a small audited implementation required?
3. Does `ctx_i` bind enough — should section length or a pack identifier be
   added?
4. Are the three published 64-bit truncations (`key_hint`, `salt`, `pack_id`)
   acceptable, and should any be removed or rekeyed?
5. Is the random-nonce-per-build argument sound, or should a counter be
   mandatory?
6. Does the structural digest's position, before the MACs, create a
   distinguishability or denial-of-service issue?
7. Is `hmac.compare_digest` used at every tag comparison? (Measured: four sites.
   Independent confirmation wanted, not acceptance.)
8. Does any error message leak information — the loader distinguishes count
   mismatch, state invalid, integrity failure and length mismatch.

Three findings are already known and should be disclosed up front so the
reviewer does not bill time rediscovering them. They are in
`REVIEW_FINDINGS_FILED.md`:

* **MIMOSA-INTAKE-001** — a cross-pack section splice: two packs under one key
  and one total were interchangeable section-by-section. Fixed in pack format
  v3 by binding a per-pack identity into the MAC context.
* **MIMOSA-INTAKE-002** — keystream reuse when `nonce_seed` repeats under one
  key. Filed OPEN, graded `low` because the shipped call path derives key and
  seed from the same input, so a colliding nonce implies a colliding key.
* **MIMOSA-INTAKE-003** — the review documents described `salt` as unkeyed when
  it is a truncated hash of the encryption key. Documentation corrected; the
  question of whether three published 64-bit truncations are acceptable is left
  to the reviewer.

**The v3 fix itself is unreviewed maintainer design and is the item most in need
of independent opinion.** It answers a maintainer finding, at owner direction,
and nobody independent has looked at it.

## 3. What to send

Two files, both self-contained:

* `CRYPTO_REVIEW_BUNDLE_STANDALONE.md` — ~14 KB. The construction, the seven
  known weaknesses, the eight questions, a hand-checkable test vector (§11), and
  a return channel.
* `CRYPTO_REVIEW_COVER_BRIEF.md` — the message itself, ready to paste.

No repository access is needed, and that is deliberate: a reviewer who must
clone a build system before starting will bill for the setup. §11 exists so they
can verify the implementation matches the specification in about five minutes
using only `hashlib` and `hmac`.

## 4. What the ask costs, in effort not money

Prices are a commercial matter and are not estimated here. What can be stated is
the shape of the work:

* **Scope is one construction**, roughly 250 lines of Python, not a codebase.
* **A worked vector removes discovery time.** The reviewer does not have to
  build anything to start.
* **Known weaknesses are pre-disclosed**, so the first hour is spent on the
  composition question rather than on re-finding the splice.
* **The questions are numbered**, so an answer can be scored against them and a
  "we did not look at that" is visible.

An engagement that returns "here is what we examined and here is what we did
not" is more useful than one that returns a clean bill. The register treats
silence as unmeasured, not as absence of defects.

## 5. What to do with the answer

File each returned finding as a row in `REVIEW_FINDINGS_FILED.md` using the
15-field format, quoting the reviewer verbatim. The rules that matter:

* `accept` requires a `resolution` — a commit plus the test that pins it, or an
  explicit decision not to change anything, with the reason;
* a **disputed** finding stays in the register;
* out-of-scope findings are recorded as out-of-scope with the `SECURITY.md`
  paragraph that excludes them.

Until a reply arrives, the P1 crypto review row stays OPEN and the packages keep
their `NOT PERFORMED` banner. A test asserts the banner survives.

## 6. If no engagement happens

Then the row stays open, and that is the correct outcome. What must not happen
is the row being marked closed because the maintainer wrote more documents about
it. Three findings were self-found and are filed with `reviewed-by: NOBODY` —
that is honest bookkeeping, and it is explicitly not the review the register
asked for.
