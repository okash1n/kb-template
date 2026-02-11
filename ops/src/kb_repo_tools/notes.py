from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .frontmatter import Doc, FrontmatterError, read_doc


@dataclass(frozen=True)
class Note:
    path: Path
    meta: dict[str, Any]
    body: str


def iter_note_paths(repo_root: Path, note_dirs: Iterable[str]) -> Iterable[Path]:
    for d in note_dirs:
        base = (repo_root / d).resolve()
        if not base.exists():
            continue
        for p in base.rglob("*.md"):
            if p.is_file():
                yield p


def read_note(path: Path) -> Note:
    doc: Doc = read_doc(path)
    return Note(path=path, meta=doc.meta, body=doc.body)


def try_read_note(path: Path) -> Note | None:
    try:
        return read_note(path)
    except (OSError, FrontmatterError):
        return None

