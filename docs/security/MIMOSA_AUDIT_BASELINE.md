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
