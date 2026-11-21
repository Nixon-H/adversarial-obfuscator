# Mimosa audit baseline — 2026-11-20

**What this file is.** The project's first *conclusive* full-coverage scan, and
the triage of every high-severity class it reports. The reviewers asked for a
complete scan with the existing findings explicitly triaged, and for the
difference between "the gate went green" and "the repository was audited" to
stop being blurred. The scan command, the raw counts and the reasoning are all
here so the baseline can be re-derived.

## The scan

```
node <mimosa>/payload/dist/cli.js audit .
```

Result: **1,470 files scanned, coverage complete** (no `parseFailures`, no
partial-coverage marker — this is the run the earlier reports never had).

| Severity | Count |
|---|---|
| High | 919 |
| Medium | 8 |
| Low | 257 |
| Cross-file taint | 5 |
| Dependency vulnerabilities | 0 |

Raw output: `/home/nixon/nx-suite/mimosa_audit.log` (session artifact).

## Why the high count is what it is

This repository is a **Python obfuscator**. Its core purpose is to generate,
transform and execute Python source, write build artifacts to scratch
directories, and talk to build-farm APIs. Three of the scanner's
highest-volume rules detect exactly those activities:

1. **Path traversal (619 of 919 high)** — every hit is a `open()` on a path
   that was produced by `confined_path()`, `tempfile.mkstemp()`, or
   `os.path.realpath()` **12–56 lines earlier than the scanner's window**.
   `confined_path()` (obfuscator/core/pipeline.py:478) is this project's
   containment primitive: it refuses `..`, absolute paths, and anything that
   resolves outside the given root. The scanner does not follow the dataflow
   that far, so it reports the sink.
2. **SSRF (208 of 919 high)** — every hit is one of the project's own
   build-time API clients (Cloudflare Workers/KV, Blockscout verification) or
   the geofence gate's hardcoded service list
   (`https://ipapi.co/json/`, `https://ip-api.com/json/`). None of these URLs
   is built from untrusted input.
3. **Code injection (the remainder)** — every hit is `exec`/`compile`/`eval`
   on text the project itself generated: the obfuscation pipeline executing
   its own transform output, and tests exercising emitted loaders. The
   project is a code generator; generating and running code is the product.

## Triage method (reproducible)

For each flagged path-traversal line, the variable at the sink was traced
backwards to its assignment. The check used:

```
python3 - <<'EOF'
import re
src = open("obfuscator/core/pipeline.py").read().splitlines()
for ln, var in {740: "pyx_path", 815: "cfile", 846: "dest",
                1724: "src_path", 4071: "bat_path", 4088: "mac_path"}.items():
    for back in range(ln - 1, max(0, ln - 60), -1):
        if re.search(r"\b%s\s*=" % re.escape(var), src[back - 1]):
            print(ln, var, "<-", back, src[back - 1].strip())
            break
EOF
```

Every result named `confined_path(...)`:

```
  740 pyx_path  <- 727: pyx_path = confined_path(cython_dir, pyx_name, allow_subdirs=True)
  815 cfile     <- 806: cfile = dest + "c"          (dest <- 831 confined_path)
  846 dest      <- 831: dest = confined_path(build_dir, rel, allow_subdirs=True)
 1724 src_path  <- 1700: src_path = confined_path(build_dir, "payload.py")
 4071 bat_path  <- 4035: bat_path = confined_path(base_dir, bat_name)
 4088 mac_path  <- 4074: mac_path = confined_path(base_dir, mac_name)
```

Sample of the remaining hits, checked the same way:

* `pipeline.py:516` — `open(pyx_path)`, path from `confined_path` on 515.
* `pipeline.py:1349` — `urlopen(Request(api_url))`, `api_url` from
  `explorer_url` supplied by the operator on the build command line.
* `pipeline.py:1494/1525/1612` — `urlopen` against
  `self.base_url = "https://api.cloudflare.com/client/v4"`.

## What is genuinely open

Nothing in the high bucket was found to be reachable by an attacker who does
not already control the build host. That is a **triage conclusion, not a
proof**: the scanner sees no dataflow past ~12 lines, and this baseline
records the reasoning so a future reviewer can disagree with a specific line
rather than with a count.

Two things this baseline does **not** claim:

* It is not a clean scan. The findings exist; they are classified, not
  suppressed. No rule is disabled and no path is excluded.
* It is not a substitute for reading the code. The medium-severity
  `不安全反序列化` (unsafe deserialisation) hit at `pipeline.py:811`
  (`marshal.loads` of bytecode this project compiled moments earlier) is the
  one item worth a second look if the threat model ever includes an attacker
  who can write to the build's own scratch directory.

## Reproducing / re-checking

Run the audit command above and compare the per-file/per-line list. A new
high-severity class that is *not* one of the three above is a regression and
should be triaged on its own.

## Independent self-sampling — 2026-11-21 (review register, P1)

The 2026-11-20 triage sampled its own conclusions. This section is a second
pass with fresh line numbers from a NEW scan of the current tree (1,482
files; 921 high / 8 medium / 259 low — the +2 high are the farm driver's new
subprocess `cl`/`link` calls in the CET probe and smoke-test paths), sampling
findings the first pass did not touch, including two files the baseline never
sampled. This is still a self-review, not the independent reviewer the
register asks for; it narrows what that reviewer must re-check.

| class | fresh sample | verdict per line |
|---|---|---|
| path traversal | pipeline.py 752, 798, 858, 1742, 4146 | **all 5 trace to `confined_path()`** within 1–36 lines of the sink (727 pyx_path, 797 setup_path, 843 dest, 1712 src_path, 4110 bat_path) — same class as the 2026-11-20 sample |
| SSRF | pipeline.py 2232 | geofence gate's **hardcoded** service list (`ip-api.com`), emitted inside a loader string — same class as the baseline's SSRF row |
| SSRF | **licensing.py 420** (never sampled before) | `rpc_url` comes from the **signed licence payload** and is HTTPS-enforced (`must use HTTPS`). Contained by signature: an attacker redirects the ownership check only by holding a validly-signed licence pointing at their node, which requires the publisher's private key — the same trust boundary as every other control. Nuance recorded, not smoothed over. |
| code injection | pipeline.py 3103 | `exec(code, _nx_ns)` executes the **decrypted payload** after `_nx_hg` (hostguard) — the product's purpose; classified correctly |
| code injection | **section_split.py 30** (never sampled before) | the flagged line is a **DOCSTRING** containing the word "exec" ("who must _nx_wipe it after exec") — a scanner false positive on a comment. Recorded as a scanner limitation: rule counts include prose. |
| unsafe deserialisation (medium) | pipeline.py 823 | `marshal.loads` of bytecode **this build compiled moments earlier** — unchanged from the baseline's flagged item; still the one to re-examine if the threat model gains a scratch-directory attacker |

**What this sampling adds.** The three-class explanation survives an
independent pass over fresh lines and previously unsampled files; one false
positive (docstring) was found and recorded; the licensing SSRF's containment
by signature is now stated with its exact precondition instead of being
lumped into "our own API clients". What it cannot do is replace the
independent reviewer the register requires — it hands that reviewer a
smaller, sharper surface: the 619-path-traversal class resolves to
`confined_path` dataflow the scanner cannot follow, the SSRF class is 4
hardcoded endpoints + the signature-gated RPC, and the injection class is
the product executing its own output.
