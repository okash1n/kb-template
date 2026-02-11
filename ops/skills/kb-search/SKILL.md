---
name: kb-search
description: ~/kb を ripgrep と推論で検索して、関連ノート（id/summary/tags）と根拠箇所を特定する。Use when you need to find notes, troubleshoot, or answer questions from the kb repository.
compatibility: Filesystem-based agents with bash, rg, git, uv, and local file access.
---

# kb-search

## いつ使うか

- ユーザーが「以前のメモどこ？」「この結論の根拠は？」など、KB内の情報探索を求めているとき
- エラー文言・固有名詞・うろ覚えのフレーズから関連ノートを特定したいとき

## 基本方針（検索の順序）

1. **検索前に同期**: `git pull --ff-only`（または `uv run --project ops kb search` を使って自動同期）
2. **frontmatterからトリアージ**: `summary` と `tags` を優先して `rg` で当てる
3. **本文を確認**: 候補ファイルの本文を開いて根拠行を特定する
4. **関連を辿る**: `related` にある ULID を `kb resolve` で解決し、必要なら追加で読む
5. **適用範囲を確認**: `scope` と本文の `## 適用環境` を確認し、OS差分がある場合は適用可否を明示する

## コマンド例

### 1) 同期つき検索（推奨）

```bash
uv run --project ops kb search '<検索語>'
```

### 2) 手動トリアージ

```bash
git pull --ff-only
rg -n --hidden --glob '!**/.git/**' 'summary:|tags:|id:' notes/dev notes/infra notes/ai notes/security notes/tools notes/product notes/life notes/patterns notes/inbox
rg -n --hidden --glob '!**/.git/**' 'okta|glean|<検索語>' notes/dev notes/infra notes/ai notes/security notes/tools notes/product notes/life notes/patterns notes/inbox
```

### 3) id からファイルを解決

```bash
uv run --project ops kb resolve 01J0Z3N3Y7F4K2M9Q3T5A6B7C8
```

### 4) 仕上げ

- 回答には、該当ノートの **パス** と **根拠箇所（該当段落/行）** を必ず添える
