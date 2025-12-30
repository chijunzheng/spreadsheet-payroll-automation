import csv
import unittest
from datetime import date
from pathlib import Path

from src.csv_reader import read_punches, read_report_range
from src.utils import normalize_name, parse_csv_date


def _csv_path() -> str:
    matches = sorted(Path("data").glob("Punch_Report_*.csv"))
    if not matches:
        raise FileNotFoundError("No Punch_Report CSV found in data/")
    return str(matches[0])


class CsvReaderTests(unittest.TestCase):
    def test_reads_punches(self) -> None:
        path = _csv_path()
        punches = read_punches(path)

        with open(path, newline="") as handle:
            reader = csv.reader(handle)
            header = None
            for row in reader:
                if "EMP L NAME" in row:
                    header = row
                    break
            self.assertIsNotNone(header)
            idx_last = header.index("EMP L NAME")
            idx_first = header.index("EMP F NAME")
            idx_date = header.index("DATE")
            idx_in = header.index("IN")
            idx_out = header.index("OUT")
            for row in reader:
                if not row or len(row) <= idx_out:
                    continue
                if not row[idx_date].strip() or not row[idx_in].strip():
                    continue
                first = row[idx_first].strip()
                last = row[idx_last].strip()
                if not first and not last:
                    continue
                name = normalize_name(f"{first} {last}")
                punch_date = parse_csv_date(row[idx_date])
                key = (name, punch_date)
                self.assertIn(key, punches)
                break

    def test_reads_report_range(self) -> None:
        report_range = read_report_range(_csv_path())
        self.assertIsNotNone(report_range)
        start, end = report_range
        self.assertLessEqual(start, end)
        self.assertLessEqual((end - start).days, 7)


if __name__ == "__main__":
    unittest.main()
