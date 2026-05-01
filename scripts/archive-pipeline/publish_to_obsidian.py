#!/usr/bin/env python3
"""
publish_to_obsidian.py
Copies archive pipeline output into the Obsidian vault.

- Reads _client-summary.md files from <archive-dir>/clients/
- Adds YAML frontmatter (type, client, industry, status, outcome, category tags, platforms, service_areas)
- Writes to <vault>/Archive/Clients/<ClientName>/__client-summary.md
- Copies knowledge bases to <vault>/Archive/Knowledge Bases/ with corrected wikilinks

Usage:
    python publish_to_obsidian.py --archive-dir /path/to/archive --vault /path/to/vault
    python publish_to_obsidian.py --archive-dir /path/to/archive --vault /path/to/vault --dry-run
"""

import argparse
import re
import sys
from pathlib import Path

VAULT_ARCHIVE_CLIENTS = "Archive/Clients"
VAULT_ARCHIVE_KB = "Archive/Knowledge Bases"


def _resolve_config_defaults():
    """Try to load path defaults from scripts/config.py if available."""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from config import VAULT_PATH, WORKSPACE_PATH  # noqa: F401
        return WORKSPACE_PATH, VAULT_PATH
    except (ImportError, AttributeError):
        return None, None


def parse_summary(text: str) -> dict:
    """Extract structured fields from a _client-summary.md."""
    result = {
        "client": "",
        "industry": "",
        "outcome": "",
        "approximate_value": "",
        "category_primary": "",
        "category_secondary": "",
        "platforms": [],
        "service_areas": [],
    }

    m = re.search(r'^# (.+)$', text, re.MULTILINE)
    if m:
        result["client"] = m.group(1).strip()

    for field, pattern in [
        ("industry", r'\*\*Industry:\*\* (.+)'),
        ("outcome", r'\*\*Engagement Outcome:\*\* (.+)'),
        ("approximate_value", r'\*\*Approximate Value:\*\* (.+)'),
        ("category_primary", r'- Primary: (.+)'),
        ("category_secondary", r'- Secondary: (.+)'),
    ]:
        m = re.search(pattern, text)
        if m:
            result[field] = m.group(1).strip()

    m = re.search(r'- Platforms: (.+)', text)
    if m:
        val = m.group(1).strip()
        if val.lower() != "unknown":
            result["platforms"] = [p.strip() for p in val.split(",") if p.strip()]

    m = re.search(r'- Service Areas: (.+)', text)
    if m:
        val = m.group(1).strip()
        if val.lower() != "unknown":
            result["service_areas"] = [a.strip() for a in val.split(",") if a.strip()]

    return result


def yaml_list(items: list) -> str:
    if not items:
        return "[]"
    escaped = [f'"{x}"' if "," in x or ":" in x else x for x in items]
    return "[" + ", ".join(escaped) + "]"


def yaml_str(value: str) -> str:
    if not value:
        return '""'
    # Quote if contains special chars
    if any(c in value for c in [':', '#', '[', ']', '{', '}', '&', '*', '!', '|', '>']):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return f'"{value}"'


def build_frontmatter(parsed: dict) -> str:
    lines = ["---"]
    lines.append("type: archive-summary")
    lines.append(f"client: {yaml_str(parsed['client'])}")
    lines.append(f"industry: {yaml_str(parsed['industry'])}")
    lines.append("status: Archived")
    lines.append(f"engagement_outcome: {yaml_str(parsed['outcome'])}")
    if parsed["category_primary"]:
        lines.append(f"category_primary: {yaml_str(parsed['category_primary'])}")
    if parsed["category_secondary"]:
        lines.append(f"category_secondary: {yaml_str(parsed['category_secondary'])}")
    if parsed["platforms"]:
        lines.append(f"platforms: {yaml_list(parsed['platforms'])}")
    if parsed["service_areas"]:
        lines.append(f"service_areas: {yaml_list(parsed['service_areas'])}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def _normalize(filename: str) -> str:
    """Normalize a filename for fuzzy matching: strip suffix/ext, lowercase, collapse whitespace."""
    name = re.sub(r'-summary\.md$', '', filename, flags=re.IGNORECASE)
    name = re.sub(r'\.[a-zA-Z0-9]+$', '', name)  # strip file extension
    name = name.replace('_', ' ').replace('-', ' ').lower()
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def inject_file_wikilinks(text: str, client_folder: str, actual_files: list) -> str:
    """Replace `filename-summary.md` backtick refs with wikilinks to actual vault files."""
    # Build lookup: normalized name → actual filename stem (no .md)
    lookup = {}
    for f in actual_files:
        stem = f[:-3] if f.endswith(".md") else f
        lookup[_normalize(f)] = stem

    def replace_match(m):
        ref = m.group(1)
        key = _normalize(ref)
        actual_stem = lookup.get(key)
        if actual_stem:
            return f"[[Archive/Clients/{client_folder}/{actual_stem}]]"
        # fallback: use ref as-is (strip .md)
        stem = ref[:-3] if ref.endswith(".md") else ref
        return f"[[Archive/Clients/{client_folder}/{stem}]]"

    return re.sub(r'`([^`]+-summary\.md)`', replace_match, text)


def fix_kb_wikilinks(text: str) -> str:
    """Replace [[clients/Name/_client-summary]] with [[Archive/Clients/Name/_client-summary]]."""
    return re.sub(
        r'\[\[clients/(.+?)/_client-summary\]\]',
        r'[[Archive/Clients/\1/__client-summary]]',
        text
    )


def publish(archive_dir: Path, vault_dir: Path, dry_run: bool):
    clients_src = archive_dir / "clients"
    kb_src = archive_dir / "knowledge-bases"
    clients_dst = vault_dir / VAULT_ARCHIVE_CLIENTS
    kb_dst = vault_dir / VAULT_ARCHIVE_KB

    client_dirs = sorted([d for d in clients_src.iterdir() if d.is_dir()])
    print(f"Found {len(client_dirs)} client folders in archive.")

    published = 0
    skipped = 0

    for client_dir in client_dirs:
        summary_path = client_dir / "_client-summary.md"
        if not summary_path.exists():
            print(f"  SKIP (no summary): {client_dir.name}")
            skipped += 1
            continue

        text = summary_path.read_text(encoding="utf-8")
        parsed = parse_summary(text)

        if not parsed["client"]:
            print(f"  SKIP (could not parse client name): {client_dir.name}")
            skipped += 1
            continue

        # Collect actual file summary names from disk for wikilink matching
        actual_files = [f.name for f in client_dir.glob("*-summary.md") if f.name != "_client-summary.md"]

        frontmatter = build_frontmatter(parsed)
        linked_text = inject_file_wikilinks(text, client_dir.name, actual_files)
        output_content = frontmatter + linked_text

        out_dir = clients_dst / client_dir.name
        out_file = out_dir / "__client-summary.md"

        if dry_run:
            print(f"  [DRY RUN] Would write: {out_file.relative_to(vault_dir)}")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file.write_text(output_content, encoding="utf-8")
            # Remove old single-underscore file if it exists from a previous run
            old_file = out_dir / "_client-summary.md"
            if old_file.exists():
                old_file.unlink()
            print(f"  Published: Archive/Clients/{client_dir.name}/__client-summary.md")

        published += 1

        # Copy individual file summaries with frontmatter injected (exclude _client-summary.md)
        client_name = parsed["client"]
        for file_summary in sorted(client_dir.glob("*-summary.md")):
            if file_summary.name == "_client-summary.md":
                continue
            dst_file = out_dir / file_summary.name
            file_text = file_summary.read_text(encoding="utf-8")
            file_fm = f'---\ntype: archive-file-summary\nclient: {yaml_str(client_name)}\n---\n\n'
            file_output = file_fm + file_text
            if dry_run:
                print(f"    [DRY RUN] Would write: {dst_file.relative_to(vault_dir)}")
            else:
                out_dir.mkdir(parents=True, exist_ok=True)
                dst_file.write_text(file_output, encoding="utf-8")
                print(f"    + {file_summary.name}")

    # Knowledge bases
    for kb_file in ["engagement-type-kb.md", "technical-kb.md"]:
        src = kb_src / kb_file
        if not src.exists():
            print(f"  SKIP (missing KB): {kb_file}")
            continue

        text = src.read_text(encoding="utf-8")
        fixed = fix_kb_wikilinks(text)

        out_file = kb_dst / kb_file

        if dry_run:
            print(f"  [DRY RUN] Would write: {VAULT_ARCHIVE_KB}/{kb_file}")
        else:
            kb_dst.mkdir(parents=True, exist_ok=True)
            out_file.write_text(fixed, encoding="utf-8")
            print(f"  Published: {VAULT_ARCHIVE_KB}/{kb_file}")

    print(f"\nDone. {published} client summaries {'would be ' if dry_run else ''}published, {skipped} skipped.")


def main():
    _default_workspace, _default_vault = _resolve_config_defaults()

    parser = argparse.ArgumentParser(description="Publish archive pipeline output to Obsidian vault")
    parser.add_argument(
        "--archive-dir",
        required=(_default_workspace is None),
        default=None,
        help="Path to archive pipeline output directory (contains clients/ and knowledge-bases/)",
    )
    parser.add_argument(
        "--vault",
        required=(_default_vault is None),
        default=_default_vault,
        help="Path to Obsidian vault root",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    archive_dir = Path(args.archive_dir)
    vault_dir = Path(args.vault)

    if not archive_dir.exists():
        print(f"ERROR: Archive dir not found: {archive_dir}", file=sys.stderr)
        sys.exit(1)
    if not vault_dir.exists():
        print(f"ERROR: Vault dir not found: {vault_dir}", file=sys.stderr)
        sys.exit(1)

    publish(archive_dir, vault_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
