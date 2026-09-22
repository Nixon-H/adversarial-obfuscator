"""Trial deadline MAC-binding + clock-rollback detection (AUDIT GAPS #52/#75).

Build-time: compute an absolute deadline (epoch seconds) from a trial spec
(parse via :func:`obfuscator.macros.parse_trial`, i.e. ``--trial '7d'``)
plus a sealed token::

    trial_token = HMAC-SHA256(build_key, hwid_fp || b"|" || deadline_iso)

``hwid_fp`` is the machine fingerprint the trial is bound to:

- when ``--hwid`` is given (or ``--hwid-lock``), the fingerprint is that
  HWID string — moving the build to another machine breaks the trial
  rather than extending it;
- otherwise a machine-stable composite fallback is collected both at
  build time and at runtime: ``platform.node()``, ``uuid.getnode()`` MAC,
  Linux ``machine-id``, and ``platform.system()/machine()``
  (see :func:`fallback_fingerprint`).  Documented caveat: without ``--hwid``
  the binding is OS-surface-derived (a reimaged box reads as a new machine;
  a determined attacker can spoof components) — pass ``--hwid`` for a
  strong binding.

Runtime (emitted snippet, see :func:`emit_trial_snippet`): re-derive the
fingerprint, recompute the HMAC with constant-time compare, and refuse to
run on mismatch.  Additionally:

- absolute deadline: ``now > deadline`` -> expired;
- rollback detection: on first successful run persist a sealed last-seen
  timestamp (same HMAC scheme) in a dotfile next to the artifact
  (platform-appropriate: ``XDG_STATE_HOME``/``~/.local/state`` on Linux,
  ``LOCALAPPDATA`` on Windows, ``~/Library/Application Support`` on
  macOS); on each run, if ``now < last_seen - tolerance`` (default 300s
  skew allowance) -> clock rollback detected -> refuse.  ``last_seen`` is
  updated on each successful run.

Pure-python, stdlib only, dependency-free so the snippet is emittable
into stubs/loaders the same way ``obfuscator/macros.py`` emits runtime
helpers and ``obfuscator/vm_score.py`` emits the loader snippet.

Tamper model: deadline, token, and the sealed last-seen stamp are all
authenticated by HMAC under the per-build ``build_key`` (a fresh 32-byte
secret minted at build time, embedded only as an opaque literal in the
artifact).  Editing the deadline without the key invalidates the token;
copying the artifact to another machine changes the fingerprint, which
invalidates the token.  The sealed last-seen stamp prevents naive
``date -s`` rollback games; a fresh dotfile simply restarts last_seen at
``now`` (documented limitation: deleting the state file resets the
rollback window, but the absolute deadline still holds).
"""

import hashlib
import hmac as _hmac
import os
import platform
import time
import uuid

#: Allowed clock skew before a backwards jump counts as a rollback.
ROLLBACK_TOLERANCE_S = 300.0

#: HMAC domain separators (keep trial and last-seen stamps distinct).
_TRIAL_DOMAIN = b"nx-trial-v1"
_LASTSEEN_DOMAIN = b"nx-trial-lastseen-v1"


def _read_first(path):
    # type: (str) -> str
    try:
        with open(path, "r", errors="ignore") as _f:
            return _f.read().strip()
    except Exception:
        return ""


def fallback_fingerprint():
    # type: () -> str
    """Machine-stable fingerprint (no --hwid configured).

    Composite of ``platform.node()``, ``uuid.getnode()`` MAC,
    Linux ``/etc/machine-id`` (or ``/var/lib/dbus/machine-id`` fallback),
    and ``platform.machine()`` + ``platform.system()``.  Every component
    is collected at BOTH build time and runtime with per-component
    try/except, so missing files never break the check — the fingerprint
    simply has fewer components on restricted hosts.

    Rationale: hostname+MAC alone is trivially spoofed (one ioctl /
    one config edit each).  ``machine-id`` is a 128-bit random value
    minted at install time — stable across reboots, but changed on
    reinstall/reimage (acceptable: a reimaged box is a new machine for
    licensing purposes).  An attacker must spoof ALL components at once
    to transplant a trial, vs one before.  Pass ``--hwid`` for a strong
    binding (PBKDF2-derived key material, not just a comparison string).
    """
    try:
        node = str(platform.node() or "")
    except Exception:
        node = ""
    try:
        mac = format(int(uuid.getnode()), "x")
    except Exception:
        mac = "0"
    mid = _read_first("/etc/machine-id") or \
        _read_first("/var/lib/dbus/machine-id")
    try:
        plat = "%s|%s" % (platform.system(), platform.machine())
    except Exception:
        plat = ""
    return "%s|%s|%s|%s" % (node, mac, mid, plat)


def resolve_fingerprint(hwid=""):
    # type: (str) -> str
    """Return the fingerprint to bind the trial to.

    Explicit ``--hwid`` wins; otherwise the best-effort fallback.
    """
    hwid = str(hwid or "")
    if hwid:
        return hwid
    return fallback_fingerprint()


def compute_deadline(trial_seconds, now=None):
    # type: (float, float) -> int
    """Absolute deadline epoch (int seconds) = now + trial_seconds."""
    if trial_seconds is None:
        raise ValueError("trial_seconds is required")
    secs = float(trial_seconds)
    if not secs > 0:
        raise ValueError("trial_seconds must be > 0")
    base = float(now) if now is not None else time.time()
    return int(base + secs)


def mint_token(build_key, fingerprint, deadline_epoch):
    # type: (bytes, str, int) -> str
    """HMAC-SHA256 hex token binding deadline to fingerprint.

    Message: ``domain || fingerprint || b"|" || str(deadline)``.
    """
    if not isinstance(build_key, (bytes, bytearray)) or not len(build_key):
        raise ValueError("build_key must be non-empty bytes")
    msg = (_TRIAL_DOMAIN + b"|" + str(fingerprint).encode("utf-8")
           + b"|" + str(int(deadline_epoch)).encode("ascii"))
    return _hmac.new(bytes(build_key), msg, hashlib.sha256).hexdigest()


def verify_token(build_key, fingerprint, deadline_epoch, token):
    # type: (bytes, str, int, str) -> bool
    """Constant-time token check.  Never raises on bad input."""
    try:
        expected = mint_token(build_key, fingerprint, deadline_epoch)
        return _hmac.compare_digest(str(expected), str(token or ""))
    except Exception:
        return False


def seal_last_seen(build_key, last_seen_epoch):
    # type: (bytes, float) -> str
    """Seal a last-seen timestamp: ``"<epoch>:<hex>"``."""
    if not isinstance(build_key, (bytes, bytearray)) or not len(build_key):
        raise ValueError("build_key must be non-empty bytes")
    epoch = float(last_seen_epoch)
    body = repr(epoch)
    mac = _hmac.new(bytes(build_key),
                    _LASTSEEN_DOMAIN + b"|" + body.encode("utf-8"),
                    hashlib.sha256).hexdigest()
    return "%s:%s" % (body, mac)


def unseal_last_seen(build_key, sealed):
    # type: (bytes, str) -> float
    """Inverse of :func:`seal_last_seen`.  Raises ValueError on tamper."""
    try:
        body, mac = str(sealed).rsplit(":", 1)
        epoch = float(body)
    except Exception as e:
        raise ValueError("bad sealed last_seen: %s" % (e,))
    try:
        expected = _hmac.new(bytes(build_key),
                             _LASTSEEN_DOMAIN + b"|" + body.encode("utf-8"),
                             hashlib.sha256).hexdigest()
    except Exception as e:
        raise ValueError("bad sealed last_seen: %s" % (e,))
    if not _hmac.compare_digest(expected, str(mac)):
        raise ValueError("bad last_seen seal")
    return epoch


def check_trial(build_key, fingerprint, deadline_epoch, token, now=None):
    # type: (bytes, str, int, str, float) -> str
    """Pure expiry+binding verdict: ``"ok"`` / ``"expired"`` / ``"tampered"``.

    Order: binding first (tampered deadline/fingerprint or wrong host),
    then the absolute deadline.
    """
    moment = float(now) if now is not None else time.time()
    try:
        deadline = int(deadline_epoch)
    except Exception:
        return "tampered"
    if not verify_token(build_key, fingerprint, deadline, token):
        return "tampered"
    if moment > float(deadline):
        return "expired"
    return "ok"


def state_file_for(argv0=None, app_tag="nixon-trial"):
    # type: (str, str) -> str
    """Platform-appropriate sealed-state path for the rollback dotfile.

    - Linux: ``$XDG_STATE_HOME/<tag>/`` else ``~/.local/state/<tag>/``.
    - macOS: ``~/Library/Application Support/<tag>/``.
    - Windows: ``%LOCALAPPDATA%/<tag>/``.
    The leaf name derives from the artifact path (sha256 hex, 16 chars)
    so co-located artifacts do not share rollback state.
    """
    try:
        anchor = os.path.abspath(argv0) if argv0 else "default"
    except Exception:
        anchor = str(argv0 or "default")
    leaf = hashlib.sha256(anchor.encode("utf-8", errors="ignore")).hexdigest()[:16]
    fname = ".trial_%s.state" % (leaf,)
    tag = str(app_tag or "nixon-trial")
    try:
        system = platform.system().lower()
    except Exception:
        system = ""
    base = None
    try:
        if system == "windows":
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        elif system == "darwin":
            base = os.path.join(os.path.expanduser("~"), "Library",
                                "Application Support")
        else:
            base = (os.environ.get("XDG_STATE_HOME")
                    or os.path.join(os.path.expanduser("~"), ".local", "state"))
    except Exception:
        base = None
    if not base:
        try:
            base = os.path.join(os.path.expanduser("~"), ".local", "state")
        except Exception:
            base = os.path.expanduser("~") if "HOME" in os.environ else "."
    return os.path.join(str(base), tag, fname)


def check_and_update(build_key, fingerprint, deadline_epoch, token,
                     state_path=None, now=None,
                     tolerance_s=ROLLBACK_TOLERANCE_S):
    # type: (bytes, str, int, str, str, float, float) -> str
    """Full runtime gate: binding + deadline + rollback, then advance state.

    Returns ``"ok"`` / ``"expired"`` / ``"tampered"`` / ``"rollback"``.

    On ``"ok"`` the sealed last-seen stamp is written (best-effort; a
    write failure does not fail the run — rollback protection simply
    degrades for that run).  A missing/corrupt state file is treated as
    first run (sealed at ``now``); deleting the state file therefore
    resets the rollback window but never extends the absolute deadline.
    """
    moment = float(now) if now is not None else time.time()
    verdict = check_trial(build_key, fingerprint, deadline_epoch, token,
                          now=moment)
    if verdict != "ok":
        return verdict
    try:
        tol = float(tolerance_s)
    except Exception:
        tol = ROLLBACK_TOLERANCE_S
    path = state_path
    last_seen = None
    if path:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                sealed = fh.read().strip()
            if sealed:
                last_seen = unseal_last_seen(build_key, sealed)
        except FileNotFoundError:
            last_seen = None
        except (IOError, OSError):
            last_seen = None
        except ValueError:
            # Tampered state file: fail closed (attacker edited last_seen).
            return "tampered"
        except Exception:
            last_seen = None
    if last_seen is not None:
        try:
            if moment < float(last_seen) - tol:
                return "rollback"
        except Exception:
            pass
    if path:
        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(seal_last_seen(build_key, moment))
        except Exception:
            pass
    return "ok"


def build_trial_context(trial_seconds, hwid="", build_key=None, now=None,
                        app_tag="nixon-trial"):
    # type: (float, str, bytes, float, str) -> dict
    """Build-time helper: fingerprint + deadline + token (+ fresh key).

    Returns ``{"fingerprint": ..., "deadline": int, "token": hex,
    "build_key": bytes, "app_tag": ...}``.  When ``trial_seconds`` is
    None, returns ``{"disabled": True}`` (no trial requested — additive
    no-op for callers).
    """
    if trial_seconds is None:
        return {"disabled": True}
    import secrets as _secrets
    secs = float(trial_seconds)
    if not secs > 0:
        raise ValueError("trial_seconds must be > 0")
    key = bytes(build_key) if build_key is not None else _secrets.token_bytes(32)
    if not key:
        raise ValueError("build_key must be non-empty bytes")
    fp = resolve_fingerprint(hwid)
    deadline = compute_deadline(secs, now=now)
    token = mint_token(key, fp, deadline)
    return {"fingerprint": fp, "deadline": deadline, "token": token,
            "build_key": bytes(key), "app_tag": str(app_tag or "nixon-trial")}


def emit_trial_snippet(deadline_epoch, token_hex, build_key_hex,
                       app_tag="nixon-trial",
                       tolerance_s=ROLLBACK_TOLERANCE_S,
                       func_name="_nx_trial_gate"):
    # type: (int, str, str, str, float, str) -> str
    """Return the emittable runtime gate snippet.  Must compile().

    The snippet defines ``<func_name>(hwid_hint="")`` returning one of
    ``"ok"`` / ``"expired"`` / ``"tampered"`` / ``"rollback"``.  On
    ``"ok"`` it advances the sealed last-seen stamp.  Callers enforce::

        _verdict = _nx_trial_gate()
        if _verdict != "ok":
            sys.exit("trial " + _verdict)  # or silent sys.exit(1)

    ``hwid_hint``: when the build used ``--hwid``, pass that string so the
    runtime checks the explicit HWID; otherwise the snippet re-derives the
    composite fallback (node + MAC + machine-id + platform) itself.

    All literals are embedded via ``repr`` (hex/hmac digests contain only
    ``[0-9a-f]``; no quoting hazards).  Stdlib only.
    """
    deadline = int(deadline_epoch)
    token = str(token_hex or "")
    key_hex = str(build_key_hex or "")
    tag = str(app_tag or "nixon-trial")
    try:
        tol = float(tolerance_s)
    except Exception:
        tol = ROLLBACK_TOLERANCE_S
    # Validate literals early (fail at build time, not in the artifact).
    bytes.fromhex(key_hex)
    bytes.fromhex(token)
    if not token or len(token) != 64:
        raise ValueError("token_hex must be a 64-char sha256 hex digest")
    src = (
        "def %s(hwid_hint=\"\"):\n" % (func_name,)
        + "    import hashlib as _tb_hashlib\n"
        + "    import hmac as _tb_hmac\n"
        + "    import os as _tb_os\n"
        + "    import platform as _tb_platform\n"
        + "    import sys as _tb_sys\n"
        + "    import time as _tb_time\n"
        + "    import uuid as _tb_uuid\n"
        + "    _tb_deadline = %r\n" % (deadline,)
        + "    _tb_token = %r\n" % (token,)
        + "    _tb_key = bytes.fromhex(%r)\n" % (key_hex,)
        + "    _tb_tag = %r\n" % (tag,)
        + "    _tb_tol = %r\n" % (tol,)
        + "    try:\n"
        + "        _tb_fp = str(hwid_hint) if hwid_hint else None\n"
        + "    except Exception:\n"
        + "        _tb_fp = None\n"
        + "    if not _tb_fp:\n"
        + "        try:\n"
        + "            _tb_node = str(_tb_platform.node() or \"\")\n"
        + "        except Exception:\n"
        + "            _tb_node = \"\"\n"
        + "        try:\n"
        + "            _tb_mac = format(int(_tb_uuid.getnode()), \"x\")\n"
        + "        except Exception:\n"
        + "            _tb_mac = \"0\"\n"
        + "        try:\n"
        + "            with open(\"/etc/machine-id\", \"r\", errors=\"ignore\") as _tb_f:\n"
        + "                _tb_mid = _tb_f.read().strip()\n"
        + "        except Exception:\n"
        + "            _tb_mid = \"\"\n"
        + "        if not _tb_mid:\n"
        + "            try:\n"
        + "                with open(\"/var/lib/dbus/machine-id\", \"r\", errors=\"ignore\") as _tb_f:\n"
        + "                    _tb_mid = _tb_f.read().strip()\n"
        + "            except Exception:\n"
        + "                _tb_mid = \"\"\n"
        + "        try:\n"
        + "            _tb_plat = \"%s|%s\" % (_tb_platform.system(), _tb_platform.machine())\n"
        + "        except Exception:\n"
        + "            _tb_plat = \"\"\n"
        + "        _tb_fp = \"%s|%s|%s|%s\" % (_tb_node, _tb_mac, _tb_mid, _tb_plat)\n"
        + "    try:\n"
        + "        _tb_msg = b\"nx-trial-v1|\" + str(_tb_fp).encode(\"utf-8\") + b\"|\" + str(int(_tb_deadline)).encode(\"ascii\")\n"
        + "        _tb_exp = _tb_hmac.new(_tb_key, _tb_msg, _tb_hashlib.sha256).hexdigest()\n"
        + "    except Exception:\n"
        + "        return \"tampered\"\n"
        + "    try:\n"
        + "        _tb_match = _tb_hmac.compare_digest(str(_tb_exp), str(_tb_token))\n"
        + "    except Exception:\n"
        + "        _tb_match = (_tb_exp == _tb_token)\n"
        + "    if not _tb_match:\n"
        + "        return \"tampered\"\n"
        + "    try:\n"
        + "        _tb_now = float(_tb_time.time())\n"
        + "    except Exception:\n"
        + "        return \"tampered\"\n"
        + "    if _tb_now > float(_tb_deadline):\n"
        + "        return \"expired\"\n"
        + "    try:\n"
        + "        _tb_argv0 = _tb_sys.argv[0] if _tb_sys.argv else \"default\"\n"
        + "    except Exception:\n"
        + "        _tb_argv0 = \"default\"\n"
        + "    try:\n"
        + "        _tb_anchor = _tb_os.path.abspath(_tb_argv0)\n"
        + "    except Exception:\n"
        + "        _tb_anchor = str(_tb_argv0)\n"
        + "    _tb_leaf = _tb_hashlib.sha256(_tb_anchor.encode(\"utf-8\", errors=\"ignore\")).hexdigest()[:16]\n"
        + "    _tb_fname = \".trial_%s.state\" % (_tb_leaf,)\n"
        + "    try:\n"
        + "        _tb_sysname = _tb_platform.system().lower()\n"
        + "    except Exception:\n"
        + "        _tb_sysname = \"\"\n"
        + "    _tb_base = None\n"
        + "    try:\n"
        + "        if _tb_sysname == \"windows\":\n"
        + "            _tb_base = _tb_os.environ.get(\"LOCALAPPDATA\") or _tb_os.path.expanduser(\"~\")\n"
        + "        elif _tb_sysname == \"darwin\":\n"
        + "            _tb_base = _tb_os.path.join(_tb_os.path.expanduser(\"~\"), \"Library\", \"Application Support\")\n"
        + "        else:\n"
        + "            _tb_base = (_tb_os.environ.get(\"XDG_STATE_HOME\") or _tb_os.path.join(_tb_os.path.expanduser(\"~\"), \".local\", \"state\"))\n"
        + "    except Exception:\n"
        + "        _tb_base = None\n"
        + "    if not _tb_base:\n"
        + "        try:\n"
        + "            _tb_base = _tb_os.path.join(_tb_os.path.expanduser(\"~\"), \".local\", \"state\")\n"
        + "        except Exception:\n"
        + "            _tb_base = \".\"\n"
        + "    _tb_path = _tb_os.path.join(str(_tb_base), _tb_tag, _tb_fname)\n"
        + "    _tb_last = None\n"
        + "    try:\n"
        + "        with open(_tb_path, \"r\", encoding=\"utf-8\") as _tb_fh:\n"
        + "            _tb_sealed = _tb_fh.read().strip()\n"
        + "        if _tb_sealed:\n"
        + "            _tb_body, _tb_mac2 = _tb_sealed.rsplit(\":\", 1)\n"
        + "            _tb_want = _tb_hmac.new(_tb_key, b\"nx-trial-lastseen-v1|\" + _tb_body.encode(\"utf-8\"), _tb_hashlib.sha256).hexdigest()\n"
        + "            try:\n"
        + "                _tb_ok = _tb_hmac.compare_digest(_tb_want, str(_tb_mac2))\n"
        + "            except Exception:\n"
        + "                _tb_ok = (_tb_want == str(_tb_mac2))\n"
        + "            if not _tb_ok:\n"
        + "                return \"tampered\"\n"
        + "            _tb_last = float(_tb_body)\n"
        + "    except FileNotFoundError:\n"
        + "        _tb_last = None\n"
        + "    except (IOError, OSError):\n"
        + "        _tb_last = None\n"
        + "    except Exception:\n"
        + "        return \"tampered\"\n"
        + "    if _tb_last is not None:\n"
        + "        try:\n"
        + "            if _tb_now < float(_tb_last) - float(_tb_tol):\n"
        + "                return \"rollback\"\n"
        + "        except Exception:\n"
        + "            pass\n"
        + "    try:\n"
        + "        _tb_parent = _tb_os.path.dirname(_tb_path)\n"
        + "        if _tb_parent:\n"
        + "            _tb_os.makedirs(_tb_parent, exist_ok=True)\n"
        + "        _tb_body2 = repr(float(_tb_now))\n"
        + "        _tb_mac3 = _tb_hmac.new(_tb_key, b\"nx-trial-lastseen-v1|\" + _tb_body2.encode(\"utf-8\"), _tb_hashlib.sha256).hexdigest()\n"
        + "        with open(_tb_path, \"w\", encoding=\"utf-8\") as _tb_fh2:\n"
        + "            _tb_fh2.write(\"%s:%s\" % (_tb_body2, _tb_mac3))\n"
        + "    except Exception:\n"
        + "        pass\n"
        + "    return \"ok\"\n"
    )
    compile(src, "<nx_trial_gate>", "exec")
    return src
