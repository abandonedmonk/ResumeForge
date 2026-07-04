#!/usr/bin/env sh
# Install ResumeForge as an agent skill.
#
#   1. Install the `resumeforge` CLI (pipx preferred; falls back to pip -e . from a clone).
#   2. Run `resumeforge init` to check LaTeX + provider keys and scaffold .env.
#   3. Copy this skill into ~/.claude/skills/resumeforge/ (Claude Code / OpenCode).
#
# Idempotent and non-interactive. For Codex, see skill/README.md.
set -eu

# Resolve skill/ (parent of this scripts/ dir) and the repo root (parent of skill/).
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SKILL_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SKILL_DIR/.." && pwd)

echo "ResumeForge skill installer"
echo "  skill dir: $SKILL_DIR"

# 1. Install the CLI.
if command -v resumeforge >/dev/null 2>&1; then
  echo "  resumeforge already on PATH — skipping install."
elif command -v pipx >/dev/null 2>&1; then
  echo "  Installing resumeforge via pipx..."
  if [ -f "$REPO_ROOT/pyproject.toml" ]; then
    pipx install --force "$REPO_ROOT"
  else
    pipx install --force resumeforge
  fi
elif [ -f "$REPO_ROOT/pyproject.toml" ]; then
  echo "  pipx not found — installing editable via pip from the clone..."
  python -m pip install -e "$REPO_ROOT"
else
  echo "  pipx not found and no local clone — installing from PyPI via pip..."
  python -m pip install resumeforge
fi

# 2. Check LaTeX + keys (never fatal — informational).
echo "  Running 'resumeforge init'..."
resumeforge init --no-install || true

# 3. Copy the skill into Claude Code's skills directory.
DEST="$HOME/.claude/skills/resumeforge"
mkdir -p "$DEST"
# Copy skill contents without nesting a second 'skill' dir.
cp -R "$SKILL_DIR/." "$DEST/"
echo "  Installed skill to $DEST"

echo
echo "Done. Restart your agent CLI so it picks up the skill."
echo "Try:  \"roast my resume\"  or  \"tailor my resume for this JD\""
echo "Codex users: add this to ~/.codex/config.toml ->"
echo "  [[skills.config]]"
echo "  path = \"$DEST/SKILL.md\""
