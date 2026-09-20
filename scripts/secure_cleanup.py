#!/usr/bin/env python3
"""secure_cleanup.py — securely wipe a build tree (overwrite + unlink).

Library use:
    from scripts.secure_cleanup import secure_cleanup_tree

CLI use:
    python3 -m scripts.secure_cleanup <dir> [--passes N] [--yes]
"""

from __future__ import annotations

import argparse
import os
import sys


def _overwrite_file(path: str, passes: int) -> None:
    size = os.path.getsize(path)
    if size <= 0:
        return
    with open(path, "r+b") as f:
        for _ in range(max(0, int(passes))):
            f.seek(0)
            remaining = size
            while remaining > 0:
                chunk = os.urandom(min(remaining, 1024 * 1024))
                f.write(chunk)
                remaining -= len(chunk)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass


def secure_cleanup_tree(root: str, passes: int = 3) -> dict:
    """Walk *root* bottom-up, overwrite+unlink files, then rmdir dirs.

    Never follows symlinks: symlinked files/dirs are skipped and recorded
    in ``errors``. Returns ``{'files': n, 'dirs': n, 'errors': [...]}``.
    A missing *root* yields ``errors`` entry with zero counts (no raise).
    """
    result: dict = {"files": 0, "dirs": 0, "errors": []}
    if not os.path.lexists(root):
        result["errors"].append(f"missing dir: {root}")
        return result
    if os.path.islink(root) or not os.path.isdir(root):
        result["errors"].append(f"not a directory: {root}")
        return result
    try:
        for dirpath, dirnames, filenames in os.walk(
            root, topdown=False, followlinks=False
        ):
            for name in filenames:
                fpath = os.path.join(dirpath, name)
                try:
                    if os.path.islink(fpath):
                        result["errors"].append(f"skipped symlink: {fpath}")
                        continue
                    if not os.path.isfile(fpath):
                        result["errors"].append(f"skipped non-regular: {fpath}")
                        continue
                    try:
                        _overwrite_file(fpath, passes)
                    except OSError as e:
                        result["errors"].append(f"overwrite failed {fpath}: {e}")
                        continue
                    os.unlink(fpath)
                    result["files"] += 1
                except OSError as e:
                    result["errors"].append(f"{fpath}: {e}")
            for name in dirnames:
                dpath = os.path.join(dirpath, name)
                try:
                    if os.path.islink(dpath):
                        result["errors"].append(f"skipped symlink: {dpath}")
                        continue
                    try:
                        os.rmdir(dpath)
                    except OSError:
                        # Might be non-empty due to skipped symlinks etc.
                        # Leave it; record but keep walking.
                        result["errors"].append(f"rmdir failed (non-empty?): {dpath}")
                        continue
                    result["dirs"] += 1
                except OSError as e:
                    result["errors"].append(f"{dpath}: {e}")
        try:
            os.rmdir(root)
            result["dirs"] += 1
        except OSError as e:
            result["errors"].append(f"rmdir failed {root}: {e}")
    except OSError as e:
        result["errors"].append(str(e))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Securely wipe a directory tree (overwrite with urandom, then unlink)."
    )
    parser.add_argument("dir", help="Directory tree to securely delete")
    parser.add_argument("--passes", type=int, default=3, help="Overwrite passes (default: 3)")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args(argv)

    if not args.yes:
        try:
            answer = input(f"Securely delete '{args.dir}' with {args.passes} passes? [y/N] ")
        except EOFError:
            answer = "n"
        if answer.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return 1

    result = secure_cleanup_tree(args.dir, passes=args.passes)
    print(f"files={result['files']} dirs={result['dirs']} errors={len(result['errors'])}")
    for err in result["errors"]:
        print(f"  error: {err}", file=sys.stderr)
    return 0 if os.path.lexists(args.dir) is False else 1


if __name__ == "__main__":
    sys.exit(main())
