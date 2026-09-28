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

# Canonical armed tokens (lowercase-compared): matches the native gate
# (IsDriverGateArmed lowercases before comparing against {1,true,yes}).
# The mixed-case tuple below is kept for back-compat display; the actual
# comparison is case-insensitive, so "tRuE"/"yEs" arm on both sides.
_ARMED_TRUE = ("1", "true", "True", "TRUE", "yes", "Yes", "YES")
_ARMED_TRUE_LOWER = ("1", "true", "yes")

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
    """Return True when the gate is armed via env (``NIXON_DRIVER_CHECK``).

    Case-insensitive (mirrors the native gate's lowercase compare):
    "1"/"true"/"yes" in any case arm. Broadening (vs. the old exact
    tuple) is the fail-closed direction — more spellings kill on hit.
    """
    try:
        if env is None:
            env = os.environ
        val = env.get(ARM_VAR, "")
    except Exception:
        return False
    try:
        return str(val).strip().lower() in _ARMED_TRUE_LOWER
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


# ---------------------------------------------------------------------------
# Hardened detection: evidence records, path signal, version fingerprints.
#
# ADDITIVE ONLY. check_names() (bare sorted stems), enum_loaded_drivers(),
# check_current(), and emit_driver_snippet() semantics are UNCHANGED: the
# emitted loader snippet still compares bare stems and still kills at any
# stem hit when armed. Everything below only ADDS explainability on top.
#
# Still hard-boundary clean: pure enumeration + blocklist comparison. No
# driver loading, no ring-0, no IOCTLs, no service installation, no writes.
# Read-only sources only: EnumDeviceDrivers / GetDeviceDriverFileNameW /
# file version-resource reads (all fail-soft, never raise).
# ---------------------------------------------------------------------------

#: Confidence tiers. Gate kills at >= KILL_THRESHOLD, which equals the
#: stem-only tier, so current stem behavior is preserved EXACTLY (a stem
#: hit always kills when armed, with or without extra signals).
CONF_STEM_ONLY = 0.6
CONF_SUSPICIOUS_PATH = 0.8
CONF_VULN_VERSION = 0.95
CONF_BAD_SIGNATURE = 0.9
KILL_THRESHOLD = 0.6

#: Allowlisted driver-image directories (normalized: forward slashes,
#: lowercase). A blocked stem found OUTSIDE these dirs raises confidence
#: to CONF_SUSPICIOUS_PATH (BYOVD droppers stage .sys files in temp /
#: user-writable dirs). Kept deliberately small: only OS-owned driver
#: dirs; vendor install dirs are NOT allowlisted (fail-closed direction).
KNOWN_DRIVER_DIRS = (
    "c:/windows/system32/drivers",
    "c:/windows/system32",
    "c:/windows/sysnative/drivers",
    "c:/windows/sysnative",
    "/systemroot/system32/drivers",
    "/systemroot/system32",
)

#: Explainability strings attached to every evidence record.
LIMITATION_HIDDEN = ("user-space enumeration cannot detect unloaded-on-boot "
                     "drivers hidden by rootkits")
LIMITATION_LINUX_PATHS = ("Linux /proc/modules exposes module names only, "
                          "no image paths: location signal unavailable")
LIMITATION_RENAME = ("stem matching catches renames that keep the basename "
                     "stem (e.g. .\\evil\\RTCore64.sys); a copy renamed to a "
                     "different stem is invisible to this check")
LIMITATION_SIGNATURE = ("live signature validation unavailable: mapping a "
                        "WinVerifyTrust failure to 'invalid' would be "
                        "dishonest (TRUST_E_NOSIGNATURE is common for legit "
                        "unsigned drivers), so no cert-chain validator is "
                        "built; caller-supplied overrides only")
LIMITATION_VERSIONS = ("version fingerprints are hand-curated "
                       "(obfuscator/driver_versions.json) and may be stale; "
                       "stem match alone still reports at 0.6")

_VERSION_FP_FILENAME = "driver_versions.json"
_version_fp_cache = None


def _load_version_fingerprints():
    # type: () -> dict
    """Load driver_versions.json once (cached). Never raises; {} on error."""
    global _version_fp_cache
    try:
        if isinstance(_version_fp_cache, dict):
            return _version_fp_cache
    except Exception:
        pass
    fp = {}
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, _VERSION_FP_FILENAME),
                  "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for stem, entry in data.items():
                try:
                    s = _stem(stem)
                    if s and s in BLOCKED_DRIVERS and isinstance(entry, dict):
                        fp[s] = entry
                except Exception:
                    continue
        _version_fp_cache = fp
        return fp
    except Exception:
        try:
            _version_fp_cache = {}
        except Exception:
            pass
        return {}


def version_fingerprints_mtime():
    # type: () -> object
    """mtime (epoch float) of driver_versions.json, or None when unreadable."""
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.getmtime(os.path.join(here, _VERSION_FP_FILENAME))
    except Exception:
        return None


def version_fingerprints_stale(max_age_s=90 * 86400):
    # type: (object) -> bool
    """True when fingerprints are older than ``max_age_s`` (or unreadable).

    Evaluable staleness flag for the hand-curated version fingerprints:
    callers can warn (never gate) on True. Unreadable/missing counts as
    stale (fail-closed direction: flag it, don't silently trust).
    """
    try:
        mtime = version_fingerprints_mtime()
        if mtime is None:
            return True
        import time as _t
        return (_t.time() - float(mtime)) > float(max_age_s)
    except Exception:
        return True


def _parse_version(text):
    # type: (object) -> object
    """Parse 'a.b.c.d' into a 4-tuple of ints. None when unparseable."""
    try:
        parts = str(text).strip().split(".")
        nums = []
        for part in parts[:4]:
            digit_run = ""
            for ch in str(part).strip():
                if ch.isdigit():
                    digit_run += ch
                else:
                    break
            if not digit_run:
                return None
            nums.append(int(digit_run))
        if not nums:
            return None
        while len(nums) < 4:
            nums.append(0)
        return tuple(nums)
    except Exception:
        return None


def _version_less(a, b):
    # type: (object, object) -> object
    """True if version a < b, False if a >= b, None if either unparseable."""
    try:
        pa = _parse_version(a)
        pb = _parse_version(b)
        if pa is None or pb is None:
            return None
        return pa < pb
    except Exception:
        return None


def _is_vulnerable_version(stem, version, fp=None):
    # type: (object, object, object) -> object
    """True/False/None: vulnerable / fixed / unknown for (stem, version).

    True on exact affected-version match or version < affected_below.
    False only when a boundary comparison proves version >= affected_below.
    None (unknown) when no fingerprint, no version, or inconclusive data:
    callers must fall back to stem-only confidence, never fail-open.
    """
    try:
        s = _stem(stem)
        v = str(version).strip() if version else ""
        if not s or not v:
            return None
        if fp is None:
            fp = _load_version_fingerprints()
        entry = fp.get(s)
        if not isinstance(entry, dict):
            return None
        try:
            affected = entry.get("affected") or []
        except Exception:
            affected = []
        try:
            for known in list(affected):
                try:
                    if _parse_version(known) == _parse_version(v):
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        try:
            below = entry.get("affected_below")
        except Exception:
            below = None
        if below:
            cmp_result = _version_less(v, below)
            if cmp_result is True:
                return True
            if cmp_result is False:
                return False
        return None
    except Exception:
        return None


def _path_suspicious(path):
    # type: (object) -> object
    """True if path is outside KNOWN_DRIVER_DIRS, False if inside, None if no path."""
    try:
        p = str(path or "").replace("\\", "/").strip().lower()
        if not p:
            return None
        for known in KNOWN_DRIVER_DIRS:
            if p.startswith(known):
                return False
        return True
    except Exception:
        return None


def _enum_windows_paths():
    # type: () -> list
    """Windows-only: [(basename, fullpath)] via EnumDeviceDrivers + GetDeviceDriverFileNameW.

    Best-effort, read-only, never raises (returns [] on any failure).
    """
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
            _fname = _psapi.GetDeviceDriverFileNameW
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
                _buf = _ct.create_unicode_buffer(512)
                _r = _fname(_arr[_i], _buf, 512)
                if _r:
                    _full = _buf.value or ""
                    _base = _full.replace("\\", "/")
                    if "/" in _base:
                        _base = _base.rsplit("/", 1)[-1]
                    out.append((_base, _full))
            except Exception:
                continue
        return out
    except Exception:
        return []


def enum_loaded_drivers_with_paths(modules_path="/proc/modules"):
    # type: (object) -> list
    """Enumerate [(name, path-or-None)] pairs (read-only, never raises).

    Windows: EnumDeviceDrivers + GetDeviceDriverFileNameW (paths present).
    Linux: /proc/modules first column (paths ALWAYS None: the file has no
    path column -- see LIMITATION_LINUX_PATHS). Other platforms: [].
    """
    try:
        system = ""
        try:
            system = str(platform.system() or "").lower()
        except Exception:
            system = ""
        if system == "windows":
            return _enum_windows_paths()
        if system == "linux":
            try:
                return [(n, None) for n in _enum_linux_modules(modules_path)]
            except Exception:
                return []
        return []
    except Exception:
        return []


def get_file_version(path):
    # type: (object) -> object
    """Read a file's version resource (read-only). Version str or None.

    Windows-only via version.dll (GetFileVersionInfo*); None on any
    failure or non-Windows. Never raises. No driver loading: this reads
    a PE file's VERSIONINFO resource like any file-property query.
    """
    try:
        if not path:
            return None
        try:
            if str(platform.system() or "").lower() != "windows":
                return None
        except Exception:
            return None
        import ctypes as _ct
        try:
            _ver = _ct.WinDLL("version.dll")
        except Exception:
            return None
        _p = str(path)
        try:
            _size = _ver.GetFileVersionInfoSizeW(_p, None)
        except Exception:
            return None
        if not _size:
            return None
        try:
            _buf = _ct.create_string_buffer(int(_size))
            if not _ver.GetFileVersionInfoW(_p, 0, int(_size), _buf):
                return None
            _ptr = _ct.c_void_p(0)
            _len = _ct.c_uint(0)
            if not _ver.VerQueryValueW(_buf, "\\", _ct.byref(_ptr),
                                       _ct.byref(_len)):
                return None
            _ffi = _ct.cast(_ptr, _ct.POINTER(_ct.c_ulong * 4)).contents
            _ms, _ls = int(_ffi[0]), int(_ffi[1])
            return "%d.%d.%d.%d" % (_ms >> 16, _ms & 0xFFFF,
                                    _ls >> 16, _ls & 0xFFFF)
        except Exception:
            return None
    except Exception:
        return None


def signature_status(path):
    # type: (object) -> object
    """Live signature verdict for ``path``. ALWAYS None (unknown).

    Deliberately unimplemented: a correct cert-chain validator does not
    fit the trivial-ctypes budget, and mapping any WinVerifyTrust
    nonzero return to 'invalid' would inflate confidence dishonestly
    (unsigned-but-legit drivers fail verification routinely). Callers
    with their own validator may pass verdicts via the ``signatures``
    override of check_names_evidence(). Never raises.
    """
    try:
        return None
    except Exception:
        return None


def check_names_evidence(names=None, paths=None, versions=None,
                         signatures=None):
    # type: (object, object, object, object) -> list
    """Return evidence records for blocked stems found in ``names``.

    Each record: {stem, raw, rule, rules, confidence, path, version,
    signature, limitation}. Never raises; bad input yields [].

    ``names`` items may be plain strings or (name, path) tuples.
    ``paths``: optional {stem-or-raw: path} override map. ``versions``:
    optional {stem-or-raw: version-string} override map (else a
    best-effort version-resource read runs for entries WITH a path).
    ``signatures``: optional {stem: True(valid)/False(invalid)} map from
    a caller-owned validator; live validation is unavailable (None).

    Confidence: stem-only 0.6; +suspicious-path 0.8; +vulnerable-version
    0.95; +caller-reported-invalid-signature 0.9. ``rule`` is the
    highest-signal rule fired; ``rules`` lists all fired rules.
    """
    try:
        fp = _load_version_fingerprints()
    except Exception:
        fp = {}
    try:
        path_map = dict(paths) if isinstance(paths, dict) else {}
    except Exception:
        path_map = {}
    try:
        ver_map = dict(versions) if isinstance(versions, dict) else {}
    except Exception:
        ver_map = {}
    try:
        sig_map = dict(signatures) if isinstance(signatures, dict) else {}
    except Exception:
        sig_map = {}
    try:
        items = [] if names is None else list(names)
    except Exception:
        return []
    out = []
    seen = set()
    for entry in items:
        try:
            raw_name = ""
            entry_path = None
            try:
                if isinstance(entry, (tuple, list)) and len(entry) == 2:
                    raw_name, entry_path = entry[0], entry[1]
                else:
                    raw_name = entry
            except Exception:
                raw_name = entry
            try:
                raw = str(raw_name) if raw_name is not None else ""
            except Exception:
                continue
            stem = _stem(raw)
            if not stem or stem not in BLOCKED_DRIVERS:
                continue
            if stem in seen:
                continue
            seen.add(stem)
            path_str = ""
            try:
                cand = entry_path
                if cand is None:
                    try:
                        cand = path_map.get(stem, path_map.get(raw))
                    except Exception:
                        cand = None
                if cand:
                    path_str = str(cand)
            except Exception:
                path_str = ""
            try:
                # A raw string that already carries a directory (e.g.
                # "C:\evil\RTCore64.sys") doubles as its own location
                # signal when no explicit path was supplied.
                if not path_str and ("\\" in raw or "/" in raw):
                    path_str = raw
            except Exception:
                pass
            rules = ["stem_match"]
            conf = CONF_STEM_ONLY
            susp = _path_suspicious(path_str)
            if susp is True:
                rules.append("location_suspicious")
                if CONF_SUSPICIOUS_PATH > conf:
                    conf = CONF_SUSPICIOUS_PATH
            ver_str = ""
            try:
                if stem in ver_map:
                    ver_str = str(ver_map.get(stem) or "").strip()
                elif raw in ver_map:
                    ver_str = str(ver_map.get(raw) or "").strip()
                elif path_str:
                    ver_str = str(get_file_version(path_str) or "").strip()
            except Exception:
                ver_str = ""
            vuln = _is_vulnerable_version(stem, ver_str, fp)
            if vuln is True:
                rules.append("vulnerable_version")
                if CONF_VULN_VERSION > conf:
                    conf = CONF_VULN_VERSION
            elif vuln is False:
                rules.append("fixed_version_stem_only")
            sig_text = "unknown (live validation unavailable)"
            try:
                sig = sig_map.get(stem)
            except Exception:
                sig = None
            if sig is False:
                rules.append("signature_invalid")
                if CONF_BAD_SIGNATURE > conf:
                    conf = CONF_BAD_SIGNATURE
                sig_text = "invalid (caller-supplied)"
            elif sig is True:
                sig_text = "valid (caller-supplied)"
            limitation = LIMITATION_HIDDEN
            if not path_str:
                limitation += "; " + LIMITATION_LINUX_PATHS
            out.append({
                "stem": stem,
                "raw": raw,
                "rule": rules[-1],
                "rules": list(rules),
                "confidence": float(conf),
                "path": path_str,
                "version": ver_str,
                "signature": sig_text,
                "limitation": limitation,
            })
        except Exception:
            continue
    try:
        out.sort(key=lambda r: r.get("stem", ""))
    except Exception:
        pass
    return out


def check_current_evidence(names=None, paths=None, versions=None):
    # type: (object, object, object) -> list
    """Enumerate (or use ``names``) and return evidence records.

    On Windows enumerates (name, path) pairs so the location signal is
    live; elsewhere paths come only from ``paths``. Pure query helper;
    never exits, never raises.
    """
    try:
        if names is None:
            try:
                system = str(platform.system() or "").lower()
            except Exception:
                system = ""
            if system == "windows":
                try:
                    return check_names_evidence(
                        enum_loaded_drivers_with_paths(),
                        paths=paths, versions=versions)
                except Exception:
                    return []
            names = enum_loaded_drivers()
        return check_names_evidence(names, paths=paths, versions=versions)
    except Exception:
        return []


def should_kill(evidence):
    # type: (object) -> bool
    """True when any evidence record meets KILL_THRESHOLD (>= 0.6).

    Mirrors the armed snippet's fail-closed rule (any stem hit kills);
    separated here so the confidence gate is testable. Never raises.
    """
    try:
        for rec in (evidence or []):
            try:
                if float(rec.get("confidence", 0.0)) >= KILL_THRESHOLD:
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False


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
        + "        _v = str(_os.environ.get(_NX_DRIVER_VAR, '')).strip().lower()\n"
        + "        return _v in ('1', 'true', 'yes')\n"
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
