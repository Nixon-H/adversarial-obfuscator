# Research Program Plan: Cross-Build Attack Transfer in Python Obfuscation

**Prepared:** 2026-10-29  
**Purpose:** Turn the repository's current pilot experiments into a defensible, reproducible paper program.  
**Workspace baseline checked:** `98ef6fca8eeaa180bb6f7ed0d2699be8c57d6f97` (`98ef6fc`).  
**Working-tree note:** while this plan was being prepared, the previously uncommitted `obfuscator/core/pipeline.py` change was committed as `98ef6fc` (“One owner for the C core: build it and hash it once”). It is a product-pipeline change, not evidence for the research claims below.

## Executive recommendation

Build one paper around this narrow question:

> **When one Python artifact is reverse-engineered, how much of that work carries over to a separately diversified build of the same program, and how much additional work does a target-aware attacker need?**

The paper should compare three explicitly different conditions: (1) a frozen attack artifact learned on build A and replayed unchanged on build B, (2) an attack allowed to adapt to B under a fixed budget, and (3) a fresh attack on B with no A-derived artifact. Compare per-build heterogeneous transform selection with fixed-transform, seed-only baselines. Score recovered behavior on evaluator-only tests, then report attack work and product costs alongside it.

This is the strongest direction in the repository because it can turn the existing transfer harness, transform families, and negative results into a falsifiable empirical study. It is a **candidate contribution**, not a confirmed novelty claim. Prior work already explicitly studies reuse of reverse-engineering knowledge across diversified virtualized code. A plausible narrower gap is a rigorously controlled, project-held-out Python source study that separates frozen reuse from adaptive reanalysis and quantifies both recovery and cost. A documented systematic review must verify that gap before the paper says “first” or “to our knowledge.”

The current evidence is **pilot-grade**. It is not ready for a paper submission or a claim that this obfuscator resists reverse engineering. The next step is not another protection feature: it is to repair and freeze the experimental protocol, define a credible attacker, and run a small calibration pilot before any confirmatory measurements.

## Repository snapshot and evidence boundary

The earlier [research-readiness audit](research-readiness-audit-2026-10-29.md) is recorded at `d42bed4`; this plan rechecked the central research files in the current checkout. The research generator and transfer runner remain separate from the two product build paths. In particular, `scripts/transfer/experiment.py` and `scripts/diversity/generator.py` produce transformed Python source; they do not evaluate the complete `scripts/build.py` or hybrid loader product build. A paper based on these experiments must say it evaluates this source-level research path.

There is a material revision mismatch to resolve before treating the pasted status as the repository's current implementation. The current workspace is at `98ef6fc`, not the pasted `0118936`. `_BuildEntropy` is absent here. The checked-in `docs/EMITTER_PIPELINE.md` says full build pinning was removed after incomplete determinism and a pack/runtime key mismatch. The earlier audit also reports that the H0-H5 experiment runner selects a pass set using variant ID, while each build invocation asks the generator for one variant and thereby reuses variant ID zero. Confirm the intended commit/worktree and reconcile the report, but do not count the pasted entropy work or 24-site result as current code evidence until the exact commit is available and reviewed.

Other current research-path facts that drive this plan:

| Current observation | Research consequence |
|---|---|
| The H0-H5 pass-set selection issue can leave the intended heterogeneous arms using only their first pass set. | Regenerate all confirmatory artifacts with an explicit build index and record the actual resolved options for every build. Do not relabel old outputs as corrected results. |
| Transform defaults are not uniformly isolated across arms. | Explicitly set every transformation option in each arm; include a machine-readable manifest of both enabled options and transformations that actually fired. |
| The current static attack uses clean-source information and supplied vectors during development/application. | It is a known-source/oracle-assisted matcher, not the primary general attacker. Replace it for the primary experiment or give it a separate, explicit oracle track. |
| Current `S_cfg` is function-candidate recovery with finite I/O confirmation, not CFG recovery. | Name the outcome for what it measures. Keep AST/CFG/bytecode labels only for measurements that actually build those representations. |
| Current diversity helpers count AST constructs, compare source-file byte n-grams, or summarize AST features under names implying CFG/bytecode/IR. | Replace or relabel them. Treat structural distances as descriptive; do not infer security from distance alone. |
| Existing analyses reuse builds across many ordered pairs; self-pairs are fixed at 1.0. | Model project/function/build clustering. Do not treat pair cells as independent samples or include self-pairs in cross-build inference. |
| VM results cover one eligible function/program and extract a visible target map. | Keep this as a secondary case study unless eligibility and a genuine adaptive devirtualization attack are established across the corpus. A frozen-map miss is not evidence that the target map cannot be recovered. |
| The planner uses hand-written security-gain estimates. | It cannot support a claim of empirically optimal or evidence-calibrated protection selection yet. Keep planner claims out of this paper. |

The repository contains far more than the research harness. The prior audit inventoried 1,567 tracked files and traced the live product and experiment paths; it did **not** literally read every line of every generated fixture and archived artifact. This plan uses that audit plus targeted reinspection of the experiment, generator, arms, metrics, and pipeline notes. Its claims are about those inspected paths and saved results, not a claim of line-by-line review of the entire tree.

## Proposed paper

### Working title

**Beyond Output Diversity: Measuring Frozen and Adaptive Attack Transfer Across Obfuscated Python Builds**

Alternative if the results are mostly negative: **What Transfers Across Diversified Python Builds? A Reproducible Study of Attack Reuse and Adaptation Cost**.

### Proposed contribution

The paper is an empirical measurement and benchmark contribution, not a claim of a cryptographic guarantee or a new general-purpose virtual machine. Its contribution would be:

1. A precise, reusable protocol for measuring how a concrete analysis artifact learned on one protected build transfers to another build of the same program.
2. A separation between frozen transfer, target-adaptive recovery, and cold-start recovery under equal attacker budgets.
3. A project-held-out Python source benchmark with behavior-based scoring, transform-firing evidence, and raw build/attack artifacts sufficient to reproduce the result.
4. A measured comparison between seed-only diversification and balanced per-build transform-family selection, including correctness, attack effort, and runtime/size/build cost.
5. Evidence about when source-shape distances do and do not track actual attack outcomes, reported as an empirical result rather than assumed from a composite score.

The contribution is valuable if it is a careful null or negative result. If adaptive analysis cheaply catches up, the honest finding is that the current diversity strategy does not buy much attacker effort under the tested conditions. The paper must not convert failure of a stale template into a claim of attack resistance.

### What the paper is not

- Not “unbreakable” or “secure obfuscation.” Practical obfuscation is evaluated against named, bounded attacks and budgets.
- Not the first work on attack knowledge transfer, randomized VM mappings, software diversity, Python obfuscation, obfuscation benchmarks, attacker-effort measurement, or diversity metrics.
- Not a result about the entire product unless the production build path and its complete distributed artifact are separately evaluated.
- Not a paper about deterministic entropy on its own. A deterministic seed is experimental infrastructure, not a security result.
- Not an empirical validation of the synthesis planner until its predicted gains are fitted and validated against held-out attack outcomes.

## Literature and novelty assessment

The literature screen conducted for this plan searched publisher and primary proceedings pages, arXiv-indexed records, author/institutional PDFs, and project/benchmark pages, and followed reference/citation trails from the closest VM-diversity and evaluation papers. It was a targeted screen, not a PRISMA-style systematic review: no complete ACM/Scopus/Web of Science exports, full forward/backward citation census, or double-screened exclusion log was produced. Connected Elicit/Sider scholarly-index calls required reauthentication, so the screen relied on direct public scholarly pages and web-indexed primary sources. This is enough to reject broad “nobody did it” claims, not enough to prove priority for a narrow gap.

### Prior work that constrains the claim

| Line of work | What it establishes | Positioning implication |
|---|---|---|
| DCVP and CoDiver | DCVP (2018) partitions virtualized code and randomizes opcode/handler mappings to impede migration of analysis knowledge. CoDiver (2019) explicitly targets “invalidating analysis knowledge” through partition diversity. | Do not claim cross-program/build transfer resistance or randomized opcode mappings as a new concept. Compare the present work's measurement protocol, language/artifact level, attacker conditions, and adaptive-cost endpoint. |
| DSVMP and DynOpVM | Dynamic bytecode scheduling and dynamic opcode mappings already address cumulative attacks and mapping reuse across runs/regions. | Treat the current VM dispatcher as a treatment, not a standalone novelty claim. A real adaptive mapping-extraction attack is mandatory for any VM security conclusion. |
| N-Version Obfuscation and software renewability/diversification | Program diversity has been used to impede replication of tampering and reduce the usefulness of prior attacks across variants or time. | Distinguish semantic recovery from tamper replication and code-reuse portability; state exactly which attacker outcome is measured. |
| Chosen-instruction VM attacks, Syntia, Loki, and the VM deobfuscation SoK | Attackers can learn VM semantics from chosen inputs, symbolic execution, traces, taint, synthesis, or target-specific analysis. Stronger attacks are not represented by a frozen map alone. | Include target adaptation and an adequate attack baseline. State any chosen-input, dynamic, or oracle access explicitly. |
| DEBRA and other deobfuscation benchmarks | Large, real-program benchmarks and systematic reevaluation of deobfuscators already exist. DEBRA reports 1,917 artifacts from selected functions in 15 programs. | Do not claim “first real-world deobfuscation benchmark.” Explain why same-source, cross-build pairing and the three attacker policies answer a different question. |
| Python obfuscation studies | Python-specific work already studies transformation quality, semantic preservation, runtime/size costs, and LLM-generated transformations. A 2025 benchmark compares Python protection/packaging tools; EASE 2025 studies LLM-driven Python transformations; a 2026 Springer paper studies class-based Python obfuscation with multi-objective search. | Do not claim “first Python obfuscation study/benchmark.” The candidate gap is attack-artifact transfer across independently generated builds, with adaptation cost, under a precise threat model. |
| Recent LLM deobfuscation benchmarks | JsDeObsBench and 2026 binary-deobfuscation benchmarks make generic LLM benchmark novelty untenable; recent work evaluates function-name recovery and code comprehension as well. | If an LLM is included, it is one attack family, not the paper's novelty. Pin model, checkpoint, prompt, token budget, tool access, and training contamination limitations. |
| Evaluation-methodology surveys and human/automated attack studies | Reviews of 571 protection papers and prior resilience prediction, symbolic-execution, human-effort, and metric studies show evaluation and measurement are established research topics. | A new metric or “complexity predicts difficulty” result needs rigorous comparison and validated outcomes; the methodology must itself address validity, clustering, coverage, and reproducibility. |

### Novelty statement allowed after systematic review

If a later documented search finds no direct match, use wording like:

> “Prior work has studied knowledge reuse in diversified virtualized/native software and has benchmarked deobfuscation methods. We study a narrower setting: transfer of explicit attack artifacts between independently generated builds of the same Python source program, while separating frozen replay, target-aware adaptation, and cold-start recovery under matched budgets.”

Only after a systematic review can this be strengthened to “we found no prior study that…” with the search date, databases, queries, screening criteria, and closest excluded work attached. Do not use “nobody has done this” in the abstract, title, or press copy.

## Research questions and preregistered hypotheses

### Research questions

- **RQ1 — Frozen reuse:** How does attack success change when an artifact learned on build A is applied unchanged to a separately seeded build B?
- **RQ2 — Adaptation:** At the same time/compute/query budget, how much recovery does target-aware adaptation restore, and how much work is saved relative to starting from scratch on B?
- **RQ3 — Heterogeneity:** Does choosing among multiple transform families across builds reduce frozen reuse more than changing the seed while keeping one transform family fixed?
- **RQ4 — Cost and correctness:** What are the behavioral-preservation rate, transform coverage, build-time, artifact-size, startup, and steady-state costs of each configuration?
- **RQ5 — Proxy validity:** Do correctly computed AST, bytecode, and CFG distances predict frozen recovery or adaptation effort after controlling for program and attack family?

### Hypotheses to lock before the confirmatory run

- **H1:** At a fixed attacker budget, a balanced mixed-family release regime lowers frozen-transfer success relative to the matched fixed-family seed-only regime.
- **H2:** Target-adaptive analysis recovers a substantial part of any frozen-transfer loss; its recovery and extra cost are both measured. This is not assumed to be true.
- **H3:** Output/structure distance alone is not a sufficient security proxy; its association with task recovery is measured and may be null.
- **H4:** Any observed security-relevant reduction is considered useful only with behavior-preservation and overhead results reported alongside it.

Do not turn these hypotheses into desired outcomes. The preregistration must say that null, reversed, or low-coverage outcomes are reportable and that the claim will be limited to the actual attacks and budget tested.

## Estimands: measure transfer without a misleading single score

For a held-out target function (f), source build (A_i), target build (B_j), attack family (a), and fixed budget (b), define:

- (R_F(i \rightarrow j, a, b)): behavior-recovery score when the attack artifact learned on (A_i) is replayed unchanged on (B_j).
- (R_A(j, a, b)): score when the same attack family may adapt to (B_j) under budget (b), with the artifact from (A_i) available.
- (R_C(j, a, b)): score when the attack starts from scratch on (B_j) under the same budget.
- **Adaptation gap:** (G = R_A - R_F), compared between the mixed-family and fixed-family regimes. This is the primary success-at-equal-budget contrast.
- **Reuse benefit:** (C_C - C_A), where (C_C) and (C_A) are measured resources to reach the pre-registered recovery threshold from cold-start and A-assisted adaptation. This indicates how much previous work saves, not just how badly a frozen artifact fares.
- **Frozen transfer:** report (R_F) as an absolute rate alongside same-build and unprotected positive controls. Any ratio is secondary, requires a preregistered adequacy floor on its denominator, and is never reported without absolute values.

The main treatment contrast is the mixed-family adaptation gap minus the weighted average gap for fixed families A, B, and C. Use an equal weighting fixed before data collection. Include the directed build-pair structure in the model; do not average all pairs into a fictitious large independent sample. Exclude self-pairs from cross-build inference; retain them only as a same-build ceiling/positive control.

## Threat model and attack contract

The primary study should evaluate **Python source artifacts** because that is what the current H0-H5 research path emits. Do not pool `.py` source, `.pyc`, PyArmor-protected modules, and frozen executables into one experiment: they expose different artifact surfaces and require different attacker tools.

### Attacker sees and can do

- Receives one emitted protected Python source artifact, can inspect and execute it in a sandbox, and knows the Python minor version and the task definition.
- For frozen transfer, receives build A's explicit analysis bundle (e.g. recovered rewrite rules, mappings, or model/prompt state) and can run it on B, but cannot revise the recipe or its learned parameters.
- For adaptive transfer, can revise that bundle after seeing B within the same locked wall-clock/CPU/query budget as the cold-start attacker.
- Produces a standalone recovered function/module. The evaluator runs it in an isolated process on hidden inputs; it may not import, call, or delegate to the protected target at scoring time.

### Attacker does not receive in the primary artifact-only track

- Clean target source, evaluator ground truth, source-to-output mapping, hidden test vectors, expected outputs, transform seed/config, or labels that identify the correct answer.
- Network access, unless a separate network-enabled attack is preregistered and all requests are archived.
- Runtime secrets, signing keys, or production credentials. Research inputs must contain no real secrets.

If a public target's exact clean source can be fetched from a repository or pretrained model, label that exposure. The primary artifact-only evaluation should use a sequestered holdout or programs not retrievable during the run, with the original source and tests released after evaluation. A separate **known-source/prior-version** track may be useful, but must not be merged with artifact-only results. It must specify exactly which earlier version/source the attacker knows and which target release is protected.

### Attack families

Use at least two materially different attack families, selected and calibrated before confirmatory data:

1. **Static source/AST recovery.** Normalize syntax; recognize/remedy the transformations actually fired; simplify constants and control flow; extract string tables, key-independent recipes, or VM maps where applicable. Its immutable artifact is the exact code, rules, and learned configuration. This is not the current `StaticRecoveryAttack` unchanged, because that implementation uses clean-source features and evaluator vectors.
2. **Execution-assisted recovery.** Use controlled tracing, runtime observation, differential inputs from an attacker-available budget, and/or symbolic reasoning to recover a standalone implementation. Log every query and analysis step. For VM-specific results, include target-specific map extraction/devirtualization rather than merely applying an old map.
3. **Optional LLM-assisted track.** Include only if local weights/checkpoint and inference stack can be frozen. Record exact model/checkpoint hash, prompt, decoding parameters, context/token limit, tools, seed, and any code execution. Use it as a secondary attack family; do not make the core paper depend on a hosted model that silently changes.

For each attack, document calibration and adequacy. On pilot-only projects, require the unprotected and same-build controls to reach a pre-agreed minimum recovery rate (a candidate threshold is 80%, to be locked after the pilot). If a strong attack cannot solve the control tasks, its failure on protected targets cannot support a resilience claim.

## Experimental design

### Population and project split

1. Build a pilot set of **10 projects** used only to validate the protocol, estimate runtime/variance, select tasks, calibrate attacks, and run the power simulation. Exclude them from confirmatory results.
2. Use at least **30 independent confirmatory repositories**, stratified across numerical algorithms, parsing/text processing, stateful/data handling, and application logic. Increase this number if the preregistered simulation requires it; do not lower it after looking at confirmatory results.
3. Select at least five behaviorally testable target functions per repository before obfuscation. Record size, dependency, statefulness, and transformation eligibility. Split and resample by repository, not by random functions from the same project.
4. Pin upstream commit hashes, licenses, test provenance, Python version, dependencies, and source hashes. Preserve a smaller existing six-program corpus as a pilot/sensitivity set only.
5. Use 12 independent build seeds per treatment/project as a starting design. Confirm the number and the number of build-pair replays by power/cost simulation. If a full directed matrix is too costly, preregister a balanced random-pair sample and its inclusion probabilities before running; never silently select pairs after observing outcomes.

The exact sample count is not a magic number. Use pilot variance to simulate power for the primary interaction, targeting at least 90% power for a practically relevant effect that the authors define before the confirmatory run. The project is the principal generalization unit; thousands of functions or build-pair cells do not substitute for independent projects.

### Arms

After confirming each operator is real, enabled, and fires on eligible inputs, use a small factorial-like design:

| Arm | Definition | Purpose |
|---|---|---|
| U | Original input; no research transformation | Attack success and cost baseline. |
| A | One explicit fixed pass family, independently seeded per build | Seed-only / same-family baseline. |
| B | A second fixed family, independently seeded | Fixed-family comparison. |
| C | A third fixed family, independently seeded | Fixed-family comparison. |
| MIX | Select A, B, or C per build in a balanced randomized block (e.g. four of each in every 12-build block); exact order generated and logged before attacks | Main per-build heterogeneity treatment, matched to the marginal mix of fixed-family transforms. |

The existing A/B/C pass lists can seed design, but they are provisional. Verify that options map to real transformations in the current generator, set every option explicitly, remove legacy no-op labels, and measure transform firing/coverage. Do not use the old H0-H5 report as the confirmatory result. Keep REP and VM-dispatch arms secondary until coverage is broad enough and the attack models are adequate; the current VM coverage is too narrow for the main paper.

For each project and arm, generate independently seeded builds. For every sampled pair, create one attack-development record on A, freeze and hash the resulting artifact, then test it on B. Also run adaptive-from-A and cold-start-on-B with equal budgets. Make attack order and randomization reproducible, and blind the evaluator where possible to arm names.

### Correctness and transformation evidence

- Execute the original project test suite where available and a differential suite on original versus transformed functions.
- Add generated/property-based inputs from evaluator-only seeds, boundary cases, exceptions, Unicode, empty collections, and stateful sequences appropriate to each target.
- Require syntax/compile checks and hermetic execution. Record failure reason and stage.
- Report transformation failure and semantic mismatch rates for every arm. Do not silently drop failures; primary attack efficacy among valid artifacts and end-to-end usable protection yield are both reported.
- Emit a per-build manifest: source hash, arm, seed, resolved options, actual operator firing counts/locations, tool versions, output hashes, test outcomes, and run environment.
- Test whether a repeated research build with the same source/config/structural seed is byte-identical **for the structural artifact under the locked environment**. If security-sensitive randomness prevents full-artifact identity, define and hash the reproducible structural portion and explain the nondeterministic envelope.

### Outcomes

**Primary:** per-function stand-alone behavioral recovery success on hidden tests at equal frozen/adaptive attacker budgets. The primary success criterion can be all hidden tests passing; report partial test pass fraction as a secondary measure. This is empirical behavioral recovery on a finite test suite, not proof of universal semantic equivalence.

**Attack work:** wall-clock and CPU time, memory, dynamic queries/inputs, symbolic solver calls, tool invocations, tokens (if any), analyst intervention, failures, and time-to-threshold with censored timeouts. Archive recovered outputs and attack state for audit.

**Protection cost:** build time, artifact size, startup latency, steady-state runtime, peak memory, compatibility, correctness yield, and percentage of program/functions actually transformed. Report each separately; no opaque “security score” composite.

**Structural descriptors:** real AST edit/shape measures; actual bytecode generated by the pinned interpreter if the artifact calls for bytecode; real CFG basic blocks/edges from a named, validated analyzer; and source similarity. Validate each on known-equivalent and known-different controls. Treat these as descriptive predictors, not resistance itself. Do not call source byte n-grams bytecode similarity or AST control-node counts CFG reconstruction.

## Statistical analysis plan

- Publish one primary contrast and its directional interpretation before the confirmatory run: the MIX-versus-fixed-family difference in the adaptive-minus-frozen behavioral recovery gap at equal budget.
- Use a hierarchical model appropriate to the endpoint: e.g. a mixed-effects logistic model for binary success, with fixed effects for arm, attacker policy, and their interaction; random effects for repository, function nested in repository, source build, and target build. Check convergence and predefine an alternative if the model fails.
- Use a project-cluster bootstrap as a robustness check, resampling projects first and then builds/functions within project. Report equal-weighted-project and task-weighted summaries if both are informative.
- For time-to-recovery with timeouts, use a survival/censored-time analysis; do not replace timeouts with arbitrary numbers without a sensitivity analysis.
- Report absolute success rates, effect sizes, 95% confidence intervals, missingness, failures, and denominators. Use a single pre-registered primary endpoint; correct secondary comparisons (e.g. Holm) and label exploratory results.
- Never calculate confidence intervals by resampling the 36/144/other pairwise cells as if they were independent; each build recurs in many cells. Do not include self-pairs in cross-build effects.
- Conduct the power simulation using pilot estimates only. Freeze analysis code and the statistical plan before the confirmatory labels are unblinded.

## Reproducibility and security constraints

Reproducible research and secure production builds are different requirements. A supplied seed must control only research transformation choices that need replay. It must **not** make production cryptographic keys, HMAC secrets, signing keys, session tokens, or licensing secrets predictable. Python documents `random.Random` as deterministic and unsuitable for cryptographic purposes, and recommends `secrets` for security-sensitive randomness ([`random`](https://docs.python.org/3/library/random.html), [`secrets`](https://docs.python.org/3/library/secrets.html)).

Therefore:

1. Do not route structural seeds and security secrets through one seeded PRNG. Use separate interfaces and security types.
2. Keep the default production path on the existing OS-backed CSPRNG behavior. Research determinism remains opt-in and cannot disable or weaken existing protections.
3. If a fully byte-identical test requires deterministic keys, inject test-only fixtures inside an isolated test harness; the production CLI must not create shipping artifacts with those fixtures.
4. Document that “same source + same structural seed” means reproducible structural transformation under a pinned environment, not deterministic production secrets.
5. Preserve a security regression gate: no seed path can set, recover, or reuse a production secret; default output behavior and feature coverage remain unchanged; all existing security/compatibility gates remain required before any eventual product change.

The user's stated constraint is part of the design: **do not disable, remove, or reduce any existing product feature to make the experiment easier.** Keep research arms opt-in and separate from default behavior. If an experimental technique changes correctness, size, speed, compatibility, or key handling, report the cost; do not quietly ship an inferior default.

## Go/no-go gates

| Gate | Pass condition before next stage | If it fails |
|---|---|---|
| G0 — Revision and scope | Exact source revision and dirty diff recorded; reconcile `0118936`/`_BuildEntropy` claims with the current workspace. | Pause claims based on those changes; fetch/attach the correct revision, or proceed only with current code. |
| G1 — Experimental wiring | Explicit options per arm; build index drives intended family selection; no hidden defaults/no-op labels; actual transformation firing is observable. | Repair protocol code and preserve the old results as historical, not corrected. |
| G2 — Reproducibility | Structural build output replays byte-for-byte for fixed input/config/seed/environment; independent runs match hashes. | Find uncontrolled randomness/time/process state before the pilot; do not use noisy outputs in paired inference. |
| G3 — Security | No seeded PRNG controls production keys/secrets; default security path unchanged. | Stop any full-artifact seeded-build work until deterministic testing is isolated from live key generation. |
| G4 — Semantic validity | Differential/property-based suite passes at the preregistered rate; failure/coverage reports are complete. | Revise transformations or limit the claim; do not count broken outputs as successful protection. |
| G5 — Attacker adequacy | Attack reaches the preregistered calibration threshold on unprotected and same-build controls and is not using evaluator oracle data. | Improve the attack or narrow its claim. A weak attack's failure is not evidence of defense. |
| G6 — Novelty and power | Search/screen log is complete, closest-prior comparison is written, and the confirmatory design reaches the predeclared power target. | Narrow or change the paper question before collecting confirmatory data. |
| G7 — Confirmation | Held-out results, costs, artifacts, statistics, and limitations all support a bounded claim. | Publish a null/negative result honestly, redesign, or stop; do not relabel endpoints post hoc. |

## Ordered work plan

### Phase 0 — Freeze reality (first)

1. Record `git rev-parse HEAD`, branch, dirty state, and all experiment configs.
2. Locate the exact `0118936` revision or confirm it is not in this checkout; compare its actual diff before inheriting any pasted claim.
3. Reconcile `docs/research/research-readiness-audit-2026-10-29.md`, `docs/research/protocol-v2.md`, saved JSON reports, and current source. Mark every mismatch as historical, corrected, or still open.
4. Leave the unrelated uncommitted pipeline change intact while working on research design; isolate future research edits in a branch when implementation starts.

**Deliverable:** a one-page revision/provenance note and an inventory of claims with code path, evidence artifact, and current status.

### Phase 1 — Repair and freeze the experiment (before more measurement)

1. Fix explicit build-index/pass-set selection and taxonomy keys; add schema checks so empty expected groups fail the run.
2. Make every arm fully specified: options, pass sets, randomization, expected firing, exclusions, and output directory.
3. Remove oracle leakage from the primary attack. If retaining the current known-source matcher, rename it and isolate it as a secondary threat-model track.
4. Replace inaccurate endpoints/metrics or rename them; store raw output of every attack and the VM case inside the repository's artifact bundle rather than `/tmp`.
5. Implement a machine-readable transfer bundle with source/target hashes, exact attack code, learned state, policy (frozen/adaptive/cold), budgets, logs, outputs, and evaluator score.
6. Add all protocol integrity checks before data collection; freeze the manifest and analysis code with hashes.

**Deliverable:** a versioned experiment spec, threat model, attack interface, data schema, and a dry-run report. Do not regenerate the confirmatory study until G1–G5 pass.

### Phase 2 — Pilot and preregister

1. Run the 10-project calibration set only.
2. Confirm arms actually differ and transforms fire; measure semantic failures, task difficulty, attacker baseline adequacy, attack runtime, output sizes, and variance.
3. Refine hidden test construction, attack budgets, eligibility, and smallest practically relevant effect using only pilot data.
4. Simulate statistical power at the repository level and decide the final corpus/build-pair count.
5. Publish or timestamp the preregistration: hypotheses, threat model, arm assignment, exclusions, endpoints, budgets, sample size, statistical model, multiplicity, stopping rule, and planned artifacts.

**Deliverable:** a preregistered protocol and power memo. A protocol change after this point requires a dated amendment before examining confirmatory outcomes.

### Phase 3 — Confirmatory study

1. Acquire and pin the held-out corpus with license review.
2. Generate randomized, balanced builds and validate them without exposing evaluation labels to attackers.
3. Run frozen, adaptive-from-A, and cold-start attack conditions in randomized order with matched budgets.
4. Capture all failures, exclusions, interruptions, and resource usage.
5. Preserve source, outputs, tool/environment locks, attack bundles, and manifests under a versioned artifact ID.

**Deliverable:** immutable raw dataset and signed/hashed run manifest. No arm or endpoint edits after labels are exposed.

### Phase 4 — Analysis and paper

1. Run the frozen analysis script; report the preregistered endpoint first.
2. Analyze project-level uncertainty, attack adequacy, coverage, semantic correctness, and costs.
3. Add exploratory analyses in clearly marked sections only.
4. Conduct a final novelty sweep, especially for source-level same-program transfer and new 2025–2026 papers.
5. Release a reproduction package with a clean environment, scripts, licenses, raw data, and a single command to regenerate tables/figures.
6. Write the paper after results are fixed; state exact tested scope and negative evidence.

**Deliverable:** manuscript, artifact, limitations, data-availability statement, and reviewer-ready response to the closest prior work.

## Suggested manuscript outline

1. **Introduction:** the practical deployment question: what survives from analysis of one customer/build variant to the next?
2. **Background and related work:** DCVP/CoDiver/DSVMP/DynOpVM, VM attacks, diversity/version matching, Python obfuscation studies, benchmarks, and evaluation methodology.
3. **Definitions and threat model:** frozen artifact, adaptive analysis, cold start, build pair, recovery task, attacker budget, and source access.
4. **System and experiment:** only the exact source-level transformation path, configuration, build generation, telemetry, corpus, correctness gates, attacks, and preregistration.
5. **Results:** primary transfer and adaptation outcomes, adequacy, costs, coverage, and robustness analyses.
6. **Discussion:** what transfers, what target adaptation recovers, what outputs/metrics predict, and what the result does not establish.
7. **Validity, ethics, and limitations:** public-source leakage, finite hidden tests, project sampling, attack family coverage, Python version, nondeterminism, and artifact constraints.
8. **Conclusion:** narrow empirical finding, not universal protection claim.

## Publication bar and venue strategy

“10/10” cannot be promised in advance. The quality bar is: clear question; defensible novelty; a realistic and adequate attacker; valid measurement; independent projects; power-backed analysis; complete negative-result reporting; reproducible artifacts; and no security or product regression. If the contribution remains mostly a measurement protocol and empirical dataset, target a software security, reverse-engineering, or empirical software engineering venue that values evaluation artifacts. A top security venue becomes realistic only if results reveal a consequential, generalizable mechanism or the paper adds a strong new defense/attack contribution beyond the benchmark. Choose the actual venue after the confirmatory pilot and current call-for-paper scope are known.

## References for the research plan

The following references are closest to the proposed claim; the related-work section must read and compare the primary paper, not cite a search snippet.

1. Xue et al., [Exploiting Code Diversity to Enhance Code Virtualization Protection](https://doi.org/10.1109/ICPADS.2018.00086), ICPADS 2018.
2. Wang et al., [Invalidating Analysis Knowledge for Code Virtualization Protection Through Partition Diversity (CoDiver)](https://doi.org/10.1109/ACCESS.2019.2954165), IEEE Access 2019.
3. Kuang et al., [Enhance Virtual-Machine-Based Code Obfuscation Security Through Dynamic Bytecode Scheduling](https://doi.org/10.1016/j.cose.2018.01.008), Computers & Security 2018.
4. Cheng et al., [DynOpVM: VM-Based Software Obfuscation with Dynamic Opcode Mapping](https://doi.org/10.1007/978-3-030-21568-2_8), ACNS 2019.
5. Xu, Zhou, and Lyu, [N-Version Obfuscation: Impeding Software Tampering Replication with Program Diversity](https://doi.org/10.1145/2899015.2899026), ACM CPSS 2016.
6. Coppens et al., [Feedback-Driven Binary Code Diversification](https://doi.org/10.1145/2400682.2400683), ACM TACO 2013.
7. Li et al., [Chosen-Instruction Attack Against Commercial Code Virtualization Obfuscators](https://doi.org/10.14722/ndss.2022.24015), NDSS 2022.
8. Kochberger et al., [SoK: Automatic Deobfuscation of Virtualization-protected Applications](https://doi.org/10.1145/3465481.3465772), ARES 2021.
9. Schloegel et al., [Loki: Hardening Code Obfuscation Against Automated Attacks](https://www.usenix.org/conference/usenixsecurity22/presentation/schloegel), USENIX Security 2022.
10. Banescu et al., [Predicting the Resilience of Obfuscated Code Against Symbolic Execution Attacks via Machine Learning](https://www.usenix.org/conference/usenixsecurity17/technical-sessions/presentation/banescu), USENIX Security 2017.
11. Ebad et al., [Measuring Software Obfuscation Quality—A Systematic Literature Review](https://doi.org/10.1109/ACCESS.2021.3094517), IEEE Access 2021.
12. De Sutter et al., [Evaluation Methodologies in Software Protection Research](https://doi.org/10.1145/3702314), ACM Computing Surveys 2024.
13. Jin et al., [A Framework to Quantify the Quality of Source Code Obfuscation](https://doi.org/10.3390/app14125056), Applied Sciences 2024.
14. De Tomasi et al., [Simplicity by Obfuscation: Evaluating LLM-Driven Code Transformation with Semantic Elasticity](https://arxiv.org/abs/2504.14024), EASE 2025.
15. Feng and Xu, [DEBRA: A Real-World Benchmark for Evaluating Deobfuscation Methods](https://doi.org/10.1145/3733822.3764674), SURE 2025.
16. Regano et al., [Empirical Assessment of the Code Comprehension Effort Needed to Attack Programs Protected with Obfuscation](https://doi.org/10.1016/j.cose.2026.104881), Computers & Security 2026.
17. [Python source obfuscation benchmark repository](https://github.com/jpwieland/Python_Obfuscation_benchmark), accompanying Wieland and Mello, *Evaluation of Obfuscation Strategies for Python Source Codes* (2025); verify venue metadata against the primary paper before citing.
18. [Class-based Obfuscation with Multi-objective Evolutionary Algorithms on Source Code](https://doi.org/10.1007/s10207-026-01297-z), International Journal of Information Security 2026.
19. Feng et al., [Accurate and Efficient Code Matching Across Android Application Versions Against Obfuscation](https://doi.org/10.1109/SANER60148.2024.00028), SANER 2024.
20. [Can LLMs Deobfuscate Binary Code? BinDeObfBench](https://arxiv.org/abs/2604.08083), arXiv preprint 2026; treat as a preprint unless publication status is rechecked.
21. [Python `random` module security warning](https://docs.python.org/3/library/random.html) and [Python `secrets` module](https://docs.python.org/3/library/secrets.html), official documentation; relevant to the separation between reproducibility and production secrets.

## Bottom line

There is a plausible publishable study here, but the paper is not currently a “10/10” result and novelty is not established. The highest-value action is to make the benchmark experimentally valid and then let a strong attacker test the core premise. Do not spend the next iteration adding another obfuscation layer, claiming the entropy audit is in this checkout, or polishing a “first” claim. Keep the product's security and feature set intact; make the research path stricter, observable, and reproducible; then publish whichever answer the data supports.
