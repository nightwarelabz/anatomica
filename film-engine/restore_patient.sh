#!/bin/sh
# Restore patient.blend from the in-repo compressed archive and verify
# it byte-for-byte against the recorded SHA-256.
# Usage: ./restore_patient.sh [output-path]
set -e
cd "$(dirname "$0")"
OUT="${1:-patient.blend}"
EXPECTED="10fd128418624492e00773621eefa4da069658198594a4c3ed8674618793fe0a"
if [ -f patient.blend.xz ]; then
    xz -dc patient.blend.xz > "$OUT"
else
    # transport-split fallback: reassemble the parts in order
    cat patient.blend.xz.part-* | xz -dc > "$OUT"
fi
ACTUAL="$(sha256sum "$OUT" | awk '{print $1}')"
if [ "$ACTUAL" = "$EXPECTED" ]; then
    echo "OK: $OUT verified ($ACTUAL)"
else
    echo "FAIL: sha256 mismatch: got $ACTUAL, expected $EXPECTED" >&2
    exit 1
fi
