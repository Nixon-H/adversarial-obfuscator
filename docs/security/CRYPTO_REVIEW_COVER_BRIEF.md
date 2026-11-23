# Cover brief — request for independent cryptographic review

**What this is.** A ready-to-send message. The attachment is
`CRYPTO_REVIEW_BUNDLE_STANDALONE.md` (one file, ~13 KB, needs no repository
access). Copy the text below, attach that file, send to a cryptographer.

**Status: NOT SENT.** The maintainer has no mail transport on the build host
(exim4 installed, inactive, unconfigured) and no reviewer address. This file
exists so the remaining step is one paste, not a briefing.

---

## The message

> Subject: Request for independent review — custom section-sealing construction
>
> I maintain a Python code-protection tool. Its payload is shipped as N
> individually sealed sections, and the construction is custom rather than a
> standardised AEAD: SHA-256 in counter mode for the keystream, HMAC-SHA256 for
> the tag, with an authenticated context binding version, index, total, nonce
> and a per-pack identity.
>
> The constraint that produced it is real: the loader runs on customer machines
> where only the Python standard library is guaranteed, so AES-GCM and
> ChaCha20-Poly1305 are not available. Whether that constraint justifies a
> bespoke construction, or whether a small audited native dependency is the
> better answer, is one of the things I am asking you.
>
> I have attached a self-contained specification. It needs no repository access.
> It includes:
>
> - the construction written out completely, with every equation;
> - a worked test vector (§11) with every intermediate value, reproducible with
>   `hashlib` and `hmac` alone — you can check the implementation agrees with
>   the specification in about five minutes without trusting my code;
> - **the seven weaknesses I already know about**, listed deliberately so you
>   do not spend budget rediscovering them;
> - eight specific questions, led by whether MAC-then-encrypt over a bespoke
>   keystream is acceptable here at all.
>
> Two things I want to be explicit about. First, passing my tamper matrix does
> not mean this is secure — it means particular attacks were rejected, and I am
> not claiming more than that. Second, I have already found two exploitable
> defects in this construction myself (a cross-pack section splice, since fixed
> by binding a pack identity; and keystream reuse when a seed repeats under one
> key, which is documented but not yet fixed). Both are in the bundle. I expect
> there are more, which is why I am asking.
>
> If you would rather scope this smaller — just the composition question, or
> just the nonce handling — say so and I will send only what is needed.
>
> Findings can come back in whatever shape is clearest. I have a filing format
> on my side; you do not need to use it.

## What the reviewer gets, and what they do not

They get: the construction, the weaknesses, the questions, a hand-checkable
test vector, and the tamper-matrix results.

They do **not** get: the source tree, the build system, or any claim that the
work has already been reviewed. The bundle states `NOT REVIEWED` in its first
paragraph and asks the reviewer to treat the v3 fix as unreviewed maintainer
design — which it is.

## What to do with a reply

File each finding as a row in `REVIEW_FINDINGS_FILED.md` using the 15-field
format, quoting the reviewer verbatim. The rules that matter:

- a finding graded `accept` needs a `resolution`, and `resolution` means a
  commit plus the test that pins it — or an explicit decision not to change
  anything, with the reason;
- a **disputed** finding stays in the register; deleting it because the
  maintainers disagree is the failure the format exists to prevent;
- out-of-scope findings are recorded as out-of-scope with the `SECURITY.md`
  paragraph that excludes them, not as "the reviewer was wrong".

Until a reply arrives, all three review rows stay open and the packages keep
their `NOT PERFORMED` / `NOT RUN` banners. A test asserts those banners survive.

## If no reviewer is available

The honest fallback is not to fabricate one. It is to record that the review is
outstanding, keep the packages current, and continue the adversarial work that
has already produced three findings — while being clear that self-review is not
what the register asked for and does not substitute for it.
