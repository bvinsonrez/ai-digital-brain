import sys
from pathlib import Path
from datetime import date

# Import user-configured vault path from root config
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from config import VAULT_PATH as _vault_root
except ImportError:
    raise RuntimeError(
        "scripts/config.py not found. "
        "Copy scripts/config.example.py to scripts/config.py and fill in VAULT_PATH."
    )

VAULT_ROOT = Path(_vault_root)

# Adjust these folder paths to match your vault variant.
# For the consulting vault: use Clients/, Meetings/Notes, Opportunities/
# For the general vault: use Projects/, Meetings/Notes/
MEETINGS_DIR = VAULT_ROOT / "Meetings" / "Notes"      # update to your actual meetings folder
INBOX_DIR = VAULT_ROOT / "Inbox"

# Stale thresholds in days
STALE_ACTIVE_DAYS = 30
STALE_HUB_DAYS = 90

# How long an unenriched note is tolerated before flagging
UNENRICHED_GRACE_HOURS = 24

# Required frontmatter fields per note type
REQUIRED_FIELDS = {
    "hub": ["type", "status", "created", "last_reviewed"],
    "meeting-note": ["type", "date", "created"],
    "literature-note": ["type", "source", "created"],
}

ALLOWED_HUB_STATUSES = {"active", "on-hold", "complete", "archive"}


def audit_report_path() -> Path:
    today = date.today().isoformat()
    return INBOX_DIR / f"vault-audit-{today}.md"
