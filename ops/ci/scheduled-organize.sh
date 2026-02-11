#!/usr/bin/env bash
# ローカル cron / launchd から呼び出す KB 自動整理スクリプト
# claude -p によるヘッドレス実行で、LLM推論による整理を行う
set -euo pipefail

REPO_ROOT="${KB_REPO_ROOT:-$HOME/kb}"
LOG_FILE="${REPO_ROOT}/ops/automation/organize-schedule.log"
WATCH_PATHS=("notes" "ops/rules/kb.rules.yml")

cd "$REPO_ROOT"

timestamp_jst() {
  TZ=Asia/Tokyo date '+%Y-%m-%dT%H:%M%:z'
}

head_sha() {
  git rev-parse --short=12 HEAD
}

last_auto_sha() {
  git log --grep '\[organize-auto\]' --format='%H' -n 1 -- || true
}

append_log() {
  local status="$1"
  local reason="$2"
  local base_sha="$3"
  mkdir -p "$(dirname "$LOG_FILE")"
  printf '%s\t%s\treason=%s\thead=%s\tbase=%s\n' \
    "$(timestamp_jst)" \
    "$status" \
    "$reason" \
    "$(head_sha)" \
    "$base_sha" >> "$LOG_FILE"
}

ensure_main_branch() {
  local branch
  branch="$(git rev-parse --abbrev-ref HEAD)"
  if [[ "$branch" != "main" ]]; then
    echo "Expected branch main, got: $branch" >&2
    exit 2
  fi
}

main() {
  ensure_main_branch
  git pull --ff-only origin main

  local base_sha
  base_sha="$(last_auto_sha)"

  if [[ -n "$base_sha" ]]; then
    if git diff --quiet "$base_sha"..HEAD -- "${WATCH_PATHS[@]}"; then
      append_log "skipped" "no-updates-since-last-organize" "$base_sha"
      git add "$LOG_FILE"
      if ! git diff --cached --quiet; then
        git commit -m "organizeをスキップ: 変更なし [organize-auto]"
        git push origin HEAD:main
      fi
      exit 0
    fi
  fi

  cat ops/skills/kb-organize/SKILL.md | claude -p \
    --allowedTools "Bash(git:*),Bash(uv:*),Read,Write,Edit,Glob,Grep"

  append_log "executed" "organize-ran" "${base_sha:-none}"
  git add "$LOG_FILE"
  if ! git diff --cached --quiet; then
    git commit -m "organize実行ログを記録 [organize-auto]"
    git push origin HEAD:main
  fi
}

main "$@"
