# scanner.py
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

from classifier import classify_file, is_twb_folder, Disposition


@dataclass
class FileEntry:
    path: Path
    relative_path: str  # relative to client folder, always forward slashes
    disposition: Disposition
    note_label: str = None


@dataclass
class ClientInventory:
    client_name: str
    client_dir: Path
    files: List[FileEntry] = field(default_factory=list)


def scan_source(config) -> List[ClientInventory]:
    inventories = []
    for client_dir in sorted(config.source_dir.iterdir()):
        if client_dir.is_dir():
            inventories.append(scan_client_folder(client_dir, config))
    return inventories


def scan_client_folder(client_dir: Path, config) -> ClientInventory:
    inventory = ClientInventory(client_name=client_dir.name, client_dir=client_dir)
    _walk(client_dir, client_dir, inventory, config)
    return inventory


def _walk(base: Path, current: Path, inventory: ClientInventory, config):
    for item in sorted(current.iterdir()):
        if item.is_dir():
            if is_twb_folder(item.name):
                for f in item.rglob("*"):
                    if f.is_file():
                        rel = f.relative_to(base).as_posix()
                        inventory.files.append(
                            FileEntry(path=f, relative_path=rel, disposition=Disposition.TRASH)
                        )
            else:
                _walk(base, item, inventory, config)
        elif item.is_file():
            rel = item.relative_to(base).as_posix()
            disposition, note_label = classify_file(item, config.file_rules)
            inventory.files.append(
                FileEntry(path=item, relative_path=rel, disposition=disposition, note_label=note_label)
            )
