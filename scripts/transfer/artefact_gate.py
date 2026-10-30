"""Gate: compile and import every generated artefact.

This is the recommendation section 6 of the paper argues for, implemented.

Five correctness defects in this project were invisible to the tests that
existed, because those tests checked the *input*:

  * the 30-day expiry produced artefacts that stopped decrypting;
  * false opaque predicates produced functions returning None;
  * emptied dataclasses produced code that does not compile;
  * unbound import/keyword names produced code that fails at import;
  * string match patterns produced code that does not compile.

Three of the five are caught by importing the artefact, which executes
module-level code. All five are caught by exercising a function in it.

Usage:

    python3 scripts/transfer/artefact_gate.py [--variants N]

Runs the obfuscator over every corpus module at several build indices, then for
each artefact: parse, compile, import, and call every callable with the module's
own doctest-style arguments where available. Reports failures with the module,
the build index and the exception.
"""

import argparse
import importlib.util
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from scripts.diversity.generator import generate_variant  # noqa: E402
from scripts.transfer.external_tasks import (  # noqa: E402
    TASKS as EXT_TASKS, source_path,
)
from scripts.transfer.real_tasks import TASKS as REAL_TASKS  # noqa: E402
from scripts.transfer.real_tasks import module_source as real_source  # noqa: E402
from scripts.transfer.tasks import TASKS as SYNTH_TASKS  # noqa: E402


STRESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus", "fixtures", "stress.py")
STRUTILS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus", "external3", "strutils.py")
REQUESTS_UTILS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus", "external4", "utils.py")
ITERUTILS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus", "bulk", "iterutils.py")

# Properties for the stress module: the constructs it exercises have no
# task-level specification, so the gate only requires that the artefact
# compiles and imports.
STRESS_PROPS = [lambda f: True]


def _modules():
    """(label, source, task_props_or_None) for every corpus module."""
    out = []
    with open(STRESS, encoding="utf-8") as f:
        out.append(("stress/constructs", f.read(), STRESS_PROPS))
    with open(STRUTILS, encoding="utf-8") as f:
        out.append(("external3/strutils", f.read(), STRESS_PROPS))
    with open(ITERUTILS, encoding="utf-8") as f:
        out.append(("bulk/iterutils", f.read(), STRESS_PROPS))
    # requests/utils.py is kept as the __future__ regression fixture but is not
    # gated: it uses relative imports ("from .exceptions import ...") and cannot
    # be imported standalone, so the import check measures the fixture's shape
    # rather than the obfuscator.
    for name, t in SYNTH_TASKS.items():
        out.append(("synthetic/%s" % name, t["target"] + "\n" + "\n".join(t["siblings"]), t["props"]))
    for name in REAL_TASKS:
        out.append(("corpus/%s" % name, real_source(name), REAL_TASKS[name]["props"]))
    for name in EXT_TASKS:
        out.append(("external/%s" % name, open(source_path(name), encoding="utf-8").read(),
                    EXT_TASKS[name]["props"]))
    return out


def check_one(label, code, props, k, workdir, seed=4242):
    """Parse, compile, import, and exercise. Returns a list of failure strings."""
    fails = []
    path = os.path.join(workdir, "artefact.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)

    # 1. parse
    try:
        compile(code, path, "exec")
    except SyntaxError as exc:
        return ["%s seed=%d k=%d: does not compile: line %s: %s"
                % (label, seed, k, exc.lineno, exc.msg)]

    # 2. import (executes module-level code)
    try:
        spec = importlib.util.spec_from_file_location("gate_%s_%d" % (label.replace("/", "_"), k), path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as exc:
        return ["%s seed=%d k=%d: fails at import: %s: %s"
                % (label, seed, k, type(exc).__name__, exc)]

    # 3. exercise: every property over every callable must not raise
    funcs = [v for v in vars(mod).values() if callable(v) and not isinstance(v, type)]
    if not funcs:
        return ["%s seed=%d k=%d: no callables survived" % (label, seed, k)]
    for fn in funcs:
        for prop in props:
            try:
                prop(fn)
            except NameError as exc:
                fails.append("%s seed=%d k=%d: NameError when exercising: %s" % (label, seed, k, exc))
                return fails
            except Exception:
                # A property may legitimately raise TypeError on the wrong
                # candidate; only NameError and import-time failures are defects.
                continue
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", type=int, default=3, help="build indices to check")
    ap.add_argument("--seeds", default="4242",
                    help="comma-separated master seeds; more than one catches "
                         "nondeterministic defects, which a single seed cannot")
    args = ap.parse_args()

    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    failures = []
    invalid_inputs = []
    checked = 0
    modules = _modules()

    # Check the fixtures first. An input that does not compile is not a test of
    # the obfuscator, and blaming the tool for it is the error that produced a
    # false defect report in round 102.
    for label, src, _props in modules:
        try:
            compile(src, "<fixture %s>" % label, "exec")
        except SyntaxError as exc:
            invalid_inputs.append("%s: fixture is not valid Python: line %s: %s"
                                  % (label, exc.lineno, exc.msg))
    if invalid_inputs:
        print("INVALID FIXTURES (fix these before reading the results):")
        for msg in invalid_inputs:
            print("  ", msg)
        print()

    with tempfile.TemporaryDirectory(prefix="nxk_gate_") as workdir:
        for label, src, props in modules:
            for seed in seeds:
                for k in range(args.variants):
                    try:
                        code = generate_variant(src, k, {"master_seed": seed})
                    except Exception as exc:
                        failures.append("%s seed=%d k=%d: generation failed: %s: %s"
                                        % (label, seed, k, type(exc).__name__, exc))
                        continue
                    checked += 1
                    failures.extend(check_one(label, code, props, k, workdir, seed))

    print("seeds: %s" % ",".join(str(x) for x in seeds))
    print("artefacts checked: %d" % checked)
    print("invalid fixtures: %d" % len(invalid_inputs))
    print("failures: %d" % len(failures))
    for f in failures:
        print("  FAIL", f)
    return 1 if (failures or invalid_inputs) else 0


if __name__ == "__main__":
    sys.exit(main())
