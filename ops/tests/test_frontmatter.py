from __future__ import annotations

from kb_repo_tools.frontmatter import dump_frontmatter, split_frontmatter


def test_split_and_dump_roundtrip_minimal():
    text = """---
id: 01J0Z3N3Y7F4K2M9Q3T5A6B7C8
kind: note
domain: dev
summary: test
created: 2026-02-10T23:15+09:00
updated: 2026-02-10T23:15+09:00
---

hello
"""
    doc = split_frontmatter(text)
    assert doc.meta["id"] == "01J0Z3N3Y7F4K2M9Q3T5A6B7C8"
    assert "hello" in doc.body

    out = dump_frontmatter(doc.meta, doc.body)
    doc2 = split_frontmatter(out)
    assert doc2.meta["id"] == doc.meta["id"]
    assert "hello" in doc2.body

