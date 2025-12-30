from __future__ import annotations

import argparse
from pathlib import Path

from datetime import timedelta

from src.csv_reader import read_punches, read_report_range
from src.report import write_report
from src.validator import validate
from src.xlsx_reader import read_timesheet
from src.xlsx_writer import write_statuses


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate payroll timesheet against punch data.")
    parser.add_argument("--csv", required=True, help="Path to the punch report CSV.")
    parser.add_argument("--xlsx", required=True, help="Path to the filled payroll XLSX.")
    parser.add_argument(
        "--out-dir",
        default="outputs",
        help="Directory for the validation report and validated XLSX.",
    )
    args = parser.parse_args()

    punches = read_punches(args.csv)
    target_dates = {daily.date for daily in punches.values()}
    report_range = read_report_range(args.csv)
    sheet_hint = None
    if report_range:
        start_date, end_date = report_range
        delta = (7 - start_date.weekday()) % 7
        monday = start_date + timedelta(days=delta)
        if monday > end_date:
            monday = start_date
        sheet_hint = f"{monday.month:02d}{monday.day:02d}"

    blocks = read_timesheet(
        args.xlsx, target_dates=target_dates, sheet_hint=sheet_hint
    )
    discrepancies, status_by_row = validate(blocks, punches)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "validation_report.csv"
    write_report(report_path, discrepancies)

    xlsx_path = Path(args.xlsx)
    validated_name = f"{xlsx_path.stem}-validated.xlsx"
    validated_path = out_dir / validated_name
    write_statuses(xlsx_path, validated_path, status_by_row)

    ok_count = sum(1 for status in status_by_row.values() if status == "ok")
    needs_attention = sum(1 for status in status_by_row.values() if status != "ok")
    print(f"Discrepancies: {len(discrepancies)}")
    print(f"Employees OK: {ok_count}")
    print(f"Employees Needs Attention: {needs_attention}")
    print(f"Report: {report_path}")
    print(f"Validated XLSX: {validated_path}")


if __name__ == "__main__":
    main()
