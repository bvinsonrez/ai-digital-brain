# synthesizer.py
from pathlib import Path
from typing import List, Optional, Tuple
import anthropic


_FILE_PROMPT = """\
You are analyzing a business document from a consulting firm's archive.

Client: {client_name}
File location: {relative_path}
File type: {file_type}
Subdirectory context: {subdir_context}

Document content:
---
{content}
---

Analyze this document. If it has no meaningful business content (contact list, \
data dump, empty file, or pure boilerplate), respond with exactly: SKIP

Otherwise respond in this exact format:

# {filename}
**Type:** [Proposal | SOW | Discovery | Pricing | Presentation | Transcript | Other]
**Date:** [date found in document, or "unknown"]
**Source:** {relative_path}

## Summary
[2-4 sentences describing what this document is and what it says]

## Key Details
- [bullet points: scope items, dollar amounts, technologies mentioned, people named, outcomes]

Do not include image placeholders, raw HTML, or conversion artifacts.\
"""

_CLIENT_PROMPT = """\
You are building a knowledge base entry for a consulting firm's client archive.

Client: {client_name}
{hints_section}
Document summaries:
---
{file_summaries}
---

Files noted but not converted: {noted_files}

Respond in this exact format:

# {client_name}
**Industry:** [inferred industry]
**Engagement Outcome:** [Won | Lost | Unknown]
**Approximate Value:** [dollar amount if found, or "unknown"]
**Primary Contact:** [name and title if found, or "unknown"]

## What We Did
[3-5 sentence narrative: what was the engagement, what was built or proposed, outcome]

## Category Tags
- Primary: [single best matching category from the hints, or "Other"]
- Secondary: [second category if applicable, or "None"]

## Technical Tags
- Platforms: [comma-separated platforms that appear in the documents, or "Unknown"]
- Service Areas: [comma-separated service areas that apply, or "Unknown"]

## Files Archived
{files_archived}
\
"""


def _build_hints_section(classification_hints: dict) -> str:
    """Format classification_hints dict into prompt context lines."""
    if not classification_hints:
        return ""
    lines = []
    for key, values in classification_hints.items():
        label = key.replace("_", " ").title()
        lines.append(f"{label}: {', '.join(values)}")
    return "\n".join(lines) + "\n\n"


def synthesize_file(
    content: str,
    client_name: str,
    relative_path: str,
    filename: str,
    config,
) -> Optional[str]:
    """Returns markdown string, or None if Claude signals SKIP."""
    client = anthropic.Anthropic()
    subdir = str(Path(relative_path).parent) if "/" in relative_path else ""
    file_type = Path(filename).suffix.lstrip(".").upper()

    prompt = _FILE_PROMPT.format(
        client_name=client_name,
        relative_path=relative_path,
        file_type=file_type,
        subdir_context=subdir or "(root)",
        content=content[:7995],  # cap to keep total prompt within ~8k token budget
        filename=filename,
    )

    msg = client.messages.create(
        model=config.claude.model,
        max_tokens=config.claude.max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )

    text = msg.content[0].text.strip()
    return None if text == "SKIP" else text


def synthesize_client(
    client_name: str,
    file_summaries: List[Tuple[str, str]],
    noted_files: List[Tuple[str, str]],
    config,
) -> str:
    """Build _client-summary.md content."""
    client = anthropic.Anthropic()

    summaries_text = "\n\n---\n\n".join(
        f"File: {fname}\n{md}" for fname, md in file_summaries
    ) or "(no converted files)"

    noted_text = ", ".join(
        f"{fname} ({label})" for fname, label in noted_files
    ) or "None"

    files_archived = "\n".join(
        f"- `{Path(fname).stem}-summary.md` — {fname}" for fname, _ in file_summaries
    )
    if noted_files:
        files_archived += f"\n- [files noted but not converted: {noted_text}]"
    if not files_archived:
        files_archived = "- (no files archived)"

    hints_section = _build_hints_section(config.classification_hints)

    prompt = _CLIENT_PROMPT.format(
        client_name=client_name,
        hints_section=hints_section,
        file_summaries=summaries_text,
        noted_files=noted_text,
        files_archived=files_archived,
    )

    msg = client.messages.create(
        model=config.claude.model,
        max_tokens=config.claude.max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )

    return msg.content[0].text.strip()
