"""Every command-line interface must render its help.

``--help`` is the only place most users ever see a flag's contract, and
it is the easiest thing in a CLI to break: argparse expands a help
string with ``%`` formatting, so a single stray percent sign in a help
text makes the whole ``--help`` crash with a TypeError.  That is not a
hypothetical -- it is what a "90% of baseline" help text did here.

These tests run ``--help`` for every parser in the repo and require it
to exit 0 with non-empty output.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: (label, argv) for every CLI that has a --help.
CLIS = [
    ("scripts/build.py", [os.path.join(ROOT, "scripts", "build.py")]),
    ("pipeline.py", ["-m", "obfuscator.core.pipeline"]),
    ("llvmgen/codegen.py", ["-m", "llvmgen.codegen"]),
    ("irgen/__init__.py", ["-m", "irgen"]),
    ("irgen/chaff_circuits.py", ["-m", "irgen.chaff_circuits"]),
    ("irgen/fragmentation.py", ["-m", "irgen.fragmentation"]),
    ("irgen/jit_template.py", ["-m", "irgen.jit_template"]),
    ("irgen/variant_pool.py", ["-m", "irgen.variant_pool"]),
    ("irgen/watermark.py", ["-m", "irgen.watermark"]),
    ("irgen/microjit.py", ["-m", "irgen.microjit"]),
    ("obfuscator/provenance.py",
     [os.path.join(ROOT, "obfuscator", "provenance.py")]),
    ("obfuscator/dataflow.py", [os.path.join(ROOT, "obfuscator", "dataflow.py")]),
    ("obfuscator/classification.py",
     [os.path.join(ROOT, "obfuscator", "classification.py")]),
    ("vm/__main__.py", ["-m", "vm"]),
    ("encrypt/__init__.py", ["-m", "encrypt"]),
    ("scripts/sbom.py", [os.path.join(ROOT, "scripts", "sbom.py")]),
    ("scripts/secure_cleanup.py",
     [os.path.join(ROOT, "scripts", "secure_cleanup.py")]),
    ("scripts/artifact_sign.py",
     [os.path.join(ROOT, "scripts", "artifact_sign.py")]),
    ("scripts/classify_features.py",
     [os.path.join(ROOT, "scripts", "classify_features.py")]),
    ("scripts/ci_security_artifact.py",
     [os.path.join(ROOT, "scripts", "ci_security_artifact.py")]),
]


def _env():
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
    return env


def test_every_cli_help_renders():
    failures = []
    for label, argv in CLIS:
        proc = subprocess.run([sys.executable] + argv + ["--help"],
                              capture_output=True, text=True, timeout=300,
                              cwd=ROOT, env=_env())
        if proc.returncode != 0:
            failures.append("%s --help exited %d: %s"
                            % (label, proc.returncode,
                               (proc.stderr or proc.stdout)[-400:]))
        elif not proc.stdout.strip():
            failures.append("%s --help printed nothing" % label)
    assert not failures, "\n".join(failures)


def test_no_help_string_contains_a_bare_percent():
    """argparse expands help strings with %-formatting.

    A literal percent sign must be doubled, or the help crashes.
    """
    import re
    offenders = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs
                   if d not in (".git", "__pycache__", "build", "archive",
                                ".opencode", ".pytest_cache", ".mypy_cache",
                                "node_modules")]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    src = fh.read()
            except OSError:
                continue
            for i, line in enumerate(src.splitlines(), 1):
                if "help=" not in line:
                    continue
                for m in re.finditer(r"%(?![%sdfrxo])", line):
                    # %s/%d/%r/%f are argparse's own placeholders and are
                    # fine; anything else is a literal percent.
                    offenders.append("%s:%d: %s" % (path, i, line.strip()[:100]))
    assert not offenders, ("a help string contains a bare %%, which makes "
                           "--help crash: %r" % (offenders[:10],))
