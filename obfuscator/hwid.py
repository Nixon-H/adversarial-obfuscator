"""Hardware identity that never shells out and never goes random.

Why this exists
---------------
``uuid.getnode()`` looks harmless, but CPython falls back to *running
commands* when it cannot read the MAC from netlink/sysfs: ``ip link``,
``ifconfig``, ``arp`` (``uuid._ip_getnode`` / ``_ifconfig_getnode`` /
``_arp_getnode``), each through ``subprocess``.  Two things go wrong with
that inside the loader:

* the loader starts dozens of noise threads, and on the Python 3.13/3.14
  CI runners the spawn from that state blocked for ~500 s -- the build's
  own verification run then timed out, which is what made the whole
  3.13/3.14 job look "slow";
* when every method fails, ``uuid.getnode()`` returns a *random* 48-bit
  value with the multicast bit set, and it re-draws on every process.  A
  fingerprint built from it can never match between two runs, so the
  trial gate (``trial_bind.fallback_fingerprint``) fails closed with
  "tampered" on such hosts.

``/sys/class/net/<iface>/address`` is a plain file on Linux; reading it
is a syscall, has no subprocess, and is stable.  When it is unavailable
the answer is "" -- callers decide what that means, and nothing is
invented.
"""

from __future__ import annotations

import os

_SYSFS_NET = "/sys/class/net"


def machine_mac() -> str:
    """First usable non-loopback MAC as 12 lowercase hex chars, or "".

    A multicast/random bit cannot appear here: sysfs only reports real
    interface addresses.  ``00:00:00:00:00:00`` is skipped because it is
    the "no address" placeholder some virtual interfaces report.
    """
    try:
        names = sorted(os.listdir(_SYSFS_NET))
    except OSError:
        return ""
    for name in names:
        if name == "lo":
            continue
        try:
            with open(os.path.join(_SYSFS_NET, name, "address"),
                      encoding="utf-8") as fh:
                mac = fh.read().strip().lower().replace(":", "")
        except OSError:
            continue
        if len(mac) == 12 and mac != "0" * 12:
            return mac
    return ""


def machine_fingerprint_part() -> str:
    """``machine_mac()`` or "0" -- the value to fold into a fingerprint."""
    return machine_mac() or "0"


#: Emitted into generated loaders: the same logic without imports of this
#: package (the artifact is standalone).  Kept in one place so the loader
#: and the build can never drift.
LOADER_SNIPPET = '''def _nx_mac():
    try:
        import os as _o
        for _n in sorted(_o.listdir("/sys/class/net")):
            if _n == "lo": continue
            try:
                with open("/sys/class/net/" + _n + "/address") as _f:
                    _m = _f.read().strip().lower().replace(":", "")
            except Exception: continue
            if len(_m) == 12 and _m != "0" * 12: return _m
    except Exception: pass
    return "0"
'''
