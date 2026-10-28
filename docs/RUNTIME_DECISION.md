# Should the Rust runtime be load-bearing?

Status: **open decision.** This records the evidence so the decision is a
judgement, not another investigation.

## What exists

- `runtime/` — a Rust crate with an integrity check (`runtime/src/integrity.rs`
  verifies the process's own text section against a CRC that
  `scripts/runtime_config.py` writes at build time from the binary itself).
- `relay/` — the transport binary; `make relay` builds it.
- `runtime_config.json` — produced by the Makefile for **native** binaries.

## What the artefact actually contains

A packed Python artefact references neither:

```
$ grep -c "nixon_runtime\|relay" dist/h_protected_dbg.py
0
```

Neither `obfuscator/core/sources.py` nor `obfuscator/core/pipeline.py`
mentions the relay. The Rust runtime is a **separate native-build
component**, not part of the Python artefact's critical path.

## The three options

**A. Leave it as it is (recommended).** Zero cost, no change to the
artefact's behaviour. The runtime remains available for native builds. The
"load-bearing" property is not met, and the changelog says so.

**B. Make it load-bearing for native builds only.** The native path already
builds the relay; requiring `runtime_config.json` and refusing to start
without a verified CRC is a small change to `runtime/src/main.rs` and the
Makefile. Cost: small. Benefit: the integrity check the crate already
implements stops being optional.

**C. Make it load-bearing for the Python artefact.** Package the relay
inside the bundle, spawn it on start, block the payload until it reports
healthy. Cost: a second binary to ship per platform, a process per run, a
new failure mode on hosts that block execution from a temp directory, and a
detection surface for anyone watching process trees. Benefit: a real
integrity signal for the Rust path — but the Python path already has the
core-digest key binding and the loader's self-check, so it buys defence in
depth rather than a missing control.

## The judgement

C is the expensive one and the least justified: it adds a runtime dependency
to the artefact that currently runs from an extracted temp directory, which
is the most fragile environment the artefact has. A is honest and free. B
is the cheap version of the same idea and is where I would spend an hour if
this mattered.

**Recommendation: A today, B if the native path is being shipped to anyone.**
Do not do C without a specific threat it addresses that the existing key
binding and self-check do not already cover.
