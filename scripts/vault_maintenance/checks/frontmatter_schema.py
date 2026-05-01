# vault_maintenance/checks/frontmatter_schema.py
from pathlib import Path
from typing import NamedTuple
import frontmatter

from vault_maintenance.config import (
    VAULT_ROOT, MEETINGS_DIR,
    REQUIRED_FIELDS, ALLOWED_HUB_STATUSES,
)

# Hub folder and glob pattern — update to match your vault structure.
# Example: VAULT_ROOT / "Clients" with glob "*/* — Hub.md" for consulting vaults.
# Example: VAULT_ROOT / "Projects" with glob "*/Hub.md" for general vaults.
HUBS_DIR = VAULT_ROOT / "Clients"
HUB_GLOB = "*/* — Hub.md"


class SchemaFinding(NamedTuple):
    path: Path
    note_type: str
    missing_fields: list[str]
    invalid_values: list[str]


def run() -> list[SchemaFinding]:
    findings = []

    # Hub notes
    if HUBS_DIR.exists():
        for hub in HUBS_DIR.glob(HUB_GLOB):
            findings.extend(_check_note(hub, "hub"))

    # Meeting notes
    for note in MEETINGS_DIR.glob("*.md"):
        findings.extend(_check_note(note, "meeting-note"))

    return findings


def _check_note(path: Path, note_type: str) -> list[SchemaFinding]:
    try:
        post = frontmatter.load(path)
    except Exception:
        return [SchemaFinding(path, note_type, ["(could not parse frontmatter)"], [])]

    required = REQUIRED_FIELDS.get(note_type, [])
    missing = [f for f in required if f not in post.metadata]
    invalid = []

    if note_type == "hub":
        status = post.metadata.get("status")
        if status and status not in ALLOWED_HUB_STATUSES:
            invalid.append(f"status: '{status}' not in {ALLOWED_HUB_STATUSES}")

    if missing or invalid:
        return [SchemaFinding(path, note_type, missing, invalid)]
    return []
