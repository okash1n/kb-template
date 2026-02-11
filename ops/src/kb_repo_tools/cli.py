from __future__ import annotations

import os
import platform
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from getpass import getuser
from pathlib import Path
from typing import Any

import click

from .frontmatter import Doc, FrontmatterError, dump_frontmatter, read_doc, write_doc
from .notes import iter_note_paths, read_note
from .repo import Repo, RepoError, open_repo
from .timeutil import iso_jst_minute, now_jst
from .ulidutil import is_ulid, new_ulid


@dataclass
class Ctx:
    repo: Repo


AUTO_RELATED_START = "<!-- kb:auto-related-links:start -->"
AUTO_RELATED_END = "<!-- kb:auto-related-links:end -->"


def _rules_scope_values(rules: dict[str, Any]) -> list[str]:
    fm = rules.get("frontmatter", {})
    if not isinstance(fm, dict):
        raise RepoError("Invalid rules: frontmatter must be a mapping")
    scope = fm.get("scope", {})
    if not isinstance(scope, dict):
        raise RepoError("Invalid rules: frontmatter.scope must be a mapping")
    allowed = scope.get("allowed", ["cross", "os-specific"])
    if not isinstance(allowed, list) or not all(isinstance(x, str) for x in allowed):
        raise RepoError("Invalid rules: frontmatter.scope.allowed")
    values = [x.strip().lower() for x in allowed if x.strip()]
    if not values:
        raise RepoError("Invalid rules: frontmatter.scope.allowed must not be empty")
    return values


def _rules_created_os_values(rules: dict[str, Any]) -> list[str]:
    fm = rules.get("frontmatter", {})
    if not isinstance(fm, dict):
        raise RepoError("Invalid rules: frontmatter must be a mapping")
    created_os = fm.get("created_os", {})
    if not isinstance(created_os, dict):
        raise RepoError("Invalid rules: frontmatter.created_os must be a mapping")
    allowed = created_os.get("allowed", ["macos", "linux", "windows", "other"])
    if not isinstance(allowed, list) or not all(isinstance(x, str) for x in allowed):
        raise RepoError("Invalid rules: frontmatter.created_os.allowed")
    values = [x.strip().lower() for x in allowed if x.strip()]
    if not values:
        raise RepoError(
            "Invalid rules: frontmatter.created_os.allowed must not be empty"
        )
    return values


def _rules_list(rules: dict[str, Any], key: str) -> list[str]:
    v = rules.get(key, [])
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise RepoError(f"Invalid rules field: {key}")
    return list(v)


def _placement_dir(repo_root: Path, rules: dict[str, Any], kind: str, domain: str) -> Path:
    placement = rules.get("placement", {})
    if not isinstance(placement, dict):
        raise RepoError("Invalid rules: placement must be a mapping")

    inbox_dir = placement.get("inbox_dir", "inbox")
    patterns_dir = placement.get("patterns_dir", "patterns")
    domain_map = placement.get("domain_dir_map", {})
    if not isinstance(domain_map, dict):
        raise RepoError("Invalid rules: placement.domain_dir_map must be a mapping")

    if kind == "pattern":
        return repo_root / str(patterns_dir)

    if kind == "inbox" or domain == "cross":
        return repo_root / str(inbox_dir)

    domain_dir = domain_map.get(domain, domain)
    return repo_root / str(domain_dir)


def _default_slug(kind: str) -> str:
    # Slug is fixed and does not need to be human-semantic. Keep it stable.
    return kind


def _note_template(kind: str) -> str:
    # Templates are inserted on creation but not enforced by lint.
    templates: dict[str, str] = {
        "inbox": "",
        "note": "## 本文\n\n",
        "research": "## 背景\n\n## 調査メモ\n\n## 結論\n\n## 出典\n\n",
        "decision": "## 結論\n\n## 背景\n\n## 選択肢\n\n## 決め手\n\n## 影響\n\n",
        "troubleshoot": (
            "## 適用環境\n\n"
            "- 確認済み:\n"
            "- 未確認だが有効見込み:\n"
            "- 非対応/注意:\n\n"
            "## 症状\n\n## 環境\n\n## 原因\n\n## 対処\n\n## 再発防止\n\n"
        ),
        "howto": (
            "## 目的\n\n"
            "## 適用環境\n\n"
            "- 確認済み:\n"
            "- 未確認だが有効見込み:\n"
            "- 非対応/注意:\n\n"
            "## 手順\n\n## 検証\n\n## 注意点\n\n"
        ),
        "pattern": "## 概要\n\n## 使うとき\n\n## 例\n\n## 関連\n\n",
    }
    return templates.get(kind, "## 本文\n\n")


def _parse_iso_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _filename_matches_template(name: str, note_id: str, template: str) -> bool:
    pattern = re.escape(template)
    pattern = pattern.replace(re.escape("{id}"), re.escape(note_id))
    pattern = pattern.replace(
        re.escape("{slug}"),
        r"[a-z0-9]+(?:-[a-z0-9]+)*",
    )
    return re.fullmatch(pattern, name) is not None


def _normalize_os_name(value: str) -> str:
    raw = value.strip().lower()
    if raw in ("macos", "darwin", "mac"):
        return "macos"
    if raw in ("linux",):
        return "linux"
    if raw in ("windows", "win32", "win"):
        return "windows"
    return "other"


def _detect_created_os() -> str:
    env_value = os.environ.get("KB_CREATED_OS")
    if env_value and env_value.strip():
        return _normalize_os_name(env_value)
    return _normalize_os_name(platform.system())


def _detect_created_by() -> str:
    env_value = os.environ.get("KB_CREATED_BY")
    if env_value and env_value.strip():
        return env_value.strip()
    host_env = os.environ.get("HOSTNAME")
    if host_env and host_env.strip():
        return host_env.strip()
    host = platform.node().strip()
    if host:
        return host

    user = getuser().strip()
    return user or "unknown"


def _extract_related_ids(meta: dict[str, Any]) -> list[str]:
    raw = meta.get("related")
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for value in raw:
        if not isinstance(value, str):
            continue
        rid = value.strip().upper()
        if not is_ulid(rid):
            continue
        if rid in seen:
            continue
        seen.add(rid)
        out.append(rid)
    return out


def _note_link_label(meta: dict[str, Any], fallback: str) -> str:
    title = meta.get("title")
    if isinstance(title, str) and title.strip():
        text = title.strip()
    else:
        summary = meta.get("summary")
        if isinstance(summary, str) and summary.strip():
            text = summary.strip()
        else:
            text = fallback
    return " ".join(text.replace("|", " / ").split())


def _build_related_block(
    related_ids: list[str],
    note_index: dict[str, tuple[str, dict[str, Any]]],
) -> str | None:
    if not related_ids:
        return None
    lines = [AUTO_RELATED_START, "## 関連ノート"]
    for rid in related_ids:
        hit = note_index.get(rid)
        if hit is None:
            lines.append(f"- [missing] {rid}")
            continue
        stem, meta = hit
        label = _note_link_label(meta, stem)
        lines.append(f"- [[{stem}|{label}]]")
    lines.append(AUTO_RELATED_END)
    return "\n".join(lines)


def _replace_related_block(body: str, block: str | None) -> str:
    pattern = re.compile(
        rf"\n?{re.escape(AUTO_RELATED_START)}\n.*?\n{re.escape(AUTO_RELATED_END)}\n?",
        re.DOTALL,
    )
    cleaned = pattern.sub("\n", body).strip("\n")
    if block is None:
        return cleaned
    if cleaned:
        return f"{cleaned}\n\n{block}"
    return block


def _is_tracked(repo_root: Path, path: Path) -> bool:
    rel = os.fspath(path.relative_to(repo_root))
    try:
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", rel],
            cwd=repo_root,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _has_git_worktree(repo_root: Path) -> bool:
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=repo_root,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _require_git_worktree(repo_root: Path) -> None:
    if _has_git_worktree(repo_root):
        return
    raise click.ClickException(
        "git worktree is required for this command (git repository not available)."
    )


def _has_upstream(repo_root: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode != 0:
        return False
    upstream = result.stdout.strip()
    if not upstream or upstream in ("@{upstream}", "@{u}"):
        return False
    return True


def _git_pull_ff_only(repo_root: Path, *, allow_no_upstream: bool = False) -> None:
    if not _has_upstream(repo_root):
        if allow_no_upstream:
            click.echo(
                "No upstream is configured yet; skipping git pull --ff-only for initial bootstrap.",
                err=True,
            )
            return
        raise click.ClickException(
            "git upstream is not configured. Set upstream first, then retry."
        )

    try:
        subprocess.run(["git", "pull", "--ff-only"], cwd=repo_root, check=True)
    except subprocess.CalledProcessError as e:
        raise click.ClickException("git pull --ff-only failed") from e


def _git_commit_and_push(repo_root: Path, message: str) -> bool:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if not status.stdout.strip():
        return False

    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo_root, check=True)
    if _has_upstream(repo_root):
        subprocess.run(["git", "push"], cwd=repo_root, check=True)
    else:
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=repo_root, check=True)
    return True


def _move_path(repo_root: Path, src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    rel_src = os.fspath(src.relative_to(repo_root))
    rel_dst = os.fspath(dst.relative_to(repo_root))
    if not _is_tracked(repo_root, src):
        subprocess.run(["git", "add", rel_src], cwd=repo_root, check=True)
    subprocess.run(["git", "mv", rel_src, rel_dst], cwd=repo_root, check=True)


@click.group()
@click.pass_context
def main(ctx: click.Context) -> None:
    """kb repository helper CLI."""
    try:
        repo = open_repo()
    except RepoError as e:
        raise click.ClickException(str(e))
    ctx.obj = Ctx(repo=repo)


@main.command("new")
@click.option("--kind", type=str, default="note", show_default=True)
@click.option("--domain", type=str, default="cross", show_default=True)
@click.option("--title", type=str, default=None)
@click.option("--summary", type=str, required=True)
@click.option("--tag", "tags", type=str, multiple=True)
@click.option("--related", "related_ids", type=str, multiple=True)
@click.option("--slug", type=str, default=None)
@click.option("--scope", type=str, default=None)
@click.pass_obj
def cmd_new(
    ctx: Ctx,
    kind: str,
    domain: str,
    title: str | None,
    summary: str,
    tags: tuple[str, ...],
    related_ids: tuple[str, ...],
    slug: str | None,
    scope: str | None,
) -> None:
    rules = ctx.repo.rules
    repo_root = ctx.repo.root
    _require_git_worktree(repo_root)
    _git_pull_ff_only(repo_root, allow_no_upstream=True)

    kinds = set(_rules_list(rules, "kinds"))
    domains = set(_rules_list(rules, "domains"))
    scope_values = set(_rules_scope_values(rules))
    created_os_values = set(_rules_created_os_values(rules))

    if kind not in kinds:
        raise click.ClickException(f"Invalid kind: {kind} (allowed: {sorted(kinds)})")
    if domain not in domains:
        raise click.ClickException(
            f"Invalid domain: {domain} (allowed: {sorted(domains)})"
        )

    summary = (summary or "").strip()
    if not summary:
        raise click.ClickException("--summary must be non-empty")

    for rid in related_ids:
        if not is_ulid(rid):
            raise click.ClickException(f"Invalid related ULID: {rid}")

    normalized_scope = (scope or "").strip().lower() or "cross"
    if normalized_scope not in scope_values:
        raise click.ClickException(
            f"Invalid scope: {normalized_scope} (allowed: {sorted(scope_values)})"
        )

    created_by = _detect_created_by()
    created_os = _detect_created_os()
    if created_os not in created_os_values:
        raise click.ClickException(
            f"Invalid detected created_os: {created_os} "
            f"(allowed: {sorted(created_os_values)})"
        )

    note_id = new_ulid()
    ts = iso_jst_minute(now_jst())

    meta: dict[str, Any] = {
        "id": note_id,
        "kind": kind,
        "domain": domain,
        "scope": normalized_scope,
        "created_by": created_by,
        "created_os": created_os,
        "summary": summary,
        "created": ts,
        "updated": ts,
    }

    if title is not None and title.strip():
        meta["title"] = title.strip()

    if tags:
        meta["tags"] = [t.strip().lower() for t in tags if t.strip()]

    if related_ids:
        meta["related"] = [rid.upper() for rid in related_ids]

    out_dir = _placement_dir(repo_root, rules, kind, domain)
    out_dir.mkdir(parents=True, exist_ok=True)

    slug = (slug or _default_slug(kind)).strip()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise click.ClickException(
            f"Invalid slug: {slug} (expected lowercase kebab-case)"
        )

    filename = (rules.get("naming", {}) or {}).get("file_template", "{slug}--{id}.md")
    if not isinstance(filename, str):
        filename = "{slug}--{id}.md"
    out_path = out_dir / filename.format(id=note_id, slug=slug)

    body = _note_template(kind)
    text = dump_frontmatter(meta, body)
    out_path.write_text(text, encoding="utf-8")
    _git_commit_and_push(repo_root, f"ナレッジを追加: {note_id}")
    click.echo(os.fspath(out_path.relative_to(repo_root)))


@main.command("resolve")
@click.argument("note_id", type=str, required=True)
@click.pass_obj
def cmd_resolve(ctx: Ctx, note_id: str) -> None:
    note_id = note_id.strip().upper()
    if not is_ulid(note_id):
        raise click.ClickException(f"Invalid ULID: {note_id}")

    repo_root = ctx.repo.root
    note_dirs = _rules_list(ctx.repo.rules, "note_dirs")
    for p in iter_note_paths(repo_root, note_dirs):
        try:
            meta = read_doc(p).meta
        except FrontmatterError:
            continue
        if str(meta.get("id", "")).upper() == note_id:
            click.echo(os.fspath(p.relative_to(repo_root)))
            return

    raise click.ClickException(f"Note not found: {note_id}")


@main.command("search")
@click.argument("query", type=str, required=True)
@click.pass_obj
def cmd_search(ctx: Ctx, query: str) -> None:
    repo_root = ctx.repo.root
    _require_git_worktree(repo_root)
    _git_pull_ff_only(repo_root)

    note_dirs = _rules_list(ctx.repo.rules, "note_dirs")
    cmd = [
        "rg",
        "-n",
        "--hidden",
        "--glob",
        "!**/.git/**",
        query,
        *note_dirs,
    ]
    result = subprocess.run(cmd, cwd=repo_root, check=False)
    if result.returncode in (0, 1):
        if result.returncode == 1:
            click.echo("No matches")
        return
    raise click.ClickException(f"rg failed with exit code {result.returncode}")


@main.command("lint")
@click.pass_obj
def cmd_lint(ctx: Ctx) -> None:
    repo_root = ctx.repo.root
    rules = ctx.repo.rules

    note_dirs = _rules_list(rules, "note_dirs")
    required = (rules.get("frontmatter", {}) or {}).get("required", [])
    if not isinstance(required, list):
        raise click.ClickException("Invalid rules: frontmatter.required")
    required = [str(x) for x in required]

    allowed_kinds = set(_rules_list(rules, "kinds"))
    allowed_domains = set(_rules_list(rules, "domains"))
    allowed_scopes = set(_rules_scope_values(rules))
    allowed_created_os = set(_rules_created_os_values(rules))
    filename_template = (rules.get("naming", {}) or {}).get(
        "file_template", "{slug}--{id}.md"
    )
    if not isinstance(filename_template, str):
        filename_template = "{slug}--{id}.md"

    problems: list[str] = []

    for p in iter_note_paths(repo_root, note_dirs):
        rel = os.fspath(p.relative_to(repo_root))
        try:
            doc = read_doc(p)
        except FrontmatterError as e:
            problems.append(f"{rel}: {e}")
            continue
        meta = doc.meta

        for k in required:
            if k not in meta or meta[k] in (None, ""):
                problems.append(f"{rel}: missing required field: {k}")

        note_id = str(meta.get("id", "")).upper()
        if note_id and not is_ulid(note_id):
            problems.append(f"{rel}: invalid id (expected ULID): {meta.get('id')}")

        # Filename should match naming.file_template
        if note_id:
            if not _filename_matches_template(p.name, note_id, filename_template):
                problems.append(
                    f"{rel}: filename does not match template '{filename_template}' "
                    f"for id '{note_id}' (got: {p.name})"
                )

        kind = str(meta.get("kind", ""))
        if kind and kind not in allowed_kinds:
            problems.append(f"{rel}: invalid kind: {kind}")

        domain = str(meta.get("domain", ""))
        if domain and domain not in allowed_domains:
            problems.append(f"{rel}: invalid domain: {domain}")

        scope = meta.get("scope")
        if scope is not None:
            if not isinstance(scope, str) or not scope.strip():
                problems.append(f"{rel}: scope must be a non-empty string")
            else:
                normalized_scope = scope.strip().lower()
                if normalized_scope not in allowed_scopes:
                    problems.append(
                        f"{rel}: invalid scope: {scope} (allowed: {sorted(allowed_scopes)})"
                    )

        created_by = meta.get("created_by")
        if created_by is not None:
            if not isinstance(created_by, str) or not created_by.strip():
                problems.append(f"{rel}: created_by must be a non-empty string")

        created_os = meta.get("created_os")
        if created_os is not None:
            if not isinstance(created_os, str) or not created_os.strip():
                problems.append(f"{rel}: created_os must be a non-empty string")
            else:
                normalized_created_os = _normalize_os_name(created_os)
                if normalized_created_os not in allowed_created_os:
                    problems.append(
                        f"{rel}: invalid created_os: {created_os} "
                        f"(allowed: {sorted(allowed_created_os)})"
                    )

        for ts_field in ("created", "updated"):
            v = meta.get(ts_field)
            if isinstance(v, str) and v.strip():
                if _parse_iso_dt(v.strip()) is None:
                    problems.append(f"{rel}: invalid {ts_field}: {v}")

        created = meta.get("created")
        updated = meta.get("updated")
        if isinstance(created, str) and isinstance(updated, str):
            cdt = _parse_iso_dt(created.strip())
            udt = _parse_iso_dt(updated.strip())
            if cdt and udt and udt < cdt:
                problems.append(f"{rel}: updated is before created")

        tags = meta.get("tags")
        if tags is not None:
            if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
                problems.append(f"{rel}: tags must be a string list")
            else:
                tag_re = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
                for t in tags:
                    if not tag_re.fullmatch(t):
                        problems.append(f"{rel}: invalid tag: {t}")

        related = meta.get("related")
        if related is not None:
            if not isinstance(related, list) or not all(
                isinstance(x, str) for x in related
            ):
                problems.append(f"{rel}: related must be a string list")
            else:
                for rid in related:
                    if not is_ulid(rid):
                        problems.append(f"{rel}: invalid related ULID: {rid}")

    if problems:
        for p in problems:
            click.echo(p, err=True)
        raise click.ClickException(f"lint failed: {len(problems)} problem(s)")

    click.echo("OK")


@main.command("organize")
@click.pass_obj
def cmd_organize(ctx: Ctx) -> None:
    repo_root = ctx.repo.root
    rules = ctx.repo.rules
    _require_git_worktree(repo_root)
    _git_pull_ff_only(repo_root)
    note_dirs = _rules_list(rules, "note_dirs")
    allowed_scopes = set(_rules_scope_values(rules))
    allowed_created_os = set(_rules_created_os_values(rules))
    default_created_by = _detect_created_by()
    default_created_os = _detect_created_os()
    if default_created_os not in allowed_created_os:
        default_created_os = "other"
    ts = iso_jst_minute(now_jst())

    notes = [read_note(p) for p in iter_note_paths(repo_root, note_dirs)]
    note_index: dict[str, tuple[str, dict[str, Any]]] = {}
    for note in notes:
        note_id = str(note.meta.get("id", "")).upper()
        if not note_id or not is_ulid(note_id):
            continue
        note_index[note_id] = (note.path.stem, note.meta)

    moved: list[tuple[Path, Path]] = []
    metadata_updated: list[Path] = []

    for note in notes:
        p = note.path
        meta = dict(note.meta)
        changed = False

        kind = str(meta.get("kind", ""))
        domain = str(meta.get("domain", ""))
        note_id = str(meta.get("id", "")).upper()
        if not note_id or not is_ulid(note_id):
            continue
        if not kind or not domain:
            continue

        scope = meta.get("scope")
        if scope is None or (isinstance(scope, str) and not scope.strip()):
            meta["scope"] = "cross"
            changed = True
        elif isinstance(scope, str):
            normalized_scope = scope.strip().lower()
            if normalized_scope in allowed_scopes and normalized_scope != scope:
                meta["scope"] = normalized_scope
                changed = True

        created_by = meta.get("created_by")
        if created_by is None or (isinstance(created_by, str) and not created_by.strip()):
            meta["created_by"] = default_created_by
            changed = True

        created_os = meta.get("created_os")
        if created_os is None or (isinstance(created_os, str) and not created_os.strip()):
            meta["created_os"] = default_created_os
            changed = True
        elif isinstance(created_os, str):
            normalized_created_os = _normalize_os_name(created_os)
            if (
                normalized_created_os in allowed_created_os
                and normalized_created_os != created_os
            ):
                meta["created_os"] = normalized_created_os
                changed = True

        related_block = _build_related_block(_extract_related_ids(meta), note_index)
        next_body = _replace_related_block(note.body, related_block)
        if next_body != note.body:
            changed = True

        if changed:
            meta["updated"] = ts
            write_doc(p, Doc(meta=meta, body=next_body))
            metadata_updated.append(p)

        desired_dir = _placement_dir(repo_root, rules, kind, domain)
        if desired_dir.resolve() == p.parent.resolve():
            continue

        dst = desired_dir / p.name
        _move_path(repo_root, p, dst)
        moved.append((p, dst))

    if not moved and not metadata_updated:
        click.echo("No changes")
        return

    for src, dst in moved:
        click.echo(
            f"{os.fspath(src.relative_to(repo_root))} -> {os.fspath(dst.relative_to(repo_root))}"
        )

    for path in metadata_updated:
        click.echo(f"metadata updated: {os.fspath(path.relative_to(repo_root))}")

    _git_commit_and_push(repo_root, "ナレッジ配置とメタデータを整理")
