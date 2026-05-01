# vault_maintenance/fixers/inbox_cleanup.py
import shutil
from datetime import date
from pathlib import Path
from typing import NamedTuple

from vault_maintenance.config import INBOX_DIR, VAULT_ROOT

# Archive destination for old vault audit reports.
# Update to match your vault's archive folder structure.
VAULT_AUDITS_DIR = VAULT_ROOT / "Archive" / "VaultAudits"

# Archive destination for cc-sessions files (Claude Code session logs).
# Update or remove if your vault doesn't use this pattern.
SESSIONS_ARCHIVE_DIR = VAULT_ROOT / "Archive" / "Sessions"


class CleanupResult(NamedTuple):
    moved: list[tuple[Path, Path]]  # (source, dest)
    skipped: list[Path]


def _current_week_string() -> str:
    iso = date.today().isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def run(apply: bool = True) -> CleanupResult:
    moved = []
    skipped = []
    current_week = _current_week_string()

    # Vault audit files — keep the most recent, archive the rest
    audit_files = sorted(INBOX_DIR.glob("vault-audit-*.md"))
    for f in audit_files[:-1]:
        dest = VAULT_AUDITS_DIR / f.name
        if apply:
            VAULT_AUDITS_DIR.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(dest))
        moved.append((f, dest))

    # cc-sessions files — archive any week older than current
    for f in sorted(INBOX_DIR.glob("cc-sessions-*.md")):
        week = f.stem.replace("cc-sessions-", "")  # e.g. 2026-W17
        if week < current_week:
            dest = SESSIONS_ARCHIVE_DIR / f.name
            if apply:
                SESSIONS_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(dest))
            moved.append((f, dest))
        else:
            skipped.append(f)

    return CleanupResult(moved=moved, skipped=skipped)
