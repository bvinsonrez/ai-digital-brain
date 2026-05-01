#!/usr/bin/env python3
# archive_pipeline.py
import argparse
from pathlib import Path

from config import load_config
from scanner import scan_source
from extractor import extract_text
from synthesizer import synthesize_file, synthesize_client
from knowledge_base import parse_client_summary, build_engagement_kb, build_technical_kb
from publisher import write_md, trash_file
from checkpoint import CheckpointManager
from classifier import Disposition


def run_pipeline(
    config_path: str,
    source_override: str = None,
    dry_run: bool = False,
    resume: bool = False,
):
    config = load_config(config_path, source_override)
    if dry_run:
        config.dry_run = True

    clients_dir = config.output_dir / "clients"
    kb_dir = config.output_dir / "knowledge-bases"

    if not config.dry_run:
        clients_dir.mkdir(parents=True, exist_ok=True)
        kb_dir.mkdir(parents=True, exist_ok=True)

    checkpoint = CheckpointManager(config.output_dir, config.source_dir)
    if resume:
        loaded = checkpoint.load()
        done = len(checkpoint.state["completed_clients"])
        print(f"Resuming. {done} client(s) already completed." if loaded else "No checkpoint found — starting fresh.")

    inventories = scan_source(config)
    print(f"Found {len(inventories)} client folder(s) in {config.source_dir}")

    all_parsed = []

    for inventory in inventories:
        name = inventory.client_name

        if resume and checkpoint.is_completed(name):
            print(f"  [{name}] skipping (already completed)")
            existing = clients_dir / name / "_client-summary.md"
            if existing.exists():
                all_parsed.append(parse_client_summary(existing.read_text()))
            continue

        print(f"  [{name}] processing...")
        if not config.dry_run:
            checkpoint.mark_in_progress(name)

        try:
            file_summaries = []
            noted_files = []
            to_trash = []

            for entry in inventory.files:
                if entry.disposition == Disposition.TRASH:
                    to_trash.append(entry.path)

                elif entry.disposition == Disposition.NOTE_TRASH:
                    noted_files.append((entry.path.name, entry.note_label))
                    to_trash.append(entry.path)

                elif entry.disposition == Disposition.CONVERT:
                    content = extract_text(entry.path)
                    if not content.strip():
                        to_trash.append(entry.path)
                        continue

                    summary = synthesize_file(
                        content=content,
                        client_name=name,
                        relative_path=entry.relative_path,
                        filename=entry.path.name,
                        config=config,
                    )

                    if summary is None:
                        to_trash.append(entry.path)
                    else:
                        # Use relative path as stem to avoid filename collisions
                        safe_stem = entry.relative_path.replace("/", "_").replace(" ", "_")
                        out_name = f"{safe_stem}-summary.md"
                        file_summaries.append((entry.path.name, summary))
                        if not config.dry_run:
                            write_md(summary, clients_dir / name / out_name)

            if file_summaries or noted_files:
                client_md = synthesize_client(
                    client_name=name,
                    file_summaries=file_summaries,
                    noted_files=noted_files,
                    config=config,
                )
                if not config.dry_run:
                    write_md(client_md, clients_dir / name / "_client-summary.md")
                all_parsed.append(parse_client_summary(client_md))
                if config.dry_run:
                    print(f"    [DRY RUN] would write {len(file_summaries)} summary file(s) + _client-summary.md")
                    for fname, _ in file_summaries:
                        safe_stem = fname.replace("/", "_").replace(" ", "_")
                        print(f"      + {safe_stem}-summary.md")
                    if noted_files:
                        print(f"    [DRY RUN] would note-and-trash: {', '.join(f for f, _ in noted_files)}")
                    if to_trash:
                        print(f"    [DRY RUN] would trash {len(to_trash)} file(s) silently")
                else:
                    print(f"    {len(file_summaries)} file(s) summarized, {len(noted_files)} noted, {len(to_trash)} to trash")
            else:
                print(f"    {'[DRY RUN] ' if config.dry_run else ''}no meaningful content found")

            for f in to_trash:
                trash_file(f, dry_run=config.dry_run)

            if not config.dry_run:
                checkpoint.mark_completed(name)

        except Exception as exc:
            print(f"  [{name}] ERROR: {exc}")
            if not config.dry_run:
                checkpoint.mark_errored(name)

    if all_parsed and not config.dry_run:
        build_engagement_kb(all_parsed, kb_dir / "engagement-type-kb.md")
        build_technical_kb(all_parsed, kb_dir / "technical-kb.md")
        print(f"Knowledge bases written to {kb_dir}")

    print("Done.")


def main():
    parser = argparse.ArgumentParser(description="Archive Pipeline")
    parser.add_argument("--config", required=True, help="Path to pipeline-config.yaml")
    parser.add_argument("--source", help="Override source_dir from config")
    parser.add_argument("--dry-run", action="store_true", help="Preview only — no files written or trashed")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    args = parser.parse_args()

    run_pipeline(
        config_path=args.config,
        source_override=args.source,
        dry_run=args.dry_run,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
