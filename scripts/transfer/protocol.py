"""G2 transfer-resistance protocol, frozen as code (do not edit lightly).

Frozen experiment specification (agreed 2026-09-28; any change requires a
dated amendment note in this docstring and a SPEC_VERSION bump):

  H1: Heterogeneous transformation selection reduces cross-build attack
      transfer relative to seed-only diversification.
  H0: No measurable difference in transfer.

  Primary attack: portable attack artifact (Phase 1: deterministic static
      arm; Ghidra arm where toolchain allows).
  Primary endpoint: S_cfg (spec §measure).
  Controls: (1) unprotected Python, (2) seed-only diversification,
      (3) heterogeneous diversification.
  Reporting: T matrix, confidence intervals, structural-diversity matrix,
      semantic-equivalence failures, attack success/failure, execution
      time, build overhead.
  Falsification: if heterogeneous diversification does not produce a
      statistically distinguishable transfer distribution from the
      seed-only control, do NOT claim transfer resistance.

Anti-tuning rule: pass_sets are frozen per corpus program in
``corpus/*/config.json``. Every report embeds
``config_freeze_hash`` = sha256 of the canonical pass-set config. Any
report whose hash differs from the frozen value is a *different*
experiment, not a replication. Do not tune pass sets after seeing T.

Corpus discipline: ``held_out/`` programs must not inform planner
calibration, resilience-model training, or pass-set choice. G2 trains
nothing, but the directory split is load-bearing for G1.
"""

SPEC_VERSION = "1.0.0"
SPEC_DATE = "2026-09-28"

# Primary endpoint identifier (see measure.S_CFG).
PRIMARY_ENDPOINT = "S_cfg"

# Secondary endpoints reported alongside the primary (see measure.py).
SECONDARY_ENDPOINTS = (
    "S_cfg_boundary",   # function-boundary recovery (names ignored)
    "S_const",          # constant recovery rate
    "S_deobf",          # fully-deobfuscated-function rate
    "attack_time_s",    # wall time of apply()
)

# Control arm identifiers.
ARM_UNPROTECTED = "unprotected"
ARM_SEED_ONLY = "seed_only"
ARM_HETERO = "hetero"

# Attack arm identifiers, in protocol order.
ATTACK_STATIC = "static"
ATTACK_GHIDRA = "ghidra"
ATTACK_LLM = "llm"  # Phase 2; registered here so reports name it consistently.

# Bootstrap resamples for transfer CIs (see measure.transfer_ci).
BOOTSTRAP_B = 1000

# Minimum builds per arm for a reportable transfer matrix.
MIN_BUILDS_PER_ARM = 2
