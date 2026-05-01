# ai-digital-brain

A personal AI operating system built on Claude Code and Obsidian. Fork it, personalize it with your own LLM, and work the way you think.

## What's in the box

Three layers that work together (or independently):

1. **Claude Code workspace** — CLAUDE.md template, skill library, three-agent pipeline, session hooks, settings
2. **Obsidian vault** — Two scaffold variants (consulting/BD and general knowledge worker) with real Templater templates
3. **Vault scripts** — Python scripts for note enrichment, tag cleanup, vault organization, and archive processing

---

## Quick Start

### 30-minute path (Claude Code workspace only)

No Obsidian or scripts required.

1. Install Claude Code: [claude.ai/code](https://claude.ai/code) and run `claude login`
2. Clone this repo and open it in Claude Code:
   ```bash
   git clone https://github.com/bvinsonrez/ai-digital-brain.git
   cd ai-digital-brain
   claude .
   ```
3. In Claude Code, paste `CLAUDE.md` into the chat with this prompt:
   > "Help me customize this CLAUDE.md for my own setup. Ask me questions one at a time about my role, tools, and workflow."
4. Save the result as your new `CLAUDE.md`
5. Do the same for `00_Skills/Core/your-voice-SKILL.md`

You now have a working workspace with skill-loading and a three-agent pipeline.

---

### Full system path (workspace + Obsidian + scripts)

Continue from the 30-minute path, then follow [SETUP.md](SETUP.md) in order:

1. **Prerequisites** — Claude Code, Obsidian, Node.js, Python 3.10+
2. **Workspace personalization** — covered in the 30-minute path above
3. **Vault setup** — copy your vault variant, install Obsidian plugins, configure Templater and Periodic Notes
4. **MCP connection** — connect Claude Code to your vault via `@bitbonsai/mcpvault`
5. **Scripts setup** — configure paths, install dependencies, run the health check

Full instructions in [SETUP.md](SETUP.md).

---

## Vault Variants

| Variant | Best for |
|---------|----------|
| `vault/consulting/` | Client-facing roles, BD, account management — structured around clients, opportunities, and meetings |
| `vault/general/` | Knowledge workers, researchers, writers — structured around projects, learning, and meetings |

Copy one variant to your Obsidian vault location (outside this repo) and open it in Obsidian.

---

## Structure

```
ai-digital-brain/
├── CLAUDE.md                  # Template workspace context (personalize with LLM)
├── SETUP.md                   # Full setup guide
├── 00_Skills/                 # Skill library
│   ├── Core/                  # Voice, workspace, Obsidian
│   ├── Agents/                # Three-agent pipeline
│   ├── Clients/               # Client skill stubs
│   └── Technical/             # Domain skill stubs
├── scripts/                   # Vault management scripts
│   ├── README.md              # Script reference and setup
│   └── ...
├── vault/
│   ├── consulting/            # Copy to Obsidian vault location
│   └── general/               # Or this one
└── .claude/
    ├── settings.json          # Permissions + session hooks
    └── commands/pipeline.md   # /pipeline command
```

---

## The Agent Pipeline

Three agents in `00_Skills/Agents/` that demonstrate the coordinator + specialist pattern:

- **Coordinator** — reads your request and routes to the right specialist
- **Research** — takes a topic and returns a structured brief
- **Deliverable** — takes a brief and produces a polished output (email, summary, one-pager)

Works for consulting, writing, sales, or any knowledge-work role. Run via `/pipeline` or load agents directly.

---

## Skills

Skills are markdown files that load context into Claude Code. The core skills:

| Skill | What it does |
|-------|-------------|
| `your-voice-SKILL.md` | Writing standards, banned words, tone rules |
| `workspace-SKILL.md` | Folder structure, naming conventions |
| `obsidian-SKILL.md` | Vault structure and MCP usage |

Stub templates in `00_Skills/Clients/` and `00_Skills/Technical/` show how to create your own.

---

## License

MIT
