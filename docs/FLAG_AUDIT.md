# CLI Flag Audit

**Generated:** 2026-11-10 from the live parsers (`scripts/build.py` and
`obfuscator/core/pipeline.py`). **Status:** current inventory; regenerate after
adding flags.

`Parser` says which entry point accepts the option. `both` means both do, but
not necessarily with the same behaviour; see the cross-pipeline table in
[`SECURITY_FEATURES.md`](SECURITY_FEATURES.md). `Default` is the parser default,
not the effective value after the opt-level ladder resolves. When a flag is
accepted by both parsers and their defaults differ, the table shows the
`build.py` default; the loader default is in the cross-pipeline table.
`Objective` is the primary security objective; a flag may serve more than one.

## Counter-REA / deception (31)

| Flag | Parser | Default | Objective |
|---|---|---|---|
| `--adaptive-adversarial` | build.py | `` | Counter-REA / deception |
| `--adversarial-level` | build.py | `3` | Counter-REA / deception |
| `--anti-rea` | loader | `True` | Counter-REA / deception |
| `--anti-rea-level` | loader | `'balanced'` | Counter-REA / deception |
| `--attention-poison` | build.py | `0` | Counter-REA / deception |
| `--decoy-api-count` | build.py | `5` | Counter-REA / deception |
| `--decoy-apis` | build.py | `` | Counter-REA / deception |
| `--exclude-rea` | loader | `False` | Counter-REA / deception |
| `--exclude-rea-cognitive` | loader | `False` | Counter-REA / deception |
| `--exclude-rea-compliance` | loader | `False` | Counter-REA / deception |
| `--false-confidence-audit` | build.py | `` | Counter-REA / deception |
| `--honey-functions` | build.py | `0` | Counter-REA / deception |
| `--llm-resilient` | build.py | `` | Counter-REA / deception |
| `--llm-resilient-depth` | build.py | `15` | Counter-REA / deception |
| `--llm-resilient-vars` | build.py | `50` | Counter-REA / deception |
| `--manipulation-detector` | build.py | `` | Counter-REA / deception |
| `--multi-agent-deception` | build.py | `` | Counter-REA / deception |
| `--no-anti-rea` | loader | `` | Counter-REA / deception |
| `--poison-all` | build.py | `` | Counter-REA / deception |
| `--poison-apis` | build.py | `` | Counter-REA / deception |
| `--poison-call-graph` | build.py | `` | Counter-REA / deception |
| `--poison-imports` | build.py | `` | Counter-REA / deception |
| `--poison-paths` | build.py | `` | Counter-REA / deception |
| `--poison-protocols` | build.py | `` | Counter-REA / deception |
| `--prompt-resistance` | build.py | `` | Counter-REA / deception |
| `--reasoning-traps` | build.py | `` | Counter-REA / deception |
| `--red-team` | build.py | `` | Counter-REA / deception |
| `--red-team-output` | build.py | `'build/redteam'` | Counter-REA / deception |
| `--self-critique` | build.py | `` | Counter-REA / deception |
| `--storyline-count` | build.py | `3` | Counter-REA / deception |
| `--trap-depth` | build.py | `5` | Counter-REA / deception |

## Cryptographic / key handling (2)

| Flag | Parser | Default | Objective |
|---|---|---|---|
| `--flow-entangle` | build.py | `` | Cryptographic / key handling |
| `--sign-key-env` | build.py | `''` | Cryptographic / key handling |

## Fragmentation / execution (30)

| Flag | Parser | Default | Objective |
|---|---|---|---|
| `--cross-process` | build.py | `` | Fragmentation / execution |
| `--dispersal-slices` | build.py | `3` | Fragmentation / execution |
| `--dist-diversity` | build.py | `` | Fragmentation / execution |
| `--dist-diversity-nodes` | build.py | `4` | Fragmentation / execution |
| `--dist-diversity-rotation` | build.py | `3600.0` | Fragmentation / execution |
| `--dist-diversity-variants` | build.py | `8` | Fragmentation / execution |
| `--distributed-mode` | build.py | `'simulation'` | Fragmentation / execution |
| `--distributed-vm` | build.py | `` | Fragmentation / execution |
| `--ephemeral-isa` | build.py | `` | Fragmentation / execution |
| `--fragment` | build.py | `` | Fragmentation / execution |
| `--fragment-functions` | build.py | `` | Fragmentation / execution |
| `--fragment-migration` | build.py | `` | Fragmentation / execution |
| `--fragment-size` | build.py | `5` | Fragmentation / execution |
| `--micro-fragment` | build.py | `` | Fragmentation / execution |
| `--micro-fragment-size` | build.py | `64` | Fragmentation / execution |
| `--microjit` | build.py | `` | Fragmentation / execution |
| `--multi-binary` | build.py | `` | Fragmentation / execution |
| `--multi-binary-num` | build.py | `4` | Fragmentation / execution |
| `--multi-host` | build.py | `` | Fragmentation / execution |
| `--multi-host-count` | build.py | `3` | Fragmentation / execution |
| `--payload-dispersal` | build.py | `` | Fragmentation / execution |
| `--recovery-prevention` | build.py | `` | Fragmentation / execution |
| `--recovery-prevention-nodes` | build.py | `5` | Fragmentation / execution |
| `--rop` | build.py | `` | Fragmentation / execution |
| `--section-count` | loader | `4` | Fragmentation / execution |
| `--section-split` | loader | `True` | Fragmentation / execution |
| `--simd-vm` | build.py | `` | Fragmentation / execution |
| `--skip-llvmgen` | build.py | `` | Fragmentation / execution |
| `--split-bootstrap` | both | `False` | Fragmentation / execution |
| `--vm-threshold` | both | `50.0` | Fragmentation / execution |

## Inert / metadata-only (11)

| Flag | Parser | Default | Objective |
|---|---|---|---|
| `--cfg-mutation` | build.py | `` | Inert / metadata-only |
| `--class-dispatch` | build.py | `` | Inert / metadata-only |
| `--class-dispatch-count` | build.py | `4` | Inert / metadata-only |
| `--crypto-binding` | build.py | `` | Inert / metadata-only |
| `--per-exec-recompile` | build.py | `` | Inert / metadata-only |
| `--self-healing` | build.py | `` | Inert / metadata-only |
| `--ssa-mutation` | build.py | `` | Inert / metadata-only |
| `--state-isa` | build.py | `` | Inert / metadata-only |
| `--state-isa-history-len` | build.py | `8` | Inert / metadata-only |
| `--temporal-keys` | build.py | `` | Inert / metadata-only |
| `--temporal-window` | build.py | `60.0` | Inert / metadata-only |

## Licensing / access gates (31)

| Flag | Parser | Default | Objective |
|---|---|---|---|
| `--allow-countries` | loader | `` | Licensing / access gates |
| `--allow-regions` | loader | `` | Licensing / access gates |
| `--auto-deploy` | loader | `` | Licensing / access gates |
| `--bind-mac` | loader | `` | Licensing / access gates |
| `--block-countries` | loader | `` | Licensing / access gates |
| `--block-regions` | loader | `` | Licensing / access gates |
| `--cf-account` | loader | `` | Licensing / access gates |
| `--cf-token` | loader | `` | Licensing / access gates |
| `--contract` | loader | `` | Licensing / access gates |
| `--customer-salt` | both | `''` | Licensing / access gates |
| `--deploy-rpc` | loader | `` | Licensing / access gates |
| `--expire` | loader | `` | Licensing / access gates |
| `--explorer` | loader | `` | Licensing / access gates |
| `--hostguard` | both | `False` | Licensing / access gates |
| `--hwid` | both | `''` | Licensing / access gates |
| `--hwid-lock` | both | `False` | Licensing / access gates |
| `--kod` | both | `False` | Licensing / access gates |
| `--licence-token` | loader | `''` | Licensing / access gates |
| `--lock-hwid` | loader | `''` | Licensing / access gates |
| `--name-gate` | both | `False` | Licensing / access gates |
| `--net-url` | loader | `` | Licensing / access gates |
| `--one-shot` | loader | `` | Licensing / access gates |
| `--private-key` | loader | `` | Licensing / access gates |
| `--remote-unlock` | build.py | `` | Licensing / access gates |
| `--remote-unlock-ttl` | build.py | `30.0` | Licensing / access gates |
| `--rename-internal` | both | `False` | Licensing / access gates |
| `--rpc` | loader | `` | Licensing / access gates |
| `--shards` | loader | `` | Licensing / access gates |
| `--token-file` | loader | `` | Licensing / access gates |
| `--trial` | both | `''` | Licensing / access gates |
| `--webhook` | loader | `` | Licensing / access gates |

## Operational / reporting (33)

| Flag | Parser | Default | Objective |
|---|---|---|---|
| `--advanced-protection-only` | build.py | `` | Operational / reporting |
| `--artifacts-output` | build.py | `'build/artifacts'` | Operational / reporting |
| `--bind` | loader | `` | Operational / reporting |
| `--coverage-output` | build.py | `None` | Operational / reporting |
| `--diversity-dir` | build.py | `'build/variants'` | Operational / reporting |
| `--diversity-report` | build.py | `` | Operational / reporting |
| `--eval-summary` | build.py | `` | Operational / reporting |
| `--evaluate` | build.py | `` | Operational / reporting |
| `--exclude-android` | loader | `` | Operational / reporting |
| `--force-output` | build.py | `False` | Operational / reporting |
| `--help` | loader | `<expr>` | Operational / reporting |
| `--include-original` | build.py | `` | Operational / reporting |
| `--knowledge-graph-output` | build.py | `None` | Operational / reporting |
| `--no-section-split` | loader | `` | Operational / reporting |
| `--output` | both | `` | Operational / reporting |
| `--payload` | both | `` | Operational / reporting |
| `--pin-structure` | loader | `` | Operational / reporting |
| `--public` | loader | `` | Operational / reporting |
| `--python` | loader | `<expr>` | Operational / reporting |
| `--resume` | loader | `` | Operational / reporting |
| `--silent-fallback` | build.py | `` | Operational / reporting |
| `--skip-conflict-check` | build.py | `` | Operational / reporting |
| `--skip-encrypt` | build.py | `` | Operational / reporting |
| `--skip-extras` | build.py | `` | Operational / reporting |
| `--skip-irgen` | build.py | `` | Operational / reporting |
| `--skip-obfuscate` | build.py | `` | Operational / reporting |
| `--skip-relay` | build.py | `` | Operational / reporting |
| `--tls-ca-bundle` | loader | `` | Operational / reporting |
| `--tor` | loader | `` | Operational / reporting |
| `--tor-proxy` | loader | `None` | Operational / reporting |
| `--update-baseline` | build.py | `` | Operational / reporting |
| `--verification-bundle-output` | build.py | `None` | Operational / reporting |
| `--version` | build.py | `` | Operational / reporting |

## Packaging / native (20)

| Flag | Parser | Default | Objective |
|---|---|---|---|
| `--auto` | loader | `` | Packaging / native |
| `--compile` | loader | `` | Packaging / native |
| `--cross` | build.py | `` | Packaging / native |
| `--debug-dump-raw` | loader | `False` | Packaging / native |
| `--generate-payload-h` | build.py | `True` | Packaging / native |
| `--layers` | loader | `` | Packaging / native |
| `--native` | loader | `` | Packaging / native |
| `--native-only` | loader | `` | Packaging / native |
| `--no-generate-payload-h` | build.py | `` | Packaging / native |
| `--phase2-extras` | build.py | `` | Packaging / native |
| `--platform` | loader | `'auto'` | Packaging / native |
| `--portable` | loader | `False` | Packaging / native |
| `--pyinstaller-spec` | build.py | `` | Packaging / native |
| `--python-dll` | build.py | `` | Packaging / native |
| `--pytoc` | build.py | `` | Packaging / native |
| `--pytoc-out` | build.py | `''` | Packaging / native |
| `--rust-exe` | build.py | `` | Packaging / native |
| `--skip-cloud` | loader | `` | Packaging / native |
| `--stego` | loader | `` | Packaging / native |
| `--zips` | loader | `` | Packaging / native |

## Research / experimental (42)

| Flag | Parser | Default | Objective |
|---|---|---|---|
| `--adaptive` | build.py | `` | Research / experimental |
| `--adaptive-classifier-loop` | build.py | `` | Research / experimental |
| `--adversarial-bench` | build.py | `` | Research / experimental |
| `--adversarial-bench-count` | build.py | `20` | Research / experimental |
| `--adversarial-loop` | build.py | `` | Research / experimental |
| `--ai-guided-diversity` | build.py | `` | Research / experimental |
| `--apply-synthesis` | build.py | `` | Research / experimental |
| `--classify` | build.py | `` | Research / experimental |
| `--classify-features` | build.py | `` | Research / experimental |
| `--code-genome` | build.py | `` | Research / experimental |
| `--cpu-gpu-hybrid` | build.py | `` | Research / experimental |
| `--cpu-port` | build.py | `` | Research / experimental |
| `--deobfuscation-threshold` | build.py | `0.7` | Research / experimental |
| `--diversity` | build.py | `None` | Research / experimental |
| `--diversity-threshold` | build.py | `0.3` | Research / experimental |
| `--evolution-generations` | build.py | `3` | Research / experimental |
| `--evolution-iterations` | build.py | `1` | Research / experimental |
| `--exclude-rea-bio` | loader | `False` | Research / experimental |
| `--fhe-vm` | build.py | `` | Research / experimental |
| `--fhe-vm-functions` | build.py | `` | Research / experimental |
| `--generate-artifacts` | build.py | `` | Research / experimental |
| `--genome-generations` | build.py | `50` | Research / experimental |
| `--genome-population` | build.py | `30` | Research / experimental |
| `--gpu` | build.py | `` | Research / experimental |
| `--gpu-execution` | build.py | `` | Research / experimental |
| `--gpu-hybrid` | build.py | `` | Research / experimental |
| `--hpc` | build.py | `` | Research / experimental |
| `--hpc-key` | build.py | `` | Research / experimental |
| `--io-research` | build.py | `` | Research / experimental |
| `--io-research-functions` | build.py | `` | Research / experimental |
| `--kernel-assist` | build.py | `` | Research / experimental |
| `--kernel-assist-features` | build.py | `` | Research / experimental |
| `--oram` | build.py | `` | Research / experimental |
| `--sgx` | build.py | `` | Research / experimental |
| `--synthesis` | build.py | `` | Research / experimental |
| `--synthesis-max-overhead` | build.py | `50.0` | Research / experimental |
| `--synthesis-max-size` | build.py | `3.0` | Research / experimental |
| `--synthesis-output` | build.py | `None` | Research / experimental |
| `--synthesis-target-security` | build.py | `70.0` | Research / experimental |
| `--tee` | build.py | `` | Research / experimental |
| `--tee-type` | build.py | `'software'` | Research / experimental |
| `--uarch-diversity` | build.py | `` | Research / experimental |

## Runtime integrity / anti-tamper (16)

| Flag | Parser | Default | Objective |
|---|---|---|---|
| `--attestation` | build.py | `` | Runtime integrity / anti-tamper |
| `--benchmark-integrity` | build.py | `` | Runtime integrity / anti-tamper |
| `--challenge-response` | build.py | `` | Runtime integrity / anti-tamper |
| `--claim-audit` | build.py | `` | Runtime integrity / anti-tamper |
| `--dist-attestation` | build.py | `` | Runtime integrity / anti-tamper |
| `--dist-attestation-nodes` | build.py | `5` | Runtime integrity / anti-tamper |
| `--driver-check` | both | `False` | Runtime integrity / anti-tamper |
| `--fast` | loader | `` | Runtime integrity / anti-tamper |
| `--history-bound-decryption` | build.py | `` | Runtime integrity / anti-tamper |
| `--invariant-engine` | build.py | `` | Runtime integrity / anti-tamper |
| `--no-audit-hook-plant` | both | `False` | Runtime integrity / anti-tamper |
| `--no-snapshot` | both | `False` | Runtime integrity / anti-tamper |
| `--no-stdlib-audit` | both | `False` | Runtime integrity / anti-tamper |
| `--rolling-keys` | build.py | `` | Runtime integrity / anti-tamper |
| `--self-audit` | build.py | `` | Runtime integrity / anti-tamper |
| `--strict-detections` | loader | `True` | Runtime integrity / anti-tamper |

## Static code obfuscation (30)

| Flag | Parser | Default | Objective |
|---|---|---|---|
| `--advanced-protection` | build.py | `` | Static code obfuscation |
| `--adversarial-injection` | build.py | `` | Static code obfuscation |
| `--bogus-exceptions` | both | `True` | Static code obfuscation |
| `--build-id` | build.py | `''` | Static code obfuscation |
| `--cfg-flatten` | both | `True` | Static code obfuscation |
| `--cfg-mutation-variants` | build.py | `4` | Static code obfuscation |
| `--data-obf-level` | build.py | `3` | Static code obfuscation |
| `--data-obfuscation` | build.py | `` | Static code obfuscation |
| `--fragment-strings` | both | `True` | Static code obfuscation |
| `--function-intent` | build.py | `` | Static code obfuscation |
| `--lowering` | both | `''` | Static code obfuscation |
| `--mba-subs` | both | `True` | Static code obfuscation |
| `--no-bogus-exceptions` | build.py | `` | Static code obfuscation |
| `--no-cfg-flatten` | build.py | `` | Static code obfuscation |
| `--no-fragment-strings` | build.py | `` | Static code obfuscation |
| `--no-mba-subs` | build.py | `` | Static code obfuscation |
| `--no-opaque-predicates` | build.py | `` | Static code obfuscation |
| `--no-unicode-ids` | build.py | `` | Static code obfuscation |
| `--opaque-predicates` | both | `True` | Static code obfuscation |
| `--opt-level` | both | `4` | Static code obfuscation |
| `--phase2` | build.py | `` | Static code obfuscation |
| `--phase2-only` | build.py | `` | Static code obfuscation |
| `--poly-engine` | build.py | `` | Static code obfuscation |
| `--randomization-level` | build.py | `3` | Static code obfuscation |
| `--randomization-seed` | build.py | `None` | Static code obfuscation |
| `--seed` | build.py | `None` | Static code obfuscation |
| `--speculation-obfuscation` | build.py | `` | Static code obfuscation |
| `--ssa-variants` | build.py | `4` | Static code obfuscation |
| `--struct-randomization` | build.py | `` | Static code obfuscation |
| `--unicode-ids` | both | `True` | Static code obfuscation |

## Verification / assurance (67)

| Flag | Parser | Default | Objective |
|---|---|---|---|
| `--analyst-time` | build.py | `` | Verification / assurance |
| `--assumptions-report` | build.py | `` | Verification / assurance |
| `--attack-corpus` | build.py | `` | Verification / assurance |
| `--attack-store` | build.py | `'build/attacks'` | Verification / assurance |
| `--attack-surface` | build.py | `` | Verification / assurance |
| `--audit-drift` | build.py | `` | Verification / assurance |
| `--benchmark` | build.py | `` | Verification / assurance |
| `--benchmark-model` | build.py | `None` | Verification / assurance |
| `--benchmark-report` | build.py | `` | Verification / assurance |
| `--capture-attacks` | build.py | `` | Verification / assurance |
| `--confidence-interval` | build.py | `` | Verification / assurance |
| `--confidence-level` | build.py | `0.95` | Verification / assurance |
| `--context-saturation` | build.py | `` | Verification / assurance |
| `--cost-model` | build.py | `` | Verification / assurance |
| `--coverage-map` | build.py | `` | Verification / assurance |
| `--dependency-graph` | build.py | `` | Verification / assurance |
| `--diagnostic` | build.py | `False` | Verification / assurance |
| `--embed-proof` | build.py | `` | Verification / assurance |
| `--emit-certificates` | build.py | `` | Verification / assurance |
| `--evidence-completeness` | build.py | `` | Verification / assurance |
| `--evidence-ledger` | build.py | `` | Verification / assurance |
| `--feature-effectiveness` | build.py | `` | Verification / assurance |
| `--gate-threshold` | build.py | `None` | Verification / assurance |
| `--independent-audit` | build.py | `` | Verification / assurance |
| `--knowledge-base` | build.py | `` | Verification / assurance |
| `--knowledge-graph` | build.py | `` | Verification / assurance |
| `--longitudinal-tracking` | build.py | `` | Verification / assurance |
| `--max-cpu-overhead` | build.py | `20.0` | Verification / assurance |
| `--max-size-mult` | build.py | `3.0` | Verification / assurance |
| `--metrics` | build.py | `` | Verification / assurance |
| `--min-resilience` | build.py | `None` | Verification / assurance |
| `--min-security` | build.py | `0.5` | Verification / assurance |
| `--multi-tool` | build.py | `` | Verification / assurance |
| `--optimize` | build.py | `` | Verification / assurance |
| `--plaintext-exposure` | build.py | `` | Verification / assurance |
| `--proof-aware-optimizer` | build.py | `` | Verification / assurance |
| `--proof-carrying` | build.py | `` | Verification / assurance |
| `--proof-coverage` | build.py | `` | Verification / assurance |
| `--proof-soundness` | build.py | `` | Verification / assurance |
| `--protection-roi` | build.py | `` | Verification / assurance |
| `--prove-fragments` | build.py | `` | Verification / assurance |
| `--prove-vm` | build.py | `` | Verification / assurance |
| `--reachability-report` | build.py | `` | Verification / assurance |
| `--reality-score` | build.py | `` | Verification / assurance |
| `--release-confidence` | build.py | `` | Verification / assurance |
| `--replay-attacks` | build.py | `` | Verification / assurance |
| `--reproducibility-score` | build.py | `` | Verification / assurance |
| `--require-live-features` | build.py | `None` | Verification / assurance |
| `--retirement-report` | build.py | `` | Verification / assurance |
| `--runtime-truth` | build.py | `` | Verification / assurance |
| `--security-debt` | build.py | `` | Verification / assurance |
| `--security-gates` | build.py | `` | Verification / assurance |
| `--semantic-leakage` | build.py | `` | Verification / assurance |
| `--survivability` | build.py | `` | Verification / assurance |
| `--threat-coverage` | build.py | `` | Verification / assurance |
| `--trust-boundary` | build.py | `` | Verification / assurance |
| `--validate` | build.py | `` | Verification / assurance |
| `--validate-fail` | build.py | `` | Verification / assurance |
| `--verification-bundle` | build.py | `` | Verification / assurance |
| `--verification-diversity` | build.py | `` | Verification / assurance |
| `--verify-jit` | build.py | `` | Verification / assurance |
| `--verify-mba` | build.py | `` | Verification / assurance |
| `--verify-mutations` | build.py | `` | Verification / assurance |
| `--verify-preservation` | build.py | `` | Verification / assurance |
| `--verify-preservation-formal` | build.py | `` | Verification / assurance |
| `--zk-state` | build.py | `` | Verification / assurance |
| `--zk-state-config` | build.py | `` | Verification / assurance |

## Watermark / provenance (11)

| Flag | Parser | Default | Objective |
|---|---|---|---|
| `--dist-watermark` | build.py | `` | Watermark / provenance |
| `--dist-watermark-shares` | build.py | `5` | Watermark / provenance |
| `--fingerprint-model` | build.py | `'gpt'` | Watermark / provenance |
| `--llm-fingerprint` | build.py | `` | Watermark / provenance |
| `--poison-level` | build.py | `0` | Watermark / provenance |
| `--provenance-poison` | build.py | `` | Watermark / provenance |
| `--provenance-replace` | build.py | `` | Watermark / provenance |
| `--uarch-watermark` | build.py | `` | Watermark / provenance |
| `--verify-watermark` | build.py | `` | Watermark / provenance |
| `--verify-watermark-survivability` | build.py | `` | Watermark / provenance |
| `--watermark` | both | `None` | Watermark / provenance |

