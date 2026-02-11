from __future__ import annotations

import re
from typing import Final

import ulid

_ULID_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def new_ulid() -> str:
    # ulid.new() returns an object that stringifies to a canonical ULID.
    return str(ulid.new()).upper()


def is_ulid(value: str) -> bool:
    if not isinstance(value, str):
        return False
    return bool(_ULID_RE.match(value.upper()))

