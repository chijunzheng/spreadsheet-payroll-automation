import unittest
from datetime import date

from src.models import DailyPunches, EmployeeBlock, PunchSegment, RecordedTimes
from src.validator import validate


class ValidatorTests(unittest.TestCase):
    def test_rounding_and_lunch_rules(self) -> None:
        day = date(2025, 1, 6)
        punches = {
            ("alex worker", day): DailyPunches(
                employee_name="Alex Worker",
                employee_key="alex worker",
                date=day,
                segments=[
                    PunchSegment(in_minutes=7 * 60 + 15, out_minutes=11 * 60 + 5),
                    PunchSegment(in_minutes=11 * 60 + 20, out_minutes=16 * 60 + 44),
                ],
            )
        }
        recorded = RecordedTimes(
            clock_in=7 * 60 + 30,
            lunch_out=11 * 60 + 5,
            lunch_in=11 * 60 + 35,
            clock_out=16 * 60 + 44,
        )
        block = EmployeeBlock(
            name="Alex Worker",
            key="alex worker",
            dates_by_col={},
            times_by_date={day: recorded},
            status_row=10,
        )

        discrepancies, status_by_row = validate([block], punches)
        self.assertEqual(len(discrepancies), 0)
        self.assertEqual(status_by_row.get(10), "ok")

    def test_raw_time_match_is_valid(self) -> None:
        day = date(2025, 12, 16)
        punches = {
            ("javier lopez", day): DailyPunches(
                employee_name="Javier Lopez",
                employee_key="javier lopez",
                date=day,
                segments=[PunchSegment(in_minutes=8 * 60 + 24, out_minutes=13 * 60)],
            )
        }
        recorded = RecordedTimes(
            clock_in=8 * 60 + 24,
            lunch_out=None,
            lunch_in=None,
            clock_out=13 * 60,
        )
        block = EmployeeBlock(
            name="Javier Lopez",
            key="javier lopez",
            dates_by_col={},
            times_by_date={day: recorded},
            status_row=12,
        )

        discrepancies, status_by_row = validate([block], punches)
        self.assertEqual(len(discrepancies), 0)
        self.assertEqual(status_by_row.get(12), "ok")

    def test_enforces_lunch_break_from_raw_out(self) -> None:
        day = date(2025, 12, 18)
        punches = {
            ("francisco quiroga reyes", day): DailyPunches(
                employee_name="Francisco Quiroga Reyes",
                employee_key="francisco quiroga reyes",
                date=day,
                segments=[
                    PunchSegment(in_minutes=9 * 60, out_minutes=13 * 60 + 40),
                    PunchSegment(in_minutes=14 * 60 + 1, out_minutes=18 * 60),
                ],
            )
        }
        recorded = RecordedTimes(
            clock_in=9 * 60,
            lunch_out=13 * 60 + 40,
            lunch_in=14 * 60 + 10,
            clock_out=18 * 60,
        )
        block = EmployeeBlock(
            name="Francisco Quiroga Reyes",
            key="francisco quiroga reyes",
            dates_by_col={},
            times_by_date={day: recorded},
            status_row=20,
        )

        discrepancies, status_by_row = validate([block], punches)
        self.assertEqual(len(discrepancies), 0)
        self.assertEqual(status_by_row.get(20), "ok")

    def test_manual_lunch_without_punches_is_allowed(self) -> None:
        day = date(2025, 12, 24)
        punches = {
            ("dioselina serrano", day): DailyPunches(
                employee_name="Dioselina Serrano",
                employee_key="dioselina serrano",
                date=day,
                segments=[PunchSegment(in_minutes=7 * 60 + 10, out_minutes=14 * 60 + 58)],
            )
        }
        recorded = RecordedTimes(
            clock_in=7 * 60 + 10,
            lunch_out=12 * 60,
            lunch_in=12 * 60 + 30,
            clock_out=14 * 60 + 58,
        )
        block = EmployeeBlock(
            name="Dioselina Serrano",
            key="dioselina serrano",
            dates_by_col={},
            times_by_date={day: recorded},
            status_row=30,
        )

        discrepancies, status_by_row = validate([block], punches)
        self.assertEqual(len(discrepancies), 0)
        self.assertEqual(status_by_row.get(30), "ok")


if __name__ == "__main__":
    unittest.main()
