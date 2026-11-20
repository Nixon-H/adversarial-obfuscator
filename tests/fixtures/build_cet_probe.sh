#!/bin/sh
# Build tests/fixtures/cet_probe.c into a PE carrying CET guard bits.
#
# Used by tests/test_native_harden.py so the CET check exercises a REAL object
# rather than a synthetic header. The object is built, not checked in, because
# *.exe is gitignored -- a checked-in binary would silently skip in CI.
#
# Prints "ok=<path>" on success, or "skip=<reason>" when the toolchain is
# absent, so the caller can distinguish "not exercised" from "passed".
#
# Writes only inside $NX_CET_OUTDIR.
set -eu

if [ -z "${NX_CET_OUTDIR:-}" ] || [ ! -d "$NX_CET_OUTDIR" ]; then
    echo "skip=no-outdir"
    exit 2
fi

SRC="$(dirname "$0")/cet_probe.c"
if [ ! -f "$SRC" ]; then
    echo "skip=no-source"
    exit 3
fi

CC=""
for candidate in clang-cl clang-cl-19; do
    if command -v "$candidate" >/dev/null 2>&1; then
        CC="$candidate"
        break
    fi
done
if [ -z "$CC" ]; then
    echo "skip=no-clang-cl"
    exit 0
fi
if ! command -v lld-link >/dev/null 2>&1; then
    echo "skip=no-lld-link"
    exit 0
fi

OBJ="$NX_CET_OUTDIR/cet_probe.obj"
EXE="$NX_CET_OUTDIR/cet_probe.exe"

# shellcheck disable=SC2086
"$CC" --target=x86_64-w64-windows-gnu /guard:cf /c "$SRC" /Fo:"$OBJ" \
    > "$NX_CET_OUTDIR/compile.log" 2>&1 || {
    echo "skip=compile-failed"
    exit 0
}
lld-link /guard:cf /subsystem:console /nodefaultlib \
    /entry:mainCRTStartup /out:"$EXE" "$OBJ" \
    > "$NX_CET_OUTDIR/link.log" 2>&1 || {
    echo "skip=link-failed"
    exit 0
}
if [ ! -f "$EXE" ]; then
    echo "skip=no-output"
    exit 0
fi
echo "ok=$EXE"
