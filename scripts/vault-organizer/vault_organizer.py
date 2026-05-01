#!/usr/bin/env python3
"""
vault_organizer.py — Main entrypoint for the vault organizer.

Classifies and moves misplaced notes to their correct vault folders.

Usage:
    python vault_organizer.py --config config.yaml
    python vault_organizer.py --config config.yaml --dry-run

Requires:
    1. scripts/config.py with VAULT_PATH set
    2. vault-organizer/config.yaml with entity mappings and folder rules
       (copy from config.example.yaml and fill in your values)
"""

import sys
from pathlib import Path
import yaml
import click

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from config import VAULT_PATH
except ImportError:
    sys.exit(
        "Error: scripts/config.py not found.\n"
        "Copy scripts/config.example.py to scripts/config.py and fill in VAULT_PATH."
    )

from checkpoint import Checkpoint
from classifier import classify_file, Disposition
from entity_mapper import resolve_destination
from mover import move_file
from hub_updater import update_hub_links


@click.command()
@click.option("--config", "config_path", default="config.yaml",
              help="Path to config.yaml (default: config.yaml in this directory)")
@click.option("--dry-run", is_flag=True, default=False,
              help="Preview actions without moving files")
def main(config_path: str, dry_run: bool) -> None:
    config_file = Path(config_path)
    if not config_file.is_absolute():
        config_file = Path(__file__).parent / config_file

    if not config_file.exists():
        sys.exit(
            f"Config file not found: {config_file}\n"
            "Copy config.example.yaml to config.yaml and fill in your values."
        )

    with open(config_file) as f:
        config = yaml.safe_load(f)

    dry_run = dry_run or config.get("dry_run", False)
    source_dir = Path(config["source_dir"])
    output_dir = Path(config["output_dir"])
    checkpoint = Checkpoint(source_dir / ".organizer-checkpoint.json")

    if not source_dir.exists():
        sys.exit(f"Source directory does not exist: {source_dir}")

    moved = 0
    skipped = 0
    errors = 0

    for note_path in sorted(source_dir.rglob("*.md")):
        if checkpoint.already_processed(note_path):
            skipped += 1
            continue

        try:
            fm = _read_frontmatter(note_path)
            entity = fm.get("client") or fm.get("project") or fm.get("entity")
            destination = resolve_destination(entity, config)
            dest_folder = output_dir / destination.notes_path
            dest_path = dest_folder / note_path.name

            if dry_run:
                print(f"[DRY RUN] {note_path.name} → {destination.notes_path}/")
            else:
                dest_folder.mkdir(parents=True, exist_ok=True)
                move_file(note_path, dest_path)
                checkpoint.mark_processed(note_path)
                moved += 1
        except Exception as exc:
            print(f"Error processing {note_path.name}: {exc}", file=sys.stderr)
            errors += 1

    if not dry_run:
        checkpoint.save()

    print(f"\nDone. Moved: {moved}, Skipped: {skipped}, Errors: {errors}")
    if dry_run:
        print("(dry run — no files moved)")


def _read_frontmatter(path: Path) -> dict:
    import frontmatter
    post = frontmatter.load(str(path))
    return dict(post.metadata)


if __name__ == "__main__":
    main()
