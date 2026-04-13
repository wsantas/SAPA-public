#!/bin/bash
# Install SAPA on Raspberry Pi
# Run from the set-apart directory on the Pi

set -e

echo "Installing SAPA..."

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Installing dependencies..."
.venv/bin/pip install -e . --quiet

# Create inbox directories
INBOX_DST="$HOME/.sapa/plugins/health/inbox"
mkdir -p "$INBOX_DST/john" "$INBOX_DST/jane"
echo "Inbox directories created at $INBOX_DST"

# Install systemd service
echo "Installing systemd service..."
sudo cp templates/sapa.service /etc/systemd/system/sapa.service
sudo systemctl daemon-reload
sudo systemctl enable sapa

echo ""
echo "SAPA installed. Commands:"
echo "  sudo systemctl start sapa     # Start"
echo "  sudo systemctl stop sapa      # Stop"
echo "  sudo systemctl restart sapa   # Restart"
echo "  sudo systemctl status sapa    # Status"
echo "  journalctl -u sapa -f         # Logs"
echo ""
