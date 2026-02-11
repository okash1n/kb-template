from __future__ import annotations

from pathlib import Path

import click
import pytest

from kb_repo_tools import cli


def test_require_git_worktree_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_has_git_worktree", lambda _root: True)
    cli._require_git_worktree(Path("/tmp/repo"))


def test_require_git_worktree_raises_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "_has_git_worktree", lambda _root: False)
    with pytest.raises(click.ClickException):
        cli._require_git_worktree(Path("/tmp/repo"))


def test_move_path_uses_git_mv_for_tracked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path
    src = repo_root / "inbox" / "note.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("x", encoding="utf-8")
    dst = repo_root / "tools" / "note.md"

    calls: list[list[str]] = []

    def fake_run(
        cmd: list[str], cwd: Path, check: bool, stdout=None, stderr=None
    ) -> None:
        assert cwd == repo_root
        assert check is True
        calls.append(cmd)

    monkeypatch.setattr(cli, "_is_tracked", lambda _root, _path: True)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    cli._move_path(repo_root, src, dst)

    assert calls == [["git", "mv", "inbox/note.md", "tools/note.md"]]


def test_move_path_stages_untracked_then_git_mv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path
    src = repo_root / "inbox" / "note.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("x", encoding="utf-8")
    dst = repo_root / "tools" / "note.md"

    calls: list[list[str]] = []

    def fake_run(
        cmd: list[str], cwd: Path, check: bool, stdout=None, stderr=None
    ) -> None:
        assert cwd == repo_root
        assert check is True
        calls.append(cmd)

    monkeypatch.setattr(cli, "_is_tracked", lambda _root, _path: False)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    cli._move_path(repo_root, src, dst)

    assert calls == [
        ["git", "add", "inbox/note.md"],
        ["git", "mv", "inbox/note.md", "tools/note.md"],
    ]


def test_filename_matches_template_slug_id() -> None:
    note_id = "01KH5AP6B38MDFJESSS7EW3WHA"
    assert (
        cli._filename_matches_template(
            f"skills-authoring-playbook--{note_id}.md",
            note_id,
            "{slug}--{id}.md",
        )
        is True
    )


def test_filename_matches_template_id_slug() -> None:
    note_id = "01KH5AP6B38MDFJESSS7EW3WHA"
    assert (
        cli._filename_matches_template(
            f"{note_id}--skills-authoring-playbook.md",
            note_id,
            "{id}--{slug}.md",
        )
        is True
    )


def test_rules_scope_values_default() -> None:
    assert cli._rules_scope_values({}) == ["cross", "os-specific"]


def test_note_template_has_environment_section_for_troubleshoot_and_howto() -> None:
    troubleshoot = cli._note_template("troubleshoot")
    howto = cli._note_template("howto")
    assert "## 適用環境" in troubleshoot
    assert "## 適用環境" in howto


def test_rules_created_os_values_default() -> None:
    assert cli._rules_created_os_values({}) == ["macos", "linux", "windows", "other"]


def test_normalize_os_name_aliases() -> None:
    assert cli._normalize_os_name("Darwin") == "macos"
    assert cli._normalize_os_name("mac") == "macos"
    assert cli._normalize_os_name("Linux") == "linux"
    assert cli._normalize_os_name("WIN32") == "windows"
    assert cli._normalize_os_name("Solaris") == "other"


def test_detect_created_os_prefers_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KB_CREATED_OS", "Darwin")
    assert cli._detect_created_os() == "macos"


def test_detect_created_by_prefers_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KB_CREATED_BY", "manual-creator")
    monkeypatch.setattr(cli.platform, "node", lambda: "host-from-node")
    assert cli._detect_created_by() == "manual-creator"


def test_detect_created_by_uses_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KB_CREATED_BY", raising=False)
    monkeypatch.setattr(cli.platform, "node", lambda: "kb-host-01")
    monkeypatch.setattr(cli, "getuser", lambda: "fallback-user")
    assert cli._detect_created_by() == "kb-host-01"


def test_extract_related_ids_dedup_and_validate() -> None:
    valid = "01KH5AP6B38MDFJESSS7EW3WHA"
    invalid = "not-ulid"
    meta = {"related": [valid.lower(), valid, invalid, 123]}
    assert cli._extract_related_ids(meta) == [valid]


def test_build_and_replace_related_block() -> None:
    rid = "01KH5AP6B38MDFJESSS7EW3WHA"
    note_index = {
        rid: (
            "skills-authoring-playbook--01KH5AP6B38MDFJESSS7EW3WHA",
            {"title": "スキル作成手順"},
        )
    }
    block = cli._build_related_block([rid], note_index)
    assert block is not None
    body = "## 本文\n\n内容\n"
    merged = cli._replace_related_block(body, block)
    assert cli.AUTO_RELATED_START in merged
    assert "[[skills-authoring-playbook--01KH5AP6B38MDFJESSS7EW3WHA|スキル作成手順]]" in merged
    assert merged == cli._replace_related_block(merged, block)
    removed = cli._replace_related_block(merged, None)
    assert cli.AUTO_RELATED_START not in removed
