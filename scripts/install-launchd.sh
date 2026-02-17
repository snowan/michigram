#!/usr/bin/env bash
set -euo pipefail

LABEL="com.michi-context-v2.daemon"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
MICHI_BIN=$(command -v michi-context-v2 2>/dev/null || echo "")

if [ -z "$MICHI_BIN" ]; then
    echo "Error: michi-context-v2 not found. Install with: pip install -e /path/to/michi-context-v2"
    exit 1
fi

LOG_DIR="$HOME/.michi-context-v2/logs"
mkdir -p "$LOG_DIR"

cat > "$PLIST_PATH" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${MICHI_BIN}</string>
        <string>daemon</string>
        <string>--interval</string>
        <string>1800</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/daemon.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/daemon.err</string>
</dict>
</plist>
PLIST

if launchctl list | grep -q "$LABEL" 2>/dev/null; then
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

launchctl load "$PLIST_PATH"
echo "Installed and started launchd daemon: $LABEL"
echo "Logs: $LOG_DIR/daemon.log"
