#!/bin/sh
# Independent binary analysis of a shipped blob (reviewer P2, 2026-11-20).
#
# Runs Ghidra headless over an extracted blob and reports two numbers that
# answer different questions:
#
#   * is the ENFORCEMENT SHIM readable?  -> decompile nx_apply_protections
#   * is the PAYLOAD recoverable?        -> survey the largest functions
#
# Both matter, and conflating them is how a 305-byte shim's readability gets
# mistaken for the payload being readable (or vice versa).
#
# Usage:  ./ghidra_boundary_check.sh <blob.so> [outdir]
# Requires analyzeHeadless from a Ghidra install (GHIDRA_HOME or on PATH).
set -eu

if [ $# -lt 1 ]; then
    echo "usage: $0 <blob.so> [outdir]" >&2
    exit 2
fi

BLOB="$1"
if [ ! -f "$BLOB" ]; then
    echo "not a file: $BLOB" >&2
    exit 3
fi

OUT="${2:-$(mktemp -d -t nx-ghidra-XXXXXX)}"
mkdir -p "$OUT"

HEADLESS="${GHIDRA_ANALYZE_HEADLESS:-}"
if [ -z "$HEADLESS" ]; then
    if [ -n "${GHIDRA_HOME:-}" ] && [ -x "$GHIDRA_HOME/support/analyzeHeadless" ]; then
        HEADLESS="$GHIDRA_HOME/support/analyzeHeadless"
    elif command -v analyzeHeadless >/dev/null 2>&1; then
        HEADLESS="$(command -v analyzeHeadless)"
    else
        for candidate in /opt/ghidra /usr/local/ghidra "$HOME/Tools/Ghidra"; do
            if [ -x "$candidate/support/analyzeHeadless" ]; then
                HEADLESS="$candidate/support/analyzeHeadless"
                break
            fi
        done
    fi
fi
if [ -z "$HEADLESS" ]; then
    echo "analyzeHeadless not found; set GHIDRA_HOME or GHIDRA_ANALYZE_HEADLESS" >&2
    exit 4
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$SCRIPT_DIR/ghidra_scripts"

PROJ="$OUT/proj-enf"
mkdir -p "$PROJ"
"$HEADLESS" "$PROJ" enf -import "$BLOB" \
    -postScript DecompileProbe.java "$OUT/enforcement.json" nx_apply_protections \
    -scriptPath "$SCRIPTS" -deleteProject > "$OUT/enforcement.log" 2>&1 || true

PROJ2="$OUT/proj-payload"
mkdir -p "$PROJ2"
NEEDLES="${NX_PAYLOAD_NEEDLES:-}"
"$HEADLESS" "$PROJ2" pay -import "$BLOB" \
    -postScript BigFnSurvey.java "$OUT/payload.json" "$NEEDLES" \
    -scriptPath "$SCRIPTS" -deleteProject > "$OUT/payload.log" 2>&1 || true

echo "outdir: $OUT"
if [ -f "$OUT/enforcement.json" ]; then
    echo "enforcement: $OUT/enforcement.json"
else
    echo "enforcement report MISSING (see $OUT/enforcement.log)" >&2
fi
if [ -f "$OUT/payload.json" ]; then
    echo "payload:     $OUT/payload.json"
else
    echo "payload report MISSING (see $OUT/payload.log)" >&2
fi
