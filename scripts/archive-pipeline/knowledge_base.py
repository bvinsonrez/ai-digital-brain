import re
from pathlib import Path
from typing import Dict, List


def parse_client_summary(summary_md: str) -> dict:
    """Extract structured tags from a _client-summary.md string."""
    result = {
        "client_name": "",
        "industry": "",
        "outcome": "",
        "category_primary": "",
        "category_secondary": "",
        "platforms": [],
        "service_areas": [],
    }

    m = re.search(r'^# (.+)$', summary_md, re.MULTILINE)
    if m:
        result["client_name"] = m.group(1).strip()

    for field, pattern in [
        ("industry", r'\*\*Industry:\*\* (.+)'),
        ("outcome", r'\*\*Engagement Outcome:\*\* (.+)'),
        ("category_primary", r'- Primary: (.+)'),
        ("category_secondary", r'- Secondary: (.+)'),
    ]:
        m = re.search(pattern, summary_md)
        if m:
            result[field] = m.group(1).strip()

    m = re.search(r'- Platforms: (.+)', summary_md)
    if m:
        val = m.group(1).strip()
        if val.lower() != "unknown":
            result["platforms"] = [p.strip() for p in val.split(",") if p.strip()]

    m = re.search(r'- Service Areas: (.+)', summary_md)
    if m:
        val = m.group(1).strip()
        if val.lower() != "unknown":
            result["service_areas"] = [a.strip() for a in val.split(",") if a.strip()]

    return result


def build_engagement_kb(client_summaries: List[dict], output_path: Path):
    """Build engagement type knowledge base from parsed client summaries."""
    by_category: Dict[str, List[dict]] = {}

    for c in client_summaries:
        for key in ("category_primary", "category_secondary"):
            category = c.get(key, "").strip()
            if category and category.lower() not in ("none", "other", ""):
                by_category.setdefault(category, []).append(c)

    lines = [
        "# Engagement Type Knowledge Base\n",
        "*Rebuilt on every pipeline run.*\n\n---\n",
    ]

    for category, clients in sorted(by_category.items()):
        lines.append(f"\n## {category}\n\n")
        for c in clients:
            name = c["client_name"]
            outcome = c["outcome"]
            industry = c["industry"]
            lines.append(
                f"- **{name}** ({industry}, {outcome})"
                f" — [[clients/{name}/_client-summary]]\n"
            )

    output_path.write_text("".join(lines))


def build_technical_kb(client_summaries: List[dict], output_path: Path):
    """Build technical knowledge base from parsed client summaries."""
    by_platform: Dict[str, List[dict]] = {}
    by_area: Dict[str, List[dict]] = {}

    for c in client_summaries:
        for platform in c["platforms"]:
            by_platform.setdefault(platform, []).append(c)
        for area in c["service_areas"]:
            by_area.setdefault(area, []).append(c)

    lines = [
        "# Technical Knowledge Base\n",
        "*Rebuilt on every pipeline run.*\n\n---\n",
        "\n## By Platform\n",
    ]

    for platform, clients in sorted(by_platform.items()):
        lines.append(f"\n### {platform}\n\n")
        for c in clients:
            lines.append(
                f"- **{c['client_name']}** ({c['outcome']})"
                f" — [[clients/{c['client_name']}/_client-summary]]\n"
            )

    lines.append("\n---\n\n## By Service Area\n")

    for area, clients in sorted(by_area.items()):
        lines.append(f"\n### {area}\n\n")
        for c in clients:
            lines.append(
                f"- **{c['client_name']}** ({c['outcome']})"
                f" — [[clients/{c['client_name']}/_client-summary]]\n"
            )

    output_path.write_text("".join(lines))
