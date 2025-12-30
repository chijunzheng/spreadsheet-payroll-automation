from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional


@dataclass(frozen=True)
class PunchSegment:
    in_minutes: int
    out_minutes: int


@dataclass
class DailyPunches:
    employee_name: str
    employee_key: str
    date: date
    segments: List[PunchSegment]


@dataclass
class RecordedTimes:
    clock_in: Optional[int]
    lunch_out: Optional[int]
    lunch_in: Optional[int]
    clock_out: Optional[int]


@dataclass
class ExpectedTimes:
    clock_in: Optional[int]
    lunch_out: Optional[int]
    lunch_in: Optional[int]
    clock_out: Optional[int]
    shift_minutes: Optional[int]


@dataclass
class Discrepancy:
    employee_name: str
    date: Optional[date]
    field: str
    expected: Optional[str]
    actual: Optional[str]
    error_type: str


@dataclass
class EmployeeBlock:
    name: str
    key: str
    dates_by_col: Dict[str, date]
    times_by_date: Dict[date, RecordedTimes]
    status_row: Optional[int]
