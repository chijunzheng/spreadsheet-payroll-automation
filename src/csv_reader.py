from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path
from typing import Dict, Tuple

from .models import DailyPunches, PunchSegment
from .utils import normalize_name, parse_csv_date, parse_csv_time


DATE_RANGE_SLASH_RE = re.compile(
    r"(\d{1,2}/\d{1,2}/\d{4})\s*[-_]\s*(\d{1,2}/\d{1,2}/\d{4})"
)
DATE_RANGE_DASH_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2})\s*[-_]\s*(\d{4}-\d{2}-\d{2})"
)


def read_report_range(csv_path: str | Path) -> Tuple[date, date] | None:
    path = Path(csv_path)
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        for _ in range(5):
            try:
                row = next(reader)
            except StopIteration:
                break
            joined = " ".join(row)
            parsed = _parse_date_range(joined)
            if parsed:
                return parsed

    parsed = _parse_date_range(path.name)
    return parsed


def read_punches(csv_path: str | Path) -> Dict[Tuple[str, date], DailyPunches]:
    path = Path(csv_path)
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = None
        for row in reader:
            if not row:
                continue
            if "EMP L NAME" in row:
                header = row
                break
        if header is None:
            raise ValueError("CSV header row not found.")

        def idx(name: str) -> int:
            try:
                return header.index(name)
            except ValueError as exc:
                raise ValueError(f"CSV missing column: {name}") from exc

        idx_last = idx("EMP L NAME")
        idx_first = idx("EMP F NAME")
        idx_date = idx("DATE")
        idx_in = idx("IN")
        idx_out = idx("OUT")

        grouped: Dict[Tuple[str, date], DailyPunches] = {}
        for row in reader:
            if not row or len(row) <= idx_out:
                continue
            date_raw = row[idx_date].strip()
            time_in_raw = row[idx_in].strip()
            time_out_raw = row[idx_out].strip()
            if not date_raw or not time_in_raw or not time_out_raw:
                continue

            first = row[idx_first].strip()
            last = row[idx_last].strip()
            if first and last:
                name = f"{first} {last}"
            else:
                name = first or last
            if not name:
                continue

            punch_date = parse_csv_date(date_raw)
            in_minutes = parse_csv_time(time_in_raw)
            out_minutes = parse_csv_time(time_out_raw)
            if in_minutes is None or out_minutes is None:
                continue

            key = normalize_name(name)
            bucket_key = (key, punch_date)
            if bucket_key not in grouped:
                grouped[bucket_key] = DailyPunches(
                    employee_name=name.strip(),
                    employee_key=key,
                    date=punch_date,
                    segments=[],
                )
            grouped[bucket_key].segments.append(
                PunchSegment(in_minutes=in_minutes, out_minutes=out_minutes)
            )

        for daily in grouped.values():
            daily.segments.sort(key=lambda seg: seg.in_minutes)

        return grouped


def _parse_date_range(text: str) -> Tuple[date, date] | None:
    match = DATE_RANGE_SLASH_RE.search(text)
    if match:
        return (parse_csv_date(match.group(1)), parse_csv_date(match.group(2)))
    match = DATE_RANGE_DASH_RE.search(text)
    if match:
        start = date.fromisoformat(match.group(1))
        end = date.fromisoformat(match.group(2))
        return (start, end)
    return None
