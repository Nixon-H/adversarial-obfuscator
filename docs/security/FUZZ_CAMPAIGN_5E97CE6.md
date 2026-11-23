# Fuzz campaign — parsers at commit `5e97ce6`

**Scope note, stated first.** This campaign was run against the parser
implementations as committed in `5e97ce6`, which is AFTER the malformed-input
fixes (`JSON null`, corrupted `state`, negative `total`/`OverflowError`). The
earlier 34,479,063-execution campaign predates those fixes; its result is not
evidence for them and is not cited here. Re-running was the point.

## Environment

| Item | Value |
|---|---|
| Tool | Atheris (libFuzzer driver), `/tmp/fuzzvenv` |
| Harness | `scripts/fuzz/nx_fuzz.py` |
| Parser loading | `_load_parsers()` runs INSIDE `atheris.instrument_imports()`, so every parser module is instrumented. The first version imported parsers inside each fuzz body, after instrumentation had already closed — which is why its coverage numbers were flat |
| Seed corpus | `_seed_blobs()` writes a structured seed per target before fuzzing; the first campaign ran with an empty corpus and the oracle rejected valid packs, so it was measuring nothing |
| Oracle | An acceptance is a FINDING unless it is a pack the builder itself produced (keyed hint + declared structure + plaintext). "Did not raise" is not acceptance |

## Results

| Target | Executions | New corpus units | Crashes | Unintended acceptances |
|---|---|---|---|---|
| `pack` | 7,794,036 | 814 | 0 | 0 |
| `state` | 19,427,456 | 904 | 0 | 0 |
| `manifest` | 861,672 | 13 | 0 | 0 |
| `elf` | 16,574,928 | 20 | 0 | 0 |
| `pe` | 23,417,916 | 6 | 0 | 0 |
| `macho` | 9,689,462 | 111 | 0 | 0 |
| **total** | **77,765,470** | **1,868** | **0** | **0** |

Peak RSS stayed at 70 MB for every target at the configured `-max_len`, so the
resource bound held under adversarial input rather than being assumed.

A benign libFuzzer message appears on four targets:
`WARNING: Failed to find function "__sanitizer_acquire_crash_state"`. It is
emitted by libFuzzer when the asan runtime is not linked into the process; the
campaign still runs and still reports crashes, it just cannot use the
crash-state file. Recorded here because a warning in a security log should never
be silently dropped — it is a limitation of this harness, not a finding.

## What this does and does not establish

**Does:** malformed input to six parsers did not produce a crash or a
result the oracle treats as acceptance, over 77.7 million executions derived
from structured seeds. That is meaningful evidence for the specific claim "the
parser fixes hold and nothing adjacent regressed".

**Does not:** prove the absence of bugs. A fuzzer finds what its oracle defines
as wrong, and this oracle is deliberately narrow (crash or unintended
acceptance). It cannot see a parser that returns a *plausible but wrong* value
inside the accepted range, and it cannot see logic errors that require a
well-formed input to reach. Those are what the deterministic matrix in
`tests/test_parser_fuzz.py` and the adversarial findings in
`docs/security/REVIEW_FINDINGS_FILED.md` are for.

**Corpus preservation, honestly scoped.** The harness writes its seed corpus to
a temporary directory that is removed with the process, so the 1,868 evolved
units from this campaign were NOT retained for replay. An attempt to make the
corpus path persistent was blocked by the local write-time security scanner
(any environment-derived path trips its path-traversal rule), and rather than
weaken or bypass the scanner the change was dropped. The consequence is
concrete: the next campaign restarts from the hand-written seeds and will not
reuse this one's coverage. Recorded here as an open limitation rather than
described as "corpus preserved".

## Reproducing

```
python3 -m venv /tmp/fuzzvenv
/tmp/fuzzvenv/bin/pip install atheris
cd <repo>
NX_FUZZ_TARGET=pack PYTHONPATH=$PWD \
    NX_FUZZ_SECONDS=90 /tmp/fuzzvenv/bin/python scripts/fuzz/nx_fuzz.py
```

Targets: `pack`, `state`, `manifest`, `elf`, `pe`, `macho`.
