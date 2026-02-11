# kb-template

`git + ripgrep + LLM推論` で運用する個人ナレッジベースのテンプレート。

RAGサーバーやベクトルDBを使わず、Anthropicが提唱する「エージェンティック検索」の思想に沿った設計。Claude Code、Codex、Gemini CLIなど複数のAIコーディングツールで横断的に利用できる。

## セットアップ

### 1. リポジトリを作成

GitHub で「Use this template」をクリックしてリポジトリを作成するか、手動でクローンする。

```bash
git clone <your-repo-url> ~/kb
cd ~/kb
```

> リポジトリのクローン先は `~/kb` を推奨。スキルやCLIがこのパスを前提としている。

### 2. 依存関係をインストール

[uv](https://docs.astral.sh/uv/) が必要。

```bash
uv sync --project ops
```

### 3. スキルを配置

Claude Code / Codex / Gemini CLI にスキルをシンボリックリンクで配置する。

```bash
bash ops/setup.sh
```

### 4. GitHub Actions を設定（任意）

`.github/workflows/organize.yml` の `GIT_AUTHOR_NAME` / `GIT_AUTHOR_EMAIL` / `GIT_COMMITTER_NAME` / `GIT_COMMITTER_EMAIL` を自分の情報に書き換える。

このワークフローは12時間ごとに `kb organize` を自動実行し、配置の整合やメタデータの補完を行う。

## 使い方

### CLI

```bash
# ノートを新規作成
uv run --project ops kb new --kind note --domain dev --summary "要約" --tag tag1 --scope cross

# 検索
uv run --project ops kb search "クエリ"

# 整合性チェック
uv run --project ops kb lint

# 配置整理（メタデータ補完、ディレクトリ移動、Obsidianリンク生成）
uv run --project ops kb organize

# ULIDからファイルパスを解決
uv run --project ops kb resolve <ULID>
```

### スキル（AI コーディングツール経由）

スキルを配置済みであれば、AIツール上でナレッジベースを操作できる。

- **kb-search**: ナレッジの検索（ripgrep + 推論）
- **kb-update**: ノートの追加・更新
- **kb-organize**: 配置整理・メタデータ補完

## ディレクトリ構成

```
~/kb/
├── notes/                 # ナレッジ本体
│   ├── inbox/             # 未分類
│   ├── dev/               # 開発
│   ├── infra/             # インフラ
│   ├── ai/                # AI
│   ├── security/          # セキュリティ
│   ├── tools/             # ツール
│   ├── product/           # プロダクト
│   ├── life/              # 生活
│   ├── patterns/          # パターン集
│   └── drafts/            # 下書き（lint/organize 対象外）
├── ops/                   # 運用ツール
│   ├── src/               # CLI 実装
│   ├── rules/             # ルール定義
│   ├── skills/            # AIツール向けスキル
│   ├── tests/             # テスト
│   ├── ci/                # CI スクリプト
│   └── docs/              # 設計ドキュメント
├── AGENTS.md              # AIツール向け規約
├── CLAUDE.md -> AGENTS.md
└── GEMINI.md -> AGENTS.md
```

## ノートの書き方

各ノートは YAML frontmatter を持つ。

```yaml
---
id: 01J0Z3N3Y7F4K2M9Q3T5A6B7C8       # ULID（自動生成）
kind: note                             # 種別
domain: dev                            # ドメイン
summary: このノートの要点を1-2文で     # 必須
tags:                                  # 英語小文字
  - docker
  - nginx
created: 2026-02-10T23:15+09:00
updated: 2026-02-10T23:15+09:00
---

本文をここに書く。
```

ファイル名は `{slug}--{ULID}.md`（例: `note--01J0Z3N3Y7F4K2M9Q3T5A6B7C8.md`）。

### 種別（kind）

| kind | 用途 |
|------|------|
| inbox | 未整理のメモ |
| note | 一般的なノート |
| research | 調査・分析 |
| decision | 判断記録 |
| troubleshoot | トラブルシューティング |
| howto | 手順書 |
| pattern | 再利用可能なパターン |

### ドメイン（domain）

| domain | 用途 |
|--------|------|
| dev | 開発 |
| infra | インフラ |
| ai | AI |
| security | セキュリティ |
| tools | ツール |
| product | プロダクト |
| life | 生活 |
| cross | 分野横断（未分類） |

## カスタマイズ

### ドメイン・種別の変更

`ops/rules/kb.rules.yml` を編集する。ドメインを追加した場合は `notes/` 配下に対応するディレクトリも作成し、`AGENTS.md` のノート対象ディレクトリ一覧も更新する。

### タイムゾーン

デフォルトは `Asia/Tokyo`（JST）。`ops/rules/kb.rules.yml` の `timezone` と `ops/src/kb_repo_tools/timeutil.py` を変更する。

### Obsidian との併用

`notes/` ディレクトリを Obsidian Vault として開けば、GUI でもノートを閲覧・編集できる。`kb organize` が生成する wikilink ブロックにより、関連ノート間のリンクが自動で維持される。

## 設計思想

詳しくは [ops/docs/CONCEPT.md](ops/docs/CONCEPT.md) を参照。

## ライセンス

[CC0 1.0](LICENSE)
