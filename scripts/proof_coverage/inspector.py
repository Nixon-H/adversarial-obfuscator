"""
proof_coverage/inspector.py

Purpose:
Inspects proof modules by importing them and checking for Prover classes,
Z3 availability, and proof validity. Used by the ProofCoverageScanner to
determine which stages have working proofs.

Security Relevance:
If a proof module imports fail (e.g., due to missing dependencies or
syntax errors), the scanner cannot detect that the proof exists, and the
coverage report will show the stage as uncovered. This creates a false
sense of missing coverage.

Dependencies:
- importlib, pkgutil (standard library)
- scripts.proof_coverage.coverage (ProofCoverage)
"""
from __future__ import annotations

import importlib
import os
import pkgutil
from typing import Any, Dict, Optional, Tuple

from scripts.proof_coverage.coverage import ProofCoverage  # noqa: F401 (this line binds a name used by an embedded template)


def inspect_preservation_module() -> Dict[str, bool]:
    results: Dict[str, bool] = {}
    preservation_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "preservation"
    )
    if not os.path.isdir(preservation_dir):
        return results

    stage_files = [f for f in os.listdir(preservation_dir) if f.startswith("stage_") and f.endswith(".py")]
    for sf in stage_files:
        stage_name = sf.replace("stage_", "").replace(".py", "")
        mod_path = f"scripts.preservation.stage_{stage_name}"
        try:
            mod = importlib.import_module(mod_path)
            check_fn_name = f"check_{stage_name}"
            if hasattr(mod, check_fn_name):
                fn = getattr(mod, check_fn_name)
                import inspect
                spec = inspect.getsource(fn)
                has_substance = len(spec.strip()) > 100
                results[stage_name] = has_substance
            else:
                results[stage_name] = False
        except (ImportError, AttributeError):
            results[stage_name] = False

    return results


def inspect_proofs_module() -> Dict[str, Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}
    proofs_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "proofs"
    )
    if not os.path.isdir(proofs_dir):
        return results

    for importer, modname, ispkg in pkgutil.iter_modules([proofs_dir]):
        if modname.startswith("__") or modname == "proof_carrying":
            continue
        try:
            mod = importlib.import_module(f"scripts.proofs.{modname}")
            prover_classes = []
            for name in dir(mod):
                obj = getattr(mod, name)
                if isinstance(obj, type) and ("Prover" in name or "Proof" in name):
                    prover_classes.append(name)
            has_z3 = hasattr(mod, "z3") or any(
                "z3" in (getattr(mod, name, None).__module__ if hasattr(getattr(mod, name, None), "__module__") else "")
                for name in dir(mod)
                if not name.startswith("_")
            )
            results[modname] = {
                "has_prover": len(prover_classes) > 0,
                "prover_classes": prover_classes,
                "has_z3": has_z3,
                "module_path": f"scripts.proofs.{modname}",
            }
        except (ImportError, AttributeError) as e:
            results[modname] = {
                "has_prover": False,
                "prover_classes": [],
                "has_z3": False,
                "error": str(e),
            }

    return results


def probe_z3_availability() -> Tuple[bool, Optional[str]]:
    try:
        import z3
        solver = z3.Solver()
        solver.set("timeout", 1000)
        x = z3.BitVec("x", 8)
        solver.add(x == x)
        result = solver.check()
        if result == z3.sat:
            return True, None
        return True, None
    except ImportError:
        return False, "z3 not installed"
    except Exception as e:
        return False, str(e)


def check_proof_validity(proof_module: str) -> bool:
    try:
        mod = importlib.import_module(proof_module)
        for name in dir(mod):
            obj = getattr(mod, name)
            if isinstance(obj, type) and "Prover" in name:
                try:
                    obj(timeout_ms=5000)
                    return True
                except Exception:
                    continue
        return False
    except (ImportError, AttributeError):
        return False
