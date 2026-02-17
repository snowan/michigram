#!/usr/bin/env bash
set -euo pipefail

SETTINGS_FILE="$HOME/.claude/settings.json"
HOOK_CMD="michi-context-v2 inject --project \$CWD --adapter claude-code"

if ! command -v michi-context-v2 &>/dev/null; then
    echo "Error: michi-context-v2 not found. Install with: pip install -e /path/to/michi-context-v2"
    exit 1
fi

mkdir -p "$(dirname "$SETTINGS_FILE")"

if [ ! -f "$SETTINGS_FILE" ]; then
    cat > "$SETTINGS_FILE" << 'SETTINGS'
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "michi-context-v2 inject --project $CWD --adapter claude-code"
      }
    ]
  }
}
SETTINGS
    echo "Created $SETTINGS_FILE with SessionStart hook"
    exit 0
fi

if grep -q "michi-context-v2" "$SETTINGS_FILE" 2>/dev/null; then
    echo "Hook already installed in $SETTINGS_FILE"
    exit 0
fi

python3 -c "
import json, sys

with open('$SETTINGS_FILE') as f:
    settings = json.load(f)

hooks = settings.setdefault('hooks', {})
session_hooks = hooks.setdefault('SessionStart', [])

session_hooks.append({
    'type': 'command',
    'command': 'michi-context-v2 inject --project \$CWD --adapter claude-code'
})

with open('$SETTINGS_FILE', 'w') as f:
    json.dump(settings, f, indent=2)
"

echo "Added SessionStart hook to $SETTINGS_FILE"
