# Protection Techniques and Transformations

**Status:** current catalogue. It describes what each layer changes, how to
switch it on, and what is actually known about its effect. It does not repeat
the vendor's claims or treat a flag's existence as evidence that it works.

Related: [`ARCHITECTURE.md`](ARCHITECTURE.md) for where each stage runs,
[`RESULTS.md`](RESULTS.md) for measured effects, and
[`research/transform-taxonomy.md`](research/transform-taxonomy.md) for the
original taxonomy and the `vm` pass finding.

---

## 1. Why a taxonomy

A count of transformations is not a measure of protection. Renaming five
hundred identifiers is not equivalent to changing control-flow topology: the
first changes spellings, the second changes a representation an attacker must
reconstruct.

Every transform here is classified by the **attacker-visible representation**
it changes:

| Class | Changes | Typical attacker work it costs |
|---|---|---|
| **LEX** | Identifier spellings, annotations, docstrings, formatting | Name recovery; grep; string search |
| **EXPR** | Local expression shape | Algebraic simplification; pattern matching |
| **CFG** | Control-flow topology | CFG recovery; decompilation |
| **DATA** | Literal and value representation | Constant recovery; data-flow analysis |
| **REP** | Code representation or packaging | Tool-based recovery; re-hosting |
| **EXEC** | Execution model | Devirtualisation; emulation |
| **INT** | Integrity only | Tamper detection, not reverse engineering |
| **NOOP** | Nothing | Nothing |

A transform that cannot name the representation it changes is not an
obfuscation. The programme found one such pass: configurations containing
`"vm"` believed they enabled virtualisation, but no transformer, phase, or
pipeline branch read the option. That is recorded in
[`research/transform-taxonomy.md`](research/transform-taxonomy.md).

---

## 2. The AST ladder (`--opt-level 0..5`)

One dial, 17 canonical flags (`obfuscator/opt_levels.py`). Default **4**,
which enables 14.

| Flag | Class | What changes | Notes |
|---|---|---|---|
| `cfg_flatten` | CFG | State-dispatch loop replaces structured control flow | Requires block-order correctness; a shuffled chain once executed blocks out of order |
| `opaque_predicates` | CFG | Branches whose condition is always true/false | Two of twelve builders once emitted unsatisfiable predicates; functions returned `None` |
| `bogus_exceptions` | CFG | Fake exception paths | — |
| `mba_subs` | EXPR | Arithmetic rewritten to mixed boolean-arithmetic forms | Linear MBA is simplifiable by public tools; treat as a speed bump, not a wall |
| `fragment_strings` | DATA | String literals encoded/encrypted behind lookups | — |
| `unicode_ids` | LEX | Identifier glyphs | — |
| `junk` | LEX | Dead statements and noise | — |
| `decoys` | LEX | Decoy content | The only transform whose RNG was not pinned, which caused level-3 builds to differ between runs |
| `minify` | LEX | Formatting and whitespace | — |
| `const_unfold` | EXPR | Constants expanded into expressions | — |
| `call_indirection` | CFG | Calls routed through tables | A shared table name once let one assignment silently replace another |
| `reflection` | REP | Reflective call paths | — |
| `dataflow` | DATA | Value splitting / affine encoding | Storage virtualisation once deleted a cell a nested `nonlocal` needed |
| `watermark` | INT | IR watermark + refuse-to-run gate | Needs IR; conflicts with `--skip-irgen` |
| `variant_pool` | REP | Cloned crown-jewel functions | Increases binary size |
| `fragmentation` | REP | Semantic fragmentation | — |
| `provenance` | LEX | Provenance removal | — |

Level 0 enables none of the 17. It is **not** a byte-identical copy through
the CLI: always-on passes (symbol rename, integrity checksums, string sealing,
adversarial injection) still run. `--skip-obfuscate` is the byte-identical
path (verified: 2,635 bytes in, 2,635 bytes out, `diff` clean). The ladder is
the only way to enable a transform; individual transforms are disabled with
`--no-cfg-flatten`, `--no-opaque-predicates`, `--no-bogus-exceptions`,
`--no-mba-subs`, `--no-fragment-strings`, `--no-unicode-ids`. There is no
`--mba-subs` because the ladder owns enablement.

### 2.1 Beyond the ladder

| Flag | Class | What it does | Status |
|---|---|---|---|
| `--ssa-mutation` | IR | SSA-level mutation variants | Experimental |
| `--cfg-mutation` | CFG | CFG mutation variants | Experimental |
| `--class-dispatch` | CFG | Class-based dispatch rewriting | Experimental |
| `--struct-randomization` | DATA | Structure randomisation | Experimental |
| `--speculation-obfuscation` | EXPR | Speculative-execution-shaped rewriting | Experimental |
| `--data-obfuscation` | DATA | Storage virtualisation / inlining | Experimental; several defects fixed |
| `--micro-fragment` | REP | Micro-fragmentation | Experimental |
| `--fragment` | REP | Semantic fragmentation | Experimental |
| `--per-exec-recompile` | REP | Recompile per execution | Experimental |
| `--self-healing` | INT | Rebuild on tamper | Experimental |

These are not on the default path. "Experimental" here means the code exists
and has tests, but it has not been evaluated against an attacker and has a
history of edge-case defects.

---

## 3. Semantic lowering (`--lowering`)

Rewrites covered call sites to `_nxk_*` kernel calls across **20 families /
140 verified operations**. Families default ON: io, scalar, string, container,
service, protocol, function, import, fusion, list, dict, set, tuple, bytes,
range. Opt-in: arithmetic, truth, slice, format, augassign.

What it changes: the call graph and the builtin surface an analyst sees. The
artefact no longer calls `len`, `str.join`, and similar names directly; it
calls per-build-renamed kernel symbols.

What it costs: the Python shim adds **1.46×–3.84×** per family
(`obfuscator/lowering_DESIGN.md`). The vendor's 0.19×–1.56× figures describe a
native kernel and are **not reproduced** here. Lowered artefacts require
`obfuscator/lowering_shim.py` on `PYTHONPATH`.

---

## 4. Counter-REA shields and deception

Ported from [BLA](https://github.com/qybaihe/bla) and extended. On by default
in the **packed loader** (`--anti-rea`, level `balanced`). `scripts/build.py`
does not expose `--anti-rea`/`--anti-rea-level`; its `--adversarial-injection`
is a different phase. A bare `--anti-rea` is therefore a no-op on the loader
(default true); `--no-anti-rea` is the switch that matters.

| Control | What it tries to do | Honest limit |
|---|---|---|
| Architecture-mirage chaff | Make the artefact look like a different architecture | An analyst who runs it sees the truth |
| Canary credentials / URL parser differentials | Detect exfiltration or analysis environments | Client-side; editable |
| Evidence-contract poison | Corrupt the evidence an automated analyst collects | Targets a specific workflow |
| Decoy call graph | Weave plausible but false call edges into real functions | Distorts a call-graph recovery, not the program |
| BPE token amplifier | Increase token cost for LLM-assisted analysis | Model-dependent; not measured here |
| Shadow business logic | Present plausible alternate behaviour | Requires the analyst to trust the decoy |
| Aliasing illusion | Make distinct objects appear aliased | Local reasoning only |
| Crash-trace decoys / diagnostic rabbit holes | Waste analyst time on false leads | Wastes an automated analyst's time too |
| Classifier-directed bait (`--anti-rea-level`) | Intensity dial for the above | On by default; every combination is built and run in CI |

Deception flags include `--poison-apis`, `--poison-imports`,
`--poison-call-graph`, `--poison-paths`, `--poison-protocols`, `--poison-all`,
`--decoy-apis`, `--honey-functions`, `--reasoning-traps`, `--trap-depth`,
`--prompt-resistance`, `--attention-poison`, `--llm-resilient`,
`--multi-agent-deception`, `--storyline-count`, `--provenance-poison`,
`--manipulation-detector`, `--false-confidence-audit`, `--self-critique`,
`--red-team`.

These are **not measured against an adversary** in this repository. They are
implemented and tested for "does the build still run"; their effect on an
analyst is a hypothesis. The counter-REA literature (BLA) reports effects in
its own setting; those numbers do not transfer automatically. The maximum
practical build uses `--anti-rea-level maximum`; that is a size/build-time
increase whose security effect is unmeasured — see
[`MAXIMUM_SECURITY.md`](MAXIMUM_SECURITY.md).

---

## 5. Runtime integrity and anti-tamper

| Gate | Default | Off switch | What it checks |
|---|---|---|---|
| Frozen-stdlib snapshot | **on** | `NIXON_SNAPSHOT_OFF`, `--no-snapshot` | Stdlib files match a build-time snapshot |
| Stdlib function audit | **on** | `NIXON_STDLIB_AUDIT_OFF`, `--no-stdlib-audit` | Called stdlib functions match fingerprints |
| Audit-hook plant detector | **on** | `--no-audit-hook-plant` | Detects an injected audit hook |
| Loader traceback suppression | **on** | — | Hides paths and internals from tracebacks |
| BYOVD driver check | off (`--driver-check`) | read-only | Enumerates loaded-driver names and compares against a public blocklist |

Structural anti-tamper, all opt-in unless stated:

| Flag | Mechanism | Status |
|---|---|---|
| `--section-split` (loader) | Shamir (n=3, k=2) threshold key + fragmented decoder | Implemented, tested |
| `--rolling-keys` | Key evolution across sections | Experimental |
| `--temporal-keys` | Time-window key evolution | **Inert** — produces metadata nothing reads; ~19 s of hashing |
| `--history-bound-decryption` | Bind decryption to execution history | Experimental |
| `--state-isa` | Per-build instruction encoding | Experimental |
| `--attestation` | Remote attestation | Experimental |
| `--challenge-response` | Challenge-response gate | Experimental |
| `--crypto-binding` | Fragment binding chain | **Build-time validation only**; nothing decrypts at run time |
| `--section-split` | Threshold sharing | Opt-in; in the loader path |

The inert and build-time-only flags are documented because a reader who finds
them in `--help` would otherwise assume they protect something. Their rows in
[`CLI.md`](CLI.md) carry the warning.

---

## 6. Licensing, binding, and provenance

| Flag | Effect | Status |
|---|---|---|
| `--hwid` + `--hwid-lock` | Bind to a machine, or to a static `HWID:<hex>` | Implemented; loader only |
| `--trial` (`90s 1m 1h 1d 1w 1mo`) | Expiry enforcement | Implemented; loader only |
| `--watermark` + `--verify-watermark` | Semantic watermark in IR + refuse-to-run gate | Implemented; needs IR |
| `--verify-watermark-survivability` | Probe whether the mark survives transforms | Research instrument |
| `--name-gate` / `--rename-internal` | Per-build token map / rename proven-internal names | Opt-in |
| `--licence-token PATH` | Signed Ed25519 token; payload key masked with it | Implemented; packed emitter only |
| `--customer-salt` | Domain-separated per-customer mask | Implemented |
| `--sign-key-env VAR` | Signing key from the environment | Implemented |
| `--embed-proof` / `--zk-state` / `--remote-unlock` | Proof / ZK / remote unlock | Research-only |
| `--dist-watermark` / `--provenance-replace` | Distributed watermark / provenance replacement | Research-only |

The licence token is the strongest client-side binding currently implemented:
an artefact built with `--licence-token` derives its payload key from the
token's key material, so an artefact without its token decrypts to garbage.
It is still a client-side check; [`LICENSING.md`](LICENSING.md) states the
three things it does not do.

---

## 7. Packaging and native backends

| Flag | What it produces | Status |
|---|---|---|
| `--pytoc` | Cython-compiled payload | Best-effort; never fails the build |
| `--pyinstaller-spec` | PyInstaller spec | Best-effort |
| `--simd-vm` | C SIMD VM (SSE on x86, scalar fallback) | Implemented; opt-in |
| `--fhe-vm` | FHE VM | Research-only |
| `--oram` | ORAM storage backend | Research-only |
| `--rop` | ROP-oriented compilation | Research-only |
| `--sgx` / `--tee` | SGX / TEE partitioning | Research-only |
| `--cross win,linux,macos,linux-arm` | Cross-compilation | Best-effort; needs toolchains |
| `--payload-dispersal` / `--split-bootstrap` | Dispersed payload / split loader | Experimental |
| `--generate-payload-h` | Embed payload in a C header | Implemented |
| `--rust-exe` / `--python-dll` | Embed a Rust launcher / Python DLL | Implemented; build-host inputs |

---

## 8. Flags that do not do what their names suggest

Recorded here and in [`CLI.md`](CLI.md), because the alternative is a reader
discovering it in the implementation:

| Flag | Reality |
|---|---|
| `--temporal-keys` | **Inert.** Hashes metadata that nothing reads; its verifier proves nothing. ~24 s per build. |
| `--crypto-binding` | **Build-time validation only.** The chain secret is not written to the artefact; nothing decrypts at run time. |
| `--randomization-seed` / `SEED` | Seeds structure randomisation, speculation, and CPU-port phases. It does **not** make builds byte-reproducible; thousands of values are drawn from `secrets`. |
| `--seed` | Reduces variation but is only partially wired: the CLI path does not pass it into `ObfuscationTransformer`, so string keys remain `secrets`-random. Same-seed builds differ by a few bytes. |
| `--build-id` | Seeds the `--pytoc` lowering kernel only; recorded in the manifest. Not a whole-build seed. |
| `--lock-hwid` | Registers a licence and seeds the polymorphic-map/VM RNG. It does **not** "seed the build deterministically" as its help says. |
| `--pin-structure` | Pins structure, not key material; two builds differed (1,882,254 / 1,882,385 bytes). |
| `--cfg-mutation`, `--class-dispatch`, `--ssa-mutation`, `--state-isa`, `--per-exec-recompile`, `--self-healing` | **Metadata-only.** The phase writes a JSON config; the runtime modules were archived and no component reads it. |
| `--watermark` + `--skip-irgen` (build.py) | Logs a conflict and writes an IR watermark, but the watermark string is **not** in the emitted AST artefact (`grep` count 0). |
| `--opt-level 0` | Disables the 17 ladder transforms, **not** the always-on passes. Not a copy; use `--skip-obfuscate`. |
| `--fast` + `--strict-detections` | Share one dest; the last flag on the command line wins. |
| `--hwid-lock` without `--hwid` | Silently disabled (`hwid_lock = flag and bool(hwid)`). |
| `--licence-token` + `--customer-salt` | The token's `key_material` overrides the salt. |
| `"vm"` pass name (research generator) | **No consumer.** The legacy generator's `vm` pass set entry enabled nothing. |
| `--code-genome` | Real but expensive: defaults to 50 generations × 30 population = 1,500 fitness evaluations; did not finish in 300 s on a three-line file. With `--genome-generations 2 --genome-population 4` it takes 2 s. |
| `--driver-check` | Read-only enumeration of the **host's** drivers, not protection of the artefact. |

---

## 9. What is actually known about effect

| Claim | Evidence | Status |
|---|---|---|
| Lowering adds 1.46×–3.84× overhead per family | `obfuscator/lowering_DESIGN.md`; `scripts/benchmark/lowering_perf.py` | **Measured** |
| A three-line payload at O4 becomes ~15 KB | README quick start, 2026-11-10 | **Measured** |
| A maximum-security build takes ~405 s on a three-line payload | README, 2026-11-10 | **Measured** |
| Level 3 builds differed between runs until `decoys` was seeded | `research/transform-defects-2026-11.md` | **Measured** |
| Opaque predicates silently returned `None` about one build in twelve | `research/paper-draft.md` §6.2 | **Measured, fixed** |
| Transform-family diversity raises identification cost | Research programme | **Negative result**: the effect was callable count |
| Symbol stripping / MBA / packing stop a capable analyst | Not measured here | **Not claimed** |

The last row matters. The repository has no measurement of these layers
against a frontier automated analyst. The research programme measures
identification cost for a specification-derived attacker on small programs;
that is a different question, and it does not license extrapolation to the full
protection stack.
