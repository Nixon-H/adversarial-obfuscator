# v2.0 Structural-signature transfer (calc, H0/H1/H2): boundary signal

Date: 2026-09-29. Level: Python bytecode CFG (builtin compile, never
executed; opname-only labels; no Cython/binary involvement).
Primary: out-degree-multiset Jaccard (pure topology). Secondary: content
edge-Jaccard. Tertiary: block-hash Jaccard. Raw cells:
Topo means: h0>h0 1.000, h2>h2 1.000, h1>h1 1.000,
  h2>h0 0.833, h0>h2 0.833, h2>h1 0.833, h1>h2 0.833,
  h0>h1 1.000, h1>h0 1.000. (n=30 within-arm, 36 cross-arm.)

## Gate history (instrument revision disclosed)

First primary (content-labeled edges) failed the H2->H2 gate at 0.767:
rep tuple-rewrites change intra-block opcodes, relabeling edges while
topology is identical (diagnosed via fib disassembly: BUILD_TUPLE/
UNPACK form vs rotation form). Gate worked as designed -- no cross-arm
number had been measured. Primary switched to topology-only
(out-degree multiset), re-gated at 1.000 min/mean, then cross-arm
measured. The three-level readout separates concerns: topo 1.00 /
edge 0.77 / block 0.88 on H2->H2 shows rep moves content, not shape.

## Directional result

Flatten boundary (H2 rep-only vs H0/H1 flattened+junk arms): topo 0.833
vs self 1.000, frozen falsification verdict SUPPORTS-H1 (p~=0,
n=36/30). A real, modest, statistically distinguishable structural
signal -- not a collapse. Within-flattened matching (h0>h0, h1>h1,
h0>h1) is 1.000: dispatcher topology is seed- and set-stable.

Attribution caveat: the boundary bundles flattening + dead-code junk +
MBA (H0/H1 pass sets); the effect is arm-level separation, not
single-transform attribution. Single-factor arms would be future work
under a new pre-registration, not post-hoc slicing here.

## Contrast with v1.0/v2.0-VM

Semantic attacks: T=1.00 across this same boundary. VM-table attack:
T~=0.03 across seeds. CFG topology: T=0.83 across the flatten
boundary. Three attacks, three transfer regimes on the same builds --
the (attack, transform) pairing thesis with both null and positive
instances plus a graded middle case.
