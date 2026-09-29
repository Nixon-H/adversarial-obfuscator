# Ghidra pilot (calc, sampled 6x6): Path A — mechanistically uninformative

Date: 2026-09-29. Scope: 6 develop + 36 apply headless runs (~55-80s each),
calc program, one build per arm per role (_0 develop, _1 target).
Raw observables only; frozen spec untouched (no endpoint added).

## Raw 6x6 apply matrix (detected function counts)

Target:        H0   H1   H2   H3   H4   H5
dev H0        270  255  254  332  507  491
dev H1        270  255  254  332  507  491
dev H2        270  255  254  332  507  491
dev H3        270  255  254  332  507  491
dev H4        270  255  254  332  507  491
dev H5        270  255  254  332  507  491

Name overlap: 0 in all 36 cells (Cython-mangled names; expected).
Run stability: repeated apply identical (332/332). Attack time ~55-80s/run.

## Falsification Test 2 (row invariance): REJECT

Every target column is perfectly row-invariant (spread 0 in all 6
columns). M[i,j] = f(target_j) exactly; the development arm contributes
nothing. A T_ghidra(i->j) = M[i,j]/M[j,j] would equal 1.00 in all 36
cells by construction -- the amendment would add zero information.
No diagonal decay, no triangular structure: no transfer dynamics exist
in this observable.

## Falsification Test 1 (size confound): REJECT

.text sizes (H0..H5): 69921, 55649, 36481, 140224, 386516, 332212.
Matched same-build pairing (apply-column counts vs same-target .text):
Spearman r = 1.000, Pearson r = 0.997 (n=6, p<0.0001).
Transparency note: the pre-registered script paired develop (_0) counts
against recompiled _1 sizes (seed noise across builds), giving r=0.829
(marginal pass). The corrected same-build pairing -- the principled
quantity, since counts are target-determined per Test 2 -- gives 1.000.
Both numbers reported; conclusion identical under either: detections
are a pure binary-mass proxy (Cython boilerplate + k*code).

## Verdict: Path A locks

No S_detect / T_ghidra amendment. The frozen spec stays clean.
Paper framing (negative/orthogonal finding): decompilation symbol yield
under C-transpilation scales monotonically with binary mass and provides
no transform-specific transfer signal -- a documented negative control
for the transfer benchmark, consistent with the static arm's
target-determined T=1.00. The Ghidra arm as designed (count-based
recovery on Cython-mangled binaries) cannot discriminate obfuscation
tiers; a discriminating binary-level arm would need semantic recovery
(e.g., decompiled-equivalence checks), which is future work, not a
spec patch.
