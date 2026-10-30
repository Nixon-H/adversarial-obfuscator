# Novelty Search Log

**Date:** 2026-10-30
**Purpose:** replace the plan's "targeted screen" with a documented one, so the
paper can state a bounded novelty claim with its criteria attached.

This is **not** a PRISMA-style systematic review. It is a reproducible screen:
the queries, the sources returned, the inclusion decision, and the closest
matches. Anything stronger needs database exports and double screening, which
this session did not do.

## Queries run

1. `attack transfer across obfuscated builds deobfuscation`
2. `deobfuscation knowledge reuse across software versions obfuscation`
3. `Python source obfuscation empirical evaluation reverse engineering`
4. `software diversity analysis knowledge transfer obfuscation measurement`

## Sources returned and screened

| source | relevance | decision |
|---|---|---|
| [SoK: Automated Software Diversity](https://www.ics.uci.edu/~perl/automated_software_diversity.pdf) | states that diversity's cost goal "cannot be measured directly, so researchers resort to proxy measurements" | **include as methodology support** |
| [Empirical assessment of the code comprehension effort…](https://www.sciencedirect.com/science/article/pii/S016740482600057X) | controlled experiment on human effort against obfuscation | **include as closest prior on effort** |
| [Deconstructing Obfuscation (arXiv 2505.19887)](https://arxiv.org/html/2505.19887v1) | four-dimensional LLM deobfuscation evaluation, mentions transfer across dimensions | **include; distinct artefact class** |
| [SoK: Automatic Deobfuscation of Virtualization-protected Applications](https://www.ics.uci.edu/~perl/automated_software_diversity.pdf) | (already held) established deobfuscation taxonomy | include as background |
| [pyREtic (DEF CON 18)](https://www.youtube.com/watch?v=JDQf3rvPiaQ) | Python bytecode reverse engineering toolkit | background only |
| [PreEmptive: measuring obfuscation](https://www.preemptive.com/blog/measuring-software-obfuscation) | vendor blog on metrics | **exclude** — not peer-reviewed |
| [Hexacon / TyphoonCon training pages](https://www.hexacon.fr/trainer/software_deobfuscation_techniques) | practitioner training, mentions reusing workflows across related targets | **exclude from novelty**, note as practitioner evidence that reuse is real |

## Closest prior work and why each differs

1. **CoDiver (2019)**, **DSVMP (2018)**, **DynOpVM (2019)** — these study
   knowledge reuse and re-analysis for **virtualised bytecode**, where a stale
   opcode map fails for a structural reason (renumbering). No source-level
   analogue exists, which is why the mechanism argument was required.
2. **N-version obfuscation (2016)** — variant-to-variant tampering
   replication, not semantic identification.
3. **SANER 2024 code matching across Android versions** — obfuscation-resilient
   matcher transfer, but for binary/mobile artefacts and matching, not
   identification cost under a specification.
4. **Regano et al. 2026** — human comprehension effort against obfuscation;
   closest on *effort* measurement, different on transfer and artefact class.
5. **DEBRA (2025)** — real-world deobfuscation benchmark; benchmark
   contribution without cross-build transfer.

## What the screen supports

A bounded statement:

> We found no prior study that measures the cost for an attacker to identify a
> function across independently generated builds of the same Python source
> program, separating frozen from adaptive reuse, at matched budget, with an
> oracle-free attacker and a specification-derived property set.
>
> Search date 2026-10-30; four queries; seven sources screened; closest prior
> work and exclusion reasons recorded above.

## What it does not support

- "Nobody has done this." Not established, and the phrasing must not be used.
- Priority. A targeted screen cannot establish priority; a full systematic
  review with database exports would still be a claim about the databases
  searched, not the world.
- Completeness. Four queries on one day is a screen, not a census. The closest
  bodies of work (VM diversity, deobfuscation benchmarks, effort measurement)
  were known from the literature matrix before this search and are the real
  competition for the claim.

## Why the SoK quote matters

> "The goal of diversity—to drive up costs to attackers—cannot be measured
> directly, so researchers resort to proxy measurements."

That is the methodological premise of this work stated by a SoK: cost is the
goal, proxies are unavoidable, so the contribution is a **better-instrumented
proxy** — not a new theory of diversity. It also means the study must be
explicit that it measures a proxy, which the manuscript does.
