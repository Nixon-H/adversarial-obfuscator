import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.vm_score import SIGNALS, emit_loader_snippet, score, verdict


def test_signals_total_is_235():
    # NOTE: the weights as specified in the task sum to 225, not 220
    # (25*2 + 20*5 + 15*3 + 10*3 = 225). We keep the specified weights
    # verbatim; total is derived from SIGNALS. The additive V10
    # clock_bias signal (+10, timing family, existing weights unchanged)
    # brings the build-time total to 235.
    assert sum(w for _, w in SIGNALS) == 235


def test_signals_names_and_weights():
    d = dict(SIGNALS)
    assert d["cpuid_hypervisor"] == 25
    assert d["vm_processes"] == 25
    assert d["registry_keys"] == 20
    assert d["mac_prefix"] == 20
    assert d["wmi_bios"] == 20
    assert d["drivers"] == 20
    assert d["fs_artifacts"] == 15
    assert d["net_adapters"] == 15
    assert d["services"] == 15
    assert d["timing"] == 10
    assert d["sysinfo"] == 10
    assert d["hw_constraints"] == 10
    assert d["dmi_strings"] == 20
    assert d["clock_bias"] == 10  # V10 additive signal, timing family


def test_scoring_math():
    total = sum(w for _, w in SIGNALS)
    hit, t, pct = score({"cpuid_hypervisor": True, "vm_processes": True})
    assert (hit, t) == (50, total)
    assert abs(pct - 50 / total * 100) < 1e-9
    hit2, total2, pct2 = score({n: True for n, _ in SIGNALS})
    assert hit2 == total and total2 == total and pct2 == 100.0
    assert score({}) == (0, total, 0.0)


def test_missing_keys_safe():
    total = sum(w for _, w in SIGNALS)
    # Only one known key; everything else missing -> no crash.
    hit, t, pct = score({"timing": True})
    assert (hit, t) == (10, total)
    # Unknown keys ignored.
    assert score({"nope": True}) == (0, total, 0.0)
    # None / falsy values safe.
    assert score({"cpuid_hypervisor": False}) == (0, total, 0.0)


def test_verdict_boundary():
    assert verdict(50.0) == "VM"
    assert verdict(49.999) == "CLEAN"
    assert verdict(100.0) == "VM"
    assert verdict(0.0) == "CLEAN"
    assert verdict(10.0, threshold=10.0) == "VM"
    assert verdict(9.9, threshold=10.0) == "CLEAN"


def test_snippet_compiles_and_subset_weights_match():
    src = emit_loader_snippet()
    compile(src, "<t>", "exec")
    # Same weights subset used at runtime.
    for name, w in (("cpuid_hypervisor", 25), ("dmi_strings", 20),
                    ("mac_prefix", 20), ("sysinfo", 10)):
        assert f'"{name}": {w}' in src


def test_snippet_returns_clean_without_exiting():
    src = emit_loader_snippet(threshold=50.0)
    ns = {}
    exec(compile(src, "<t>", "exec"), ns)
    assert "NIXON_KOD" not in os.environ or os.environ.get("NIXON_KOD") == "0" or True
    old = os.environ.get("NIXON_KOD")
    os.environ["NIXON_KOD"] = "0"
    try:
        # Must not raise SystemExit / call os._exit on this host with KOD off.
        result = ns["vm_check"]()
        assert result in ("VM", "CLEAN")
        pct = ns["vm_score_percent"]()
        assert 0.0 <= pct <= 100.0
        assert result == ("VM" if pct >= 50.0 else "CLEAN")
    finally:
        if old is None:
            del os.environ["NIXON_KOD"]
        else:
            os.environ["NIXON_KOD"] = old


def test_snippet_kod_gating_present():
    src = emit_loader_snippet()
    assert "NIXON_KOD" in src
    # Kill ladder: single failure path via _nx_kill (exit 137).
    assert "_nx_kill(" in src
    # Default-OFF: gate requires env != '0'.
    assert '!= "0"' in src or "!='0'" in src or '!= \'0\'' in src
    # Registry-free Linux checks present.
    assert "/proc/cpuinfo" in src
    assert "systemd-detect-virt" in src
    # MAC OUI check reads sysfs; uuid.getnode() is not used (it can shell
    # out to ip/arp and blocks inside the threaded loader).
    assert "/sys/class/net" in src
    assert "getnode" not in src
