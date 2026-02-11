# kb rules

このリポジトリのルールは「変わり続ける」前提で設計する。

## ルールの正本

- 正本: `ops/rules/kb.rules.yml`
- このファイルは解説（理由・例・運用メモ）を置く

## ノートの範囲

以下配下の `*.md` を「KBノート」として扱う。

- `notes/inbox/`
- `notes/dev/`
- `notes/infra/`
- `notes/ai/`
- `notes/security/`
- `notes/tools/`
- `notes/product/`
- `notes/life/`
- `notes/patterns/`

`ops/docs/CONCEPT.md` などのメタ文書は対象外。

## frontmatter（KBノート）

KBノートは YAML frontmatter を持つ。

必須フィールド:

- `id`: ULID（大文字）
- `kind`: `inbox|note|research|decision|troubleshoot|howto|pattern`
- `domain`: `dev|infra|ai|security|tools|product|life|cross`
- `created`: JST固定（分まで） `YYYY-MM-DDTHH:MM+09:00`
- `updated`: JST固定（分まで） `YYYY-MM-DDTHH:MM+09:00`
- `summary`: 日本語の要約（検索/分類のため）

任意フィールド:

- `scope`: 適用範囲（`cross|os-specific`）。未指定は `cross` として扱う
- `created_by`: 作成ホスト識別子（通常は hostname を自動付与）
- `created_os`: 作成時OS（`macos|linux|windows|other` を自動付与）
- `title`: 日本語（手入力しない前提。必要なら自動提案）
- `tags`: 英語小文字（人間が指定して検索しない前提。機械向け索引）
- `related`: ULID配列（参照の正は `id`）

例:

```yaml
---
id: 01J0Z3N3Y7F4K2M9Q3T5A6B7C8
kind: research
domain: dev
scope: cross
created_by: kb-host-01
created_os: macos
title: タイトル（任意）
summary: このノートの要点を1〜2文で書く
tags:
  - okta
  - glean
related:
  - 01J0Z3N3Y7F4K2M9Q3T5A6B7C9
created: 2026-02-10T23:15+09:00
updated: 2026-02-10T23:15+09:00
---
```

`kind: troubleshoot` / `kind: howto` は本文先頭に `## 適用環境` を置き、以下3行を埋める。

- 確認済み
- 未確認だが有効見込み
- 非対応/注意

`kb organize` は未付与の `scope` / `created_by` / `created_os` を後付け補完する（`updated` も更新）。
また `related` から本文末尾の Obsidian 自動リンクブロックを再生成する。

- 開始: `<!-- kb:auto-related-links:start -->`
- 終了: `<!-- kb:auto-related-links:end -->`
- この範囲は手編集しない

## 配置ルール（ディレクトリ）

- `kind: pattern` は常に `notes/patterns/`
- `kind: inbox` は常に `notes/inbox/`
- `domain: cross` は未分類のプレースホルダで、原則 `notes/inbox/` に置く（`kind` は `inbox` でなくてよい）
- それ以外は `notes/<domain>/` 配下に置く

## ファイル命名

`{slug}--{id}.md`

- `slug` は人間可読の識別子（後から自動リネームしない）
- `id` はULID（大文字、参照の正）

## 変更の進め方

1. `ops/rules/kb.rules.yml` を更新する
2. `uv run --project ops kb lint` で問題を把握する
3. `uv run --project ops kb organize` で配置を揃える
