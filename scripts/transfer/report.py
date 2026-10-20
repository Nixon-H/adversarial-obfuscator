"""Experiment orchestration + JSON/markdown report (G2).

run_experiment() executes the frozen protocol end to end for one corpus
program: build matrix -> develop attacks per build -> apply cross matrix
-> endpoints -> T -> CIs -> falsification verdict -> report with
config_freeze_hash, exclusions, timing, overhead.
"""
import json
import os
import tempfile
import time

from scripts.transfer import attack as attack_mod
from scripts.transfer import builds as builds_mod
from scripts.transfer import measure as measure_mod
from scripts.transfer import protocol


def _build_key(arm, idx):
    return "%s:%d" % (arm, idx)


def run_experiment(prog_entry, out_root, n_hetero=3, n_seed=3,
                   attack_arms=("static",), seed=0):
    t0 = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="nxk_g2_") as work:
        matrix = builds_mod.build_matrix(prog_entry, out_root, n_hetero, n_seed)
        gt, vectors = matrix["ground_truth"], matrix["vectors"]
        builds = {}
        for i, rec in enumerate(matrix["variants"]):
            builds[_build_key(rec["arm"], i)] = {
                "path": rec["path"], "arm": rec["arm"],
                "ground_truth": gt, "vectors": vectors}
        report = {"spec": protocol.SPEC_VERSION,
                  "spec_date": protocol.SPEC_DATE,
                  "program": matrix["program"], "split": matrix["split"],
                  "config_freeze_hash": matrix["config_freeze_hash"],
                  "n_hetero": n_hetero, "n_seed": n_seed,
                  "excluded": matrix["excluded"],
                  "arms": {}}
        try:
            from scripts.diversity import metrics as div_metrics
            div = div_metrics.DiversityMetrics()
            paths = [b["path"] for b in builds.values()]
            report["structural_diversity"] = div.compare_all(paths)
        except Exception as e:
            report["structural_diversity"] = {"error": str(e)[:200]}
        for arm_name in attack_arms:
            arm = (attack_mod.StaticRecoveryAttack()
                   if arm_name == protocol.ATTACK_STATIC else
                   attack_mod.GhidraAttack())
            art_dir = os.path.join(work, "artifacts_" + arm_name)
            os.makedirs(art_dir, exist_ok=True)
            artifacts, recoveries = {}, {}
            dev_keys = sorted(builds)
            for dk in dev_keys:
                try:
                    if arm_name == protocol.ATTACK_STATIC:
                        art = arm.develop(builds[dk], art_dir,
                                          matrix["original_source"])
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
            for dk in dev_keys:
                for tk in dev_keys:
                    try:
                        rec = arm.apply(artifacts[dk], builds[tk], art_dir)
                    except Exception as e:
                        rec = {"status": "failed",
                               "reason": "apply: %s" % str(e)[:200]}
                    recoveries[(dk, tk)] = rec
            entries = measure_mod.transfer_matrix(
                recoveries, gt, vectors, endpoint=protocol.PRIMARY_ENDPOINT)
            for e in entries:
                rec = recoveries.get((e["dev"], e["target"]), {})
                e["attack_time_s"] = rec.get("attack_time_s", 0.0)
                e["rec_status"] = rec.get("status", "?")
            h_t = [e["T"] for e in entries
                   if e["dev"].startswith(protocol.ARM_HETERO)
                   and e["target"].startswith(protocol.ARM_HETERO)]
            s_t = [e["T"] for e in entries
                   if e["dev"].startswith(protocol.ARM_SEED_ONLY)
                   and e["target"].startswith(protocol.ARM_SEED_ONLY)]
            verdict = measure_mod.falsification_verdict(h_t, s_t)
            # Control 1 (unprotected): every artifact applied to the
            # original must score HIGH S_cfg — if the attack cannot recover
            # the plain program, cross-build numbers are uninterpretable
            # (broken attack, not transfer resistance).
            unprot = {"path": matrix["unprotected"],
                      "arm": protocol.ARM_UNPROTECTED,
                      "ground_truth": gt, "vectors": vectors}
            sanity = {}
            for dk in dev_keys:
                try:
                    rec = arm.apply(artifacts[dk], unprot, art_dir)
                    sc = measure_mod.score_recovery(rec, gt, vectors)
                    sanity[dk] = {"S_cfg": sc["S_cfg"],
                                  "status": rec.get("status")}
                except Exception as e:
                    sanity[dk] = {"S_cfg": 0.0, "status": "failed",
                                  "reason": str(e)[:120]}
            report["arms"][arm_name] = {
                "entries": entries,
                "T_hetero": h_t, "T_seed": s_t,
                "T_hetero_ci": list(measure_mod.bootstrap_ci(h_t, seed=seed)),
                "T_seed_ci": list(measure_mod.bootstrap_ci(s_t, seed=seed + 1)),
                "falsification": verdict,
                "taxonomy": measure_mod.taxonomy_transfer(
                    recoveries, gt, vectors),
                "skipped": sum(1 for r in recoveries.values()
                               if r.get("status") == "skipped"),
                "failed": sum(1 for r in recoveries.values()
                              if r.get("status") == "failed"),
                "sanity_unprotected": sanity,
            }
        report["elapsed_s"] = round(time.monotonic() - t0, 1)
        sizes = {}
        for k, b in builds.items():
            try:
                sizes[k] = os.path.getsize(b["path"])
            except Exception:
                pass
        report["build_sizes"] = sizes
    return report


def write_report(report, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    return out_path


def render_markdown(report):
    L = ["# G2 transfer report: %s" % report["program"],
         "",
         "spec %s (%s) · freeze `%s` · elapsed %ss" % (
             report["spec"], report["spec_date"],
             report["config_freeze_hash"][:12], report["elapsed_s"]),
         "",
         "excluded builds: %d" % len(report.get("excluded", []))]
    for ex in report.get("excluded", []):
        L.append("- %s: %s" % (os.path.basename(ex["path"]), ex["gate_detail"][:100]))
    for arm, data in report.get("arms", {}).items():
        L.append("")
        L.append("## arm: %s" % arm)
        L.append("T_hetero n=%d ci=%s" % (len(data["T_hetero"]), data["T_hetero_ci"]))
        L.append("T_seed n=%d ci=%s" % (len(data["T_seed"]), data["T_seed_ci"]))
        f = data["falsification"]
        L.append("verdict: %s (U=%.2f p=%.4f med_h=%.3f med_s=%.3f)" % (
            f["verdict"], f["U"], f["p"], f["median_hetero"], f["median_seed"]))
        L.append("skipped=%d failed=%d" % (data["skipped"], data["failed"]))
        L.append("")
        L.append("### attack taxonomy (per-type transfer)")
        for tname, tdata in data.get("taxonomy", {}).items():
            if tdata.get("status") == "uncovered":
                L.append("- %s: UNCOVERED (%s)" % (tname, tdata.get("reason")))
                continue
            fh = tdata.get("falsification", {})
            L.append("- %s: med_h=%.3f med_s=%.3f p=%.4f → %s" % (
                tname, fh.get("median_hetero"), fh.get("median_seed"),
                fh.get("p"), fh.get("verdict")))
        L.append("")
        L.append("| dev \\ target | " + " | ".join(
            sorted({e["target"] for e in data["entries"]})) + " |")
        L.append("|---" * (len({e["target"] for e in data["entries"]}) + 1) + "|")
        devs = sorted({e["dev"] for e in data["entries"]})
        tgts = sorted({e["target"] for e in data["entries"]})
        cell = {(e["dev"], e["target"]): e for e in data["entries"]}
        for d in devs:
            row = [d] + ["%.2f%s" % (cell[(d, t)]["T"],
                                     "" if cell[(d, t)]["flag"] == "ok" else "*")
                         if (d, t) in cell else "-" for t in tgts]
            L.append("| " + " | ".join(row) + " |")
    L.append("")
    return "\n".join(L)
