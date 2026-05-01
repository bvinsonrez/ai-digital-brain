<!-- SETUP: Paste this file into Claude and use this prompt to personalize it:
     "Help me customize this CLAUDE.md for my own setup.
      Ask me questions one at a time about my role, tools, and workflow." -->

# [Your Name] — Claude Code Workspace Context
**Auto-loaded by Claude Code on every session.**

---

## Who I Am

[Your name], [your role] at [your organization]. I [brief description of what you do].

This workspace is my personal AI operating system. It contains my skill library, agent definitions, research notes, and project artifacts.

---

## Workspace Root

`/path/to/your/ai-digital-brain/`

```
00_Skills/          Portable skill library — always check here first
01_Active_Work/     Current active work
02_Projects/        Longer-running projects
03_Research/        Research and reference material
04_Operations/      Internal operational artifacts: plans, specs, meeting logs
05_Personal/        Personal projects and notes
06_Archive/         Completed or inactive work
07_Experiments/     Throwaway tools, prototypes
.claude/commands/   Slash commands for this workspace
```

---

## Skill Loading Convention

### Always load for any written output:
`00_Skills/Core/your-voice-SKILL.md` — writing voice, tone standards. Every email, memo, or deliverable must follow this.

### Always load when creating, naming, or placing files:
`00_Skills/Core/workspace-SKILL.md` — naming conventions, folder purposes, archive policy.

### Load for Obsidian vault work:
`00_Skills/Core/obsidian-SKILL.md` — vault structure, hub note conventions, MCP usage.

### Load by client or project when mentioned:
`00_Skills/Clients/[CLIENT]_SKILL.md` — check this folder first when a client is named.
`00_Skills/Technical/[DOMAIN]_SKILL.md` — load for technical deep-dives in a given domain.

---

## Agent Pipeline

My pipeline has three agents. All live in `00_Skills/Agents/`. Use the `/pipeline` command to invoke.

| File | Role |
|------|------|
| `00_AGENT_Coordinator.md` | Orchestrator — routes to Research or Deliverable |
| `01_AGENT_Research.md` | Pre-meeting / pre-deliverable research agent |
| `02_AGENT_Deliverable.md` | Research → polished output agent |

To run the pipeline: `/pipeline [context]`

---

## Key File Paths

| What | Path |
|------|------|
| Obsidian vault | `/path/to/your/vault` (via Obsidian MCP) |
| Working deliverables | `/path/to/your/working/files/` |
