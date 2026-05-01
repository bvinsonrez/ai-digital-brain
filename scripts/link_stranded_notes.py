#!/usr/bin/env python3
"""
link_stranded_notes.py — Link isolated internal meeting notes to People/ and/or hub notes.

Targets enriched notes where hub_note is blank (internal/personal meetings with no
client-hub match) and body has no wikilinks.

Strategy:
  1. Fuzzy-match note title against People/ filenames (rapidfuzz token_set_ratio)
  2. Match note title against known meeting series patterns
  3. Match "Unknown" client notes against client name in title
  4. Collect low-confidence and no-match notes for Haiku classification

Usage:
    python3 link_stranded_notes.py --dry-run               # preview all matches (title-only)
    python3 link_stranded_notes.py --apply                 # apply HIGH-confidence matches
    python3 link_stranded_notes.py --apply --haiku         # apply all confirmed matches incl. Haiku
    python3 link_stranded_notes.py --haiku-only            # just run Haiku title pass, print results
    python3 link_stranded_notes.py --body-classify         # body-reading Haiku pass (dry run)
    python3 link_stranded_notes.py --apply --body-classify # body pass + apply links (titles still manual)
"""

import os
import re
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

try:
    from rapidfuzz import fuzz, process as rf_process
except ImportError:
    print("❌ rapidfuzz not installed. Run: venv/bin/pip install rapidfuzz")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent))
try:
    from config import VAULT_PATH
except ImportError:
    sys.exit(
        "Error: scripts/config.py not found.\n"
        "Copy scripts/config.example.py to scripts/config.py and fill in VAULT_PATH."
    )

VAULT = Path(VAULT_PATH)

# Explicit overrides: note stem → exact list of links to add (replaces auto-detection).
# Add entries here to force specific links for notes that auto-detection gets wrong.
# Example: "My Meeting Note Title": ["People/Alice Johnson"]
OVERRIDES: dict[str, list[str]] = {}

# Stems to skip — note titles where auto-detection finds the wrong person.
# Add entries here to suppress false-positive matches.
EXCLUSIONS: set[str] = set()

# Link paths that should never be written — prevents self-links to the vault owner
# and dangling links to People notes that don't exist.
# Example: "People/Vault Owner"
LINK_EXCLUSIONS: set[str] = set()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Update these to match your vault's meeting note folder locations.
MEETING_FOLDERS = [
    VAULT / "Meetings" / "Notes",
]

# Confidence thresholds
HIGH = 88
MEDIUM = 70

# Meeting series hub map — keyed on title substrings.
# Add entries for your org's recurring meeting series.
# Example: "Weekly Pipeline Call": "Internal/Meeting Series/Weekly Pipeline Call — Hub"
SERIES_MAP: dict[str, str] = {}

# Client hub map — for "Unknown" client notes where the title contains a client name.
# Add entries to map title keywords to vault-relative hub note paths.
# Example: "Acme Corp": "Clients/AcmeCorp/Acme Corp — Hub"
# Use None as the value to explicitly skip a keyword (prevents false-positive matches).
CLIENT_MAP: dict[str, str | None] = {}

_FRONTMATTER_RE = re.compile(r"^---\n([\s\S]*?)\n---\n([\s\S]*)$")


def parse_frontmatter(content: str):
    m = _FRONTMATTER_RE.match(content)
    return (m.group(1), m.group(2)) if m else (None, None)


def build_people_lookup() -> tuple[dict, dict, list]:
    """
    Returns:
      token_lookup: {name_token_lower: [(people_path, full_name)]} — first/last name word tokens
      full_lookup:  {full_name_lower: people_path}
      stems:        [full_name_str, ...]
    """
    people_dir = VAULT / "People"
    token_lookup: dict[str, list] = {}
    full_lookup: dict[str, str] = {}
    stems = []

    # Stop words: common non-name words that might appear in meeting titles.
    # Add your own first name and org name here to avoid false-positive matches.
    # Example additions: "alice", "acme"
    STOP = {"and", "with", "for", "the", "internal", "bi", "weekly",
            "check", "monthly", "bi-weekly", "quick", "personal"}

    for p in sorted(people_dir.glob("*.md")):
        stem = p.stem
        path = f"People/{stem}"
        stems.append(stem)
        full_lookup[stem.lower()] = path
        parts = stem.split()
        for word in parts:
            w = word.lower()
            if len(w) >= 4 and w not in STOP:  # skip short/common words
                if w not in token_lookup:
                    token_lookup[w] = []
                token_lookup[w].append((path, stem))

    return token_lookup, full_lookup, stems


def get_stranded_notes() -> list:
    """Returns list of (path, stem, body, client) for stranded notes with no body links."""
    results = []
    for folder in MEETING_FOLDERS:
        if not folder.exists():
            continue
        for f in sorted(folder.glob("*.md")):
            text = f.read_text(encoding="utf-8")
            if "enriched: true" not in text:
                continue
            if 'hub_note: ""' not in text and "hub_note: ''" not in text:
                continue
            fm, body = parse_frontmatter(text)
            if fm is None:
                continue
            if re.findall(r"\[\[[^\]]+\]\]", body):
                continue  # already has body links
            client_m = re.search(r'^client:\s*"?([^"\n]+?)"?\s*$', fm, re.MULTILINE)
            client = client_m.group(1) if client_m else ""
            results.append((f, f.stem, body, client))
    return results


def match_series(title: str) -> str | None:
    for pattern, hub in SERIES_MAP.items():
        if pattern.lower() in title.lower():
            return hub
    return None


def match_client(title: str, client: str) -> str | None:
    if "Unknown" not in client and client:
        return None  # only apply to Unknown/blank clients
    for keyword, hub in CLIENT_MAP.items():
        if keyword.lower() in title.lower():
            return hub
    return None


def token_match_people(title: str, token_lookup: dict) -> list[tuple[str, str]]:
    """
    Find People matches by looking for name tokens in the title.
    Returns list of (people_path, full_name) for each unique match found.
    Ambiguous tokens (same word maps to multiple people) are excluded.
    """
    # Extract words from title, strip punctuation, lowercase
    title_words = set(re.findall(r"[a-zA-Z]{4,}", title.lower()))
    matches = {}
    for word in title_words:
        if word in token_lookup:
            entries = token_lookup[word]
            if len(entries) == 1:  # unambiguous match
                path, full_name = entries[0]
                if path not in matches:
                    matches[path] = full_name
    return list(matches.items())  # [(path, full_name), ...]


def write_link(filepath: Path, body: str, links: list[str], dry_run: bool = True) -> str:
    """Append wikilinks to body in a ## Links section."""
    content = filepath.read_text(encoding="utf-8")
    fm, _ = parse_frontmatter(content)
    if fm is None:
        return "error"

    formatted = "\n".join(f"- [[{l}]]" for l in links if l)
    if not formatted:
        return "skip"

    # Check if any of these links already exist or are self-links
    new_links = [l for l in links if l and f"[[{l}]]" not in content and l not in LINK_EXCLUSIONS]
    if not new_links:
        return "exists"

    formatted = "\n".join(f"- [[{l}]]" for l in new_links)

    if "## Links" in body:
        new_body = body.rstrip() + f"\n{formatted}\n"
    else:
        new_body = body.rstrip() + f"\n\n## Links\n\n{formatted}\n"

    if not dry_run:
        filepath.write_text(f"---\n{fm}\n---\n{new_body}", encoding="utf-8")
    return "added"


HAIKU_BATCH_SIZE = 30


def _call_haiku_batch(titles: list[str], people_stems: list) -> dict[str, tuple]:
    """Send one batch of titles to Haiku. Returns {title: (match, confidence)}."""
    people_list = "\n".join(f"- {s}" for s in sorted(people_stems))
    series_list = "\n".join(f"- {k}" for k in SERIES_MAP.keys())
    titles_block = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))

    prompt = f"""You are classifying meeting note titles from a sales executive's vault.

For each title, return the BEST match from the People list OR the Meeting Series list, or null if no confident match.

People (vault paths = People/<Name>):
{people_list}

Meeting Series:
{series_list}

Titles to classify:
{titles_block}

Return a JSON array matching title order. Each element must be:
{{"title": "...", "match": "People/<Name>", "confidence": "high"}}
or
{{"title": "...", "match": "series:<SeriesName>", "confidence": "medium"}}
or
{{"title": "...", "match": null, "confidence": "low"}}

Return ONLY a raw JSON array with no markdown fencing, no extra text.
"""

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
    )

    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        raw = result["content"][0]["text"].strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        items = json.loads(raw)
        return {item["title"]: (item["match"], item["confidence"]) for item in items}


def call_haiku(titles: list[str], people_stems: list) -> dict[str, str | None]:
    """Send ambiguous titles to Haiku in batches. Returns {title: (match, confidence)}."""
    if not ANTHROPIC_API_KEY:
        print("⚠️  ANTHROPIC_API_KEY not set — skipping Haiku batch")
        return {}

    results = {}
    batches = [titles[i:i + HAIKU_BATCH_SIZE] for i in range(0, len(titles), HAIKU_BATCH_SIZE)]
    for idx, batch in enumerate(batches):
        print(f"  Batch {idx + 1}/{len(batches)} ({len(batch)} titles)...")
        try:
            batch_results = _call_haiku_batch(batch, people_stems)
            results.update(batch_results)
        except Exception as e:
            print(f"  ❌ Haiku error on batch {idx + 1}: {e}")
    return results


# ---------------------------------------------------------------------------
# Body-classify pass
# ---------------------------------------------------------------------------

HAIKU_BODY_BATCH_SIZE = 8


def _call_haiku_body_batch(items: list[tuple], people_stems: list) -> list[dict]:
    """
    items: [(filepath, stem, body), ...]
    Returns list of dicts with people_match, series_match, client_match,
    suggested_title, and confidence.
    """
    people_list = "\n".join(f"- {s}" for s in sorted(people_stems))
    series_list = "\n".join(f"- {k}" for k in SERIES_MAP.keys())
    client_list = "\n".join(f"- {k}" for k, v in CLIENT_MAP.items() if v)

    notes_block = ""
    for i, (_, stem, body) in enumerate(items):
        excerpt = body.strip()[:500].replace("\n", " ")
        notes_block += f"\n--- NOTE {i+1} ---\nTitle: {stem}\nBody: {excerpt}\n"

    prompt = f"""You are classifying meeting notes from a sales executive's Obsidian vault.

For each note, return:
- people_match: "People/<Name>" if the meeting is primarily with/about a known person, else null
- series_match: "series:<keyword>" if it belongs to a known recurring series, else null
- client_match: "<keyword>" if a specific known client is clearly the subject, else null
- suggested_title: a concise improved title (max 60 chars) if the current title is unclear/generic/initials-only, else null
- confidence: "high", "medium", or "low"

Only return high or medium confidence matches — use low if genuinely uncertain.

Known People (use exact "People/<Name>" format):
{people_list}

Known Meeting Series keywords:
{series_list}

Known Clients:
{client_list}

Notes:
{notes_block}

Return ONLY a raw JSON array. Each element:
{{"note_index": 1, "title": "exact original title", "people_match": null, "series_match": null, "client_match": null, "suggested_title": null, "confidence": "low"}}
"""

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
    )

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        raw = data["content"][0]["text"].strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)


def run_body_classify(dry_run: bool, people_stems: list, token_lookup: dict):
    """Body-reading classification pass. Prints results; applies links only if not dry_run."""
    if not ANTHROPIC_API_KEY:
        print("⚠️  ANTHROPIC_API_KEY not set — cannot run body-classify")
        return

    all_stranded = get_stranded_notes()
    to_classify = [(f, stem, body) for f, stem, body, client in all_stranded
                   if stem not in EXCLUSIONS]

    if not to_classify:
        print("No stranded notes to body-classify.")
        return

    print(f"\n=== BODY-CLASSIFY PASS ({len(to_classify)} notes) ===\n")

    body_results: dict[str, dict] = {}
    batches = [to_classify[i:i + HAIKU_BODY_BATCH_SIZE]
               for i in range(0, len(to_classify), HAIKU_BODY_BATCH_SIZE)]
    for idx, batch in enumerate(batches):
        print(f"  Batch {idx + 1}/{len(batches)} ({len(batch)} notes)...")
        try:
            items = _call_haiku_body_batch(batch, people_stems)
            for r in items:
                body_results[r["title"]] = r
        except Exception as e:
            print(f"  ❌ Error on batch {idx + 1}: {e}")

    links_to_write: list[tuple] = []
    title_suggestions: list[tuple] = []

    print("\nMatches found:")
    for filepath, stem, body in to_classify:
        r = body_results.get(stem)
        if not r:
            continue
        conf = r.get("confidence", "low")
        if conf == "low":
            continue

        links = []
        match_labels = []

        if r.get("people_match"):
            links.append(r["people_match"])
            match_labels.append(r["people_match"])

        if r.get("series_match"):
            series_key = r["series_match"].replace("series:", "").strip()
            hub = next((v for k, v in SERIES_MAP.items()
                        if series_key.lower() in k.lower()), None)
            if hub:
                links.append(hub)
                match_labels.append(f"series:{hub.split('/')[-1]}")

        if r.get("client_match"):
            ck = r["client_match"]
            hub_path = CLIENT_MAP.get(ck)
            if hub_path:
                links.append(hub_path)
                match_labels.append(f"client:{hub_path.split('/')[-1]}")

        if links:
            folder = "Granola" if "Granola" in str(filepath) else "Internal"
            print(f"  [{folder}] [{conf}] {stem[:50]:<50} → {', '.join(match_labels)}")
            links_to_write.append((filepath, stem, body, links))

        if r.get("suggested_title"):
            title_suggestions.append((filepath, stem, r["suggested_title"], conf))

    # Title suggestion table (never auto-applied)
    if title_suggestions:
        print(f"\n=== TITLE SUGGESTIONS ({len(title_suggestions)}) ===")
        print("(Not auto-applied — review and confirm before renaming)\n")
        for filepath, old_title, new_title, conf in title_suggestions:
            folder = "Granola" if "Granola" in str(filepath) else "Internal"
            print(f"  [{folder}] [{conf}]")
            print(f"    OLD: {old_title}")
            print(f"    NEW: {new_title}")

    # Apply links
    if not dry_run and links_to_write:
        print(f"\n--- Applying body-classified links ({len(links_to_write)} notes) ---")
        applied = skipped = 0
        for filepath, stem, body, links in links_to_write:
            result = write_link(filepath, body, links, dry_run=False)
            tag = "✅" if result == "added" else "──"
            print(f"  {tag} {stem[:60]} ({result})")
            if result == "added":
                applied += 1
            else:
                skipped += 1
        print(f"\nDone. Applied: {applied}, Already linked/skipped: {skipped}")
    elif links_to_write:
        print(f"\nRun with --apply --body-classify to write {len(links_to_write)} links.")


def main():
    dry_run = "--apply" not in sys.argv
    run_haiku = "--haiku" in sys.argv or "--haiku-only" in sys.argv
    haiku_only = "--haiku-only" in sys.argv
    body_classify = "--body-classify" in sys.argv

    if dry_run:
        print("=== DRY RUN — no files will be modified ===\n")

    token_lookup, full_lookup, people_stems = build_people_lookup()

    if body_classify:
        run_body_classify(dry_run, people_stems, token_lookup)
        return
    stranded = get_stranded_notes()
    print(f"Stranded notes with no body wikilinks: {len(stranded)}\n")

    high_conf = []
    no_match = []

    for filepath, stem, body, client in stranded:
        # Check overrides first
        if stem in OVERRIDES:
            links_to_add = OVERRIDES[stem]
            label = [f"override:{l.split('/')[-1]}" for l in links_to_add]
            high_conf.append((filepath, stem, body, links_to_add, label))
            continue

        # Skip known false positives
        if stem in EXCLUSIONS:
            no_match.append((filepath, stem, body, client, []))
            continue

        links_to_add = []
        label = []

        # 1. Meeting series match
        series_hub = match_series(stem)
        if series_hub:
            links_to_add.append(series_hub)
            label.append(f"series:{series_hub.split('/')[-1]}")

        # 2. Client match (for Unknown/blank client notes)
        client_hub = match_client(stem, client)
        if client_hub:
            links_to_add.append(client_hub)
            label.append(f"client:{client_hub.split('/')[-1]}")

        # 3. People token match — find name words from People/ in the title
        people_matches = token_match_people(stem, token_lookup)
        for path, full_name in people_matches:
            links_to_add.append(path)
            label.append(f"people:{full_name}")

        if links_to_add:
            high_conf.append((filepath, stem, body, links_to_add, label))
        else:
            no_match.append((filepath, stem, body, client, []))

    # --- Print HIGH confidence ---
    print(f"HIGH confidence ({len(high_conf)} notes) — will auto-apply:")
    for filepath, stem, body, links, label in high_conf:
        short_folder = "Granola" if "Granola" in str(filepath) else "Internal"
        print(f"  [{short_folder}] {stem[:55]:<55} → {', '.join(label)}")

    # --- Print NO_MATCH ---
    print(f"\nNO MATCH ({len(no_match)} notes) — Haiku batch or manual review:")
    for filepath, stem, body, client, existing in no_match:
        short_folder = "Granola" if "Granola" in str(filepath) else "Internal"
        print(f"  [{short_folder}] {stem[:75]}")

    # --- Haiku batch ---
    haiku_results = {}
    if run_haiku and no_match:
        uncertain_titles = [stem for filepath, stem, body, client, existing in no_match
                            if stem not in EXCLUSIONS]
        print(f"\nSending {len(uncertain_titles)} titles to Haiku for classification "
              f"({len(no_match) - len(uncertain_titles)} exclusions skipped)...")
        haiku_results = call_haiku(uncertain_titles, people_stems)
        print("\nHaiku results:")
        for title, result in haiku_results.items():
            match, conf = result if result else (None, None)
            print(f"  {title[:60]:<60} → {match} ({conf})")

    if haiku_only:
        return

    # --- Apply ---
    if not dry_run:
        print("\n--- Applying HIGH-confidence links ---")
        applied = skipped = 0
        for filepath, stem, body, links, label in high_conf:
            result = write_link(filepath, body, links, dry_run=False)
            tag = "✅" if result == "added" else "──"
            print(f"  {tag} {stem[:60]} ({result})")
            if result == "added":
                applied += 1
            else:
                skipped += 1

        if run_haiku and haiku_results:
            print("\n--- Applying Haiku high/medium-confidence links ---")
            for filepath, stem, body, client, existing_links in no_match:
                if stem in EXCLUSIONS:
                    continue
                result_tuple = haiku_results.get(stem)
                if not result_tuple:
                    continue
                match, conf = result_tuple
                if not match or conf == "low":
                    continue
                # Resolve match to a path
                if match and match.startswith("People/"):
                    all_links = existing_links + [match]
                elif match and match.startswith("series:"):
                    series_name = match[7:]
                    hub = next((v for k, v in SERIES_MAP.items() if series_name in k), None)
                    all_links = existing_links + ([hub] if hub else [])
                else:
                    all_links = existing_links
                if all_links:
                    result = write_link(filepath, body, all_links, dry_run=False)
                    tag = "✅" if result == "added" else "──"
                    print(f"  {tag} {stem[:55]} → {all_links}")
                    if result == "added":
                        applied += 1

        print(f"\nDone. Applied: {applied}, Already linked/skipped: {skipped}")
    else:
        total_to_apply = len(high_conf)
        print(f"\nRun with --apply to write {total_to_apply} HIGH-confidence links.")
        print("Run with --apply --haiku to also write Haiku-confirmed links for the NO_MATCH set.")


if __name__ == "__main__":
    main()
