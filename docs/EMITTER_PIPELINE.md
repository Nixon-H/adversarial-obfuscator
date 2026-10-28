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

## Known gaps

- Only the ptrace detection feeds the key poison; the other five still
  `sys.exit(N)`. Extending it is **blocked on debugging the detection
  path**, not on editing it.

  **Correction (round 14): the poison has never been demonstrated to
  work.** The emitted `{FUNC_HARD}` body is still the original
  `sys.exit(N)` ladder, so a traced run exits **0** -- a clean refusal,
  not a poisoned key. What round 8 measured was that exit, not the poison.
  The flag-setting code was in fact wiped by a later
  `git checkout -- obfuscator/core/sources.py`, leaving only the reader in
  `pipeline.py`.

  Re-applying it (all six detections set one flag, no exits) put the new
  body in the artefact and the poison in the right place -- `BLOB_KEY`,
  then the detection call, then the xor -- and the payload still ran, so
  the flag is set but not observed.

  Round 15 ruled out the obvious cause: the artefact does **not** re-exec
  (`strace -f -e trace=execve` shows exactly one `execve`), and
  `/proc/self/status` reports a non-zero `TracerPid` inside a traced
  process, so the check runs in the same process that decrypts and the
  detection itself fires. The flag therefore reaches neither the poison
  nor the other process through any path established so far; the emitted
  setter and reader both exist, and comparing table indices across the two
  sites was inconclusive because the ones inspected belonged to a different
  guard.

  **Root cause (round 16): the loader and the payload do not share
  globals.** The loader executes the payload with
  `exec(code, module.__dict__)` into a fresh namespace, so a flag written
  to the loader's `globals()` is invisible to the code that decrypts and
  runs the payload. The detection call and the poison are both emitted in
  the loader's module -- the right order, the wrong namespace. That also
  explains why `LD_PRELOAD` never appeared to fire: the check runs, sets
  its flag, and nothing downstream can see it.

  Round 17 tested the namespace fix directly: `{FUNC_HARD}` now *returns*
  its verdict instead of writing a `globals()` entry (a `globals()` write
  inside a function lands in the function's own module), and the caller
  applies the poison in the same statement block. The payload still ran
  under `strace` and under `LD_PRELOAD`. So the block that applies the
  poison is itself in a namespace the decryption does not read -- the
  decrypt happens on the far side of the `exec`, not next to `BLOB_KEY`.

  That is where this item stops until someone traces the actual decrypt
  call: which module performs it, and which namespace holds the key it
  uses. Six attempts have now been made on the assumption that the emitted
  `BLOB_KEY` is that key, and the last one falsified it. Shipping state is
  the clean exit on detection, which is verified.
- The Rust runtime is not on the Python artefact's path at all.
- The loader template is ~66% identical between two builds; the shared
  part is the template itself, which any artefact exposes.
