#!/bin/bash
# Records session start time for timesheet logging.
# Called by SessionStart hook — receives Claude Code session JSON on stdin.
SESSION_ID=$(cat | jq -r '.session_id // "unknown"')
if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "unknown" ]; then
  echo "$(date +%s)" > "/tmp/cc-session-${SESSION_ID}.start"
fi
