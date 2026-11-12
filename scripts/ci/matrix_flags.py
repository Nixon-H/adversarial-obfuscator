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

# Representative, value-safe transforms: one per major technique family.
WANTED = [
    "--cfg-flatten", "--mba-subs", "--opaque-predicates",
    "--fragment-strings", "--class-dispatch", "--anti-rea-level",
]


def main():
    by_name = {e["flag"]: e for e in catalogue()}
    out = []
    for name in WANTED:
        entry = by_name.get(name)
        if entry is None or entry["kind"] == "excluded":
            continue
        out.append(" ".join(entry["argv"]))
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
