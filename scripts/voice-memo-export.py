#!/usr/bin/env python3
# Mac-only: uses Apple Voice Memos export via AppleScript.
# Linux users: this script will not run. Use a different voice recording app
# and adapt the export logic to your tool's output format.
"""
Export Apple Voice Memos with embedded transcripts to Obsidian vault Inbox.

Reads recording metadata from CloudRecordings.db, extracts the tsrp transcript
atom from each .m4a file, and writes a markdown note per recording.
"""

import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
try:
    from config import VAULT_PATH
except ImportError:
    sys.exit(
        "Error: scripts/config.py not found.\n"
        "Copy scripts/config.example.py to scripts/config.py and fill in VAULT_PATH."
    )

RECORDINGS_DIR = os.path.expanduser(
    "~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings"
)
DB_PATH = os.path.join(RECORDINGS_DIR, "CloudRecordings.db")
INBOX_DIR = Path(VAULT_PATH) / "Inbox"


def extract_transcript(m4a_path: str) -> str | None:
    with open(m4a_path, "rb") as f:
        content = f.read()

    idx = content.find(b"tsrp{")
    if idx == -1:
        return None

    json_start = idx + 4  # skip 'tsrp'

    # Walk bytes to find the balanced closing brace
    depth = 0
    in_string = False
    escape = False
    end = json_start

    for i in range(json_start, len(content)):
        b = content[i]
        c = chr(b)
        if escape:
            escape = False
        elif c == "\\" and in_string:
            escape = True
        elif c == '"':
            in_string = not in_string
        elif not in_string:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

    try:
        data = json.loads(content[json_start:end].decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    attributed = data.get("attributedString", {})
    if not isinstance(attributed, dict):
        return None  # empty transcription placeholder

    runs = attributed.get("runs", [])
    words = [item for item in runs if isinstance(item, str)]
    return "".join(words).strip()


def sanitize_filename(name: str) -> str:
    return re.sub(r'[/\\:*?"<>|]', "-", name).strip()


def apple_timestamp_to_datetime(ts: float) -> datetime:
    # Apple timestamps use Jan 1 2001 epoch (CoreData/CFAbsoluteTime)
    apple_epoch = 978307200  # seconds between Unix epoch and Apple epoch
    return datetime.fromtimestamp(ts + apple_epoch, tz=timezone.utc)


def main():
    os.makedirs(INBOX_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT ZENCRYPTEDTITLE, ZPATH, ZDATE FROM ZCLOUDRECORDING "
        "WHERE ZPATH IS NOT NULL ORDER BY ZDATE"
    ).fetchall()
    conn.close()

    created = 0
    skipped = 0
    no_transcript = 0

    for title, path, apple_ts in rows:
        m4a_path = os.path.join(RECORDINGS_DIR, path)
        if not os.path.exists(m4a_path):
            skipped += 1
            continue

        dt = apple_timestamp_to_datetime(apple_ts)
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.astimezone().strftime("%Y-%m-%d %H:%M")

        transcript = extract_transcript(m4a_path)
        if transcript is None:
            no_transcript += 1
            transcript_body = "_No transcript available._"
        else:
            transcript_body = transcript

        safe_title = sanitize_filename(title)
        filename = f"{date_str} {safe_title}.md"
        out_path = os.path.join(INBOX_DIR, filename)

        # Avoid overwriting if a file with this name already exists
        if os.path.exists(out_path):
            base, ext = os.path.splitext(filename)
            out_path = os.path.join(INBOX_DIR, f"{base} (1){ext}")

        frontmatter = f"""---
title: "{title}"
date: {date_str}
type: voice-memo
source: apple-voice-memos
tags:
  - voice-memo
  - inbox
---"""

        content = f"""{frontmatter}

# {title}

*Recorded: {time_str}*

{transcript_body}
"""

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)

        created += 1
        if created % 50 == 0:
            print(f"  {created} files written...")

    print(f"\nDone.")
    print(f"  Created:        {created}")
    print(f"  No transcript:  {no_transcript}")
    print(f"  Skipped (missing .m4a): {skipped}")


if __name__ == "__main__":
    main()
