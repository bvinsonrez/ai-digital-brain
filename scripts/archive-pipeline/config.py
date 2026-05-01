# config.py — loads pipeline configuration from a YAML file.
# Run: python archive_pipeline.py --config pipeline.yaml
# Copy pipeline.example.yaml to pipeline.yaml and fill in your values.

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from config import VAULT_PATH as _default_vault_path
except ImportError:
    _default_vault_path = None


@dataclass
class ClaudeConfig:
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 2048


@dataclass
class TrashConfig:
    method: str = "macos"


@dataclass
class FileRules:
    convert: List[str] = field(default_factory=list)
    note_trash: List[str] = field(default_factory=list)
    trash: List[str] = field(default_factory=list)


@dataclass
class PipelineConfig:
    source_dir: Path
    output_dir: Path
    dry_run: bool
    trash: TrashConfig
    claude: ClaudeConfig
    file_rules: FileRules
    classification_hints: Dict[str, List[str]]  # optional domain-specific tagging hints for Claude


def load_config(config_path: str, source_override: Optional[str] = None) -> PipelineConfig:
    with open(config_path) as f:
        data = yaml.safe_load(f)

    source_dir = Path(source_override or data.get("source_dir", ""))
    output_dir = Path(data.get("output_dir") or _default_vault_path or "")

    if not source_dir or not output_dir:
        raise ValueError(
            "source_dir and output_dir must be set in pipeline.yaml "
            "or VAULT_PATH must be set in scripts/config.py"
        )

    raw_rules = data.get("file_rules", {})
    file_rules = FileRules(
        convert=raw_rules.get("convert", []),
        note_trash=raw_rules.get("note_trash", []),
        trash=raw_rules.get("trash", []),
    )

    raw_claude = data.get("claude", {})
    claude = ClaudeConfig(
        model=raw_claude.get("model", "claude-sonnet-4-6"),
        max_tokens=raw_claude.get("max_tokens", 2048),
    )

    raw_trash = data.get("trash", {})
    trash = TrashConfig(method=raw_trash.get("method", "macos"))

    return PipelineConfig(
        source_dir=source_dir,
        output_dir=output_dir,
        dry_run=data.get("dry_run", False),
        trash=trash,
        claude=claude,
        file_rules=file_rules,
        classification_hints=data.get("classification_hints", {}),
    )
