<!-- Delete the vault variant section you didn't choose (consulting or general) after copying your vault. -->

# Obsidian Vault — Structure and MCP Usage

Load this before reading or writing anything in the Obsidian vault.

---

## MCP Server

The vault is accessed via `@bitbonsai/mcpvault`. Tools are prefixed `mcp__obsidian__*`:
- `mcp__obsidian__read_note` — read a note by path
- `mcp__obsidian__write_note` — write or overwrite a note
- `mcp__obsidian__patch_note` — append or insert into an existing note
- `mcp__obsidian__search_notes` — full-text search across the vault
- `mcp__obsidian__list_directory` — list files in a vault folder
- `mcp__obsidian__get_frontmatter` — read YAML frontmatter from a note

All paths are relative to the vault root. Example: `Inbox/my-note.md`

If MCP tools appear missing: run ToolSearch with query `obsidian` and try again. The server initializes asynchronously.

---

## Vault Variant: Consulting / BD

*(Delete this section if you chose the general vault)*

```
Clients/
  [Client Name]/
    [Client Name] — Hub.md   # Hub note: account context, contacts, open items
People/
Opportunities/
Meetings/
  Granola/
    Notes/                   # Meeting notes synced from Granola
    Transcripts/             # Raw transcripts
Periodic Notes/
  Daily/
  Weekly/
Templates/                   # Templater templates — configure folder in Templater settings
Inbox/                       # Unprocessed items; sort weekly
Archive/                     # Completed clients, closed opps
```

**Hub note pattern:** Every client and opportunity gets a Hub note. Hub notes use Dataview to pull in related notes. Template: `Templates/Hub Note.md`.

**Meeting note pattern:** Notes in `Meetings/Granola/Notes/` link back to the client hub via `hub_note: "[[Clients/[Client]/[Client] — Hub]]"` frontmatter.

---

## Vault Variant: General Knowledge Worker

*(Delete this section if you chose the consulting vault)*

```
Projects/
  [Project Name]/
    [Project Name] — Hub.md  # Hub note: goals, status, related notes
People/
Meetings/
  Notes/                     # Meeting notes
  Transcripts/               # Raw transcripts
Learning/                    # Literature notes, course notes, book summaries
Periodic Notes/
  Daily/
  Weekly/
Templates/                   # Templater templates — configure folder in Templater settings
Inbox/
Archive/
```

**Hub note pattern:** Every project gets a Hub note. Template: `Templates/Hub Note.md`.

**Learning note pattern:** Notes in `Learning/` use type: `literature-note` or `course-note` in frontmatter.

---

## Inbox Discipline

The Inbox is a staging area, not permanent storage. Review it weekly:
1. Notes that belong to a client/project → move to the right folder
2. Notes that need a hub created → create the hub first, then move
3. Notes that are noise → delete

Aim for an empty inbox by end of each week.

---

## Frontmatter Schema

All notes should have at minimum:
```yaml
---
type: [hub | meeting-note | literature-note | daily | weekly | project-note]
created: YYYY-MM-DD
tags: []
---
```

Hub notes additionally need:
```yaml
status: [active | on-hold | complete | archive]
```
