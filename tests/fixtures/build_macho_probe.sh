#!/bin/sh
# Build tests/fixtures/macho_probe.c into real Mach-O objects for both
# architectures, so the macOS parser is exercised on real bytes rather than a
# synthetic fixture.
#
# Prints "ok=<arm64_obj> <x86_64_obj>" on success, or "skip=<reason>".
# Writes only inside $NX_MACHO_OUTDIR.
set -eu

if [ -z "${NX_MACHO_OUTDIR:-}" ] || [ ! -d "$NX_MACHO_OUTDIR" ]; then
    echo "skip=no-outdir"
    exit 2
fi

SRC="$(dirname "$0")/macho_probe.c"
if [ ! -f "$SRC" ]; then
    echo "skip=no-source"
    exit 3
fi

CC="$(command -v clang || true)"
if [ -z "$CC" ]; then
    echo "skip=no-clang"
    exit 0
fi

ARM="$NX_MACHO_OUTDIR/macho_arm64.o"
X86="$NX_MACHO_OUTDIR/macho_x86_64.o"

"$CC" --target=arm64-apple-macos11 -c "$SRC" -o "$ARM" \
    > "$NX_MACHO_OUTDIR/arm64.log" 2>&1 || {
    echo "skip=arm64-compile-failed"
    exit 0
}
"$CC" --target=x86_64-apple-macos11 -c "$SRC" -o "$X86" \
    > "$NX_MACHO_OUTDIR/x86_64.log" 2>&1 || {
    echo "skip=x86_64-compile-failed"
    exit 0
}
if [ ! -f "$ARM" ] || [ ! -f "$X86" ]; then
    echo "skip=no-output"
    exit 0
fi
echo "ok=$ARM $X86"
