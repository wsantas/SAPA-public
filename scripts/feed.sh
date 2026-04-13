#!/bin/bash
# Feed content to SAPA Pi inbox via SSH.
# Falls back to local pending queue on failure.
#
# Usage: feed.sh <plugin> <profile> <filename> < content
#   feed.sh health john "sleep-guide.md" < content.md
#   echo "# Title" | feed.sh homestead "" "topic.md"

set -euo pipefail

PI_HOST="${SAPA_PI_HOST:-pi@raspberrypi.local}"
PENDING_DIR="$HOME/.sapa/pending-feeds"

PLUGIN="${1:?Usage: feed.sh <plugin> <profile> <filename>}"
PROFILE="${2:-}"
FILENAME="${3:?Usage: feed.sh <plugin> <profile> <filename>}"

# Build remote path
if [ "$PLUGIN" = "health" ] && [ -n "$PROFILE" ]; then
    REMOTE_PATH="~/.sapa/plugins/health/inbox/${PROFILE}/${FILENAME}"
elif [ "$PLUGIN" = "homestead" ]; then
    REMOTE_PATH="~/.sapa/plugins/homestead/inbox/${FILENAME}"
else
    echo "Error: health requires a profile name (john/jane)"
    exit 1
fi

# Read content from stdin
CONTENT=$(cat)

# Try SSH delivery (cat > triggers watchdog)
if ssh -o ConnectTimeout=5 "$PI_HOST" "cat > ${REMOTE_PATH}" <<< "$CONTENT" 2>/dev/null; then
    echo "Delivered: ${REMOTE_PATH}"
else
    # Queue for later retry
    mkdir -p "$PENDING_DIR"
    TIMESTAMP=$(date +%s)
    BASENAME=$(basename "$FILENAME" .md)

    # Save content
    echo "$CONTENT" > "${PENDING_DIR}/${TIMESTAMP}_${BASENAME}.md"

    # Save metadata
    cat > "${PENDING_DIR}/${TIMESTAMP}_${BASENAME}.json" <<EOF
{
    "plugin": "$PLUGIN",
    "profile": "$PROFILE",
    "filename": "$FILENAME",
    "remote_path": "$REMOTE_PATH",
    "queued_at": "$(date -Iseconds)"
}
EOF

    echo "SSH failed. Queued: ${PENDING_DIR}/${TIMESTAMP}_${BASENAME}.md"
    exit 2
fi
