from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Optional, Tuple

from .csv_reader import read_punches, read_report_range
from .report import write_report
from .validator import validate
from .xlsx_reader import read_timesheet
from .xlsx_writer import write_statuses


def run_validation(
    csv_path: str | Path,
    xlsx_path: str | Path,
    out_dir: str | Path,
) -> Tuple[Path, Path, int, int, int]:
    punches = read_punches(csv_path)
    target_dates = {daily.date for daily in punches.values()}
    report_range = read_report_range(csv_path)
    sheet_hint = _sheet_hint_from_range(report_range)

    blocks = read_timesheet(
        xlsx_path, target_dates=target_dates, sheet_hint=sheet_hint
    )
    discrepancies, status_by_row = validate(blocks, punches)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "validation_report.csv"
    write_report(report_path, discrepancies)

    xlsx_path = Path(xlsx_path)
    validated_name = f"{xlsx_path.stem}-validated.xlsx"
    validated_path = out_dir / validated_name
    write_statuses(xlsx_path, validated_path, status_by_row)

    ok_count = sum(1 for status in status_by_row.values() if status == "ok")
    needs_attention = sum(1 for status in status_by_row.values() if status != "ok")
    return report_path, validated_path, len(discrepancies), ok_count, needs_attention


def _sheet_hint_from_range(
    report_range: Optional[Tuple[date, date]]
) -> Optional[str]:
    if report_range is None:
        return None
    start_date, end_date = report_range
    delta = (7 - start_date.weekday()) % 7
    monday = start_date + timedelta(days=delta)
    if monday > end_date:
        monday = start_date
    return f"{monday.month:02d}{monday.day:02d}"
