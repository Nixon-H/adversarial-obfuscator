"""Every corpus artefact must compile, import, and survive being exercised.

This is `scripts/transfer/artefact_gate.py` run as a test. It exists because six
correctness defects in this project were invisible to the tests that existed:
those checked the INPUT, and three of the defects produced output that compiled
and then failed.

The set here is a fast subset — the external modules at one build index plus the
stress module — chosen so the suite stays usable. The full gate (66 artefacts)
is `python3 scripts/transfer/artefact_gate.py`.
"""

import importlib.util
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.diversity.generator import generate_variant  # noqa: E402
from scripts.transfer.external_tasks import (  # noqa: E402
    TASKS as EXT_TASKS, module_source,
)

STRESS = os.path.join(os.path.dirname(__file__), "..", "scripts", "transfer", "corpus", "fixtures", "stress.py")


def _run(source, label, props):
    code = generate_variant(source, 0, {"master_seed": 4242})
    td = tempfile.mkdtemp(prefix="nxk_gate_test_")
    path = os.path.join(td, "artefact.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    compile(code, path, "exec")            # 1. parses
    spec = importlib.util.spec_from_file_location("gate_%s" % label, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)           # 2. imports (runs module-level code)
    funcs = [v for v in vars(mod).values() if callable(v) and not isinstance(v, type)]
    assert funcs, "%s: no callables survived obfuscation" % label
    for fn in funcs:
        for prop in props:
            try:
                prop(fn)                   # 3. exercises
            except NameError as exc:
                pytest.fail("%s: NameError when exercising: %s" % (label, exc))
            except Exception:
                continue


@pytest.mark.parametrize("task_name", sorted(EXT_TASKS))
def test_external_artefact_runs(task_name):
    _run(module_source(task_name), task_name, EXT_TASKS[task_name]["props"])


def test_stress_artefact_runs():
    with open(STRESS, encoding="utf-8") as f:
        source = f.read()
    compile(source, STRESS, "exec")        # the fixture must be valid first
    _run(source, "stress", [lambda f: True])


def test_stress_fixture_is_valid_python():
    """A fixture that does not compile is not a test of the obfuscator.

    Round 102 reported a defect that was actually an invalid fixture. This guard
    exists so that cannot recur silently.
    """
    with open(STRESS, encoding="utf-8") as f:
        source = f.read()
    compile(source, STRESS, "exec")
