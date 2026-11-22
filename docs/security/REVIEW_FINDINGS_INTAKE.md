# Review findings intake

**Purpose.** When an independent reviewer returns findings against one of the
three commissioning packages, those findings must become register rows in the
same form as every other item in this project: a claim, the evidence for it,
and a measurement. This document is the format, so a returned report is filed
mechanically rather than reconstructed from memory months later.

**Status: no findings have been returned.** No reviewer has been engaged,
because no intake channel is configured — see `SECURITY.md`. This file exists
so that the first returned report is cheap to file correctly, not to suggest
one has arrived.

## Why a format at all

This project has already been burned twice by records that looked like
evidence but were not:

* the acceptance matrix that lived only inside a CI workflow and had never run
  locally;
* `signature.key_fingerprint`, documented as signature-covered while sitting
  outside the signed body, so an attacker could re-attribute an artefact.

Both were plausible-looking records that deferred the actual check. A reviewer
report filed as "reviewer says the construction is weak" would be the third.
The format below forces each finding to name what was tested and what was
observed, so it can be reproduced or disputed line by line.

## The row format

Every returned finding becomes one row with these fields. Empty fields are
**not** optional — an empty `evidence` means the row is a hypothesis, and it
must be recorded as such rather than as a finding.

```
FINDING <id>
  package:     crypto | re-evaluation | mimosa-baseline
  reviewer:    <name or handle>, independent of the maintainers
  received:    <YYYY-MM-DD>
  severity:    critical | high | medium | low | informational
  claim:       one sentence, falsifiable
  evidence:    what the reviewer ran or read; quote their output
  reproducible: yes | no | not-attempted  (+ the command, if yes)
  affects:     file:line, or the construction section (§3.1 etc.)
  maintainer-response:
               accept | dispute | need-more-info | out-of-scope
  resolution:  fix commit | documented limitation | register row deferred
```

`maintainer-response: accept` requires a `resolution`. `dispute` requires the
maintainers to state what they think the reviewer got wrong, with evidence —
a bare "disagree" is not a response.

## Rules that keep this honest

1. **Quote the reviewer verbatim.** Paraphrase loses the distinction between
   "the tag is not bound to the version" and "the tag seems weakly bound".
2. **Never grade a finding as resolved without a measurement.** If the fix is
   a code change, the row names the commit and the test that pins it. If the
   fix is a decision not to change anything, the row says so and says why.
3. **A disputed finding stays in the register.** Deleting it because the
   maintainers disagree is the failure mode this format exists to prevent.
4. **Out-of-scope findings are recorded as out-of-scope, with the reason.**
   `SECURITY.md` already defines the trust boundary (operator trusted,
   artefact holder and build runner untrusted). A path-traversal report
   against an operator-supplied build directory is out of scope *by that
   definition*, and the row says which paragraph excludes it — not that the
   report was wrong.
5. **No finding is downgraded because the reviewer was not a known name.**
   Independence is what the register asked for; credentials are not.

## Where rows go

Into the research log (`docs/research/pydeobsbench-2026-11-18.md`) under a new
`§6x` section named for the package, in the same numbered style as the rest of
that document, plus the register table in whatever pass follows. A finding that
changes code also gets a test, and the row cites it.

## What is deliberately not automated

There is no parser for reviewer output. Reports arrive as prose and differ in
shape; a parser would either reject the ones that matter or force reviewers to
fill a form, which biases what they report. The format above is a filing
template, applied by hand, checked by a second reader where one exists.

## If you are the reviewer reading this

You do not need to use this format. Send what you actually found, in whatever
shape is clearest, and it will be transcribed into these rows by the
maintainer. The format exists to constrain the *maintainers'* response, not to
constrain your report.
