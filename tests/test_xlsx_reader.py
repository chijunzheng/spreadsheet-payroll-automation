import unittest
from datetime import date

from src.xlsx_reader import _parse_start_hint, read_timesheet


class XlsxReaderTests(unittest.TestCase):
    def test_reads_timesheet(self) -> None:
        blocks = read_timesheet("data/Chef & Amazing time sheet - checking purposes.xlsx")
        block = next(b for b in blocks if b.key == "eden zuniga")
        monday = date(2024, 12, 9)
        self.assertIn(monday, block.times_by_date)
        recorded = block.times_by_date[monday]
        self.assertEqual(recorded.clock_in, 7 * 60)
        self.assertEqual(block.status_row, 15)

    def test_parse_start_hint_addj(self) -> None:
        parsed = _parse_start_hint("Addj- 7:00am", {})
        self.assertIsNotNone(parsed)
        hint_date, minutes = parsed
        self.assertIsNone(hint_date)
        self.assertEqual(minutes, 7 * 60)


if __name__ == "__main__":
    unittest.main()
