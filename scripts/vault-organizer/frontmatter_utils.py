# frontmatter_utils.py
from pathlib import Path
from typing import Any
import frontmatter


def read_note(path: Path) -> tuple[dict[str, Any], str]:
    """Return (metadata_dict, body_content) for a markdown file."""
    post = frontmatter.load(str(path))
    return dict(post.metadata), post.content


def write_note(path: Path, metadata: dict[str, Any], content: str) -> None:
    """Write metadata + content back to a markdown file."""
    post = frontmatter.Post(content, **metadata)
    path.write_text(frontmatter.dumps(post), encoding="utf-8")
