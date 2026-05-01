#!/usr/bin/env python3
"""
add_people_links.py — backfill [[People/Name]] body wikilinks into 1-1 / check-in meeting notes.

Usage:
    python3 add_people_links.py --dry-run   # preview only
    python3 add_people_links.py             # apply changes
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
try:
    from config import VAULT_PATH
except ImportError:
    sys.exit(
        "Error: scripts/config.py not found.\n"
        "Copy scripts/config.example.py to scripts/config.py and fill in VAULT_PATH."
    )

VAULT = Path(VAULT_PATH)

# Update these to match your vault structure and meeting note locations.
MEETING_FOLDERS = [
    VAULT / "Meetings" / "Notes",
]

# Add entries here to map meeting note filename stems to People/ note paths.
# Example: "1-1 with alice": "People/Alice Johnson"
EXACT_MAP: dict[str, str] = {}


def add_people_link(filepath: Path, people_path: str, dry_run: bool = False) -> str:
    """
    Add [[People/Name]] to note body.
    Returns: 'added' | 'exists' | 'error'
    """
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return f"error: {e}"

    link = f"[[{people_path}]]"

    if link in content:
        return "exists"

    # Split frontmatter from body
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = "---" + parts[1] + "---"
            body = parts[2]
        else:
            fm = ""
            body = content
    else:
        fm = ""
        body = content

    # Append to existing ## Links section, or create one
    if "## Links" in body:
        new_body = body.rstrip() + f"\n- {link}\n"
    else:
        new_body = body.rstrip() + f"\n\n## Links\n\n- {link}\n"

    new_content = (fm + new_body) if fm else new_body

    if not dry_run:
        filepath.write_text(new_content, encoding="utf-8")

    return "added"


def main(dry_run: bool = False) -> None:
    if dry_run:
        print("=== DRY RUN — no files will be modified ===\n")

    added = skipped = missing = 0

    for stem, people_path in sorted(EXACT_MAP.items(), key=lambda x: x[1] + x[0]):
        resolved = None
        for folder in MEETING_FOLDERS:
            candidate = folder / f"{stem}.md"
            if candidate.exists():
                resolved = candidate
                break

        if resolved is None:
            print(f"  ❌ NOT FOUND: {stem}.md")
            missing += 1
            continue

        result = add_people_link(resolved, people_path, dry_run)
        short_folder = "Granola" if "Granola" in str(resolved) else "Internal"

        if result == "added":
            tag = "DRY" if dry_run else "  ✅"
            print(f"{tag} [{short_folder}] {resolved.name} → [[{people_path}]]")
            added += 1
        elif result == "exists":
            print(f"  ── [{short_folder}] {resolved.name} already linked")
            skipped += 1
        else:
            print(f"  ⚠️  [{short_folder}] {resolved.name} — {result}")

    print(f"\n{'DRY RUN ' if dry_run else ''}Done. Added: {added}, Already linked: {skipped}, Not found: {missing}")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
