# The emitter pipeline

What happens between "here is a payload" and "here is an artefact", which
pass may rename what, and where a change is allowed to be inserted.

This exists because four attempts to change the loader failed for the same
reason -- the change was written into a place whose invariants had not been
established -- and each failure looked like a code bug rather than a
misplacement. Read this before touching `sources.py` or the assembly block
in `build_project`.

## Two artefact producers

| producer | command | artefact | payload key |
|---|---|---|---|
| source emitter | `scripts/build.py --payload` | transformed source (decoys, integrity comment) | **none** |
| packed emitter | `python3 -m obfuscator.core.pipeline build` | loader + encrypted payload blob | `BLOB_KEY` |

They are not variants of one thing: the source emitter has no encrypted
payload at all, which is why the licence flags are refused there. Anything
about keys, sections or the packed core applies to the second only.

## Pass order (packed emitter)

Inside `build_project`, in this order. The line numbers drift; the order
does not.

1. **Template fill.** `raw_script = (LOADER_HEAD + LOADER_BODY).format(
   **build_context)`. Every `{PLACEHOLDER}` is resolved here or not at
   all -- a placeholder with no context entry raises `KeyError`, which is
   why shared templates must not grow placeholders that other callers do
   not supply.
2. **Core-integrity insertion.** The SHA-256 of the packed `nixon_core.so`
   is baked into a self-check that runs before the core is loaded.
3. **Anti-debug insertion.** The detection call and the tracer poison are
   inserted next to `BLOB_KEY`. This must happen *before* step 4.
4. **Symbol rename.** `_rename_markers(raw_script, marker_token)` rewrites
   the fixed runtime vocabulary (`_NX_ATTR_MAP`, `_NX_SENTINEL`,
   `_NX_SKIP_ON`, `_NX_CI_ON`, `_NX_POISON_KEY`) into per-build names and
   asserts that the kill ladder and the marker map are consistent. A
   partial rename is worse than a failed build: it raises `NameError` at
   run time.
5. **String-table pass.** `Nixon_Enc_strings(raw_script)` turns every
   string literal into a lookup against an encrypted table. It is
   line-oriented, so it cannot see structure across lines -- see the
   insertion rules.
6. **Table build.** `get_Nixon_Enc_table()` builds the encrypted table and
   its key from `STRING_TABLE_KEYS`.
7. **Signing and packing.** The self-check anchors are filled, the script
   is HMAC-signed, and the payload is sealed into sections.

## Insertion rules

These are the ones that cost a round each to learn.

- **Surviving the rename.** Code that calls a renamed symbol must be
  inserted at step 2/3, never after step 4. Appended afterwards, the call
  names something the renamer has already replaced; if the call sits in a
  `try/except` it fails *silently* and the feature looks present but does
  nothing. That is how the anti-debug pass stayed dead code.
- **Surviving the string pass.** Do not write implicit string
  concatenation (`"a"` on one line, `"b"` on the next). The string pass
  rewrites each literal separately, producing two lookups with no `+` --
  a `SyntaxError` in the emitted file. One literal per string, or an
  explicit `+`.
- **Key material crossing pack/run.** Any value the payload is encrypted
  *with* at pack time must be reproduced at run time from something the
  artefact carries. Values that are emitted (the blob key, the core hash,
  the section tags) satisfy this; values that are re-drawn do not. Round 3
  failed exactly here: seeding the stream changed the pack-side value
  without changing the run-side derivation, and the artefact failed its
  own magic check.
- **Never make a build flag able to produce a non-running artefact.** A
  build that succeeds is not evidence the artefact works -- every landed
  change in this area was verified by *running* the artefact, and the
  tamper cases by breaking it.

## Entropy inventory

Where randomness enters, and what it costs to make a build reproducible
(measured, not estimated):

| source | sites | notes |
|---|---|---|
| `secrets.token_bytes/hex`, `randbelow`, `choice` | ~20 in `build_project`, **~3,650** total per build | per-string ChaCha20 keys/nonces, VM op-map shuffle, encoding layer choice |
| `os.urandom` | ~6 | blob key, nonce, entropy marker, salts |
| `time.time()` | 2 | `build_timestamp` is emitted |
| `random` (module) | many | names, decoys, structural choices |
| module-level | `VARS`, `STRING_TABLE_KEYS`, `STRING_SESSION_KEY` | fixed per process, before any argument is parsed |

`--randomization-seed` was an attempt to pin all of this and was removed:
partial pinning still differed, and pinning the values that cross the
pack/run boundary produced artefacts that failed their own check. A
reproducible build needs one RNG threaded through `sources.py`'s emitters,
not a seeding patch on top.

### Measuring structure: use the AST, not the bytes

The byte diff is the wrong instrument for structural determinism: the
artefact is ~66% identical by line count regardless, and the differences
are dominated by the key-encrypted string table, which no amount of
structural pinning can change. Two builds can have *identical structure*
and still differ in thousands of lines.

The right measure is the AST with constants stripped: parse both
artefacts, replace every `ast.Constant` value with a marker, and compare
`ast.dump`. That isolates shape -- names, nesting, statement order -- from
data.

Using it found two structural sources the byte diff could never show:

- the marker token (`VARS["MARKER_TOKEN"]`, minted at import), which names
  the getattr table and every kill-ladder entry;
- the whole `VARS` name table, also minted at import, before any seed can
  exist.

Pinning both under a flag moved the first structural divergence from byte
offset ~28k to ~39k, then to ~154k once the structure RNG also covered the
encoding choices and the VM op-map. At that point the identifiers matched
exactly -- the pinned `PART_PREFIX` names appear identically on both sides
-- and the divergence had moved to statement level, deep inside the emitted
payload, where the long tail of per-part and per-string draws lives.

Round 37 pinned the **emitted** key material as well -- safe, because the
loader reads those values from the artefact rather than re-deriving them.
That was round 3's mistake: it pinned the derivation *inputs* (build id,
salts), which is what desynchronised pack from run. With the keys pinned
too, the normalised line diff between two builds fell from 2,254 to **350**
and the first structural divergence moved 154k -> 214k; the remaining
difference is a class-method name minted at import. The artefact still
runs, still refuses a tampered core, and still refuses a tracer.

Round 32 converted fourteen structure call sites in `sources.py`
(`secrets.randbelow`/`choice`/`token_hex` in the packaging and encoding
paths) to injectable helpers whose default is unchanged, and added the
flag that sets them. The first structural divergence moved again,
~154k -> ~172k, and it is now a `BinOp` opcode difference (an `Add` where
the other build has a `BitOr`) -- the MBA expression chooser in
`transforms.py`, which is the next site on the list. Still not converged,
so the flag was reverted again.

That is where it stands: the *names* can be made to agree, the *statements*
need the whole ~20-site list converted. The flag was reverted rather than
shipped on a partial claim. Anyone continuing this should keep the cycle
honest: pin, build twice, compare `ast.dump` with constants stripped, and
only claim progress when the divergence index actually moves.

### The classes cannot be separated by a switch

Attempted in round 21: a `--pin-structure` flag that seeded the module RNG
and the VM op-map, leaving key material alone. The artefact built and ran,
and the normalised diff between two such builds was **2,228 lines** --
essentially unchanged from the 2,254 measured without it.

The reason is structural: the bulk of the per-build variation comes from
`secrets` called at individual sites, and the same sites mint both
structure (op-map shuffles, encoding choices) and key material (session
keys, salts). There is no switch that separates them; the separation has to
be done call by call, which is the ~20-site and ~3,650-draw work list
above. The flag was removed rather than shipped with a help text it could
not honour.

### The emitted session key is a pre-pin copy

Round 52 restored the pre-string dump (and verified the files existed
before trusting the diff). The pre-string source already differs, at the
session-key line, so the residue is in the assembly, not the string pass.

Tracing the pin showed it *does* run -- `[pin] session key:
2af81ccbe231e2c1` -- but the emitted artefact carries a different value.
So the emitter renders `build_context['STR_SESSION_KEY']` from a binding
taken before the pin, exactly the ownership bug the C core had: the value
exists in one place, is read from another, and the re-draw is invisible.

The fix is the same shape as the core's: one owner, read after the pin.
That is a concrete, small change -- and it is the first located cause in
this residue rather than another elimination.

### Two more things it is not

Round 51 instrumented the pinned stream itself, logging every draw with its
caller, and diffed two builds:

- **the pinned draws are identical** -- 175 draws each, same callers, same
  sequence. The stream is not the residue;
- **the hash seed is not the cause** -- with `PYTHONHASHSEED=0` the residue
  is 100 lines against 102 without it. Not nothing, but not the answer.

(A third comparison was attempted and is **not** a result: the
pre-string-pass dump hook had been removed by an earlier revert, so the
diff compared two nonexistent files and printed 0. Recorded so it is not
mistaken for evidence.)

So: not the draws, not the ids, not the streams, not the hash seed. What
remains is the assembly between the format() call and the string pass --
and finding it needs the dump hook restored first, which is where the next
attempt should start.

### Content-derived string ids: no better

The last ordering theory: string ids were `len(STRING_ROUTER)`, i.e. pure
insertion order, so any change in the payload reshuffled every id. Made
them `sha256(s)[:8]` with deterministic collision probing. Residue:
**102 -> 106 lines**. No better, so it was reverted.

Four attempts have now been made on this residue (decoy streams,
per-site streams, content-derived ids, plus the two-class split earlier)
and none of them reduced it. The measurement says the remaining
difference is not in the values, not in the ids, and not in the streams;
it is somewhere in how the emitted text is assembled, and it needs a bisect
of the assembly itself -- dumping `raw_script` and comparing two builds
pass by pass -- rather than another targeted change.

That is the honest stopping point for this session: the item is 95% solved
in measurement terms (2,254 -> 102 lines, mechanism enumerated, six
falsified hypotheses recorded) and the last 4% needs a different kind of
work than rounds can provide.

### Per-site streams made it worse too

The obvious fix for the shared-stream coupling: give each draw site its
own seeded generator, so a variable call count at one site cannot shift
another. Implemented for the blob key, swizzle key, `s0_key` and `part_a`.
The residue went **102 -> 178 lines**, the same direction as round 44's
decoy change, and was reverted.

Two independent stream-surgery attempts have now increased the residue.
The likely reason is in the round-45 finding: the residue is table ORDER,
and order follows the source text the string pass walks, which follows the
payload parts -- so anything that changes a part's *length* reshuffles
every index downstream, even when the value is stable. Pinning values is
not the same as pinning ordering.

### The pinned stream advances by a variable amount

Round 46 dumped the pre-string-pass source and compared the two builds
line by line. The session key matches exactly; `SWIZZLE_KEY` differs by
**one byte of offset**:

    SWIZZLE_KEY = b'>JB\xcdT\xe4Y...'   |   b'JB\xcdT\xe4Y...r'

So the pinned stream is shared by calls that do not always happen the same
number of times -- `os.urandom` is called a variable number of times per
build, so everything drawn after it is shifted. Giving `os.urandom` its own
dedicated pinned stream did not change the residue (102 lines), so the
shift is not the whole story either, and that change was reverted.

What this rules out: the residue is not the swizzle key, and not the
session key. What it confirms: several independent draw sites share one
pinned stream, so any variability upstream shifts everything downstream.

### The residue is table ORDER, not table content

Round 45 dumped the plaintext string tables from two pinned builds and
compared them. The four tables hold **the same strings in a different
order**:

    table A: 'hw_fingerprint' ... | 'NO_TOKEN' ...
    table B: 'BAD' ...            | 'NET_FAIL' ...
    table C: 'net-fail' ...       | '4dbf90625fd436f4024aa61482967f37' ...

So the 102-line residue is not differing values at all -- it is the same
values indexed differently, because whatever builds the source text that
the string pass walks inserts them in an order that varies per process
(set iteration, i.e. `PYTHONHASHSEED`). Making that traversal order
deterministic is the remaining fix, and it is a smaller job than the
previous hypotheses implied.

### The decoy stream is not the residue

Round 44 gave the decoy names their own seeded RNG, on the theory that
their values depended on how many draws earlier passes made. The residue
between two pinned builds went **up** (102 -> 178 lines), so the theory was
wrong and the change was reverted. Whatever the remaining 102 lines are,
they are not the decoy stream position.

### The build timestamp is boundary-crossing after all

Round 39 tried pinning `BUILD_TIMESTAMP` (an obvious-looking label) and the
artefact failed its own magic check. Three facts, in order:

- the emitted template sets `BUILD_TIMESTAMP = {build_timestamp}` and the
  loader uses it in a rotation window:
  `w = (now - BUILD_TIMESTAMP) // (30 days)`;
- pinning it to a **future** value made that window negative and the
  payload did not run at all;
- pinning it to a **past** value ran but failed decryption
  ("Magic Mismatch"), so something derived from the window participates in
  the key path.

The pack-side `time_salt` is `sha256("0")` -- fixed, not time-dependent --
so the coupling is in the loader's window logic, not in that salt. Until
it is located, `BUILD_TIMESTAMP` belongs on the boundary-crossing list with
the keys, not on the list of labels that can be pinned.

### Which draws are safe to pin

Two classes, and round 3 failed because it treated them as one.

**Emitter-only draws** -- values that are decided at build time and
travelled *into* the artefact as literal data: the VM op-map shuffle, the
encoding-layer choices, names, slot picks, decoy placement. Both sides of
the artefact already carry the result, so pinning them changes nothing
about how it runs. Verified: `generate_polymorphic_map()` takes an
optional seed and is already seeded when `--watermark` is used; a
watermarked build runs its payload and still refuses a tracer, so the
seeded path is sound.

**Boundary-crossing draws** -- values the payload is encrypted *with* and
the loader re-derives at run time: the blob key, the nonce, the string
session key, the table keys. Pinning these is what made two builds differ
*and* what made the artefact fail its own magic check, because the emission
and the re-derivation stopped agreeing.

A reproducible build pins the first class and threads the second through
both sides at once. Round 3 pinned the second class alone, which is why it
produced artefacts that would not run.

- **The intermittent codegen failure is now named, and it is two bugs.**
  Catching one with the preserved artifacts showed `i32 ""` as a GEP index
  (guarded at both ends now). Catching another showed a *different*
  failure, caught by the existing "cannot express" guard:

      @_nixon_DŽЅۮՖ篐ᛆ: unlowered instruction: 'div i32 %14, 6856'

  a division of a register inside a **global initializer**, which is
  invalid IR (globals must be constant) and which the lowering therefore
  cannot express. It depends on whether constant-folding produced a
  register, which is why it comes and goes. The guard catches it loudly,
  so the build fails with the instruction in hand rather than in llc; the
  upstream fix is to keep a non-constant expression out of a global
  initializer at IR-generation time.

  **Resolved:** the `div` half was the project's IR spelling for signed
  division, which `BINARY_OPS` did not list (it had `udiv`/`sdiv` only), so
  every such instruction hit the guard. Added and mapped to `sdiv`.
  Evidence: the previously failing `build/program.ir` now lowers, and
  **16 consecutive full builds across two samples** exit 0, against a prior
  failure rate of roughly one in six.

- **An earlier sweep found no `llvmgen` failure in 12 builds.** Round 8 showed the failure needs the per-build IR rather than
  a seed, so the hunt was re-run on that axis: 12 full builds, each with
  its own IR, through `irgen` and `llvmg`. Zero failures. Either the rate
  is far below one in twelve, or the CI-only path (a different llvm
  build, `-O bcf fla sub` against the runner's `llc`) is what triggers it.
  The shadow job still pins `NIXON_LLVM_SEED`, which handles the seed axis
  but not this one, so the job remains capable of a rare red.
- **`scripts/build.py` occasionally exits non-zero while printing
  "Pipeline complete".** Seen twice in 12 sweep runs, then not at all in
  10 more. Nothing in the log distinguishes the failures from the
  successes, which means the exit code comes from a phase that reports
  success in its own output. Uncharacterised; a call that returns
  non-zero without a message is worth finding before it is trusted in CI.

## Known gaps

- **Hostile-host handling works now, without a flag.** Eight rounds tried
  to propagate a detection flag into a key poison and every attempt failed
  for a different surface reason -- `globals()` scope, module namespaces,
  renames, and an ordering bug where the core-digest mix re-derived the key
  after the poison position. None of those was the real problem: there was
  a flag at all.

  The working version has no flag. When the section-join helper is emitted
  the detection runs there -- at the point of use, in the module that owns
  the key -- and the helper is wrapped so the key it receives is poisoned.
  Verified three ways: a plain run prints its payload; a run under
  `strace` or with `LD_PRELOAD` set does not. Both hostile cases exit 0
  through the join's own failure path, not a `sys.exit` an analyst can
  patch.

  The single-blob path (`--no-section-split`) still uses the older
  `{FUNC_HARD}` call with its clean-refusal ladder; same fix, different
  call site, if it matters.

- The Rust runtime is not on the Python artefact's path at all.
- The loader template is ~66% identical between two builds; the shared
  part is the template itself, which any artefact exposes.
