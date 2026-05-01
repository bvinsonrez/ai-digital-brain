---
type: hub
project: My Project
status: active
created: 2026-01-15
last_reviewed: 2026-01-15
tags:
  - project
---

# My Project — Hub

## Overview

**Goal:** Build a personal knowledge management system that actually gets used
**Started:** 2026-01-15
**Status:** Active

## Related Notes

```dataview
TABLE file.mtime as "Updated"
FROM "Projects/_ExampleProject"
WHERE file.name != this.file.name
SORT file.mtime DESC
```

## Open Items

- [ ] Set up Templater template folder in Obsidian settings
- [ ] Configure Periodic Notes daily folder to `Periodic Notes/Daily/`
- [ ] Review example templates and customize for your workflow

## Notes

This is an example project hub. Hub notes are the anchor for a project — everything related to the project links back here.

Create a hub note for each major project by using `Templates/Hub Note.md` (Ctrl+T in Obsidian with Templater installed).
