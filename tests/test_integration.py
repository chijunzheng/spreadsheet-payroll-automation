import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from src.csv_reader import read_punches, read_report_range
from src.report import write_report
from src.validator import validate
from src.xlsx_reader import read_timesheet
from src.xlsx_writer import write_statuses


class IntegrationTests(unittest.TestCase):
    def test_end_to_end_outputs(self) -> None:
        matches = sorted(Path("data").glob("Punch_Report_*.csv"))
        if not matches:
            raise FileNotFoundError("No Punch_Report CSV found in data/")
        csv_path = str(matches[0])
        punches = read_punches(csv_path)
        target_dates = {daily.date for daily in punches.values()}
        report_range = read_report_range(csv_path)
        sheet_hint = None
        if report_range:
            start_date, end_date = report_range
            delta = (7 - start_date.weekday()) % 7
            monday = start_date + timedelta(days=delta)
            if monday > end_date:
                monday = start_date
            sheet_hint = f"{monday.month:02d}{monday.day:02d}"
        blocks = read_timesheet(
            "data/Chef & Amazing time sheet - checking purposes.xlsx",
            target_dates=target_dates,
            sheet_hint=sheet_hint,
        )
        discrepancies, statuses = validate(blocks, punches)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            report_path = tmpdir / "report.csv"
            write_report(report_path, discrepancies)
            self.assertTrue(report_path.exists())

            output_xlsx = tmpdir / "validated.xlsx"
            write_statuses(
                "data/Chef & Amazing time sheet - checking purposes.xlsx",
                output_xlsx,
                statuses,
            )
            self.assertTrue(output_xlsx.exists())


if __name__ == "__main__":
    unittest.main()
