from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


class FrontmatterError(ValueError):
    pass


_yaml = YAML(typ="safe")
_yaml.default_flow_style = False
_yaml.allow_unicode = True


PREFERRED_KEY_ORDER = [
    "id",
    "kind",
    "domain",
    "scope",
    "created_by",
    "created_os",
    "title",
    "summary",
    "tags",
    "related",
    "created",
    "updated",
]


@dataclass(frozen=True)
class Doc:
    meta: dict[str, Any]
    body: str


def split_frontmatter(text: str) -> Doc:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("Missing YAML frontmatter (expected starting ---)")

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        raise FrontmatterError("Frontmatter not closed (missing terminating ---)")

    fm_text = "\n".join(lines[1:end_idx]).strip() + "\n"
    body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")

    meta = _yaml.load(fm_text) or {}
    if not isinstance(meta, dict):
        raise FrontmatterError("Frontmatter must be a YAML mapping")

    # ruamel.yaml returns CommentedMap sometimes; normalize to plain dict
    meta = dict(meta)
    return Doc(meta=meta, body=body)


def dump_frontmatter(meta: dict[str, Any], body: str) -> str:
    ordered: dict[str, Any] = {}
    for k in PREFERRED_KEY_ORDER:
        if k in meta and meta[k] is not None:
            ordered[k] = meta[k]

    for k in sorted(meta.keys()):
        if k in ordered:
            continue
        if meta[k] is None:
            continue
        ordered[k] = meta[k]

    from io import StringIO

    buf = StringIO()
    _yaml.dump(ordered, buf)
    fm_text = buf.getvalue().rstrip() + "\n"

    body = body.rstrip() + "\n"
    return f"---\n{fm_text}---\n\n{body}"


def read_doc(path: Path) -> Doc:
    return split_frontmatter(path.read_text(encoding="utf-8"))


def write_doc(path: Path, doc: Doc) -> None:
    text = dump_frontmatter(doc.meta, doc.body)
    path.write_text(text, encoding="utf-8")
