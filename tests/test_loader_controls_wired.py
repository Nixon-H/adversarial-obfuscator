"""The loader's security controls must actually control.

Six controls in the emitted hybrid loader were present but inert.  Each
one is now wired, and each has a test here that fails if the wiring is
removed:

* ``--kod`` only wrote a marker; the kill was armed solely by the
  ``NIXON_KOD`` environment variable on the TARGET, so the flag's help
  text ("the artifact terminates when a detection fires") was false.
* The watermark gate was unreachable: no CLI path ever passed a
  watermark, so the emitted gate was always ``DISABLED`` -- while the
  threat model promoted the row to ENVIRONMENT_VALIDATED.
* The hostguard snippet was emitted but never called, so it checked
  nothing.
* The split-bootstrap (Shamir) key was reconstructed and then ignored:
  the payload was decrypted with the direct key, so the control was
  decorative.
* The plaintext-dump debug aid shipped in every release artifact.
* The gates were emitted AFTER the payload entry point, so a
  trial-expired artifact ran its payload and only then died.
"""
import ast
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from obfuscator.core.pipeline import generate_hybrid_loader_script  # noqa: E402
from obfuscator.core.sources import IMPORTER_SOURCE  # noqa: E402

_BLANKS = {"windows": "", "linux": "", "darwin": ""}


def _emit(**kwargs):
    src, _, _ = generate_hybrid_loader_script(_BLANKS, b"", "00" * 32, **kwargs)
    return src


def _run(src, tmp_path, env_extra=None):
    path = os.path.join(str(tmp_path), "loader.py")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src)
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, path], capture_output=True, text=True,
                          timeout=300, env=env, cwd=str(tmp_path))


# --- --kod arms the kill -------------------------------------------------

def test_kod_flag_bakes_the_arming_into_the_loader():
    src = _emit(kod=True, vm_threshold=0.0)
    assert "_NX_KOD_ARMED_BUILD = True" in src
    assert '_os.environ.get("NIXON_KOD", "0")' in src


def test_kod_flag_kills_without_any_environment_variable(tmp_path):
    """The flag alone must arm it -- that is what its help says."""
    src = _emit(kod=True, vm_threshold=0.0)
    run = _run(src, tmp_path)
    assert run.returncode == 137, (
        "--kod did not arm the kill (exit %d); the flag's help says the "
        "artifact terminates when a detection fires" % run.returncode)


def test_without_kod_the_vm_gate_stays_report_only(tmp_path):
    src = _emit(kod=False, vm_threshold=0.0)
    run = _run(src, tmp_path)
    assert run.returncode == 0, (
        "the VM gate killed without being armed (exit %d)" % run.returncode)


# --- the watermark gate is reachable -------------------------------------

def test_watermark_gate_is_armed_when_a_watermark_is_given():
    src = _emit(watermark="owner-tag-42")
    assert '_NX_WATERMARK_GATE = "DISABLED"' not in src
    assert "_NX_WATERMARK_GATE = _nx_watermark_gate()" in src
    assert "_nx_kill(\"watermark-\"" in src


def test_watermark_gate_is_disabled_without_a_watermark():
    src = _emit()
    assert '_NX_WATERMARK_GATE = "DISABLED"' in src


# --- the hostguard is called ---------------------------------------------

def test_hostguard_is_called_not_just_emitted():
    src = _emit(hostguard=True)
    assert "def bind_host(" in src or "def bind_host (" in src
    assert "isolated_exec" in src, (
        "the hostguard snippet is emitted but never called, so it checks "
        "nothing")
    # The snippet publishes the callable the template calls.
    assert "_NX_HOSTGUARD = " in src
    assert '_nx_hg = globals().get("_NX_HOSTGUARD")' in src
    assert "_nx_hg(code, _nx_ns)" in src


def test_without_hostguard_the_payload_uses_a_plain_exec():
    """The branch is always in the template; the callable decides it.

    Without the hostguard snippet nothing publishes _NX_HOSTGUARD, so
    the loader takes the plain-exec branch at run time.  The template
    stays free of hostguard-specific names.
    """
    src = _emit(hostguard=False)
    assert "def bind_host" not in src, (
        "the hostguard must not be published unless it is requested")
    assert "isolated_exec" not in src
    # The template only ever calls the published callable.
    assert '_nx_hg = globals().get("_NX_HOSTGUARD")' in src
    assert "_nx_hg(code, _nx_ns)" in src


# --- the split-bootstrap key is the key that decrypts ---------------------

def test_split_bootstrap_key_is_the_effective_decryption_key():
    src = _emit(split_bootstrap=True)
    assert "_NX_EFF_KEY = BLOB_KEY_SB" in src, (
        "the Shamir key is reconstructed and then ignored; the payload is "
        "still decrypted with the direct key")
    assert "_xor_decrypt(bytes(encrypted), _NX_EFF_KEY)" in src
    assert "_xor_decrypt(encrypted_blob, _NX_EFF_KEY)" in src


def test_without_split_bootstrap_the_effective_key_is_the_direct_one():
    src = _emit(split_bootstrap=False)
    assert "_NX_EFF_KEY = BLOB_KEY" in src
    assert "_NX_EFF_KEY = BLOB_KEY_SB" not in src


# --- the plaintext-dump aid is not in a normal artifact -------------------

def test_the_plaintext_dump_aid_is_not_in_a_normal_artifact():
    # The importer source is what carries the aid.
    assert "NIXON_DUMP_RAW" not in IMPORTER_SOURCE.replace(
        "{RAW_DUMP_BLOCK}", ""), (
        "the plaintext-dump aid is back in the shipped importer source")


def test_the_plaintext_dump_aid_is_build_time_opt_in():
    assert "{RAW_DUMP_BLOCK}" in IMPORTER_SOURCE, (
        "the importer must carry the dump aid behind a placeholder so a "
        "normal build can leave it out")
    # Substituting the placeholder with a no-op leaves no dump code.
    without = IMPORTER_SOURCE.replace("{RAW_DUMP_BLOCK}", "pass")
    assert "NIXON_DUMP_RAW" not in without


# --- the gates run before the payload ------------------------------------

def test_the_payload_entry_point_is_the_last_statement():
    """A gate that fires must be able to stop the payload."""
    src = _emit(trial_seconds=3600)
    tree = ast.parse(src)
    # The entry point is the final top-level statement.
    last = tree.body[-1]
    assert isinstance(last, ast.If), (
        "the loader's last top-level statement is %s, not the __main__ "
        "entry point" % type(last).__name__)
    assert "__main__" in ast.unparse(last)

    # And every gate call comes before it.
    entry_at = src.rfind('if __name__ == "__main__":')
    for marker in ("_nx_kill(", "vm_check()", "driver_check(",
                   "_nx_snapshot_gate()", "_nx_stdlib_gate()"):
        pos = src.find(marker)
        if pos < 0:
            continue
        assert pos < entry_at, (
            "the gate %r is emitted AFTER the payload entry point, so a "
            "firing gate cannot stop the payload" % marker)


def test_the_gates_precede_the_entry_point_in_the_emitted_source():
    src = _emit(trial_seconds=3600, watermark="w")
    entry_at = src.rfind('if __name__ == "__main__":')
    for marker in ("_nx_kill(", "_NX_WATERMARK_GATE = _nx_watermark_gate()"):
        pos = src.find(marker)
        assert 0 <= pos < entry_at, (
            "%r must be emitted before the payload entry point" % marker)
