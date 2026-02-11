# ナレッジリポジトリ構想まとめ

## コンセプト

RAGサーバーやベクトルDBを使わず、**gitリポジトリ + ripgrep + LLMの推論力**で個人ナレッジベース（外部脳）を構築する。

Anthropic自身がClaude Agent SDKのドキュメントで「セマンティック検索よりエージェンティック検索（grep + LLM推論）を推奨」と明言しており、Claude Codeもembeddingを一切使わずripgrepとファイルグロブだけでコードナビゲーションを実装している。この構成はその方向性と一致する。

## なぜRAGではないのか

- 個人のナレッジ規模（数百〜数千ファイル）ではembeddingモデルの選定・チャンク戦略・ベクトルDB運用のオーバーヘッドが検索精度の向上に見合わない
- LLMがripgrepの検索主体になることで、セマンティック検索の「意味的マッチング」をLLM側の推論で代替できる
- 枯れた技術（git, ファイルシステム, grep）の組み合わせで十分な結果が出るなら、それが最善

## アーキテクチャ

### リポジトリ構成

```text
~/kb/                      # kb = knowledge base の略
├── AGENTS.md              # 共通規約ファイル（正本）
├── CLAUDE.md -> AGENTS.md
├── GEMINI.md -> AGENTS.md
├── notes/                 # 実際のナレッジ
│   ├── inbox/
│   ├── dev/
│   ├── infra/
│   ├── ai/
│   ├── security/
│   ├── tools/
│   ├── product/
│   ├── life/
│   └── patterns/
├── ops/                   # リポジトリ運用の実装
│   ├── setup.sh
│   ├── rules/
│   │   ├── kb.rules.yml
│   │   └── KB_RULES.md
│   ├── skills/
│   │   ├── kb-search/SKILL.md
│   │   ├── kb-update/SKILL.md
│   │   └── kb-organize/SKILL.md
│   ├── pyproject.toml
│   ├── src/kb_repo_tools/
│   ├── tests/
│   └── docs/CONCEPT.md
└── README.md
```

スキル自体が「このリポジトリの使い方」というナレッジであり、リポジトリ内で一元管理する。スキルもgit管理されるため、LLMによるスキル手順の改善もコミット履歴に残る。

### frontmatterスキーマ（例）

```yaml
---
id: 01J0Z3N3Y7F4K2M9Q3T5A6B7C8               # ULID（参照の正）
kind: research                                # 種別
domain: dev                                   # 領域（粗い集合）
scope: cross                                  # 適用範囲（任意: cross|os-specific）
created_by: kb-host-01                        # 作成ホスト（任意: 自動付与）
created_os: macos                             # 作成時OS（任意: 自動付与）
title: OktaユーザーデータのGlean連携          # 日本語（任意）
summary: Okta属性の制約を回避してGleanのディレクトリ検索を機能させた手順  # 日本語（必須）
tags:                                         # 英語・小文字（任意。機械向け索引）
  - okta
  - glean
related:                                      # ULID配列
  - 01J0Z3N3Y7F4K2M9Q3T5A6B7C9
created: 2026-02-10T23:15+09:00               # JST固定（分まで）
updated: 2026-02-10T23:15+09:00               # JST固定（分まで）
---
```

#### 言語規則（CLAUDE.mdに明記する）

| フィールド | 言語 | 備考 |
|-----------|------|------|
| id | — | ULID（大文字） |
| kind | — | `inbox|note|research|decision|troubleshoot|howto|pattern` |
| domain | — | `dev|infra|ai|security|tools|product|life|cross` |
| scope | — | `cross|os-specific`（任意。未指定は `cross` 扱い） |
| created_by | — | 作成ホスト識別子（任意。`kb new/organize` が補完） |
| created_os | — | `macos|linux|windows|other`（任意。`kb new/organize` が補完） |
| title | 日本語 | — |
| tags | 英語・小文字 | 表記揺れ防止。技術用語はそのまま（例: `auth`, `okta`, `csv`） |
| summary | 日本語 | — |
| related | — | ULID配列（参照の正は `id`） |
| 本文 | 日本語 | — |
| created/updated | — | JST固定（`YYYY-MM-DDTHH:MM+09:00`） |

- frontmatterのスキーマ（必須フィールド、tagsの粒度、言語規則）はCLAUDE.mdに明記し、LLMが整理時に揺れないようにする
- ルールの正本は `ops/rules/kb.rules.yml` とし、Markdown側（`ops/rules/KB_RULES.md`）は解説に寄せる（ルール変更に追従しやすくする）
- `troubleshoot` / `howto` の本文テンプレでは `## 適用環境`（確認済み・未確認見込み・非対応/注意）を埋めてOS差分を表現する

### CLAUDE.md / AGENTS.md と skill の役割分担

| 項目 | CLAUDE.md / AGENTS.md | skill |
|------|----------------------|-------|
| 役割 | **何を守るか**（規約） | **どうやるか**（手順） |
| 読まれるタイミング | ツール起動時に自動で読む | タスク実行時に呼び出される |
| 内容 | frontmatterスキーマ定義、ディレクトリ構成ルール、命名規則 | 検索・更新・整理の具体的手順 |

CLAUDE.mdとAGENTS.mdは同じリポジトリに共存させ、それぞれのツールが自分の規約ファイルだけ読む。内容は基本同じだが、ツール固有の記法がある場合は個別に調整する。

規約ファイルに全部書くとコンテキスト圧迫、skillに全部書くと呼び出されない限り規約が効かない。両方に書くとDRY違反でズレる。

## skillに必要な3つの能力

### 1. 検索

- frontmatterの `tags` / `summary` をripgrepでトリアージ → 該当ファイルの本文を読む2段階戦略
- 曖昧なクエリでもLLMが推論で適切な検索語を生成できる

### 2. 更新

- 新規ドキュメント追加、既存ドキュメントの加筆
- frontmatterスキーマに従ってメタデータを付与
- gitコミットまで含めて自動化

### 3. 整理

- タグの正規化、重複ナレッジの統合、ディレクトリ配置の見直し
- cronでヘッドレスモード（`claude -p "kbリポジトリを整理して"`）による自動整理も可能
- 整理結果が気に入らなければ `git diff` で確認、`git revert` で戻せる

## マルチマシン・マルチツール運用

- すべてのマシンでホームディレクトリの同じ場所（例: `~/kb`）にクローン
- 固定パスを前提にskillを汎用的に記述できる
- Claude Codeではネイティブにファイルアクセス、claude.ai等からはfilesystem MCP経由で同じパスを参照
- クライアントを選ばない外部脳がRAGサーバーなしで成立する

### クロスツールのスキル配信

SKILL.mdの形式はAgent Skills open standard準拠で、Claude Code・Codex・Gemini CLIで共通。スキルの正本はリポジトリ内の1箇所に置き、各ツールのスキルディレクトリからシンボリックリンクで参照する。

```bash
# Claude Code
ln -s ~/kb/ops/skills/kb-search "${CLAUDE_SKILLS_DIR:-${CLAUDE_CONFIG_DIR:-$HOME/.config/claude}/skills}/kb-search"
ln -s ~/kb/ops/skills/kb-update "${CLAUDE_SKILLS_DIR:-${CLAUDE_CONFIG_DIR:-$HOME/.config/claude}/skills}/kb-update"
ln -s ~/kb/ops/skills/kb-organize "${CLAUDE_SKILLS_DIR:-${CLAUDE_CONFIG_DIR:-$HOME/.config/claude}/skills}/kb-organize"

# Codex
ln -s ~/kb/ops/skills/kb-search "${CODEX_HOME:-$HOME/.config/codex}/skills/kb-search"
ln -s ~/kb/ops/skills/kb-update "${CODEX_HOME:-$HOME/.config/codex}/skills/kb-update"
ln -s ~/kb/ops/skills/kb-organize "${CODEX_HOME:-$HOME/.config/codex}/skills/kb-organize"

# Gemini CLI
ln -s ~/kb/ops/skills/kb-search "${GEMINI_SKILLS_DIR:-${GEMINI_CLI_HOME:-$HOME}/.gemini/skills}/kb-search"
ln -s ~/kb/ops/skills/kb-update "${GEMINI_SKILLS_DIR:-${GEMINI_CLI_HOME:-$HOME}/.gemini/skills}/kb-update"
ln -s ~/kb/ops/skills/kb-organize "${GEMINI_SKILLS_DIR:-${GEMINI_CLI_HOME:-$HOME}/.gemini/skills}/kb-organize"
```

リポジトリにセットアップスクリプト（`ops/setup.sh`）を含めておけば、新しいマシンでも `git clone → ./ops/setup.sh` で完了。`git pull` すれば全マシン・全ツールにスキルの更新が反映される。

### 対応表

| | Claude Code | Codex | Gemini CLI |
|---|---|---|---|
| 規約ファイル | `CLAUDE.md` | `AGENTS.md` | `GEMINI.md` |
| スキル配置先 | `${CLAUDE_CONFIG_DIR}/skills`（上書き: `CLAUDE_SKILLS_DIR`） | `${CODEX_HOME}/skills` | `${GEMINI_CLI_HOME}/.gemini/skills`（上書き: `GEMINI_SKILLS_DIR`） |
| スキル形式 | `SKILL.md` | `SKILL.md`（共通） | `SKILL.md`（共通） |
| スキル呼び出し | 自動 or `/skill-name` | 自動 or `$skill-name` | 自動 |

## 運用上の注意点

### git競合の防止

- cronで自動整理を実行するマシンは1台に限定する
- 整理前に必ず `git pull` するルールをskillに組み込む

### ヘッドレス整理の暴走防止

- 「変更内容のサマリをコミットメッセージに詳細に書く」ルールをskillに入れる
- `git log --oneline` で異変に気づけるようにする

## 背景：業界の潮流

- Anthropic公式（Claude Agent SDK）: 「セマンティック検索はエージェンティック検索より精度が低く、メンテナンスが難しく、透明性も低い。まずはエージェンティック検索から始めよ」
- Claude Code: 最初からembeddingもベクトルDBも不使用。ripgrepとファイルグロブのみ
- 議論の変化: grepとセマンティック検索の比較自体が文脈を見誤っており、LLMの推論力でembeddingモデルの意味理解を代替する「エージェンティック検索」が新たなパラダイムとして台頭
