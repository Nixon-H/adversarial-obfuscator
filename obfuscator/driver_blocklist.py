"""V10 Kernel Driver Detection: SAFE read-only defensive gate.

Scope (deliberately narrow, defensive-only):

- PURE ENUMERATION + blocklist comparison. No driver loading, no ring-0,
  no IOCTLs, no service/driver installation, no writes of any kind.
- Read-only sources only:
  - Linux: first column of ``/proc/modules`` (same file the vm_score
    snippet already reads for its ``drivers`` signal).
  - Windows: ``ctypes`` ``EnumDeviceDrivers`` + ``GetDeviceDriverBaseName``
    wrapped in ``try/except`` (returns ``[]`` on any failure).
  - Other platforms: ``[]`` (never raises).
- Comparison is case-insensitive STEM matching: strip a trailing ``.sys``,
  lowercase. Stems are matched against :data:`BLOCKED_DRIVERS`.

Blocklist content: known-vulnerable / known-malicious Windows driver
filenames from public BYOVD knowledge (LOLDrivers project). Only entries
the author is confident existed are listed (~20 stems). Each entry carries
a short vendor/purpose comment. Deliberately EXCLUDED: legit AV drivers,
VirtualBox guest drivers, and any driver that is not publicly documented
as vulnerable/malicious (false positives there would be a fail-closed
availability bug).

Arming (OFF BY DEFAULT, two independent paths, either arms):

- Build flag ``--driver-check`` (default off): bakes the gate snippet
  into the loader and sets the ``_NX_DRIVER_CHECK_ARMED`` marker True.
- Env ``NIXON_DRIVER_CHECK=1`` at runtime (read live by the snippet).

When disarmed the emitted ``driver_check()`` enumerates and returns hits
but NEVER exits. When armed, a non-empty hit list fails closed via
``_nx_kill("driver-blocked")`` (exit 137; same ladder as vm_score).

V10 asks for "at load time and continuously afterwards": the emitted
snippet runs ``driver_check()`` once at import AND starts a lightweight
daemon re-check thread (60 s interval, same fail-closed) when armed.
The thread is best-effort (any error kills only the thread, never the
app) and only starts when armed.

Python 3.10 compatible: no ``match``, no ``X | Y`` annotations.
"""

import json
import os
import platform


#: Runtime opt-in env var. Any of these values arms the gate.
ARM_VAR = "NIXON_DRIVER_CHECK"

_ARMED_TRUE = ("1", "true", "True", "TRUE", "yes", "Yes", "YES")

#: Background re-check interval (seconds) for the continuous mode.
RECHECK_INTERVAL_S = 60


# Blocked driver STEMS (lowercase, no ".sys" suffix). Matched via
# normalize(): lowercase + strip one trailing ".sys" + strip path parts.
# Only drivers publicly documented (LOLDrivers project / vendor advisories)
# as vulnerable-to-BYOVD or outright malicious. NEVER legit AV / hypervisor
# guest drivers.
BLOCKED_DRIVERS = frozenset([
    # -- MSI Afterburner / RivaTuner: RTCore64.sys ships with a signed,
    # -- vulnerable driver abused for arbitrary MSR/RAM/Ring-0 access.
    "rtcore64",
    "rtcore32",
    # -- CPU-Z / HW monitoring: WinRing0 driver exposes raw MSR/IO access.
    "winring0",
    "winring0x64",
    # -- Gigabyte firmware utilities: GDRV.sys arbitrary physical-memory RW.
    "gdrv",
    "gdrv2",
    # -- ASUS: AsIO.sys / AsUpIO.sys ship with signed vulns (physical mem).
    "asio",
    "asupio",
    # -- Dell DBUtilDrv2.sys (dbutil_2_3.sys variant): CVE-2021-21551.
    "dbutildrv2",
    "dbutil_2_3",
    # -- Lenovo / generic diagnostics abused in BYOVD chains.
    "bwcw10x64",
    # -- Process Hacker / System Informer kernel driver (kprocesshacker):
    # -- legitimate tool, but its signed driver is a classic BYOVD handle
    # -- to arbitrary kernel RW once loaded by an attacker.
    "kprocesshacker",
    "kprocesshacker2",
    # -- CDBurnerXP / NTI driver abused for kernel access.
    "ntidrv",
    # -- Virtual Disk / direct-SCSI helpers abused for raw disk access.
    "amsdk",
    # -- Micro-Star / Dragon Center driver with known vuln.
    "eneio64",
    "enetechio64",
    # -- Razer Synapse driver (rzpnk.sys) abused for local privesc.
    "rzpnk",
    # -- Paragon Partition Manager BioNTdrv.sys: 5 CVEs (CVE-2025-0286..).
    "biontdrv",
    # -- Huawei PCManager driver (dbcohc.sys family) with known vuln.
    "dbcohc",
    # -- LG / monitor-control driver abused in BYOVD samples.
    "lha",
    # -- Truesight / RogueKiller anti-rootkit driver abused for killAV.
    "truesight",
])


def _stem(text):
    # type: (object) -> str
    """Lowercase stem of a driver name: basename + strip one .sys."""
    try:
        s = str(text or "")
    except Exception:
        return ""
    try:
        s = s.replace("\\", "/")
        if "/" in s:
            s = s.rsplit("/", 1)[-1]
        s = s.strip().lower()
        if s.endswith(".sys"):
            s = s[:-4]
        return s.strip()
    except Exception:
        return ""


def normalize(name):
    # type: (object) -> str
    """Public normalizer: case-insensitive stem (strip .sys)."""
    return _stem(name)


def check_names(names):
    # type: (object) -> list
    """Return sorted list of blocked stems found in ``names``.

    Never raises; non-iterable / bad input yields ``[]``.
    Matching is stem-based and case-insensitive.
    """
    try:
        hits = set()
        if names is None:
            return []
        try:
            iterator = list(names)
        except Exception:
            return []
        for entry in iterator:
            stem = _stem(entry)
            if stem and stem in BLOCKED_DRIVERS:
                hits.add(stem)
        return sorted(hits)
    except Exception:
        return []


def enum_loaded_drivers(modules_path="/proc/modules"):
    # type: (object) -> list
    """Enumerate loaded driver/module names (read-only, never raises).

    - Linux: parse first column of ``/proc/modules``.
    - Windows: ``ctypes`` ``EnumDeviceDrivers`` + ``GetDeviceDriverBaseName``
      wrapped in ``try/except`` (``[]`` on any failure).
    - Other platforms: ``[]``.
    """
    try:
        system = ""
        try:
            system = str(platform.system() or "").lower()
        except Exception:
            system = ""
        if system == "windows":
            return _enum_windows_drivers()
        if system == "linux":
            return _enum_linux_modules(modules_path)
        return []
    except Exception:
        return []


def _enum_linux_modules(modules_path="/proc/modules"):
    # type: (object) -> list
    try:
        names = []
        with open(str(modules_path), "r", errors="ignore") as f:
            for line in f:
                try:
                    parts = line.split()
                    if parts:
                        names.append(parts[0])
                except Exception:
                    continue
        return names
    except Exception:
        return []


def _enum_windows_drivers():
    # type: () -> list
    """Windows-only: EnumDeviceDrivers via ctypes. Never raises."""
    try:
        import ctypes as _ct
    except Exception:
        return []
    try:
        try:
            _psapi = _ct.WinDLL("psapi.dll")
        except Exception:
            return []
        try:
            _enum = _psapi.EnumDeviceDrivers
            _basename = _psapi.GetDeviceDriverBaseNameW
        except Exception:
            return []
        _count = 1024
        _arr_type = _ct.c_void_p * _count
        _arr = _arr_type()
        _needed = _ct.c_ulong(0)
        try:
            _ok = _enum(_arr, _ct.sizeof(_arr), _ct.byref(_needed))
        except Exception:
            return []
        if not _ok:
            return []
        out = []
        try:
            _n = _needed.value // _ct.sizeof(_ct.c_void_p)
        except Exception:
            _n = 0
        for _i in range(min(_n, _count)):
            try:
                _buf = _ct.create_unicode_buffer(260)
                _r = _basename(_arr[_i], _buf, 260)
                if _r:
                    out.append(_buf.value)
            except Exception:
                continue
        return out
    except Exception:
        return []


def is_armed(env=None):
    # type: (object) -> bool
    """Return True when the gate is armed via env (``NIXON_DRIVER_CHECK``)."""
    try:
        if env is None:
            env = os.environ
        val = env.get(ARM_VAR, "")
    except Exception:
        return False
    try:
        return str(val) in _ARMED_TRUE
    except Exception:
        return False


def check_current(env=None, names=None):
    # type: (object, object) -> list
    """Enumerate (or use ``names``) and return blocked-stem hits.

    Pure query helper used by tests; never exits, never raises.
    """
    try:
        if names is None:
            names = enum_loaded_drivers()
        return check_names(names)
    except Exception:
        return []


def emit_driver_snippet(armed=False, interval_s=60):
    # type: (object, object) -> str
    """Return the runtime gate snippet source. Must compile on 3.10+.

    The snippet defines ``driver_check()`` (returns hit list; exits only
    when armed) and runs it once at import. When armed (build flag OR
    ``NIXON_DRIVER_CHECK`` env at runtime) it also starts a daemon
    re-check thread every ``interval_s`` seconds.

    Arming rule (either arms)::

        armed = _NX_DRIVER_ARMED_BUILD or
                os.environ.get("NIXON_DRIVER_CHECK", "") in (...truthy...)

    Disarmed behavior: enumerate + return hits, never exit, no thread.
    """
    try:
        _armed = bool(armed)
    except Exception:
        _armed = False
    try:
        _interval = int(interval_s)
    except Exception:
        _interval = 60
    if _interval <= 0:
        _interval = 60
    blocked_json = json.dumps(sorted(BLOCKED_DRIVERS), sort_keys=True)
    from obfuscator.kill_ladder import emit_kill_snippet as _kl_emit
    _kl_src = _kl_emit()
    src = (
        "import os as _os\n"
        + "import platform as _platform\n"
        + "\n"
        + _kl_src +
        "\n"
        + "_NX_DRIVER_ARMED_BUILD = %r\n" % (_armed,)
        + "_NX_DRIVER_BLOCKED = %s\n" % (blocked_json,)
        + "_NX_DRIVER_ARMED_VALUES = %r\n" % (tuple(_ARMED_TRUE),)
        + "_NX_DRIVER_INTERVAL = %r\n" % (_interval,)
        + "_NX_DRIVER_VAR = %r\n" % (ARM_VAR,)
        + "\n"
        + "\n"
        + "def _nx_driver_stem(_name):\n"
        + "    try:\n"
        + "        _s = str(_name if _name is not None else '')\n"
        + "    except Exception:\n"
        + "        return ''\n"
        + "    try:\n"
        + "        _s = _s.replace(chr(92), '/')\n"
        + "        if '/' in _s:\n"
        + "            _s = _s.rsplit('/', 1)[-1]\n"
        + "        _s = _s.strip().lower()\n"
        + "        if _s.endswith('.sys'):\n"
        + "            _s = _s[:-4]\n"
        + "        return _s.strip()\n"
        + "    except Exception:\n"
        + "        return ''\n"
        + "\n"
        + "\n"
        + "def _nx_driver_armed():\n"
        + "    try:\n"
        + "        if bool(_NX_DRIVER_ARMED_BUILD):\n"
        + "            return True\n"
        + "    except Exception:\n"
        + "        pass\n"
        + "    try:\n"
        + "        return str(_os.environ.get(_NX_DRIVER_VAR, '')) in _NX_DRIVER_ARMED_VALUES\n"
        + "    except Exception:\n"
        + "        return False\n"
        + "\n"
        + "\n"
        + "def _nx_enum_drivers():\n"
        + "    try:\n"
        + "        _sys = ''\n"
        + "        try:\n"
        + "            _sys = str(_platform.system() or '').lower()\n"
        + "        except Exception:\n"
        + "            _sys = ''\n"
        + "        if _sys == 'linux':\n"
        + "            _names = []\n"
        + "            try:\n"
        + "                with open('/proc/modules', 'r', errors='ignore') as _f:\n"
        + "                    for _line in _f:\n"
        + "                        try:\n"
        + "                            _parts = _line.split()\n"
        + "                            if _parts:\n"
        + "                                _names.append(_parts[0])\n"
        + "                        except Exception:\n"
        + "                            continue\n"
        + "            except Exception:\n"
        + "                _names = []\n"
        + "            return _names\n"
        + "        if _sys == 'windows':\n"
        + "            try:\n"
        + "                import ctypes as _ct\n"
        + "                _psapi = _ct.WinDLL('psapi.dll')\n"
        + "                _enum = _psapi.EnumDeviceDrivers\n"
        + "                _base = _psapi.GetDeviceDriverBaseNameW\n"
        + "                _cnt = 1024\n"
        + "                _arr = (_ct.c_void_p * _cnt)()\n"
        + "                _need = _ct.c_ulong(0)\n"
        + "                if not _enum(_arr, _ct.sizeof(_arr), _ct.byref(_need)):\n"
        + "                    return []\n"
        + "                try:\n"
        + "                    _n = _need.value // _ct.sizeof(_ct.c_void_p)\n"
        + "                except Exception:\n"
        + "                    _n = 0\n"
        + "                _out = []\n"
        + "                for _i in range(min(_n, _cnt)):\n"
        + "                    try:\n"
        + "                        _buf = _ct.create_unicode_buffer(260)\n"
        + "                        if _base(_arr[_i], _buf, 260):\n"
        + "                            _out.append(_buf.value)\n"
        + "                    except Exception:\n"
        + "                        continue\n"
        + "                return _out\n"
        + "            except Exception:\n"
        + "                return []\n"
        + "        return []\n"
        + "    except Exception:\n"
        + "        return []\n"
        + "\n"
        + "\n"
        + "def _nx_driver_hits(_names=None):\n"
        + "    try:\n"
        + "        if _names is None:\n"
        + "            _names = _nx_enum_drivers()\n"
        + "    except Exception:\n"
        + "        _names = []\n"
        + "    _hits = []\n"
        + "    try:\n"
        + "        for _entry in list(_names or []):\n"
        + "            _stem = _nx_driver_stem(_entry)\n"
        + "            if _stem and _stem in _NX_DRIVER_BLOCKED and _stem not in _hits:\n"
        + "                _hits.append(_stem)\n"
        + "    except Exception:\n"
        + "        pass\n"
        + "    return sorted(_hits)\n"
        + "\n"
        + "\n"
        + "def driver_check(_names=None):\n"
        + "    \"\"\"Enumerate drivers, return blocked-stem hits; exit iff armed.\"\"\"\n"
        + "    _hits = _nx_driver_hits(_names)\n"
        + "    if _hits and _nx_driver_armed():\n"
        + "        _nx_kill(\"driver-blocked\")\n"
        + "    return _hits\n"
        + "\n"
        + "\n"
        + "def _nx_driver_watch():\n"
        + "    try:\n"
        + "        import time as _nx_driver_time\n"
        + "        while True:\n"
        + "            try:\n"
        + "                _nx_driver_time.sleep(float(_NX_DRIVER_INTERVAL))\n"
        + "            except Exception:\n"
        + "                return\n"
        + "            try:\n"
        + "                driver_check()\n"
        + "            except SystemExit:\n"
        + "                return\n"
        + "            except Exception:\n"
        + "                continue\n"
        + "    except Exception:\n"
        + "        return\n"
        + "\n"
        + "\n"
        + "try:\n"
        + "    driver_check()\n"
        + "except SystemExit:\n"
        + "    raise\n"
        + "except Exception:\n"
        + "    pass\n"
        + "try:\n"
        + "    if _nx_driver_armed():\n"
        + "        import threading as _nx_driver_thr\n"
        + "        _t = _nx_driver_thr.Thread(target=_nx_driver_watch, daemon=True)\n"
        + "        _t.start()\n"
        + "except Exception:\n"
        + "    pass\n"
    )
    compile(src, "<nx_driver_gate>", "exec")
    return src
