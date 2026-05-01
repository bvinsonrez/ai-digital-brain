# vault_maintenance/checks/orphans.py
import re
from pathlib import Path
from typing import NamedTuple
import frontmatter

from vault_maintenance.config import VAULT_ROOT, MEETINGS_DIR

WIKILINK_RE = re.compile(r'\[\[([^\]|#]+)')


class OrphanFinding(NamedTuple):
    path: Path


def _is_dataview_connected(note: Path) -> bool:
    """Enriched notes with a client field are connected to hub Dataview queries — not truly orphaned."""
    try:
        post = frontmatter.load(note)
        return bool(post.metadata.get("enriched")) and bool(post.metadata.get("client"))
    except Exception:
        return False


def run() -> list[OrphanFinding]:
    # Build inbound link map: target_stem -> set of source paths
    inbound: dict[str, set[Path]] = {}

    for md_file in VAULT_ROOT.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue
        for match in WIKILINK_RE.finditer(content):
            target = match.group(1).strip()
            # Normalize: strip path prefix if present, use stem
            target_stem = Path(target).stem
            inbound.setdefault(target_stem, set()).add(md_file)

    orphans = []
    for note in MEETINGS_DIR.glob("*.md"):
        stem = note.stem
        if stem not in inbound or not inbound[stem]:
            if not _is_dataview_connected(note):
                orphans.append(OrphanFinding(path=note))

    return orphans
