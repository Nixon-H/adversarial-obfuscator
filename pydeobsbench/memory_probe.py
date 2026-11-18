"""Memory-extraction probe: what does a RUNNING artefact leave readable?

The static probes answer "what can an analyst read off the artefact". This one
answers the question the security review actually cares about: an attacker who
executes the artefact and dumps its memory. Without it, "nothing is
recoverable" is not a measured claim -- every earlier number in this harness
was static.

Method (no debugger required, no ptrace-scope change):

  1. run the artefact under the real interpreter, in its own directory;
  2. poll /proc/<pid>/maps and read every READABLE private mapping while the
     process is alive -- this is what `gcore` would capture, minus the
     ptrace handshake;
  3. scan those bytes for the payload's ground-truth secrets and identifiers;
  4. also scan the process's regular-file fds to separate "decrypted payload
     in heap" from "the loader's own literals".

The scan runs repeatedly during startup and again just before exit, because
moving decryption means the window matters: a section is plaintext for a short
interval. The probe therefore reports the MAXIMUM match count seen across all
samples, not a single snapshot -- a single snapshot is how a moving-decryption
scheme gets scored as clean by accident.

Reading /proc/<pid>/mem needs ptrace attach on Linux (kernel.yama.ptrace_scope
allows a parent to read its own child, which is what we do here), so this works
without privileges: we are the parent.

Safety notes (the probe audits hostile code, so it must not itself be a
liability):
  * the target is executed with a LIST argv and no shell, so a path
    containing spaces or metacharacters cannot become a command;
  * the target path must resolve to a regular file that the caller passed
    explicitly; it is absolute-ised once and never rebuilt from strings;
  * every /proc path is built from a validated integer pid.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

_READ_CHUNK = 1 << 20        # 1 MiB per read() call
_MAX_MAP_BYTES = 96 << 20    # cap per mapping so a huge heap does not stall


def _validated_target(artefact_path):
    """Resolve the artefact to an absolute regular file, or raise.

    No globbing, no shell, no relative traversal: the probe only ever executes
    a path the caller named, and refuses anything that is not a plain file.
    """
    if not artefact_path:
        raise ValueError("artefact_path is required")
    full = os.path.realpath(os.path.abspath(artefact_path))
    if not os.path.isfile(full):
        raise ValueError("artefact_path is not a regular file: %r"
                         % (artefact_path,))
    return full


def _proc(pid, leaf):
    """Build /proc/<pid>/<leaf> from a validated integer pid (no string input)."""
    if not isinstance(pid, int) or pid <= 0:
        raise ValueError("pid must be a positive int")
    return "/proc/%d/%s" % (pid, leaf)


def _readable_private_maps(pid):
    """Yield (start, end, perms, path) for readable private mappings."""
    try:
        with open(_proc(pid, "maps")) as fh:
            rows = fh.readlines()
    except OSError:
        return
    for row in rows:
        parts = row.split()
        if len(parts) < 2:
            continue
        try:
            lo_s, hi_s = parts[0].split("-")
            lo, hi = int(lo_s, 16), int(hi_s, 16)
        except ValueError:
            continue
        perms = parts[1]
        if "r" not in perms:
            continue
        path = parts[5] if len(parts) >= 6 else ""
        # Skip the interpreter's own file-backed text: identifiers found there
        # would be Python's, not the payload's. Keep [heap], [stack], [anon],
        # and private writable file mappings (where decrypted buffers land).
        if path.endswith((".so", ".so.1", ".pyd", ".py", ".pyc")) and "w" not in perms:
            continue
        yield lo, hi, perms, path


def _dump_region(fd, lo, size):
    """pread a region; returns bytes actually read (short reads are normal).

    `fd` is an integer descriptor: os.pread does not accept file objects.
    """
    try:
        return os.pread(fd, size, lo)
    except OSError:
        return b""


def _scan_blob(blob, needles):
    """Which needles appear in this byte range? Literal bytes only."""
    hits = set()
    for n in needles:
        if n and n in blob:
            hits.add(n)
    return hits


def _fds_text(pid):
    """Concatenate the contents of the process's regular-file fds."""
    out = []
    try:
        names = os.listdir(_proc(pid, "fd"))
    except OSError:
        return b""
    for name in names:
        if not name.isdigit():
            continue
        p = _proc(pid, "fd/" + name)
        try:
            tgt = os.readlink(p)
        except OSError:
            continue
        if tgt.startswith(("/dev/", "pipe:", "socket:", "anon_inode:")):
            continue
        try:
            with open(p, "rb") as fh:
                out.append(fh.read(1 << 20))
        except OSError:
            continue
    return b"\n".join(out)


def probe_memory_extraction(artefact_path, target=None, timeout=180,
                            samples=24, settle=0.03):
    """Run the artefact and measure what its live memory exposes.

    Returns a structured result with the maximum observed recovery across
    samples, so a scheme that is plaintext only briefly is still caught.
    """
    target = target or {}
    secrets = [s.encode() for s in target.get("secrets", []) if s]
    names = [n.encode() for n in target.get("names", []) if n]
    needles = secrets + names

    try:
        full = _validated_target(artefact_path)
    except ValueError as exc:
        return {"probe": "memory_extraction", "ran": False,
                "error": str(exc)}

    env = dict(os.environ, NIXON_LOG_REDIRECT="0")
    argv = [sys.executable, full]          # list argv, shell=False by default
    workdir = os.path.dirname(full)
    try:
        proc = subprocess.Popen(argv, cwd=workdir, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=env, shell=False)
    except OSError as exc:
        return {"probe": "memory_extraction", "error": str(exc)[:200],
                "ran": False}

    max_secret = set()
    max_name = set()
    map_counts = []
    regions_seen = set()
    samples_taken = 0
    # A payload that exits in a few milliseconds yields ONE sample, which is
    # exactly the situation a moving-decryption scheme would be scored clean
    # in by accident. Measured 2026-11-18: a 3-line plain payload produced
    # samples=1 and missed its own module-level secret, while the same payload
    # held open for 2s reported it. So `samples` is reported alongside the
    # result: a single-sample measurement is visible as low confidence rather
    # than passing as a clean sweep.
    try:
        with open(_proc(proc.pid, "mem"), "rb", buffering=0) as mem:
            memfd = mem.fileno()
            for _ in range(samples):
                if proc.poll() is not None:
                    break
                distinct = set()
                for lo, hi, perms, path in _readable_private_maps(proc.pid):
                    size = min(hi - lo, _MAX_MAP_BYTES)
                    if size <= 0:
                        continue
                    distinct.add((lo, path))
                    regions_seen.add(path or "[anon]")
                    off = 0
                    while off < size:
                        want = min(_READ_CHUNK, size - off)
                        blob = _dump_region(memfd, lo + off, want)
                        if not blob:
                            break
                        found = _scan_blob(blob, needles)
                        for f in found:
                            (max_secret if f in secrets else max_name).add(f)
                        off += len(blob)
                map_counts.append(len(distinct))
                samples_taken += 1
                time.sleep(settle)
            # One last pass on whatever is still mapped, then fd contents.
            try:
                for lo, hi, perms, path in _readable_private_maps(proc.pid):
                    size = min(hi - lo, _MAX_MAP_BYTES)
                    if size > 0:
                        blob = _dump_region(memfd, lo, size)
                        for f in _scan_blob(blob, needles):
                            (max_secret if f in secrets else max_name).add(f)
            except OSError:
                pass
            try:
                fdblob = _fds_text(proc.pid)
                for f in _scan_blob(fdblob, needles):
                    (max_secret if f in secrets else max_name).add(f)
            except OSError:
                pass
    except (OSError, PermissionError) as exc:
        proc.kill()
        return {"probe": "memory_extraction", "ran": True,
                "error": "%s: %s" % (type(exc).__name__, exc),
                "note": "could not read /proc/<pid>/mem; treat as NOT MEASURED"}
    finally:
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    return {
        "probe": "memory_extraction",
        "ran": True,
        "samples": samples_taken,
        "max_mapped_regions": max(map_counts) if map_counts else 0,
        "region_kinds": sorted(r for r in regions_seen)[:20],
        "secrets_total": len(secrets),
        "secrets_recovered": len(max_secret),
        "secrets_hit": [s.decode() for s in sorted(max_secret)],
        "names_total": len(names),
        "names_recovered": len(max_name),
        "names_hit": [n.decode() for n in sorted(max_name)],
        "evidence": "literal byte match in a readable private mapping or "
                    "regular-file fd of the LIVE process; max across samples",
    }
