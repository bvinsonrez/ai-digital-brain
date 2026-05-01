# Setup Guide

> **Platform:** Mac and Linux. Shell scripts and path syntax are Unix-native.
> **Windows:** WSL2 users can adapt paths, but this guide assumes Unix paths throughout.

---

## Before You Start

**Required:**
- [ ] Claude Code installed and authenticated: [claude.ai/code](https://claude.ai/code), then run `claude login`
- [ ] [Obsidian](https://obsidian.md) installed
- [ ] Node.js + npm (for MCP server): `node --version` should return v18 or higher
- [ ] Python 3.10+: `python3 --version`

**Obsidian community plugins (install after vault setup):**
- Dataview — powers vault queries and hub note tables
- Templater — required for Templates folder to work (plain Obsidian templates won't handle dynamic date fields)
- Periodic Notes — manages daily and weekly notes into configured folders

**Optional but recommended:**
- [Granola](https://granola.ai) (Mac, paid) — automates meeting note sync to Obsidian; manual fallback is documented below
- [Superpowers](https://superpowers.so) plugin for Claude Code — enables skill auto-loading from `settings.json`; without it, skills still work but must be invoked manually

---

## Step 1: Workspace Personalization

This step uses Claude to help you customize the workspace templates for your situation.

1. Clone this repo and open it in Claude Code:
   ```bash
   git clone https://github.com/bvinsonrez/ai-digital-brain.git ~/ai-digital-brain
   claude ~/ai-digital-brain
   ```

2. Paste `CLAUDE.md` into Claude with this prompt:
   > "Help me customize this CLAUDE.md for my own setup. Ask me questions one at a time about my role, tools, and workflow."

3. Save the result as `CLAUDE.md`. Commit the change:
   ```bash
   git add CLAUDE.md && git commit -m "chore: personalize CLAUDE.md"
   ```

4. Do the same for `00_Skills/Core/your-voice-SKILL.md`.

---

## Step 2: Vault Setup

1. **Choose your vault variant.** Copy one folder to your Obsidian vault location (outside the git repo):
   ```bash
   # Consulting/BD variant:
   cp -r ~/ai-digital-brain/vault/consulting ~/obsidian-vaults/my-vault

   # General knowledge worker variant:
   cp -r ~/ai-digital-brain/vault/general ~/obsidian-vaults/my-vault
   ```
   Adjust the destination path to wherever you keep your Obsidian vaults.

2. **Open the vault in Obsidian.** File → Open Vault → select the folder you just copied.

3. **Install community plugins.** Settings → Community Plugins → Browse. Install and enable:
   - **Dataview**
   - **Templater**
   - **Periodic Notes**

4. **Configure Templater — critical step.**
   Settings → Templater → Template folder location → set to `Templates`
   Without this, Templater won't find the shipped templates and will silently fail.

5. **Configure Periodic Notes — critical step.**
   Settings → Periodic Notes:
   - Daily Notes → Folder: `Periodic Notes/Daily`
   - Weekly Notes → Folder: `Periodic Notes/Weekly` → Template: `Templates/Weekly Review`
   Without this, the plugin dumps notes in the vault root.

6. **(Consulting vault only) Granola setup.**
   If using Granola: install the Granola Obsidian plugin and point it at `Meetings/Granola/`.
   If not using Granola: delete `Meetings/Granola/` — the folder will re-create itself if you add Granola later. Create meeting notes manually using `Templates/Meeting Note.md` and store them in `Meetings/Notes/`.

7. **Edit `obsidian-SKILL.md` to match your vault variant.**
   Open `00_Skills/Core/obsidian-SKILL.md` and delete the section for the variant you didn't choose.

---

## Step 3: MCP Connection

The `@bitbonsai/mcpvault` MCP server is what lets Claude Code read and write your Obsidian vault. This is the most important dependency in the system.

The version used during development is `@bitbonsai/mcpvault@0.3.2`. Check npm for a newer stable release before pinning your own version.

### Option A — Global config (recommended for personal use)

Makes the vault accessible in any Claude Code workspace on this machine.

Edit `~/.claude.json` (create it if it doesn't exist) and add:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "npx",
      "args": ["@bitbonsai/mcpvault@0.3.2", "/path/to/your/vault"]
    }
  }
}
```

Replace `/path/to/your/vault` with the absolute path to your vault folder.

### Option B — Project config (for team sharing)

Scopes the MCP connection to this workspace only. Create `.mcp.json` at the repo root:

```bash
claude mcp add --scope project obsidian npx @bitbonsai/mcpvault@0.3.2 /path/to/your/vault
```

Note: `.mcp.json` is gitignored (it contains your local vault path).

### Test the connection

In Claude Code:
```
Use mcp__obsidian__get_vault_stats to show me my vault statistics.
```

Expected: Claude returns a summary of note counts and folder structure from your vault.

If it fails on first try: close the Claude Code session and reopen — the MCP server initializes asynchronously and sometimes needs a second attempt.

---

## Step 4: Scripts Setup

1. **Copy and fill in the config:**
   ```bash
   cp scripts/config.example.py scripts/config.py
   ```
   Edit `scripts/config.py`:
   ```python
   VAULT_PATH = "/absolute/path/to/your/obsidian/vault"
   WORKSPACE_PATH = "/absolute/path/to/your/ai-digital-brain"
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   cd scripts
   python3 -m venv venv     # or: uv venv (if you have uv installed)
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Test with the vault health report:**
   ```bash
   cd scripts                    # must run from scripts/ directory
   source venv/bin/activate
   python -m vault_maintenance
   ```
   Expected: a report file written to your vault's `Inbox/` folder.

4. **For `enrich_notes.py` and `archive-pipeline/` only:**
   These two scripts call the Claude API directly (not through `claude login`). Set your API key:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```
   Get a key at [console.anthropic.com](https://console.anthropic.com). This is separate from `claude login`. No other script in this repo requires it.

---

## Troubleshooting

**Obsidian templates aren't working (dates show raw Templater syntax)**
→ Did you configure the Templater folder location? Settings → Templater → Template folder location → `Templates`

**Periodic Notes are going to the vault root**
→ Did you configure the folder paths? Settings → Periodic Notes → Daily Notes folder → `Periodic Notes/Daily`

**MCP tools missing from Claude Code session**
→ The server initializes asynchronously. Try again — it usually works on the second attempt. Do not diagnose by checking whether Obsidian is open (mcpvault does not use the REST API).

**Scripts error: "scripts/config.py not found"**
→ Run `cp scripts/config.example.py scripts/config.py` and fill in your vault path.

**Archive pipeline error: "ANTHROPIC_API_KEY not set"**
→ Run `export ANTHROPIC_API_KEY="sk-ant-..."` before running the script.
