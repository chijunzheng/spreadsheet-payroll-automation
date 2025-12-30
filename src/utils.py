from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

EXCEL_EPOCH = datetime(1899, 12, 30)
MINUTES_PER_DAY = 24 * 60


def normalize_name(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", name.lower())
    return " ".join(cleaned.strip().split())


def parse_csv_date(value: str) -> date:
    return datetime.strptime(value.strip(), "%m/%d/%Y").date()


def parse_csv_time(value: str) -> Optional[int]:
    text = value.strip()
    if not text:
        return None
    if set(text) == {"-"}:
        return None
    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.hour * 60 + dt.minute
        except ValueError:
            continue
    raise ValueError(f"Unrecognized time format: {value}")


def excel_serial_to_date(serial: float) -> date:
    days = int(round(serial))
    return (EXCEL_EPOCH + timedelta(days=days)).date()


def excel_fraction_to_minutes(value: float) -> int:
    minutes = int(round(value * MINUTES_PER_DAY))
    return minutes % MINUTES_PER_DAY


def format_minutes(value: Optional[int]) -> Optional[str]:
    if value is None:
        return None
    hours, minutes = divmod(value, 60)
    return f"{hours:02d}:{minutes:02d}"
