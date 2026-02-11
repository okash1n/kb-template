---
name: kb-organize
description: ~/kb を整理する（配置の整合、inboxの解消、重複の統合提案、tagsの正規化など）。Use when you want to refactor, reorganize, or clean up the kb repository.
compatibility: Filesystem-based agents with bash, rg, git, uv, and local file access.
---

# kb-organize

## いつ使うか

- `notes/inbox/` が増えてきた
- `domain: cross` を確定して分類したい
- `notes/patterns/` にまとめたいパターンがある
- ルールを変更したので、全体を再配置したい

## ルールの正本

- `ops/rules/kb.rules.yml` を正として扱う
- 変更したら `lint` → `organize` を回す
- 整理操作は git を必須とする（`kb organize` は内部で `git mv` を使う）
- `kb organize` は未付与の `scope` / `created_by` / `created_os` を後付け補完する
- `kb organize` は `related` から Obsidian 向けの自動リンクブロックを本文に再生成する

## 手順（機械的な整合）

```bash
git status --short
uv run --project ops kb lint
uv run --project ops kb organize
uv run --project ops kb lint
```

`kb organize` は内部で `git pull --ff-only` → 配置修正（`git mv`）+ メタデータ補完 → `git add -A` → `git commit` → `git push` を実行する。

## 手順（中身の整理）

- 重複が疑われるノートを `summary/tags` で探索して、統合方針を決める
- 統合したら `related` を更新して参照関係を残す
- 内容編集を伴った場合は `git add -A` → `git commit -m "ナレッジ内容を整理"` → `git push` を必ず行う
