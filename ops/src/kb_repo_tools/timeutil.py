from __future__ import annotations

from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))


def now_jst() -> datetime:
    return datetime.now(tz=JST)


def iso_jst_minute(dt: datetime) -> str:
    dt = dt.astimezone(JST).replace(second=0, microsecond=0)
    return dt.isoformat(timespec="minutes")

