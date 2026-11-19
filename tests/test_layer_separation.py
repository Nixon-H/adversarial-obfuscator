"""§10 architectural separation: three systems, and the boundary is enforced.

The review's closing architectural directive is specific:

    "separate your project into three independently evaluated systems:
     ProtectionCompiler, RuntimeProtection, PyDeObsBench. This separation
     prevents the protection system from becoming its own judge."

A separation that exists only in a README is not a separation: the first
convenient import reverses it, and then the benchmark is grading code that
imports the thing it grades. So this file asserts the boundary as a test, which
means a future edit that couples the layers fails here rather than quietly
making the benchmark self-referential.

The three layers, as they exist in this tree:

  ProtectionCompiler  obfuscator/core/  + scripts/c_transform.py
                      turns source into a protected artefact
  RuntimeProtection   obfuscator/{cfi,memlock,pack_state,rollback,
                      licence_replay,key_lifecycle,remote_attest,
                      secure_update,runner_attest,native_harden}.py
                      EMITS code the artefact runs; imports no compiler
  PyDeObsBench        pydeobsbench/
                      attacks the artefact; imports no compiler, no runtime

The direction of allowed dependencies is one-way: the benchmark may read
artefacts (as files/bytes), and the runtime modules may be imported by the
compiler when it assembles an artefact. Neither may reach back.
"""
import ast
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

#: Runtime-protection modules: they emit snippets, they do not compile.
RUNTIME_MODULES = (
    "cfi", "memlock", "pack_state", "rollback", "licence_replay",
    "key_lifecycle", "remote_attest", "secure_update", "runner_attest",
    "native_harden",
)

#: Names that only exist in the compiler layer.
COMPILER_ROOTS = ("obfuscator.core", "obfuscator.adaptive_rewriter",
                  "obfuscator.all_preserve", "c_transform")


def _imports(path):
    """Every module name imported by *path* (absolute or from-import)."""
    with open(path, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=path)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
            for alias in node.names:
                names.add(alias.name)
    return names


def _reaches_compiler(names):
    """Which of *names* belong to the compiler layer."""
    return sorted(name for name in names
                  if any(name == root or name.startswith(root + ".")
                         for root in COMPILER_ROOTS))


# ── the runtime layer must not depend on the compiler ────────────────────

@pytest.mark.parametrize("module", RUNTIME_MODULES)
def test_a_runtime_module_does_not_import_the_compiler(module):
    """RuntimeProtection emits text; compiling is the compiler's job.

    If a runtime module imported the compiler, the artefact's enforcement code
    would only be producible by the thing it is meant to constrain, and the two
    layers could no longer be evaluated apart.
    """
    path = os.path.join(REPO, "obfuscator", module + ".py")
    assert os.path.exists(path), "%s is missing" % module
    offenders = _reaches_compiler(_imports(path))
    assert offenders == [], (
        "%s imports the compiler layer (%s); RuntimeProtection must stay "
        "emittable without it" % (module, ", ".join(offenders)))


@pytest.mark.parametrize("module", RUNTIME_MODULES)
def test_a_runtime_module_offers_decision_or_emission_logic(module):
    """Each runtime module exposes a public entry point, not a build step.

    The layer contains two shapes and both are legitimate:

      * EMITTERS write the snippet the artefact runs -- `cfi.emit_snippet`,
        `memlock.emit_snippet`, `pack_state.emit_state_check_snippet`;
      * DECIDERS answer a yes/no question about state the caller holds --
        `rollback.check_rollback`, `key_lifecycle.check_revoked`,
        `remote_attest.verify_response`, `secure_update.verify_update`.

    The earlier version of this test only accepted `emit_`/`verify(`/`check(`,
    which rejected `check_rollback` and `verify_response` -- a test shaped
    around one naming convention rather than around the property. What matters
    is that the module is CALLABLE LOGIC, importable without the compiler, not
    that it spells its verb a particular way.
    """
    path = os.path.join(REPO, "obfuscator", module + ".py")
    functions = sorted(
        node.name for node in ast.parse(open(path, encoding="utf-8").read()).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_"))
    assert functions, "%s exposes no public function" % module
    # A pure decision/emission layer does not spawn builds.
    text = open(path, encoding="utf-8").read()
    for forbidden in ("subprocess.run", "subprocess.Popen", "os.system"):
        assert forbidden not in text, (
            "%s spawns a process (%s); building belongs to the compiler layer"
            % (module, forbidden))


# ── the benchmark must not depend on the compiler ────────────────────────

def test_pydeobsbench_does_not_import_the_compiler():
    """The benchmark grades artefacts; it must not import the grader's subject.

    This is the directive's actual point: "prevents the protection system from
    becoming its own judge". If the harness could import `obfuscator.core`, an
    import-time side effect could change what it measures.
    """
    bench = os.path.join(REPO, "pydeobsbench")
    offenders = {}
    for name in sorted(os.listdir(bench)):
        if not name.endswith(".py"):
            continue
        hits = _reaches_compiler(_imports(os.path.join(bench, name)))
        if hits:
            offenders[name] = hits
    assert offenders == {}, (
        "pydeobsbench imports the compiler layer: %r" % (offenders,))


def test_pydeobsbench_drives_the_builder_as_a_subprocess_only():
    """The one legitimate coupling: invoke the CLI, do not import it.

    A subprocess boundary is what keeps the benchmark honest -- it can observe
    the builder's output and exit status, and nothing else.
    """
    run_py = os.path.join(REPO, "pydeobsbench", "run.py")
    text = open(run_py, encoding="utf-8").read()
    assert "subprocess" in text, "the harness is expected to shell out"
    assert "obfuscator.core.pipeline" in text, (
        "the harness should name the builder module it invokes")


# ── the three layers are all present and distinct ────────────────────────

def test_all_three_layers_exist():
    assert os.path.isdir(os.path.join(REPO, "obfuscator", "core")), \
        "ProtectionCompiler layer missing"
    for module in RUNTIME_MODULES:
        assert os.path.isfile(os.path.join(REPO, "obfuscator", module + ".py"))
    assert os.path.isdir(os.path.join(REPO, "pydeobsbench")), \
        "PyDeObsBench layer missing"


def test_the_benchmark_and_runtime_share_no_private_state():
    """No runtime module may be imported BY the benchmark, either.

    A benchmark that imported `obfuscator.cfi` could assert its own expectations
    from the same constants the emitter uses, which is the self-judging failure
    the directive names, one level down.
    """
    bench = os.path.join(REPO, "pydeobsbench")
    runtime = set(RUNTIME_MODULES)
    offenders = {}
    for name in sorted(os.listdir(bench)):
        if not name.endswith(".py"):
            continue
        imported = _imports(os.path.join(bench, name))
        hits = sorted(imported & runtime)
        hits += sorted(n for n in imported
                       if n.startswith("obfuscator.") and
                       n.split(".", 1)[1] in runtime)
        if hits:
            offenders[name] = hits
    assert offenders == {}, (
        "pydeobsbench imports runtime-protection modules: %r" % (offenders,))


def test_the_runtime_layer_is_importable_without_the_compiler_installed():
    """The five snippet emitters must import with no build toolchain present.

    They are pure stdlib today; this pins that, because a build-time-only
    dependency (cython, cryptography) appearing here would mean the artefact's
    enforcement code could not be produced on a minimal runner.
    """
    for module in ("cfi", "memlock", "pack_state"):
        imported = _imports(os.path.join(REPO, "obfuscator", module + ".py"))
        heavy = {name for name in imported
                 if name.split(".")[0] in {"cython", "Cython", "numpy",
                                           "cryptography", "Crypto"}}
        assert heavy == set(), (
            "%s imports a build-time-only dependency: %s"
            % (module, sorted(heavy)))
