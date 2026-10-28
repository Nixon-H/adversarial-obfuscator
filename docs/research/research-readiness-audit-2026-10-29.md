# Research Readiness Audit

**Audited revision:** d42bed4caf78ec1473f5bee0e9e92bc94b388a0e
**Date:** 2026-10-29
**Scope:** repository architecture, active build paths, research harness and saved outputs, novelty screen

## Executive assessment

**The repository is not submission-ready as a research paper today. A good paper could be developed from it, but it needs a corrected experiment and new evidence before the headline claims are defensible.**

The most promising direction is a focused empirical study of how reverse-engineering work learned from one protected Python build carries over to other builds. The repository already has useful infrastructure: reproducible experiment configuration, held-out program labels, semantic gates, saved results, and an unusually candid record of failed instruments and corrections. Those are meaningful foundations.

The current results do not yet establish that diversified builds resist realistic reverse engineering. Two advertised arms did not run as configured, the primary static attack uses clean-source knowledge and evaluator test vectors, the statistical samples reuse builds as if pairwise observations were independent, and the diversity metrics do not measure compiled bytecode or real CFGs as named. The VM result is narrower: a frozen opcode map fails after the target's map changes. It does not show that an attacker cannot recover the target map.

**Do not claim “nobody has done this.”** Prior work has explicitly studied making analysis knowledge fail to transfer across diversified virtualized code. A narrow contribution may still exist in a validated benchmark for frozen versus adaptive attack reuse in Python, but this rapid literature screen cannot establish priority.

## What I inspected

The repository has 1,567 tracked files, including 1,183 Python files, 250 JSON files, 53 Markdown files, and 41 Rust files. I inventoried the tracked tree and deeply reviewed the current product documentation, threat model, research protocols, H0-H5 runner, attacks, metrics, arm definitions, synthesis planner, and committed experiment outputs. I also checked the six saved H0-H5 JSON reports and the corpus metadata.

I cannot honestly say that I read every line of all 1,567 files. The tree includes many archived, generated, and experiment-artifact files; this was a focused audit of the live paths and research evidence rather than a literal line-by-line read of every fixture.

The product docs describe two different build paths: the native builder in [scripts/build.py](../../scripts/build.py) and the hybrid loader in [obfuscator/core/pipeline.py](../../obfuscator/core/pipeline.py). The H0-H5 experiments use the research generator and ObfuscationTransformer; they do not evaluate the complete default production build. Any paper must state which path and exact research configuration it studies. The repository's SECURITY.md and THREAT_MODEL.md do a good job of limiting claims and separating research flags from validated defaults.

## What the current evidence supports

### H0-H5 static transfer experiment

The [aggregate report](h0h5-results/AGGREGATE.md) records 216 builds across six programs and 1,296 attack applications per program, with all 216 builds passing the existing semantic gate. It reports transfer ratio T=1 across the static attack's tested comparisons. This is a real pilot result, but its scope is much narrower than “heterogeneous obfuscation does not resist reverse engineering.”

The runner generates one variant at a time: [experiment.py](../../scripts/transfer/experiment.py#L50). The generator selects a pass set using variant_id modulo the number of pass sets in [generator.py](../../scripts/diversity/generator.py#L30). Since each call generates one variant, its ID is always zero. H1 and H5 therefore always use only their first configured pass set. H0 and H1 have the same first pass set and options; H5 adds representation diversification and alternating VM dispatch to that first set. The advertised pass-set heterogeneity in H1/H5 was not tested.

There is a second arm-comparison problem. [generator.py](../../scripts/diversity/generator.py#L47) hardcodes metadata stripping, constant unfolding, and call obfuscation to true. H0/H1/H5 leave these enabled, while H2/H3/H4 explicitly turn them off through ISOLATION_OFF in [arms.py](../../scripts/transfer/arms.py#L9). This makes comparisons across these arms confounded by transformations outside the named hypothesis.

The primary endpoint name is misleading. S_cfg counts functions mapped to candidates that pass a finite set of known input/output vectors; it does not score control-flow graph recovery. S_cfg_boundary is candidate mapping presence, not CFG-boundary recovery. See [measure.py](../../scripts/transfer/measure.py#L80).

The static attack is also oracle-assisted. During development it reads the clean original source to create target-function structural features and uses known vectors to select weights ([attack.py](../../scripts/transfer/attack.py#L210)). During application it maps target AST features against those clean-source features and confirms with the supplied vectors ([attack.py](../../scripts/transfer/attack.py#L262)). This can be a valid *known-source template-matching* scenario if stated explicitly. It is not a general MATE reverse-engineering attacker, and the code does not learn a rich build-specific attack artifact: the application recomputes target features, while extracted marker counts are not used.

The main statistical comparison treats 36 ordered within-arm build pairs as observations, including six self-pairs whose T value is fixed at 1. Each of the same six builds is reused across many cells. The CI resamples these pair cells rather than independent functions or independent builds ([experiment.py](../../scripts/transfer/experiment.py#L155), [measure.py](../../scripts/transfer/measure.py#L144)). This overstates the independent sample size. Inference needs a pre-defined experimental unit and a cluster-aware analysis.

The taxonomy output is empty where it should compare seed-only and heterogeneous groups. [measure.py](../../scripts/transfer/measure.py#L68) filters for keys beginning with hetero: and seed_only:, while the saved experiments use H0-H5 keys. All six committed H0-H5 JSON reports contain 1,296 endpoint entries but zero grouped T_hetero and T_seed values. protocol-v2.md says the grouping bug was fixed; the checked-out source and outputs do not reflect that fix.

### Diversity measurements

The current composite diversity score cannot support the broad statement that structural diversity does not predict transfer:

- [metrics.py](../../scripts/diversity/metrics.py#L39) counts AST control constructs and calls; it does not construct basic blocks or graph edges.
- compute_bytecode_similarity in [metrics.py](../../scripts/diversity/metrics.py#L120) reads raw Python source-file bytes and compares 4-grams; it does not inspect compiled Python bytecode.
- The reported “IR” similarity is another AST feature count, not an IR comparison.

These may be useful exploratory source-shape proxies, but they need accurate names and validation before the paper links them to CFG or bytecode diversity. Report component metrics separately; do not rely on one weighted score as a security measure.

### VM, CFG, and constant experiments

The VM result is based on calc, the only VM-eligible program in the current corpus. The extractor parses the emitted dispatcher from each target's source, and the evaluator aligns functions with exact true-op sequences ([vm_attack.py](../../scripts/transfer/vm_attack.py#L286), [vm_attack.py](../../scripts/transfer/vm_attack.py#L330)). Applying build A's map to build B shows that stale opcode numbers decode poorly after a per-function permutation. It does not test whether an attacker can parse or adapt to build B; the target's mapping is directly visible to the same parser. The claim should be “frozen-map decoding fails across these variants,” not “VM reverse engineering is blocked.” The raw matrix cited in vm-transfer.md lives at /tmp/opencode/vm_matrix.json, outside the repository, so the result is not fully archived for reproduction.

The CFG transfer report is a useful pilot structural signal, but it covers one program and uses an instrument that measures signatures rather than a complete reverse-engineering attacker. The Ghidra pilot was correctly rejected after its function-count endpoint tracked binary mass rather than protection effect; that was good research judgment, but it leaves the main results without an independent decompiler attack.

The const-split report has stronger protocol discipline, including disclosed instrumentation changes and semantic gates. It still uses three builds per arm per program, and its bytecode constant-pool endpoint measures literal search, not algebraic recovery of values.

### Research planner and entropy work

The protection planner is engineering scaffolding, not an evidence-based adaptive planner. [costs.py](../../scripts/synthesis/costs.py#L42) assigns hand-written security gains and overheads; those gains are not calibrated against the measured attack outcomes. The optimizer's outputs therefore cannot substantiate a claim that it chooses empirically optimal protections.

The entropy audit and pinned builds help reproducibility. Deterministic seeds are already standard engineering practice in other obfuscators, including [Obfuscator-LLVM](https://github.com/obfuscator-llvm/obfuscator/wiki/FAQ) and [xollvm](https://xollvm.github.io/concepts/determinism/). That work is useful infrastructure, not by itself a new security contribution. It should not be the paper's central claim.

## Novelty screen

The closest prior work makes a broad “first transfer-resistant diversification” claim untenable:

- [CoDiver (IEEE Access, 2019)](https://doi.org/10.1109/ACCESS.2019.2954165) randomizes virtual-opcode-to-semantics mappings across code partitions specifically so knowledge learned from one region or program cannot simply be reused on another.
- [DCVP (ICPADS, 2018)](https://doi.org/10.1109/PADSW.2018.8644535) partitions VM-protected code and changes opcode-to-handler mappings to limit reuse of analysis knowledge.
- [N-Version Obfuscation (ACM CPSS, 2016)](https://doi.org/10.1145/2899015.2899026) studies program diversity as a way to impede replication of tampering attacks.

Python obfuscation evaluation is not an empty field either. The [EASE 2025 study](https://doi.org/10.1145/3756681.3757041) evaluates LLM-generated Python obfuscation on 30 functions and measures semantic correctness; it is adjacent work, not a direct cross-build attack-transfer benchmark. A [2024 source-code obfuscation evaluation framework](https://doi.org/10.3390/app14125056) measures CFG, paths, and performance, while a [2026 controlled human study](https://doi.org/10.1016/j.cose.2026.104881) examines attacker effort and whether complexity metrics predict success. The [2024 ACM survey](https://doi.org/10.1145/3702314) reviewed 571 software-protection papers and documents substantial methodological and reproducibility problems.

These sources mean the literature matrix's claims that no transfer metric or Python benchmark exists should be revised and qualified. This was a rapid search, not a systematic review; it cannot establish that the narrower benchmark contribution has never appeared.

## Strongest candidate paper

**Working title:** *When Does Analysis Transfer Across Obfuscated Python Builds? Measuring Frozen and Adaptive Attack Reuse*

**Research question:** Under which attacker capabilities does analysis learned from one diversified Python artifact transfer to another, after accounting for target-specific adaptation, semantic correctness, and overhead?

The paper should measure one clearly defined thing: **how much work learned on build A helps against build B, and how much new work is required to adapt to B.** Separate these two conditions:

1. **Frozen transfer:** apply the same recovered rules, maps, or templates from A to B without updating them.
2. **Adaptive recovery:** give the attacker B and allow target-specific analysis, then measure recovery and adaptation time or effort.

This distinction keeps “the old map is stale” separate from “the target is hard to analyze.” The clean source and test vectors should either be evaluator-only or form a separately labeled known-source threat model; they must not silently flow into the attacker.

Useful research questions:

- **RQ1:** How does a specific attack artifact's recovery success change when transferred across seeds and transformation families?
- **RQ2:** How much does target-specific adaptation restore recovery, and what time or query cost does that add?
- **RQ3:** Do validated source, bytecode, or CFG distances predict attack recovery or adaptation effort?
- **RQ4:** What semantic and operational costs accompany each protection configuration?

Use controlled arms with one factor changed at a time, plus a combined arm whose components are genuinely active. Include seed-only and unprotected controls. Evaluate at least two meaningfully different attack families, and include an adaptive baseline for every claimed frozen-transfer effect. A target-specific VM parser is an appropriate adaptive baseline for the current VM experiment.

Move beyond the six hand-written programs (37–51 lines, 3–4 functions each, and 4–8 total vectors). Use a varied open-source Python corpus, split at the project level so functions from one project cannot leak between calibration and held-out evaluation. Set corpus size from a pilot and power analysis rather than choosing a round number after seeing results. Add broader differential or property-based correctness coverage; passing a few vectors is a semantic smoke gate, not proof of equivalence.

Pre-register the primary endpoint, attacker knowledge, exclusions, sample unit, statistical model, multiplicity handling, and stopping rule. Report absolute attack success alongside any transfer ratio. Analyze independent builds and projects as clusters; do not treat all A→B pairings as unrelated observations or include self-pairs in the cross-transfer sample. Preserve raw builds, tool versions, seeds, commands, intermediate attack artifacts, and outputs inside a versioned/reproducible artifact bundle.

The paper can still make a strong contribution if the result is negative. If an adaptive attacker cheaply recovers each randomized mapping, that is evidence about the limit of this diversification technique. Do not reinterpret a frozen-template failure as attack resistance.

## Prioritized work before drafting

1. **Fix the experiment wiring and version the protocol.** Pass the intended arm index into variant generation (or generate a complete batch with explicit per-build treatment). Repair taxonomy grouping, remove or accurately rename unused labels, and preserve the corrected raw outputs.
2. **Define the attacker boundary.** Specify whether the attacker knows clean source, test inputs/outputs, tool internals, and transformation family. Keep evaluator truth out of the attacker except in an explicitly named oracle scenario.
3. **Replace the weak metrics.** Implement actual CFG and bytecode features where those names are used. Keep source n-gram similarity labeled as such. Validate the metrics against known positive and negative controls.
4. **Add adaptive attack comparisons.** For each frozen artifact, run the best reasonable target-specific extractor or deobfuscator. Record both recovery and the cost of adaptation.
5. **Improve the corpus and correctness evidence.** Use real projects with richer behavior and held-out projects; retain the current toy corpus as a sensitivity suite.
6. **Pre-register and rerun.** Use a power analysis and cluster-aware inference, report failures and exclusions, and reproduce the full run from a clean checkout.
7. **Only then write the paper and lock the contribution.** Run a documented systematic literature search before any “first” or “to our knowledge” statement.

## Protecting the existing product

This research plan does not require weakening or removing shipped features. Keep experiment arms and new research transforms behind opt-in research configuration. Do not change default pipeline behavior to simplify an experiment. Any later production change should preserve existing feature coverage and pass the repository's current CI and security gates; the paper should report any runtime, size, compatibility, or behavior cost rather than quietly accepting an inferior build.

## Final verdict

There is a serious research program here, but **the present evidence is pilot-grade, not publication-grade**. The strongest assets are the attempt to preregister, freeze configurations, record failed instruments, keep a threat model, and report null results. The blockers are concrete and fixable: arm selection, confounding, attack-oracle disclosure, metric validity, statistical dependence, a missing raw VM artifact, and limited attack/corpus coverage.

A publishable paper is plausible if it becomes a rigorous, narrow study of frozen versus adaptive cross-build analysis in Python and the literature review confirms a sufficiently specific gap. The current repository cannot yet support “new, nobody did this” or broad claims that its obfuscation resists reverse engineering.

## Selected references

- De Sutter et al. [Evaluation Methodologies in Software Protection Research](https://doi.org/10.1145/3702314), *ACM Computing Surveys* (2024).
- Xue et al. [Exploiting Code Diversity to Enhance Code Virtualization Protection](https://doi.org/10.1109/PADSW.2018.8644535), *ICPADS* (2018).
- Wang et al. [Invalidating Analysis Knowledge for Code Virtualization Protection Through Partition Diversity](https://doi.org/10.1109/ACCESS.2019.2954165), *IEEE Access* (2019).
- Xu, Zhou, and Lyu. [N-Version Obfuscation: Impeding Software Tampering Replication with Program Diversity](https://doi.org/10.1145/2899015.2899026), *ACM CPSS* (2016).
- Jin et al. [A Framework to Quantify the Quality of Source Code Obfuscation](https://doi.org/10.3390/app14125056), *Applied Sciences* (2024).
- De Tomasi et al. [Simplicity by Obfuscation: Evaluating LLM-Driven Code Transformation with Semantic Elasticity](https://doi.org/10.1145/3756681.3757041), *EASE* (2025).
- Regano et al. [Empirical Assessment of the Code Comprehension Effort Needed to Attack Programs Protected with Obfuscation](https://doi.org/10.1016/j.cose.2026.104881), *Computers & Security* (2026).

**Audit actions:** no implementation files were changed and no tests were run. The only research-claim checking beyond source review was read-only inspection of the committed experiment JSON and a rapid scholarly web search.
