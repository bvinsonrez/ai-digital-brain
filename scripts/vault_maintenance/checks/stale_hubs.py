# vault_maintenance/checks/stale_hubs.py
from pathlib import Path
from datetime import date, datetime
from typing import NamedTuple
import frontmatter

from vault_maintenance.config import (
    VAULT_ROOT, STALE_ACTIVE_DAYS, STALE_HUB_DAYS,
)

# Folder containing hub notes — update to match your vault structure.
# Example: VAULT_ROOT / "Clients" for consulting vaults,
#          VAULT_ROOT / "Projects" for general vaults.
HUBS_DIR = VAULT_ROOT / "Clients"


class StaleHubFinding(NamedTuple):
    path: Path
    hub_name: str
    last_reviewed: str      # raw value from frontmatter, or "(missing)"
    days_since_review: int  # -1 if unparseable
    status: str


class MissingHubFinding(NamedTuple):
    folder: Path


def run() -> tuple[list[StaleHubFinding], list[MissingHubFinding]]:
    stale = []
    missing = []
    today = date.today()

    if not HUBS_DIR.exists():
        return stale, missing

    for hub_folder in HUBS_DIR.iterdir():
        if not hub_folder.is_dir():
            continue

        hubs = list(hub_folder.glob("* — Hub.md"))
        if not hubs:
            missing.append(MissingHubFinding(folder=hub_folder))
            continue

        hub = hubs[0]
        try:
            post = frontmatter.load(hub)
        except Exception:
            stale.append(StaleHubFinding(hub, hub_folder.name, "(parse error)", -1, "unknown"))
            continue

        last_reviewed_raw = post.metadata.get("last_reviewed", "(missing)")
        status = post.metadata.get("status", "unknown")
        # Use STALE_HUB_DAYS for on-hold/archived hubs, STALE_ACTIVE_DAYS for active ones
        threshold = STALE_HUB_DAYS if status in {"on-hold", "archive"} else STALE_ACTIVE_DAYS

        if last_reviewed_raw == "(missing)":
            stale.append(StaleHubFinding(hub, hub_folder.name, "(missing)", -1, status))
            continue

        try:
            if isinstance(last_reviewed_raw, datetime):
                last_reviewed = last_reviewed_raw.date()
            elif isinstance(last_reviewed_raw, date):
                last_reviewed = last_reviewed_raw
            else:
                last_reviewed = datetime.strptime(str(last_reviewed_raw), "%Y-%m-%d").date()
            days_since = (today - last_reviewed).days
        except ValueError:
            stale.append(StaleHubFinding(hub, hub_folder.name, str(last_reviewed_raw), -1, status))
            continue

        if days_since > threshold:
            stale.append(StaleHubFinding(hub, hub_folder.name, str(last_reviewed_raw), days_since, status))

    return stale, missing
