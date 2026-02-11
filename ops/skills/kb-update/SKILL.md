---
name: kb-update
description: ~/kb にノートを追加・更新する（重複確認、kind/domain付与、summary/tags更新、updated更新、配置の整合まで）。Use when adding notes, updating existing knowledge, or capturing new information into the kb repo.
compatibility: Filesystem-based agents with bash, rg, git, uv, and local file access.
---

# kb-update

## いつ使うか

- 新しい知見をKBに追加したい
- 既存ノートに追記・訂正したい
- `summary/tags` を整えて検索精度を上げたい

## 基本方針

- 作業開始前に必ず `git pull --ff-only` で同期する
- まず **既存があるか** を `rg` で確認する（重複を増やさない）
- 参照は `related`（ULID）を正とする
- `summary` は必須で、内容が変わったら更新する
- `scope` は `cross|os-specific` を使い、OS差分は本文の `## 適用環境` に明示する
- `created_by` / `created_os` は `kb new` で自動付与される（`created_by` は通常 hostname）。既存ノートは `kb organize` で補完できる
- 配置は `uv run --project ops kb organize` で揃える
- すべての更新は git 管理下で実施し、最後に必ずコミットする

## 手順（新規追加）

1. `git pull --ff-only`
2. `git status --short` で作業ツリーを確認する
3. 既存確認（`summary/tags/本文` を検索）
4. `kind` と `domain` を決める（不確実なら `domain: cross` で `notes/inbox/` に置く）
5. `summary` を1〜2文で作る（日本語）
6. `tags` を必要に応じて付ける（英語小文字、ハイフン区切り）
7. 作成

```bash
uv run --project ops kb new --kind note --domain dev --scope cross --summary "..." --tag okta --tag glean
```

8. `kb new` は内部で `git add -A` → `git commit` → `git push` まで実行する
9. `related` を設定した場合は `uv run --project ops kb organize` を実行して Obsidian 向け自動リンクブロックを生成する
10. 必要なら `uv run --project ops kb lint` を実行して整合性を確認する

## 手順（更新）

1. `git pull --ff-only`
2. `git status --short` で作業ツリーを確認する
3. 対象ノートを特定（`kb-search` の要領）
4. 本文を追記/修正
5. `summary` と `tags` を見直して更新（必要なら `related` も追加）
6. `related` を追加・変更した場合は `uv run --project ops kb organize` を実行して Obsidian 向け自動リンクブロックを再生成する
7. `uv run --project ops kb lint`
8. `git add -A` → `git commit -m "ナレッジを更新"`（内容に合わせて具体化）
9. `git push`
