# checkpoint.py
import json
from datetime import datetime
from pathlib import Path

_FILENAME = ".pipeline-state.json"


class CheckpointManager:
    def __init__(self, output_dir: Path, source_dir: Path):
        self._path = output_dir / _FILENAME
        self.state = {
            "source_dir": str(source_dir),
            "started_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "completed_clients": [],
            "skipped_clients": [],
            "errored_clients": [],
            "in_progress_client": None,
        }

    def load(self) -> bool:
        if not self._path.exists():
            return False
        with open(self._path) as f:
            self.state = json.load(f)
        return True

    def is_completed(self, client_name: str) -> bool:
        return client_name in self.state["completed_clients"]

    def mark_in_progress(self, client_name: str):
        self.state["in_progress_client"] = client_name
        self._save()

    def mark_completed(self, client_name: str):
        if client_name not in self.state["completed_clients"]:
            self.state["completed_clients"].append(client_name)
        self.state["in_progress_client"] = None
        self.state["last_updated"] = datetime.now().isoformat()
        self._save()

    def mark_errored(self, client_name: str):
        if client_name not in self.state["errored_clients"]:
            self.state["errored_clients"].append(client_name)
        self.state["in_progress_client"] = None
        self._save()

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self.state, f, indent=2)
