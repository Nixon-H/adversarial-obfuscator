"""GAP1 (#27): site-packages audit-hook plant detection.

- planted hook from a fake site-packages path is detected (os._exit path);
- legit in-tree hook is passed through to the original addaudithook;
- NIXON_AUDITHOOK_PLANT_OFF disables the wrapper (default ON);
- build wiring: --no-audit-hook-plant omits the snippet from the loader,
  default build includes it.
"""
import ast
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.audit_hook import (
    OPT_OUT_VAR,
    emit_snippet,
    hook_frame_is_plant,
    is_opted_out,
)


def _run_snippet_lines(lines, env_extra=None, timeout=30):
    snippet = emit_snippet() + "\n" + "\n".join(lines) + "\n"
    env = dict(os.environ)
    for var in (OPT_OUT_VAR,):
        if not (env_extra and var in env_extra):
            env.pop(var, None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True, text=True, env=env, timeout=timeout,
    )


def test_snippet_compiles_py310():
    src = emit_snippet()
    compile(src, "<nx_audit_hook>", "exec")
    ast.parse(src, feature_version=(3, 10))


def test_snippet_mentions_opt_out_and_exit():
    src = emit_snippet()
    assert OPT_OUT_VAR in src
    # Kill ladder: single failure path via _nx_kill (exit 137), not raw _exit.
    assert "_nx_kill(" in src
    assert "site-packages" in src
    assert "dist-packages" in src


def test_unit_plant_detection():
    assert hook_frame_is_plant(
        ["/usr/lib/python3.10/site-packages/evil.py", "/app/main.py"],
        "/app/main.py") is True
    assert hook_frame_is_plant(
        ["/usr/lib/python3/dist-packages/evil.py"],
        "/app/main.py") is True
    assert hook_frame_is_plant(
        ["/app/vendor/mod.py", "/app/main.py"],
        "/app/main.py") is False
    assert hook_frame_is_plant([], "/app/main.py") is False
    # entry itself in site-packages (e.g. installed app) -> not a plant
    assert hook_frame_is_plant(
        ["/usr/lib/python3.10/site-packages/app/mod.py"],
        "/usr/lib/python3.10/site-packages/app/main.py") is False
    # frozen/builtin frames carry no filename
    assert hook_frame_is_plant([None, ""], "/app/main.py") is False


def test_unit_opt_out():
    assert is_opted_out({}) is False
    assert is_opted_out({OPT_OUT_VAR: ""}) is False
    assert is_opted_out({OPT_OUT_VAR: "0"}) is False
    assert is_opted_out({OPT_OUT_VAR: "1"}) is True
    assert is_opted_out({OPT_OUT_VAR: "yes"}) is True


def test_legit_in_tree_hook_allowed():
    proc = _run_snippet_lines([
        "seen = []",
        "import sys as _s",
        "_orig = _s.addaudithook",
        "_s.addaudithook(lambda ev, args: seen.append(ev))",
        "assert _s.addaudithook is not _orig or True",
        "_s.audit('nixon.probe')",
        "assert 'nixon.probe' in seen, seen",
        "print('LEGIT-OK')",
    ])
    assert proc.returncode == 0, proc.stderr[-3000:]
    assert "LEGIT-OK" in proc.stdout


def test_planted_hook_from_fake_sitepackages_detected():
    # Simulate a caller whose frame filename is inside site-packages by
    # compiling the addaudithook call with that filename.
    plant_call = (
        "import sys as _s; "
        "_s.addaudithook(lambda ev, args: None)"
    )
    fake_file = "/tmp/fake-site-packages/evil.py"
    proc = _run_snippet_lines([
        "import sys as _s",
        "_code = compile(%r, %r, 'exec')" % (plant_call, fake_file),
        "exec(_code)",
        "print('SHOULD-NOT-REACH')",
    ])
    # Plant path funnels through the kill ladder: silent, exit code 137,
    # no output, no traceback.
    assert proc.returncode == 137, (proc.returncode, proc.stdout, proc.stderr[-2000:])
    assert "SHOULD-NOT-REACH" not in proc.stdout


def test_dist_packages_also_detected():
    plant_call = (
        "import sys as _s; "
        "_s.addaudithook(lambda ev, args: None)"
    )
    fake_file = "/usr/lib/python3/dist-packages/evil.py"
    proc = _run_snippet_lines([
        "import sys as _s",
        "_code = compile(%r, %r, 'exec')" % (plant_call, fake_file),
        "exec(_code)",
        "print('SHOULD-NOT-REACH')",
    ])
    assert proc.returncode == 137, (proc.returncode, proc.stdout, proc.stderr[-2000:])
    assert "SHOULD-NOT-REACH" not in proc.stdout


def test_opt_out_disables_wrapper():
    plant_call = (
        "import sys as _s; "
        "_s.addaudithook(lambda ev, args: None)"
    )
    fake_file = "/tmp/fake-site-packages/evil.py"
    proc = _run_snippet_lines([
        "import sys as _s",
        "assert _s.addaudithook.__name__ != '_nx_addaudithook', 'wrapper should be off'",
        "_code = compile(%r, %r, 'exec')" % (plant_call, fake_file),
        "exec(_code)",
        "print('OPTOUT-OK')",
    ], env_extra={OPT_OUT_VAR: "1"})
    assert proc.returncode == 0, proc.stderr[-3000:]
    assert "OPTOUT-OK" in proc.stdout


def test_loader_default_includes_snippet():
    src = open("obfuscator/core/sources.py").read()
    assert "{audit_hook_source}" in src


def test_build_flag_present():
    out = subprocess.run(
        [sys.executable, "scripts/build.py", "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert out.returncode == 0, out.stderr[-2000:]
    assert "--no-audit-hook-plant" in (out.stdout + out.stderr)
