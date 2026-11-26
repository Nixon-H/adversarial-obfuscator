# Mimosa baseline review package

**Purpose.** This is the evidence bundle for the register's P1 row
*independent Mimosa baseline review*. It hands an independent reviewer the
existing sampling, states what that sampling can and cannot support, and lists
the specific claims that need adjudicating.

**Status of the review itself: NOT PERFORMED.** No independent reviewer has
examined this baseline. Everything below is the maintainers' own triage plus
scanner output, and the register treats it as such. The project's own
`MIMOSA_AUDIT_BASELINE.md` says the same thing in its own words: "This is
still a self-review, not the independent reviewer the register asks for."

Target commit: `bf9bcee`
Baseline document: `docs/security/MIMOSA_AUDIT_BASELINE.md`
Scanner: Mimosa 1.0.4, `node <mimosa>/payload/dist/cli.js audit .`

---

## 1. Why this row exists

The register's wording is precise, and it is the whole justification for
spending a reviewer's time here:

> "Your own sampling is valuable, but it is not independent verification."

The project runs a 900+-finding static scan. Those findings are **not
suppressed**: no rule is disabled and no path is excluded. They are
*classified* by the maintainers into three buckets — and that classification
is a judgement made by the people who wrote the code. That is exactly the
arrangement a reviewer should distrust.

## 2. The four scans, and the numbers

| date | files | high | medium | low | cross-file taint | dep vulns |
|---|---|---|---|---|---|---|
| 2026-11-20 (baseline) | 1,470 | 919 | 8 | 257 | 5 | 0 |
| 2026-11-21 (self-sampling) | 1,482 | 921 | 8 | 259 | — | — |
| 2026-11-22 (fresh, this package) | 1,495 | 916 | 8 | 259 | 5 | 0 |

The high count moved **down 5** between 2026-11-21 and 2026-11-22, and the
cause is known rather than mysterious: `checked_url()` was added to
`obfuscator/core/pipeline.py` and wired into all four outbound request sites
(the register's SSRF/path-hardening item). The scanner still reports those
lines, because it flags the `urlopen` sink regardless of the guard above it —
itself an instance of the general problem in §4.

Raw logs: `/home/nixon/nx-suite/mimosa_audit.log` (2026-11-20) and
`/home/nixon/nx-suite/mimosa_audit_2026-11-22.log` (this package).
These are session artefacts outside the repository; a reviewer needs them
copied alongside this document.

## 3. The classification, restated as a claim to be checked

| class | baseline share | maintainers' claim |
|---|---|---|
| path traversal | 619 of 919 | every hit is an `open()` on a path produced by `confined_path()`, `tempfile.mkstemp()`, or `os.path.realpath()` — 12–56 lines earlier than the scanner's window |
| SSRF | 208 of 919 | every hit is one of the project's own build-time API clients (Cloudflare, Blockscout) or the geofence gate's **hardcoded** service list; none built from untrusted input |
| code injection | remainder | every hit is `exec`/`compile`/`eval` on text the project itself generated — the product is a code generator |

Supporting evidence: `MIMOSA_AUDIT_BASELINE.md` §"Triage method" prints a
backwards variable trace for six sampled sites, each resolving to
`confined_path(...)`, plus individually-read SSRF and injection sites.

## 4. What the maintainers already know is wrong with this method

Listed so the review starts past them rather than rediscovering them.

**4.1 The scanner cannot follow dataflow.** It sees roughly 12 lines. Every
"path traversal" verdict therefore rests on a human trace the scanner did not
perform — and that trace was performed by the author of the containment
function. Not independent of the thing being checked.

**4.2 Rule counts include prose.** The 2026-11-21 self-sampling found
`section_split.py:30` flagged as code injection because a **docstring**
contains the word "exec". At least one high finding is a false positive on a
comment. Nobody has measured how many others are.

**4.3 A FOURTH high class exists that the baseline never mentions.** Found
while assembling this package. The 2026-11-22 scan reports

```
core/transforms.py (67)
  ✗ 高危  命令白名单策略违反  L2507
```

i.e. *command allowlist policy violation* — a class absent from the
baseline's three-class enumeration. Reading the line shows it is also a
**comment** (`#   exec("x = 5") in the enclosing scope ...`), so it is the same
prose false-positive class as 4.2. But the baseline's own reproduction rule
says "a new high-severity class that is not one of the three above is a
regression", and by that rule this scan should have been flagged. It was not,
because the enumeration was written from a sample rather than derived from the
log. §4.2 is therefore not an isolated blemish; it is a systematic gap in how
the classes were counted.

**4.3a Counting the findings by eye also fails, and here is the demonstration.**
The scan's own summary line says **916 高危**. A naive `grep -c 高危` over the
same log returns **917** — because the summary line itself contains the word.
One of the two is right and neither method is trustworthy: the per-file list
and the summary are generated separately, and any count taken by pattern match
can land on either. This is the same failure mode as §4.3 in miniature, and it
is why §6 question 9 asks whether the published counts must be machine-derived
from the structured scan output rather than from its rendered text.

**4.4 The classification is coarse where it matters most.** The SSRF bucket
lumps together three genuinely different things:

* `pipeline.py` — four outbound calls that now pass through `checked_url()`;
* `sources.py` — the geofence gate's hardcoded endpoint list, **emitted into
  the artefact** rather than called by the build (7 hits: L2149, L2782, L2843,
  L2861, L2929, L3150, L3166);
* `licensing.py:420` — an RPC URL taken from the **signed licence payload**,
  HTTPS-enforced, contained by the signature rather than a host allowlist.

Those have different threat models. Calling them one class flatters two.

**4.5 The 2026-11-20 sample sampled its own conclusions.** That pass traced
six sites and generalised. The 2026-11-21 pass ran specifically because of
this, over fresh lines and two previously-unsampled files — but by the same
maintainers, so it narrows the reviewer's work without replacing it.

## 5. The one item the maintainers flag as genuinely open

The baseline names it; this package repeats it rather than burying it:

> The medium-severity `不安全反序列化` (unsafe deserialisation) hit at
> `pipeline.py` `marshal.loads` of bytecode this project compiled moments
> earlier — the one item worth a second look if the threat model ever includes
> an attacker who can write to the build's own scratch directory.

Every other high finding is claimed to require an attacker who already
controls the build host. That is a **triage conclusion, not a proof**, and the
baseline says so in those words.

## 6. Specific questions for the reviewer

1. Is the `confined_path()` trace actually sound? In particular for
   `cfile = dest + "c"`, where `dest` traces to `confined_path` but the sink
   is a *derived* name, and for the `allow_subdirs=True` variant.
2. Are there path-traversal findings that do **not** trace to
   `confined_path()`? Six were sampled; nobody has enumerated all 619.
3. Is the emitted geofence service list (`sources.py`) correctly classified as
   SSRF at all, given it is code inside the artefact rather than a build-host
   request? If not, what is the right class?
4. Is the `licensing.py:420` containment-by-signature argument sound? The
   claim: redirecting the ownership check requires a validly-signed licence
   pointing at an attacker's node, i.e. the publisher's private key.
5. For code injection: is "the product executes its own output" sufficient, or
   are there sites where "own output" could be influenced by the payload's
   **input** rather than its source?
6. How many of the 916 high findings are prose false positives like
   `section_split.py:30` and `transforms.py:2507`? A sample-based estimate is
   enough to say whether the bucket is directionally right or badly inflated.
7. Is the medium `marshal.loads` item reachable under any threat model the
   product actually claims? The maintainers say only if an attacker can write
   the build scratch directory — is that dismissal correct?
8. Does the 5-item cross-file taint set contain anything that contradicts the
   three-class story? The baseline does not discuss it at all.
9. **The class totals were never derived from the log.** §4.3 shows that
   hand-enumeration missed a class present in the scan. Should the reviewer
   require the published per-class counts to be machine-derived from the raw
   log before accepting them?

## 7. What this package does NOT claim

* Not that the scan is clean. It is not; 916 high findings exist and are
  reported, not suppressed.
* Not that the three-class explanation is correct. It is the maintainers'
  reading, offered for adjudication.
* Not that "requires build-host control" is proven. A triage conclusion.
* Not that the scanner is worthless. It found the `marshal.loads` item, and
  the prose false positives are a cheap known limitation — but a tool whose
  verdicts need a 12-line-window caveat cannot be the basis of a safety claim.

## 8. How to reproduce every number

```
node <mimosa>/payload/dist/cli.js audit .
```

Then compare the per-file / per-line list against the logs named in §2. Adopt
the maintainers' rule, sharpened by §4.3: **derive the class totals from the
log rather than from a sample, and treat any class not in the published table
as a regression until it is explained.**

## 9. Why this package exists

The register asks for an independent review of the baseline, not for the
baseline to be better argued. What the maintainers can do is make the review
cheap to start and hard to misdirect: hand over the numbers, the logs, the
method, the known flaws in the method, and a numbered list of the claims that
actually need adjudicating. When findings come back they join this register
alongside every other measured item.
