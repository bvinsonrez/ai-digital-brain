# archive-pipeline

Scans a folder of project files, extracts text, synthesizes summaries via Claude, and publishes structured markdown notes to an Obsidian vault organized by client/project.

This is a periodic or one-time ingestion tool — run it when clearing old project files out of an archive folder.

## What It Does

1. Scans `source_dir` for supported file types
2. Extracts text (docx, pptx, pdf, xlsx, txt)
3. Classifies each file — skip, convert, or trash
4. Synthesizes per-file summaries and per-client engagement summaries using Claude
5. Publishes markdown notes to `output_dir` organized by client
6. Moves processed source files to Trash (recoverable via macOS Trash)

Unsupported formats (Tableau workbooks, Alteryx workflows, binaries, etc.) are trashed directly without conversion.

## Usage

```bash
cd scripts/archive-pipeline

# Normal run
python archive_pipeline.py --config pipeline.yaml

# Preview only — no files moved or written
python archive_pipeline.py --config pipeline.yaml --dry-run

# Resume a previously interrupted run
python archive_pipeline.py --config pipeline.yaml --resume

# Override source directory
python archive_pipeline.py --config pipeline.yaml --source "/path/to/folder"
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r ../../requirements.txt
export ANTHROPIC_API_KEY=<your key>
```

## Configuration — `pipeline.yaml`

Copy `pipeline.example.yaml` to `pipeline.yaml` and fill in your paths.
`pipeline.yaml` is gitignored — never commit it.

| Key | Purpose |
|-----|---------|
| `source_dir` | Folder to scan for files |
| `output_dir` | Where synthesized notes are written (overrides VAULT_PATH from scripts/config.py) |
| `dry_run` | Set to `true` to preview without writing |
| `trash.method` | `macos` = moves to macOS Trash (recoverable); `delete` = permanent |
| `file_rules.convert` | Extensions to extract and synthesize |
| `file_rules.note_trash` | Extensions to note and trash without text conversion |
| `file_rules.trash` | Binary/junk extensions to trash silently |
| `classification_hints` | Optional domain-specific categories passed to Claude as tagging context |

## Key Files

| File | Role |
|------|------|
| `archive_pipeline.py` | Main entry point |
| `scanner.py` | Finds and classifies files by extension |
| `extractor.py` | Extracts text from docx, pptx, pdf, xlsx, txt |
| `synthesizer.py` | Claude calls for per-file and per-client summaries |
| `knowledge_base.py` | Builds engagement and technical KB structures |
| `publisher.py` | Writes markdown output; moves files to Trash |
| `publish_to_obsidian.py` | Post-processing step: injects frontmatter and copies to vault |
| `classifier.py` | Disposition logic (convert / note-trash / trash) |
| `checkpoint.py` | Progress tracking for `--resume` |
| `config.py` | Loads pipeline.yaml; falls back to VAULT_PATH from scripts/config.py |
| `pipeline.example.yaml` | Template configuration — copy to pipeline.yaml |
