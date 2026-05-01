# publisher.py
from pathlib import Path
import send2trash


def write_md(content: str, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def trash_file(path: Path, dry_run: bool = False):
    if dry_run:
        return
    try:
        send2trash.send2trash(str(path))
    except Exception as exc:
        print(f"  WARNING: could not trash {path}: {exc}")
