# vault_maintenance/fixers/tags.py
"""
Migrates flat tags to the nested taxonomy defined in obsidian-SKILL.md.
Always dry-run by default. Pass apply=True to write changes.
"""
from pathlib import Path
from typing import NamedTuple
import frontmatter

from vault_maintenance.config import VAULT_ROOT

# Map old flat tag -> new nested tag. None = remove the tag.
TAG_MIGRATION: dict[str, str | None] = {
    "meeting":   "type/meeting",
    "enriched":  None,             # redundant with enriched: true frontmatter field
    "hub":       "type/hub",
    "proposal":  "type/proposal",
    "reference": "type/reference",
}


class TagChange(NamedTuple):
    path: Path
    old_tags: list[str]
    new_tags: list[str]


def run(apply: bool = False) -> list[TagChange]:
    changes = []

    for md_file in VAULT_ROOT.rglob("*.md"):
        try:
            post = frontmatter.load(md_file)
        except Exception:
            continue

        raw_tags = post.metadata.get("tags", [])
        if not raw_tags:
            continue

        # Normalize to list of strings
        if isinstance(raw_tags, str):
            old_tags = [raw_tags]
        else:
            old_tags = list(raw_tags)

        new_tags = []
        changed = False
        for tag in old_tags:
            if tag in TAG_MIGRATION:
                replacement = TAG_MIGRATION[tag]
                changed = True
                if replacement is not None:
                    new_tags.append(replacement)
                # else: tag is dropped
            else:
                new_tags.append(tag)

        if changed:
            changes.append(TagChange(path=md_file, old_tags=old_tags, new_tags=new_tags))
            if apply:
                post.metadata["tags"] = new_tags
                md_file.write_text(frontmatter.dumps(post), encoding="utf-8")

    return changes
