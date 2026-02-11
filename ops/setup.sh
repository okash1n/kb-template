#!/usr/bin/env bash
set -euo pipefail

OPS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_SOURCE_ROOT="$OPS_ROOT/skills"
CLAUDE_SKILLS_ROOT="${CLAUDE_SKILLS_DIR:-${CLAUDE_CONFIG_DIR:-$HOME/.config/claude}/skills}"
CODEX_SKILLS_ROOT="${CODEX_HOME:-$HOME/.config/codex}/skills"
GEMINI_SKILLS_ROOT="${GEMINI_SKILLS_DIR:-${GEMINI_CLI_HOME:-$HOME}/.gemini/skills}"

link_dir() {
  local src="$1"
  local dst="$2"

  mkdir -p "$(dirname "$dst")"
  ln -sfn "$src" "$dst"
}

# Claude Code
link_dir "$SKILLS_SOURCE_ROOT/kb-search" "$CLAUDE_SKILLS_ROOT/kb-search"
link_dir "$SKILLS_SOURCE_ROOT/kb-update" "$CLAUDE_SKILLS_ROOT/kb-update"
link_dir "$SKILLS_SOURCE_ROOT/kb-organize" "$CLAUDE_SKILLS_ROOT/kb-organize"

# Codex
link_dir "$SKILLS_SOURCE_ROOT/kb-search" "$CODEX_SKILLS_ROOT/kb-search"
link_dir "$SKILLS_SOURCE_ROOT/kb-update" "$CODEX_SKILLS_ROOT/kb-update"
link_dir "$SKILLS_SOURCE_ROOT/kb-organize" "$CODEX_SKILLS_ROOT/kb-organize"

# Gemini CLI
link_dir "$SKILLS_SOURCE_ROOT/kb-search" "$GEMINI_SKILLS_ROOT/kb-search"
link_dir "$SKILLS_SOURCE_ROOT/kb-update" "$GEMINI_SKILLS_ROOT/kb-update"
link_dir "$SKILLS_SOURCE_ROOT/kb-organize" "$GEMINI_SKILLS_ROOT/kb-organize"

echo "Linked skills into:"
echo "  Claude: $CLAUDE_SKILLS_ROOT"
echo "  Codex : $CODEX_SKILLS_ROOT"
echo "  Gemini: $GEMINI_SKILLS_ROOT"
