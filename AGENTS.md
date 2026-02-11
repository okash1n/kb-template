# kb リポジトリ（共通）

このリポジトリは、`git + ripgrep + LLM推論` で運用する個人ナレッジベースです。

## ルール（正本）

- ルールの正本: `ops/rules/kb.rules.yml`
- ルールの解説: `ops/rules/KB_RULES.md`

## ノートの対象ディレクトリ

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

## ノートの参照

- ノート間の関連付けは **ULID（`id`）** を正とする（`related` はULID配列）。
- OS差異があるノートは `scope`（`cross|os-specific`）と本文の `## 適用環境` で表現する。
- `kb organize` は未付与の `scope` / `created_by` / `created_os` を補完する。
- `kb organize` が管理する Obsidian自動リンクブロック（`kb:auto-related-links`）は手編集しない。

## CLI

Python/uvで `kb` CLI を提供する。

```bash
uv run --project ops kb search <query>
uv run --project ops kb lint
uv run --project ops kb organize
uv run --project ops kb resolve <ULID>
```

- `kb search` は実行前に `git pull --ff-only` を行う
- `kb new` は作成後に `git add -A` / `git commit` / `git push` まで行う
- `kb organize` は実行前に `git pull --ff-only`、実行後に `git add -A` / `git commit` / `git push` を行う
