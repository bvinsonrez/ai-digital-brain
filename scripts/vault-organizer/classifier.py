# classifier.py
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import anthropic

from frontmatter_utils import read_note

_CLASSIFY_PROMPT = """\
You are classifying a meeting note from a consulting firm's Obsidian vault.

Note title: {title}
Note content:
---
{content}
---

Attendees: {attendees}
Existing client tag: {existing_client}

Known clients and prospects (use exact spelling if matched):
{client_list}

Classify this note. Respond with ONLY these fields, one per line, no extra text:

client: [exact client name from the known list, OR infer from content, OR "Internal" if purely internal, OR "Personal" if personal/non-work]
meeting_type: [Stand-up | Check-in | Discovery | Kickoff | Planning | Review | 1:1 | Pipeline | Strategy | Training | Other]
vertical: [category that best fits the organization, e.g. Healthcare | Financial Services | Internal | Personal | Other]
opportunity: [deal/project name if mentioned, else leave blank]
summary: [one sentence describing what this meeting was about]
clean_title: [a clean, descriptive title for this note, e.g. "AcmeCorp Sprint Review - 2024-01-15". Include date if inferrable from content or title. Leave blank if the existing title is already clean and not "Untitled".]
"""

# Populate _KNOWN_CLIENTS from entity_folder_map in config at runtime.
# This list is intentionally empty — users configure their own entities in config.yaml.
_KNOWN_CLIENTS: list[str] = []


@dataclass
class ClassificationResult:
    client: Optional[str]
    meeting_type: Optional[str]
    vertical: Optional[str]
    opportunity: Optional[str]
    summary: Optional[str]
    clean_title: Optional[str]   # None means "keep existing filename"


def classify_note(note_path: Path, config: dict) -> ClassificationResult:
    """
    Return classification for a note.

    - If enriched=true AND title is not "Untitled": return existing frontmatter values, no API call.
    - If enriched=true AND title starts with "Untitled": call API only for clean_title, keep other existing fields.
    - Otherwise: full API classification.
    """
    meta, content = read_note(note_path)
    title = meta.get("title", note_path.stem)
    is_untitled = str(title).startswith("Untitled Granola Note")
    is_enriched = meta.get("enriched") is True

    if is_enriched and not is_untitled:
        return ClassificationResult(
            client=meta.get("client"),
            meeting_type=meta.get("meeting_type"),
            vertical=meta.get("vertical"),
            opportunity=meta.get("opportunity"),
            summary=meta.get("summary"),
            clean_title=None,
        )

    # Call API — for enriched+untitled, we only need clean_title but run full prompt
    # and selectively use the result.
    raw = _call_claude(title, content, meta, config)
    parsed = _parse_response(raw)

    if is_enriched and is_untitled:
        # Keep all existing enriched fields; only take clean_title from API
        return ClassificationResult(
            client=meta.get("client"),
            meeting_type=meta.get("meeting_type"),
            vertical=meta.get("vertical"),
            opportunity=meta.get("opportunity"),
            summary=meta.get("summary"),
            clean_title=parsed.get("clean_title") or None,
        )

    return ClassificationResult(
        client=parsed.get("client") or meta.get("client"),
        meeting_type=parsed.get("meeting_type"),
        vertical=parsed.get("vertical"),
        opportunity=parsed.get("opportunity"),
        summary=parsed.get("summary"),
        clean_title=parsed.get("clean_title") or None,
    )


def _call_claude(title: str, content: str, meta: dict, config: dict) -> str:
    client = anthropic.Anthropic()
    attendees = ", ".join(meta.get("attendees") or []) or "unknown"
    existing_client = meta.get("client") or "none"
    # Build entity list from config; fall back to module-level list if not configured
    known = list(config.get("entity_folder_map", {}).keys()) or _KNOWN_CLIENTS
    client_list = "\n".join(f"- {c}" for c in known)

    prompt = _CLASSIFY_PROMPT.format(
        title=title,
        content=content[:4000],
        attendees=attendees,
        existing_client=existing_client,
        client_list=client_list,
    )

    msg = client.messages.create(
        model=config["claude"]["model"],
        max_tokens=config["claude"]["max_tokens"],
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def _parse_response(text: str) -> dict:
    """Parse "key: value" lines into a dict. Blank values become None."""
    result = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip() or None
    return result
