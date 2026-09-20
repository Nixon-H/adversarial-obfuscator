"""VM confidence scoring (Phase-4 policy/product).

Build-time helpers (:func:`score`, :func:`verdict`) mirror the documented
VM indicator weights. :func:`emit_loader_snippet` produces a small runtime
subset for loaders (registry-free, Linux-safe).
"""

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
]

_TOTAL = sum(w for _, w in SIGNALS)

# Subset weights reused by the runtime loader snippet (must stay in sync).
_SUBSET_WEIGHTS = {
    "cpuid_hypervisor": 25,
    "dmi_strings": 20,
    "mac_prefix": 20,
    "sysinfo": 10,
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


def emit_loader_snippet(threshold: float = 50.0) -> str:
    """Return Python source implementing a small runtime VM-check subset.

    Checks (Linux, registry-free):
      - cpuid_hypervisor (25): /proc/cpuinfo 'hypervisor' flag
      - dmi_strings (20): /sys/class/dmi/id product_name/sys_vendor
      - mac_prefix (20): uuid.getnode() OUI against known VM OUIs
      - sysinfo (10): systemd-detect-virt (exit 0 => virtualized)

    Computes percent with the SAME weights subset and calls os._exit(1)
    only if percent >= threshold AND env var NIXON_KOD != '0'
    (default: report only, no kill - KOD default-OFF).
    """
    thr = float(threshold)
    src = f'''import os as _os
import uuid as _uuid
import subprocess as _subprocess

_NX_VM_THRESHOLD = {thr!r}
_NX_VM_WEIGHTS = {{"cpuid_hypervisor": 25, "dmi_strings": 20, "mac_prefix": 20, "sysinfo": 10}}
_NX_VM_OUIS = {{"000569", "000c29", "001c14", "005056", "080027", "00155d", "525400", "000f4b", "00163e", "00215e"}}
_NX_VM_DMI_KEYWORDS = ("vmware", "virtualbox", "vbox", "qemu", "kvm", "xen", "hyper-v", "hyperv", "parallels", "bhyve", "virtio", "amazon ec2", "google compute")


def _nx_has_cpu_hypervisor():
    try:
        with open("/proc/cpuinfo", "r", errors="ignore") as _f:
            for _line in _f:
                _l = _line.strip().lower()
                if _l.startswith("flags") and "hypervisor" in _l:
                    return True
    except Exception:
        pass
    return False


def _nx_has_dmi_strings():
    try:
        for _p in ("/sys/class/dmi/id/product_name", "/sys/class/dmi/id/sys_vendor", "/sys/class/dmi/id/board_vendor"):
            try:
                with open(_p, "r", errors="ignore") as _f:
                    _v = _f.read().lower()
                for _kw in _NX_VM_DMI_KEYWORDS:
                    if _kw in _v:
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _nx_has_vm_mac():
    try:
        _node = _uuid.getnode()
        _oui = format((_node >> 24) & 0xFFFFFF, "06x")
        if _oui in _NX_VM_OUIS:
            return True
    except Exception:
        pass
    return False


def _nx_has_sysvirt():
    try:
        _r = _subprocess.run(["systemd-detect-virt"], capture_output=True, timeout=3)
        if _r.returncode == 0:
            _out = (_r.stdout or b"").decode(errors="ignore").strip().lower()
            if _out and _out != "none":
                return True
    except Exception:
        pass
    return False


def vm_check(threshold=None):
    """Compute runtime VM percent; exit only if KOD armed. Returns 'VM'/'CLEAN'."""
    _thr = _NX_VM_THRESHOLD if threshold is None else float(threshold)
    _findings = {{
        "cpuid_hypervisor": _nx_has_cpu_hypervisor(),
        "dmi_strings": _nx_has_dmi_strings(),
        "mac_prefix": _nx_has_vm_mac(),
        "sysinfo": _nx_has_sysvirt(),
    }}
    _hit = sum(_NX_VM_WEIGHTS[_k] for _k, _v in _findings.items() if _v)
    _total = sum(_NX_VM_WEIGHTS.values())
    _pct = (_hit / _total * 100.0) if _total else 0.0
    _verdict = "VM" if _pct >= _thr else "CLEAN"
    if _verdict == "VM" and _os.environ.get("NIXON_KOD", "0") != "0":
        _os._exit(1)
    return _verdict


def vm_score_percent():
    _findings = {{
        "cpuid_hypervisor": _nx_has_cpu_hypervisor(),
        "dmi_strings": _nx_has_dmi_strings(),
        "mac_prefix": _nx_has_vm_mac(),
        "sysinfo": _nx_has_sysvirt(),
    }}
    _hit = sum(_NX_VM_WEIGHTS[_k] for _k, _v in _findings.items() if _v)
    _total = sum(_NX_VM_WEIGHTS.values())
    return (_hit / _total * 100.0) if _total else 0.0
'''
    compile(src, "<nx_vm_loader>", "exec")
    return src
