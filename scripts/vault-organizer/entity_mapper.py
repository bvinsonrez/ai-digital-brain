# entity_mapper.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class EntityDestination:
    kind: str              # "client" | "internal" | "personal" | "unknown"
    folder: Optional[str]  # e.g. "AcmeCorp"; None for non-client
    notes_path: str        # vault-relative path for notes
    transcripts_path: str  # vault-relative path for transcripts


def resolve_destination(entity: Optional[str], config: dict) -> EntityDestination:
    """
    Map an entity/client field value to an EntityDestination using config rules.

    Priority:
      1. Exact match in entity_folder_map (case-insensitive)
      2. Substring match in internal_patterns
      3. Substring match in personal_patterns
      4. Fallback: unknown → Inbox

    Example config structure for entity_mapper:
    # entity_folder_map:
    #   "acme corp": "AcmeCorp"
    #   "widget co": "WidgetCo"
    # internal_patterns: ["internal", "1-1", "team meeting"]
    # personal_patterns: ["personal", "family"]
    """
    destinations = config["destinations"]

    if not entity or not str(entity).strip():
        return _unknown_dest(destinations)

    normalized = str(entity).strip().lower()

    # 1. Exact match in entity map
    folder_map = config["entity_folder_map"]
    if normalized in folder_map:
        folder = folder_map[normalized]
        base = destinations["client"].format(folder=folder)
        return EntityDestination(
            kind="client",
            folder=folder,
            notes_path=f"{base}/Notes",
            transcripts_path=f"{base}/Transcripts",
        )

    # 2. Internal patterns (substring match)
    for pattern in config.get("internal_patterns", []):
        if pattern.lower() in normalized:
            base = destinations["internal"]
            return EntityDestination(
                kind="internal",
                folder=None,
                notes_path=f"{base}/Notes",
                transcripts_path=f"{base}/Transcripts",
            )

    # 3. Personal patterns (substring match)
    for pattern in config.get("personal_patterns", []):
        if pattern.lower() in normalized:
            base = destinations["personal"]
            return EntityDestination(
                kind="personal",
                folder=None,
                notes_path=f"{base}/Notes",
                transcripts_path=f"{base}/Transcripts",
            )

    # 4. Unknown
    return _unknown_dest(destinations)


def _unknown_dest(destinations: dict) -> EntityDestination:
    base = destinations["unknown"]
    return EntityDestination(
        kind="unknown",
        folder=None,
        notes_path=base,
        transcripts_path=base,
    )
