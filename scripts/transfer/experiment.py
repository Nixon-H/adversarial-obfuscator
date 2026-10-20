"""H0-H5 experiment runner (frozen config companion to arms.py).

For each corpus program x arm: build n variants (per-build wall time +
size recorded), semantic gate (existing, decision unchanged), VM
coverage, cost probes, attack develop/apply (static arm; ghidra
optional), transfer + taxonomy + falsification per arm vs H0 (same
frozen definitions), D_VM + structural diversity, cost summary.

Writes <out_root>/<program>/experiment.json + .md. The locked config
(scripts/transfer/experiment_H0H5.json) hash is embedded; arms.py hash
too. Any post-results change to either hash = a different experiment.
"""
import json
import os
import tempfile
import time

from scripts.transfer import arms as arms_mod
from scripts.transfer import attack as attack_mod
from scripts.transfer import builds as builds_mod
from scripts.transfer import corpus as corpus_mod
from scripts.transfer import extended as ext_mod
from scripts.transfer import measure as measure_mod
from scripts.transfer import protocol


def _demo_argv(prog_name):
    return builds_mod.DEMO_ARGV.get(prog_name, [])


def run_program(prog_entry, out_dir, n_per_arm, attack_arms=("static",),
                seed=0):
    t0 = time.monotonic()
    prog = corpus_mod.load_program(prog_entry["dir"])
    name = prog_entry["name"]
    os.makedirs(out_dir, exist_ok=True)
    orig_path = os.path.join(out_dir, "unprotected.py")
    with open(orig_path, "w", encoding="utf-8") as f:
        f.write(prog["source"])

    from scripts.diversity.generator import DiversityGenerator
    builds, excluded, costs = {}, [], {}
    # Reproducibility fix: hash() is PYTHONHASHSEED-randomized per
    # process, which silently re-seeded every experiment run. Use a
    # stable digest so identical code + config => identical builds.
    import hashlib as _hl
    base_master = 41000 + (int(_hl.sha256(name.encode()).hexdigest(),
                             16) % 1000)

    for arm in arms_mod.ARM_ORDER:
        for i in range(n_per_arm):
            key = "%s:%d" % (arm, i)
            seed_i = base_master * 1000 + 100 * arms_mod.ARM_ORDER.index(arm) + i
            psets, extra = arms_mod.resolve_options(arm, i)
            t_build = time.monotonic()
            try:
                gen = DiversityGenerator(config={
                    "master_seed": seed_i, "pass_sets": psets,
                    "extra_options": extra})
                with tempfile.TemporaryDirectory(prefix="nxk_h_") as td:
                    paths = gen.generate(orig_path, 1, td)
                    with open(paths[0], encoding="utf-8") as f:
                        code = f.read()
                dst = os.path.join(out_dir, "%s_%d.py" % (arm.lower(), i))
                with open(dst, "w", encoding="utf-8") as f:
                    f.write(code)
                dt_build = time.monotonic() - t_build
                ok, detail = builds_mod.semantic_gate(orig_path, dst, name)
                size = os.path.getsize(dst)
                cov = ext_mod.vm_coverage(prog["source"], dst)
                perf = ext_mod.perf_probe(dst, _demo_argv(name))
                rec = {"path": dst, "arm": arm, "pass_set": psets[0],
                       "seed": seed_i, "extra": extra,
                       "gate_passed": ok, "gate_detail": detail}
                costs[key] = {"build_time_s": round(dt_build, 3),
                              "size_bytes": size,
                              "vm_virtualized": cov[0], "vm_eligible": cov[1],
                              "perf": perf}
                if not ok:
                    excluded.append({"path": dst, "arm": arm,
                                     "gate_detail": detail})
                if ok:
                    builds[key] = {"path": dst, "arm": arm,
                                   "ground_truth": prog["ground_truth"],
                                   "vectors": prog["vectors"]}
            except Exception as e:
                excluded.append({"path": "", "arm": arm,
                                 "gate_detail": "build-error: %s" % str(e)[:160]})

    gt, vectors = prog["ground_truth"], prog["vectors"]
    rep = {"experiment": "H0-H5-transfer-v1",
           "spec": protocol.SPEC_VERSION, "spec_date": protocol.SPEC_DATE,
           "program": name, "split": prog_entry["split"],
           "n_per_arm": n_per_arm,
           "config_freeze_hash": arms_mod.config_freeze_hash(),
           "corpus_freeze_hash": corpus_mod.config_freeze_hash(prog["config"]),
           "excluded": excluded, "costs": costs, "arms": {}}
    bkeys = sorted(builds)
    try:
        from scripts.diversity import metrics as div_metrics
        div = div_metrics.DiversityMetrics()
        rep["structural_diversity"] = div.compare_all(
            [builds[k]["path"] for k in bkeys])
    except Exception as e:
        rep["structural_diversity"] = {"error": str(e)[:200]}
    # D_VM over all build pairs.
    dvm = {}
    for a in bkeys:
        for b in bkeys:
            if a < b:
                dvm["%s|%s" % (a, b)] = ext_mod.vm_distance(
                    builds[a]["path"], builds[b]["path"])
    rep["d_vm"] = dvm

    for arm_name in attack_arms:
        arm = (attack_mod.StaticRecoveryAttack()
               if arm_name == protocol.ATTACK_STATIC else
               attack_mod.GhidraAttack())
        art_dir = os.path.join(out_dir, "artifacts_" + arm_name)
        os.makedirs(art_dir, exist_ok=True)
        artifacts, recoveries = {}, {}
        for dk in bkeys:
            try:
                if arm_name == protocol.ATTACK_STATIC:
                    art = arm.develop(builds[dk], art_dir,
                                      prog["source"])
                else:
                    art = arm.develop(builds[dk], art_dir)
            except Exception as e:
                art = {"arm": arm_name, "status": "failed",
                       "reason": "develop: %s" % str(e)[:200]}
            artifacts[dk] = art
            ap = os.path.join(art_dir, dk.replace(":", "_") + ".json")
            try:
                with open(ap, "w", encoding="utf-8") as f:
                    json.dump(art, f, indent=2, sort_keys=True)
            except Exception:
                pass
        for dk in bkeys:
            for tk in bkeys:
                try:
                    rec = arm.apply(artifacts[dk], builds[tk], art_dir)
                except Exception as e:
                    rec = {"status": "failed",
                           "reason": "apply: %s" % str(e)[:200]}
                recoveries[(dk, tk)] = rec
                drec = recoveries[(dk, tk)]
                drec["attack_time_s"] = drec.get("attack_time_s", 0.0)
        entries = measure_mod.transfer_matrix(
            recoveries, gt, vectors, endpoint=protocol.PRIMARY_ENDPOINT)
        for e in entries:
            rec = recoveries.get((e["dev"], e["target"]), {})
            e["attack_time_s"] = rec.get("attack_time_s", 0.0)
            e["rec_status"] = rec.get("status", "?")
        # Falsification per arm vs H0 (frozen definition, H0 as control).
        h0_t = [e["T"] for e in entries
                if e["dev"].startswith("H0") and e["target"].startswith("H0")]
        arm_data = {}
        for arm_id in arms_mod.ARM_ORDER:
            t_arm = [e["T"] for e in entries
                     if e["dev"].startswith(arm_id + ":")
                     and e["target"].startswith(arm_id + ":")]
            arm_data[arm_id] = {
                "T": t_arm,
                "T_ci": list(measure_mod.bootstrap_ci(t_arm, seed=seed)),
                "vs_H0": measure_mod.falsification_verdict(t_arm, h0_t)
                if arm_id != "H0" else None,
            }
        unprot = {"path": orig_path, "arm": protocol.ARM_UNPROTECTED,
                  "ground_truth": gt, "vectors": vectors}
        sanity = {}
        for dk in bkeys:
            try:
                rec = arm.apply(artifacts[dk], unprot, art_dir)
                sc = measure_mod.score_recovery(rec, gt, vectors)
                sanity[dk] = {"S_cfg": sc["S_cfg"], "status": rec.get("status")}
            except Exception as e:
                sanity[dk] = {"S_cfg": 0.0, "status": "failed",
                              "reason": str(e)[:120]}
        rep["arms"][arm_name] = {
            "entries": entries, "per_arm": arm_data,
            "taxonomy": measure_mod.taxonomy_transfer(recoveries, gt, vectors),
            "sanity_unprotected": sanity,
            "skipped": sum(1 for r in recoveries.values()
                           if r.get("status") == "skipped"),
            "failed": sum(1 for r in recoveries.values()
                          if r.get("status") == "failed"),
        }
    rep["elapsed_s"] = round(time.monotonic() - t0, 1)
    with open(os.path.join(out_dir, "experiment.json"), "w",
              encoding="utf-8") as f:
        json.dump(rep, f, indent=2, sort_keys=True)
    return rep


def render_experiment_markdown(rep):
    L = ["# H0-H5 transfer experiment: %s" % rep["program"], "",
         "config `%s` · corpus `%s` · elapsed %ss" % (
             rep["config_freeze_hash"][:12], rep["corpus_freeze_hash"][:12],
             rep["elapsed_s"]),
         "", "excluded builds: %d" % len(rep.get("excluded", []))]
    for ex in rep.get("excluded", [])[:20]:
        L.append("- %s [%s]: %s" % (os.path.basename(ex.get("path", "?")),
                                    ex.get("arm"), ex.get("gate_detail", "")[:90]))
    if len(rep.get("excluded", [])) > 20:
        L.append("- ... +%d more" % (len(rep["excluded"]) - 20))
    costs = rep.get("costs", {})
    L.append("")
    L.append("## cost + coverage per arm (mean)")
    for arm in arms_mod.ARM_ORDER:
        ks = [k for k in costs if k.startswith(arm + ":")]
        if not ks:
            L.append("- %s: no builds" % arm)
            continue
        bt = sum(costs[k]["build_time_s"] for k in ks) / len(ks)
        sz = sum(costs[k]["size_bytes"] for k in ks) / len(ks)
        vv = [costs[k]["vm_virtualized"] for k in ks
              if isinstance(costs[k].get("vm_virtualized"), int)]
        ve = [costs[k]["vm_eligible"] for k in ks
              if isinstance(costs[k].get("vm_eligible"), int)]
        L.append("- %s: n=%d build=%.2fs size=%.0fB vm=%s/%s gate-pass=%d/%d" % (
            arm, len(ks), bt, sz,
            sum(vv) if vv else "?", sum(ve) if ve else "?",
            len([k for k in costs if k.startswith(arm + ":")]),
            rep.get("n_per_arm", 0)))
    for arm, data in rep.get("arms", {}).items():
        L.append("")
        L.append("## arm: %s" % arm)
        for aid, ad in data.get("per_arm", {}).items():
            v = ad["vs_H0"]
            if v is None:
                L.append("- %s: T=%s (control)" % (
                    aid, ["%.2f" % x for x in ad["T"]]))
            else:
                L.append("- %s vs H0: p=%.4f med=%.3f/%.3f → %s" % (
                    aid, v["p"], v["median_hetero"], v["median_seed"],
                    v["verdict"]))
        L.append("taxonomy:")
        for tname, tdata in data.get("taxonomy", {}).items():
            if tdata.get("status") == "uncovered":
                L.append("  - %s: UNCOVERED" % tname)
            else:
                fh = tdata.get("falsification", {})
                L.append("  - %s: med_h=%.3f med_s=%.3f p=%.4f" % (
                    tname, fh.get("median_hetero"), fh.get("median_seed"),
                    fh.get("p")))
    L.append("")
    return "\n".join(L)
