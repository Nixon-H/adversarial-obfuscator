"""Hosted-CI real-artifact gate probes (`.github/workflows/security-artifact.yml`).

Builds standalone loader artifacts with the production builder
(`obfuscator.core.pipeline.generate_hybrid_loader_script` -- the same
function the native/hybrid packaging path calls), writes each artifact to
disk, executes it as a FRESH subprocess (real `os._exit` kill ladder, real
clock, real hosted VM signals -- no monkeypatching), and asserts
fail-closed behaviour.

Probes:
  happy      gated artifact (trial + watermark) runs, marker printed, rc 0
  expired    short-lived trial expires on the real clock -> rc 137, silent
  wm-strip   watermark marker stripped -> rc 137, payload never runs.
             Death is reported by the outer integrity self-check (the
             mutation invalidates the merkle/HMAC) rather than silently
             by the watermark gate; silent kill is only reachable for
             gates that fire without byte-level mutation.
  wm-tamper  watermark message edited without the key -> rc 137, same
             mechanism as wm-strip.
  kod        vm_threshold=0.0 forces the VM verdict: NIXON_KOD=1 -> rc 137
             silent (armed kill on the hosted runner, confined to the probe
             process); KOD unset -> rc 0 (report-only never kills)
  vm-report  INFORMATIONAL ONLY: genuine verdict/percent at the default
             threshold on this host. Never asserted (host-noise-dependent);
             logged as hosted evidence.

Why this exists (and what it is NOT): the fast
`scripts/build.py --skip-*` path accepted by argparse but silently drops
`--trial`/`--watermark`/`--vm-threshold` (verified 2026-09-28: a 3-second
trial artifact still ran 8s after the build, rc 0) -- those gates only
ship in the hybrid-loader path. Probing `build.py` negatives would
assert on gates that are not in the artifact. These probes therefore
emit via the production hybrid-loader builder and probe the emitted
FILE, which is the closest faithful replica of a deployed gated loader
exercisable fast (<10 min) on hosted runners.

Python 3.10 compatible: stdlib only (`marshal`, `zlib`, `subprocess`,
`re`, `os`, `sys`, `time`, `json`, `argparse`); no `match`, no `X | Y`
annotations.
"""

import argparse
import json  # noqa: F401 (this line binds a name used by an embedded template)
import marshal
import os
import re
import subprocess
import sys
import time
import zlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import secrets

from obfuscator.core.pipeline import generate_hybrid_loader_script, _stamp_hybrid_selfcheck
from obfuscator.core.utils import fast_xor_bytes
from obfuscator.kill_ladder import KILL_CODE

_BLANKS = {"windows": "", "linux": "", "darwin": ""}
_RAW_KEY = bytes(range(32))
_MARKER = "CI_GATE_OK"
_PROBE_TIMEOUT = 60


def _clean_env(state_dir, extra=None):
    """Hermetic probe env: isolated trial state, no CI-bypass vars."""
    env = dict(os.environ)
    env["XDG_STATE_HOME"] = state_dir
    env["NIXON_LOG_REDIRECT"] = "0"
    # The loader's native-blob fallback honors these ONLY together
    # (pipeline._nx_ci_bypass_ok); scrub so a gate failure can never be
    # masked into a fallback pass. Mirrors tests/test_watermark_gate.py.
    env.pop("NIXON_VERIFY_SKIP_VERSION_CHECK", None)
    env.pop("NIXON_CI", None)
    env.pop("NIXON_ALLOW_SKIP", None)
    env.pop("NIXON_LADDER_DEBUG", None)  # kills must stay silent
    if extra:
        env.update(extra)
    return env


def _emit(payload_src, workdir, name, extra_src="", **kwargs):
    """Emit a gated loader artifact file via the production builder."""
    enc = fast_xor_bytes(
        zlib.compress(marshal.dumps(compile(payload_src, "<ci>", "exec"))),
        _RAW_KEY,
    )
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(), **kwargs
    )
    # Blank native blobs never execute under __main__ (_load_native
    # returns None); drive the encrypted fallback explicitly -- the same
    # pattern tests/test_build_id.py and the gate e2e tests use.
    src += "\n_ci_probe_out = _exec_fallback()\n"
    if extra_src:
        src += extra_src
    # Production artefacts are stamped with their self-check values before
    # shipping; since the AI-BIN-002 fix an unstamped loader fails closed
    # (the zeroed anchor can no longer skip the check), so an unstamped
    # probe artefact dies at startup with a merkle mismatch regardless of
    # the gates being probed. Stamp after the driver line is appended so
    # the hash covers the exact bytes written to disk -- the same ordering
    # production uses. The secret is probe-local and never persisted.
    src = _stamp_hybrid_selfcheck(src, secrets.token_hex(32))
    target = os.path.join(workdir, name)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(src)
    return target


def _run(target, workdir, state_dir, extra_env=None):
    state = os.path.join(workdir, state_dir)
    try:
        os.makedirs(state)
    except OSError:
        pass
    return subprocess.run(
        [sys.executable, target],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        timeout=_PROBE_TIMEOUT,
        cwd=workdir,
        env=_clean_env(state, extra_env),
    )


def _check(name, cond, detail):
    print("PROBE %s: %s (%s)" % (name, "PASS" if cond else "FAIL", detail))
    return cond


def probe_happy(workdir):
    target = _emit(
        "print('%s')\n" % _MARKER,
        workdir,
        "happy.py",
        trial_seconds=7 * 86400,
        watermark="ci-owner",
        watermark_key=b"k" * 32,
        build_id="ci-happy",
    )
    proc = _run(target, workdir, "state_happy")
    return _check(
        "happy",
        proc.returncode == 0 and _MARKER in proc.stdout,
        "rc=%s marker=%s" % (proc.returncode, _MARKER in proc.stdout),
    )


def probe_expired(workdir):
    # 2-second trial minted now; sleep past it on the REAL clock, then
    # run -> absolute deadline expired -> _nx_kill (silent 137).
    target = _emit(
        "print('SHOULD_NOT_PRINT')\n",
        workdir,
        "expired.py",
        trial_seconds=2,
        build_id="ci-expired",
    )
    time.sleep(5)
    proc = _run(target, workdir, "state_expired")
    # The mutation invalidates the merkle/HMAC self-check, so the
    # artefact dies at the outer integrity gate with a diagnostic on
    # stderr before the watermark gate's silent kill can ever fire --
    # silent death is only reachable for gates that trigger WITHOUT
    # byte-level mutation (expired trial, KoD). The security property
    # asserted here is that the payload never executes and the process
    # dies; which layered gate reports first is mechanism, not property.
    ok = (
        proc.returncode == KILL_CODE
        and "SHOULD_NOT_PRINT" not in proc.stdout
        and proc.stdout == ""
    )
    return _check(
        "expired",
        ok,
        "rc=%s stdout=%dB stderr=%dB" % (proc.returncode, len(proc.stdout), len(proc.stderr)),
    )


def _mutate(path, pattern, repl, count=1):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    m = re.search(pattern, src)
    if not m:
        return None
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src.replace(m.group(0), repl, count))
    return m.group(0)


def probe_wm_strip(workdir):
    target = _emit(
        "print('SHOULD_NOT_PRINT')\n",
        workdir,
        "wm_stripped.py",
        watermark="ci-owner",
        watermark_key=b"k" * 32,
        build_id="ci-wm-strip",
    )
    old = _mutate(
        target,
        r"_NX_WATERMARK_MARKER = '([^']+)'",
        "_NX_WATERMARK_MARKER = 'STRIPPED'",
    )
    if old is None:
        return _check("wm-strip", False, "marker literal not found")
    proc = _run(target, workdir, "state_wm_strip")
    # The mutation invalidates the merkle/HMAC self-check, so the
    # artefact dies at the outer integrity gate with a diagnostic on
    # stderr before the watermark gate's silent kill can ever fire --
    # silent death is only reachable for gates that trigger WITHOUT
    # byte-level mutation (expired trial, KoD). The security property
    # asserted here is that the payload never executes and the process
    # dies; which layered gate reports first is mechanism, not property.
    ok = (
        proc.returncode == KILL_CODE
        and "SHOULD_NOT_PRINT" not in proc.stdout
        and proc.stdout == ""
    )
    return _check(
        "wm-strip",
        ok,
        "rc=%s stdout=%dB stderr=%dB" % (proc.returncode, len(proc.stdout), len(proc.stderr)),
    )


def probe_wm_tamper(workdir):
    target = _emit(
        "print('SHOULD_NOT_PRINT')\n",
        workdir,
        "wm_tampered.py",
        watermark="ci-owner",
        watermark_key=b"k" * 32,
        build_id="ci-wm-tamper",
    )
    with open(target, encoding="utf-8") as fh:
        src = fh.read()
    m = re.search(r"_NX_WATERMARK_MSG = '([^']+)'", src)
    if not m:
        return _check("wm-tamper", False, "message literal not found")
    src = src.replace(m.group(0), "_NX_WATERMARK_MSG = 'attacker-msg'", 1)
    src = src.replace(
        "_wm_msg = %r" % (m.group(1),), "_wm_msg = 'attacker-msg'", 1
    )
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(src)
    proc = _run(target, workdir, "state_wm_tamper")
    # Same mechanism note as wm-strip: the mutation dies loudly at the
    # integrity self-check; the asserted property is payload-never-runs.
    ok = (
        proc.returncode == KILL_CODE
        and "SHOULD_NOT_PRINT" not in proc.stdout
        and proc.stdout == ""
    )
    return _check(
        "wm-tamper",
        ok,
        "rc=%s stdout=%dB stderr=%dB" % (proc.returncode, len(proc.stdout), len(proc.stderr)),
    )


def probe_kod(workdir):
    # vm_threshold=0.0 forces the VM verdict on ANY host (pct >= 0
    # always). Armed at RUNTIME via NIXON_KOD=1 -> the probe process
    # must die silent 137; disarmed it must run clean (report-only
    # never kills). Deterministic on hosted runners precisely because
    # it does not depend on genuine VM signals.
    target = _emit(
        "print('%s')\n" % _MARKER,
        workdir,
        "kod.py",
        vm_threshold=0.0,
        build_id="ci-kod",
    )
    armed = _run(target, workdir, "state_kod_armed", {"NIXON_KOD": "1"})
    ok_armed = (
        armed.returncode == KILL_CODE
        and armed.stdout == ""
        and armed.stderr == ""
    )
    calm = _run(target, workdir, "state_kod_calm")
    ok_calm = calm.returncode == 0 and _MARKER in calm.stdout
    return _check(
        "kod",
        ok_armed and ok_calm,
        "armed_rc=%s calm_rc=%s" % (armed.returncode, calm.returncode),
    )


def probe_vm_report(workdir):
    # Informational: genuine verdict at the DEFAULT threshold on this
    # host. Never asserted -- hosted VM signals are host-noise
    # dependent. Logged as evidence for the anti-VM threat-model row.
    # The verdict prints must be part of the artefact BEFORE it is
    # stamped: appending them after sealing invalidates the merkle/HMAC
    # self-check and the artefact dies at startup on EVERY host, so the
    # probe could never observe the evidence it exists to collect.
    target = _emit(
        "print('%s')\n" % _MARKER,
        workdir,
        "vm_report.py",
        build_id="ci-vm-report",
        extra_src=(
            'print("CI_VM_VERDICT=" + str(vm_check()))\n'
            'print("CI_VM_PERCENT=%.2f" % (vm_score_percent(),))\n'
        ),
    )
    proc = _run(target, workdir, "state_vm_report")
    print("INFO vm-report rc=%s" % proc.returncode)
    for line in proc.stdout.splitlines():
        if line.startswith("CI_VM_"):
            print("INFO %s" % line)
    return _check(
        "vm-report",
        proc.returncode == 0 and _MARKER in proc.stdout,
        "rc=%s (verdict itself NOT asserted)" % (proc.returncode,),
    )


PROBES = {
    "happy": probe_happy,
    "expired": probe_expired,
    "wm-strip": probe_wm_strip,
    "wm-tamper": probe_wm_tamper,
    "kod": probe_kod,
    "vm-report": probe_vm_report,
}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Hosted-CI gated-artifact probes.")
    ap.add_argument("--workdir", required=True, help="scratch dir for artifacts")
    ap.add_argument(
        "--only",
        default="",
        help="comma-separated probe subset (default: all)",
    )
    args = ap.parse_args(argv)
    try:
        os.makedirs(args.workdir)
    except OSError:
        pass
    wanted = [p for p in args.only.split(",") if p] or sorted(PROBES)
    unknown = [p for p in wanted if p not in PROBES]
    if unknown:
        print("unknown probes: %s" % ",".join(unknown))
        return 2
    results = []
    for name in wanted:
        try:
            results.append(PROBES[name](args.workdir))
        except Exception as exc:  # fail closed, never a silent pass
            print("PROBE %s: FAIL (exception %r)" % (name, exc))
            results.append(False)
    print("SUMMARY %d/%d probes passed" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
