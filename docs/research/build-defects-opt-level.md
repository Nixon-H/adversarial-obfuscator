# Two Build Defects Found While Producing a Maximum-Security Artefact

> **Status: both fixed** (commit `f835e21`). Four root causes, all one rule — a name must have
> one authority. `tests/test_opt_level_behaviour.py` holds a guard for each, and each guard was
> verified to fail when its defect is reinstated. The text below records the defects as they
> were found, which is why it reads in the present tense.

**Date:** 2026-11-02. Found by building a payload at every opt-level with the advanced
protection set, not by any existing test.

## Defect 14: `--opt-level 5` silently drops statements

A payload that prints eight lines prints **four** at `--opt-level 5`:

| opt-level | lines printed (expected 8) | output identical to source |
|---|---|---|
| 0 | 8 | yes |
| 1 | 0 | no |
| 2 | 1 | no |
| 3 | 7 | no |
| **4** | **8** | **yes** |
| 5 | 4 | no |

The dropped lines are exactly those following the recursive/iterative functions. No warning
is emitted; the artefact exits 0 and prints `OK`. **A silent wrong answer is worse than a
crash**, and the default is 4, which is why the default path is unaffected.

## Defect 15: any `import`, `class`, or `try/except` fails from opt-level 1 upward

```
NameError: name 'HAJJADEAFDCCGFBJDAAIFBBAECBADBCD' is not defined
```

Isolated by bisection:

| payload | opt-level 0 | opt-level 5 |
|---|---|---|
| function + comprehension | works | works |
| `import zlib` + function | **works** | **NameError** |
| `class` | **works** | **NameError** |
| `try/except` | — | **NameError** on an exception alias |

So the obfuscator can only harden modules that contain **no imports, no classes and no
exception handling** — which excludes most real code, including the project's own modules.

## What was exported

Because of both defects, the published artefact is a payload written to avoid those
constructs, built at **opt-level 4** with the full advanced-protection set. That combination
reproduces the source output **exactly** (verified by `diff`) and is 280x the source size.

## Why this matters for the paper

§6 claims thirteen defects, all found by gates and by external code. These two were found by
**using the tool as a user would** — building a realistic module at the highest settings —
and neither the artefact gate nor any test covers them, because the gate's 38 artefacts were
generated at the default level with payloads that avoid these constructs.
