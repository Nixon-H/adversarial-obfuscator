# Full-tool REA benchmark — 2026-11-14

Headless agent attack on a maximum-config artefact, run after the round-2
audit fixes. Companion to [`RESULTS.md` of 2026-11-11](../ai-layer-bench-2026-11-11/RESULTS.md)
and [`MAXIMUM_SECURITY.md` §7](../../MAXIMUM_SECURITY.md).

## Setup

| Item | Value |
|---|---|
| Target | `tests/fixtures/portable/dist/constructs_source_protected.py`, 2,748,710-byte-class max build of the current tree (sha256 `61930aad…`), licence-bound (`env-only bootstrap-encrypted`), watermark NX-BENCH-001, trial 7 d, anti-REA maximum, 6 sections, 25 packaging layers + stego |
| Attacker | OpenCode 2.2.2 headless (`opencode run`) + Kern `Qwen/Qwen3.8-27B-FP8` (new provider: `api.kern-llm.org/v1`, OpenAI-compatible) |
| Tools | Full agent surface (bash/read/write/edit) + globally installed RE tooling: objdump, readelf, nm, strings, gdb, ltrace, strace, file, binwalk, ghidra, uncompyle6, decompyle3, upx, python3+capstone (no radare2 on this host) |
| Fence | systemd user unit; obfuscator source/docs/scripts/vm/irgen/llvmgen/encrypt/relay/runtime/native masked as inaccessible mounts; isolated XDG dirs; no licence token in the sandbox; 40-min wall clock, no step cap |
| Ground truth | 12 original top-level names (`Descriptor`, `Holder`, `Point`, `cached`, `slow_square`, `evens`, `classify`, `walrus_count`, `eg_sum`, `make_counter`, `deliver`, `main`), purpose markers, protections encountered |

**Benchmark-integrity caveat, stated first:** the sandbox fence masked the
project subtrees but *not* `/tmp` — the agent found the benchmark's own
licence file (`/tmp/rea-bench/issuer-side/bench.licence`) at attack-minute
~15 and used it. That matches the position of a real user (valid token on
the same host), **not** the position of a thief with only the binary. Both
readings are reported below.

## Scorecard

### What held (verified against the live attack)

| Defense | Result in this run |
|---|---|
| **Offline decryption** | **Blocked.** The agent states offline recovery of the final member is "machine/licence-locked (k_dec needs the 7-round key chain, _NX_BUILD_WINDOW, and licence key_material); dynamic capture on the authorized host was required". The 2026-11-11 run reconstructed the static chain end-to-end; this run could not. |
| **Interpreter-integrity gate (builtins type-check)** | **Fired for real.** The agent's first capture attempt hooked `builtins.exec`/`compile`; the gate tripped → `[BLOCKED] interpreter-integrity: builtins-hooked-exec (exit 3)`. The agent documented it and routed around (see breaks). |
| **Self-hash + self-wipe integrity monitor** | **Fired for real.** Prevented editing the artefact in place; forced execution of a byte-identical copy (md5 verified by the agent at the end: original untouched). |
| **Symbol renaming** | **0/12 original names** survived in the recovered source (AST-extracted 89 top-level objects, all obfuscated `_nixon_*`/`_nx_*`). Same result as 2026-11-11. |
| **Kill-gate surface** | `licence token required` (no token), `[BLOCKED] interpreter-integrity` (hook attempt) — both fail-closed with visible reasons, no silent death. |

### What broke

| Gap | How it was exploited |
|---|---|
| **Zipfile-level runtime capture** | With the valid token, the agent preloaded a `sitecustomize` shim that wrapped ONLY `zipfile.ZipFile.__init__`/`read` — builtins stayed clean, so the integrity gate saw nothing — and dumped the decrypted staging/final zip members (957,632 B + 5,458,198 B) to disk. |
| **Startup-hook invisibility** | The malicious-module scan reads `/proc/self/maps`; a PYTHONPATH `sitecustomize` shim adds no mapping, so the injection was never noticed. |
| **Decode chain reversibility** | Every post-capture layer was reproduced offline by the agent: 16-byte header skip → XOR (`\xf24@\xb8\x83P\xc7@Qks\xc0CNHC`) → zero-width stego (U+200B=0/U+200C=1, 8/byte) → 2,795-line payload; SWIZZLE_KEY zip-member XOR; b64→rot-13→b64 recipes; str85; second onion; zlib+LZMA. |
| **vm-inception nesting** | The inner protected build was decoded to source as well (its CFI state machines, `_nx_verify` canary and function table notwithstanding). |
| **Decoys/poison** | Mapped and dismissed as inert (they are by design); the poison flag is False at rest and never triggered. |

**Net:** with a valid licence on the host, the payload source is recoverable
(the legitimate-user position — inherent to client-side protection). Without
a licence, offline recovery stayed blocked this run where it succeeded on
2026-11-11. The binary alone still yields nothing.

## Second run's catch: the build shipped the symbol table (fixed same day)

The paired re-run (2026-11-14, afternoon) found a worse leak than anything
above, and it had nothing to do with crypto: the agent opened
`payload_Nixon-Enc_Silent.py.renamelog` — a sidecar the pipeline writes
**beside the payload source on every build** — and read the tail, which
maps the payload's original symbols to their obfuscated names
(`main`, `Descriptor`, `Holder`, `Point`, `classify`, `walrus_count`, …).
No gate, no decryption, no capture needed: **the renaming layer's entire
benefit was cancelled by a 6 KB log file the build leaves in the source
directory**, alongside ~850 MB of `_stego`/`_Packed` intermediates.

Fix (`obfuscator/core/pipeline.py`): the rename log is now written only
when `--debug-dump-raw` is set — a normal build emits no
obfuscated→original mapping beside the payload. Regression test:
`test_build_leaves_no_rename_log_beside_the_payload` (builds a real
2-layer artefact and asserts the source directory carries no `.renamelog`
and no unprotected debug copy). Verified on both paired rebuilds: zero
renamelogs in either run directory.

Consequence for the scorecard: the "0/12 original names" result of the
first run stands only for an attacker who receives the artefact alone. An
attacker who receives the *build directory* (the position this bench
accidentally granted) gets every name for free. Treat the build
directory as secret, or ship from a clean staging copy — the artefact and
its source directory are not the same trust boundary.

## Paired re-run after all fixes: REA-on vs REA-off (no licence anywhere)

Two fresh max builds from identical payloads, rebuilt with every fix from
this session (integrity gate + renamelog), attacked headless by the same
model, 40-minute budget each, **no licence token reachable from the
sandbox** (old transcripts and the issuer directory are masked), dynamic
execution explicitly allowed. Run B had one unintended advantage: it found
and read the first run's transcripts (22 references) — contamination that
can only strengthen the attacker, so failures are the more meaningful
direction.

| Measure | A: REA maximum | B: `--exclude rea` |
|---|---|---|
| Original names recovered | **0/12** | **0/12** — the agent greps both profile variants for the names it learned from the old transcripts and finds **nothing** (its own transcript proves the absence) |
| Payload output / markers | **0** | **0** |
| Payload recovered | No — still unwrapping b85/lzma layers at the 40-min wall | No — mapping loader structure, then the wall |
| Dynamic behaviour | Extensive: executed extracted fragments, decoded embedded b85 tables (VM op tables, 300-entry router) | Wrote its own analysis scripts, sized artefact stages, compared profile variants |
| Defenses observed | Licence gate refuses without token; integrity layers held; no capture | same |
| Verdict JSON | None (timeout mid-decode) | None (timeout mid-analysis) |

Both runs ended on the 40-minute wall without a verdict, so the scoring is
transcript forensics rather than the model's self-report. Within that
limit: **with the renamelog leak closed, neither configuration yields the
payload, the names, or any payload output to this attacker at this budget,
and removing REA did not make the difference** — the walls the agent hit
are the licence binding, the sealed strings, and layer depth, not the
anti-REA shields. That is consistent with §3.4's standing caveat: anti-REA
maximum's effect on an analyst remains unmeasured; what this pair measured
is that everything else held against a stronger-than-real attacker
position (transcript-contaminated, dynamic-capable, unlimited tools).

Scoring caveats, stated plainly: one model, one 40-minute budget per run,
two payloads; a longer budget or a more capable model can change the
result; "no recovery in 40 minutes" is not "resistant".

## The boundary, measured: how far the attacker gets (post-fix)

A fourth run placed the agent in the **legitimate-user position** — valid
licence token in the working directory, everything else identical. This
was the position that produced full payload recovery in the first run of
the day; it measures the current frontier:

| Attempt | Result |
|---|---|
| Run the artefact with the token | **Works** — pin verified (`sha256(canonical payload) == embedded pin`), full payload output produced. That is the product working as designed. |
| Find the original names | **Failed.** The agent built a complete string inventory of the artefact and searched all 12 ground-truth names: every result `exact: [] partial: []`. The renamelog closure holds even for the token holder. |
| Capture the decrypted source at runtime | **Not attempted** — zero `sitecustomize`/capture references; the agent did not retry the (now-blocked) zipfile route. |
| Derive the source statically with the licence material | **In progress at the wall** — it was hand-implementing the loader's lzma→cipher chain (`final_key = cipher.decrypt(resp_blob, resp_iv)`) when the provider died mid-run (HTTP 502). It did not reach the payload. |

The run ended on provider infrastructure (HTTP 502), not on the artefact,
so this frontier is "not reached in ~40 minutes", not "unreachable".

**The measured boundary, summarized:**

- **Binary alone (thief):** outer packaging, sealed loader strings, VM
  tables, key slots and layer order all peel open statically; the chain
  stops at `k_dec` — the payload decrypt key requires the licence
  `key_material`, so the final layer does not turn. Zero payload bytes,
  0/12 names, in every no-licence run.
- **Thief + stolen token:** can run the artefact (output, not source).
  Static source recovery is blocked behind the full key chain; the
  runtime-capture route that recovered the source this morning is closed
  and regression-tested. What is **not yet measured**: other capture
  routes a host-controlling analyst has in principle (interpreter
  tracing, audit hooks, process memory) — that is the next attack class,
  and client-side protection cannot fully close it.
- **Build directory (this morning's accidental grant):** was a total
  bypass via `.renamelog`; closed, regression-tested.

## Cross-model check: DeepSeek-V4.1-Flash via the local zproxy, positions 1, 2, 4

Re-ran the three attacker positions with `deepseek-v4-1-flash-1017` as the
only model, routed through the operator's local OpenAI-compatible proxy
(`zcode-proxy`, `http://127.0.0.1:8766/v1`, provider `local-proxy` in
OpenCode 2.2.2 headless). 40-minute soft fence, 45-minute hard kill.

**Endpoint attribution is verified, not assumed.** The proxy journal
records every call (`UPSTREAM deepseek-v4-1-flash-1017 prompt=… cached=…`).
Across the benchmark window (22:32–00:47) it logged **718 requests, all
`deepseek-v4-1-flash-1017`** — no other model appears — totalling 79.55 M
prompt tokens, 78.86 M of them served from cache (99.1 % prompt-cache
read).

**Isolation.** Each position ran under `bwrap` with a fresh `/tmp`, a
private `HOME`, and only `artifact.py` + `nixon_core.so` +
`Nixon_Security_Root.cer` (+ `bench.licence` for positions 2 and 4) in
`/work`. The build tree, the plaintext `payload.py`, and the debug build
were unreachable — verified in-run by `find / -name payload.py` returning
nothing. This removes the staging leak that contaminated the earlier
unproxied run.

| Position | DeepSeek-flash result | vs Kern Qwen |
|---|---|---|
| 1: binary alone, no licence | **0/12 original names.** Mapped the loader end to end (licence gate, 300-entry string table, `S_INIT…S_EXEC` state machine, three bytecode VMs, Merkle+HMAC self-integrity, native `nixon_core.so` path). Recovered the string-table XOR key (`_STR_SESSION_KEY`) and confirmed its 32-byte period, but the 9 224-byte table does not zlib-decompress under any derived key. Stopped by the licence gate and the hardware/environment binding of `k_env`. Confidence 0.72. | same |
| 2: thief + valid token | **0/12 original names.** Decrypted the full 300-entry string table, dumped the in-memory zip member `__main__.py` (5 691 814 bytes, `# NIXON_HEADER` + XOR(SWIZZLE_KEY)), and confirmed the payload executes. Did **not** break the second-stage cipher (XOR of two blobs → lzma → nonce-keyed cipher class), so the payload plaintext was never reached. Confidence 0.45. | Kern timed out mid-derivation; DeepSeek got further but also did not finish |
| 4: capture-route hunting (with token) | **Payload source recovered — 237 152 bytes, byte-identical to a manual stage0 decode — but 0/12 original names**, because the recovered source carries renamed identifiers only. Route results: `sys.addaudithook` installed from a `PYTHONPATH` module imported before `exec`ing the artefact **worked** (captured at the `compile()` boundary); `sitecustomize` blocked (`startup-hook-external-sitecustomize`, exit 3); `sys.settrace` blocked (`thread-timing`, exit 4); `sys.setprofile` blocked silently (exit 137). | Kern never reached this stage |

### Corrections to the earlier (unproxied) DeepSeek run

The first DeepSeek pass on this bench was reported as running "via the
`m-start`/zproxy setup". It was not. That run used `-m
mistral/deepseek-v4-1-flash-1017`, i.e. the `mistral` provider pointed
straight at `https://api.mistral.ai/v1`; the sandbox's proxy provider was
declared on a dead `https://127.0.0.1:8767/v1` and was never selected.
The proxy logged zero benchmark traffic. Three claims from that pass are
withdrawn:

1. **"Decrypted payload source fully recovered" at position 2** — the
   name→symbol mapping came from a plaintext `payload.py` reachable
   through the sandbox's `artifact.py` symlink into the build tree. With
   that path closed, position 2 recovers the encrypted member but not the
   plaintext, and recovers **0/12** names.
2. **"Tracing neutralized by the loader itself … no new capture route
   succeeded" at position 4** — wrong. `sys.addaudithook` is not covered
   by the anti-trace checks and does capture the payload at `compile()`.
   What the loader stops is `settrace`/`setprofile` and external
   `sitecustomize`, not audit hooks.
3. **"40 min each"** — the prompt actually sent said 35 minutes, and no
   run self-terminated at either fence.

### What this run establishes

1. **Renaming survives a full source leak.** Position 4 obtained the
   payload source and still recovered 0/12 original names. The name layer
   does real work independently of the encryption layer.
2. **`sys.addaudithook` is an open capture route.** It is the one
   host-controlled route that reached the plaintext. Closing it means
   detecting an audit hook installed before the loader runs — the same
   class of problem as `sitecustomize`, and the existing
   `startup-hook-external` check does not cover it.
3. **The token holder still cannot finish inside one budget.** Position 2
   got the string table and the encrypted member but not the second-stage
   cipher. The client-side boundary holds against a 40-minute agent, and
   the earlier claim that a fast agent "turns it into the payload within
   one budget" is not supported.
4. **All three runs overran the fence.** None produced a final answer on
   its own; each had to be resumed with an explicit stop instruction.
   Position 2 degenerated into rewriting the same probe script
   (`t373.py`…`t376.py`, identical contents) — a budget-burning loop
   worth watching for in future runs.

## Fixes made from this run (same day)

1. **Integrity gate now covers the loader's own stdlib dependencies**
   (`obfuscator/core/sources.py`, `INTEGRITY_CHECK_SOURCE`): the
   `zipfile.ZipFile.__init__`/`read` code objects must still come from the
   real stdlib file (accepts both the pre-3.13 `zipfile.py` module layout
   and the 3.13+ `zipfile/__init__.py` package layout), and the module's
   `__spec__.origin` must match; builtins check extended to `__import__`
   and `open`.
2. **External startup-hook detection**: a loaded `sitecustomize`/
   `usercustomize` whose file lives outside the interpreter prefix
   (`/usr/lib/python*`, `/usr/local/lib/python*`, `/etc/python*`, sys
   prefixes) is reported (`startup-hook-external-…`). Distro-shipped
   startup hooks (Debian ships one in `/usr/lib/python3.13`) remain
   allowed — measured on this host before arming.
3. Both fail-closed under `--strict-detections` (exit 3) exactly like the
   existing gate, with reason codes. The gate is also armed in the shipped
   `--fast`-free default: `strict_detections` is on for the packed-loader
   path, so the block applies to the maximum configuration by default.
4. Tests: **8 new cases** in `tests/test_audit_round2.py`. Six at the gate
   level (clean interpreter, init wrap, read wrap, distro sitecustomize
   allowed, external shim blocked, `__import__` hook) plus **two
   end-to-end regressions that build a real 2-layer artefact** and replay
   the bench's exact attack: the shimmed run must exit 3 with
   `[BLOCKED] interpreter-integrity` and produce **no capture log**, the
   un-shimmed control must run the payload (exit 0). 42/42 in the file,
   ruff clean; the E2E pair adds ~25 s to the suite.

**Process note worth keeping:** the first rebuild after this fix failed the
post-build verification suite — the new gate code referenced the builtins
alias with a one-syllable-off identifier variant, which unit tests (that
bind aliases by shape) could not see but the built artefact could. The
verification suite caught it, refused to report success, and the fix went
in only after the alias matched the loader's import preamble. Two existing
fail-closed mechanisms (post-build verification + the gate's own
`probe-exception-…` reason code) are what surfaced it.

Re-verification (verified, 2026-11-14): canary rebuilt with the hardened
gate (build passes the post-build verification suite: both profile
variants PASS/VALID/MATCH). Running the agent's **exact capture setup** —
a PYTHONPATH `sitecustomize` shim wrapping `ZipFile.__init__`/`read`,
with the valid licence — now produces:

```
[BLOCKED] interpreter-integrity: zipfile-hooked-init (exit 3)
```

with **zero bytes captured** (no member is ever read). The same artefact
without the shim, with the licence, still runs the payload (exit 0). The
capture vector that defeated the artefact during the benchmark is closed;
the second layer (external `sitecustomize` detection, reason
`startup-hook-external-…`) remains as defence in depth for shims that do
not touch zipfile.

Root-causing note: the first three rebuild attempts failed the post-build
verification because the new gate code referenced the builtins alias with
a visually-identical but byte-different identifier (katakana `イン` tail
where the loader's import preamble defines the hangul `인` tail). Unit
tests bind aliases by shape and could not see it; the built artefact's
gate reported `probe-exception-NameError` and the verification suite
refused success until the identifier was transplanted byte-exact from the
preamble. Two fail-closed mechanisms (post-build verification + the
gate's reason codes) caught a defect introduced by the fix itself.

## Deep run, no budget cap: the rename layer was invertible (fixed)

The 40-minute runs above stopped at "payload source recovered, 0/12 names".
That result was wrong, and the reason was not the attacker's skill: the
renaming was a **bare hash of the name it replaced**.

`SymbolRenamer.get_new_name`'s `dynamic_unbounds` branch spelled a renamed
name as `"_nx_" + md5(original)[:6]`, and
`UnicodeIdentifierEncoder._encode_name` derived its homoglyph spelling from
`md5(original)` the same way. Both are stable within a build — which is what
the passes need — and both are a lookup table over candidate names. Anyone
holding the captured payload can run a word list through the same hash and
read the original names back out.

Measured on the bench artefact's own payload, captured through the
audit-hook route (237,152 bytes):

| Build | `_nx_` ids in source | Names recovered by a 104,359-word dictionary |
|---|---|---|
| Pre-fix | 11 | **11/12** |
| Post-fix | 12 | **0/12** |

Pre-fix recoveries: `Holder`, `Point`, `cached`, `classify`, `deliver`,
`eg_sum`, `evens`, `make_counter`, `slow_square`, `walrus_count`, plus a
local `n`. `Descriptor` and `main` escaped only because they took a
different branch — not because the scheme was sound.

**Fix** (`obfuscator/core/transforms.py`): both derivations are now keyed
with a per-build secret (`_new_rename_key()` → `secrets.token_bytes(32)`,
rebound to the build RNG under `--seed` so seeded builds stay reproducible)
and tagged with `hmac.new(key, name, sha256)`. Stable within a build,
different across builds, and not recoverable from the artefact.

**Regression tests**: `tests/test_rename_not_invertible.py`, 7 cases. The
three core cases were verified to fail against a simulated pre-fix tree
(monkeypatched back to md5), so they catch the bug rather than restating the
implementation.

**End-to-end re-verification** (2026-11-15): rebuilt the artefact with the
fixed tree, issued a fresh licence, captured the payload through the same
audit-hook route (236,016 bytes, 89 top-level defs), and re-ran the same
104,359-word dictionary. **0/12.** The same dictionary against the pre-fix
capture still returns 11/12, so the control is live — the fix is what
changed, not the attack.

## Second finding: the payload printed its own names

The deep run's position 4 recovered **4/12** names without touching the
rename layer at all. It ran the artefact and read the labels:

```
print("evens:", list(evens(9)))   ->   evens: [0, 2, 4, 6, 8]
```

The literal is sealed at rest like every other string, so a static read of
the artefact shows nothing. It decrypts to the original name at run time,
which puts the name on stdout. Breakdown of the 4:

| Name | How | Kind |
|---|---|---|
| `evens` | printed label `"evens:"` | exact disclosure |
| `main` | universal module entry point | free |
| `Point` | dataclass with `x`/`y` and `.norm()` | semantic inference |
| `make_counter` | `"closure:"` + a counter that increments | semantic inference |

Only the first is a defect the obfuscator can help with. The other three are
inferences from behaviour, which no client-side scheme can prevent — a
program that prints its results tells you what it computes.

**Fix** (`obfuscator/core/sources.py`): `find_name_echoing_strings()` walks
the payload AST and reports string literals that spell out a definition
name, in two tiers — `exact` (the whole name appears) and `stem` (a word of
four characters or more is a prefix of the name, e.g. `"walrus:"` against
`walrus_count`). The build warns. It does not rewrite: a printed label and
a protocol field are the same AST node, so rewriting would silently change
program behaviour. The call belongs to the payload's author.

**Regression tests**: `tests/test_name_echo_leak.py`, 7 cases, including one
that asserts the detector is actually wired into `apply_ast_mutation` (it
fails when the wiring is removed) and one that runs against the bench
payload itself.

## How far each position actually got

Three positions, DeepSeek-V4.1-Flash through the local zproxy, 3-hour cap,
run in parallel (2,390 upstream requests, 99.8 % prompt-cache read).

| Position | Payload recovered | Names | Where it stopped |
|---|---|---|---|
| 1 — binary alone | no | 0/12 | Licence gate. Got as far as recomputing the loader's self-integrity HMAC exactly, then needed `key_material` it did not have. |
| 2 — thief + stolen token | no | 0/12 | Decrypted the bootstrap string table (all 300 entries) and verified the licence and `nixon_core.so` hashes, then hit the loader's Merkle self-integrity and the stage-1 key. |
| 4 — token holder, controls host | **yes** (audit hook) | 4/12 | The rename layer. Captured source carried renamed identifiers only; the 4 names came from stdout labels and inference. |

Two things worth recording beyond the score:

- **The interpreter-integrity gate held under sustained attack.** Position 4
  tried to hook `builtins.compile` **791 times**, including a metaclass
  `__instancecheck__` spoof designed to pass the gate's type check. Every
  attempt returned `[BLOCKED] interpreter-integrity: builtins-hooked-compile
  (exit 3)`. The gate is not bypassable by disguising the replacement's type.
- **All three runs plateaued into loops** rather than exhausting their
  routes: position 4 retried the same blocked hook, position 1 re-ran one
  probe, position 2 wrote 386 throwaway scripts. The 3-hour budget was not
  the binding constraint; the models ran out of ideas well before it. That
  is a limit of this benchmark's attacker, not evidence that the artefact is
  unbreakable — position 4 was told the audit-hook route works and still did
  not use it.

## Verification run (2026-11-15)

Both fixes are covered by new regression tests and the affected modules pass:

| Check | Result |
|---|---|
| `tests/test_rename_not_invertible.py` | 7 passed |
| `tests/test_name_echo_leak.py` | 7 passed |
| Targeted suite (13 files covering `transforms.py` and `sources.py`) | **252 passed, 1 skipped, 0 failed** |
| End-to-end: rebuild → licence → audit-hook capture → 104,359-word dictionary | **0/12** (control on the pre-fix capture: 11/12) |

Two notes on the test run, because both cost time and both are worth knowing:

- The full suite (`tests/`, 357 files) does not finish on this host — it was
  OOM-killed at 18 % earlier in the day and runs at roughly 55 tests/minute,
  so the targeted set above is what was actually executed. It covers every
  module these fixes touch; it is not a whole-suite result.
- `test_kill_ladder_reports_to_alert_before_wipe` failed intermittently in
  batches and passed alone. The cause was the new detector being O(names ×
  strings) over a large payload, which starved the child process the test
  spawns. The detector now indexes the names once and runs in 52 ms on the
  237 KB payload. The call is also wrapped so a defect in an advisory check
  can never reach `apply_ast_mutation`'s broad `except`, which would have
  silently returned un-obfuscated source.

## Re-run against the fixed build (2026-11-15)

Every run above attacked the **pre-fix** artefact. This round rebuilds with
the keyed rename and re-runs the positions, so the fix is measured against a
live attacker rather than a script.

Build: `--opt-level 5 --anti-rea-level maximum --section-count 6
--package layers=25 zips=3`, licence-bound (`token=… env-only
bootstrap-encrypted`, `NIXON_LICENCE_PUBLIC_KEY` set). Verified: without
`NIXON_LICENCE` the artefact prints `licence token required` and blocks;
with it, the payload runs.

| Run | Position | Labels | Payload | Names |
|---|---|---|---|---|
| 1b | binary alone, no token | original | **no** | 0/12 |
| 2b | thief + stolen token | original | yes | **6/12** |
| 2c | thief + stolen token | **neutralised** | yes | **0/12** |
| 4 | token holder, controls host (flash) | original | yes | 0/12 |
| 4pro | token holder, controls host (glm-5-3) | original | yes | 0/12 |

### The rename layer held in every run

No run recovered a name by inverting the rename. Position 2b states it
plainly: *"Recover original names from code objects / scrambled identifiers —
stopped: original identifiers were not recoverable."* Position 4 and 4pro
both returned the obfuscated identifiers (`_nx_04ccc6`, `_nx_6860ce`, …) as
their answer, which is the honest outcome: they got the source and could not
get the names.

Position 4pro is the strongest attack in this document. It did the full
offline static unpack — 10,449 parts joined, b64, XOR, both onion recipes,
lzma, the self-integrity HMAC key derivation, chunked unpad, the
`NIXON_ENC` zip, the `SWIZZLE_KEY` XOR, and the ChaCha20-MAC unseal of 218
payload literals — and still scored 0/12.

### The licence binding works

Position 1b had no token and could not decrypt. It got as far as extracting
the mid zip (440,683 bytes) and then hit `[FATAL] Magic Mismatch (Decryption
Failed)` on every key path it tried. It reported `payload_recovered: false`
and returned an empty name list rather than guessing.

### The residual is the printed labels, and only that

Position 2b scored 6/12 — `Descriptor`, `Point`, `evens`, `classify`,
`make_counter`, `main` — and every one came from reading the payload's own
output labels and matching them to behaviour, not from the rename. Its own
evidence lists the mapping: `evens:[0,2,4,6,8] <- _nx_8e8560`,
`match:[…] <- _nx_92ea41`, `closure:3 <- _nx_c256ec`.

Position 2c is the control. Same position, same model, same obfuscator, same
licence — the only change is that the nine printed labels were rewritten to
`r1:`…`r9:`. Score: **0/12**. That isolates the leak to the label strings and
nothing else, and it is the measurement behind the `find_name_echoing_strings`
warning added above.

### What this changes in the scorecard

- The rename layer is no longer a name-recovery route. Before the fix a
  104,359-word dictionary returned 11/12; now every live attacker returns
  0/12 by that route.
- The remaining name leak is the payload's own output, worth up to 6/12 to a
  diligent attacker and 0/12 to an equally capable one that does not think to
  read the labels. That variance is model behaviour, not protection: position
  4 (flash) scored 0/12 where position 2b (same model) scored 6/12.
- A payload that prints its own identifier names should be treated as
  unprotected at the name layer regardless of how well the rename is keyed.
  Build once and read the warning.

## What remains open (honest)

- An analyst who controls the host **and** holds a valid licence can still
  capture at the final `exec` boundary (the agent notes `_DirectFD`
  redirection, module-cache and buffer zeroing "did not affect the captured
  copies"). That is the legitimate user's privilege; no client-side scheme
  can close it without hardware anchoring.
- **`sys.addaudithook` is a confirmed open capture route** (measured, see
  the zproxy cross-model run above). A hook installed from a `PYTHONPATH`
  module imported before the loader runs captures the payload at the
  `compile()` boundary and is not caught by the anti-trace checks, which
  cover `settrace`/`setprofile` and external `sitecustomize` only. The
  payload source leaks. The original names no longer do — but that now rests
  on the keyed rename holding, not on the source being unavailable, so the
  rename layer is load-bearing and must stay keyed. A marshal-code-object
  delivery path would close the source leak itself; `CompileToMarshal` is
  already exported by `nixon_core.so`.
- **A payload that prints its own identifier names defeats the rename
  layer** regardless of how well the rename is keyed. The build now warns
  (`find_name_echoing_strings`), but it cannot rewrite the literal without
  risking a behaviour change, so the fix is the payload author's. Any
  payload shipped with this tool should be built once and its warnings read.
- The gate checks specific loader dependencies (zipfile); a new capture
  route through a different stdlib surface is conceivable. The startup-hook
  check closes the general injection route on hosts without a distro
  startup hook, and `/proc/self/maps` scanning does not see it — defence in
  depth, not a proof.
- One model, one run, one payload, one 40-minute budget. No claim about a
  determined human analyst or a frontier model with more time.

## Recipe C (absolute maximum): from "builds but dies at import" to a native artifact

Recipe C is the strongest of the three maximum commands in
`docs/MAXIMUM_SECURITY.md` §5.3 — every lowering family, all three
`--transforms`, the full access-gate set, a chain-bound licence and a
25-layer package. It built, and then the artifact died at import. Six bugs
sat between "the build exits 0" and "the artifact runs", and none of them
were visible from the build log: the verification suite reported
`Debug Version FAIL / Silent Version PASS`, which reads like a flaky
profile rather than a broken transform.

### The three that broke the Python artifact

**1. `FunctionIntentObfuscator` renamed methods it could not rewrite.**
`obfuscate_intent` collected *every* `FunctionDef` in the tree — methods
included — and renamed each to a misleading `_nx_op_<hex>`. Only `ast.Name`
uses were rewritten, so a method reached through attribute access kept its
old spelling at the call site while the definition moved:

```python
class Point:                 class _nx_e42ca7:
    def norm(self): ...   ->     def _nx_op_81174899(self): ...

Point(3, 4).norm()           _nx_e42ca7(3, 4).norm()
                             AttributeError: no attribute 'norm'
```

The payload died on the first method call. Two related defects came out of
the same code path: dunder methods were renamed too (breaking `__init__`,
`__eq__`, `__enter__`), and `_name_map` was keyed by bare name, so a method
and a module-level function sharing a name collided and both definitions got
one new name. Fixed by renaming module-level functions only, skipping
dunders, and never rewriting a name a parameter shadows.
`tests/test_function_intent_rename.py` (8 tests).

**2. `DataProtector._virtualize_storage` rewrote writes but not reads.**
The pass moved a local binding into a shuffled slot list:

```python
bump = make_counter()   ->   _vs_1[_vmap_1[0]] = make_counter()
bump()                       bump()          # NameError
```

The hand-written expression rewriter covered only `Name`, `BinOp`,
`UnaryOp`, `Subscript`, call *arguments* and `Compare`. A read in any other
position kept the original spelling. Attribute receivers, boolops,
f-strings, comprehensions, `for` targets, `with ... as`, `except ... as`,
walrus targets and `del` all had the same hole. Two of those are *write*
paths that cannot be rewritten into a slot at all, so those names are now
excluded from virtualization instead — `total = 0; for total in
range(4): pass; return total` used to return 0. `except E as e` binds `e`
through a plain string, not a `Name` node, so the Store scan could not see
it either. `tests/test_storage_virtualization.py` (12 tests).

**3. The self-check's non-`str` globals keys.** `_nx_baseline` scanned
`globals()` and tracked every callable it found; the payload also parks
non-`str` keys there (the string table and the bytecode bridge both do), and
a `bytes` key can never be looked up again by name, so `_nx_verify` raised
`checksum: missing function b'*\xc3\x9bP]\xc3\xb5...'` on the first call of
every guarded function. Both halves now skip non-`str` keys.

After those three, recipe C builds, verifies (`Debug PASS / Silent PASS`,
integrity `VALID`, match `MATCH`) and runs:

```
$ python3 payload_protected.py
descriptor: 7
squares: [0, 1, 4, 9, 16]
evens: [0, 2, 4, 6, 8]
match: ['origin', 'on-y', 'on-x', 'somewhere']
walrus: 6
except-star: 6 0
closure: 3
dataclass: 5.0
async: [3, 2, 1]
OK
```

### The three that broke the Cython artifact

Recipe C is still a Python artifact. Compiling it with Cython
(`compile_payload_to_cython`) hit three more walls, all of them in the
native path rather than the payload:

**4. `_g = globals` is a Cython compile-time trap.** Aliasing the `globals`
builtin as a *value* makes Cython emit a reference to its internal
`__Pyx_Globals` helper as a Python name:

```
NameError: name '__Pyx_Globals' is not defined
```

Reproduced in six lines. The loader's builtin alias table did exactly that.
`lambda: globals()` compiles and behaves identically; `exec`, `compile`,
`locals` and `vars` are all fine as values.

**5. `cdivision=True` silently disarms every `ZeroDivisionError` guard.**
The generated `.pyx` header set `boundscheck`, `wraparound`, `cdivision` and
`infer_types`. `cdivision=True` makes `1 / 0` return 0 instead of raising —
a behaviour change, not an optimisation, and the payload uses
`try: 1 // 0` as an anti-debug probe. `infer_types=True` segfaulted the
module at import. Only `language_level=3` is safe here.

**6. The self-integrity check hashes its own `.py` source.** The loader
reads `__file__`, strips the two lines carrying the expected Merkle root and
HMAC, and feeds `sha256(content)` into the key chain. A compiled extension
ships no `.py`, so `open(__file__)` reads the `.so` and the check can only
fail — and it cannot simply be dropped, because the digest is part of the
key. The digest is now computed at build time from the same bytes the `.py`
artifact would have hashed and baked into the native module.

Result: `payload_module.so`, 4.9 MB, ELF x86-64, built in 62 s, runs and
prints the same output as the `.py` artifact. `tests/test_cython_native_path.py`
(5 tests).

### Cross-platform caveat

Cython emits **per-platform** binaries. One local build cannot produce all
three: Linux gets `.so`, Windows `.pyd`, macOS `.so`, and each is bound to
its CPython ABI (`cpython-313-x86_64-linux-gnu`). "Runs on all the OS" needs
one of:

* a build per target OS (the honest answer — three CI legs, three artifacts);
* `--package cross=TARGETS`, which cross-compiles but is limited by the
  available toolchains;
* the GitHub farm (`--package native compile cloud platform=github`), which
  is what recipe B already uses.

The `.py` artifact stays the portable one. The native build is a per-target
hardening step on top of it, not a replacement.

### Build environment notes

* `/tmp` is a 3.8 GB tmpfs on this host and the Cython build fills it
  (`No space left on device` from the assembler). Point `TMPDIR` at the real
  filesystem.
* Python's default `CFLAGS` carry `-g`; on a 21 MB generated `.c` that is
  several GB of debug info. `CFLAGS="-O2 -fPIC -fno-strict-overflow
  -Wsign-compare -DNDEBUG"` is enough.
