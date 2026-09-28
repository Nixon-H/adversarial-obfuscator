# Subsystem Contracts: overlapping twins and near-twins

For each pair/group: who owns what, whether a shared interface exists,
and differential-test status. Rule used throughout: a differential test
exists ONLY where semantics genuinely overlap (same inputs → comparable
outputs). Otherwise: **no differential — different jobs**.

All paths relative to repo root. Both sides of every pair verified present
(2026-09-28).

## 1. Poly engines: `scripts/poly/poly_engine.py` vs `scripts/environment/poly_engine.py`

- Ownership: `scripts/poly` (`PolyEngine`) owns *emitting polymorphic
  decryptors* bound to the environment (`generate_decrypt_code`,
  `encrypt_for_environment`, `verify_environment`). `scripts/environment`
  (`EnvironmentalPolyEngine`) owns *fingerprinting the platform to pick
  code variants* (`generate_poly_variant`, `adapt_value_to_environment`,
  `get_variant`). Both files declare each other TWIN / "do not merge" in
  their module docstrings.
- Contract: partial overlap — both expose `get_environment_profile()`
  with the same three platform-fact fields (`os`, `python`, `arch`), but
  fingerprints differ BY DESIGN (`PolyEngine` mixes in cpu-features +
  seed, 32 hex chars; `EnvironmentalPolyEngine` mixes in hardware
  features + seed, 16 hex chars). Fingerprint VALUES are not comparable
  across engines; the platform FACTS are.
- Differential-test status: YES — `tests/test_subsystem_contracts.py`
  asserts both profiles agree on `os`/`python`/`arch` on the same host
  (same inputs → comparable outputs). Fingerprint equality is explicitly
  NOT asserted.

## 2. Dispersal: `scripts/payload/dispersal.py` vs `scripts/dispersal/payload_dispersal.py`

- Ownership: `scripts/payload` (`PayloadDisperser`) owns *AST-level slice
  dispersal* — splits a payload FUNCTION into `Slice`s with `MergePoint`
  state reconstruction (`disperse(source, num_slices)`). `scripts/dispersal`
  (`PayloadDispersal` + `ShamirSharing`) owns *secret-share dispersal* —
  splits payload BYTES into N Shamir shares over GF(251) with quorum
  reconstruction (`disperse(payload, num_shares, threshold)`).
- Contract: no shared contract — different jobs (code slicing vs crypto
  secret sharing; `str` function source in, `bytes` out vs `bytes` in,
  share quorum out). Neither imports the other.
- Differential-test status: no differential — different jobs.
  (`tests/test_payload_dispersal.py` already covers each side separately.)

## 3. Profiler vs classification: `scripts/optimizer/profiler.py` vs `scripts/classification/`

- Ownership: `FunctionProfiler` owns *measurement* — per-function metrics
  (`FunctionInfo`: LOC, cyclomatic complexity, exec frequency, imports,
  category default `simple_helper`) feeding `CostOptimizer` (Stage 0.5,
  `--optimize`). `FunctionClassifier` + `StrategySelector` own *labeling
  and policy* — AST-pattern category (`crypto`, `license_check`, …) mapped
  to a protection pass stack (Stage 0.6, `--adaptive`). Wired sequentially
  in `scripts/build.py`, never importing each other.
- Contract: no shared contract — different jobs (measure vs label).
  `FunctionInfo.category` is a profiler-side default string, not a
  classifier verdict.
- Differential-test status: no differential — different jobs.

## 4. Fragment cryptos: `scripts/fragment/fragment_compiler.py` vs `scripts/fragment/micro_fragment.py`

- Ownership: `fragment_compiler.py` owns *chained bytecode fragments* —
  `derive_fragment_key` binds each key via
  HMAC-SHA256(chain_key, previous_output || fragment_id);
  `aes_ctr_encrypt_fragment` encrypts the payload. `micro_fragment.py`
  owns *index-keyed line fragments* — `_derive_sequence_key` is
  SHA-256(master_key || index); `_xor_encrypt` is a SHA-256-counter stream
  cipher; `MicroFragmentExecutor` decrypt→exec→wipe per line-chunk. The
  compiler header names both twins ("different granularity/binding; do
  not merge").
- Contract: overlapping primitive shape — both are symmetric
  encrypt→decrypt transforms over `bytes` with a derived key, so the
  SAME plaintext vectors must roundtrip through BOTH (each with its own
  key schedule; cross-decryption is NOT expected).
- Differential-test status: YES — `tests/test_subsystem_contracts.py`
  roundtrips shared vectors (empty, 1-byte, text, 0-255, 1K zeros, 4K
  binary) through `aes_ctr_encrypt_fragment` (self-inverse) and
  `_xor_encrypt` (self-inverse) and asserts byte-identity.

## 5. Attestation trio: `scripts/distributed/dist_attestation.py` vs `scripts/runtime/challenge_response.py` vs `--attestation` flag

- Ownership (three layers, three scopes):
  - `DistributedAttestation` owns *cross-host orchestration* —
    N-node pairwise challenges + consensus (`run_pairwise_attestation`,
    `run_consensus_protocol`), simulation/process modes.
  - `scripts/runtime/challenge_response.py` (`ChallengeResponse`) owns the
    *standalone pairwise protocol* — per-peer secrets, nonce challenges,
    timing jitter, self-destruct after `max_failures`; operable without
    the distributed system (enabled via `--challenge-response`).
  - `--attestation` owns the *in-artifact core*: build flag sets the
    phase2 `attestation` feature whose canonical implementation is
    `runtime/src/sw_attestation.rs` (`ChallengeHandler`/`AttestationEngine`,
    answered INSIDE one artifact). The legacy C sim
    (`native/attestation.c`) was DELETED (see `tests/test_attestation.py`,
    `docs/ATTESTATION.md`).
- Contract: no shared contract — different jobs (orchestrate-between vs
  authenticate-peer vs answer-inside). Method names rhyme
  (`create_challenge`/`verify_response`) but peer-ID types differ
  (`int` node ids vs `str` peer ids) and consensus exists only on the
  distributed side.
- Differential-test status: no differential — different jobs.

## 6. Evidence trio: `scripts/evidence/ledger.py` vs `scripts/certificates/` vs `scripts/verification_bundle/`

- Ownership:
  - `EvidenceLedger` owns the *claim↔evidence data model* — `ClaimEntry`/
    `EvidenceEntry`, hash-verified claim chain, `build_evidence_ledger` /
    `verify_evidence` / `generate_evidence_report`.
  - `scripts/certificates/` owns *per-pass proof-carrying certificates* —
    `Certificate` binds (pass, input_hash, output_hash, equivalence_proof);
    `CertificateChain` links them; `CertificateCollector` gathers;
    `integrity.py` hashes AST/IR/bytes/source.
  - `scripts/verification_bundle/` owns *tamper-evident packaging* —
    `ArtifactCollector` + `ManifestBuilder` + `file_sha256`/`data_sha256`
    produce a self-verifying `tar.gz` snapshot.
- Contract: no shared contract — different jobs (model vs per-pass proofs
  vs archive). They compose (certificates can be ledger evidence; the
  bundle can ship both) but share no interface. (Nearby names that are NOT
  this trio: `scripts/ledger_proof.py` is a proof script and
  `runtime/src/ledger.rs` is the artifact-side Rust ledger — different
  layers, pinned by the no-third-impl lint's exact-match rule.)
- Differential-test status: no differential — different jobs.

## 7. Audit quartet: `scripts/self_audit/` vs `scripts/independent_audit/` vs `scripts/claim_auditor/` vs `scripts/false_confidence/`

- Ownership (four scopes, each header says "do not merge"):
  - `self_audit` (`SelfAuditor`): in-pipeline ten-category release gate
    (F180), CONSUMES claim-auditor scores.
  - `independent_audit` (`IndependentAuditor` + `independent_audit()`):
    external cross-check of pipeline artifacts (F197/F200), not part of
    the pipeline.
  - `claim_auditor` (`ClaimDetector` → `auditor.audit_source`): per-claim
    evidence scoring (F172) — does a claim have supporting artefacts?
  - `false_confidence` (`FalseConfidenceDetector` → `audit_source/tests/
    benchmarks`): vacuous-pattern shapes (assert-nothing, 100-on-empty)
    in source/tests/benchmarks (F173).
- Contract: no shared contract — different jobs (gate vs external check
  vs evidence scoring vs vacuous-pattern detection). Report types differ
  (`AuditReport` vs `ClaimAuditResult` vs `DetectionResult`).
- Differential-test status: no differential — different jobs.

## 8. String crypto layers: `obfuscator/string_crypto.py` vs `obfuscator/chacha20.py`

- Ownership (stacked layers, not twins): `chacha20.py` owns the
  *primitive* — RFC 8439 block/stream (`chacha20_block`, `chacha20_xor`)
  plus HMAC-SHA256 AEAD (`aead_encrypt`/`aead_decrypt`, nonce||ct||tag).
  `string_crypto.py` owns *policy + integration* — allowlist semantics
  (`is_allowlisted`, exact + `re:` entries + safety-net sentinels), mode
  selection (`chacha20` vs legacy `xor`), sessions, and runtime stub
  emission (`emit_decoder_source`). `string_crypto` IMPORTS `chacha20`
  (one direction only); `chacha20` imports nothing project-internal.
  Both sit alongside (not replacing) the legacy XOR transform in
  `obfuscator/core/transforms.py` (`StringLiteralObfuscator`).
- Contract: layered import, not a shared interface — the AEAD boundary
  (`aead_encrypt`/`aead_decrypt`) is the contract, owned by `chacha20`.
- Differential-test status: no differential — different jobs (primitive
  vs policy). Roundtrip coverage already exists in
  `tests/test_chacha20_strings.py`.
