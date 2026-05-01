# vault_maintenance/checks/unenriched.py
from pathlib import Path
from datetime import datetime, timezone
from typing import NamedTuple
import frontmatter

from vault_maintenance.config import MEETINGS_DIR, UNENRICHED_GRACE_HOURS


class UnenrichedFinding(NamedTuple):
    path: Path
    created: str
    hours_old: float


def run() -> list[UnenrichedFinding]:
    findings = []
    now = datetime.now(tz=timezone.utc)

    for note in MEETINGS_DIR.glob("*.md"):
        try:
            post = frontmatter.load(note)
        except Exception:
            continue

        if post.metadata.get("enriched") is True:
            continue

        created_raw = post.metadata.get("created")
        if not created_raw:
            continue

        try:
            if isinstance(created_raw, datetime):
                created = created_raw
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
            else:
                created = datetime.fromisoformat(str(created_raw))
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue

        hours_old = (now - created).total_seconds() / 3600
        if hours_old > UNENRICHED_GRACE_HOURS:
            findings.append(UnenrichedFinding(
                path=note,
                created=str(created_raw),
                hours_old=round(hours_old, 1),
            ))

    return findings
