#!/bin/bash
# Retry pending feeds that failed SSH delivery.
#
# Usage: retry-pending.sh
# Run manually or via cron: */5 * * * * /path/to/retry-pending.sh

set -euo pipefail

PI_HOST="${SAPA_PI_HOST:-pi@raspberrypi.local}"
PENDING_DIR="$HOME/.sapa/pending-feeds"

if [ ! -d "$PENDING_DIR" ]; then
    echo "No pending directory. Nothing to retry."
    exit 0
fi

# Check if Pi is reachable
if ! ssh -o ConnectTimeout=5 "$PI_HOST" "true" 2>/dev/null; then
    echo "Pi unreachable. Will retry later."
    exit 1
fi

DELIVERED=0
FAILED=0

for json_file in "$PENDING_DIR"/*.json; do
    [ -f "$json_file" ] || continue

    BASENAME="${json_file%.json}"
    MD_FILE="${BASENAME}.md"

    if [ ! -f "$MD_FILE" ]; then
        echo "Warning: no content file for $json_file, removing metadata"
        rm -f "$json_file"
        continue
    fi

    REMOTE_PATH=$(python3 -c "import json; print(json.load(open('$json_file'))['remote_path'])" 2>/dev/null)
    if [ -z "$REMOTE_PATH" ]; then
        echo "Warning: could not parse $json_file"
        ((FAILED++)) || true
        continue
    fi

    if ssh -o ConnectTimeout=5 "$PI_HOST" "cat > ${REMOTE_PATH}" < "$MD_FILE" 2>/dev/null; then
        echo "Delivered: $REMOTE_PATH"
        rm -f "$MD_FILE" "$json_file"
        ((DELIVERED++)) || true
    else
        echo "Failed: $REMOTE_PATH"
        ((FAILED++)) || true
    fi
done

echo "Retry complete: $DELIVERED delivered, $FAILED failed"

# If any were delivered, trigger rescan
if [ "$DELIVERED" -gt 0 ]; then
    ssh "$PI_HOST" "wget -q -O - --post-data='' http://localhost:8001/api/rescan" 2>/dev/null || true
    echo "Rescan triggered"
fi
