from __future__ import annotations

import argparse
from pathlib import Path

from src.runner import run_validation


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

    report_path, validated_path, count, ok_count, needs_attention = run_validation(
        args.csv, args.xlsx, args.out_dir
    )

    print(f"Discrepancies: {count}")
    print(f"Employees OK: {ok_count}")
    print(f"Employees Needs Attention: {needs_attention}")
    print(f"Report: {report_path}")
    print(f"Validated XLSX: {validated_path}")


if __name__ == "__main__":
    main()
