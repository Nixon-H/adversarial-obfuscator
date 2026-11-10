# Limitations, Open Questions, and Future Work

**Status:** current. This document is deliberately adversarial to the project's
own claims. If a statement here conflicts with a more optimistic document, this
one is the conservative reading and should be preferred until new evidence
arrives.

Related: [`RESULTS.md`](RESULTS.md), [`BENCHMARK.md`](BENCHMARK.md),
[`research/research-readiness-audit-2026-10-29.md`](research/research-readiness-audit-2026-10-29.md).

---

## 1. Security limitations

### 1.1 Not unbreakable, and not close

No construction here resists a root-privileged analyst who can observe the
plaintext the CPU must execute. Every client-side control — trial expiry, HWID
binding, watermarks, integrity checks, anti-debug — is a speed bump that raises
effort and catches opportunistic tampering. It does not create a trust boundary.

The only architectural answer that holds against a capable adversary is to move
the secret and the trust decision to a server. The repository's licensing design
is explicitly "the client half" of that; it is not a replacement.

### 1.2 The client is the attacker's machine

Any key that the client must use is a key the client's owner can eventually
find. Memory scrubbing, lazy decryption, and section splitting raise the cost of
a memory dump; they do not prevent one. The threat model accepts this.

### 1.3 Build-host trust

The build host is trusted. An attacker who can set the operator's build
arguments can make the artefact contain an arbitrary file. This is inside the
threat model and is not defended against.

### 1.4 Root and local admin

Out of scope by construction. No detector can run above its attacker.

### 1.5 Inert and build-time-only controls

`--temporal-keys` is inert: it produces metadata nothing reads. `--crypto-binding`
is build-time validation only: nothing decrypts at run time. `--randomization-seed`
seeds part of the pipeline but does not make builds byte-reproducible. These are
documented in [`TRANSFORMS.md`](TRANSFORMS.md) §8 so a reader does not trust
them by name.

### 1.6 Only a bounded attack measurement exists

The repository now has a **bounded** probe of the maximum-loader surface
(deterministic string/identifier probes plus one LLM pass) in
[`MAXIMUM_SECURITY.md`](MAXIMUM_SECURITY.md) §7. It is not a study against a
frontier automated reverse-engineering agent: one model, one prompt, no tool
use, no dynamic execution. The research programme measures identification cost
for a specification-derived attacker on small programs. Extrapolating either to
"the product resists LLM-assisted reversing" is unsupported.

---

## 2. Research limitations

These are the paper's own limits (§7) plus the readiness audit's findings.

### 2.1 Corpus

Seventeen internal tasks by one author, plus five external sources gated for
execution. The external sources validate that artefacts run; they do not
provide independent specifications. Six tasks were specified blind, covering
six of twenty-three tasks, and only two of those are load-bearing.

Twelve-plus projects specified independently would be a corpus. Six tasks are a
check.

The tasks are also small: mostly 37–51 lines, 3–4 functions, 4–8 total vectors.
That is a pilot corpus. It cannot support a claim about Python packages at
scale.

### 2.2 Single author

All 38 properties and most specifications are the paper's author's. The blind
specification mitigates this; it does not remove it. Four reviews of the paper
happened, all by the same author — that is not external review.

### 2.3 Probes are not effort

Probe count is a resolution unit. No human has been timed. The study does not
claim a probe-to-minutes mapping. A result in probes says nothing about how long
an analyst would take.

### 2.4 Identification is not comprehension

Nothing here measures whether an analyst could explain, repair, or reuse a
recovered function. Identification is the narrowest interesting outcome.

### 2.5 Three families

Two families were shown equally hard. Unequal families differ for reasons of
strength rather than variation — a confound intrinsic to any comparison that
crosses strengths. The design cannot separate "this family is stronger" from
"this family is more diverse."

### 2.6 The instrument cannot answer the original question as posed

A specification-derived property set is semantic, so it is blind to a
semantics-preserving transform — but it is sensitive to structure, because
families insert different numbers of callables. The benchmark conflated the two.
That is the paper's actual finding, and it is also a limitation: the instrument
cannot measure a pure diversity effect.

### 2.7 The H0–H5 pilot is not evidence

The pilot's arm selection did not rotate pass sets, its arms were confounded by
transform defaults, and its static attack used clean-source knowledge and known
vectors. It is preserved as a record, not cited as a result.

### 2.8 The diversity metrics are not validated

The programme's source-shape metrics (AST feature counts, source n-grams,
"IR similarity") are descriptive proxies. They were not validated against CFG,
bytecode, or attack outcomes. The readiness audit flags the names as
misleading: `S_cfg` measured candidate recovery, not CFG recovery;
`compute_bytecode_similarity` read source bytes, not bytecode.

### 2.9 The synthesis planner is not calibrated

`scripts/synthesis/costs.py` assigns hand-written security gains and overheads.
They are not fitted to measured attack outcomes. The planner cannot support a
claim of empirically optimal protection selection.

### 2.10 The const-split result is narrow

Three builds per arm per program; the endpoint is literal search in CPython
`co_consts`, not algebraic or value recovery. "No transfer resistance" is
scoped to that instrument.

### 2.11 The build spread is not reproducible from the repository

The paper reports eight build sizes and a 17.9% spread, but gives no seed set or
command. The arithmetic is right; the measurement is a reported observation, not
a reproduced table. This was flagged in the final review and remains open.

### 2.12 Novelty is bounded, not established

The screen is eight queries over two sessions, fifteen sources. It supports a
bounded statement. It does not support "first", "to our knowledge", or priority.
OFCI is close on the outcome; CoDiver is close on the framing.

---

## 3. Implementation limitations

| Limitation | Consequence | Status |
|---|---|---|
| **Open defect: cross-module exports** | A module with public functions and no `__all__` can be obfuscated into something its own package cannot import, silently | A caller-side scan (`obfuscator/cross_module.py`) fixes it for callers that supply it; the default path does not |
| **`urllib3` and `requests` un-gated** | The two largest external sources cannot be gated until the export question is settled | Blocked by design, not packaging |
| **Packed-loader builds are not byte-reproducible** | Source emitter with `--seed` is now byte-identical for the same payload/tool/flags; the loader still draws blob/string/section keys and packaging choices from `secrets`, and `--pin-structure` pins structure only | ~3,650 `secrets` draws per loader build. [`SEED_ARCHITECTURE.md`](SEED_ARCHITECTURE.md) §3.1, §5 |
| **Trial/HWID gates did not reach the standard packed-loader artefact** | `--trial 1s` and `--hwid … --hwid-lock` builds still ran past expiry / on the wrong identity; gate symbols absent from the artefact | Measured in [`MAXIMUM_SECURITY.md`](MAXIMUM_SECURITY.md) §6.9; gates are wired into the hybrid-loader path, not the `--skip-cloud` packed-loader path |
| **Six flags are metadata-only** | `--cfg-mutation`, `--class-dispatch`, `--ssa-mutation`, `--state-isa`, `--per-exec-recompile`, `--self-healing` (and the phase-2 variant pool) write JSON that no runtime component reads | Rust modules archived; consumer trace in [`SECURITY_FEATURES.md`](SECURITY_FEATURES.md) |
| **Artefact size is not stable** | Same config, 25 layers: 1.46–8.25 MB across runs; size cannot rank configurations | [`MAXIMUM_SECURITY.md`](MAXIMUM_SECURITY.md) §2.2 |
| **Maximum flags can time out** | The maximum-flags build with 100 layers did not finish in 600 s | [`MAXIMUM_SECURITY.md`](MAXIMUM_SECURITY.md) §6 |
| **Lowered artefacts need the shim** | `--lowering` output requires `obfuscator/lowering_shim.py` on `PYTHONPATH` | Documented; the default build does not |
| **`--pytoc` / `--pyinstaller-spec` are best-effort** | They never fail the build; a missing toolchain silently produces a pure-Python artefact | Documented |
| **Native backends need toolchains** | `cargo`, `g++`, `llc`; a full build is minutes, not seconds | Documented |
| **Platform coverage** | Linux x86_64 is primary; ARM64, Windows, and macOS are partial | [`PLATFORMS.md`](PLATFORMS.md) |
| **Python 3.10–3.14** | Older and newer versions unsupported | `obfuscator/nyser.py`, `py_matrix.py` |
| **Kill primitives can destroy work** | A false positive can delete the operator's artefact | Mitigated by default posture; opt-in strict mode restores destructive behaviour |
| **Temporal-redundancy self-destruct never ran** | `execute_redundant` has no call sites; the "hardware fault" response is dead code in both modes | Recorded in `research/transform-defects-2026-11.md`; either wire it soundly or delete it |
| **Many flags are accepted but not isolated** | 253 of 273 ladder flags were not isolated in the flag sweep | Ongoing; the sweep runner separates PASS/FAIL/CONFLICT/etc. |

---

## 4. Documentation limitations

| Gap | Why it is open |
|---|---|
| Per-round research documents are snapshots | Counts in `HANDOFF.md` and old round reports reflect their round, not `master` |
| Sealed reports are outside the repository | They exist in the author's workspace; not committed |
| The changelog's reproducibility entry is stale | It says `--randomization-seed` is gone; the flag remains but does not achieve reproducibility |
| The paper's build-spread measurement lacks a command | See §2.11 |
| No independent reproduction of the full suite on another machine | The suite is large and host-specific in places; CI covers 3.10–3.14 on Linux |

---

## 5. Open questions

Ordered by what would most change the conclusions:

1. **Does an adaptive attacker recover what a frozen one misses?**
   The next experiment: frozen transfer, adaptive recovery under a fixed budget,
   and cold start, with a pre-registered equivalence bound. This is the
   question the current paper cannot answer.

2. **Do the results hold on a project-held-out corpus?**
   Real packages, split at project level so functions from one project cannot
   leak between calibration and evaluation. The current corpus is too small and
   too self-referential.

3. **Does the instrument track human effort?**
   A timed analyst study with a protocol, not a script. Needed before any claim
   about analyst cost.

4. **Can independent authors write specifications that reproduce the result?**
   Twelve-plus projects, specified blind, by people who have not read the
   paper. This is the only way to remove the single-author limitation.

5. **Do source/bytecode/CFG distances predict attack outcomes?**
   Requires validated metrics, not source-shape proxies, and positive/negative
   controls.

6. **Does the full protection stack behave like the research path?**
   The benchmark studies a source-level research generator, not the packed
   loader with counter-REA, section splitting, and native backends.

7. **Which controls survive a frontier automated analyst?**
   Only the bounded probe in [`MAXIMUM_SECURITY.md`](MAXIMUM_SECURITY.md) §7
   exists. The honest position is that the counter-REA and deception layers are
   implemented hypotheses, not evaluated defences.

---

## 6. What would falsify the current conclusions

Stated so the claims are testable:

| Current claim | What would falsify it |
|---|---|
| The family effect is the callable-count gap | A matched-count experiment on a new corpus showing a non-zero difference |
| Module size raises probe cost | A task where adding a candidate does not add a probe, replicated across tasks |
| The property set has no semantic channel | A semantics-preserving transform that changes probe count at matched callable count |
| The H0–H5 pilot is invalid as evidence | A corrected run with explicit arm indices and an oracle-free attacker reproducing T=1.00 |
| Const-split has no transfer resistance | A cross-arm delta below its matched same-arm control on a new corpus |

A negative result that survives these tests is still a result. The programme's
standing rule is that a claim gets a check, and the check must be able to fail.

---

## 7. What not to do next

- **Do not add another obfuscation layer** before the adaptive experiment is
  run. More layers do not answer the question.
- **Do not claim the entropy/reproducibility work is a security contribution.**
  Deterministic seeds are engineering infrastructure; other obfuscators do it.
- **Do not reinterpret a frozen-template failure as attack resistance.** The
  readiness audit is explicit about this.
- **Do not quote a green suite from an earlier round as current.** Read the live
  count.
- **Do not add test skips to make the suite green.** Fix the claim or withdraw
  it.
