"""Runtime VM-subset coverage tests (anti-VM gap closure).

Validates that emit_loader_snippet() covers every Linux-checkable SIGNALS
entry, that snippet helpers accept path overrides for fakery, and that KOD
semantics are unchanged. Helpers exec the snippet source (not imports) so
tests exercise exactly what ships to the target.
"""

import ast
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.vm_score import SIGNALS, _SUBSET_WEIGHTS, emit_loader_snippet

# Windows-only: build-time-only by design, documented in the snippet NOTE.
WINDOWS_ONLY = {"registry_keys", "wmi_bios"}


def _stub_run(stdout=b"", exc=None):
    def _fake(*a, **k):
        if exc is not None:
            raise exc
        return type("R", (), {"stdout": stdout, "returncode": 0})()
    return _fake


def _exec_snippet(threshold=50.0):
    src = emit_loader_snippet(threshold=threshold)
    ns = {}
    exec(compile(src, "<nx_vm_subset>", "exec"), ns)
    return src, ns


def test_weights_in_sync():
    d = dict(SIGNALS)
    # Existing weights unchanged (clock_bias is ADDITIVE: +10, timing
    # family; no existing weight touched).
    for name, w in (("cpuid_hypervisor", 25), ("dmi_strings", 20),
                    ("mac_prefix", 20), ("sysinfo", 10),
                    ("timing", 10), ("clock_bias", 10)):
        assert _SUBSET_WEIGHTS[name] == w
    # Subset weights match SIGNALS for the same names.
    for name, w in _SUBSET_WEIGHTS.items():
        assert d[name] == w, name
    # All Linux-checkable signals covered.
    covered = set(_SUBSET_WEIGHTS)
    expected = {n for n, _ in SIGNALS} - WINDOWS_ONLY
    assert covered == expected


def test_snippet_weights_match_by_construction():
    src, ns = _exec_snippet()
    assert ns["_NX_VM_WEIGHTS"] == _SUBSET_WEIGHTS
    for name, w in _SUBSET_WEIGHTS.items():
        assert ns["_NX_VM_WEIGHTS"][name] == w


def test_snippet_compiles_and_parses_310():
    src, _ = _exec_snippet()
    compile(src, "<t>", "exec")
    ast.parse(src, feature_version=(3, 10))
    assert "match " not in src  # stdlib-only, no match statement


def test_all_linux_signals_wired():
    src, ns = _exec_snippet()
    for name in _SUBSET_WEIGHTS:
        assert name in src, name
    for fn in ("_nx_has_vm_processes", "_nx_has_vm_drivers", "_nx_has_vm_fs",
               "_nx_has_vm_net", "_nx_has_vm_services", "_nx_has_steal_time",
               "_nx_has_hw_constraints", "_nx_has_clock_bias"):
        assert callable(ns[fn]), fn
    # vm_check + vm_score_percent consult every subset signal (exec the
    # snippet source has no retrievable file, so check src text instead).
    for name in _SUBSET_WEIGHTS:
        assert src.count('"%s"' % name) >= 2, name  # vm_check + vm_score_percent


def test_windows_only_documented_not_implemented():
    src, ns = _exec_snippet()
    assert "registry_keys" not in ns["_NX_VM_WEIGHTS"]
    assert "wmi_bios" not in ns["_NX_VM_WEIGHTS"]
    assert "registry_keys" in src and "wmi_bios" in src  # NOTE comment
    assert "stub_win.cpp" in src


def test_vm_processes_positive_and_negative(tmp_path):
    _, ns = _exec_snippet()
    f = ns["_nx_has_vm_processes"]
    assert f(str(tmp_path)) is False  # empty root
    pid = tmp_path / "1234"
    pid.mkdir()
    (pid / "comm").write_text("vmtoolsd\n")
    (pid / "cmdline").write_bytes(b"/usr/sbin/vmtoolsd\x00")
    assert f(str(tmp_path)) is True
    # cmdline-only hit (comm empty).
    pid2 = tmp_path / "5678"
    pid2.mkdir()
    (pid2 / "comm").write_text("init\n")
    (pid2 / "cmdline").write_bytes(b"/usr/bin/qemu-ga --daemon\x00")
    assert f(str(tmp_path)) is True
    # benign tree: no hit.
    clean = tmp_path / "clean"
    clean.mkdir()
    p = clean / "1"
    p.mkdir()
    (p / "comm").write_text("systemd\n")
    (p / "cmdline").write_bytes(b"/sbin/init\x00")
    assert f(str(clean)) is False
    # non-digit entries skipped, missing files tolerated.
    (tmp_path / "self").mkdir(exist_ok=True)
    assert f(str(tmp_path)) is True  # still finds 1234


def test_drivers_positive_and_negative(tmp_path, monkeypatch):
    _, ns = _exec_snippet()
    f = ns["_nx_has_vm_drivers"]
    mod = tmp_path / "modules"
    mod.write_text("tun 77824 0 - Live 0x0\nnft_reject 12288 0 - Live 0x0\n")
    assert f(str(mod)) is False
    mod.write_text("vboxguest 12345 0 - Live 0x0\ntun 77824 0 - Live 0x0\n")
    assert f(str(mod)) is True
    mod.write_text("virtio_net 123 0 - Live 0x0\n")
    assert f(str(mod)) is True
    mod.write_text("hv_vmbus 99 0 - Live 0x0\n")
    assert f(str(mod)) is True
    # Prefix-anchored: 'myvmw_x' must NOT match 'vmw_'.
    mod.write_text("myvmw_x 1 0 - Live 0x0\n")
    assert f(str(mod)) is False
    # Missing file + failing lsmod => False (no fallback crash).
    monkeypatch.setattr(ns["_subprocess"], "run", _stub_run(exc=OSError("no lsmod")))
    assert f(str(tmp_path / "nope")) is False


def test_fs_artifacts_positive_and_negative(tmp_path):
    _, ns = _exec_snippet()
    f = ns["_nx_has_vm_fs"]
    assert f(["/nonexistent-nx-vm-probe"]) is False
    marker = tmp_path / "vboxguest"
    marker.write_text("x")
    assert f([str(marker)]) is True
    # /sys/hypervisor exists as an (empty) dir even on bare metal kernels,
    # so the default path set may hit there; assert explicit-absent instead.
    assert f(["/nonexistent-nx-vm-probe-1", "/nonexistent-nx-vm-probe-2"]) is False


def test_net_adapters_oui_and_iface_names(tmp_path):
    _, ns = _exec_snippet()
    f = ns["_nx_has_vm_net"]
    net = tmp_path / "net"
    net.mkdir()
    lo = net / "lo"
    lo.mkdir()
    (lo / "address").write_text("00:00:00:00:00:00\n")
    assert f(str(net)) is False  # lo excluded
    eth = net / "eth0"
    eth.mkdir()
    (eth / "address").write_text("00:0c:29:aa:bb:cc\n")  # VMware OUI
    assert f(str(net)) is True
    (eth / "address").write_text("f8:54:f6:1b:af:f7\n")  # physical OUI
    assert f(str(net)) is False
    vbox = net / "vboxnet0"
    vbox.mkdir()
    (vbox / "address").write_text("0a:00:27:00:00:01\n")
    assert f(str(net)) is True
    # Dash-separated MAC tolerated.
    (vbox / "address").write_text("00-15-5D-01-02-03\n")  # Hyper-V OUI
    assert f(str(net)) is True
    # Name-prefix hit needs no address file.
    net2 = tmp_path / "net2"
    net2.mkdir()
    (net2 / "hv_net0").mkdir()
    assert f(str(net2)) is True
    # Unknown iface with missing address file: no hit.
    net3 = tmp_path / "net3"
    net3.mkdir()
    (net3 / "eth9").mkdir()
    assert f(str(net3)) is False


def test_services_unit_dir_and_systemctl(tmp_path, monkeypatch):
    _, ns = _exec_snippet()
    f = ns["_nx_has_vm_services"]
    # Deterministic: stub systemctl (this dev host has vbox* HOST units).
    monkeypatch.setattr(ns["_subprocess"], "run", _stub_run(b""))
    assert f(str(tmp_path)) is False
    (tmp_path / "qemu-guest-agent.service").write_text("x")
    assert f(str(tmp_path)) is True
    clean = tmp_path / "cleanunits"
    clean.mkdir()
    assert f(str(clean)) is False
    # systemctl output hit even with empty unit dir.
    monkeypatch.setattr(ns["_subprocess"], "run",
                        _stub_run(b"qemu-guest-agent.service loaded active\n"))
    assert f(str(clean)) is True
    # systemctl failure tolerated (systemd absent).
    monkeypatch.setattr(ns["_subprocess"], "run", _stub_run(exc=OSError("no systemd")))
    assert f(str(clean)) is False


def test_timing_steal_detection(tmp_path):
    _, ns = _exec_snippet()
    f = ns["_nx_has_steal_time"]
    idle = tmp_path / "stat"
    idle.write_text("cpu  100 0 100 10000 0 0 0 0 0 0\n")
    assert f(str(idle)) is False  # steal constant 0
    # Two-sample growth requires monkeypatched reads; static file => 0 delta.
    assert f(str(idle)) is False
    missing = tmp_path / "nostat"
    assert f(str(missing)) is False
    short = tmp_path / "short"
    short.write_text("cpu  1 2 3\n")  # fewer than 9 fields
    assert f(str(short)) is False


def test_timing_steal_positive(tmp_path, monkeypatch):
    _, ns = _exec_snippet()
    f = ns["_nx_has_steal_time"]
    stat = tmp_path / "stat"
    stat.write_text("cpu  100 0 100 10000 0 0 0 5 0 0\n")

    def fake_sleep(_s):
        stat.write_text("cpu  200 0 200 20000 0 0 0 9 0 0\n")

    monkeypatch.setattr(ns["_time"], "sleep", fake_sleep)
    assert f(str(stat)) is True


def test_hw_constraints(tmp_path):
    _, ns = _exec_snippet()
    f = ns["_nx_has_hw_constraints"]
    cpu = tmp_path / "cpuinfo"
    mem = tmp_path / "meminfo"
    cpu.write_text("processor\t: 0\nprocessor\t: 1\n")
    mem.write_text("MemTotal:        1048576 kB\n")  # 1 GiB
    assert f(str(cpu), str(mem)) is True
    mem.write_text("MemTotal:        7842136 kB\n")  # ~8 GiB
    assert f(str(cpu), str(mem)) is False
    cpu.write_text("processor\t: 0\n" * 12)
    mem.write_text("MemTotal:        1048576 kB\n")
    assert f(str(cpu), str(mem)) is False  # 12 cpus
    assert f(str(tmp_path / "n1"), str(tmp_path / "n2")) is False


def test_kod_gate_respected(monkeypatch):
    _, ns = _exec_snippet(threshold=0.0)  # threshold 0 => always VM verdict
    monkeypatch.setenv("NIXON_KOD", "0")
    assert ns["vm_check"]() == "VM"  # must NOT os._exit with KOD=0
    monkeypatch.delenv("NIXON_KOD", raising=False)
    assert ns["vm_check"]() == "VM"  # default '0' => no exit


def test_kod_armed_exits(monkeypatch):
    import os as _os
    _, ns = _exec_snippet(threshold=0.0)
    monkeypatch.setenv("NIXON_KOD", "1")
    exited = {}

    def fake_exit(code):
        exited["code"] = code
        raise SystemExit(code)

    monkeypatch.setattr(_os, "_exit", fake_exit)
    # Need the snippet's _os reference patched too (it imported os as _os).
    # The kill ladder embeds its own "import os as _nx_os" INSIDE _nx_kill.
    monkeypatch.setitem(ns, "_os", _os)
    monkeypatch.setitem(ns, "_nx_os", _os)
    with pytest.raises(SystemExit):
        ns["vm_check"]()
    assert exited.get("code") == 137


def test_end_to_end_consistent_with_build_time(monkeypatch):
    monkeypatch.setenv("NIXON_KOD", "0")
    _, ns = _exec_snippet(threshold=50.0)
    # Stub the host-dependent probes that legitimately hit on this dev
    # host for HOST-side reasons (vbox host units in systemctl, empty
    # /sys/hypervisor dir present on bare-metal kernels), so e2e asserts
    # the scoring math, not host quirks. Unit tests above cover the
    # individual probes with fakes.
    monkeypatch.setattr(ns["_subprocess"], "run", _stub_run(b""))
    orig_fs = ns["_nx_has_vm_fs"]
    ns["_nx_has_vm_fs"] = lambda _p=None: orig_fs(["/nonexistent-nx-vm-probe"])
    pct = ns["vm_score_percent"]()
    assert 0.0 <= pct <= 100.0
    result = ns["vm_check"]()
    assert result == ("VM" if pct >= 50.0 else "CLEAN")
    # Runtime percent must equal build-time score() over the same findings.
    findings = {
        "cpuid_hypervisor": ns["_nx_has_cpu_hypervisor"](),
        "vm_processes": ns["_nx_has_vm_processes"](),
        "dmi_strings": ns["_nx_has_dmi_strings"](),
        "mac_prefix": ns["_nx_has_vm_mac"](),
        "drivers": ns["_nx_has_vm_drivers"](),
        "fs_artifacts": ns["_nx_has_vm_fs"](),
        "net_adapters": ns["_nx_has_vm_net"](),
        "services": ns["_nx_has_vm_services"](),
        "timing": ns["_nx_has_steal_time"](),
        "sysinfo": ns["_nx_has_sysvirt"](),
        "hw_constraints": ns["_nx_has_hw_constraints"](),
        "clock_bias": ns["_nx_has_clock_bias"](),
    }
    sub_total = sum(_SUBSET_WEIGHTS.values())
    # build-time score uses full 235 total; rescale to subset for comparison.
    subset_hit = sum(_SUBSET_WEIGHTS[k] for k, v in findings.items() if v)
    expected = (subset_hit / sub_total * 100.0) if sub_total else 0.0
    assert abs(pct - expected) < 1e-9
    # This dev machine is bare metal: expect CLEAN (documents assumption).
    assert result == "CLEAN"
    assert pct < 50.0
