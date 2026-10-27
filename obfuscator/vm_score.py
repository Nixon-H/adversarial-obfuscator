"""VM confidence scoring (Phase-4 policy/product).

Build-time helpers (:func:`score`, :func:`verdict`) mirror the documented
VM indicator weights. :func:`emit_loader_snippet` produces the runtime
subset for loaders (registry-free, Linux-safe): every SIGNALS entry except
the two Windows-only ones (registry_keys, wmi_bios).

The ``clock_bias`` signal (weight 10, in the ``timing=10`` family) is the
clock-interrupt-bias side-channel detector (V10 REAL signal; algorithm in
``obfuscator/clock_bias.py``, native counterpart in
``runtime/src/timing.rs``): tight-loop delta distribution, flag iff
p99/median > 50x AND tail (>10x median) fraction > 0.5%. Existing signal
weights are unchanged; ``clock_bias`` is ADDITIVE (build-time total
225 -> 235). Loader-wired ON by default (report tier: KOD default-OFF,
Monitor semantics -- no kill path unless NIXON_KOD is armed).
"""

import json

SIGNALS = [
    ("cpuid_hypervisor", 25),
    ("vm_processes", 25),
    ("registry_keys", 20),
    ("mac_prefix", 20),
    ("wmi_bios", 20),
    ("drivers", 20),
    ("fs_artifacts", 15),
    ("net_adapters", 15),
    ("services", 15),
    ("timing", 10),
    ("sysinfo", 10),
    ("hw_constraints", 10),
    ("dmi_strings", 20),
    ("clock_bias", 10),
]

_TOTAL = sum(w for _, w in SIGNALS)

# Subset weights reused by the runtime loader snippet (must stay in sync).
# emit_loader_snippet() serializes this dict into the snippet via json.dumps,
# so the embedded weights match by construction. registry_keys + wmi_bios are
# Windows-only and stay build-time-only (documented in the snippet NOTE).
# clock_bias (10, timing family) is loader-wired ON by default via the
# _nx_has_clock_bias() fragment from obfuscator/clock_bias.py.
_SUBSET_WEIGHTS = {
    "cpuid_hypervisor": 25,
    "vm_processes": 25,
    "dmi_strings": 20,
    "mac_prefix": 20,
    "drivers": 20,
    "fs_artifacts": 15,
    "net_adapters": 15,
    "services": 15,
    "timing": 10,
    "sysinfo": 10,
    "hw_constraints": 10,
    "clock_bias": 10,
}


def score(findings: dict[str, bool]) -> tuple[int, int, float]:
    """Score VM findings.

    Unknown/missing signals count as False (never crashes on missing keys).
    Returns (hit_weight, total, percent_0_100).
    """
    if findings is None:
        findings = {}
    hit = 0
    for name, weight in SIGNALS:
        try:
            val = findings.get(name, False)
        except Exception:
            val = False
        if val:
            hit += weight
    total = _TOTAL
    percent = (hit / total * 100.0) if total else 0.0
    return (hit, total, percent)


def verdict(percent: float, threshold: float = 50.0) -> str:
    """Return 'VM' if percent >= threshold else 'CLEAN'."""
    try:
        p = float(percent)
    except Exception:
        p = 0.0
    try:
        t = float(threshold)
    except Exception:
        t = 50.0
    return "VM" if p >= t else "CLEAN"


def emit_loader_snippet(threshold: float = 50.0, armed: bool = False) -> str:
    """Return Python source implementing the runtime VM-check subset.

    Checks (Linux, registry-free, stdlib-only, no match statement):
      - cpuid_hypervisor (25): /proc/cpuinfo 'hypervisor' flag
      - vm_processes (25): /proc scan for guest-agent processes
      - dmi_strings (20): /sys/class/dmi/id product_name/sys_vendor
      - mac_prefix (20): uuid.getnode() OUI against known VM OUIs
      - drivers (20): /proc/modules (or lsmod fallback) VM module prefixes
      - fs_artifacts (15): known guest-tool paths
      - net_adapters (15): /sys/class/net OUI + iface-name check
      - services (15): guest-agent systemd units
      - timing (10): /proc/stat cpu steal > 0 over two samples
      - sysinfo (10): systemd-detect-virt (exit 0 => virtualized)
      - hw_constraints (10): cpu count <= 2 AND total mem < 2 GiB
      - clock_bias (10): clock-interrupt-bias side-channel
        (_nx_has_clock_bias from obfuscator/clock_bias.py:
        tight perf_counter_ns loop, flag iff p99/median > 50x AND
        tail fraction > 0.5%; Monitor/report tier, default ON)

    Windows-only signals registry_keys (20) and wmi_bios (20) are NOT
    implemented in this Linux snippet; they stay build-time-only. Their
    Windows-side coverage lives in the native stub: native/stub_win.cpp
    CollectAdvancedFingerprint() SMBIOS UUID extraction via
    GetSystemFirmwareTable ('RSMB' provider, line ~328) covers the
    wmi_bios/BIOS angle, and CheckSandboxVM() (line ~502, CPUID leaf
    0x40000000 hypervisor-vendor check at line ~516) covers the
    registry/driver/VM-vendor angle on Windows.

    Computes percent with the SAME weights subset (_SUBSET_WEIGHTS,
    embedded by value) and calls _nx_kill("vm-detect") (exit 137) only if percent >=
    threshold AND env var NIXON_KOD != '0' (default: report only,
    no kill - KOD default-OFF).
    """
    thr = float(threshold)
    weights_json = json.dumps(_SUBSET_WEIGHTS, sort_keys=True)
    from obfuscator.kill_ladder import emit_kill_snippet as _kl_emit
    _kl_src = _kl_emit()
    try:
        from obfuscator.clock_bias import loader_snippet_fragment as _cb_frag
        _cb_src = _cb_frag()
    except Exception:
        _cb_src = (
            "def _nx_has_clock_bias(_samples=2000, _timer=None,"
            " _deltas=None):\n"
            "    return False\n"
        )
    src = (
        "import os as _os\n"
        "import time as _time\n"
        "import uuid as _uuid\n"
        "import subprocess as _subprocess\n"
        "\n"
        f"_NX_VM_THRESHOLD = {thr!r}\n"
        f"_NX_KOD_ARMED_BUILD = {bool(armed)!r}\n"
        f"_NX_VM_WEIGHTS = {weights_json}\n"
        "_NX_VM_OUIS = {\"000569\", \"000c29\", \"001c14\", \"005056\","
        " \"080027\", \"00155d\", \"525400\", \"000f4b\", \"00163e\", \"00215e\"}\n"
        "_NX_VM_DMI_KEYWORDS = (\"vmware\", \"virtualbox\", \"vbox\", \"qemu\","
        " \"kvm\", \"xen\", \"hyper-v\", \"hyperv\", \"parallels\", \"bhyve\","
        " \"virtio\", \"amazon ec2\", \"google compute\")\n"
        "# NOTE: registry_keys + wmi_bios are Windows-only and stay\n"
        "# build-time-only; their Windows-side equivalent is\n"
        "# native/stub_win.cpp CollectAdvancedFingerprint() SMBIOS UUID\n"
        "# extraction via GetSystemFirmwareTable ('RSMB', line ~328) plus\n"
        "# CheckSandboxVM() line ~502 (CPUID leaf 0x40000000 hypervisor\n"
        "# vendor check, line ~516).\n"
        "_NX_VM_PROC_NAMES = (\"vmtoolsd\", \"vboxservice\", \"vboxclient\","
        " \"qemu-ga\", \"hv_kvp_daemon\", \"xe-daemon\")\n"
        "_NX_VM_MOD_PREFIXES = (\"vmw_\", \"vboxguest\", \"vboxsf\","
        " \"virtio\", \"hv_\", \"xen\")\n"
        "_NX_VM_FS_PATHS = (\"/usr/sbin/vmtoolsd\", \"/usr/bin/VBoxClient\","
        " \"/dev/vboxguest\", \"/proc/xen\", \"/sys/hypervisor\")\n"
        "_NX_VM_SVC_NAMES = (\"vmtoolsd\", \"vbox\", \"qemu-guest-agent\")\n"
        "_NX_VM_IFACE_PREFIXES = (\"vmnet\", \"vboxnet\", \"hv_\")\n"
        "\n"
        "\n"
        "def _nx_has_cpu_hypervisor(_cpuinfo=\"/proc/cpuinfo\"):\n"
        "    try:\n"
        "        with open(_cpuinfo, \"r\", errors=\"ignore\") as _f:\n"
        "            for _line in _f:\n"
        "                _l = _line.strip().lower()\n"
        "                if _l.startswith(\"flags\") and \"hypervisor\" in _l:\n"
        "                    return True\n"
        "    except Exception:\n"
        "        pass\n"
        "    return False\n"
        "\n"
        "\n"
        "def _nx_has_vm_processes(_proc_root=\"/proc\"):\n"
        "    try:\n"
        "        for _pid in _os.listdir(_proc_root):\n"
        "            if not _pid.isdigit():\n"
        "                continue\n"
        "            try:\n"
        "                with open(_os.path.join(_proc_root, _pid, \"comm\"),"
        " \"r\", errors=\"ignore\") as _f:\n"
        "                    _comm = _f.read().strip().lower()\n"
        "            except Exception:\n"
        "                _comm = \"\"\n"
        "            try:\n"
        "                with open(_os.path.join(_proc_root, _pid, \"cmdline\"),"
        " \"rb\") as _f:\n"
        "                    _cmd = _f.read().decode(errors=\"ignore\").lower()\n"
        "            except Exception:\n"
        "                _cmd = \"\"\n"
        "            for _n in _NX_VM_PROC_NAMES:\n"
        "                if _n in _comm or _n in _cmd:\n"
        "                    return True\n"
        "    except Exception:\n"
        "        pass\n"
        "    return False\n"
        "\n"
        "\n"
        "def _nx_has_dmi_strings(_dmi_dir=\"/sys/class/dmi/id\"):\n"
        "    try:\n"
        "        for _leaf in (\"product_name\", \"sys_vendor\", \"board_vendor\"):\n"
        "            try:\n"
        "                with open(_os.path.join(_dmi_dir, _leaf),"
        " \"r\", errors=\"ignore\") as _f:\n"
        "                    _v = _f.read().lower()\n"
        "            except Exception:\n"
        "                continue\n"
        "            for _kw in _NX_VM_DMI_KEYWORDS:\n"
        "                if _kw in _v:\n"
        "                    return True\n"
        "    except Exception:\n"
        "        pass\n"
        "    return False\n"
        "\n"
        "\n"
        "def _nx_has_vm_mac():\n"
        "    # sysfs, not uuid: uuid falls back to ip/arp on some hosts and\n"
        "    # blocks for minutes inside this threaded artifact.\n"
        "    try:\n"
        "        _oui = ''\n"
        "        for _n in sorted(_os.listdir('/sys/class/net')):\n"
        "            if _n == 'lo': continue\n"
        "            try:\n"
        "                with open('/sys/class/net/' + _n + '/address') as _f:\n"
        "                    _m = _f.read().strip().lower().replace(':', '')\n"
        "            except Exception: continue\n"
        "            if len(_m) == 12 and _m != '0' * 12:\n"
        "                _oui = _m[:6]\n"
        "                break\n"
        "        if _oui and _oui in _NX_VM_OUIS:\n"
        "            return True\n"
        "    except Exception:\n"
        "        pass\n"
        "    return False\n"
        "\n"
        "\n"
        "def _nx_has_vm_drivers(_modules=\"/proc/modules\"):\n"
        "    try:\n"
        "        try:\n"
        "            with open(_modules, \"r\", errors=\"ignore\") as _f:\n"
        "                _text = _f.read().lower()\n"
        "        except Exception:\n"
        "            _r = _subprocess.run([\"lsmod\"], capture_output=True,"
        " timeout=3)\n"
        "            _text = (_r.stdout or b\"\").decode(errors=\"ignore\").lower()\n"
        "        for _line in _text.splitlines():\n"
        "            _tok = _line.split()[0] if _line.split() else \"\"\n"
        "            for _p in _NX_VM_MOD_PREFIXES:\n"
        "                if _tok.startswith(_p):\n"
        "                    return True\n"
        "    except Exception:\n"
        "        pass\n"
        "    return False\n"
        "\n"
        "\n"
        "def _nx_has_vm_fs(_paths=None):\n"
        "    try:\n"
        "        for _p in (_paths if _paths is not None else _NX_VM_FS_PATHS):\n"
        "            try:\n"
        "                if _os.path.exists(_p):\n"
        "                    return True\n"
        "            except Exception:\n"
        "                continue\n"
        "    except Exception:\n"
        "        pass\n"
        "    return False\n"
        "\n"
        "\n"
        "def _nx_has_vm_net(_net_dir=\"/sys/class/net\"):\n"
        "    try:\n"
        "        for _iface in _os.listdir(_net_dir):\n"
        "            _il = _iface.lower()\n"
        "            if _il == \"lo\":\n"
        "                continue\n"
        "            for _p in _NX_VM_IFACE_PREFIXES:\n"
        "                if _il.startswith(_p):\n"
        "                    return True\n"
        "            try:\n"
        "                with open(_os.path.join(_net_dir, _iface, \"address\"),"
        " \"r\", errors=\"ignore\") as _f:\n"
        "                    _mac = _f.read().strip().lower().replace(\"-\", \":\")\n"
        "                _oui = \"\".join(_mac.split(\":\")[:3])\n"
        "                if len(_oui) == 6 and _oui in _NX_VM_OUIS:\n"
        "                    return True\n"
        "            except Exception:\n"
        "                continue\n"
        "    except Exception:\n"
        "        pass\n"
        "    return False\n"
        "\n"
        "\n"
        "def _nx_has_vm_services(_unit_dir=\"/run/systemd/system\"):\n"
        "    try:\n"
        "        for _u in _os.listdir(_unit_dir):\n"
        "            _ul = _u.lower()\n"
        "            for _n in _NX_VM_SVC_NAMES:\n"
        "                if _n in _ul:\n"
        "                    return True\n"
        "    except Exception:\n"
        "        pass\n"
        "    try:\n"
        "        _r = _subprocess.run([\"systemctl\", \"list-units\","
        " \"--type=service\", \"--all\", \"--no-legend\", \"--no-pager\"],"
        " capture_output=True, timeout=3)\n"
        "        _out = (_r.stdout or b\"\").decode(errors=\"ignore\").lower()\n"
        "        for _n in _NX_VM_SVC_NAMES:\n"
        "            if _n in _out:\n"
        "                return True\n"
        "    except Exception:\n"
        "        pass\n"
        "    return False\n"
        "\n"
        "\n"
        "def _nx_has_steal_time(_stat_path=\"/proc/stat\"):\n"
        "    # Coarse stolen-time check: the 9th cpu field (steal) exists only\n"
        "    # on virtualized kernels; steal > 0 across two 50 ms samples\n"
        "    # means the hypervisor preempted this vCPU. Deterministic\n"
        "    # two-sample read, no wall/process-time skew heuristics.\n"
        "    def _rd():\n"
        "        try:\n"
        "            with open(_stat_path, \"r\", errors=\"ignore\") as _f:\n"
        "                for _line in _f:\n"
        "                    if _line.startswith(\"cpu \"):\n"
        "                        _parts = _line.split()\n"
        "                        if len(_parts) > 8:\n"
        "                            return int(_parts[8])\n"
        "        except Exception:\n"
        "            pass\n"
        "        return None\n"
        "    try:\n"
        "        _a = _rd()\n"
        "        if _a is None:\n"
        "            return False\n"
        "        _time.sleep(0.05)\n"
        "        _b = _rd()\n"
        "        if _b is None:\n"
        "            return False\n"
        "        return (_b - _a) > 0\n"
        "    except Exception:\n"
        "        return False\n"
        "\n"
        "\n"
        "def _nx_has_sysvirt():\n"
        "    try:\n"
        "        _r = _subprocess.run([\"systemd-detect-virt\"],"
        " capture_output=True, timeout=3)\n"
        "        if _r.returncode == 0:\n"
        "            _out = (_r.stdout or b\"\").decode(errors=\"ignore\").strip().lower()\n"
        "            if _out and _out != \"none\":\n"
        "                return True\n"
        "    except Exception:\n"
        "        pass\n"
        "    return False\n"
        "\n"
        "\n"
        "def _nx_has_hw_constraints(_cpuinfo=\"/proc/cpuinfo\","
        " _meminfo=\"/proc/meminfo\"):\n"
        "    try:\n"
        "        _cpus = 0\n"
        "        try:\n"
        "            with open(_cpuinfo, \"r\", errors=\"ignore\") as _f:\n"
        "                for _line in _f:\n"
        "                    if _line.strip().lower().startswith(\"processor\"):\n"
        "                        _cpus += 1\n"
        "        except Exception:\n"
        "            _cpus = 0\n"
        "        if _cpus == 0:\n"
        "            try:\n"
        "                _cpus = _os.cpu_count() or 0\n"
        "            except Exception:\n"
        "                _cpus = 0\n"
        "        _kb = 0\n"
        "        try:\n"
        "            with open(_meminfo, \"r\", errors=\"ignore\") as _f:\n"
        "                for _line in _f:\n"
        "                    _l = _line.strip().lower()\n"
        "                    if _l.startswith(\"memtotal\"):\n"
        "                        _dig = \"\".join(_c for _c in _l if _c.isdigit())\n"
        "                        _kb = int(_dig) if _dig else 0\n"
        "                        break\n"
        "        except Exception:\n"
        "            _kb = 0\n"
        "        if _cpus and _kb:\n"
        "            return _cpus <= 2 and _kb < 2 * 1024 * 1024\n"
        "    except Exception:\n"
        "        pass\n"
        "    return False\n"
        "\n"
        "\n"
        + _cb_src +
        "\n"
        "\n"
        + _kl_src +
        "\n"
        "\n"
        "def vm_check(threshold=None):\n"
        "    \"\"\"Compute runtime VM percent; exit only if KOD armed."
        " Returns 'VM'/'CLEAN'.\"\"\"\n"
        "    _thr = _NX_VM_THRESHOLD if threshold is None else float(threshold)\n"
        "    _findings = {\n"
        "        \"cpuid_hypervisor\": _nx_has_cpu_hypervisor(),\n"
        "        \"vm_processes\": _nx_has_vm_processes(),\n"
        "        \"dmi_strings\": _nx_has_dmi_strings(),\n"
        "        \"mac_prefix\": _nx_has_vm_mac(),\n"
        "        \"drivers\": _nx_has_vm_drivers(),\n"
        "        \"fs_artifacts\": _nx_has_vm_fs(),\n"
        "        \"net_adapters\": _nx_has_vm_net(),\n"
        "        \"services\": _nx_has_vm_services(),\n"
        "        \"timing\": _nx_has_steal_time(),\n"
        "        \"sysinfo\": _nx_has_sysvirt(),\n"
        "        \"hw_constraints\": _nx_has_hw_constraints(),\n"
        "        \"clock_bias\": _nx_has_clock_bias(),\n"
        "    }\n"
        "    _hit = sum(_NX_VM_WEIGHTS[_k] for _k, _v in _findings.items() if _v)\n"
        "    _total = sum(_NX_VM_WEIGHTS.values())\n"
        "    _pct = (_hit / _total * 100.0) if _total else 0.0\n"
        "    _verdict = \"VM\" if _pct >= _thr else \"CLEAN\"\n"
        "    if _verdict == \"VM\" and (_os.environ.get(\"NIXON_KOD\", \"0\") != \"0\" or _NX_KOD_ARMED_BUILD):\n"
        "        _nx_kill(\"vm-detect\")\n"
        "    return _verdict\n"
        "\n"
        "\n"
        "def vm_score_percent():\n"
        "    _findings = {\n"
        "        \"cpuid_hypervisor\": _nx_has_cpu_hypervisor(),\n"
        "        \"vm_processes\": _nx_has_vm_processes(),\n"
        "        \"dmi_strings\": _nx_has_dmi_strings(),\n"
        "        \"mac_prefix\": _nx_has_vm_mac(),\n"
        "        \"drivers\": _nx_has_vm_drivers(),\n"
        "        \"fs_artifacts\": _nx_has_vm_fs(),\n"
        "        \"net_adapters\": _nx_has_vm_net(),\n"
        "        \"services\": _nx_has_vm_services(),\n"
        "        \"timing\": _nx_has_steal_time(),\n"
        "        \"sysinfo\": _nx_has_sysvirt(),\n"
        "        \"hw_constraints\": _nx_has_hw_constraints(),\n"
        "        \"clock_bias\": _nx_has_clock_bias(),\n"
        "    }\n"
        "    _hit = sum(_NX_VM_WEIGHTS[_k] for _k, _v in _findings.items() if _v)\n"
        "    _total = sum(_NX_VM_WEIGHTS.values())\n"
        "    return (_hit / _total * 100.0) if _total else 0.0\n"
    )
    compile(src, "<nx_vm_loader>", "exec")
    return src
