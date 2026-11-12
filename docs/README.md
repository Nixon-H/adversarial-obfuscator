# Documentation

This directory holds two kinds of material, and the distinction matters when
you are deciding what to trust:

- **Current documentation** — describes the system, the research method, and
  the results as they stand at `master`. It is maintained and, where possible,
  guarded by tests.
- **Historical records** — dated audits, per-round research notes, retractions,
  and design records. They are preserved verbatim because they are evidence of
  how the conclusions were reached. They are not updated to match later state.

If a current document and a historical record disagree, the current document
wins; if a current document and the code disagree, the code and its tests win.

---

## Read this first

| If you want to know | Read |
|---|---|
| What the project is, why it exists, and what it found | [`../README.md`](../README.md) |
| The research question, threat models, prior work, and method | [`RESEARCH.md`](RESEARCH.md) |
| How the system is built and where each stage lives | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| What each protection technique actually changes | [`TRANSFORMS.md`](TRANSFORMS.md) |
| What each option is *for*, and whether it is wired | [`SECURITY_FEATURES.md`](SECURITY_FEATURES.md) |
| The strongest configuration that was actually built and run | [`MAXIMUM_SECURITY.md`](MAXIMUM_SECURITY.md) |
| What the seeds do, and what they do not | [`SEED_ARCHITECTURE.md`](SEED_ARCHITECTURE.md) |
| Every flag with parser, default, and objective | [`FLAG_AUDIT.md`](FLAG_AUDIT.md) |
| How the benchmark and attacker are constructed | [`BENCHMARK.md`](BENCHMARK.md) |
| What was measured, and what survived review | [`RESULTS.md`](RESULTS.md) |
| What the project does **not** claim, and what is still open | [`LIMITATIONS.md`](LIMITATIONS.md) |
| Every CLI flag, generated from the parsers | [`CLI.md`](CLI.md) |
| How to re-run the tests, gates, and tables | [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) |
| How to build, test, and extend the code | [`DEVELOPER.md`](DEVELOPER.md) |
| Task-oriented walkthroughs with pasted output | [`USER_GUIDE.md`](USER_GUIDE.md) |
| The complete research record, round by round | [`research/README.md`](research/README.md) |

---

## Current documentation

| Document | Scope | Status |
|---|---|---|
| [`RESEARCH.md`](RESEARCH.md) | Problem statement, research questions, threat models, prior work, evidence standard | Maintained |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Two artefact producers, pipeline stages, runtime, invariants | Maintained |
| [`TRANSFORMS.md`](TRANSFORMS.md) | Protection layers, transformation taxonomy, flag-to-effect map, inert flags | Maintained |
| [`SECURITY_FEATURES.md`](SECURITY_FEATURES.md) | Objective-level classification; IP protection vs licensing vs integrity; wiring | Maintained |
| [`MAXIMUM_SECURITY.md`](MAXIMUM_SECURITY.md) | Configuration matrix, interactions, measured builds, bounded attack probe, negative results | Maintained |
| [`research/ai-layer-bench-2026-11-11/RESULTS.md`](research/ai-layer-bench-2026-11-11/RESULTS.md) | Fresh per-layer AI benchmark: crack/recall and refusal rates, read-only agent replication, and full-tool packed-loader recovery | Pilot measurement |
| [`CRYPTO_REVIEW.md`](CRYPTO_REVIEW.md) | Internal review of payload/string/section/licence crypto; **not independent** | Maintained |
| [`SEED_ARCHITECTURE.md`](SEED_ARCHITECTURE.md) | Reproducibility seeds vs randomisation vs key material; measured determinism | Maintained |
| [`FLAG_AUDIT.md`](FLAG_AUDIT.md) | Every flag with parser, default, and primary objective | Generated from the parsers, 2026-11-10 |
| [`BENCHMARK.md`](BENCHMARK.md) | Corpus, attacker, cost unit, gates, protocols, validity threats | Maintained |
| [`RESULTS.md`](RESULTS.md) | Measured results, defect register, retractions, status of each claim | Maintained |
| [`LIMITATIONS.md`](LIMITATIONS.md) | Scope limits, unresolved questions, future research | Maintained |
| [`CLI.md`](CLI.md) | Complete generated reference for both entry points | Generated + CI-checked |
| [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) | Exact commands for every claimed number | Maintained |
| [`DEVELOPER.md`](DEVELOPER.md) | Prerequisites, layout, lint, tests, extension points | Maintained |
| [`USER_GUIDE.md`](USER_GUIDE.md) | Verified walkthroughs of the main build modes | Maintained |
| [`CHANGELOG.md`](CHANGELOG.md) | Product changes, including reverted attempts | Maintained |
| [`../SECURITY.md`](../SECURITY.md) | Vulnerability reporting, supported versions, security invariants | Maintained |
| [`../THREAT_MODEL.md`](../THREAT_MODEL.md) | Attacker-by-attacker coverage and evidence taxonomy | Maintained |

## Reference and design records

| Document | What it records |
|---|---|
| [`EMITTER_PIPELINE.md`](EMITTER_PIPELINE.md) | Pass order and insertion invariants in the packed emitter |
| [`contracts.md`](contracts.md) | Overlapping "twin" subsystems and which one is authoritative |
| [`failure-modes.md`](failure-modes.md) | Failure-oriented audit: fail-open vs fail-closed behaviour |
| [`LICENSING.md`](LICENSING.md) | Offline Ed25519 licence tokens and their current limits |
| [`ATTESTATION.md`](ATTESTATION.md) | Which component owns the attestation protocol |
| [`PLATFORMS.md`](PLATFORMS.md) | Platform support matrix |
| [`RUNTIME_DECISION.md`](RUNTIME_DECISION.md) | Why the Rust runtime is not load-bearing |
| [`rust_cfg_audit.md`](rust_cfg_audit.md) | Rust feature-gate audit |
| [`relay_config.md`](relay_config.md) | Relay configuration |
| [`stub_integration_plan.md`](stub_integration_plan.md) | Native stub integration plan |
| [`adr/`](adr/) | Architecture decision records 0001–0005 |
| [`../irgen/SPEC.md`](../irgen/SPEC.md) | Nixon IR specification |
| [`../native/PAYLOAD_CONTRACT.md`](../native/PAYLOAD_CONTRACT.md) | Native payload ABI |
| [`../obfuscator/lowering_DESIGN.md`](../obfuscator/lowering_DESIGN.md) | Semantic-lowering registry and kernel design |

## Historical records

| Path | Period | Why it is kept |
|---|---|---|
| [`research/`](research/) | 2026-09 → 2026-11 | The full measurement programme: protocols, per-round findings, defect documents, retractions, paper draft |
| [`AUDIT-2026-10-19.md`](AUDIT-2026-10-19.md) | 2026-10-19 | Full repository audit, including the seal corruption and `mlockall` findings |
| [`AUDIT-2026-10-19-followup.md`](AUDIT-2026-10-19-followup.md) | 2026-10-19 | Follow-up verification round |
| [`AUDIT-2026-10-20.md`](AUDIT-2026-10-20.md) | 2026-10-20 | CLI and documentation audit |
| [`ROADMAP.md`](ROADMAP.md) | 2026-06 → | Original phase design. **Historical**: the shipped pipeline is driven by `obfuscator/core/`; see `ARCHITECTURE.md` |
| [`../archive/`](../archive/) | 2026-09 | Superseded native/relay/Rust material and third-party analyses |

Dated audit reports describe the tree as it was on their date. Flags mentioned
there may no longer exist; that is expected, not a documentation bug.

---

## Status vocabulary

Used consistently in the current documents:

| Label | Meaning |
|---|---|
| **Verified** | Measured or executed in this repository, with a command that reproduces it |
| **Implemented** | Code exists and has tests, but has not been independently evaluated |
| **Experimental** | Opt-in, partially validated, or known to have narrow conditions |
| **Research-only** | Harness or scaffold; not part of the product's supported surface |
| **Inert** | Accepted by a parser but has no runtime effect; documented so nobody trusts it |
| **Planned** | Designed or proposed, not implemented |

A claim is never stronger than the strongest label attached to its evidence.

---

## Documentation invariants

These are enforced, not aspirational:

- The CLI reference is generated from the live parsers
  (`scripts/gen_cli_reference.py`) and checked in CI
  (`tests/test_readme_matches_cli.py`). A flag added to a parser without a
  regenerated reference fails the suite.
- Every flag the user-facing docs mention must exist in a parser
  (`tests/test_documented_flags_exist.py`).
- The research documents' defect counts, benchmark counts, and headline figures
  are cross-checked against the code and the paper
  (`tests/test_research_docs_consistency.py`,
  `tests/test_research_numbers_match_sources.py`).
- The README must keep the product version distinct from the vendor's
  obfuscation-technique generations `v1.1`–`V10`
  (`tests/test_version_consistency.py`).

## Known documentation gaps

Recorded here rather than hidden:

1. **No independent specification for the full benchmark.** Two of the eleven
   load-bearing tasks were specified blind; the rest were authored inside the
   programme. The paper states this; no document can fix it without new work.
2. **The build-spread measurement in the paper has no committed seed set or
   command** (final review, item 4.8). It is reported as an observation, not a
   reproduced table.
3. **Per-round research documents are snapshots.** Counts in `HANDOFF.md` and
   older round reports reflect their round, not `master`. `research/README.md`
   is the current index; the individual round documents are the record.
4. **The sealed-report path named in `research/README.md` is outside this
   repository.** The reports exist locally under `research-reports/` in the
   author's workspace but are not committed.
5. **The product changelog's reproducibility entry was stale.** It said
   `--randomization-seed` was gone; the flag is still accepted by
   `scripts/build.py`, but it seeds only part of the pipeline and does not make
   builds byte-reproducible. The entry now carries a dated correction, and
   `REPRODUCIBILITY.md` states the current behaviour.
6. **The packed loader is not byte-reproducible.** `--seed` now makes the
   source emitter byte-identical for the same payload/tool/flags (the wiring
   fix is in `phase01_obfuscate.py`), but the loader still draws blob/string/
   section keys and packaging choices from `secrets`. `--pin-structure` pins
   structure only. [`SEED_ARCHITECTURE.md`](SEED_ARCHITECTURE.md) §3.1 and §5.
7. **Attack measurement is bounded, not a study.** [`MAXIMUM_SECURITY.md`](MAXIMUM_SECURITY.md)
   §7 records a deterministic-probe + single-LLM measurement of the maximum
   loader and the O4 source artefact. It is not a frontier-analyst study.
8. **Trial/HWID gates did not reach the standard packed-loader artefact.**
   Builds with `--trial 1s` or `--hwid … --hwid-lock` still ran past expiry /
   on the wrong identity; the gates are wired into the hybrid-loader path, not
   the `--skip-cloud` packed-loader path. Recorded as an open defect in
   [`MAXIMUM_SECURITY.md`](MAXIMUM_SECURITY.md) §6.9.
9. **The crypto review is internal, not independent.**
   [`CRYPTO_REVIEW.md`](CRYPTO_REVIEW.md) records the first-party audit.
10. **Flag categories in [`FLAG_AUDIT.md`](FLAG_AUDIT.md) are a primary-objective
   classification.** A flag may serve more than one objective (for example,
   `--licence-token` is both access control and key binding, and
   `--licence-env-only` removes the local token-file search).
