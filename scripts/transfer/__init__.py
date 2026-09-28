"""Transfer-harness package (G2 experiment).

Frozen protocol: see protocol.py. Submodules:

- builds: variant-matrix construction + semantic-equivalence gate.
- attack: Attack interface + static arm + Ghidra arm.
- measure: endpoints S_*, transfer T_ij, bootstrap CIs, rank-sum test.
- corpus: holdout-corpus loader (calibration / development / held_out).
- report: JSON + markdown report incl. config_freeze_hash.
"""

from scripts.transfer import protocol  # noqa: F401
