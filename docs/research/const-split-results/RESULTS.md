# Experiment v2.0 — T_const_split (amendments 1-2)

Pre-registered arm and instrument: `docs/research/protocol-v2.md`, amendments 1 and 2 (both written before the number they govern).

**config_freeze_hash_const**: `a78ca807f9e8d659f4aaaa2306762b43a7d85bf685b39eadc5c6eae6ee5d7b46`  
**pre-amendment (disclosed)**: `19a48e75cf34ee565e36587dfb73d88e30cccaf5fa1f8a9de16f5cf85221a66d`

Builds per arm per program: 3. Seeds block: +201. Semantic gate: every variant or excluded.

## Aggregate (mean over programs)

`delta` = S(A->B) minus S(B->B), the matched same-arm control. A negative delta is transfer resistance; zero is absolute-only loss.

| cell | S_all | S_int | S_str (control) | same-arm control | delta | n_int | pairs |
|---|---|---|---|---|---|---|---|
| C0>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.3 | 36 |
| C0>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.3 | 54 |
| C0>C2 | 0.989 | 0.981 | 1.000 | 0.989 | -0.000 | 4.3 | 54 |
| C0>C3 | 0.995 | 0.992 | 1.000 | 0.995 | -0.000 | 4.3 | 54 |
| C1>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.3 | 54 |
| C1>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.3 | 36 |
| C1>C2 | 0.989 | 0.981 | 1.000 | 0.989 | -0.000 | 4.3 | 54 |
| C1>C3 | 0.995 | 0.992 | 1.000 | 0.995 | -0.000 | 4.3 | 54 |
| C2>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.2 | 54 |
| C2>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.2 | 54 |
| C2>C2 | 0.989 | 0.981 | 1.000 | 0.989 | 0.000 | 4.2 | 36 |
| C2>C3 | 0.997 | 0.995 | 1.000 | 0.995 | 0.002 | 4.2 | 54 |
| C3>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.3 | 54 |
| C3>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.3 | 54 |
| C3>C2 | 0.991 | 0.984 | 1.000 | 0.989 | 0.002 | 4.3 | 54 |
| C3>C3 | 0.995 | 0.992 | 1.000 | 0.995 | 0.000 | 4.3 | 36 |

### Verdict

NO TRANSFER RESISTANCE. Cross-arm cells sit at their matched same-arm controls (worst delta -0.000). Absolute recovery loss is 0.011, and that loss is identical whether the attacker applies the constants to another build of the same arm or to the protected arm: the hiding rule is build-invariant, so it lowers the ceiling without changing transfer. Any T below 1.00 here is absolute loss, not transfer resistance.

### Pre-amendment instrument (disclosed)

Same builds, amendment-1 extraction (folded sequences dropped). Reported because the correction was made after a number existed; the table above is primary.

| cell | S_all | S_int | S_str | same-arm control | delta | n_int |
|---|---|---|---|---|---|---|
| C0>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.0 |
| C0>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.0 |
| C0>C2 | 0.994 | 0.989 | 1.000 | 0.994 | -0.000 | 4.0 |
| C0>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.0 |
| C1>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.0 |
| C1>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.0 |
| C1>C2 | 0.994 | 0.989 | 1.000 | 0.994 | -0.000 | 4.0 |
| C1>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.0 |
| C2>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.9 |
| C2>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.9 |
| C2>C2 | 0.994 | 0.989 | 1.000 | 0.994 | 0.000 | 3.9 |
| C2>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.9 |
| C3>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.0 |
| C3>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.0 |
| C3>C2 | 0.994 | 0.989 | 1.000 | 0.994 | -0.000 | 4.0 |
| C3>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.0 |

Pre-amendment verdict: NO TRANSFER RESISTANCE. Cross-arm cells sit at their matched same-arm controls (worst delta -0.000). Absolute recovery loss is 0.006, and that loss is identical whether the attacker applies the constants to another build of the same arm or to the protected arm: the hiding rule is build-invariant, so it lowers the ceiling without changing transfer. Any T below 1.00 here is absolute loss, not transfer resistance.

## Per program

### calc (calibration)

Source constants: 8 corrected (8 pre-amendment). Usable builds: 12. Excluded: 0.

| cell | S_all | S_int | S_str | same-arm control | delta | n_int |
|---|---|---|---|---|---|---|
| C0>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C0>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C0>C2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C0>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C1>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C1>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C1>C2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C1>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C2>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C2>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C2>C2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C2>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C3>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C3>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C3>C2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C3>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |

### parser (calibration)

Source constants: 8 corrected (8 pre-amendment). Usable builds: 12. Excluded: 0.

| cell | S_all | S_int | S_str | same-arm control | delta | n_int |
|---|---|---|---|---|---|---|
| C0>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C0>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C0>C2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C0>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C1>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C1>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C1>C2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C1>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C2>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C2>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C2>C2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C2>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C3>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C3>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C3>C2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C3>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |

### auth (development)

Source constants: 9 corrected (9 pre-amendment). Usable builds: 12. Excluded: 0.

| cell | S_all | S_int | S_str | same-arm control | delta | n_int |
|---|---|---|---|---|---|---|
| C0>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C0>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C0>C2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C0>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C1>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C1>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C1>C2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C1>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C2>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C2>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C2>C2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C2>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C3>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C3>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C3>C2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C3>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |

### store (development)

Source constants: 7 corrected (7 pre-amendment). Usable builds: 12. Excluded: 0.

| cell | S_all | S_int | S_str | same-arm control | delta | n_int |
|---|---|---|---|---|---|---|
| C0>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C0>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C0>C2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C0>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C1>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C1>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C1>C2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C1>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C2>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C2>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C2>C2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C2>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C3>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C3>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C3>C2 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |
| C3>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 3.0 |

### codec (held_out)

Source constants: 10 corrected (10 pre-amendment). Usable builds: 12. Excluded: 0.

| cell | S_all | S_int | S_str | same-arm control | delta | n_int |
|---|---|---|---|---|---|---|
| C0>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C0>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C0>C2 | 0.967 | 0.933 | 1.000 | 0.967 | -0.000 | 5.0 |
| C0>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C1>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C1>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C1>C2 | 0.967 | 0.933 | 1.000 | 0.967 | -0.000 | 5.0 |
| C1>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C2>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.7 |
| C2>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.7 |
| C2>C2 | 0.967 | 0.933 | 1.000 | 0.967 | 0.000 | 4.7 |
| C2>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 4.7 |
| C3>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C3>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |
| C3>C2 | 0.967 | 0.933 | 1.000 | 0.967 | -0.000 | 5.0 |
| C3>C3 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 5.0 |

### sched (held_out)

Source constants: 11 corrected (9 pre-amendment). Usable builds: 12. Excluded: 0.

| cell | S_all | S_int | S_str | same-arm control | delta | n_int |
|---|---|---|---|---|---|---|
| C0>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 7.0 |
| C0>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 7.0 |
| C0>C2 | 0.970 | 0.952 | 1.000 | 0.970 | -0.000 | 7.0 |
| C0>C3 | 0.970 | 0.952 | 1.000 | 0.970 | -0.000 | 7.0 |
| C1>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 7.0 |
| C1>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 7.0 |
| C1>C2 | 0.970 | 0.952 | 1.000 | 0.970 | -0.000 | 7.0 |
| C1>C3 | 0.970 | 0.952 | 1.000 | 0.970 | -0.000 | 7.0 |
| C2>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 6.7 |
| C2>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 6.7 |
| C2>C2 | 0.970 | 0.952 | 1.000 | 0.970 | 0.000 | 6.7 |
| C2>C3 | 0.980 | 0.968 | 1.000 | 0.970 | 0.010 | 6.7 |
| C3>C0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 6.7 |
| C3>C1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 6.7 |
| C3>C2 | 0.980 | 0.968 | 1.000 | 0.970 | 0.010 | 6.7 |
| C3>C3 | 0.970 | 0.952 | 1.000 | 0.970 | 0.000 | 6.7 |

## Gates

- Denominator `S(B_j|P_j)` = 1.00 for every usable build: PASS
- Negative control C0->C0 >= 0.80: 1.000
- String specificity control stays 1.00 in every cell: PASS

## Notes

- Runtime: CPython 3.13.5.
- Instrument: amendment 2 (folded sequences flattened). The pre-amendment aggregate is disclosed below; it drops every element of a folded tuple/list/dict-key constant. The corpus carries only 2-3 folded elements per program (7-11 constants corrected vs 7-10 pre-amendment), but the sensitivity fixture carries 20 in one display (22 ints corrected vs 2 pre-amendment).
- Denominator power is low by construction: the corpus programs carry 7-11 literal constants in total, and the integer subset used by the split arm averages 4.3 per cell. A 1.00 here is a low-power 1.00, not a precise one.
- `split_vars` only rewrites `name = <int>` assignments and `unfold_constants` only rewrites ints in (1, 1000); the corpus has few of either, so the registered arms act on a small population. This is reported rather than fixed after the fact (anti-tuning rule).
- Mechanism: `unfold_constants` has three branches, but the compiler folds `(v^m)^m` and `(b<<s)+r` back to `v`; only `sum([parts])` survives into the bytecode pool. The other two branches hide `v` from source-text search but not from the compiled pool this endpoint measures.
- Scope: literal search only. `C` split as `C ^ m` and `m` is algebraically recoverable; a T below 1.00 would support 'hides literals from search', never 'hides values'.
- The disclosed pre-amendment instrument gives the same verdict (worst delta -0.000 vs -0.000 corrected).
