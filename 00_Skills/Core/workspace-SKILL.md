# Workspace — Naming Conventions and Structure

Load this when creating, naming, or placing files anywhere in the workspace.

---

## Folder Purposes

| Folder | What goes here |
|--------|---------------|
| `00_Skills/` | Skill files and agent definitions — the AI operating system layer |
| `01_Active_Work/` | Currently active work: in-progress deliverables, open projects |
| `02_Projects/` | Longer-running projects with multiple deliverables |
| `03_Research/` | Reference material, market research, domain notes |
| `04_Operations/` | Internal operational artifacts: plans, specs, meeting logs |
| `05_Personal/` | Personal projects, non-work content |
| `06_Archive/` | Completed or inactive work — kept for reference |
| `07_Experiments/` | Throwaway prototypes; nothing here is production |

## File Naming

- Use `kebab-case` for all files: `client-discovery-brief.md` not `ClientDiscoveryBrief.md`
- Prefix with date when chronological order matters: `2026-05-01-project-kickoff-notes.md`
- Skill files: `[topic]-SKILL.md` (all caps SKILL suffix)
- Agent files: `NN_AGENT_[Role].md` where NN is a two-digit sequence number

## Archive Policy

Move to `06_Archive/` when:
- A project is complete and the deliverable has been sent/published
- A client engagement has ended (keep for 12 months, then delete)
- A skill file has been superseded by a newer version (keep the old one for 30 days)

Do not delete files without checking `06_Archive/` first — they may already be there.

## Placement Rules

- New deliverables → `01_Active_Work/[ProjectName]/`
- Completed deliverables → `06_Archive/[ProjectName]/`
- Research files → `03_Research/[Topic]/`
- Specs and plans from Claude sessions → `04_Operations/Plans/`
- Never put files at the root of any subfolder that has named sub-subfolders

## Obsidian Vault vs. This Workspace

The Obsidian vault (accessed via the Obsidian MCP) is a separate system from this workspace. Meeting notes, knowledge base entries, and personal notes live in the vault. Deliverables, skills, and code live here. If unsure where something belongs: vault = knowledge, workspace = work artifacts.
