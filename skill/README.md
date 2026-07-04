# ResumeForge — Agent Skill

Make ResumeForge callable from any agent CLI. The agent orchestrates (reads the JD,
confirms paths, presents results); ResumeForge does the résumé generation on its own
**free** provider cascade — so your paid subscription isn't spent on bullet writing.

## What it does

| Command | Use it for |
|---|---|
| `resumeforge tailor`    | Tailor a résumé to a JD → one-page LaTeX PDF + compression receipt |
| `resumeforge roast`     | Brutally honest, shareable `[ROAST] → [FIX]` feedback |
| `resumeforge cold-read` | Zero-context recruiter read: targeted role / strongest fit / biggest gap |
| `resumeforge gap`       | What the résumé is missing vs the user's actual GitHub work |
| `resumeforge receipt`   | Re-print the compression receipt for a past run |

Every result command supports `--json` (agents should always use it).

## Install

### One command (Claude Code / OpenCode)

```bash
bash skill/scripts/install.sh
```

This installs the `resumeforge` CLI (pipx preferred), runs `resumeforge init`, and copies
this skill to `~/.claude/skills/resumeforge/`. Restart your agent CLI afterward.

### Manual

```bash
pipx install resumeforge                 # or: pip install -e .   (from a clone)
cp -r skill/ ~/.claude/skills/resumeforge/
```

### Codex CLI

```bash
cp -r skill/ ~/.codex/skills/resumeforge/
# then add to ~/.codex/config.toml:
#   [[skills.config]]
#   path = "~/.codex/skills/resumeforge/SKILL.md"
```

### Gemini CLI / others

Any agent that reads Open-Agent-Skill `SKILL.md` files: point it at
`~/.claude/skills/resumeforge/SKILL.md` (or its own skills directory). The skill's
`description` frontmatter drives intent matching.

### MCP clients (alternative)

Prefer MCP over shelling out to the CLI? ResumeForge also ships a local stdio MCP
server (`pip install "resumeforge[mcp]"`) exposing the same operations as typed tools.
Register `{"mcpServers": {"resumeforge": {"command": "resumeforge-mcp"}}}` — see the
root README's "MCP server" section.

## Requirements

- Python 3.11+ and the `resumeforge` CLI on PATH.
- At least one free provider key (e.g. `GROQ_API_KEY`) in the user's `.env`
  (`resumeforge init` scaffolds it).
- `pdflatex` only for `tailor` (TinyTeX auto-install via `resumeforge init`).

## Files

```
skill/
├── SKILL.md            # agent instructions (the actual skill)
├── agents/
│   ├── claude.yaml     # Claude Code metadata
│   └── openai.yaml     # Codex metadata
├── scripts/install.sh  # installer
└── README.md           # this file
```
