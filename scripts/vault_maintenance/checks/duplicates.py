# vault_maintenance/checks/duplicates.py
from pathlib import Path
from collections import defaultdict
from typing import NamedTuple
import frontmatter

from vault_maintenance.config import MEETINGS_DIR


class DuplicateFinding(NamedTuple):
    granola_id: str
    paths: list[Path]


def run() -> list[DuplicateFinding]:
    id_map: dict[str, list[Path]] = defaultdict(list)

    for note in MEETINGS_DIR.glob("*.md"):
        try:
            post = frontmatter.load(note)
        except Exception:
            continue
        granola_id = post.metadata.get("granola_id")
        if granola_id:
            id_map[granola_id].append(note)

    return [
        DuplicateFinding(granola_id=gid, paths=paths)
        for gid, paths in id_map.items()
        if len(paths) > 1
    ]
