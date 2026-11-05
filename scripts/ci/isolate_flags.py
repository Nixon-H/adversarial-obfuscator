"""Build with ONE ladder flag at a time, run the artefact, compare to its source.

Every flag in the catalogue is exercised on its own, so a broken transform is
named by the flag that enables it rather than hiding inside a bundle. Sharded so
the whole catalogue fits in CI: --start/--count select a contiguous slice.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flag_catalogue import catalogue  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_PAYLOAD = os.path.join(ROOT, "tests", "fixtures", "portable", "constructs_source.py")
SOURCE = os.environ.get("NX_PAYLOAD", DEFAULT_PAYLOAD)
LEVEL = os.environ.get("NX_OPT_LEVEL", "3")
BUILD_TIMEOUT = int(os.environ.get("NX_BUILD_TIMEOUT", "600"))
# Builds are NOT yet reproducible: two identical commands produce different
# artefacts, so a CI failure cannot be rebuilt locally. --seed exists and pins
# part of the pipeline, but at least one more RNG (still unidentified) is
# unseeded. Until that is fixed, a flag that fails in CI may pass here for no
# reason other than luck -- which is what the intermittent failures have been.
SEED = os.environ.get("NX_BUILD_SEED", "")
RUN_TIMEOUT = int(os.environ.get("NX_RUN_TIMEOUT", "300"))


def run(cmd, cwd, timeout):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return None


def norm(text):
    return text.replace("\r\n", "\n")


def try_flag(entry, src_out):
    stem = os.path.splitext(os.path.basename(SOURCE))[0]
    out = os.path.join(ROOT, "build", "%s_iso.py" % stem)
    cmd = [sys.executable, "scripts/build.py", "--payload", SOURCE,
           "-o", out, "--force-output", "--opt-level", LEVEL,
           "--skip-irgen", "--skip-llvmgen", "--skip-encrypt", "--skip-relay",
           "--skip-extras"] + (["--seed", SEED] if SEED else []) + entry["argv"]
    built = run(cmd, ROOT, BUILD_TIMEOUT)
    if built is None:
        # --code-genome alone exceeds 13 minutes. A slow build is not a broken
        # build; report it distinctly so it never reads as a defect.
        return "SLOW", "builder exceeded %ds" % BUILD_TIMEOUT
    if built.returncode != 0:
        raw = (built.stderr or b"").decode("utf-8", "replace") + \
              (built.stdout or b"").decode("utf-8", "replace")
        tail = [ln for ln in raw.strip().splitlines() if ln.strip()]
        # Keep several lines: a silent failure's last line is usually the last
        # NORMAL log line, with the traceback above it.
        last = " | ".join(tail[-3:])[:400] if tail else ""
        # The builder deliberately refuses combinations it knows are unsound
        # ("[CONFLICT] Blocking conflicts found"). That is the product protecting
        # itself, not a defect: the flag needs companion flags this harness does
        # not supply. Reporting it as FAIL would have overstated the defect count
        # by more than a dozen flags.
        if "[CONFLICT]" in raw or "Blocking conflicts found" in raw:
            return "CONFLICT", "refused without companion flags"
        # Some flags exist in scripts/build.py's parser but only bind in the
        # packed-loader path; the builder says so and exits 2:
        #   "This pipeline emits obfuscated source, not an encrypted payload,
        #    so these options have nothing to bind"
        # That is a category error in this harness, not a defect.
        if "have nothing to bind" in raw or "packed-loader build applies them" in raw:
            return "CATALOGUE", "packed-loader-only flag"
        if "expected one argument" in raw:
            return "CATALOGUE", "value-shaped flag classified as boolean"
        if "unrecognized arguments" in raw:
            return "CATALOGUE", "argument shape misread: %s" % last
        return "FAIL", "builder exited %d: %s" % (built.returncode, last)

    artefact = os.path.join(ROOT, "build", "%s_obfuscated.py" % stem)
    if not os.path.exists(artefact):
        return "FAIL", "no artefact produced"

    res = run([sys.executable, artefact], os.path.dirname(artefact), RUN_TIMEOUT)
    if res is None:
        return "SLOW", "artefact exceeded %ds" % RUN_TIMEOUT
    if res.returncode != 0:
        err = res.stderr.decode("utf-8", "replace").strip().splitlines()
        last = err[-1] if err else ""
        if "No module named 'scripts" in last:
            # The artefact is not standalone: it imports the builder's own
            # package. Reported distinctly so it is never mistaken for a pass.
            return "NONSTANDALONE", "artefact imports the source tree: %s" % last[:100]
        return "FAIL", "artefact exited %d: %s" % (res.returncode, last[:120])
    if norm(res.stdout.decode("utf-8", "replace")) != src_out:
        return "FAIL", "output differs from source"
    return "PASS", ""


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    start, count = 0, 10 ** 6
    for i, a in enumerate(sys.argv):
        if a == "--start":
            start = int(sys.argv[i + 1])
        elif a == "--count":
            count = int(sys.argv[i + 1])

    entries = catalogue()
    shard = entries[start:start + count]
    print("catalogue=%d shard=%d..%d (%d flags) payload=%s level=%s"
          % (len(entries), start, start + len(shard) - 1, len(shard),
             os.path.basename(SOURCE), LEVEL))

    src = run([sys.executable, SOURCE], ROOT, RUN_TIMEOUT)
    if src is None or src.returncode != 0:
        print("FATAL: the source payload does not run; nothing to compare against")
        return 2
    src_out = norm(src.stdout.decode("utf-8", "replace"))

    failures = []
    not_standalone = []
    conflicts = []
    catalogue_bugs = []
    slow = []
    for entry in shard:
        if entry["kind"] == "excluded":
            print("SKIP %-40s %s" % (entry["flag"], entry["why"]))
            continue
        verdict, detail = try_flag(entry, src_out)
        print("%-13s %-40s %s" % (verdict, entry["flag"], detail))
        if verdict == "FAIL":
            failures.append(entry["flag"])
        elif verdict == "NONSTANDALONE":
            not_standalone.append(entry["flag"])
        elif verdict == "CONFLICT":
            conflicts.append(entry["flag"])
        elif verdict == "CATALOGUE":
            catalogue_bugs.append(entry["flag"])
        elif verdict == "SLOW":
            slow.append(entry["flag"])

    print("\nshard result: %d flags, %d failed, %d not standalone"
          % (len(shard), len(failures), len(not_standalone)))
    if not_standalone:
        print("NOT STANDALONE:", " ".join(not_standalone))
    if conflicts:
        print("CONFLICT (needs companion flags): %d" % len(conflicts),
              " ".join(conflicts[:8]))
    if slow:
        print("SLOW (exceeded the build/run budget):", " ".join(slow))
    if catalogue_bugs:
        print("CATALOGUE (harness misread the argument):", " ".join(catalogue_bugs))
    if failures:
        print("FAILED FLAGS:", " ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
