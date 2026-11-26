"""Emit the flag argv list for the platform matrix, taken from the catalogue.

The workflow used to hard-code six flags. That duplicated knowledge the catalogue
already has and produced two batches of false failures: --attention-poison was
passed with no fan-out value (build.py exited 2), and one flag was misidentified
as boolean. Deriving the argv here means the matrix cannot drift from the
catalogue.

Prints a JSON array of strings suitable for a GitHub matrix.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flag_catalogue import catalogue  # noqa: E402

# Representative, value-safe transforms drawn from the live catalogue. The
# old WANTED list named flags that no longer exist, so the matrix silently
# collapsed to a single flag. Names are checked below and a missing name is
# an error rather than a silent skip.
WANTED = [
    "--anti-rea-level", "--diagnostic", "--include-original",
    "--no-cfg-flatten", "--no-mba-subs", "--optimize",
]


def main():
    entries = catalogue()
    by_name = {e["flag"]: e for e in entries}
    if "--all" in sys.argv:
        selected = [e for e in entries if e["kind"] != "excluded"]
    else:
        selected = []
        for name in WANTED:
            entry = by_name.get(name)
            if entry is None:
                raise SystemExit("matrix flag %r is not in the live catalogue" % name)
            if entry["kind"] == "excluded":
                raise SystemExit("matrix flag %r is excluded from safe builds" % name)
            selected.append(entry)
    out = [" ".join(entry["argv"]) for entry in selected]
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
