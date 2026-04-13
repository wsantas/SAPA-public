#!/bin/bash
# Full SAPA backup — database, inbox files, config, and code.
# Set SAPA_PI_HOST and SAPA_PI_DIR environment variables for your setup.
#
# Backs up EVERYTHING needed to rebuild from scratch:
#   - SQLite database (all learning data, history, recipes, protocols, etc.)
#   - Health inbox files (per-profile markdown content)
#   - Homestead inbox files (family-shared content)
#   - Config (SMTP settings, preferences)
#   - Pending feeds (local content not yet sent to Pi)
#
# Usage:
#   ./scripts/backup.sh              # Backup from Pi to local machine
#   ./scripts/backup.sh --local      # Backup local ~/.sapa/ only (no Pi)
#
# Runs on your dev machine, pulls from the Pi via SSH.
# Schedule with cron for automated backups:
#   0 2 * * * ~/sapa/scripts/backup.sh >> /tmp/sapa-backup.log 2>&1

set -euo pipefail

# ============== Config ==============
PI_HOST="${SAPA_PI_HOST:-pi@raspberrypi.local}"
PI_SAPA_DIR="${SAPA_PI_DIR:-/home/pi/.sapa}"
LOCAL_SAPA_DIR="$HOME/.sapa"
BACKUP_ROOT="$HOME/Documents/sapa-backups"
KEEP_DAYS=90
DATE=$(date +%Y-%m-%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$DATE"

LOCAL_ONLY=false
if [[ "${1:-}" == "--local" ]]; then
    LOCAL_ONLY=true
fi

# ============== Setup ==============
mkdir -p "$BACKUP_DIR"

echo "=== SAPA Backup: $DATE ==="
echo "Destination: $BACKUP_DIR"
echo ""

# ============== 1. Database ==============
echo "[1/5] Database..."
if $LOCAL_ONLY; then
    if [[ -f "$LOCAL_SAPA_DIR/learning.db" ]]; then
        cp "$LOCAL_SAPA_DIR/learning.db" "$BACKUP_DIR/learning.db"
        echo "  Copied local DB ($(du -h "$BACKUP_DIR/learning.db" | cut -f1))"
    else
        echo "  No local DB found, skipping"
    fi
else
    scp "$PI_HOST:$PI_SAPA_DIR/learning.db" "$BACKUP_DIR/learning.db" 2>/dev/null && \
        echo "  Pulled Pi DB ($(du -h "$BACKUP_DIR/learning.db" | cut -f1))" || \
        echo "  WARNING: Could not pull DB from Pi"
fi

# ============== 2. Health Inbox ==============
echo "[2/5] Health inbox files..."
mkdir -p "$BACKUP_DIR/health-inbox"
if $LOCAL_ONLY; then
    SRC="$LOCAL_SAPA_DIR/plugins/health/inbox/"
else
    SRC="$PI_HOST:$PI_SAPA_DIR/plugins/health/inbox/"
fi
rsync -az --exclude='archive/' "$SRC" "$BACKUP_DIR/health-inbox/" 2>/dev/null && \
    echo "  $(find "$BACKUP_DIR/health-inbox" -name '*.md' | wc -l) files backed up" || \
    echo "  WARNING: Could not pull health inbox"

# ============== 3. Homestead Inbox ==============
echo "[3/5] Homestead inbox files..."
mkdir -p "$BACKUP_DIR/homestead-inbox"
if $LOCAL_ONLY; then
    SRC="$LOCAL_SAPA_DIR/plugins/homestead/inbox/"
else
    SRC="$PI_HOST:$PI_SAPA_DIR/plugins/homestead/inbox/"
fi
rsync -az --exclude='archive/' "$SRC" "$BACKUP_DIR/homestead-inbox/" 2>/dev/null && \
    echo "  $(find "$BACKUP_DIR/homestead-inbox" -name '*.md' | wc -l) files backed up" || \
    echo "  WARNING: Could not pull homestead inbox"

# ============== 4. Config ==============
echo "[4/5] Config..."
if $LOCAL_ONLY; then
    [[ -f "$LOCAL_SAPA_DIR/config.json" ]] && \
        cp "$LOCAL_SAPA_DIR/config.json" "$BACKUP_DIR/config.json" && \
        echo "  Copied local config" || echo "  No config found"
else
    scp "$PI_HOST:$PI_SAPA_DIR/config.json" "$BACKUP_DIR/config.json" 2>/dev/null && \
        echo "  Pulled Pi config" || echo "  No config on Pi (or SSH failed)"
fi

# ============== 5. Pending Feeds (local only) ==============
echo "[5/5] Pending feeds..."
PENDING="$HOME/dev/sapa/pending-feeds"
if [[ -d "$PENDING" ]] && [[ -n "$(ls -A "$PENDING" 2>/dev/null)" ]]; then
    cp -r "$PENDING" "$BACKUP_DIR/pending-feeds"
    echo "  $(find "$BACKUP_DIR/pending-feeds" -name '*.md' | wc -l) pending feeds backed up"
else
    echo "  No pending feeds"
fi

# ============== Compress ==============
echo ""
echo "Compressing..."
ARCHIVE="$BACKUP_ROOT/sapa-backup-$DATE.tar.gz"
tar -czf "$ARCHIVE" -C "$BACKUP_ROOT" "$DATE"
rm -rf "$BACKUP_DIR"
echo "  Archive: $ARCHIVE ($(du -h "$ARCHIVE" | cut -f1))"

# ============== Prune Old Backups ==============
echo ""
echo "Pruning backups older than $KEEP_DAYS days..."
PRUNED=$(find "$BACKUP_ROOT" -name 'sapa-backup-*.tar.gz' -mtime +$KEEP_DAYS -delete -print | wc -l)
echo "  Removed $PRUNED old backups"

# ============== Summary ==============
TOTAL=$(find "$BACKUP_ROOT" -name 'sapa-backup-*.tar.gz' | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_ROOT" | cut -f1)
echo ""
echo "=== Backup Complete ==="
echo "  Archive:  $ARCHIVE"
echo "  Backups:  $TOTAL total ($TOTAL_SIZE)"
echo ""
