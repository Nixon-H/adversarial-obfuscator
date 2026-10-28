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
