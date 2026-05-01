# vault_maintenance/report.py
from datetime import date
from pathlib import Path

from vault_maintenance.config import audit_report_path, VAULT_ROOT


def _rel(path: Path) -> str:
    """Return vault-relative path for readable output."""
    try:
        return str(path.relative_to(VAULT_ROOT))
    except ValueError:
        return str(path)


def build(
    stale_hubs,
    missing_hubs,
    schema_findings,
    orphans,
    dataview_mismatches,
    duplicates,
    unenriched,
    empty_notes=None,
) -> str:
    today = date.today().isoformat()
    sections = [f"# Vault Audit — {today}\n"]

    # --- Stale Hubs ---
    sections.append("## Stale Hub Notes\n")
    if stale_hubs:
        for f in stale_hubs:
            age = f"{f.days_since_review}d" if f.days_since_review >= 0 else "unknown age"
            hub_label = getattr(f, "hub_name", getattr(f, "client", f.path.stem))
            sections.append(f"- `{_rel(f.path)}` — last reviewed: {f.last_reviewed} ({age} ago, status: {f.status})")
    else:
        sections.append("_None_")
    sections.append("")

    # --- Missing Hubs ---
    sections.append("## Folders Missing Hub Notes\n")
    if missing_hubs:
        for f in missing_hubs:
            sections.append(f"- `{f.folder.name}/`")
    else:
        sections.append("_None_")
    sections.append("")

    # --- Schema Violations ---
    sections.append("## Frontmatter Schema Violations\n")
    if schema_findings:
        for f in schema_findings:
            issues = []
            if f.missing_fields:
                issues.append(f"missing: {', '.join(f.missing_fields)}")
            if f.invalid_values:
                issues.append(f"invalid: {'; '.join(f.invalid_values)}")
            sections.append(f"- `{_rel(f.path)}` — {' | '.join(issues)}")
    else:
        sections.append("_None_")
    sections.append("")

    # --- Dataview Mismatches ---
    sections.append("## Dataview Client Field Mismatches\n")
    if dataview_mismatches:
        for f in dataview_mismatches:
            sections.append(
                f"- `{_rel(f.path)}`\n"
                f"  - frontmatter client: `{f.frontmatter_client}`\n"
                f"  - query uses: {[f'`{c}`' for c in f.query_clients]}"
            )
    else:
        sections.append("_None_")
    sections.append("")

    # --- Orphans ---
    sections.append("## Orphaned Meeting Notes (no inbound links)\n")
    if orphans:
        for f in orphans:
            sections.append(f"- `{_rel(f.path)}`")
    else:
        sections.append("_None_")
    sections.append("")

    # --- Duplicates ---
    sections.append("## Duplicate Meeting Notes\n")
    if duplicates:
        for f in duplicates:
            sections.append(f"- granola_id: `{f.granola_id}`")
            for p in f.paths:
                sections.append(f"  - `{_rel(p)}`")
    else:
        sections.append("_None_")
    sections.append("")

    # --- Unenriched ---
    sections.append("## Unenriched Meeting Notes (>24h old)\n")
    if unenriched:
        for f in unenriched:
            sections.append(f"- `{_rel(f.path)}` — created: {f.created} ({f.hours_old}h ago)")
    else:
        sections.append("_None_")
    sections.append("")

    # --- Empty Notes ---
    sections.append("## Empty Meeting Note Files\n")
    sections.append("_Placeholder files (0 bytes) — no content synced. Fix: add content or delete._\n")
    if empty_notes:
        for f in empty_notes:
            sections.append(f"- `{_rel(f.path)}` — in `{f.folder}`")
    else:
        sections.append("_None_")
    sections.append("")

    return "\n".join(sections)


def write(content: str) -> Path:
    out = audit_report_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return out
