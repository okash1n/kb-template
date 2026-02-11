from __future__ import annotations

from datetime import datetime, timedelta, timezone

from kb_repo_tools.timeutil import iso_jst_minute


def test_iso_jst_minute_has_offset_and_minute_precision():
    dt = datetime(2026, 2, 10, 23, 15, 59, 123456, tzinfo=timezone.utc)
    s = iso_jst_minute(dt)
    assert s.endswith("+09:00")
    assert s.startswith("2026-02-11T08:15")

