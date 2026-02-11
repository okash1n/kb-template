from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


class RepoError(RuntimeError):
    pass


_yaml = YAML(typ="safe")
_yaml.default_flow_style = False
_yaml.allow_unicode = True


@dataclass(frozen=True)
class Repo:
    root: Path
    rules: dict[str, Any]


def find_repo_root(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for parent in [cur, *cur.parents]:
        if (parent / "ops" / "rules" / "kb.rules.yml").exists():
            return parent
    raise RepoError("Could not find repo root (missing ops/rules/kb.rules.yml)")


def load_rules(root: Path) -> dict[str, Any]:
    rules_path = root / "ops" / "rules" / "kb.rules.yml"
    if not rules_path.exists():
        raise RepoError(f"Missing rules file: {rules_path}")
    data = _yaml.load(rules_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise RepoError("ops/rules/kb.rules.yml must be a YAML mapping")
    return dict(data)


def open_repo(start: Path | None = None) -> Repo:
    root = find_repo_root(start)
    rules = load_rules(root)
    return Repo(root=root, rules=rules)
