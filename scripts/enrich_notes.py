#!/usr/bin/env python3
"""
Granola → Obsidian YAML Enrichment
Reads unenriched meeting notes and uses Claude to add client, meeting_type,
vertical, opportunity, and summary fields to the YAML frontmatter.

Usage:
  python3 enrich_notes.py                       # enrich all unenriched notes
  python3 enrich_notes.py --re-enrich-internal  # re-enrich notes tagged client: "Internal"
  python3 enrich_notes.py --add-hub-links       # backfill hub_note on enriched notes missing it (all folders)
"""

import os
import re
import sys
import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# Load vault path from scripts/config.py
sys.path.insert(0, str(Path(__file__).parent))
try:
    from config import VAULT_PATH
except ImportError:
    sys.exit(
        "Error: scripts/config.py not found.\n"
        "Copy scripts/config.example.py to scripts/config.py and fill in VAULT_PATH."
    )

# --- CONFIG ---
VAULT_ROOT = VAULT_PATH
# Update NOTES_FOLDER to match your vault structure:
# Consulting vault: f"{VAULT_ROOT}/Meetings/Granola/Notes"
# General vault:    f"{VAULT_ROOT}/Meetings/Notes"
NOTES_FOLDER = f"{VAULT_ROOT}/Meetings/Notes"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-6"

# Add entries here to correct transcription errors in speaker names.
# Example: "mike s": "Mike Schmidt"
NAME_ALIASES: dict[str, str] = {}

SYSTEM_PROMPT = """You are a metadata enrichment assistant for a consultant's Obsidian vault.
Read a meeting note or voice memo transcript and return enriched YAML fields.

KNOWN CLIENTS (match exactly):
# Add your client names here, one per line, e.g.:
# - Acme Corp
# - Widgets Inc

INTERNAL MEETING CLASSIFICATION:
For meetings with no external client, use one of these two values for "client":
- "Internal - Leadership": Sensitive strategy or business meetings with senior leaders.
  Use for: pipeline reviews, compensation, org strategy, deal desk, exec 1:1s.
- "Internal - Delivery": Routine check-ins and project updates with delivery team members.
  Use for: project standups, 1:1s with ICs or project managers.

When in doubt between the two: if the meeting involves pipeline numbers, strategy, compensation, or org decisions → Leadership. If it's about project work, client delivery, or team coordination → Delivery.

KNOWN VERTICALS: (customize to your practice — e.g. Healthcare, Financial Services, Technology, Internal)

MEETING TYPES: Discovery, Demo, Proposal Review, QBR, Kickoff, Check-in, Internal, Stand-up, Strategy, Workshop

Return ONLY raw JSON, no markdown, no code fences:
{
  "client": "exact name from list, Internal - Leadership, Internal - Delivery, or Unknown",
  "meeting_type": "best match from meeting types",
  "vertical": "best match from verticals",
  "opportunity": "short deal or project name, or empty string",
  "summary": "one sentence, max 15 words",
  "people": ["First Last", "First Last"]
}

PEOPLE EXTRACTION RULES:
- List only people who actively speak or are meaningfully discussed (not passing mentions)
- Use full names where you can infer them from context
- Include both internal staff and external contacts
- If only a first name is clear, use just the first name
- Return an empty array [] if no people can be identified
- Do NOT include the vault owner unless they are being discussed by others"""

# Map client names (as returned by Claude) to vault-relative hub note paths.
# Example: "Acme Corp": "Clients/AcmeCorp/Acme Corp — Hub"
CLIENT_HUB_MAP: dict[str, str] = {}

# Keyed on filename substrings — checked when client is Internal-* and CLIENT_HUB_MAP has no match.
# Order matters: more specific patterns first.
# Example: "Weekly Pipeline Call": "Internal/Meeting Series/Weekly Pipeline Call — Hub"
MEETING_SERIES_HUB_MAP: dict[str, str] = {}

def get_all_meeting_note_folders() -> list:
    """Returns all meeting note folders: standard paths + any Clients/*/Meetings/Notes/ subfolders."""
    folders = [
        Path(NOTES_FOLDER),
    ]
    clients_dir = Path(VAULT_ROOT) / "Clients"
    if clients_dir.exists():
        for client_dir in sorted(clients_dir.iterdir()):
            if client_dir.is_dir():
                candidate = client_dir / "Meetings" / "Notes"
                if candidate.exists():
                    folders.append(candidate)
    return folders


_FRONTMATTER_RE = re.compile(r"^---\n([\s\S]*?)\n---\n([\s\S]*)$")


def parse_frontmatter(content: str):
    """Returns (fm_str, body_str) or (None, None) if no YAML frontmatter found."""
    m = _FRONTMATTER_RE.match(content)
    return (m.group(1), m.group(2)) if m else (None, None)


def extract_field(field: str, text: str) -> str:
    m = re.search(rf'"{field}"\s*:\s*"([^"]*)"', text)
    return m.group(1) if m else ""


def normalize_people(names: list) -> list:
    """Apply canonical name aliases and deduplicate."""
    out = []
    seen = set()
    for name in names:
        canonical = NAME_ALIASES.get(name.lower().strip(), name.strip())
        if canonical.lower() not in seen:
            seen.add(canonical.lower())
            out.append(canonical)
    return out


def needs_hub_link(content: str) -> bool:
    return 'hub_note:' not in content or 'hub_note: ""' in content or "hub_note: ''" in content


def _hub_short_link(hub_note_path: str) -> str:
    """Extract short [[Filename]] from a full [[path/to/Filename]] hub_note value."""
    m = re.search(r'\[\[(?:.*/)?([^\]]+)\]\]', hub_note_path)
    return f"[[{m.group(1)}]]" if m else ""


def _append_hub_link_to_body(body: str, hub_note_path: str) -> str:
    """Append a short hub wikilink footer to body if not already present."""
    if not hub_note_path:
        return body
    short = _hub_short_link(hub_note_path)
    if not short or short in body:
        return body
    return body.rstrip() + f"\n\n---\n{short}\n"


def _build_enriched_fm(base_fm: str, metadata: dict, hub_note: str, today: str) -> str:
    people = normalize_people(metadata.get("people", []))
    if people:
        people_yaml = "\npeople:\n" + "\n".join(f'  - "{p}"' for p in people)
    else:
        people_yaml = '\npeople: []'
    return (
        base_fm
        + f'\nclient: "{metadata["client"]}"'
        + f'\nmeeting_type: "{metadata["meeting_type"]}"'
        + f'\nvertical: "{metadata["vertical"]}"'
        + f'\nopportunity: "{metadata["opportunity"]}"'
        + f'\nsummary: "{metadata["summary"]}"'
        + people_yaml
        + f'\nhub_note: "{hub_note}"'
        + f'\nenriched: true'
        + f'\nenriched_date: {today}'
    )


def get_hub_note(client: str, filename: str = "") -> str:
    path = CLIENT_HUB_MAP.get(client, "")
    if path:
        return f"[[{path}]]"
    if filename and client.startswith("Internal"):
        for pattern, series_path in MEETING_SERIES_HUB_MAP.items():
            if pattern in filename:
                return f"[[{series_path}]]"
    return ""


MAX_CONTENT_CHARS = 4000  # title + first ~500 words is plenty for classification


def truncate_for_enrichment(content: str) -> str:
    """Keep frontmatter + first MAX_CONTENT_CHARS of body to stay under token limits."""
    if len(content) <= MAX_CONTENT_CHARS:
        return content
    return content[:MAX_CONTENT_CHARS] + "\n\n[transcript truncated]"


def call_claude(content: str) -> dict:
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 500,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": truncate_for_enrichment(content)}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    )

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))
                raw = result["content"][0]["text"].strip()

                # Strip markdown code fences if Claude wrapped it anyway
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
                raw = raw.strip()

                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    result = {f: extract_field(f, raw) for f in ["client", "meeting_type", "vertical", "opportunity", "summary"]}
                    result["people"] = []
                    return result
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            if e.code == 429 and attempt < 2:
                wait = 30 * (attempt + 1)
                print(f"  ⏳ Rate limited — waiting {wait}s before retry {attempt + 2}/3...")
                time.sleep(wait)
                continue
            raise Exception(f"HTTP {e.code}: {error_body}")


def enrich_note(file_path: Path, content: str = None) -> bool:
    """Enrich a note that has never been enriched before."""
    if content is None:
        content = file_path.read_text(encoding="utf-8")

    if "enriched: true" in content:
        return False

    fm, body = parse_frontmatter(content)
    if fm is None:
        print(f"  ⚠️  No frontmatter: {file_path.name}")
        return False

    print(f"  Processing: {file_path.name}")

    try:
        metadata = call_claude(content)
    except Exception as e:
        print(f"  ❌ Claude error: {e}")
        return False

    today = datetime.now().strftime("%Y-%m-%d")
    hub_note = get_hub_note(metadata["client"], file_path.name)
    new_fm = _build_enriched_fm(fm, metadata, hub_note, today)
    new_body = _append_hub_link_to_body(body, hub_note)
    file_path.write_text(f"---\n{new_fm}\n---\n{new_body}", encoding="utf-8")
    print(f"  ✅ {metadata['client']} | {metadata['meeting_type']} | {metadata['summary']}")
    return True


def re_enrich_note(file_path: Path, content: str = None) -> bool:
    """Re-enrich a note that was previously enriched — strips old enrichment fields and re-runs."""
    if content is None:
        content = file_path.read_text(encoding="utf-8")

    fm, body = parse_frontmatter(content)
    if fm is None:
        return False

    fields_to_strip = ["client", "meeting_type", "vertical", "opportunity", "summary", "hub_note", "enriched", "enriched_date"]
    cleaned_fm = "\n".join(
        line for line in fm.splitlines()
        if not any(line.startswith(f"{field}:") for field in fields_to_strip)
    )
    clean_content = f"---\n{cleaned_fm}\n---\n{body}"

    print(f"  Re-enriching: {file_path.name}")

    try:
        metadata = call_claude(clean_content)
    except Exception as e:
        print(f"  ❌ Claude error: {e}")
        return False

    today = datetime.now().strftime("%Y-%m-%d")
    hub_note = get_hub_note(metadata["client"], file_path.name)
    new_fm = _build_enriched_fm(cleaned_fm, metadata, hub_note, today)
    new_body = _append_hub_link_to_body(body, hub_note)
    file_path.write_text(f"---\n{new_fm}\n---\n{new_body}", encoding="utf-8")
    print(f"  ✅ {metadata['client']} | {metadata['meeting_type']} | {metadata['summary']}")
    return True


def add_hub_links() -> int:
    """Add hub_note to already-enriched notes that are missing it. Scans all meeting note folders."""
    folders = get_all_meeting_note_folders()

    enriched_count = 0
    candidates = []
    for folder in folders:
        if not folder.exists():
            continue
        for f in sorted(folder.glob("*.md")):
            text = f.read_text(encoding="utf-8")
            if "enriched: true" not in text:
                continue
            enriched_count += 1
            if needs_hub_link(text):
                candidates.append((f, text))
                continue
            # Frontmatter hub_note exists — check if body link is also present
            fm_check, body_check = parse_frontmatter(text)
            if fm_check and body_check is not None:
                client_m = re.search(r'^client:\s*"?([^"\n]+?)"?\s*$', fm_check, re.MULTILINE)
                if client_m:
                    hn = get_hub_note(client_m.group(1), f.name)
                    short = _hub_short_link(hn) if hn else ""
                    if short and short not in body_check:
                        candidates.append((f, text))

    print(f"Found {len(candidates)} enriched notes needing hub_note or body link (out of {enriched_count} enriched across {len(folders)} folders)\n")

    count = 0
    for file_path, content in candidates:
        fm, body = parse_frontmatter(content)
        if fm is None:
            continue

        client_match = re.search(r'^client:\s*"?([^"\n]+?)"?\s*$', fm, re.MULTILINE)
        if not client_match:
            continue
        hub_note = get_hub_note(client_match.group(1), file_path.name)

        if 'hub_note:' in fm:
            new_fm = re.sub(r'hub_note:\s*"[^"]*"', f'hub_note: "{hub_note}"', fm)
        else:
            new_fm = re.sub(r'(enriched: true)', f'hub_note: "{hub_note}"\n\\1', fm)

        new_body = _append_hub_link_to_body(body, hub_note)
        file_path.write_text(f"---\n{new_fm}\n---\n{new_body}", encoding="utf-8")
        print(f"  ✅ {file_path.name} → {hub_note or '(no match)'}")
        count += 1

    return count


def enrich_inbox(exclude_pattern: str = "") -> int:
    """Enrich voice-memo files from the Inbox, optionally excluding a filename pattern."""
    inbox = Path(VAULT_ROOT) / "Inbox"
    if not inbox.exists():
        print(f"❌ Inbox not found: {inbox}")
        return 0

    candidates = []
    for f in sorted(inbox.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        if "source: apple-voice-memos" not in text:
            continue
        if "enriched: true" in text:
            continue
        if exclude_pattern and exclude_pattern.lower() in f.name.lower():
            continue
        candidates.append((f, text))

    print(f"Found {len(candidates)} unenriched voice-memo notes in Inbox\n")
    if not candidates:
        print("Nothing to do.")
        return 0

    count = 0
    for f, text in candidates:
        if enrich_note(f, text):
            count += 1
        time.sleep(2)  # stay under 30k tokens/min rate limit
    return count


def add_people(folder: Path = None) -> int:
    """Backfill people field on already-enriched notes that are missing it."""
    if folder is None:
        folders = get_all_meeting_note_folders()
        folders.append(Path(VAULT_ROOT) / "Inbox")
        folders.append(Path(VAULT_ROOT) / "Personal")
    else:
        folders = [folder]

    candidates = []
    for f_dir in folders:
        if not f_dir.exists():
            continue
        for f in sorted(f_dir.glob("*.md")):
            text = f.read_text(encoding="utf-8")
            if "enriched: true" not in text:
                continue
            if "people:" in text:
                continue
            candidates.append((f, text))

    print(f"Found {len(candidates)} enriched notes missing people field\n")
    if not candidates:
        print("Nothing to do.")
        return 0

    count = 0
    for file_path, content in candidates:
        fm, body = parse_frontmatter(content)
        if fm is None:
            continue
        print(f"  Processing: {file_path.name[:70]}")
        try:
            metadata = call_claude(content)
        except Exception as e:
            print(f"  ❌ Claude error: {e}")
            time.sleep(2)
            continue

        people = normalize_people(metadata.get("people", []))
        if people:
            people_yaml = "people:\n" + "\n".join(f'  - "{p}"' for p in people)
        else:
            people_yaml = "people: []"

        new_fm = fm.rstrip() + f"\n{people_yaml}"
        file_path.write_text(f"---\n{new_fm}\n---\n{body}", encoding="utf-8")
        print(f"  ✅ {people}")
        count += 1
        time.sleep(2)

    return count


def main():
    re_enrich_internal = "--re-enrich-internal" in sys.argv
    add_hub_links_flag = "--add-hub-links" in sys.argv
    inbox_flag = "--inbox" in sys.argv
    add_people_flag = "--add-people" in sys.argv

    if add_hub_links_flag:
        # No API calls — skip key check
        count = add_hub_links()
        print(f"\nDone. Added hub_note to {count} notes.")
        return

    if not ANTHROPIC_API_KEY:
        print("❌ ANTHROPIC_API_KEY not set. Run: export ANTHROPIC_API_KEY=your-key")
        return

    if add_people_flag:
        count = add_people()
        print(f"\nDone. Added people to {count} notes.")
        return

    if inbox_flag:
        exclude = ""
        for i, arg in enumerate(sys.argv):
            if arg == "--exclude" and i + 1 < len(sys.argv):
                exclude = sys.argv[i + 1]
                break
        count = enrich_inbox(exclude_pattern=exclude)
        print(f"\nDone. Enriched {count} inbox notes.")
        return

    notes_path = Path(NOTES_FOLDER)
    if not notes_path.exists():
        print(f"❌ Notes folder not found: {NOTES_FOLDER}")
        return

    md_files = sorted(notes_path.glob("*.md"))

    if re_enrich_internal:
        targets = []
        for f in md_files:
            text = f.read_text(encoding="utf-8")
            if 'client: "Internal"' in text:
                targets.append((f, text))
        print(f"Found {len(targets)} notes tagged 'Internal' to re-enrich\n")
        count = sum(1 for f, text in targets if re_enrich_note(f, text))
        print(f"\nDone. Re-enriched {count} notes.")
    else:
        unenriched = []
        for f in md_files:
            text = f.read_text(encoding="utf-8")
            if "enriched: true" not in text:
                unenriched.append((f, text))
        print(f"Found {len(unenriched)} unenriched notes out of {len(md_files)} total\n")
        if not unenriched:
            print("Nothing to do — all notes already enriched.")
            return
        enriched_count = sum(1 for f, text in unenriched if enrich_note(f, text))
        print(f"\nDone. Enriched {enriched_count} notes.")


if __name__ == "__main__":
    main()
