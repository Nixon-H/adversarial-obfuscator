# CLI Flag Audit

**Generated:** 2026-11-10 from the live parsers (`scripts/build.py` and
`obfuscator/core/pipeline.py`). **Status:** current inventory; regenerate after
adding flags. **Audited:** 2026-11-12 every flag was re-verified against its
code path (see "Implementation audit" below).

`Parser` says which entry point accepts the option. `both` means both do, but
not necessarily with the same behaviour; see the cross-pipeline table in
[`SECURITY_FEATURES.md`](SECURITY_FEATURES.md). `Default` is the parser default,
not the effective value after the opt-level ladder resolves. When a flag is
accepted by both parsers and their defaults differ, the table shows the
`build.py` default; the loader default is in the cross-pipeline table.
`Objective` is the primary security objective; a flag may serve more than one.

## Unified flags (the only interface since 2026-11-12)

Two one-flag namespaces replace the per-knob spelling. Sub-options land on
the parser destinations the consumers read (obfuscator/core/pipeline.py
`apply_unified_specs`). The former per-knob spellings were **removed** on
2026-11-12 — they are no longer accepted, and tests reject them
(`tests/test_unified_flags.py::test_removed_legacy_spellings_are_rejected`).
The tables below are the pre-consolidation inventory (2026-11-10); entries
for the removed spellings are historical.

| Unified flag | Sub-options | Replaces (removed) |
|---|---|---|
| `--web3` | `rpc=URL` `explorer=URL` `contract=ADDR` `shards=URL1,URL2` `deploy` `deploy-rpc=URL` | contract/rpc/shards/auto-deploy/deploy-rpc/explorer |
| `--licence` | `token=FILE` `env-only` `bootstrap-encrypted` `chain` | the four licence-prefixed spellings |
| `--access` | `hwid=STR` `hwid-lock` `lock-hwid=STR` `trial=7d` `expire=DATE` `bind-mac` `one-shot` `kod` `hostguard` `driver-check` `name-gate` `rename-internal` `allow-countries=…` `block-countries=…` `allow-regions=…` `block-regions=…` `webhook=URL` `net-url=URL` | the 18 per-knob access-gate spellings (hwid, trial, expire, kod, hostguard, hwid-lock, driver-check, name-gate, rename-internal, lock-hwid, bind-mac, one-shot, allow/block-countries, allow/block-regions, webhook, net-url) |

`scripts/build.py` keeps its own copies of several loader-only names so its
refusal message ("this pipeline emits no hybrid loader") still reaches the
operator; those are refused there, not functional, and are not the interface.

**Default-on change (2026-11-12):** the split-bootstrap key (Shamir n=3,k=2
threshold + fragmented decoder) is now ON in every loader build. The enable
flag was removed; `--no-split-bootstrap` is the opt-out — the same shape as
`--section-split`/`--no-section-split`. Verified with a complete-security
build: the artefact builds and runs with the split bootstrap.

**Deception/provenance merged into the counter-REA gate (2026-11-12).** The
25 per-knob deception flags (poison-*, provenance-*, honey-functions,
decoy-apis/count, llm-resilient(+depth,vars), attention-poison,
reasoning-traps/trap-depth, storyline-count, multi-agent-deception,
manipulation-detector, prompt-resistance, red-team(+output), self-critique,
false-confidence-audit) were **removed** from `scripts/build.py`. One gate
replaces them: `--anti-rea-level {stealth,balanced,maximum}` (default
**maximum**, ON), `--no-anti-rea` to disable everything, and one exclusion
list `--exclude-rea poison,honey,decoy,attention,traps,storyline,
llm-resilient,red-team,self-critique,manipulation,prompt,false-confidence,
multi-agent`. `_apply_rea_shields` computes the removed destinations before
any phase reads them, so the phases are unchanged. Note: with maximum as the
default, every native build now emits the deception layers (poison, honey
functions, decoys, traps) and runs the red-team/self-critique reports; use
`--exclude-rea` for any layer you do not want.

The licence identity gate is `--licence … chain` (signed ERC-721
verification); the `--web3` sub-options drive the *other* Web3 machinery
(runtime `eth_call` licence check, Shamir key-shard fetch, contract
deployment) and are not the licence gate. Cloudflare worker deployment
(`--cf-token` / `--cf-account`) and network auth (`--net-url`) stay
separate: they belong to the `auth` command's subsystem, not the Ethereum
licence/Web3 path.

Four true alias flags were also **removed** (no behaviour lost — the
canonical flag keeps everything, including the Item-126 hybrid demo):
poison-all → `--provenance-poison`, gpu → `--gpu-execution`,
cpu-gpu-hybrid → `--gpu-hybrid`, advanced-protection → `--phase2`.

## Namespace flags — the whole CLI in four more flags (2026-11-12)

The report and research phases no longer have one flag each. They are named
entries of two namespaces, and every removed flag's old spelling is rejected:

| Namespace | What it does | Examples |
|---|---|---|
| `--audit NAME…` | run report/verification phases | `--audit reality-score security-gates proof-coverage`<br>`--audit all confidence-level=0.99` |
| `--research NAME…` | run experimental phases that write `build/` sidecars | `--research cfg-mutation code-genome tee`<br>`--research fragment fragment-size=12` |
| `--skip STAGE…` | skip build stages | `--skip llvmgen extras generate-payload-h` |
| `--exclude FAMILY…` | skip shield families | `--exclude rea` (all), `--exclude rea.cognitive rea.bio` |

The names are the old flag names without the leading `--`; `--audit all` /
`--research all` run everything. `key=value` entries tune a phase
(`--audit gate-threshold=0.8`, `--research tee-type=sgx`). Both CLIs accept the
same `--exclude` syntax: `rea`, `rea.poison`, `rea.honey`, `rea.decoy`,
`rea.attention`, `rea.traps`, `rea.storyline`, `rea.llm-resilient`,
`rea.red-team`, `rea.self-critique`, `rea.manipulation`, `rea.prompt`,
`rea.false-confidence`, `rea.multi-agent`, `rea.adversarial` (native build);
`rea`, `rea.cognitive`, `rea.compliance`, `rea.bio` (loader build).

**Result:** `scripts/build.py` went from **243 options to 30**, the loader CLI
from **74 to 30**; the distinct union is **50 — half the 100 target**. Every
removed destination still exists (defaulted by the namespace appliers), so
phase code is unchanged. The six positive transform flags were removed because
they already default ON; their `--no-` opt-outs remain. Advanced protection is
**default-on** (disable with `--exclude advanced-protection`); adversarial
injection folded into the counter-REA gate as the `adversarial` family.
Packaging is `--package` (pytoc, pyinstaller, cross=, native, compile, cloud,
layers=, zips=, stego, portable) and the opt-in passes are `--transforms`
(data, data-level=, function-intent, speculation, struct, struct-level=,
seed=). `--validate fail` replaces the old abort flag, `--licence salt=`
replaces `--customer-salt`, and `--access vm-threshold=` replaces
`--vm-threshold`.

## False-security fixes (2026-11-12)

Three flags were accepted but did nothing at run time; all three now do what
their help text claimed:

- **`--block-countries` / `--block-regions`: now enforced.** The values were
  substituted into the loader but the `Geofence` class only accepted
  allow-lists. The class now takes and enforces blocked lists (tests:
  `tests/test_geofence_blocked.py`).
- **`--expire`: now enforced.** The date was embedded into `VAR_EXP_DATE` and
  read by nothing. The boot sequence now compares the wall clock to the date
  and follows the sibling-gate pattern: hash-chain divergence in signal mode,
  exit 137 under `--strict-detections`.

## Security by default — what is already on, and what stays opt-in

Verified against the code paths (2026-11-12), not just parser defaults:

**Already on in every normal build — no change needed:**

- The six canonical AST transforms (`--cfg-flatten`, `--mba-subs`,
  `--opaque-predicates`, `--fragment-strings`, `--unicode-ids`,
  `--bogus-exceptions`): ON in `scripts/build.py` (default True), hardcoded ON
  on the pipeline `build` path, and kept ON for O1+ by the `--opt-level` ladder.
- Counter-REA shields (`--anti-rea`): ON by default; `--no-anti-rea` is the
  opt-out.
- Sectioned payload sealing (`--section-split`): ON by default.
- Strict detections (`--strict-detections`, i.e. NOT `--fast`): ON by default;
  `--fast` is its opt-out twin and prints a reduced-posture warning.
- Audit-hook plant detector, frozen-stdlib snapshot gate, stdlib function-audit
  gate: all planted/armed by default; `--no-audit-hook-plant`, `--no-snapshot`,
  `--no-stdlib-audit` are the opt-outs.
- Post-build verification suite (PHASE 3): runs on every pipeline build unless
  `--one-shot` skips it, and fails the build on real output divergence.

**Deliberately opt-in — flipping them on would break correct use:**

- Access gates (`--hwid`, `--hwid-lock`, `--trial`, `--kod`, `--hostguard`,
  `--name-gate`, `--lock-hwid`, `--bind-mac`): machine binding and
  kill-on-detect cannot be universal defaults — they would break portability
  and kill legitimate runs on false positives. Without the flag the emitted
  gate is explicitly DISABLED.
- Geofence (`--allow/block-countries/regions`) and `--expire`: network- and
  clock-dependent checks, opt-in by nature.
- Licence binding (`--licence token=…`): requires an issued token per
  customer; it is a capability, not a global switch.
- Split-bootstrap key: **now default-on** (2026-11-12); `--no-split-bootstrap`
  is the opt-out. It was opt-in until a complete-security build verified the
  split key + fragmented decoder runs.

**Net:** the audit found no protection that was default-off and safe to flip
on; the gaps were flags that did nothing (fixed above) and one inert
`--crypto-binding` suspicion that the code disproved (it is build-time only,
but it does run).

## Implementation audit (2026-11-12)

Every flag destination in the tables below was re-verified against the code
paths — consumers traced through `args.<dest>` / `getattr(args, …)` reads,
config-dict copies followed one hop, and build/ JSON outputs checked for a
reader. Coverage: 327 flag destinations across both parsers.

| Status | Count | Meaning |
|---|---|---|
| ACTIVE | 226 | consumed; changes the artefact, runtime behaviour, or an operator-readable report |
| PARTIAL | 54 | consumed on one path only (native/hybrid, loader-only) or only when its parent flag is set — parameters, not dead flags |
| REDUNDANT | 7 | alias of another flag (same dest or identical branch); all 4 true aliases **removed 2026-11-12**, the 3 opt-out twins remain |
| INERT | 40 | consumed but lands only in build/ JSON nothing reads back, or a demo/simulation with no artefact effect |
| DEAD | 0 | parsed but never consumed |

**REDUNDANT aliases — all 4 true aliases REMOVED 2026-11-12** (the canonical
flag keeps every behaviour): poison-all (→ `--provenance-poison`), gpu (→
`--gpu-execution`), cpu-gpu-hybrid (→ `--gpu-hybrid`, including the Item-126
demo the alias alone triggered), advanced-protection (→ `--phase2`). The
remaining 3 of the 7 "redundant" pairs are normal argparse opt-out twins,
not aliases, and stay: `--no-anti-rea` (twin of `--anti-rea`),
`--no-generate-payload-h` (twin of `--generate-payload-h`), `--fast`
(opt-out twin of `--strict-detections`).

**INERT flags (40).** Each runs a build-time phase that writes a `build/`
JSON or a demo that never reaches the artefact. All are marked
`**Inert.**`/`**Metadata-only.**` in the generated CLI reference. The list:

`--cfg-mutation` · `--cfg-mutation-variants` · `--class-dispatch` ·
`--class-dispatch-count` · `--ssa-mutation` · `--state-isa` ·
`--state-isa-history-len` · `--temporal-keys` · `--temporal-window` ·
`--per-exec-recompile` · `--self-healing` · `--oram` · `--poly-engine` ·
`--flow-entangle` · `--remote-unlock` · `--remote-unlock-ttl` ·
`--attestation` · `--challenge-response` · `--dist-attestation` ·
`--dist-attestation-nodes` · `--dist-diversity-nodes` ·
`--dist-diversity-rotation` · `--dist-diversity-variants` ·
`--distributed-mode` · `--distributed-vm` · `--cross-process` · `--fragment` ·
`--fragment-functions` · `--fragment-size` · `--fragment-migration` ·
`--micro-fragment` · `--micro-fragment-size` · `--microjit` · `--multi-host` ·
`--multi-host-count` · `--payload-dispersal` · `--dispersal-slices` ·
`--recovery-prevention` · `--recovery-prevention-nodes` · `--rolling-keys` ·
`--ephemeral-isa`

Two earlier "inert" suspicions were disproved by the code and corrected:
`--crypto-binding` (build-time fragment validation, ACTIVE on its path) and
`--self-healing` stayed inert.

**Decision on the INERT set:** they are research/simulation phases kept for
compatibility and documentation honesty, not removed — deleting them would
discard recorded research machinery (`docs/FLAG_AUDIT.md` history and the
bench tests under `tests/bench_*` cover several). None provides runtime
security; none is enabled by default; each is labelled at the point a reader
actually looks: the generated reference table.

**PARTIAL flags worth knowing about (54):** most are parameters of a parent
flag (`--decoy-api-count` needs `--decoy-apis`, `--genome-generations` needs
`--code-genome`, …) and `scripts/build.py` already warns when a parameter is
set without its parent ("dangling use"). The loader-only ones
(`--hwid`, `--trial`, `--kod`, `--hostguard`, `--hwid-lock`,
`--split-bootstrap`, `--vm-threshold`, `--customer-salt`, `--no-snapshot`,
`--no-stdlib-audit`, `--no-audit-hook-plant`, …) are refused or warned on the
`scripts/build.py` native path with a pointer to
`python3 -m obfuscator.core.pipeline build`, the only entry point that emits
the loader that implements them.

**The verification / assurance set (67 report flags) is real machinery:** all
but their parameter flags are ACTIVE report generators
(`phase_assumptions`, `phase_reality`, `phase_security_gates`, …) with bench
tests under `tests/bench_*`; they write operator-readable reports and several
feed each other (`evidence_ledger` → release-confidence/self-critique;
`security_gates` → reality score). They are assurance tooling, not runtime
protections, and correctly cost nothing at artefact run time.



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
| `--licence-bootstrap-encrypted` | loader | `False` | Licensing / access gates |
| `--licence-chain` | loader | `False` | Licensing / access gates |
| `--licence-env-only` | loader | `False` | Licensing / access gates |
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

