# vault_maintenance/checks/dataview_mismatch.py
# Checks that hub notes' frontmatter `client` field matches the value used in
# any Dataview WHERE clauses inside the same file.
# Only relevant if your vault uses a hub-notes folder with Dataview queries.
# If your vault doesn't use this pattern, this check will return no findings.
import re
from pathlib import Path
from typing import NamedTuple
import frontmatter

from vault_maintenance.config import VAULT_ROOT

# Matches: WHERE client = "SomeName" (with optional OR clauses)
DATAVIEW_CLIENT_RE = re.compile(r'WHERE\s+client\s*=\s*"([^"]+)"', re.IGNORECASE)

# Hub glob pattern — update to match your vault's hub note naming convention.
# Example: "*/* — Hub.md" for consulting vaults, "*/Hub.md" for general vaults.
HUB_GLOB = "*/* — Hub.md"

# Folder containing entity/project hub notes (relative to VAULT_ROOT).
# Update to match your vault structure, e.g. "Clients", "Projects", "Areas".
HUBS_DIR = VAULT_ROOT / "Clients"


class DataviewMismatchFinding(NamedTuple):
    path: Path
    frontmatter_client: str
    query_clients: list[str]    # all client values found in Dataview blocks


def run() -> list[DataviewMismatchFinding]:
    findings = []

    if not HUBS_DIR.exists():
        return findings

    for hub in HUBS_DIR.glob(HUB_GLOB):
        try:
            post = frontmatter.load(hub)
            content = hub.read_text(encoding="utf-8")
        except Exception:
            continue

        fm_client = post.metadata.get("client", "")
        if not fm_client:
            continue

        query_clients = DATAVIEW_CLIENT_RE.findall(content)
        if not query_clients:
            continue

        # Flag if frontmatter client doesn't appear anywhere in the query clients list
        if fm_client not in query_clients:
            findings.append(DataviewMismatchFinding(
                path=hub,
                frontmatter_client=fm_client,
                query_clients=list(set(query_clients)),
            ))

    return findings
