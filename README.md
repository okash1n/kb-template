# kb-template

`git + ripgrep + LLM推論` で運用する個人ナレッジベースのテンプレート。

RAGサーバーやベクトルDBを使わず、Anthropicが提唱する「エージェンティック検索」の思想に沿った設計。Claude Code、Codex、Gemini CLIなど複数のAIコーディングツールで横断的に利用できる。Obsidian Vault としても機能し、GUI での閲覧とグラフビューによるノート間の関連可視化が可能。ノートの追加・編集は AI ツールや CLI が担い、Obsidian はビューアとして併用する設計。

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

`setup.sh` は以下の環境変数でスキル配置先を制御できる。未設定の場合はデフォルトパスに配置される。

| ツール | 環境変数 | デフォルトパス |
|--------|----------|---------------|
| Claude Code | `CLAUDE_SKILLS_DIR` or `CLAUDE_CONFIG_DIR`/skills | `~/.config/claude/skills` |
| Codex | `CODEX_HOME`/skills | `~/.config/codex/skills` |
| Gemini CLI | `GEMINI_SKILLS_DIR` or `GEMINI_CLI_HOME`/.gemini/skills | `~/.gemini/skills` |

#### Cursor / Windsurf など他のツールで使う場合

Cursor や Windsurf は `AGENTS.md` を認識するため、kb リポジトリをプロジェクトとして開けば規約は自動的に読み込まれる。ただし、スキル（kb-search 等）の仕組みには対応していないため、CLI 経由で操作する。

#### Claude Desktop / claude.ai から使う場合

filesystem MCP サーバー経由で `~/kb` を公開することを推奨する。これにより、Claude Desktop や claude.ai の Projects からもナレッジベースの読み書きが可能になる。

ノートを新規追加する場合は、まず `notes/drafts/` にファイルを作成し、あとから Claude Code 等の **kb-update** スキルで正式に取り込む運用を推奨する。kb-update が frontmatter の付与、適切なディレクトリへの配置、git commit/push を一括で行うため、追加履歴が Git で管理される。

例: Claude Desktop でリサーチした結果を `notes/drafts/my-research.md` に保存 → Claude Code で kb-update を実行 → 現在のルールに従って分類・配置される。

### 4. Obsidian を設定（任意）

`notes/` ディレクトリを Obsidian Vault として開く。Vault 設定（`.obsidian/`）は `.gitignore` されるため、マシンごとに異なる設定を持てる。

Obsidian はナレッジの**閲覧・検索ビューア**として利用する。グラフビューでノート間の関連を可視化したり、タグやリンクでナレッジを辿るのに適している。正式なノートの追加・編集は AI ツールや CLI 経由で行う（frontmatter の整合性や git 管理が保たれるため）。

Obsidian 上で書きたい場合は `notes/drafts/` に下書きを作成し、内容が固まったら **kb-update** スキルで正式に取り込む。`drafts/` は lint/organize の対象外なので、形式を気にせず自由に書ける。

取り込み例（Claude Code に指示する場合）:

```
notes/drafts/my-research.md を kb-update で取り込んで
```

kb-update が下書きの内容を読み取り、kind/domain の判定、frontmatter の付与、適切なディレクトリへの配置、git commit/push までを一括で行う。

### 5. GitHub Actions を設定（任意）

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
- **kb-update**: ノートの追加・更新（drafts からの取り込みもこちら）
- **kb-organize**: 配置整理・メタデータ補完

## ディレクトリ構成

```
~/kb/
├── notes/                 # ナレッジ本体（Obsidian Vault としても利用可能）
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

## 設計思想

詳しくは [ops/docs/CONCEPT.md](ops/docs/CONCEPT.md) を参照。

## ライセンス

[CC0 1.0](LICENSE)
