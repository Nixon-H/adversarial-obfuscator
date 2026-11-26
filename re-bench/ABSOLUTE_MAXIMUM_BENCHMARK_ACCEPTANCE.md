# ABSOLUTE MAXIMUM benchmark acceptance criteria


Status: validated methodology boundary, **not a release gate**.

## Objective validity

A structurally valid attempt must exit before timeout, remain inside its isolated workspace, keep `artifact.py` byte-identical, avoid host-credential leakage and forbidden host access, produce parseable `answer.json` with the required keys, obey static/dynamic scenario policy, and match the campaign artifact hash. Provider failures, quota failures, transport failures, harness failures, timeouts, malformed answers, mixed artifact versions, isolation violations, and credential leaks are invalid evidence.

## Evidence sufficiency

A benchmark group is complete only with five structurally valid attempts for the same variant, scenario, model, artifact hash, and attacker boundary. A full statistical campaign is complete only when every pre-registered group in that campaign meets that target and final repair/scoring/redaction/scan processing succeeds. The historical 32 post-fix groups plus 4 targeted pre-fix comparison groups were the shape of the earlier Hy4/TokenHarbor matrix; the final DeepSeek diagnostic matrix instead contains 114 variant/scenario cells. Anything less than five valid attempts per group is missing statistical evidence, never resistance evidence.

## Score use

Scores are reconstruction-content measurements under a transparent rubric. They are not resistance percentages and must not drive release pass/fail selection. AI-RE-003 is therefore resolved by rejection: no unvalidated benchmark score is a release gate. Release-relevant acceptance requires independently verified implementation behavior, negative controls, artifact/runtime validation, and sufficient benchmark evidence.

## Mandatory separations

Results must remain separate for every protected variant (`maximum-packed`, `maximum-local`, `maximum-cloud`, `absolute`, `absolute-cloud`, `absolute-native-only`), runtime secrets available, runtime secrets withheld, source-assisted versus non-source, static-only, dynamic, unprivileged, privileged, model/provider, artifact hash, and redacted-remote-context versus unredacted lanes.

Machine-readable form: `benchmark_acceptance_criteria.json`.

## 2026-11-27 diagnostic-scope amendment

The completed `opencode-go/deepseek-v4.1-flash` matrix has 114/114 structurally valid active records across 6 variants × 19 scenarios, but only one attempt per cell. It therefore **does not satisfy** the five-valid-attempt statistical completion rule above.

That campaign is formally accepted only as broad diagnostic evidence. It is not statistical benchmark completion, not a resistance probability estimate, and not a release gate. The five-valid-attempt requirement remains the correct standard for any future release-oriented statistical benchmark campaign.
