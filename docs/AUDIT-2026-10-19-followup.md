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

### 1.1 The residuals round

A second round closed the four residual risks the first round recorded
(§6). It found two more real defects, both of them `NameError`s that
the test suite could not see because no test exercised the path:

| # | Finding | Severity | Status |
|---|---|---|---|
| R1 | `build_project` called `datetime.strptime` for `--expire`, but the cleanup had removed the module-level `from datetime import datetime`. The `except Exception` around it swallowed the `NameError` and reported **"Bad --expire date"** for *every* date, so `--expire` aborted every build and the expiry was never applied | **HIGH** | Fixed |
| R2 | The CLI's `print_usage` passed `file=_console`, but a star import never brings underscore names across — every argparse error produced a `NameError` instead of a usage message | MEDIUM | Fixed |
| R3 | The lint gate was **unpinned** (`pip install ruff`), so a ruff release could turn a green tree red with no change to the code | MEDIUM | Fixed |
| R4 | The chaff-circuit cleanup changed the **order** in which IR instructions were emitted, so the generated artifact differed from the pre-cleanup one | MEDIUM | Fixed |

The four residuals themselves — undefined names hiding behind star
imports, the cleanup scripts not being safe by construction, the
pipeline CLI writing into the caller's directory, and the section-split
flag path being untested end to end — are closed in §6.4 through §6.7.

**Verification (this round):** 4225 tests passed, 23 skipped, 0 failed;
`make lint` clean (ruff plus a runtime undefined-global check over the
whole live tree); 10/10 default and 8/8 section-split builds produce an
artifact that runs.

> Superseded by [`docs/AUDIT-2026-10-20.md`](AUDIT-2026-10-20.md), the
> CLI audit round: it found that the pipeline CLI was dropping 14 of its
> own flags, that the build configuration was untracked, and that the
> lint gate was unpinned.

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

## 6. The residuals round — closing what §8 left open

The four-phase round above left four residual risks recorded rather than
fixed. This round closes them, and it found three real defects on the
way — two of them introduced by the four-phase round itself.

### 6.1 "Fails why?" — the lint step was unpinned

The first CI run after the push *was* the first to enforce lint. The
gate itself was not failing: `ruff check --no-cache .` was clean on this
tree, and it is still clean. The risk was different and worth stating
plainly — **the gate was not reproducible**. The CI step ran
`pip install ruff`, which installs whatever ruff is current that day.
A ruff release that changes the behaviour of an enforced rule (F811
detection, F401 in a package `__init__`) would turn a green tree red
with no change to the code, and the failure would look like a code
problem rather than a tooling change.

Fixed: ruff is pinned to `0.16.1` in `requirements-dev.txt`, and CI
installs from that file instead of resolving the latest release. The
pin is a deliberate one-way door — bumping it is a visible act.

### 6.2 Auditing the earlier commits, mechanically

The four-phase round's cleanup removed 280 statements across the tree,
and the only evidence it had not broken anything was the test suite.
That is not enough, because the suite does not cover every path: the
"load-bearing removal" class (a statement whose *call* was the point)
is invisible to a test that never exercises that path.

So the audit was made mechanical.
`scripts/lint/audit_commit_removals.py` compares a commit against its
parent structurally (AST, not text), lists the statements that
disappeared, and — the part that matters — isolates the removals that
**dropped a call**, because a dropped call is the only kind of removal
that can change behaviour. f-strings are folded before comparison, so
the F541 prefix cleanup does not read as a removal.

Result over the two commits:

| Commit | Statements removed | Dropped a call | Unexplained |
|---|---|---|---|
| `181b151` (the first audit round) | 20 | 7 | 0 |
| `1a8c9df` (the four-phase round) | 280 | 65 | 0 |

Every one of the 72 dropped calls was classified by hand. The
overwhelming majority are pure reads (`dict.get`, `sorted`, `len`,
`set`, `ast.unparse`) whose result was unused. The rest are the
deliberate changes of those rounds: a moved `open('build.log')`, a
changed `generate_hybrid_loader_script` signature, an extended
`argparse.Namespace`, a repaired `py_compile.compile` call, and the
extended `_rewrite_if`/`_rewrite_stmt` signatures.

**One was not deliberate and has been repaired**: in
`irgen/chaff_circuits.py`, the cleanup had turned

```python
min_val = block.and_(t, block.xor(t, a, b).result, lt).result
```

into a bare `block.and_(...)`, which kept the *call* but changed the
**order** in which IR instructions were emitted (the `and_` now
followed the `xor` instead of preceding it). The generated IR is
different, which means the generated artifact is different. The
original order has been restored and the output is now verified
byte-for-byte identical to the pre-cleanup tree.

### 6.3 Two real defects, found by the audit and the runtime checker

**A `NameError` in the `--expire` path.** The cleanup removed the
`from datetime import datetime` tail from the mega-import line at the
top of `obfuscator/core/pipeline.py` — the line also carried
`from io import StringIO`, and both looked unused to a linter that
could not see the uses. `build_project` then called
`datetime.strptime(args.expire, ...)` at module scope, where `datetime`
was no longer bound.

The failure was worse than a crash. The call sits inside

```python
try: exp_ts = datetime.strptime(args.expire, "%Y-%m-%d").timestamp()
except Exception: UI.fatal(f"Bad --expire date {args.expire!r}: expected YYYY-MM-DD")
```

so the `NameError` was swallowed and reported as a **bad date** —
for *every* date, including a perfectly valid one. `--expire` aborted
every build with a misleading message, and the expiry it was supposed
to apply was never applied. The test suite did not catch it because no
test passed `--expire`.

Verified both ways: with the import removed, a build with
`--expire 2030-01-01` aborts with "Bad --expire date '2030-01-01'";
with it restored, the build completes and the report records
`"expiration": "2030-01-01"`.

**A `NameError` in the CLI's usage message.** `pipeline.py` defines a
`ConsoleArgumentParser` whose `print_usage` passed `file=_console`.
`_console` lives in `obfuscator/core/utils.py`, and **a star import
never brings underscore-prefixed names across** — so `_console` was
never bound in `pipeline.py`, and every argparse error (an unknown
flag, a missing argument) produced a confusing `NameError` instead of a
usage message. This one predates the four-phase round: it has been
broken since the star import was introduced. The fix looks the name up
on the module (`_nixon_utils._console`), which is also more correct:
it reaches the *current* console handle rather than a stale copy.

Both were found by the runtime checker described next, not by reading
the diff. The first was found because the checker resolves every global
read in the live tree; the second was found because the checker was
extended to nested classes after the first fix, and the `print_usage`
override is a class defined inside a function.

### 6.4 Closing residual 1 — undefined names are now detectable

The residual was: *star imports hide undefined names; F403/F405 are
ignored, so a name arriving through `from .mod import *` is never
checked for existence.*

The consequence is now closed, though the import style is unchanged.
`scripts/lint/check_undefined_globals.py` resolves the problem at
runtime instead of statically, which is a stronger check than F405's
approximation: for every module in the live tree, every name its code
objects load from the global scope must resolve — to a binding in the
module's own namespace, to a builtin, to a name the module declares
`global` and assigns, or to an optional dependency imported inside a
`try: ... except ImportError` (where the guard is what makes it safe).

It runs as part of `make lint`, so it is enforced in CI alongside ruff.
The first run of it against the tree found the `datetime` defect above.

Getting the checker to zero false positives took four refinements, each
of which was a real blind spot rather than a fudge:

* a function's globals belong to the module that **defined** it, not
  the one that imported it — resolving them in the importing module
  produced 2452 false positives;
* a name bound by an import inside `try/except ImportError` is
  *conditional*, not undefined;
* code from another module (e.g. `dataclasses.dataclass`, whose
  internals reference `_process_class`) is not ours to judge;
* a class defined **inside a function** is not in `vars(module)` — its
  methods are still ours, and that is where the `_console` defect hid.

### 6.5 Closing residual 2 — the cleanup scripts are safe by construction

The residual was: *the cleanup touched ~440 files, so the suite is the
safety net, not the scripts.* The suite is a net; it is not a
guarantee, and it demonstrably has holes (the `--expire` path had no
test at all).

The scripts are now constrained so the two damage classes cannot recur:

* **A call inside a `try` whose handler catches an exception is never
  removed.** The exception it raises may *be* the test:
  `float(name)` in a `try/except ValueError` answers "is this a
  number?", and deleting it makes the check answer "always yes". This
  was the first near-miss, and it broke detection logic in
  `irgen/compile.py` and `irgen/optimize.py`.
* **An import that is the only statement in a `try/except ImportError`
  is never removed.** That import is an availability probe; deleting it
  leaves the `except` branch unreachable and turns the probe into a
  lie. This is what broke `_check_aes_ctr` earlier.
* **A method call on an unknown receiver is never removed.** A method
  *name* is not evidence of purity: `str.partition` is pure,
  `hp.partition` is not. This was the second near-miss, and it
  silently dropped `hp.partition(ops)` and `p.join(timeout=1)`.

`tests/test_lint_cleanup_safety.py` pins all three, and the test is
verified to fail when the guard is removed: with the guard removed,
`_is_numeric("abc")` returns `True` — exactly the bug the class
produced.

### 6.6 Closing residual 3 — the pipeline CLI no longer writes into the CWD

The residual was: *the pipeline CLI still writes intermediates into the
working directory.* The intermediates — the packed variants and the
`.report.json` — are now written next to the source file. A build run
from a random directory now leaves that directory completely untouched;
`tests/test_pipeline_cwd_clean.py` asserts exactly that (no leftover
files at all) and that the outputs land next to the source.

Two robustness details came with it: `generate_report` now uses
`os.path.splitext` instead of `str.replace('.py', ...)`, because the
output path is now absolute and a directory whose name contains `.py`
would otherwise be mangled; and the CLI's usage message no longer
raises `NameError` (§6.3).

### 6.7 Closing residual 4 — the section-split flag is covered end to end

The residual was: *`section_split` is off by default.* The off-by-
default part is a deliberate design decision, not a defect: the pack is
larger, and turning it on for everyone is a product decision, not a
cleanup. What *was* a gap is the flag path: the loader-level tests
drove `generate_hybrid_loader_script` directly, so a break between the
CLI flag and the loader would have left the feature silently inert —
which is precisely the state the module was in before it was wired up.

`tests/test_section_split_cli.py` now drives the real command line: a
build with `--section-split` must produce a running artifact, and the
artifact must differ from the default build (the pack is a sealed
literal by then, so it cannot be grepped — the evidence is
behavioural). The default path is separately asserted to be unchanged.

### 6.8 "Never repeat them"

**The PEP 701 gap.** The repo's own 3.10 check cannot catch PEP 701,
because `ast.parse(feature_version=(3, 10))` runs the *current*
tokenizer, which already accepts it. The guard that does catch it is
the ruff `target-version = "py310"` gate (ruff parses with a 3.10
grammar), and the CI version matrix, whose 3.10 and 3.11 jobs import
the modules and would fail on the import error. `tests/test_python310_compat.py`
keeps the three-way check. The gate is now pinned, so it cannot
silently change behaviour under it.

**The cleanup near-misses.** Both are now impossible by construction
(§6.5) and pinned by tests that are verified to fail without the fix.
The audit tool remains available for any future bulk change:
`make audit-commit` prints what the last commit removed and which of
those removals dropped a call.

---

## 7. Tests executed

| Suite | Command | Result |
|---|---|---|
| Main suite, chunk 1 | 38 files | 772 passed, 1 skipped |
| Main suite, chunk 2 | 39 files | 833 passed, 12 skipped |
| Main suite, chunk 3 | 39 files | 614 passed |
| Main suite, chunk 4 | 40 files | 412 passed, 4 skipped |
| Main suite, chunk 5 | 39 files | 619 passed, 4 skipped |
| Main suite, chunk 6 | 39 files | 539 passed, 2 skipped |
| Advanced protection + bench group | `pytest tests/advanced_protection/ tests/bench_*.py` | 436 passed |
| **Total** | | **4225 passed, 23 skipped, 0 failed** |
| Lint gate | `make lint` (ruff + runtime undefined-globals) | All checks passed; 0 undefined globals |
| End-to-end build, default | `scripts/lint/e2e_build_check.py 10` | 10/10 produced a running artifact |
| End-to-end build, section-split | `scripts/lint/e2e_build_check.py 8 --section-split` | 8/8 produced a running artifact |
| Commit removal audit | `scripts/lint/audit_commit_removals.py --calls-only` | 0 unexplained dropped calls |

The suite was run in six chunks plus the bench group because the host
was under memory pressure (about 1 GB available of 7.6 GB); a single
run was killed by the harness before this. The numbers above are the
sum of the chunks and account for every one of the 4248 collected
tests.

New test files added in the four-phase round:
`tests/test_tls_context.py`, `tests/test_emitted_sources_parse.py`,
`tests/test_pipeline_loader_e2e.py`, `tests/test_import_side_effects.py`,
`tests/test_section_split_wiring.py`, `tests/test_python310_compat.py`.

New test files added in this round:
`tests/test_undefined_globals.py`, `tests/test_lint_cleanup_safety.py`,
`tests/test_pipeline_cwd_clean.py`, `tests/test_section_split_cli.py`.

---

## 8. Residual risks

The four residuals of the previous round are closed (§6.4 – §6.7). What
remains:

1. **The lint gate covers a narrow rule set on purpose.** It catches
   undefined names, unused imports and locals, repeated dictionary keys,
   redefinitions and f-strings without placeholders, plus — now — every
   global read in the live tree. It does not cover style, complexity, or
   type errors.
2. **The import style is unchanged.** The package still uses
   `from .mod import *`, which is why F403/F405 stay ignored. The
   *consequence* of that (undefined names hiding behind star imports)
   is closed by the runtime checker; the style itself is an
   architectural change with a large blast radius and is still not done.
3. **`section_split` is still off by default.** Deliberate, and now
   covered by an end-to-end test in both directions. Turning it on for
   every build is a product decision with a size cost.
4. **The ruff pin can go stale.** A pinned linter is reproducible but
   not current: new rules stay off until someone bumps the pin. That
   is the intended trade — a bump is a visible act.
5. **Host-dependent test numbers.** The suite was run in chunks under
   memory pressure; the totals are the sum of the chunks, not a single
   run, and the host's memory state is not a property of the code.

---

## 9. Files changed

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

### 9.1 Files changed in the residuals round

* `requirements-dev.txt` — **new**: the ruff pin.
* `.github/workflows/build.yml` — installs from `requirements-dev.txt`
  instead of resolving the latest ruff.
* `ruff.toml` — the F403/F405 rationale now records that the
  consequence is closed by the runtime checker.
* `Makefile` — `lint` runs the runtime checker too; new `e2e` and
  `audit-commit` targets.
* `scripts/lint/check_undefined_globals.py` — **new**: the runtime
  undefined-global checker.
* `scripts/lint/audit_commit_removals.py` — **new**: the structural
  commit-removal auditor.
* `scripts/lint/e2e_build_check.py` — **new**: the build-must-run check.
* `scripts/lint/remove_pure_dead_statements.py` — never removes a call
  inside a `try` whose handler catches an exception.
* `scripts/lint/clean_unused_imports.py` — never removes an import that
  is an availability probe.
* `obfuscator/core/pipeline.py` — the `datetime` import restored; the
  CLI's `_console` lookup fixed; the outputs now land next to the
  source; `generate_report` uses `splitext`.
* `irgen/chaff_circuits.py` — the IR emission order restored.
* `tests/test_undefined_globals.py`, `tests/test_lint_cleanup_safety.py`,
  `tests/test_pipeline_cwd_clean.py`, `tests/test_section_split_cli.py`
  — **new**.
