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

### 1.1 Intake route (verified 2026-11-23)

Their contact page was fetched and read. What it documents:

* a **contact form** on `/contact/` ("Tell us about your hardest security
  problems") — the ordinary route;
* for **sensitive material**, they direct senders to **SendSafely**
  (`https://trailofbits.sendsafely.com/...`) **or PGP**, with a public key at
  `/documents/pubkey.txt`;
* a mailing address, which is not the right channel for this.

**No plain email address is published**, which is worth noting because it means
the intake is a form rather than a mailto — and a form is the correct place for
a first approach that will name an unpatched construction.

**Do not attach the bundle to the first contact form.** The bundle describes a
live construction and three known weaknesses, one still open. Send the
*enquiry* first, and offer the material; let them tell you which channel they
want it through. Sending an unsolicited weakness description over a web form is
disclosing before there is a confidential channel to disclose into.

That is the one operational rule in this brief, and it is the sort of thing a
procurement process does not catch.

### 1.2 Draft enquiry — the message to send through the contact form

This is deliberately short and deliberately carries **no** construction detail.
Its only job is to find out whether they want the brief and over which channel.

> **Subject:** Enquiry — review of a bespoke section-sealing construction
>
> Hello,
>
> I maintain a Python code-protection tool that ships a payload as N
> individually sealed sections. The sealing construction is custom rather than a
> standardised AEAD, and it is now in a release candidate I would like reviewed
> independently before it goes further.
>
> I have a self-contained specification ready — the construction written out,
> a worked test vector that can be checked with `hashlib`/`hmac` alone, the
> weaknesses I already know about, and a numbered set of questions. It needs no
> repository access. I would rather not send it through a web form, because it
> describes a live construction and one still-open issue.
>
> Could you tell me:
>
> 1. whether this is a scope you would take on, and
> 2. which channel you would like the material through — your SendSafely
>    endpoint, or PGP?
>
> Happy to answer scoping questions first if that is easier.
>
> Thank you.

**Do not paste the bundle into this message.** If they reply asking for detail,
that reply is the confidential channel and the bundle goes there.

Three things the draft deliberately omits: the product's name, the number of
known weaknesses, and any hint of what the construction is. Those are not
secrets in a legal sense, but a first contact does not need them, and a shorter
first message is easier for a vendor to triage.

### 1.3 What the form actually requires (inspected 2026-11-23)

The contact form renders inside an iframe and does not appear in a static fetch,
so it was loaded in a browser and read. Fields marked `*` are required:

| field | required | note |
|---|---|---|
| FIRST NAME | yes | |
| LAST NAME | yes | |
| EMAIL | yes | |
| COMPANY NAME | yes | |
| INQUIRY TYPE | yes | dropdown; **"Cryptography (libraries, protocols, ZKPs & ZK EVMs, MPC & threshold crypto, & other cryptography reviews)"** is the correct option |
| WHAT SERVICES ARE YOU INTERESTED IN? | no | checkboxes: Threat Modeling, Training, **Design Review**, Code Assessment, Cryptographic Engineering, Other — `Design Review` matches §2 |
| WHAT CAN TRAIL OF BITS DO FOR YOU? | yes | free text — paste the §1.2 draft here |
| HOW DID YOU HEAR ABOUT TRAIL OF BITS? | no | |
| marketing consent | no | leave unchecked |
| data-processing consent | **yes** | required by their privacy policy |
| reCAPTCHA | — | present; automated submission will very likely be refused |

**This is why the maintainer could not submit it.** Four required fields — first
name, last name, email, company name — are the owner's identity, and the
maintainer does not have them and must not invent them. Filling that form would
mean fabricating a person and impersonating the owner to a third party, and
ticking a data-processing consent agreement in their name. There is no version
of that which is acceptable, and it is a factual blocker rather than a matter of
judgement.

**What the owner needs in hand before sending:** name, email, organisation name,
and agreement to Trail of Bits' privacy policy. Everything else is prepared.

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
