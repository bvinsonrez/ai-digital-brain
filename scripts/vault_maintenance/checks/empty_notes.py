# vault_maintenance/checks/empty_notes.py
from pathlib import Path
from typing import NamedTuple

from vault_maintenance.config import VAULT_ROOT, MEETINGS_DIR


class EmptyNoteFinding(NamedTuple):
    path: Path
    folder: str   # human-readable folder label for the report


def _all_meeting_note_folders() -> list[tuple[Path, str]]:
    """Return (folder_path, label) pairs covering all meeting note locations.

    Extend this list to cover additional meeting note folders in your vault.
    The default includes only the primary MEETINGS_DIR from config.py.
    """
    folders = [
        (MEETINGS_DIR, str(MEETINGS_DIR.relative_to(VAULT_ROOT))),
    ]
    return folders


def run() -> list[EmptyNoteFinding]:
    findings = []
    for folder, label in _all_meeting_note_folders():
        if not folder.exists():
            continue
        for note in sorted(folder.glob("*.md")):
            if note.stat().st_size == 0:
                findings.append(EmptyNoteFinding(path=note, folder=label))
    return findings
