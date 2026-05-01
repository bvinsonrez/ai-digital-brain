# checkpoint.py
import json
from datetime import datetime
from pathlib import Path

_FILENAME = ".vault-organizer-state.json"


class CheckpointManager:
    def __init__(self, vault_dir: str):
        self._path = Path(vault_dir) / _FILENAME
        self.state = {
            "started_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "completed_notes": [],
            "skipped_notes": [],
            "errored_notes": [],
            "in_progress_note": None,
        }

    def load(self) -> bool:
        if not self._path.exists():
            return False
        with open(self._path) as f:
            self.state = json.load(f)
        return True

    def is_completed(self, note_stem: str) -> bool:
        return note_stem in self.state["completed_notes"]

    def mark_in_progress(self, note_stem: str):
        self.state["in_progress_note"] = note_stem
        self._save()

    def mark_completed(self, note_stem: str):
        if note_stem not in self.state["completed_notes"]:
            self.state["completed_notes"].append(note_stem)
        self.state["in_progress_note"] = None
        self.state["last_updated"] = datetime.now().isoformat()
        self._save()

    def mark_errored(self, note_stem: str):
        if note_stem not in self.state["errored_notes"]:
            self.state["errored_notes"].append(note_stem)
        self.state["in_progress_note"] = None
        self._save()

    @property
    def completed_count(self) -> int:
        return len(self.state["completed_notes"])

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self.state, f, indent=2)
