#!/usr/bin/env python3
"""
clean_vault_tags.py — Scrub garbage tags from vault notes.

Root cause: AI-generated PDF/Excel summaries in Archive/Clients/ contain
inline text like `#4c0980` (hex color), `#B221` (suite address), `#6879-`
(invoice number), `#DIV/0!` (Excel error) — all picked up by Obsidian as tags.

What this script fixes:
  1. Archive summary bodies (*.pdf-summary.md, *.xlsx-summary.md): strips the
     leading `#` from non-tag text so Obsidian stops registering them as tags.
  2. All notes: removes "n/a" placeholder entries from frontmatter tags arrays.

Usage:
    python3 clean_vault_tags.py            # dry run — print what would change
    python3 clean_vault_tags.py --apply    # write changes to disk
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
try:
    from config import VAULT_PATH
except ImportError:
    sys.exit(
        "Error: scripts/config.py not found.\n"
        "Copy scripts/config.example.py to scripts/config.py and fill in VAULT_PATH."
    )

VAULT = Path(VAULT_PATH)
APPLY = "--apply" in sys.argv

# ---------------------------------------------------------------------------
# Patterns that produce garbage tags in archive summary note bodies.
# Each entry is (compiled_regex, replacement) — the `#` is removed, the rest kept.
# ---------------------------------------------------------------------------
GARBAGE_BODY_PATTERNS = [
    # Excel formula errors: #DIV/0! #VALUE! #REF! #N/A #NUM! #NULL! #NAME?
    re.compile(r"#(DIV/0!|VALUE!|REF!|N/A|NUM!|NULL!|NAME\?)"),
    # Hex color codes: 3–8 hex digits (e.g. #4c0980, #005cba, #fff)
    re.compile(r"#([0-9a-fA-F]{3,8})(?=[\s,)(;\n])"),
    # Suite / cell-reference / order-form style: #B221, #A1, #Q-326266
    re.compile(r"#([A-Z][0-9-]+)\b"),
    # Invoice / date numbers: #6879- #641- #2067- #01_01 (digit-led)
    re.compile(r"#([0-9][^\s#]*)"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def split_frontmatter(text: str) -> tuple[str, str, str]:
    """Return (pre, frontmatter_block, body). pre is '' or '---\\n'."""
    if not text.startswith("---"):
        return ("", "", text)
    end = text.find("\n---", 3)
    if end == -1:
        return ("", "", text)
    fm = text[3:end].strip()
    body = text[end + 4:]  # skip closing ---
    return ("---\n", fm, body)


def strip_na_from_tags(frontmatter: str) -> tuple[str, bool]:
    """Remove 'n/a' entries from the YAML tags array. Returns (new_fm, changed)."""
    changed = False

    # Inline array form: tags: ["n/a", "co-worker"] or tags: [n/a]
    def replace_inline(m: re.Match) -> str:
        nonlocal changed
        inner = m.group(1)
        cleaned = re.sub(r'["\']?n/a["\']?,?\s*', "", inner, flags=re.IGNORECASE).strip().strip(",").strip()
        if cleaned != inner:
            changed = True
        return f"tags: [{cleaned}]"

    result = re.sub(r"tags:\s*\[([^\]]*)\]", replace_inline, frontmatter, flags=re.IGNORECASE)

    # Block list form:
    #   tags:
    #     - n/a
    def replace_block_item(m: re.Match) -> str:
        nonlocal changed
        changed = True
        return ""

    result = re.sub(r"\n\s+-\s+['\"]?n/a['\"]?\s*", "", result, flags=re.IGNORECASE)

    return result, changed


def clean_body(body: str) -> tuple[str, list[str]]:
    """Strip leading # from garbage patterns in note body. Returns (new_body, list_of_removed_tags)."""
    removed: list[str] = []
    result = body
    for pat in GARBAGE_BODY_PATTERNS:
        def replacer(m: re.Match, p=pat) -> str:
            removed.append(m.group(0))
            return m.group(0)[1:]  # drop the leading #
        result = pat.sub(replacer, result)
    return result, removed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_file(path: Path, is_summary: bool) -> bool:
    """Process one file. Returns True if a change was made (or would be made)."""
    text = path.read_text(encoding="utf-8")
    pre, fm, body = split_frontmatter(text)

    new_fm, fm_changed = strip_na_from_tags(fm) if fm else (fm, False)

    body_changed = False
    removed_tags: list[str] = []
    if is_summary:
        new_body, removed_tags = clean_body(body)
        body_changed = new_body != body
    else:
        new_body = body

    if not fm_changed and not body_changed:
        return False

    # Report
    rel = path.relative_to(VAULT)
    print(f"\n{'APPLY' if APPLY else 'DRY RUN'}: {rel}")
    if fm_changed:
        print("  frontmatter: removed 'n/a' from tags")
    if removed_tags:
        unique = sorted(set(removed_tags))
        print(f"  body: stripped {len(unique)} garbage tag(s): {', '.join(unique[:8])}" +
              (" …" if len(unique) > 8 else ""))

    if APPLY:
        new_text = pre + new_fm + "\n---" + new_body if fm else new_body
        path.write_text(new_text, encoding="utf-8")

    return True


def main() -> None:
    print(f"{'APPLYING' if APPLY else 'DRY RUN (pass --apply to write)'}")
    print(f"Vault: {VAULT}\n")

    changed = 0
    scanned = 0

    for md in sorted(VAULT.rglob("*.md")):
        scanned += 1
        is_summary = md.name.endswith((".pdf-summary.md", ".xlsx-summary.md"))
        if process_file(md, is_summary):
            changed += 1

    print(f"\n{'─' * 60}")
    print(f"Scanned {scanned} notes. {'Changed' if APPLY else 'Would change'}: {changed}")
    if not APPLY and changed:
        print("Run with --apply to write changes.")


if __name__ == "__main__":
    main()
