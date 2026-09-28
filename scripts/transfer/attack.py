"""Attack interface + arms (G2 Phase 1).

An attack is a two-phase procedure:
  develop(build, workdir) -> artifact (JSON-serializable dict)
  apply(artifact, target_build, workdir) -> recovery dict

develop() may use ground truth + tooling on the DEVELOPMENT build to
tune parameters. apply() must use ONLY the frozen artifact on the
target (no re-tuning) — otherwise the experiment measures analyst
skill twice, not transfer.

Arms:
- StaticRecoveryAttack (always available, deterministic): AST-level
  function mapping with A_i-calibrated weights + frozen marker rules,
  semantic confirmation via test vectors in subprocess.
- GhidraAttack (needs pytoc toolchain + headless Ghidra): same post
  script + params on compiled variants; graceful skip with reason.
"""
import ast
import json
import os
import subprocess
import sys
import tempfile
import time

from scripts.transfer import protocol

ARTIFACT_VERSION = "1.0.0"

_RUNNER_SRC = r"""
import importlib.util
import json
import sys

def _norm(v):
    try:
        return json.loads(json.dumps(v))
    except Exception:
        return repr(v)

def main():
    mod_path, vec_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(vec_path, encoding="utf-8") as f:
        vectors = json.load(f)
    spec = importlib.util.spec_from_file_location("_nxk_variant", mod_path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except BaseException as e:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"import_error": "%s: %s" % (type(e).__name__, e)}, f)
        return
    results = []
    for v in vectors:
        fn = getattr(mod, v["func"], None)
        entry = {"func": v["func"], "ok": False}
        if callable(fn):
            try:
                got = fn(*v["args"])
                entry["ok"] = (_norm(got) == v["expected"])
                entry["got"] = _norm(got)
            except Exception as e:
                entry["error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
        else:
            entry["error"] = "missing"
        results.append(entry)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"results": results}, f)

main()
"""


def run_vectors(module_path, vectors, timeout=60, name_map=None):
    """Execute vectors against a module file in a subprocess.

    name_map maps ground-truth function names to the candidate names to
    actually call (renamed variants); results are still keyed by the
    ground-truth name. Without a map, GT names are called directly.
    Returns {gt_func: {"ok": bool, ...}}. Never raises (import errors and
    timeouts become per-vector failures).
    """
    nm = name_map or {}
    with tempfile.TemporaryDirectory(prefix="nxk_vec_") as td:
        vec_path = os.path.join(td, "vectors.json")
        out_path = os.path.join(td, "out.json")
        run_path = os.path.join(td, "runner.py")
        with open(vec_path, "w", encoding="utf-8") as f:
            json.dump(vectors, f)
        with open(run_path, "w", encoding="utf-8") as f:
            f.write(_RUNNER_SRC.replace("_nxk_variant", "_nxk_v"))
        # Rewrite vector func names to mapped candidates for the call,
        # keeping GT names as result keys.
        with open(vec_path, encoding="utf-8") as f:
            loaded = json.load(f)
        mapped = [dict(v, func=nm.get(v["func"], v["func"]),
                       _gt=v["func"]) for v in loaded]
        with open(vec_path, "w", encoding="utf-8") as f:
            json.dump(mapped, f)
        try:
            proc = subprocess.run(
                [sys.executable, run_path, module_path, vec_path, out_path],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {v["func"]: {"ok": False, "error": "timeout"} for v in vectors}
        try:
            with open(out_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return {v["func"]: {"ok": False, "error": "no-output rc=%s" % proc.returncode}
                    for v in vectors}
        if "import_error" in data:
            return {v["func"]: {"ok": False, "error": data["import_error"]} for v in vectors}
        # Results arrive keyed by called (mapped) name; translate back to
        # ground-truth keys via the inverse map.
        inv = {}
        for v in vectors:
            inv[nm.get(v["func"], v["func"])] = v["func"]
        out = {}
        for r in data.get("results", []):
            out[inv.get(r["func"], r["func"])] = r
        for v in vectors:
            out.setdefault(v["func"], {"func": v["func"], "ok": False,
                                       "error": "no-result"})
        return out


def module_functions(source):
    """Module-level function defs: (name, node). Static only, safe."""
    tree = ast.parse(source)
    return [(n.name, n) for n in tree.body if isinstance(n, ast.FunctionDef)]


def structural_features(func_node):
    """Cheap structural signature of one function (arity, size, shapes)."""
    args = func_node.args
    arity = len(args.args) + len(args.kwonlyargs)
    has_var = args.vararg is not None or args.kwarg is not None
    n_stmts = len(func_node.body)
    hist = {}
    n_loops = n_try = n_str = 0
    for node in ast.walk(func_node):
        t = type(node).__name__
        hist[t] = hist.get(t, 0) + 1
        if isinstance(node, (ast.For, ast.While)):
            n_loops += 1
        if isinstance(node, ast.Try):
            n_try += 1
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            n_str += 1
    return {"arity": arity, "has_var": has_var, "n_stmts": n_stmts,
            "hist": hist, "n_loops": n_loops, "n_try": n_try, "n_str": n_str}


def _feat_distance(fa, fb, weights):
    score = 0.0
    if fa["arity"] != fb["arity"]:
        return float("inf")
    if fa["has_var"] != fb["has_var"]:
        score += weights["var"] * 10.0
    score += weights["stmts"] * abs(fa["n_stmts"] - fb["n_stmts"])
    keys = set(fa["hist"]) | set(fb["hist"])
    score += weights["struct"] * sum(abs(fa["hist"].get(k, 0) - fb["hist"].get(k, 0)) for k in keys)
    score += weights["shape"] * (abs(fa["n_loops"] - fb["n_loops"])
                                  + abs(fa["n_try"] - fb["n_try"])
                                  + abs(fa["n_str"] - fb["n_str"]))
    return score


_WEIGHT_GRID = [
    {"stmts": 1.0, "struct": 0.5, "shape": 1.0, "var": 1.0},
    {"stmts": 2.0, "struct": 1.0, "shape": 1.0, "var": 1.0},
    {"stmts": 1.0, "struct": 1.0, "shape": 2.0, "var": 1.0},
    {"stmts": 0.5, "struct": 2.0, "shape": 1.0, "var": 1.0},
]


def _greedy_map(candidates, gt_feats, weights):
    """Deterministic argmax mapping (tie-break by candidate name)."""
    mapping = {}
    used = set()
    for gname in sorted(gt_feats):
        best, best_d = None, float("inf")
        for cname in sorted(candidates):
            if cname in used:
                continue
            d = _feat_distance(candidates[cname], gt_feats[gname], weights)
            if d < best_d:
                best, best_d = cname, d
        if best is not None and best_d < float("inf"):
            mapping[gname] = best
            used.add(best)
    return mapping


class StaticRecoveryAttack:
    """Deterministic static attack arm (Phase 1 primary-runnable arm).

    develop(): extract candidate functions from the development build,
    calibrate structural weights by grid search against ground truth,
    record marker rules (string-blob shapes, wrapper shapes). All tuned
    values frozen into the artifact.
    apply(): map target candidates with FROZEN weights, confirm by
    executing ground-truth vectors in a subprocess.
    """
    arm = protocol.ATTACK_STATIC

    def develop(self, build, workdir, original_source):
        t0 = time.monotonic()
        with open(build["path"], encoding="utf-8") as f:
            src = f.read()
        cands = {n: structural_features(nd) for n, nd in module_functions(src)
                 if n != "_demo"}
        # Ground-truth STRUCTURAL features come from the ORIGINAL program
        # (legitimate frozen analyst knowledge: the evaluator knows the
        # corpus program; what is tuned on A_i and frozen is the WEIGHTS
        # and marker rules, never re-tuned per target).
        gt_feats = {}
        for n, nd in module_functions(original_source):
            if n == "_demo":
                continue
            gt_feats[n] = structural_features(nd)
        # Calibrate: grid-search weights maximizing correct arity matches
        # refined by vector confirmation on the DEVELOPMENT build only.
        best_w, best_hit = _WEIGHT_GRID[0], -1
        for w in _WEIGHT_GRID:
            mapping = _greedy_map(cands, gt_feats, w)
            hit = self._confirmed_count(build, mapping)
            if hit > best_hit:
                best_w, best_hit = w, hit
        markers = self._extract_markers(src)
        return {"arm": self.arm, "version": ARTIFACT_VERSION,
                "weights": best_w, "markers": markers,
                "gt_names": sorted(gt_feats), "gt_feats": gt_feats,
                "developed_from": os.path.basename(build["path"]),
                "develop_time_s": round(time.monotonic() - t0, 3)}

    def _confirmed_count(self, build, mapping):
        vecs = [v for v in build["vectors"] if v["func"] in mapping]
        if not vecs:
            return 0
        res = run_vectors(build["path"], vecs, name_map=mapping)
        return sum(1 for v in vecs if res.get(v["func"], {}).get("ok"))

    def _extract_markers(self, src):
        tree = ast.parse(src)
        hexblobs = str_consts = wrappers = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                s = node.value
                str_consts += 1
                if len(s) >= 16 and all(c in "0123456789abcdefABCDEF" for c in s):
                    hexblobs += 1
            if isinstance(node, ast.FunctionDef) and len(node.body) == 1:
                b = node.body[0]
                if isinstance(b, ast.Return) and isinstance(b.value, ast.Call):
                    wrappers += 1
        return {"hex_blobs": hexblobs, "str_consts": str_consts, "wrappers": wrappers}

    def apply(self, artifact, target, workdir):
        t0 = time.monotonic()
        with open(target["path"], encoding="utf-8") as f:
            src = f.read()
        cands = {n: structural_features(nd) for n, nd in module_functions(src)
                 if n != "_demo"}
        gt = target["ground_truth"]
        # FROZEN analyst knowledge from develop() time — never re-derived
        # from the target. Falls back to arity-only if absent (old artifact).
        gt_feats = artifact.get("gt_feats")
        if not gt_feats:
            gt_feats = {}
            for gf in gt["functions"]:
                gt_feats[gf["name"]] = {"arity": gf["arity"], "has_var": False,
                                        "n_stmts": 0, "hist": {}, "n_loops": 0,
                                        "n_try": 0, "n_str": 0}
        mapping = _greedy_map(cands, gt_feats, artifact["weights"])
        vecs = [v for v in target["vectors"] if v["func"] in mapping]
        res = run_vectors(target["path"], vecs, name_map=mapping) if vecs else {}
        per_func = {}
        for gf in gt["functions"]:
            name = gf["name"]
            fv = [v for v in target["vectors"] if v["func"] == name]
            got = [res.get(v["func"], {}).get("ok") for v in fv]
            per_func[name] = {"candidate": mapping.get(name),
                              "passed": sum(1 for g in got if g),
                              "total": len(fv)}
        consts = [c for c in gt.get("constants", [])]
        found = []
        for c in consts:
            if isinstance(c, str) and c in src:
                found.append(c)
            elif repr(c) in src:
                found.append(c)
        return {"status": "ok",
                "mapping": {k: v["candidate"] for k, v in per_func.items()},
                "per_func": per_func,
                "constants_found": found,
                "constants_total": len(consts),
                "attack_time_s": round(time.monotonic() - t0, 3)}


class GhidraAttack:
    """Ghidra transfer arm (primary per protocol where toolchain allows).

    develop(): compile the development build via pytoc, run headless
    Ghidra with the frozen post-script, record baseline detections.
    apply(): compile the target, run the IDENTICAL script + params.
    Recovery here is boundary/count-based (native names are Cython-
    mangled): detected-function count vs ground-truth count, plus
    name-overlap where available. Weaker than the static arm's
    semantic mapping — documented, not hidden.
    Skips gracefully with reason when toolchain/Ghidra are absent.
    """
    arm = protocol.ATTACK_GHIDRA

    POST_SCRIPT = (
        "from ghidra.program.model.listing import FunctionManager\n"
        "fm = currentProgram.getFunctionManager()\n"
        "fns = fm.getFunctions(True)\n"
        "names = []\n"
        "count = 0\n"
        "it = fns.iterator()\n"
        "while it.hasNext():\n"
        "    f = it.next()\n"
        "    names.append(str(f.getName()))\n"
        "    count += 1\n"
        "print('NXK_GHIDRA_JSON:' + __import__('json').dumps("
        "{'count': count, 'names': names}))\n"
    )

    def _compile(self, build, workdir):
        try:
            from scripts.phases.phase_pytoc import cythonize_obfuscated
        except Exception as e:
            return None, "pytoc-unavailable: %s" % e
        out = os.path.join(workdir, os.path.basename(build["path"]) + ".so")
        try:
            so, msg = cythonize_obfuscated(build["path"], out)
        except Exception as e:
            return None, "compile-failed: %s" % e
        if not so:
            return None, "compile-skipped: %s" % msg
        return so, "ok"

    def _ghidra_headless(self):
        cands = [os.environ.get("GHIDRA_HOME", ""),
                 os.environ.get("GHIDRA_INSTALL_DIR", ""),
                 "/opt/ghidra", "/usr/local/ghidra",
                 os.path.expanduser("~/ghidra")]
        for c in cands:
            if not c:
                continue
            ah = os.path.join(c, "support", "analyzeHeadless")
            if os.path.isfile(ah):
                return ah
        return None

    def _run(self, so_path, workdir, script_text):
        ah = self._ghidra_headless()
        if not ah:
            return None, "ghidra-not-found"
        proj = tempfile.mkdtemp(prefix="nxk_ghidra_", dir=workdir)
        sp = os.path.join(proj, "post.py")
        with open(sp, "w", encoding="utf-8") as f:
            f.write(script_text)
        try:
            proc = subprocess.run(
                [ah, proj, "NXK", "-import", so_path,
                 "-postScript", sp, "-deleteProject"],
                capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return None, "ghidra-timeout"
        out = proc.stdout + proc.stderr
        i = out.find("NXK_GHIDRA_JSON:")
        if i < 0:
            return None, "no-output rc=%s" % proc.returncode
        try:
            return json.loads(out[i + len("NXK_GHIDRA_JSON:"):].splitlines()[0]), "ok"
        except Exception as e:
            return None, "parse-failed: %s" % e

    def develop(self, build, workdir):
        so, msg = self._compile(build, workdir)
        if not so:
            return {"arm": self.arm, "version": ARTIFACT_VERSION,
                    "status": "skipped", "reason": msg}
        data, msg2 = self._run(so, workdir, self.POST_SCRIPT)
        if not data:
            return {"arm": self.arm, "version": ARTIFACT_VERSION,
                    "status": "skipped", "reason": msg2}
        return {"arm": self.arm, "version": ARTIFACT_VERSION,
                "status": "ok", "script": self.POST_SCRIPT,
                "baseline_count": data.get("count", 0),
                "ghidra_home": self._ghidra_headless()}

    def apply(self, artifact, target, workdir):
        if artifact.get("status") == "skipped":
            return {"status": "skipped", "reason": artifact.get("reason")}
        so, msg = self._compile(target, workdir)
        if not so:
            return {"status": "skipped", "reason": msg}
        t0 = time.monotonic()
        data, msg2 = self._run(so, workdir, artifact["script"])
        if not data:
            return {"status": "skipped", "reason": msg2}
        gt_n = len(target["ground_truth"]["functions"])
        names = set(data.get("names", []))
        gt_names = {f["name"] for f in target["ground_truth"]["functions"]}
        overlap = len(names & gt_names)
        return {"status": "ok", "detected": data.get("count", 0),
                "gt_total": gt_n, "name_overlap": overlap,
                "attack_time_s": round(time.monotonic() - t0, 3)}
