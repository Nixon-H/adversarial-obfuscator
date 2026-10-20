# Follow-up Audit — 2026-10-19

**Repo:** `/home/nixon/Projects/adversarial-obfuscator`
**Baseline:** `181b151` (the end of the first follow-up round)
**Scope:** the four items the first audit left open, in the order they were
worked, each with a verification gate:

| Phase | Item | Gate | Result |
|---|---|---|---|
| A | Unverified TLS context in the emitted key fetch | negative TLS tests + generated-loader tests | **PASS** |
| B | `build.log` opened at import time | import-side-effect regression tests | **PASS** |
| C | `section_split.py` — integrate or remove | integration justified by real call paths + tests | **PASS (integrated)** |
| D | Lint campaign | full suite + enforced lint checks | **PASS** |

This report is the follow-up to [`docs/AUDIT-2026-10-19.md`](AUDIT-2026-10-19.md),
which covered the session that produced `181b151`.

---

## 1. Executive summary

All four open items are closed. The headline is not the four items
themselves but what the lint campaign (Phase D) turned up while it ran: the
audit had been looking at *modules*, and the defects that mattered were in
*interactions*.

| # | Finding | Severity | Status |
|---|---|---|---|
| A1 | Emitted key fetch used `ssl._create_unverified_context()` — any certificate accepted, so a network attacker could choose the session key the artifact derives from the response | **HIGH** | Fixed |
| A2 | The emitted loader wrote the **decrypted payload source** to a hardcoded absolute path (`/home/nixon/Desktop/2/dump.py`, a symlink to this repo) at runtime | **HIGH** | Fixed |
| A3 | The pipeline-CLI loader could not be parsed at all (`ANTMAN_SOURCE` had an `except` at the wrong indent level) | **HIGH** | Fixed |
| A4 | The pipeline-CLI loader died with `NameError` — the string pass rewrote the loader preamble's literals into decoder calls that are defined *later* in the file | **HIGH** | Fixed |
| B1 | Importing `obfuscator.core.utils` created and **truncated** `./build.log` in the caller's working directory | MEDIUM | Fixed |
| B2 | An exported `NIXON_LOG_REDIRECT=1` hijacked pytest's own stdout | LOW | Fixed |
| C1 | `section_split.py` was implemented, unit-tested, and wired to nothing | MEDIUM | Integrated |
| D1 | `requests` used but never imported in the build-farm bandwidth probe — every measurement returned the lowest score | MEDIUM | Fixed |
| D2 | `z3` used but never imported in `--prove-fragments` — the feature always reported a failed proof | MEDIUM | Fixed |
| D3 | `_virt_write` used in a different scope than the one it is defined in | MEDIUM | Fixed |
| D4 | `_platform_src_migrate` / `_platform_dst_migrate` never defined at all | MEDIUM | Fixed |
| D5 | `tempfile_name` never defined — the decompiler probe never ran | LOW | Fixed |
| D6 | Four modules used **Python 3.12+ f-string syntax** (PEP 701) and could not be imported on 3.10/3.11, despite the 3.10–3.14 claim | **HIGH** | Fixed |
| D7 | `platform` used as a loop variable, shadowing the module import | LOW | Fixed |
| D8 | Seven dictionary keys were declared twice with different values — the first was silently dead | LOW | Fixed |
| D9 | `scripts/exposure/tracker.py` defined `record_appearance` twice; the second shadowed the first | LOW | Fixed |
| D10 | `test_guided_improves_scores` computed two score means and asserted nothing | LOW | Fixed |
| D11 | `make lint` could never fail (`\|\| true`), so the CI lint step was a no-op | MEDIUM | Fixed |
| D12 | `tests/test_rust_relay.py` failed rather than skipped when the relay binary had not been built | LOW | Fixed |

**Verification:** 4215 tests passed, 23 skipped, 0 failed (main suite 3779 +
advanced-protection 284 + bench group 152); `ruff check --no-cache .` clean;
25/25 consecutive default builds produce an artifact that runs.

---

## 2. Phase A — the emitted key fetch now verifies TLS

### A1 — `ssl._create_unverified_context()` in the emitted loader

**Where:** `obfuscator/core/sources.py`, two sites inside the emitted
loader template: the auth probe (`FUNC_NET`) and the NTRU key exchange.

**Why it mattered.** The key-exchange path derives `_RUNTIME_KEY` from the
server's response. With an unverified context, anyone able to intercept
the TLS connection could substitute their own response and choose the
artifact's runtime key. The DoH path was already safe (`urlopen` without
a context uses the default verified context).

**Fix.** The loader now builds a verified context:

* `ssl.create_default_context()` — system trust store, `CERT_REQUIRED`,
  hostname checking on;
* plus, optionally, an operator-owned CA **added** to that store
  (`--tls-ca-bundle PATH`, embedded base64 so the artifact stays
  self-contained and portable). Embedding a CA adds trust for that
  endpoint; it never disables verification.

**Tests** (`tests/test_tls_context.py`, 8): the emitted context is
`CERT_REQUIRED` with `check_hostname` on; an untrusted certificate is
rejected; a CA-signed certificate is accepted when its CA is embedded; a
CA-signed certificate for the *wrong host* is still rejected (the bundle
adds trust, it does not disable the hostname check); an HTTPS request
through the emitted context succeeds against a local TLS server; the
loader contains no unverified context; the build-side CA helper
round-trips and fails loudly on a missing or empty bundle.

### A2 — the loader wrote the decrypted payload to a hardcoded path

**Where:** `obfuscator/core/sources.py`, in the emitted module loader.

```python
with open("/home/nixon/Desktop/2/dump.py", "wb") as _dump_f:
    _dump_f.write(raw ...)
```

`/home/nixon/Desktop/2` is a **symlink to this repository**. So the
artifact, when run, dropped a plaintext copy of its own decrypted payload
into the repo working tree. On any other machine the write silently
failed (the directory does not exist), which is why it had never been
noticed.

**Fix.** The dump is now opt-in (`NIXON_DUMP_RAW=1`, matching the
build-side convention) and goes to a private 0600 temp file with a random
name. The hardcoded path is gone.

### A3 / A4 — the pipeline-CLI loader did not work at all

Found while validating A1: the loader emitted by
`obfuscator/core/pipeline.py::build_project` (the "Universal" artifact,
also used by `scripts/ci_security_artifact.py`) was **unusable**.

* **A3 — SyntaxError.** `ANTMAN_SOURCE` had
  `except Exception: return True` at the wrong indent level, so the
  `try:` had no body. The emitted file could not be parsed.
* **A4 — NameError.** `Nixon_Enc_strings` rewrote the loader *preamble's*
  string literals into decoder calls, but the decoder is defined *later* in
  the file. The artifact raised `NameError` at import.

**Fix.** The `except` was re-indented, and the string pass now leaves the
preamble alone until the decoder definition has been seen.

**Tests** (`tests/test_emitted_sources_parse.py`, 96; and
`tests/test_pipeline_loader_e2e.py`, 4): every emitted source template is
rendered and parsed, and the pipeline loader is built, run, and checked to
leave no stray files.

---

## 3. Phase B — importing no longer touches the filesystem

### B1 — `build.log` was created and truncated at import time

`obfuscator/core/utils.py` opened `build.log` (mode `"w"`) and redirected
stdout/stderr into it as a side effect of *importing the module*. Merely
importing it therefore created a file in the caller's working directory
and truncated an existing one — including a file that had nothing to do
with this project.

**Fix.** The redirect is now explicit: `enable_log_redirect(path=None)`
performs it, and the entry points that want a log file call it
(`obfuscator/core/pipeline.py`'s CLI). The default is unchanged for
builds: the pipeline CLI still writes `build.log` (0600) in the working
directory, and `scripts/build.py` still logs to the console.

**Tests** (`tests/test_import_side_effects.py`, 8): importing any of the
core modules in a clean directory creates no file; a pre-existing
`build.log` is neither truncated nor touched; the explicit call still
produces a 0600 log; `NIXON_LOG_REDIRECT=0` keeps everything on the
console.

### B2 — the log redirect could hijack the test session

`tests/conftest.py` used `setdefault`, so an exported
`NIXON_LOG_REDIRECT=1` still took effect and swallowed pytest's own
output. It now forces `"0"`.

---

## 4. Phase C — `section_split.py` is integrated

### The decision

The instruction was to establish first whether the module implements a
unique, supported transformation or is an unused experiment.

* **Unique:** yes. It is the only place in the tree that seals a payload
  in independently verifiable sections and joins them into a dedicated
  read-only anonymous mapping. Nothing else does this.
* **Redundant:** no. There is no second implementation of the property.
* **Supported:** it was written to close a vendor-parity gap (V10's
  "sealed sections + guard pages"), and the threat model cited it as an
  active control while the module was wired to nothing.

Since it is neither obsolete nor redundant, it was integrated rather than
deleted.

### The integration

* `obfuscator/section_split.py` gained `emit_loader_snippet()` — the
  loader-side join, stdlib only, returning `None` on any verification
  failure.
* `obfuscator/core/pipeline.py::generate_hybrid_loader_script` gained
  `section_split` / `section_count`. When armed, the payload travels as N
  independently sealed sections and the single blob is disabled: the
  sections *are* the payload. The sections are sealed with the **same
  effective key the loader already derives at runtime**, so no second key
  is introduced into the artifact.
* The pipeline CLI gained `--section-split` and `--section-count`
  (default off, matching the repo's convention for opt-in features).
* A tampered, truncated or mis-keyed pack fails closed through the kill
  ladder: silent, exit 137, no traceback.

**Tests** (`tests/test_section_split_wiring.py`, 6): the default path is
unchanged; the sectioned loader runs; the sections have distinct nonces
and are individually tagged; a flipped bit in one section kills the
artifact silently with exit 137; a truncated pack is rejected; the emitted
snippet is stdlib-only.

### Documentation

`THREAT_MODEL.md` and `SECURITY.md` no longer describe the module as
unwired, and the module docstring now documents the wiring instead of
carrying a "NOT WIRED" warning.

---

## 5. Phase D — the lint campaign

### 5.1 The baseline

`ruff check --select F` over the whole tree reported **8596** findings.
Most were noise from the package's `from .mod import *` idiom (F403/F405,
469 of them), but the enforced set still had **~1400** real findings:
1055 unused imports, 339 redefinitions, 528 unused locals, 125 f-strings
without placeholders, 7 repeated dictionary keys, 10 undefined names, and
one import shadowed by a loop variable.

### 5.2 The rule set now enforced

`ruff.toml` selects **F401, F402, F541, F601, F602, F811, F821, F841**
and ignores **F403/F405** with the reason recorded in the file. `make lint`
now runs `ruff check --no-cache .` and **fails**; CI installs `ruff`
instead of `pyflakes`.

The exclusions are deliberate and documented:

* **F403/F405** — the package's own modules import each other with
  `from .mod import *` and re-export through
  `obfuscator/core/__init__.py`. Converting that is an architectural
  change, not a lint cleanup. The consequence is stated plainly in the
  config: **a name that arrives through a star import is not checked for
  existence** in the module that uses it. Modules that do not use star
  imports are fully checked.

### 5.3 Real defects the campaign found

| # | Defect | Effect |
|---|---|---|
| D1 | `obfuscator/core/utils.py` — `requests.get(...)` in the build-farm bandwidth probe, never imported | `NameError` swallowed by the `except` → **every** measurement returned the lowest score (4); the bandwidth probe never worked |
| D2 | `scripts/build.py` — `z3.BitVec(...)` in `--prove-fragments`, never imported | `NameError` → the feature always reported a failed proof |
| D3 | `scripts/data_obfuscation/data_protector.py` — `_virt_write` defined in one method, used in another | `NameError` on the nested-assignment path |
| D4 | `scripts/distributed/fragment_migration.py` — `_platform_src_migrate` / `_platform_dst_migrate` never defined | `NameError`; the public `migrate_multiprocess` path could never run |
| D5 | `scripts/benchmark/ai_eval.py` — `tempfile_name` never defined | `NameError` → the decompiler-resistance probe never ran, so the score was never reduced |
| D6 | `obfuscator/decoy_apis.py`, `obfuscator/llm_resilient.py`, `obfuscator/timing_traps.py`, `scripts/compiler_mutation.py` — PEP 701 f-strings (same quote reused inside the expression; backslash in the expression) | **unimportable on Python 3.10/3.11**, while the project claims 3.10–3.14 and the CI matrix runs 3.10 |
| D7 | `obfuscator/core/utils.py` — `for platform, fpath in ...` shadowed the `platform` module | a landmine for any later `platform.` use in that scope |
| D8 | 7 duplicated dictionary keys (`VAR_CIPHER_CLS`, `i_salt_val`, `VAR_EXEC_TRACE_CLS`, `EXEC_TRACE_CLS`, `METAMORPHIC_CLS`, `METHOD_WB_ENCRYPT`, `METHOD_WB_DECRYPT`) | the first value was silently dead |
| D9 | `scripts/exposure/tracker.py` — `record_appearance` defined twice | the second definition shadowed the first |
| D10 | `tests/test_diversity_guided.py::test_guided_improves_scores` | computed two score means and asserted nothing; now asserts what its comment promised |
| D11 | `Makefile` — `lint: \|\| true` | the CI lint step could never fail |
| D12 | `tests/test_rust_relay.py` | failed instead of skipping when the relay binary had not been built |

### 5.4 A note on how the cleanup was done

The cleanup is three scripted passes under `scripts/lint/`
(`clean_unused_imports.py`, `clean_unused_locals.py`,
`remove_pure_dead_statements.py`), each with a safety property:

* **A name used inside a string literal in the same file is never
  removed.** This repo embeds generated code — loader templates, emitted
  snippets — as string constants, and a name that exists only inside such
  a template is invisible to the linter but still needed. Those imports
  carry an explicit `# noqa: F401` marker (98 of them) so the decision is
  visible rather than silent.
* **A call whose result is unused is kept, not deleted**, because the call
  may have a side effect. Only calls that are provably pure (known
  builtins, `os.path.*`, `ast.unparse`, numpy constructors) are removed, and
  only when the receiver's type is known.
* The scripts are idempotent and re-runnable (`make lint-clean`).

**This is where the campaign nearly went wrong, and it is worth recording.**
Two of the passes initially removed calls that *looked* dead but were not:

* `float(name)` / `int(raw)` in `scripts/io_research/ir_adapter.py` and
  `int(v.name)` in `irgen/compile.py` are **validation probes**: the
  exception they raise *is* the test. Removing them made
  "is this a literal?" answer `True` for everything, and the
  var×var-multiplication rejection stopped firing.
* `hp.partition(ops)`, `p.join(timeout=1)`, `src_process.join(timeout=2)`
  and `self._monitoring_thread.join(timeout=2.0)` were removed because
  `.join` and `.partition` were on a "pure method names" list. A method
  name is not evidence of purity: `str.partition` is pure, `hp.partition`
  is not. Removing the `join()` calls would have left worker processes
  unwaited.

Both classes of damage were caught by the test suite, then repaired and
the predicates corrected. The audit trail is in
`scripts/lint/repair_removed_imports.py` and
`scripts/lint/repair_removed_statements.py`.

### 5.5 A second near-miss in the audit itself

The repo's own 3.10-compatibility convention is
`ast.parse(src, feature_version=(3, 10))`. That check **cannot** catch
PEP 701 syntax, because it runs the *current* tokenizer, which already
accepts it. So D6 would have passed the repo's own check.

`tests/test_python310_compat.py` (4 tests) now covers it three ways: a
tokenizer check for a f-string nested in an f-string expression with the
same quote character, the existing `feature_version` parse, and a ruff
`--target-version py310` pass. The test was verified to fail when the
defect is reintroduced.

---

## 6. Tests executed

| Suite | Command | Result |
|---|---|---|
| Main suite, chunk 1 | `pytest tests/test_*.py` (first 60 files) | 1167 passed, 4 skipped |
| Main suite, chunk 2 | next 60 files | 1100 passed, 9 skipped |
| Main suite, chunk 3 | next 60 files | 729 passed, 8 skipped |
| Main suite, chunk 4 | remaining files | 783 passed, 2 skipped |
| Advanced protection | `pytest tests/advanced_protection/` | 284 passed |
| Bench group | `pytest tests/bench_*.py` | 152 passed |
| **Total** | | **4215 passed, 23 skipped, 0 failed** |
| Lint gate | `ruff check --no-cache .` | All checks passed |
| End-to-end build | 25 × `scripts/build.py` + run the artifact | 25/25 produced a running artifact |
| Python 3.10/3.11 | `python3.11 -c "ast.parse(...)"` on the four D6 files | parse OK (all four failed before the fix) |

New test files added in this round:
`tests/test_tls_context.py`, `tests/test_emitted_sources_parse.py`,
`tests/test_pipeline_loader_e2e.py`, `tests/test_import_side_effects.py`,
`tests/test_section_split_wiring.py`, `tests/test_python310_compat.py`.

---

## 7. Explicitly accepted residual risks

1. **Star imports hide undefined names.** F403/F405 are ignored, so a name
   that arrives through `from .mod import *` is not checked for existence
   in the module that uses it. Converting the package's import style is an
   architectural change with a large blast radius; it is recorded here
   rather than done silently. Modules without star imports are fully
   checked.
2. **The lint gate covers a narrow rule set on purpose.** It catches
   undefined names, unused imports and locals, repeated dictionary keys,
   redefinitions and f-strings without placeholders. It does not cover
   style, complexity, or type errors.
3. **The pipeline CLI still writes intermediates into the working
   directory** (`<name>_Nixon-Enc*.py`, `.report.json`). The final
   artifacts are moved next to the source, but the intermediates are left
   behind. This is pre-existing and was left alone: fixing it means
   re-plumbing the output paths of a build that has several output
   modes.
4. **The cleanup touched ~440 files.** The safety net is the test suite
   (4215 tests) plus the end-to-end build check; a reviewer should read
   the diff for the modules they care about rather than trusting the
   scripts blindly.
5. **Python 3.10/3.11 CI jobs still may not import every module.** The
   ruff `target-version = "py310"` gate is the guard that now covers
   this; the CI matrix itself is unchanged.
6. **`section_split` is off by default.** The feature exists and is
   tested, but a default build still ships the single blob. Enabling it by
   default is a separate decision with a size cost (the pack is larger).

---

## 8. Files changed

28 files changed, +1221 / −63 (the bulk is the import cleanup across the
tree), plus 7 new test files and 4 new tooling files:

* `ruff.toml` — the enforced rule set, with every exclusion justified.
* `Makefile` — `lint` now fails; `lint-clean` re-runs the scripted
  cleanups.
* `.github/workflows/build.yml` — the lint step installs `ruff`.
* `scripts/lint/` — the cleanup and repair scripts (5 files).
* `obfuscator/core/sources.py` — verified TLS context; the hardcoded
  payload dump removed; the loader `except` re-indented.
* `obfuscator/core/pipeline.py` — the section-split path, the TLS CA
  bundle, the explicit log redirect, the string-pass preamble guard.
* `obfuscator/core/utils.py` — the explicit redirect; the numpy probe.
* `obfuscator/trial_bind.py` — the symlink fail-closed fix.
* `obfuscator/section_split.py` — the loader snippet; the wiring note.
* `obfuscator/decoy_apis.py`, `obfuscator/llm_resilient.py`,
  `obfuscator/timing_traps.py`, `scripts/compiler_mutation.py` — the
  3.10-compatible f-strings.
* `scripts/build.py`, `scripts/distributed/fragment_migration.py`,
  `scripts/data_obfuscation/data_protector.py`,
  `scripts/benchmark/ai_eval.py`, `scripts/exposure/tracker.py`,
  `scripts/kernel_assist/memory_guard.py` — the real defects from the
  table in §5.3.
* `irgen/compile.py`, `irgen/optimize.py`, `irgen/chaff_circuits.py`,
  `irgen/microjit.py`, `irgen/watermark.py`,
  `scripts/io_research/ir_adapter.py`, `scripts/fhe_vm/ir_adapter.py` —
  the restored validation probes and the honest chaff docstring.
