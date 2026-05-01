# Scripts

Python and shell scripts for Obsidian vault management, note enrichment, and Claude Code session logging.

## Setup

1. Copy the config template and fill in your paths:
   ```bash
   cp scripts/config.example.py scripts/config.py
   ```
   Edit `scripts/config.py`:
   ```python
   VAULT_PATH = "/path/to/your/obsidian/vault"
   WORKSPACE_PATH = "/path/to/your/ai-digital-brain"
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   cd scripts
   python -m venv venv          # or: uv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Test the installation:
   ```bash
   cd scripts
   python -m vault_maintenance
   ```

## Script Reference

### Note Enrichment and Maintenance

| Script | What it does | Run |
|--------|-------------|-----|
| `enrich_notes.py` | Adds metadata, backlinks, and tags to notes that lack them. Uses Claude API. **Requires `ANTHROPIC_API_KEY`.** | `python enrich_notes.py` |
| `clean_vault_tags.py` | Audits and normalizes tag usage across the vault | `python clean_vault_tags.py` |
| `link_stranded_notes.py` | Finds orphaned notes with no incoming links and suggests connections | `python link_stranded_notes.py` |
| `add_people_links.py` | Scans notes for names matching `People/` entries and injects `[[wiki links]]` | `python add_people_links.py` |
| `voice-memo-export.py` | Exports Apple Voice Memos to markdown in `Inbox/` | `python voice-memo-export.py` — **Mac only** |

### Vault Organization

**vault-organizer/** classifies and moves misplaced notes to their correct folders.

```bash
cd scripts/vault-organizer
cp config.example.yaml config.yaml   # fill in your entity mappings
python vault_organizer.py --config config.yaml --dry-run   # preview first
python vault_organizer.py --config config.yaml             # apply
```

### Archive Pipeline

**archive-pipeline/** scans a source folder, extracts and synthesizes content, and publishes structured notes to Obsidian. Uses Claude API for classification and synthesis.

**Requires:** `ANTHROPIC_API_KEY` environment variable (separate from `claude login`):
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

```bash
cd scripts/archive-pipeline
cp pipeline.example.yaml pipeline.yaml   # fill in your source/output paths
python archive_pipeline.py --config pipeline.yaml --dry-run   # preview first
python archive_pipeline.py --config pipeline.yaml             # apply
```

See `archive-pipeline/README.md` for full documentation.

### Vault Health Report

```bash
cd scripts
python -m vault_maintenance     # must run from scripts/ directory
```

Produces a markdown report in your vault's `Inbox/` folder: `vault-audit-YYYY-MM-DD.md`.

### Session Hooks

`cc-session-start.sh` and `cc-session-stop.sh` are wired to Claude Code's `SessionStart` and `Stop` hooks via `.claude/settings.json`. They log session duration to your vault's `Inbox/`.

These run automatically when you use Claude Code. No manual invocation needed.

## Dependencies

| Package | Used by | Why |
|---------|---------|-----|
| `python-frontmatter` | Most scripts | Read/write YAML frontmatter in markdown notes |
| `pyyaml` | Most scripts | YAML parsing |
| `rich` | `vault_maintenance` | Terminal output formatting for reports |
| `click` | Scripts with options | CLI argument handling |
| `anthropic` | `enrich_notes.py`, `archive-pipeline/` | Claude API client — **requires `ANTHROPIC_API_KEY`** (not used by any other script) |
