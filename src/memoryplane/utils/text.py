from __future__ import annotations

import re
from datetime import UTC, datetime
from datetime import timedelta


# Match ASCII words and individual CJK ideographs so Chinese content remains searchable
# without introducing an external tokenizer dependency in the MVP.
TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u3400-\u4DBF\u4E00-\u9FFF]")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def utc_now_datetime() -> datetime:
    return datetime.now(UTC)


def utc_now() -> str:
    return utc_now_datetime().isoformat().replace("+00:00", "Z")


def parse_source(value: str) -> tuple[str, str]:
    if ":" not in value:
        return value, ""
    kind, session_id = value.split(":", 1)
    return kind, session_id


def parse_window_to_days(value: str) -> int:
    if value.endswith("d"):
        return int(value[:-1])
    raise ValueError("Unsupported window format")


def truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 3, 0)].rstrip()}..."


def parse_recent_to_after(value: str, *, now: datetime | None = None) -> str:
    current = now or utc_now_datetime()
    match = re.fullmatch(r"(\d+)([hdw])", value.strip().lower())
    if not match:
        raise ValueError("Unsupported recent format")
    amount = int(match.group(1))
    unit = match.group(2)
    delta = {"h": timedelta(hours=amount), "d": timedelta(days=amount), "w": timedelta(weeks=amount)}[unit]
    return (current - delta).isoformat().replace("+00:00", "Z")
