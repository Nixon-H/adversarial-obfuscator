"""Extended experiment metrics (H0-H5): D_VM, VM coverage, cost.

D_VM (execution-model structural distance between two builds):
- neither build contains VM code -> 0.0
- exactly one contains VM code -> 1.0
- both VM but different families (A vs B) -> 1.0
- both VM, same family -> opcode-permutation distance: fraction of
  code-table positions whose opcodes differ (0 = identical encoding).
  Table unextractable -> None (unmeasured, excluded from means).

Family detection (markers): VM-A emits `elif _op` chains + `while _pc`;
VM-B emits `_handlers` table. Detection is syntactic and documented;
a hand-written lookalike would spoof it (accepted: corpus builds are
machine-generated, never adversarial to the measurer).

VM coverage per build: virtualized / eligible, where eligible =
module-level FunctionDefs passing vm_dispatch._eligible, virtualized =
defs whose emitted body contains VM markers. Unparseable output ->
(None, reason).

Cost per build: build_time_s (generation wall time), size_bytes,
startup_s (import in subprocess), runtime_s + peak_kb (demo argv
execution in subprocess reporting its own ru_maxrss), gate summary
from the matrix record.
"""
import ast
import os
import subprocess
import sys

_VM_A_MARKERS = ("while _pc", "elif _op")
_VM_B_MARKERS = ("_handlers", "_h_cmp")


def detect_vm_family(source):
    """Return 'a', 'b', 'both', or None. Syntactic marker detection."""
    has_a = all(m in source for m in _VM_A_MARKERS)
    has_b = all(m in source for m in _VM_B_MARKERS)
    if has_a and has_b:
        return "both"
    if has_a:
        return "a"
    if has_b:
        return "b"
    return None


def extract_code_tables(source):
    """Extract _code opcode-number sequences from emitted VM functions.

    Returns list of tuples. Unparseable/absent -> [].
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    tables = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "_code"
                            for t in sub.targets)
                    and isinstance(sub.value, ast.Tuple)):
                nums = []
                ok = True
                for elt in sub.value.elts:
                    if (isinstance(elt, ast.Tuple) and len(elt.elts) == 2
                            and isinstance(elt.elts[0], ast.Constant)
                            and isinstance(elt.elts[0].value, int)):
                        nums.append(elt.elts[0].value)
                    else:
                        ok = False
                        break
                if ok and nums:
                    tables.append(tuple(nums))
    return tables


def vm_distance(path_a, path_b):
    """D_VM in [0,1] or None (unmeasured). See module docstring."""
    try:
        with open(path_a, encoding="utf-8") as f:
            sa = f.read()
        with open(path_b, encoding="utf-8") as f:
            sb = f.read()
    except OSError:
        return None
    fa, fb = detect_vm_family(sa), detect_vm_family(sb)
    if fa is None and fb is None:
        return 0.0
    if (fa is None) != (fb is None):
        return 1.0
    if fa == "both" or fb == "both" or fa != fb:
        return 1.0
    ta, tb = extract_code_tables(sa), extract_code_tables(sb)
    if not ta or not tb or len(ta) != len(tb):
        return None
    diffs, total = 0, 0
    for qa, qb in zip(ta, tb):
        n = max(len(qa), len(qb))
        if n == 0:
            continue
        diffs += sum(1 for x, y in zip(qa, qb) if x != y)
        diffs += abs(len(qa) - len(qb))
        total += n
    if total == 0:
        return None
    return diffs / total


def vm_coverage(original_source, variant_path):
    """(n_virtualized, n_eligible) or (None, reason)."""
    try:
        from obfuscator.vm_dispatch import _eligible
    except Exception as e:
        return None, "vm_dispatch unavailable: %s" % e
    try:
        tree = ast.parse(original_source)
    except SyntaxError as e:
        return None, "original unparseable: %s" % e
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if not funcs:
        return (0, 0)
    eligible = []
    for fn in funcs:
        try:
            if _eligible(fn):
                eligible.append(fn.name)
        except Exception:
            continue
    try:
        with open(variant_path, encoding="utf-8") as f:
            vsrc = f.read()
        vtree = ast.parse(vsrc)
    except Exception as e:
        return None, "variant unreadable: %s" % e
    virt = 0
    for node in vtree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        try:
            seg = ast.get_source_segment(vsrc, node) or ""
        except Exception:
            seg = ""
        if detect_vm_family(seg) in ("a", "b"):
            virt += 1
    return virt, len(eligible)


_IMPORT_ONE_LINER = (
    "import importlib.util as _u; _s=_u.spec_from_file_location('m', %r);"
    " _m=_u.module_from_spec(_s); _s.loader.exec_module(_m)"
)


def _spawn_timed(cmd, timeout):
    """Run cmd, return (rc, wall_s, peak_kb_or_None, stdout, stderr).

    Peak RSS via os.wait4 rusage (ru_maxrss, KB on Linux) — practical,
    documented approximation, not laboratory calorimetry.
    """
    import time as _t
    t0 = _t.perf_counter()
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        try:
            _, status, rusage = os.wait4(proc.pid, 0)
            dt = _t.perf_counter() - t0
            out, err = proc.communicate(timeout=timeout)
            rc = os.waitstatus_to_exitcode(status)
            peak = getattr(rusage, "ru_maxrss", None)
            try:
                peak = int(peak) if peak is not None else None
            except Exception:
                peak = None
            return rc, dt, peak, out, err
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
            raise
    except subprocess.TimeoutExpired:
        return None, None, None, b"", b"timeout"


def perf_probe(module_path, demo_argv_sets, timeout=120, repeats=2):
    """Startup + runtime + peak-RSS probe (parent-side, name-agnostic).

    Runs the variant as a black box (import for startup, script runs
    for runtime), so renamed identifiers don't matter. Returns dict;
    never raises (all failures become ok=False entries).
    """
    best_start, peaks = None, []
    for _ in range(max(repeats, 1)):
        rc, dt, peak, _, _ = _spawn_timed(
            [sys.executable, "-c", _IMPORT_ONE_LINER % (module_path,)],
            timeout)
        if rc == 0 and dt is not None:
            best_start = dt if best_start is None else min(best_start, dt)
        if peak is not None:
            peaks.append(peak)
    runs = []
    for argv in demo_argv_sets:
        best, rc0, pk = None, None, None
        for _ in range(max(repeats, 1)):
            rc, dt, peak, out, _ = _spawn_timed(
                [sys.executable, module_path] + list(argv), timeout)
            if dt is not None:
                best = dt if best is None else min(best, dt)
            rc0 = rc
            if peak is not None:
                peaks.append(peak)
                pk = peak if pk is None else max(pk, peak)
        runs.append({"argv": list(argv), "dt_best": best,
                     "ok": rc0 == 0, "rc": rc0, "peak_kb": pk})
    return {"startup_s": best_start,
            "runs": runs,
            "peak_kb": max(peaks) if peaks else None}
