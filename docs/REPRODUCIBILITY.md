# Reproducibility

**Status:** current. Every command below was run in this repository; the
research commands were re-run on 2026-11-10. Where a claim cannot be reproduced
from the repository, this document says so instead of supplying a plausible
command.

Related: [`BENCHMARK.md`](BENCHMARK.md), [`RESULTS.md`](RESULTS.md),
[`DEVELOPER.md`](DEVELOPER.md).

---

## 1. Environment

| Item | Value |
|---|---|
| Primary host | Linux x86_64 |
| Interpreter used for verification | CPython 3.13.5 |
| Supported builder/payload range | Python 3.10–3.14 |
| Quick start | stdlib only |
| Full pipeline | `cargo`, `g++`, `llc` (checked at startup) |
| Dependency lock | `requirements.lock`, hash-pinned, CI installs with `--require-hashes` |

If a result depends on the interpreter, state which one. The programme spent
fifteen rounds on an intermittent failure that turned out to be **two Python
installations on the same machine**, with different `cryptography` versions.
The lesson is in [`research/test-isolation-flake.md`](research/test-isolation-flake.md):
run `which python3` before reading a version from it.

---

## 2. The four research checks

These are the checks the research README names. All are deterministic: explicit
seeds, no network, repository inputs.

### 2.1 Reproduction of the paper's tables

```bash
python3 scripts/transfer/reproduce.py
```

Prints ten tables, each with the regenerated value beside the document's claim.
It does **not** assert equality; a human must compare. Expected output
(re-verified 2026-11-10):

```text
singleton            | {'cells': 51, 'non_singleton': 0}   | 51 cells, 0 non-singleton
module-size          | {1: 2, 2: 3.4, 3: 5.8, 4: 8.6}      | 2.0 at 1 candidate, 8.6 at 4
diversity            | {'A-vs-B': 0.33, ...}               | A-vs-B +0.33, ...
fixed-build          | [9, 9, 9, 9, 9]                      | 9 9 9 9 9
fault-control        | {'correct': 9, 'fault': 11}         | 9 then 11 probes
authoring            | {'properties': 38}                  | 38 properties across 9 tasks
calibration          | [9, 11, 20, 20]                     | 9, 11, 20, 20 probes
sibling-substitution | {'mean': 5.11, 'min': 3, 'max': 8}  | 5.11 probes, range 3 to 8
diversity-sd         | {'per_task': [0.333], ...}          | sd 0.00 ...
blind-baseline       | {1: 8, 2: 12, 3: 16, 4: 20}         | 8.0 / 12.0 / 16.0 / 20.0
```

If a value differs, either the build changed or the document is stale. Both
are worth a round.

### 2.2 The artefact gate

```bash
python3 scripts/transfer/artefact_gate.py --variants 1 --seeds 4242
```

Expected: **38 artefacts at one index, 0 failures**. The gate compiles, imports,
and runs each artefact. It writes `docs/research/gate-count.json`, which the
number guards compare against documents.

A wider sweep is also clean but produces a different count:
`--variants 2 --seeds 4242,7` checks **152 artefacts, 0 failures**. Quote the
command alongside the count; the count depends on both options.

Do not quote the count from an old round. The count depends on `--variants` and
conditional corpus inclusion, so it is a measurement, not a source property.
An earlier attempt to derive it from the gate's AST reported 21 against a real
38.

### 2.3 Task validity

```bash
python3 scripts/transfer/evaluate_tasks.py
```

Checks that every gated cell has a unique evaluator-decided identity and a
singleton attacker set. The validity failures and repairs are recorded in
[`research/task-validity.md`](research/task-validity.md).

### 2.4 External validity

```bash
python3 scripts/transfer/evaluate_external.py
```

Expected: 12 of 12 cells valid after the round-171 evaluator fix (the original
run reported 8 of 9). Recorded in
[`research/external-tasks-evaluated.md`](research/external-tasks-evaluated.md).

---

## 3. Documentation guards

```bash
python3 -m pytest tests/test_research_docs_consistency.py \
                 tests/test_research_numbers_match_sources.py -q
```

These check that the research documents agree with each other and with the
code: benchmark counts, defect-table contiguity, the retracted flat-curve
claim, the module-size figure, the authoring count, and artefact counts.

```bash
python3 -m pytest tests/test_readme_matches_cli.py -q
```

Checks that [`CLI.md`](CLI.md) is regenerated from the live parsers.

```bash
python3 -m pytest tests/test_documented_flags_exist.py -q
```

Checks that every flag the user-facing docs mention exists.

To regenerate the CLI reference after changing a parser:

```bash
python3 scripts/gen_cli_reference.py --write
```

---

## 4. Product verification

```bash
# The whole suite (large; read the live count, not a doc)
NIXON_LOG_REDIRECT=0 python3 -m pytest tests/ -q

# Lint: ruff plus a runtime undefined-global check
make lint

# Every build must produce an artefact that RUNS
make e2e

# What the last commit removed, and which removals dropped a call
make audit-commit

# Full make target: core, whitebox, py_compile, relay
make all
```

Targeted subsets that are faster than the full suite:

```bash
NIXON_LOG_REDIRECT=0 python3 -m pytest \
  tests/test_lowering_parity_141.py tests/test_diagnostic.py \
  tests/test_trial_bind.py tests/test_hwid_static.py \
  tests/test_hwid_lock.py tests/test_pytoc.py \
  tests/test_pyinstaller_spec.py tests/test_stdlib_audit.py \
  tests/test_frozen_snapshot.py tests/test_watermark_gate.py \
  tests/test_name_gate.py tests/test_internal_rename.py \
  tests/test_split_bootstrap.py tests/test_driver_blocklist.py -q
```

`NIXON_LOG_REDIRECT=0` keeps pytest output on the console instead of
`build.log`.

---

## 5. Verified build examples

### 5.1 Minimal build (no toolchain)

```bash
echo 'print("hello-nixon")' > /tmp/hello.py

NIXON_LOG_REDIRECT=0 timeout 300 python3 scripts/build.py \
  --payload /tmp/hello.py -o /tmp/qs_hello.py --force-output \
  --skip-irgen --skip-llvmgen --skip-encrypt --skip-relay --skip-extras

NIXON_LOG_REDIRECT=0 timeout 60 python3 build/hello_obfuscated.py
# hello-nixon
```

Measured: about one second; ~15 KB artefact from a 21-byte source at the
default `--opt-level 4`. Level 0 disables the 17 ladder transforms but still
runs always-on passes, so it is **not** byte-identical through the CLI.
`--skip-obfuscate` is the byte-identical path: verified on a 2,635-byte
payload, 2,635 bytes out, `diff` clean.

### 5.2 Packed loader build

```bash
NIXON_LOG_REDIRECT=0 PYTHONPATH=$PWD \
  python3 -m obfuscator.core.pipeline build /tmp/hello.py \
    --skip-cloud --layers 25

python3 /tmp/dist/hello_protected.py
```

The packed build writes to `<dirname(source)>/dist/`, not the current
directory and not `build/`. For `/tmp/hello.py`, that is
`/tmp/dist/hello_protected.py` (verified 2026-11-10: 58 s, 2.8 MB). Without
`--layers 25`, the default is 100 packaging layers; loader defaults then took
**387 s** on a 2,635-byte payload. Its flags do not overlap with `build.py`'s;
the equivalent of `--skip-extras` is `--skip-cloud`.

### 5.3 Maximum-security build

```bash
# One-time: generate an issuer seed and keep it out of the repository.
ISSUER_SEED=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

# Issue a token for one customer.
python3 -m obfuscator.licensing issue --key-hex "$ISSUER_SEED" \
  --customer acme --days 30 --features pro --out payload.licence

NIXON_LOG_REDIRECT=0 PYTHONPATH=$PWD \
  python3 -m obfuscator.core.pipeline build payload.py \
    --skip-cloud \
    --anti-rea-level maximum \
    --section-count 6 \
    --watermark NX-MAX-001 \
    --trial 7d \
    --licence-token payload.licence \
    --layers 25
```

Measured on a 2,635-byte payload: **69–99 s**, **1.46–8.25 MB** (size varies
between runs), runs with the token and exits 1 without it. `--opt-level 5` and
`--section-split` are omitted because both are already the loader default; adding
them changes nothing. With the default 100 packaging layers, the same
anti-REA-maximum configuration **did not finish in 600 s** — see
[`MAXIMUM_SECURITY.md`](MAXIMUM_SECURITY.md). Loader defaults alone measured
**387 s** and 3.55 MB. Output includes `nixon_core.so` and a self-signed
`Nixon_Security_Root.cer`; it is written to `<dirname(source)>/dist/`.

**Known gap in this command:** `--trial` and `--hwid-lock` are accepted here
but did **not** reach the standard packed-loader artefact in the measured
builds (`MAXIMUM_SECURITY.md` §6.9). The licence token is the binding that is
verified to fire.

### 5.4 Verifying a hardened build

```bash
python3 <dirname(payload)>/dist/payload_protected.py
strings <dirname(payload)>/dist/payload_protected.py | grep -c NX-WM-001
```

A build whose phase-3 table reports a variant **mismatch** fails (exit 1). A
variant that could not be run is inconclusive and does not fail — a gate that
fires on its own inability to check is not a gate.

---

## 6. What is deterministic, and what is not

| Artefact | Deterministic? | Notes |
|---|---|---|
| Research tables | **Yes** | Explicit seeds, no network |
| Artefact gate | **Yes** | `--seeds` is required for a stable count |
| Tests | **Mostly** | Some tests are host-sensitive; CI covers 3.10–3.14 |
| Product build, no seed | **No, by design** | ~3,650 `secrets` draws per build |
| Product build with `--seed` | **Yes** | Same payload, tool version and flags produce identical bytes (verified) |
| `--skip-obfuscate` | **Yes** | Byte-identical copy of the payload |
| Packed loader | **No** | Blob keys, string keys, timestamps and packaging draws remain random |

### 6.1 The build-reproducibility caveat

`--seed` seeds Python's global `random`, the AST transformer's own RNG, its
`secrets` patch, and several AST injectors. **With a fixed seed, the source
emitter now produces byte-identical output for the same payload, tool version,
and flag set.** Measured after the wiring fix: three O4 builds gave 29,802 bytes
each with SHA-256 `50ad8c8007d95dc4…`; two builds with the phase-2 defaults on
gave 33,170 bytes each; a different seed gave 32,911 bytes.

This does **not** make the packed loader reproducible: its blob key, string
keys, section keys, timestamps and packaging draws come from `secrets`/
`os.urandom`, and several values cross the pack/run boundary. `--pin-structure`
pins structure but not key material.

Before the fix, three `--seed 42` builds differed (29,805 / 29,800 / 29,805
bytes); the first differing line was the string-encryption key. The cause was
that `phase01_obfuscate.py` never passed `seed=` into `build_pipeline`, so the
transformer never ran its `secrets` patch. [`SEED_ARCHITECTURE.md`](SEED_ARCHITECTURE.md)
records the experiment and the fix.

`docs/CHANGELOG.md` carries a dated correction to its old "the flag is gone"
entry. `--randomization-seed` remains accepted by `scripts/build.py` and seeds
structure randomisation, speculation, and the CPU-port phase.

---

## 7. CI

Fourteen workflows fan out from `all-checks.yml`. The ones that matter for
reproduction:

| Workflow | What it covers |
|---|---|
| `ci.yml` | Full suite on Ubuntu × Python 3.10–3.14; `pip-audit` gate |
| `portable-build-matrix.yml` | 3 OSes × 3.10–3.14, payload types, audits |
| `portable-deep-matrix.yml` | 12 configurations, 8 isolated packing flags, 12 isolated ladder transforms |
| `flag-isolation.yml` | One flag at a time; PASS/FAIL/CONFLICT/CATALOGUE/NONSTANDALONE/SLOW |
| `security-artifact.yml` | Real artefacts, fresh processes, strip/tamper probes |
| `codeql.yml` | Static analysis |

A hosted job that compiles or unit-tests a gate is **adversarial testing**, not
deployment validation. `THREAT_MODEL.md` caps every row except the watermark at
`ADVERSARIAL_TESTED` for this reason.

---

## 8. What cannot be reproduced here

| Item | Why |
|---|---|
| The paper's build-spread sizes (30,424 … 34,208) | No seed set or command is committed; the paper gives a description, not a reproduction |
| Analyst time | No human study exists |
| Independent specification at scale | Six blind tasks, two load-bearing; a corpus needs more authors |
| Sealed reports | They live outside the repository |
| Full suite on another machine | CI covers Linux; host-specific tests exist |
| The H0–H5 pilot's intended arms | The runner always used variant ID 0; a corrected rerun is future work |
| Counter-REA / deception effect on an analyst | No adversary-in-the-loop measurement exists |

These are the gaps. [`LIMITATIONS.md`](LIMITATIONS.md) says what would close
each one.
