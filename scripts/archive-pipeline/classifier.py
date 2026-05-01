# classifier.py
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple


class Disposition(Enum):
    CONVERT = "convert"
    NOTE_TRASH = "note_trash"
    TRASH = "trash"


_NOTE_TRASH_LABELS = {
    "twb": "Tableau analytics work",
    "twbx": "Tableau analytics work",
    "yxmd": "Alteryx workflow",
    "yxmc": "Alteryx workflow",
    "yxzp": "Alteryx workflow",
    "key": "Keynote presentation",
    "csv": "Data file",
}


def is_twb_folder(folder_name: str) -> bool:
    return folder_name.endswith(".twb Files")


def classify_file(path: Path, file_rules) -> Tuple[Disposition, Optional[str]]:
    ext = path.suffix.lstrip(".").lower()
    if ext in file_rules.convert:
        return Disposition.CONVERT, None
    if ext in file_rules.note_trash:
        return Disposition.NOTE_TRASH, _NOTE_TRASH_LABELS.get(ext, "Legacy file")
    return Disposition.TRASH, None
