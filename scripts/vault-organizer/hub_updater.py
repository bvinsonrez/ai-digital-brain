# hub_updater.py
"""
Rewrites Dataview FROM clauses in hub notes after migration.

Before: FROM "Meetings/Granola/Notes"
After:  FROM "Clients/AcmeCorp/Meetings/Notes"
"""
import re
from pathlib import Path

from entity_mapper import resolve_destination
from frontmatter_utils import read_note


def update_hub_notes(vault_dir_or_str, config: dict) -> None:
    """
    Scan all .md files in the vault. For any note with `type: client-hub`,
    rewrite Dataview FROM clauses that still point to Meetings/Granola paths.
    """
    vault_dir = Path(vault_dir_or_str)

    for md_file in vault_dir.rglob("*.md"):
        try:
            meta, _ = read_note(md_file)
        except Exception:
            continue

        if meta.get("type") != "client-hub":
            continue

        client = meta.get("client")
        if not client:
            continue

        dest = resolve_destination(client, config)
        new_notes_path = dest.notes_path

        _rewrite_from_clauses(md_file, new_notes_path)


def _rewrite_from_clauses(file_path: Path, new_notes_path: str) -> None:
    """
    Replace all occurrences of:
        FROM "Meetings/Granola/Notes"
    or
        FROM "Meetings/Granola"
    with:
        FROM "{new_notes_path}"

    If the file already contains the new path and no old paths, skip the write.
    """
    old_pattern = re.compile(r'FROM\s+"Meetings/Granola(?:/Notes)?"')
    replacement = f'FROM "{new_notes_path}"'

    content = file_path.read_text(encoding="utf-8")

    if not old_pattern.search(content):
        return  # nothing to change

    new_content = old_pattern.sub(replacement, content)

    if new_content != content:
        file_path.write_text(new_content, encoding="utf-8")
        print(f"  [hub_updater] updated: {file_path.name}")
