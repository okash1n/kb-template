#!/usr/bin/env bash
set -euo pipefail

OPS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$OPS_ROOT/.." && pwd)"
LOG_FILE="ops/automation/organize-schedule.log"
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

commit_and_push_log() {
  local message="$1"
  git add "$LOG_FILE"
  if git diff --cached --quiet; then
    return 0
  fi
  git commit -m "$message"
  git push origin HEAD:main
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
      commit_and_push_log "organizeをスキップ: 変更なし [organize-auto]"
      exit 0
    fi
  fi

  uv run --project ops kb organize

  # kb organize is responsible for its own commit/push.
  append_log "executed" "organize-ran" "${base_sha:-none}"
  commit_and_push_log "organize実行ログを記録 [organize-auto]"
}

main "$@"
