# Adversarial Obfuscator

### A measured investigation into Python software protection

This repository is a research prototype and a measurement programme. It asks a
question that the obfuscation literature largely assumes: **does shipping a
differently obfuscated build to every customer actually make an attacker's work
harder?**

It contains a protection toolchain built to make that question testable, an
attacker and benchmark built to measure it, and a record of what the
measurements can and cannot support. The toolchain is real: it ships an AST
obfuscation ladder, semantic lowering, a packed loader with integrity and
licensing gates, and native backends. The research programme is deliberately
narrow: it measures **function identification** in Python source, using a
specification-derived attacker and a probe counter as its cost unit.

> **Status: research prototype.** `shadow-compiler 2.0.0`. The research
> programme has produced one controlled negative result, one invalidated pilot,
> one no-transfer-resistance experiment, and **thirteen correctness defects** in
> the obfuscator (twelve fixed). It has **not** produced a claim that the
> product resists reverse engineering. Read
> [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) before relying on anything here.

---

## The problem

Python is normally distributed as source, or as bytecode that can be lifted
back to something close to source. That removes the usual binary-protection
story. A vendor's algorithm is readable; a licence check executes on a machine
the attacker controls; and "closed source" is a distribution convention, not a
control.

Obfuscation is the practical response, and the literature has no shortage of
transformations. What it has much less of is **measurement**: how much does a
given transformation cost an attacker, and does that cost survive when the
vendor ships a *different build* to the next customer?

That second question is the deployment justification for per-build diversity —
the claim that analysing one build does not transfer to another. It is widely
assumed and rarely tested. This project tests one narrow version of it, and
builds the tooling needed to test the rest.

---

## The research question and the result

**Question.** Does per-build transform-family diversification raise the cost
for an attacker to identify a function in Python source?

**Result.** Once the number of module-level callables each family inserts is
held constant, the answer on this instrument is **exactly 0.00 difference** —
on all three family pairings, all 17 tasks, and all 51 task/seed cells.

Uncontrolled, the same comparison shows +0.33 probes for A-vs-B and 0.00 for
B-vs-C, which reads as a null. It is not. Family A inserts one fewer
module-level callable than B and C, and the probe counter tracks callable
count. **What looked like a diversity effect was the cost of the callables
diversification happened to insert.**

| Pairing | Uncontrolled | Callable counts matched |
|---|---|---|
| A vs B | +0.33 probes | **+0.00** |
| A vs C | +0.33 | **+0.00** |
| B vs C | 0.00 | **+0.00** |

What *does* move cost is module size: from **2.0 probes at one candidate to 8.6
at four**, monotone in nine of nine tasks and invariant to sibling order on the
task whose permutations were run. A blind-property baseline costs 8.0 at one
candidate and 20.0 at four, so the growth is not merely the size of the search
space.

The honest statement is therefore about the instrument, not the defence: a
specification-derived property set is blind to semantic transformation but
sensitive to structure, and the benchmark conflated the two. We do **not**
claim that diversification fails to raise attacker cost. We claim that this
instrument cannot tell, and we explain why so the next attempt does not repeat
it.

The result is scoped to **11 load-bearing tasks** — seven hand-written, two
independently specified, two prior external. Only the two blind tasks are
independent of this paper's author. See
[`docs/RESULTS.md`](docs/RESULTS.md) for the full result and
[`docs/BENCHMARK.md`](docs/BENCHMARK.md) for the method.

---

## What this repository contains

Two coupled efforts. Confusing them is the most common way to over-read the
project.

| Track | What it is | Evidence status |
|---|---|---|
| **Protection engineering** | `shadow-compiler`: 17-transform AST ladder, semantic lowering, IR/LLVM stages, packed loader, runtime gates, licensing, native backends | Implemented and tested; individual controls evaluated against named tests, **not** against a general attacker |
| **Measurement programme** | `docs/research/` and `scripts/transfer/`: benchmark, attacker, protocols, defect discovery, paper draft | One controlled negative result; one invalidated pilot; one no-transfer-resistance experiment; thirteen defects; a retraction record |

The measurement programme uses the obfuscator as its system under test. It does
**not** evaluate the complete default production build: the experiments use the
source-level research generator, not `scripts/build.py` or the packed loader.
That scope is stated in the paper and is not a detail to gloss over.

---

## What is implemented

Nine layers, independently switchable. "Status" is deliberately conservative:
*Verified* means measured in this repository; *Implemented* means code and
tests exist but it has not been independently evaluated; *Experimental* means
opt-in and partially validated.

| Layer | What it does | Status |
|---|---|---|
| **AST ladder** (`--opt-level 0..5`) | 17 canonical transforms; level 0 disables the ladder, level 4 is the default (14/17) | Implemented; ladder disabled at O0. **Not** byte-identical through the CLI: always-on rename/checksum/string passes still run |
| **Semantic lowering** (`--lowering`) | 20 families / 140 verified operations rewritten to per-build kernel calls | Implemented; Python shim overhead measured at **1.46×–3.84×** |
| **Counter-REA shields** | Decoy call graphs, canary credentials, evidence poison, shadow logic, diagnostic rabbit holes | Implemented; effect on an analyst **not measured** |
| **Deception** | Poisoned imports/APIs/paths, honey functions, traps aimed at automated analysis | Implemented; hypothesis, not a measured defence |
| **Runtime integrity** | Frozen-stdlib snapshot, stdlib function audit, audit-hook plant detector, traceback suppression | Implemented; on by default |
| **Anti-tamper** | Shamir section splitting, rolling keys, attestation, challenge-response, history-bound decryption | Implemented; several opt-in; six mutation flags are metadata-only, `--temporal-keys` is inert and `--crypto-binding` is build-time only |
| **Licensing and binding** | HWID, trial expiry, semantic watermark, signed Ed25519 licence tokens | Implemented; the licence token is the strongest client-side binding |
| **Packaging** | Cython, PyInstaller spec, C SIMD VM, FHE/ORAM backends, cross-compilation, split bootstrap | Implemented or research-only, marked per flag |
| **Verification** | Preservation checks, SMT validation, proof coverage, evidence ledger, artefact gate | Implemented; a variant mismatch fails the build |

The complete flag surface — 260+ options for the source emitter and 69 for the
packed loader — is in [`docs/CLI.md`](docs/CLI.md), generated from the live
parsers and checked in CI.

**Seeds are not keys.** `--seed` and `--randomization-seed` exist to make a
debug build reconstructible; `--build-id` seeds the `--pytoc` lowering kernel;
`--lock-hwid` seeds only the loader's polymorphic map. Key material comes from
`secrets`/`os.urandom`. `--seed` now makes the **source emitter** byte-identical
for the same payload, tool version, and flags; the **packed loader** is still
not reproducible because its keys and packaging draws are random.
`--skip-obfuscate` is the true copy path. See
[`docs/SEED_ARCHITECTURE.md`](docs/SEED_ARCHITECTURE.md).

### What it does not claim

- **Not unbreakable.** Every client-side control is editable by the client's
  owner. The only architectural answer that holds is moving the secret and the
  trust decision to a server.
- **Not a measured defence against a frontier analyst.** No adversary-in-the-loop
  measurement of the full stack exists in this repository.
- **Not reproducible builds.** Two builds of the same payload differ by ~18%;
  comparisons must mask the per-build key.
- **Not a finished research result.** The paper's claim is narrow, and its
  primary limitation — only two independently specified load-bearing tasks — is
  not fixable by re-analysis.

The full list is in [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

---

## How the research works

1. **A corpus.** 17 internal tasks (9 hand-written, 8 from real modules), plus
   five external sources gated for execution. Each task is a target function
   among siblings.
2. **An attacker.** A specification-derived property set: three to five
   executable assertions per task, written from documentation rather than the
   function body, applied **frozen** to every build. It never sees clean source,
   evaluator vectors, labels, or another build.
3. **A cost unit.** Specification-derived probe evaluations — one assertion
   applied to one candidate. CPU seconds are recorded but not used for
   inference; at this scale they are dominated by interpreter startup.
4. **Gates.** Evaluator distinguishability, behavioural equivalence,
   compile/import/run, and singleton identity. A cell where the evaluator
   cannot name a unique target is invalid, not a zero.
5. **A record.** Every claim gets a check that can fail; every check gets a
   stated blind spot; every wrong turn stays next to the claim it corrected.

The identity/conclusion separation matters: the evaluator alone holds the
original function and decides identity; the attacker's property set decides only
its own conclusion. Conflating them produced three rounds of unattributable
numbers.

---

## Research contributions

1. **A controlled negative result with the confound identified.** Transform-family
   diversity added no measurable cost once callable counts were equalised; the
   apparent effect was the callables the families inserted.
2. **A reusable benchmark and gates.** Seventeen tasks, five external sources,
   38 gated artefacts (20 external), and four instruments that run
   deterministically from the repository.
3. **A defect corpus from code the project did not write.** Thirteen defects in
   the obfuscator, ten of which the project's own tests could not have found.
   Ten produce artefacts that compile and then fail; three do not compile.
4. **A methodology record.** Eight withdrawn claims, each kept beside what it
   corrected. Five were the programme's own instrument failing, not the system
   under test.
5. **An engineering testbed.** A protection toolchain broad enough to make the
   measurement question concrete, with its own threat model, evidence taxonomy,
   and failure-mode audit.
6. **A narrower next question.** The frozen-versus-adaptive transfer study is
   specified, with a pre-registered equivalence bound and a project-held-out
   corpus. It is **not yet run**.

The paper draft is [`docs/research/paper-draft.md`](docs/research/paper-draft.md).
The programme index is [`docs/research/README.md`](docs/research/README.md).

---

## Limitations and open questions

The short list:

- **Corpus.** Small, mostly one author, 37–51 lines per task. Not a Python
  corpus in the sense a general claim needs.
- **Independent specification.** Six blind tasks, two load-bearing. This is the
  primary limitation.
- **Probes are not analyst time.** No human has been timed; no
  probe-to-minutes mapping is claimed.
- **Identification is not comprehension.** Nothing here measures whether an
  analyst could explain or repair a recovered function.
- **The full product is not the research path.** The benchmark studies a
  source-level generator, not the packed loader with counter-REA and native
  backends.
- **One open defect.** A module with public functions and no `__all__` can be
  obfuscated into something its own package cannot import. A caller-side scan
  fixes it for callers that supply it.
- **No measurement against a frontier automated analyst.** The counter-REA and
  deception layers are implemented hypotheses.

The open questions, in priority order: Does an adaptive attacker recover what a
frozen one misses? Do the results hold on a project-held-out corpus? Does the
instrument track human effort? Can independent authors reproduce the
specification? See
[`docs/research/research-program-plan-2026-10-29.md`](docs/research/research-program-plan-2026-10-29.md).

---

## Documentation

| Start here | Why |
|---|---|
| [`docs/RESEARCH.md`](docs/RESEARCH.md) | Problem, research questions, threat models, prior work, evidence standard |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Two artefact producers, pipeline stages, runtime, invariants |
| [`docs/TRANSFORMS.md`](docs/TRANSFORMS.md) | What each protection layer actually changes, and what is inert |
| [`docs/SECURITY_FEATURES.md`](docs/SECURITY_FEATURES.md) | Objective-level classification; IP protection vs licensing vs integrity |
| [`docs/MAXIMUM_SECURITY.md`](docs/MAXIMUM_SECURITY.md) | Measured configuration matrix, bounded attack probe, interactions, negative results |
| [`docs/CRYPTO_REVIEW.md`](docs/CRYPTO_REVIEW.md) | Internal crypto review; **not independent** |
| [`docs/SEED_ARCHITECTURE.md`](docs/SEED_ARCHITECTURE.md) | Seeds vs randomisation vs key material; measured determinism |
| [`docs/FLAG_AUDIT.md`](docs/FLAG_AUDIT.md) | Every flag with parser, default, and primary objective |
| [`docs/BENCHMARK.md`](docs/BENCHMARK.md) | Corpus, attacker, cost unit, gates, protocols, validity threats |
| [`docs/RESULTS.md`](docs/RESULTS.md) | Measured results, defect register, retractions, claim status |
| [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) | Scope limits, open questions, what would falsify the claims |
| [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) | Exact commands for every claimed number |
| [`docs/CLI.md`](docs/CLI.md) | Complete generated flag reference for both entry points |
| [`docs/DEVELOPER.md`](docs/DEVELOPER.md) | Prerequisites, layout, lint, tests, extension points |
| [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) | Verified walkthroughs with pasted output |
| [`THREAT_MODEL.md`](THREAT_MODEL.md) | Attacker-by-attacker coverage and evidence taxonomy |
| [`docs/research/`](docs/research/) | The complete research record, round by round |

A full map is in [`docs/README.md`](docs/README.md).

---

## Quick start

### Prerequisites

| Need | Version / note |
|---|---|
| Python | **3.10–3.14** for the builder and payloads; verified on 3.13.5 |
| Quick start | **stdlib only** — no install required |
| Full source pipeline | `cargo`, `g++`, `llc` (checked at startup) |
| Tests / lint | `pip install -r requirements-dev.txt` |

Recommended install for normal use:

```bash
python3 -m pip install -r requirements.txt
```

The dependency lock (`requirements.lock`) is hash-pinned; CI installs it with
`--require-hashes`. If you only want to try the AST/phase-2 stage, skip the install and
use the five `--skip-*` flags below.

### Minimal build (verified)

A minimal build with no external toolchain: AST-level obfuscation. Phase-2 AST
features from `config/default.json` still run; add `--phase2-only none` if you
want the ladder without them.

```bash
echo 'print("hello-nixon")' > /tmp/hello.py

NIXON_LOG_REDIRECT=0 timeout 300 python3 scripts/build.py \
  --payload /tmp/hello.py -o /tmp/qs_hello.py --force-output \
  --skip-irgen --skip-llvmgen --skip-encrypt --skip-relay --skip-extras

NIXON_LOG_REDIRECT=0 timeout 60 python3 build/hello_obfuscated.py
# hello-nixon
```

About a second, and the artefact is ~15 KB from a 21-byte source at the default
`--opt-level 4`. Level 0 disables the 17 ladder transforms but still runs the
pipeline's always-on passes (symbol rename, integrity checksums, string
sealing), so it is **not** a byte-identical copy through the CLI;
`--skip-obfuscate` is the true copy path. The five skips remove IR generation,
LLVM codegen, post-link encryption, the Rust relay, and optional native extras;
they do **not** disable the phase-2 AST features from the default config. Add
`--phase2-only none` for the ladder alone.

### Practical build (packed loader)

The packed loader is the second entry point and the one that can apply
licensing, trial, HWID, watermark and section splitting. This command keeps the
default protections but bounds packaging to 25 layers so it finishes in about a
minute on the representative payload:

```bash
NIXON_LOG_REDIRECT=0 PYTHONPATH=$PWD \
  python3 -m obfuscator.core.pipeline build /tmp/hello.py \
    --skip-cloud --layers 25

python3 /tmp/dist/hello_protected.py
# hello-nixon
```

The packed loader writes **next to the payload**, not to the current directory:
`<dirname(payload)>/dist/<name>_protected.py`. A build of `/tmp/hello.py`
therefore writes `/tmp/dist/hello_protected.py` (verified 2026-11-10).

### Verify the output

1. The file exists: `ls -lh /tmp/dist/hello_protected.py`.
2. It runs: `python3 /tmp/dist/hello_protected.py` prints the payload's output.
3. The loader furniture is present: `nixon_core.so` and
   `Nixon_Security_Root.cer` are in the same `dist/` directory.
4. A licence-bound build refuses without its token (exit 1); a trial-bound
   build reports expiry after the window.

`--opt-level 0` is **not** the copy path; `--skip-obfuscate` is. A build is not
evidence that the artefact works — run it.

Detailed walkthroughs: [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md). Complete
flags: [`docs/CLI.md`](docs/CLI.md). Deployment requirements:
[`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

---

## Maximum security: what is actually verified

Enabling every flag is **not** maximum protection. Six flags write metadata
that no runtime component reads, `--temporal-keys` is inert, `--crypto-binding`
does not decrypt at run time, and the maximum-flags build with the default 100
packaging layers **did not finish in 600 s**. Licensing and watermarking are
access control and leak tracing, not reverse-engineering resistance. One more
measured gap: `--trial` and `--hwid-lock` did **not** reach the standard
packed-loader artefact; the licence token is the binding that fires.

The measured matrix (2,635-byte payload, Linux x86_64, CPython 3.13.5):

| Configuration | Enabled protections | Compatibility | Build time / size | Security assessment |
|---|---|---|---|---|
| **Default (source)** | O4 ladder (14/17) + phase-2 defaults | Runs standalone | ~2 s / ~34 KB | Basic static obfuscation; no loader gates |
| **Balanced (source + lowering)** | O5 (17/17) + 20-family lowering | Runs only with `obfuscator/` on `PYTHONPATH` | ~2 s / ~37 KB; shim 1.46×–3.84× | Stronger static surface; deployment cost |
| **High (loader defaults)** | Full ladder, sections (4), anti-REA balanced, strict detections, integrity gates, 100 layers | Runs; 3.55 MB artefact | 387 s / 3.55 MB | Strongest default posture; all client-side |
| **Maximum practical (verified)** | High + anti-REA **maximum**, 6 sections, watermark, trial 7 d, licence token, **25 layers** | Runs **with token**; exit 1 without | **69–99 s** / **1.46–8.25 MB** | Strongest verified under a ~2-min budget; anti-REA effect unmeasured |

The verified maximum command (token generation included) is in
[`docs/MAXIMUM_SECURITY.md`](docs/MAXIMUM_SECURITY.md). A **bounded attack
probe** exists there too: deterministic probes plus one LLM pass found no
payload identifier or plaintext in the maximum-loader surface, while the O4
source artefact exposed its string-cipher key. That is a floor, not a claim of
resistance. Read [`docs/SECURITY_FEATURES.md`](docs/SECURITY_FEATURES.md) for
the objective-level classification and [`docs/FLAG_AUDIT.md`](docs/FLAG_AUDIT.md)
for every flag.

---

## Reproducing the research

```bash
# The paper's ten tables, printed beside the documents' claims
python3 scripts/transfer/reproduce.py

# 38 artefacts at one index, compile + import + run, 0 failures
python3 scripts/transfer/artefact_gate.py --variants 1 --seeds 4242

# Task validity and external validity
python3 scripts/transfer/evaluate_tasks.py
python3 scripts/transfer/evaluate_external.py

# The product suite (large; read the live count, not a doc)
NIXON_LOG_REDIRECT=0 python3 -m pytest tests/ -q
```

Expected today: **10 of 10 tables match**, **38 artefacts and 0 failures**,
**4,500+ tests**, and **12 of 12 external cells valid**. All four research
commands are deterministic: explicit seeds, no network, repository inputs. The
reproduction script prints values beside claims and leaves comparison to a
human.

---

## Project status and version numbering

| Item | State |
|---|---|
| Product | `shadow-compiler 2.0.0` |
| Research programme | Paper draft complete; core result reproducible; final review verdict **submit with named caveats** |
| Benchmark | 17 internal tasks, 11 load-bearing; 5 external sources; 38 gated artefacts |
| Defects | 13 found, 12 fixed, 1 design-level open |
| Retractions | 8 claims withdrawn, plus the cost-curve endpoint; all retained in the record |
| Adaptive study | Designed, **not run** |
| Independent specification | 2 of 11 load-bearing tasks |
| Seed determinism | **Source emitter: yes** with `--seed` (byte-identical for same flags); **packed loader: no** (random keys/packaging) |
| Strongest verified build | Loader + anti-REA max + 6 sections + licence/trial/watermark + 25 layers; 69–99 s, runs only with its token |
| Analyst-time study | **Not done** |
| Systematic review | **Not done** |

### Which version numbers are which

| Numbering | Meaning |
|---|---|
| **2.0.0** | **this product's** version. One constant, in `obfuscator/version.py`; the CLI reports it and `config/default.json` carries the same value (a test checks they agree). See [`docs/CHANGELOG.md`](docs/CHANGELOG.md). |
| **v1.1 … V10** | the **vendor's** obfuscation-technique generations, tracked in the audit report's version matrix. They are **not releases** of this tool and must not be compared with 2.0.0. |

Research documents are dated records, not releases. `docs/research/README.md`
is the current index; the per-round documents are the evidence trail.

---

## Testing and contributing

```bash
make lint        # ruff + the runtime undefined-global check
make e2e         # every build must produce an artefact that RUNS
make test        # pytest + runtime/relay cargo tests
```

The standing rules are simple and enforced: do not add test skips to make the
suite green; do not claim an option works because it is accepted; do not trust
a check that cannot fail. [`docs/DEVELOPER.md`](docs/DEVELOPER.md) has the
prerequisites, layout, and extension points.

## Security

Report suspected vulnerabilities privately rather than in a public issue.
[`SECURITY.md`](SECURITY.md) states the supported versions, the reporting
process, and the enforceable security invariants. [`THREAT_MODEL.md`](THREAT_MODEL.md)
states what each control is claimed to do and the evidence behind it.

## License

Copyright © 2026 Nixon H. **All rights reserved.** This repository is published
for transparency and review; no licence to use, copy, modify, or redistribute
is granted by its publication. The obfuscation technology exists to protect
software against unauthorised analysis — not to defeat security products, hide
malware, or evade detection. See [`LICENSE`](LICENSE).
