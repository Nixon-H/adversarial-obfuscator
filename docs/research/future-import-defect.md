# `from __future__` Imports Are Moved Off the First Lines

**Date:** 2026-10-30
**Found by:** `requests/utils.py` (BSD), the fourth external module and the first
application-shaped code in the corpus.
**Fixture verified valid before the report** — `compile(source)` on the input
passes, per the lesson from round 102.

## Symptom

```
SyntaxError: from __future__ imports must occur at the beginning of the file
```

## Minimal reproduction

```python
from __future__ import annotations

def f(x: int) -> int:
    return x + 1
```

Build index 2 produces a file whose first sixty-five lines are obfuscation
scaffolding and whose line 66 is the `__future__` import:

```
   1| def _nixon_...(_s):
   2|     import hashlib as _nx_ha, hmac as _nx_hm
   ...
  66| from __future__ import annotations
```

## Cause

`from __future__` is a compiler directive, not an import: it must appear before
any other statement. A pass that inserts a prologue — the string decoder, the
hash/HMAC helpers — puts its code above the original first statement, and the
directive is no longer first.

## Why it had not been seen

None of the earlier sources uses `__future__`:

| source | uses `__future__` |
|---|---|
| internal fixtures | no |
| more_itertools.recipes | no |
| cpython statistics.py | no |
| boltons.strutils | no |
| **requests.utils** | **yes, `annotations`** |

`from __future__ import annotations` is common in modern application code and
rare in utility libraries written before 2017.

## Status

Open, with a minimal reproduction. The fix is to keep `__future__` imports at
the head of the emitted file — either by emitting the prologue after them, or by
hoisting the directive during assembly. Not attempted here: the assembly order
is in the loader construction path, and this programme has learned that an
unverified edit to a transform costs more than it saves.

## The count

Seven defects. This one is the third found purely because a new external source
used a construct the corpus lacked, and the first where the source is
application code rather than a utility library.

## Round 110: fixed, by hoisting after every transform

Two attempts:

1. **Splice the preamble after the directive block** in `sources.py`. Worked at
   build indices 2 and 4, failed at 0 — because `CallGraphObfuscator` inserts a
   function table at module index 0, which is *another* pass putting material
   above the original first line.
2. **Hoist `from __future__` to the top after all transforms**, in
   `_hoist_future_imports`. Works at every index.

The second is the right shape: reordering once, at the end, is more robust than
making each pass aware of a compiler rule.

```
artefacts checked: 69
invalid fixtures: 0
failures: 0
```

## The fixture that stays, and why it is not gated

`requests/utils.py` remains in the corpus as the regression fixture for this
defect — it is what found it — but it is **not** in the artefact gate. It uses
relative imports (`from .exceptions import ...`), so it cannot be imported
standalone by any tool, and the gate's import check would be measuring the
fixture's shape rather than the obfuscator's behaviour.

That distinction matters: a fixture that cannot be imported is not evidence of a
defect in the thing being tested. It is the same reasoning as round 102, applied
before the report rather than after.

## What would be needed to gate it

A package layout: copy the whole `requests` package, generate a shim that makes
it importable, and gate that. It is a real extension of the corpus and it is not
done here.
