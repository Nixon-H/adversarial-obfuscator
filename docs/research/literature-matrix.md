# Literature Matrix: Python Software Protection Research
## Adversarial-Obfuscator paper programme — compiled 2026-09-28

**Status legend.** `VERIFIED` = confirming evidence fetched 2026-09-28.
`USER-PROVIDED` = from prior analysis paste, not independently re-checked —
verify before citing. `STANDARD` = canonical textbook-level reference.

**Central claim correction (non-negotiable).** Do NOT claim "unbreakable
obfuscation." Barak et al. [1] rule out VBB general obfuscation; Loki [16],
CoBRA [22], MBA-Blast [21], and LLM deobfuscators [27–30] show layered,
virtualized, MBA-based protection falls to automated attacks. The
defensible claim is **measured resilience + diversification + attack
transfer-resistance** for Python. Note the nuance reviewers will expect:
iO [2] rescues *indistinguishability*-style obfuscation in theory, but all
constructions are galaxy-brain impractical — it does not save a practical
"unbreakable" claim, and citing Barak without citing Garg et al. signals
shallow reading. Cite both.

---

## 1. Foundations: impossibility, definitions, metrics

| # | Work | Contribution | Technique / layer | Threat model | Evaluation | Limitation | Novelty gap for Nixon |
|---|------|--------------|-------------------|--------------|------------|------------|----------------------|
| 1 | Barak et al., "On the (Im)possibility of Obfuscating Programs", CRYPTO 2001 / JACM 2012 [VERIFIED] | VBB obfuscation impossible for general programs | Theory (circuits) | PPT adversary with code access | Proof by counterexample family | Rules out VBB only; leaves iO, differing-inputs, heuristic notions open | Cite as the reason we claim resilience, never unbreakability |
| 2 | Garg et al., "Candidate iO and FE for all circuits", FOCS 2013 [VERIFIED] | First iO candidate (multilinear maps) | Theory | PPT | Construction + assumption | Assumption later invalidated; follow-ups (well-founded assumptions, CACM 2023) still impractical | Cite to show theoretical literacy; our work is heuristic/empirical, a different claim class |
| 3 | Collberg–Thomborson–Low, "A Taxonomy of Obfuscating Transformations", Auckland TR 148, 1997 [VERIFIED] | potency / resilience / cost + transformation catalogue (control-flow, data) | Source/binary transforms | Reverse engineer | Definitional | Predates empirical evaluation culture | Adopt vocabulary; extend with diversity + transfer metrics (§5) |
| 4 | Xu et al., "Layered obfuscation: a taxonomy", Cybersecurity (Springer) [VERIFIED] | source/bytecode/assembly taxonomy; layers compensate each other's weaknesses | Multi-layer | Reverse engineer | Taxonomy | No adaptive selection, no transfer measurement | Our planner (repo: `scripts/synthesis/`) is selection-over-layers — cite Xu as the static version of our dynamic claim |
| 5 | Schrittwieser et al., "Protecting software through obfuscation: Can it keep pace…", ACM CSUR [VERIFIED] | Survey: obfuscation vs analysis arms race | Survey | Analyst w/ modern tooling | Literature synthesis | Concludes race favors analysis — frames our contribution as *measuring* the race, not winning it | Cite for "we assume the attacker eventually wins single artifacts; we measure cost + transfer" |
| 6 | IEEE SLR "Measuring Software Obfuscation Quality" (9474335) [VERIFIED] | potency/resilience/cost/stealth/similarity; stealth + real-world empirical evaluation under-studied | Meta | — | 100+ papers | Gap-finding, not a method | Direct warrant for Contribution 4 (empirical benchmark incl. stealth) |
| 7 | SoK: Automated Software Diversity, Oakland 2014 [VERIFIED] | Diversity systematization; obfuscation vs diversification distinguished (Pucella–Schneider framework) | Theory of diversity | Varies | Systematization | Concludes testing-vs-attacks doesn't imply entropy | Cite for diversity≠obfuscation; motivates our transfer metric as the missing measurement |
| 8 | Hosseinzadeh et al. 2018 SLR, diversification+obfuscation (158 cites) [VERIFIED] | Joint review of both literatures | Survey | Malware + RE | 100+ papers | Stops at 2018 (pre-LLM, pre-Loki) | Position our work as the post-2018 update: +LLM adversary, +Python, +transfer |

## 2. Practical obfuscators (what "layered + virtualized" already covers)

| # | Work | Contribution | Layer | Threat model | Evaluation | Limitation | Gap for Nixon |
|---|------|--------------|-------|--------------|------------|------------|---------------|
| 9 | Tigress (Collberg, diversifying C virtualizer) [VERIFIED] | Randomized ISA, 8 dispatch kinds, anti-alias/taint/branch, JIT, arbitrary transform composition | C source→source | Static + dynamic devirtualization | Industrial + academic use | C only; no adaptive per-function planning; no transfer metric | Python analogue + planner + transfer is the gap |
| 10 | OLLVM, Junod et al. 2015 (512 cites) [VERIFIED] | Bogus CF, flattening, instruction substitution at LLVM level | LLVM IR | Reverse engineer | Widely reused | Single layer; well-fingerprinted (stealth paper: LLVM-b vs Tigress-o confusion) | Cite as baseline comparator in evaluation |
| 11 | IOLLVM 2022 (nested-switch flattening) [VERIFIED] | Harder flattening variant | LLVM IR | Pattern-based deobfuscation | Small | Incremental | Shows flattening needs structural novelty — our fusion/dispatch work must differ |
| 12 | Loki, Schloegel et al., USENIX Security 2022 (101 cites) [VERIFIED] | VM handlers hardened vs *automated* attacks (510 handlers, 2-input semantics); open source + reproduced artifacts | Binary | Symbolic/trace-based devirtualizers | vs Triton-led attacks | x86 VM handlers; design-vs-automation framing is the closest prior art to our evaluation | **Must position against Loki explicitly**: Python layer, planner, transfer metric, LLM adversary |
| 13 | PyArmor 9.x (RFT/BCC/JIT, runtime keys, HWID/expiry, restrict mode, enter/exit armor) [VERIFIED] | Commercial Python protection | Python bytecode/native | End-user RE | Commercial deployment | Closed; BCC mechanics already dissected publicly (cyber.wtf); SANS shows memory extraction works | Compare empirically where licensable; our open evaluation harness is itself a contribution |
| 14 | Obfy (AST + AES-256-GCM + native loader) [USER-PROVIDED] | Python bytecode encryption product | Python | Hostile runtime (acknowledged limit) | Vendor docs | Same fundamental limit we state | Verify before citing; compare architecture if accessible |
| 15 | Patchwork (GitHub, polymorphic AST + per-function encrypted blobs + multi-cipher loader) [USER-PROVIDED] | Open-source Python obfuscator close in spirit | Python | RE | None academic | No evaluation, no planner | Closest functional prior — must cite and differentiate (evaluation + planning + transfer) |

## 3. Attack literature (the adversary we must survive on paper)

| # | Work | Contribution | Target | Method | Result | Implication for Nixon |
|---|------|--------------|--------|--------|--------|----------------------|
| 16 | MBA-Blast, Liu et al., USENIX Security 2021 [VERIFIED] | Generic linear-MBA simplification via 1-bit arithmetic reduction; ~10k expressions | Linear MBA | Algebraic | Highest success rate at the time | Linear MBA is dead as protection — our MBA layer must be nonlinear/polynomial or measured as speed-bump only |
| 17 | SiMBA 2022 (Denuvo) [VERIFIED] | All linear MBAs, 0/1-domain restriction, faster | Linear MBA | Algebraic | Subsumes MBA-Blast on linear | Same implication, stronger |
| 18 | CoBRA, Trail of Bits 2026 [VERIFIED] | Full-range MBA (linear + polynomial) via classify–decompose–lift–collapse + Z3 verify | General MBA | Hybrid symbolic | High success across types | MBA horizon: assume any MBA we emit is simplifiable; evaluate accordingly |
| 19 | SSPAM/Arybo 2016, msynth, NeuReduce 2020 [VERIFIED] | Pattern/symbolic/neural MBA simplifiers | MBA | Various | Partial | Defense in depth only |
| 20 | Tofighi-Shirazi et al., ML opaque-predicate detection, SPRO 2019 [VERIFIED] | Hybrid symbolic + ML static opaque-predicate removal | Opaque predicates | ML + symbolic | Generic, automated | Our predicates must be evaluated against ML classifiers, not just DSE |
| 21 | Hegde & Rogova-style heuristic/NDSS 2020 opaque-predicate work [VERIFIED] | F1-scored detection of Tigress predicates (trivial/weak/strong) | Opaque predicates | Heuristics + entropy seeding analysis | Detects Tigress-family predicates | Don't emit Tigress-shaped predicates |
| 22 | CFF deobfuscation via abstract interpretation, IEEE TS 2026 [VERIFIED] | k-switch context-sensitive fragmentation + reassembly | Flattening | Static (AI) | Effective, tool-dependent | Flattening alone is insufficient; our fusion must add non-pattern structure |
| 23 | Anti-DSE opaque predicates, CMC 2025 (hash single-way + path explosion) [VERIFIED] | Predicates resisting solver (one-way functions) and DSE (path blowup) | Opaque predicates | Construction | Resists DSE | Adopt-or-compare: hash-based predicates are the current best practice for this layer |
| 24 | Static detection of Tigress VM structures, arXiv 2601.12916 [VERIFIED-existence] | LLVM-pass identification of dispatch/handlers/regions | VM structure | Static pattern | Existence confirmed; details not yet reviewed | Our dispatch must be evaluated against structural detectors, not just symbolic ones |
| 25 | VMHunt / QSynth / Khaos [USER-PROVIDED via LLM-DAS refs] | Verifiable partial devirtualization; synthesis-based deobfuscation; inter-procedural obfuscation vs diffing | VM/binary | Symbolic/synthesis | Cited as related | Verify before citing; QSynth-style synthesis bounds our VM claims |
| 26 | Koo et al. cautionary tale (code-inference vs in-place randomization) [VERIFIED] | Demonstrated attacks undoing naive randomization | Diversification | Inference attacks | Succeeds vs weak diversity | **Direct warning for our diversification**: randomized-but-inferrable structure (e.g. fixed gadget sets) does not transfer-resist; our transfer metric must catch this |

## 4. LLM adversary (2025–2026, fast-moving — re-verify at submission)

| # | Work | Contribution | Finding relevant to us |
|---|------|--------------|------------------------|
| 27 | LLM4DOBF, Choi et al., IEEE Access 2026 [VERIFIED] | Fine-tune + prompt engineering, generalizable deobfuscation, SacreBLEU eval | Fine-tuned LLMs generalize across nested obfuscation — our evaluation must include a fine-tuned (not just prompted) LLM arm |
| 28 | RECON 2026 agentic-RE keynote [VERIFIED] | Shift: LLM-as-helper → agentic orchestration (tools, patching, iteration) | Evaluate against *agentic* loops with tool access, not single-shot prompting |
| 29 | Four-dimensional LLM assembly-deobfuscation framework, arXiv 2505.19887 [VERIFIED] | Resistance ranking: control flow (low) < flattening (moderate) < substitution/combined (high); universal failure on combined | Combined techniques resist LLMs today — our layered design should reproduce and quantify this on Python |
| 30 | LLM-DAS (ARM), ChatDEOB (WISA 2025), JsDeObsBench 2025 [VERIFIED] | Domain-specific LLM deobfuscators + JS benchmark | No Python-benchmark equivalent found → **Contribution: PyDeObsBench-style harness** |
| 31 | "Can LLMs Deobfuscate Binary Code?" 2026 systematic [VERIFIED via list] | Systematic pseudocode-recovery eval | Methodology template for our LLM arm |

## 5. Adjacent lines (threat model, diversity execution, watermarking, crypto)

| # | Work | Relevance |
|---|------|-----------|
| 32 | Chow et al. white-box AES/DES; Billet–Gilbert–Ech-Chatbi SAC 2004 break; Wyseur/Goubin follow-ups [VERIFIED] | Borrow the *threat model* (attacker observes internals), never claim white-box security; our key-in-S-box designs must be framed as obfuscation, not WBC |
| 33 | Cox et al., N-Variant Systems, USENIX Sec 2006 (secretless diversity, execute-and-compare) [VERIFIED] | Architectural precedent for *executing* variants; differs from ours (we ship one of N; they run N and compare) — cite the fork explicitly |
| 34 | N-Version Obfuscation 2015 (tamper-replication impedance) [VERIFIED] | Nearest "diversity × tamper" prior; ours differs by metric (transfer, not replication) and layer (Python, adaptive) |
| 35 | Collberg watermarking models + dynamic (CT) embedding; tamper-proofing [VERIFIED] | Watermark must survive translation/optimization/obfuscation — our survivability tests (`scripts/proofs/watermark_survivability.py`) should be framed as an instance of this problem |
| 36 | Ceccato et al. human studies (ICPC 2009, ESE 2014 family) [VERIFIED] | Methodology for human-attacker evaluation (Java); no Python equivalent → optional 5th contribution or future work |
| 37 | Banescu et al., resilience vs symbolic execution, ACSAC 2016 Outstanding Paper [VERIFIED] | Characterizing resilience vs automated symbolic attack — direct template for our resilience measurements |
| 38 | Banescu et al., ML resilience prediction, USENIX Security 2017 (278 cites) [VERIFIED] | Predicting attack effort from code features via ML — **direct precedent for our planner**: they predict resilience; we *optimize* protection from predicted resilience. Frame planner as the decision-theoretic dual |
| 39 | RSW96 time-lock puzzles; Mahmoody–Moran–Vadhan ROM [VERIFIED] | Trial/licensing crypto framing; sequential-work vs wall-clock distinction our trial system should state |
| 40 | MTD literature (Jajodia school; MDPI/Casola 2026 surveys) [VERIFIED] | "What to move / how / when" taxonomy — our per-build diversification is software-layer MTD; cite to connect RE-protection to the MTD community (different venue pool) |

## 6. Novelty gaps → repo assets → work items

| Gap | Why it's open (from matrix) | Repo asset today | Work to claim it |
|-----|-----------------------------|------------------|------------------|
| G1. Adaptive protection planning | Banescu'17 predicts resilience; nobody published the closed loop (predict → optimize → emit) for Python | `scripts/synthesis/` (engine/optimizer/costs) — VERIFY it does constrained optimization, not just scoring | Formalize planner: feature extractor → resilience predictor → knapsack under overhead budget; ablate planner-on vs uniform-all |
| G2. Cross-build attack-transfer metric T | SoK'14 notes testing-vs-attacks ≠ entropy; Koo warns inference kills naive diversity; no transfer metric exists | `scripts/diversity/` (generator + metrics) | Implement T harness: attack tuned on build A, applied to build B; report T across transform pairs; show fixed-gadget-set T≈1 (negative control!) |
| G3. Exposure-window metric E | Encrypted-at-rest is standard; nobody measures recoverable-form lifetime | Encrypted assets + loader (verify lazy-decrypt granularity) | Instrument decrypt→execute→wipe regions; report E per asset class; compare lazy vs bulk decrypt |
| G4. Python LLM-adversary benchmark | JsDeObsBench is JS; LLM4DOBF general; no Python harness | `scripts/adversarial_bench/`, `attack_replay/`, redteam | PyDeObsBench: Python corpus × our transforms × {prompted, fine-tuned, agentic} LLM arms; report semantic-recovery rates |
| G5. Python anti-DSE predicates | CMC'25 is C/binary-oriented | Opaque-predicate injector (verify hash-based + path-blowup variants exist) | Implement/verify single-way + path-explosion predicates at Python AST level; evaluate vs z3 + angr |
| G6. Nonlinear MBA posture | Linear MBA dead [16–18] | MBA obfuscator (verify: linear-only or polynomial?) | If linear-only: either extend to polynomial or publish measured speed-bump-only framing with CoBRA-evaluated numbers |
| G7. Watermark×obfuscation survivability | CT theory exists; Python-measured instance missing | `scripts/proofs/watermark_survivability.py` | Measure survival across our own transform pipeline; report per-transform kill rates |

## 7. Falsifiable proposition (paper spine)

> **Adaptive, independently diversified combinations of heterogeneous Python
> protection transformations reduce the transferability of automated
> reverse-engineering attacks (T ≪ 1) while holding runtime overhead under
> budget B and semantic deviation at zero.**

Disproof shape: build the transfer harness FIRST; if T ≈ 1 across our
diversification, the diversification claim dies before writing. Negative
controls required: (a) fixed-gadget diversification must show T ≈ 1
(reproduces Koo's warning — proves the metric works); (b) uniform-all
protection must lose on overhead to the planner at equal resilience.

## 8. Evaluation blueprint (attacker models A0–A6)

- A0 source/package: identifier/CFG/constant recovery rates.
- A1 bytecode: decompile (uncompyle6/pycdc) success, marshal recovery.
- A2 runtime observation: key/asset extraction from memory dumps.
- A3 debugger/instrumentation: trace-based recovery under anti-debug.
- A4 memory extraction: decrypted-asset recovery rate + exposure E.
- A5 hybrid static+dynamic+symbolic (angr/z3): function-boundary + VM recovery.
- A6 LLM (prompted, fine-tuned, agentic-with-tools): semantic recovery
  (SacreBLEU + human-judged equivalence on samples).
- Baselines (no cherry-picking): CPython, .pyc, PyArmor (licensable tiers),
  Nuitka, Cython, ours-planner-off, ours-single-build.
- Metrics: resilience, potency, cost, stealth, similarity (SLR [6]),
  diversity (SoK [7]), transfer T (§7), exposure E (§6-G3).

## 9. Limitations section (pre-written, strengthens the paper)

"No software-only mechanism resists an attacker in full control of the
execution environment indefinitely [1]; linear MBA falls to algebraic
simplifiers [16–18]; VM structure is statically detectable [24]; fine-tuned
LLMs generalize across nested obfuscation [27]; our claims are therefore
bounded: measured cost-imposition and transfer-resistance under attacker
models A0–A6, not impossibility-style guarantees."

## 10. Candidate titles (all retire "unbreakable")

- "NIXON: Adaptive Multi-Layer Software Protection for Python Under Static and Dynamic Reverse Engineering"
- "Transfer-Resistant Diversification: Measuring Cross-Build Attack Generalization in Python Software Protection"
- "Planning Protection: Cost-Bounded Adaptive Obfuscation with Measured Adversarial Transfer"

## 11. Immediate next actions (repo work, in order)

1. Verify `scripts/synthesis/` is a real optimizer (read engine/optimizer/costs; if scoring-only, G1 needs building, not framing).
2. Build the transfer harness (G2) + negative controls — before any writing.
3. Audit MBA layer for linearity (G6) — one afternoon, decides a claim.
4. Check predicate inventory for hash-based/path-explosion variants (G5).
5. Instrument exposure E (G3) — needs loader decrypt granularity check.
6. Draft PyDeObsBench corpus design (G4) reusing `adversarial_bench/`.
7. Run watermark survivability across the pipeline (G7).
8. Freeze results, then write §19-structure paper.

## 12. G2 baseline status (2026-09-28, implemented per frozen spec v1.0.0)

Harness: `scripts/transfer/` (protocol, corpus 6 programs × 3 splits,
builds+semantic gate, static + Ghidra attack arms, measure with T/CIs/
Mann-Whitney/falsification rule, report with freeze hash) +
`tests/test_transfer.py` (13 tests green).

Pilot results (parser, 4+4 builds, static arm, 49 cross-applications):
T=1.00 everywhere, U=72, p=1.0, verdict FAIL-TO-DISTINGUISH (correct).
Structural diversity mean ≈0.1 (auth program) — the "low structural
diversity + high transfer" cell, as the protocol requires be
distinguishable. Exclusion rate high on loop/tuple/dict constructs
(renamer miscompilations — filed separately, NOT worked around: the
gate reports exclusions, corpus untouched).

Open methodological issues for the paper run: (a) S saturates at 1.0
on small arity-distinct programs — need larger programs with
same-arity functions to give weights something to discriminate;
(b) rank-sum needs ≥6 builds/arm for p<0.05 (documented in
measure.py); (c) Ghidra arm unexercised (toolchain-gated, skips
cleanly).
