# mover.py
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from frontmatter_utils import read_note, write_note


@dataclass
class MoveResult:
    note_path: Path
    transcript_path: Optional[Path]
    dry_run: bool


def move_note_pair(
    note_path: Path,
    target_base: str,   # vault-relative, e.g. "Clients/AcmeCorp/Meetings"
    config: dict,
    clean_title: Optional[str] = None,
) -> MoveResult:
    """
    Move a note (and its paired transcript) to the target directory.

    - Creates target dirs as needed.
    - Updates note frontmatter `transcript` link with new path.
    - Updates transcript frontmatter `note` link with new path.
    - If clean_title is provided and the note filename starts with "Untitled",
      renames the file to "{clean_title}.md".
    - In dry_run mode: logs operations but does not touch the filesystem.
    """
    vault_dir = Path(config["vault_dir"])
    dry_run = config.get("dry_run", False)

    # Determine output filename
    if clean_title and note_path.stem.startswith("Untitled"):
        # Sanitize the clean title for use as a filename
        safe_name = re.sub(r'[\\/:*?"<>|]', "-", clean_title)
        new_note_filename = f"{safe_name}.md"
    else:
        new_note_filename = note_path.name

    notes_dir = vault_dir / target_base / "Notes"
    transcripts_dir = vault_dir / target_base / "Transcripts"
    new_note_path = notes_dir / new_note_filename

    # Determine transcript source path
    transcript_source = _find_transcript(note_path, config)

    if dry_run:
        print(f"  [DRY RUN] would move note:       {note_path} → {new_note_path}")
        if transcript_source:
            new_t_name = _transcript_name(new_note_filename)
            print(f"  [DRY RUN] would move transcript: {transcript_source} → {transcripts_dir / new_t_name}")
        return MoveResult(note_path=new_note_path, transcript_path=None, dry_run=True)

    # Create target dirs
    notes_dir.mkdir(parents=True, exist_ok=True)

    # Read note frontmatter before moving
    meta, content = read_note(note_path)

    # Move transcript (if it exists)
    new_transcript_path = None
    if transcript_source and transcript_source.exists():
        transcripts_dir.mkdir(parents=True, exist_ok=True)
        new_t_name = _transcript_name(new_note_filename)
        new_transcript_path = transcripts_dir / new_t_name

        # Update transcript frontmatter before moving
        t_meta, t_content = read_note(transcript_source)
        new_note_vault_rel = str(new_note_path.relative_to(vault_dir))
        t_meta["note"] = f"[[{new_note_vault_rel}]]"
        write_note(transcript_source, t_meta, t_content)

        shutil.move(str(transcript_source), str(new_transcript_path))

    # Update note's transcript link
    if new_transcript_path:
        new_t_vault_rel = str(new_transcript_path.relative_to(vault_dir))
        meta["transcript"] = f"[[{new_t_vault_rel}]]"
    if clean_title and note_path.stem.startswith("Untitled"):
        meta["title"] = clean_title
    write_note(note_path, meta, content)

    shutil.move(str(note_path), str(new_note_path))

    return MoveResult(note_path=new_note_path, transcript_path=new_transcript_path, dry_run=False)


def _find_transcript(note_path: Path, config: dict) -> Optional[Path]:
    """
    Find the paired transcript for a note.
    First checks the `transcript` frontmatter field, then falls back to filename convention.
    Returns the Path if found, else None.
    """
    vault_dir = Path(config["vault_dir"])

    try:
        meta, _ = read_note(note_path)
        transcript_link = meta.get("transcript", "")
        if transcript_link:
            # Extract path from "[[path/to/file.md]]"
            inner = str(transcript_link).strip().lstrip("[[").rstrip("]]")
            candidate = vault_dir / inner
            if candidate.exists():
                return candidate
    except Exception:
        pass

    # Fallback: filename convention — note "Foo.md" → transcript "Foo-transcript.md"
    transcripts_dir = vault_dir / config["transcripts_dir"]
    fallback = transcripts_dir / f"{note_path.stem}-transcript.md"
    return fallback if fallback.exists() else None


def _transcript_name(note_filename: str) -> str:
    """Given "AcmeCorp Standup.md", return "AcmeCorp Standup-transcript.md"."""
    stem = Path(note_filename).stem
    return f"{stem}-transcript.md"
