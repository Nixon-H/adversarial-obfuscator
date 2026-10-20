"""secure_temp.py — secure temporary file helpers for build artifacts.

Provides O_EXCL|O_CREAT|O_RDWR 0o600 temp writes, stale-file purging,
multi-pass secure unlink, and a runtime loader snippet counterpart.
"""

from __future__ import annotations

import os
import secrets
import shutil
import tempfile
import time


def secure_write_temp(data: bytes, suffix: str, prefix: str = "_nx_") -> str:
    """Write *data* to a securely-created temp file and return its path.

    Uses ``os.open`` with ``O_EXCL | O_CREAT | O_RDWR | O_NOFOLLOW`` and mode
    ``0o600`` (plus an explicit ``fchmod`` to neutralise umask effects).
    ``O_NOFOLLOW`` is redundant on POSIX (``O_EXCL`` already refuses a
    symlink) but makes the property explicit and portable. Retries with a
    fresh random name on collision. Raises on failure.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be bytes")
    tmpdir = tempfile.gettempdir()
    # O_EXCL already refuses an existing path, including a symlink (POSIX:
    # "if pathname is a symbolic link, open() shall fail with EEXIST").
    # O_NOFOLLOW is added anyway so the property is EXPLICIT rather than
    # a side effect of the standard, and so it is enforced on platforms
    # whose O_EXCL semantics differ.
    flags = os.O_EXCL | os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    last_err: OSError | None = None
    for _ in range(100):
        name = f"{prefix}{secrets.token_hex(8)}{suffix}"
        path = os.path.join(tmpdir, name)
        try:
            fd = os.open(path, flags, 0o600)
        except FileExistsError as e:
            last_err = e
            continue
        except OSError as e:
            last_err = e
            continue
        try:
            try:
                os.fchmod(fd, 0o600)
            except (AttributeError, OSError):
                pass
            view = bytes(data)
            total = 0
            while total < len(view):
                n = os.write(fd, view[total:])
                if n <= 0:
                    raise OSError("short write to temp file")
                total += n
            os.fsync(fd)
        except BaseException:
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                os.unlink(path)
            except OSError:
                pass
            raise
        else:
            os.close(fd)
            # Belt-and-braces: ensure mode even on platforms where fchmod
            # is a no-op (chmod may fail on some Windows setups -> ignore).
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
            return path
    raise OSError(f"secure_write_temp: could not create unique file: {last_err}")


def purge_stale(prefix: str = "_nx_", max_age_s: int = 3600) -> int:
    """Remove stale temp files/dirs starting with *prefix*.

    Only entries whose name starts with *prefix* and whose mtime is older
    than *max_age_s* seconds are removed. Never raises; errors are ignored.
    Returns the count removed.
    """
    removed = 0
    try:
        tmpdir = tempfile.gettempdir()
    except Exception:
        return 0
    try:
        entries = os.listdir(tmpdir)
    except Exception:
        return 0
    now = time.time()
    for entry in entries:
        if not entry.startswith(prefix):
            continue
        path = os.path.join(tmpdir, entry)
        try:
            mtime = os.path.getmtime(path)
        except Exception:
            continue
        try:
            if (now - mtime) < max_age_s:
                continue
        except Exception:
            continue
        try:
            # Do not follow symlinks: unlink the link itself.
            if os.path.islink(path):
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
                # rmtree(ignore_errors=True) may silently fail; only count
                # if the path is actually gone.
                if os.path.exists(path):
                    continue
            else:
                os.unlink(path)
            removed += 1
        except Exception:
            continue
    return removed


def secure_unlink(path: str, passes: int = 3) -> bool:
    """Overwrite *path* with ``os.urandom`` *passes* times then unlink.

    Returns True on success, False on any error (including missing file).
    """
    try:
        if not isinstance(path, str) or not path:
            return False
        try:
            size = os.path.getsize(path)
        except OSError:
            return False
        # Refuse to operate on directories / non-regular files.
        try:
            if not os.path.isfile(path) or os.path.islink(path):
                # For symlinks: just unlink the link without overwriting
                # the target? Spec says overwrite file then unlink; safest
                # for a symlink is to unlink the link itself.
                if os.path.islink(path):
                    os.unlink(path)
                    return True
                return False
        except OSError:
            return False
        if size > 0:
            try:
                f = open(path, "r+b")
            except OSError:
                return False
            try:
                for _ in range(max(0, int(passes))):
                    f.seek(0)
                    remaining = size
                    # Write in bounded chunks to avoid huge allocations.
                    while remaining > 0:
                        chunk = os.urandom(min(remaining, 1024 * 1024))
                        f.write(chunk)
                        remaining -= len(chunk)
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except OSError:
                        pass
            finally:
                try:
                    f.close()
                except OSError:
                    pass
        os.unlink(path)
        return True
    except Exception:
        return False


def emit_loader_snippet() -> str:
    """Return a Python source string: the runtime loader counterpart.

    The snippet, when executed at runtime startup, will:
      * purge stale ``_nx_*`` temp files older than 3600s,
      * expose ``_nx_secure_write(data, suffix)`` using O_EXCL|O_CREAT 0600,
      * register ``atexit`` unlink cleanup for created files.
    """
    snippet = '''"""Auto-generated _nx_ secure-temp runtime loader (simple counterpart)."""
import atexit as _nx_atexit
import os as _nx_os
import tempfile as _nx_tempfile
import time as _nx_time

_nx_TRACKED = []

def _nx_purge_stale(prefix="_nx_", max_age_s=3600):
    """Remove stale _nx_* temp entries older than max_age_s (best effort)."""
    try:
        _nx_tmp = _nx_tempfile.gettempdir()
        _nx_now = _nx_time.time()
        for _nx_entry in _nx_os.listdir(_nx_tmp):
            if not _nx_entry.startswith(prefix):
                continue
            _nx_path = _nx_os.path.join(_nx_tmp, _nx_entry)
            try:
                if (_nx_now - _nx_os.path.getmtime(_nx_path)) < max_age_s:
                    continue
            except OSError:
                continue
            try:
                if _nx_os.path.isdir(_nx_path) and not _nx_os.path.islink(_nx_path):
                    import shutil as _nx_shutil
                    _nx_shutil.rmtree(_nx_path, ignore_errors=True)
                else:
                    _nx_os.unlink(_nx_path)
            except OSError:
                pass
    except Exception:
        pass

def _nx_secure_write(data, suffix="", prefix="_nx_"):
    """Write bytes via O_EXCL|O_CREAT|O_RDWR mode 0o600; track for atexit."""
    import secrets as _nx_secrets
    _nx_tmpdir = _nx_tempfile.gettempdir()
    _nx_flags = _nx_os.O_EXCL | _nx_os.O_CREAT | _nx_os.O_RDWR | getattr(_nx_os, "O_NOFOLLOW", 0)
    for _ in range(100):
        _nx_name = "%s%s%s" % (prefix, _nx_secrets.token_hex(8), suffix)
        _nx_path = _nx_os.path.join(_nx_tmpdir, _nx_name)
        try:
            _nx_fd = _nx_os.open(_nx_path, _nx_flags, 0o600)
        except FileExistsError:
            continue
        except OSError:
            continue
        try:
            try:
                _nx_os.fchmod(_nx_fd, 0o600)
            except (AttributeError, OSError):
                pass
            _nx_view = bytes(data)
            _nx_total = 0
            while _nx_total < len(_nx_view):
                _nx_n = _nx_os.write(_nx_fd, _nx_view[_nx_total:])
                if _nx_n <= 0:
                    raise OSError("short write")
                _nx_total += _nx_n
            _nx_os.fsync(_nx_fd)
        finally:
            _nx_os.close(_nx_fd)
        try:
            _nx_os.chmod(_nx_path, 0o600)
        except OSError:
            pass
        _nx_TRACKED.append(_nx_path)
        return _nx_path
    raise OSError("secure write failed: no unique name")

def _nx_cleanup():
    for _nx_p in list(_nx_TRACKED):
        try:
            _nx_os.unlink(_nx_p)
        except OSError:
            pass
        finally:
            try:
                _nx_TRACKED.remove(_nx_p)
            except ValueError:
                pass

_nx_atexit.register(_nx_cleanup)

# Purge stale _nx_* files on startup (best effort, never raises).
_nx_purge_stale()

try:
    pass
finally:
    pass
'''
    # Build-time self-check: the emitted loader must compile.
    compile(snippet, "<nx_secure_temp_loader>", "exec")
    return snippet
