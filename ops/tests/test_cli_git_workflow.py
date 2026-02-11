from __future__ import annotations

import subprocess
from pathlib import Path

import click
import pytest

from kb_repo_tools import cli


class _RunResult:
    def __init__(self, stdout: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.returncode = returncode


def test_git_pull_ff_only_runs_git_pull(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], cwd: Path, check: bool, **kwargs) -> _RunResult:
        calls.append(cmd)
        assert check is True
        return _RunResult()

    monkeypatch.setattr(cli, "_has_upstream", lambda _root: True)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    cli._git_pull_ff_only(Path("/tmp/repo"))
    assert calls == [["git", "pull", "--ff-only"]]


def test_git_pull_ff_only_raises_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd: list[str], cwd: Path, check: bool, **kwargs) -> _RunResult:
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd)

    monkeypatch.setattr(cli, "_has_upstream", lambda _root: True)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    with pytest.raises(click.ClickException):
        cli._git_pull_ff_only(Path("/tmp/repo"))


def test_git_pull_ff_only_raises_without_upstream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "_has_upstream", lambda _root: False)
    with pytest.raises(click.ClickException):
        cli._git_pull_ff_only(Path("/tmp/repo"))


def test_git_pull_ff_only_allows_missing_upstream_on_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "_has_upstream", lambda _root: False)
    cli._git_pull_ff_only(Path("/tmp/repo"), allow_no_upstream=True)


def test_git_commit_and_push_skips_without_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], cwd: Path, check: bool, **kwargs) -> _RunResult:
        calls.append(cmd)
        if cmd == ["git", "status", "--porcelain"]:
            return _RunResult(stdout="")
        return _RunResult()

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    changed = cli._git_commit_and_push(Path("/tmp/repo"), "msg")
    assert changed is False
    assert calls == [["git", "status", "--porcelain"]]


def test_git_commit_and_push_commits_and_pushes(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], cwd: Path, check: bool, **kwargs) -> _RunResult:
        calls.append(cmd)
        if cmd == ["git", "status", "--porcelain"]:
            return _RunResult(stdout=" M tools/note.md\n")
        return _RunResult()

    monkeypatch.setattr(cli, "_has_upstream", lambda _root: True)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    changed = cli._git_commit_and_push(Path("/tmp/repo"), "ナレッジ更新")
    assert changed is True
    assert calls == [
        ["git", "status", "--porcelain"],
        ["git", "add", "-A"],
        ["git", "commit", "-m", "ナレッジ更新"],
        ["git", "push"],
    ]


def test_git_commit_and_push_sets_upstream_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], cwd: Path, check: bool, **kwargs) -> _RunResult:
        calls.append(cmd)
        if cmd == ["git", "status", "--porcelain"]:
            return _RunResult(stdout=" M notes/tools/note.md\n")
        return _RunResult()

    monkeypatch.setattr(cli, "_has_upstream", lambda _root: False)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    changed = cli._git_commit_and_push(Path("/tmp/repo"), "初回コミット")
    assert changed is True
    assert calls == [
        ["git", "status", "--porcelain"],
        ["git", "add", "-A"],
        ["git", "commit", "-m", "初回コミット"],
        ["git", "push", "-u", "origin", "HEAD"],
    ]
