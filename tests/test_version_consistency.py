"""One version, reported identically everywhere.

The version lived in three places that could disagree: the pipeline
CLI, ``scripts/build.py`` and ``config/default.json``.  They now all
come from :mod:`obfuscator.version`.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from obfuscator.version import PROGRAM_NAME, VERSION, version_string  # noqa: E402


def test_version_string_shape():
    assert version_string() == "%s %s" % (PROGRAM_NAME, VERSION)
    assert re.match(r"^\d+\.\d+\.\d+$", VERSION), VERSION


def test_both_clis_report_the_same_version():
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")

    build = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build.py"),
                             "--version"], capture_output=True, text=True,
                            timeout=300, env=env)
    assert build.returncode == 0, build.stderr[-2000:]
    assert build.stdout.strip() == version_string(), (
        "scripts/build.py reports %r, expected %r"
        % (build.stdout.strip(), version_string()))

    pipe = subprocess.run([sys.executable, "-m", "obfuscator.core.pipeline",
                           "version"], capture_output=True, text=True,
                          timeout=300, env=env, cwd=ROOT)
    assert pipe.returncode == 0, pipe.stderr[-2000:]
    assert version_string() in pipe.stdout, (
        "the pipeline CLI does not report %r: %r" % (version_string(),
                                                     pipe.stdout[-500:]))


def test_config_default_json_agrees_with_the_constant():
    """The config carries the key for the schema; the value must match."""
    path = os.path.join(ROOT, "config", "default.json")
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    assert cfg["shadow_compiler"]["version"] == VERSION, (
        "config/default.json says %r, obfuscator.version says %r"
        % (cfg["shadow_compiler"]["version"], VERSION))


def test_the_changelog_exists_and_names_the_version():
    """There must be one place that says what the product's version is."""
    path = os.path.join(ROOT, "docs", "CHANGELOG.md")
    assert os.path.exists(path), "docs/CHANGELOG.md is missing"
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    assert VERSION in text, "the changelog does not mention version %s" % VERSION


def test_the_readme_distinguishes_the_product_version_from_the_vendor_matrix():
    """The product version and the vendor's v1.1-V10 must not be confused."""
    path = os.path.join(ROOT, "README.md")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    assert "Which version numbers are which" in text, (
        "the README does not separate the product version from the "
        "vendor's version matrix")
    assert "not the vendor" in text.lower() or "not releases" in text.lower()
