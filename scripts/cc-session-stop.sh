#!/bin/bash
# Records session metadata for session logging.
# Called by Stop hook — receives Claude Code session JSON on stdin.
SESSION_JSON=$(cat)
SESSION_ID=$(echo "$SESSION_JSON" | jq -r '.session_id // "unknown"')
START_FILE="/tmp/cc-session-${SESSION_ID}.start"

if [ ! -f "$START_FILE" ]; then
  exit 0
fi

START_EPOCH=$(cat "$START_FILE")
END_EPOCH=$(date +%s)
DURATION_SECS=$((END_EPOCH - START_EPOCH))

# Ignore sessions under 2 minutes (accidental /new, noise)
if [ $DURATION_SECS -lt 120 ]; then
  rm "$START_FILE"
  exit 0
fi

DURATION_HRS=$(awk "BEGIN {printf \"%.2f\", $DURATION_SECS/3600}")
WEEK=$(date +%Y-W%V)
# Read vault path from environment (set VAULT_PATH in your shell profile or scripts/config.py)
VAULT_PATH="${VAULT_PATH:-}"
if [ -z "$VAULT_PATH" ]; then
  # Try to read from scripts/config.py as fallback
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  VAULT_PATH=$(python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from config import VAULT_PATH; print(VAULT_PATH)" 2>/dev/null || echo "")
fi
LOG_DIR="${VAULT_PATH}/Inbox"
LOG_FILE="${LOG_DIR}/cc-sessions-${WEEK}.md"
DATE=$(date +%Y-%m-%d)
START_TIME=$(date -r "$START_EPOCH" "+%H:%M")
END_TIME=$(date "+%H:%M")

# Log session to vault inbox
if [ ! -f "$LOG_FILE" ]; then
  printf "# Claude Code Sessions — %s\n\n" "$WEEK" > "$LOG_FILE"
  printf "| Date | Start | End | Duration |\n" >> "$LOG_FILE"
  printf "| ---- | ----- | --- | -------- |\n" >> "$LOG_FILE"
fi

printf "| %s | %s | %s | %s hrs |\n" "$DATE" "$START_TIME" "$END_TIME" "$DURATION_HRS" >> "$LOG_FILE"

rm "$START_FILE"
