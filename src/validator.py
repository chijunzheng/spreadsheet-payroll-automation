from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Tuple

from .models import DailyPunches, Discrepancy, EmployeeBlock, ExpectedTimes, RecordedTimes
from .utils import format_minutes, normalize_name

TOLERANCE_MINUTES = 1


def validate(
    blocks: List[EmployeeBlock],
    punches: Dict[Tuple[str, date], DailyPunches],
) -> Tuple[List[Discrepancy], Dict[int, str]]:
    discrepancies: List[Discrepancy] = []
    status_by_row: Dict[int, str] = {}
    matched_keys: set[Tuple[str, date]] = set()
    blocks_by_key: Dict[str, List[EmployeeBlock]] = {}
    block_has_issue: Dict[int, bool] = {}

    for block in blocks:
        blocks_by_key.setdefault(block.key, []).append(block)

    name_index, first_index = _build_name_index(punches)

    for block in blocks:
        has_issue = False
        resolved_key = _resolve_employee_key(block, name_index, first_index) or block.key
        for day, recorded in block.times_by_date.items():
            punch_key = (resolved_key, day)
            daily = punches.get(punch_key)
            if daily is None:
                if _has_any_time(recorded):
                    discrepancies.append(
                        Discrepancy(
                            employee_name=block.name,
                            date=day,
                            field="day",
                            expected="punch data",
                            actual="missing",
                            error_type="missing_punch_data",
                        )
                    )
                    has_issue = True
                continue

            matched_keys.add(punch_key)
            raw_times, expected, error = _compute_times(daily)
            if error:
                discrepancies.append(
                    Discrepancy(
                        employee_name=block.name,
                        date=day,
                        field="punch_sequence",
                        expected="1 or 2 punch pairs",
                        actual=str(len(daily.segments)),
                        error_type="invalid_punch_sequence",
                    )
                )
                has_issue = True
                continue

            lunch_required = expected.shift_minutes is not None and expected.shift_minutes > 360
            lunch_validated = False
            if raw_times.lunch_out is None and raw_times.lunch_in is None and lunch_required:
                lunch_validated = _validate_manual_lunch(expected, recorded)
                if not lunch_validated:
                    discrepancies.append(
                        Discrepancy(
                            employee_name=block.name,
                            date=day,
                            field="lunch_break",
                            expected="30 minutes",
                            actual=_format_lunch(recorded),
                            error_type="missing_or_invalid_lunch",
                        )
                    )
                    has_issue = True

            has_issue |= _compare_times(
                discrepancies,
                block.name,
                day,
                raw_times,
                expected,
                recorded,
                skip_lunch=lunch_validated,
            )

        if block.status_row is not None:
            status_by_row[block.status_row] = "needs attention" if has_issue else "ok"
            block_has_issue[block.status_row] = has_issue

    for punch_key, daily in punches.items():
        if punch_key in matched_keys:
            continue
        discrepancies.append(
            Discrepancy(
                employee_name=daily.employee_name,
                date=daily.date,
                field="day",
                expected="timesheet entry",
                actual="missing",
                error_type="missing_timesheet_row",
            )
        )
        for block in blocks_by_key.get(daily.employee_key, []):
            if block.status_row is not None:
                status_by_row[block.status_row] = "needs attention"

    return discrepancies, status_by_row


def _compute_times(
    daily: DailyPunches,
) -> tuple[RecordedTimes, ExpectedTimes, Optional[str]]:
    segments = daily.segments
    if len(segments) == 1:
        seg = segments[0]
        raw = RecordedTimes(
            clock_in=seg.in_minutes,
            lunch_out=None,
            lunch_in=None,
            clock_out=seg.out_minutes,
        )
        return (
            raw,
            ExpectedTimes(
                clock_in=_round_in(seg.in_minutes),
                lunch_out=None,
                lunch_in=None,
                clock_out=seg.out_minutes,
                shift_minutes=seg.out_minutes - seg.in_minutes,
            ),
            None,
        )
    if len(segments) == 2:
        first, second = segments
        raw = RecordedTimes(
            clock_in=first.in_minutes,
            lunch_out=first.out_minutes,
            lunch_in=second.in_minutes,
            clock_out=second.out_minutes,
        )
        lunch_out = _round_in(first.out_minutes)
        lunch_in = max(second.in_minutes, lunch_out + 30)
        return (
            raw,
            ExpectedTimes(
                clock_in=_round_in(first.in_minutes),
                lunch_out=lunch_out,
                lunch_in=lunch_in,
                clock_out=second.out_minutes,
                shift_minutes=(first.out_minutes - first.in_minutes)
                + (second.out_minutes - second.in_minutes),
            ),
            None,
        )
    return (
        RecordedTimes(
            clock_in=None,
            lunch_out=None,
            lunch_in=None,
            clock_out=None,
        ),
        ExpectedTimes(
            clock_in=None,
            lunch_out=None,
            lunch_in=None,
            clock_out=None,
            shift_minutes=None,
        ),
        "invalid",
    )


def _round_in(minutes: int) -> int:
    boundary = _nearest_boundary(minutes)
    return boundary if minutes < boundary else minutes


def _round_out(minutes: int) -> int:
    boundary = _nearest_boundary(minutes)
    return boundary if minutes > boundary else minutes


def _nearest_boundary(minutes: int) -> int:
    # Treat the nearest 30-minute boundary as the scheduled time (ties round up).
    lower = minutes - (minutes % 30)
    upper = lower + 30
    if minutes - lower < upper - minutes:
        return lower
    if minutes - lower > upper - minutes:
        return upper
    return upper


def _compare_times(
    discrepancies: List[Discrepancy],
    employee_name: str,
    day: date,
    raw_times: RecordedTimes,
    expected: ExpectedTimes,
    recorded: RecordedTimes,
    skip_lunch: bool,
) -> bool:
    has_issue = False
    has_issue |= _compare_field(
        discrepancies,
        employee_name,
        day,
        "clock_in",
        _allowed_values(raw_times.clock_in, expected.clock_in),
        recorded.clock_in,
    )
    if not skip_lunch:
        has_issue |= _compare_field(
            discrepancies,
            employee_name,
            day,
            "clock_out_lunch",
            _allowed_values(raw_times.lunch_out, expected.lunch_out),
            recorded.lunch_out,
        )
        has_issue |= _compare_field(
            discrepancies,
            employee_name,
            day,
            "clock_in_work",
            _allowed_lunch_in(raw_times, expected),
            recorded.lunch_in,
        )
    has_issue |= _compare_field(
        discrepancies,
        employee_name,
        day,
        "clock_out",
        _allowed_values(raw_times.clock_out, expected.clock_out),
        recorded.clock_out,
    )
    return has_issue


def _compare_field(
    discrepancies: List[Discrepancy],
    employee_name: str,
    day: date,
    field: str,
    expected_values: list[Optional[int]],
    actual: int | None,
) -> bool:
    normalized = _normalize_expected(expected_values)
    if not normalized and actual is None:
        return False
    if not normalized and actual is not None:
        discrepancies.append(
            Discrepancy(
                employee_name=employee_name,
                date=day,
                field=field,
                expected=None,
                actual=format_minutes(actual),
                error_type="unexpected_entry",
            )
        )
        return True
    if normalized and actual is None:
        discrepancies.append(
            Discrepancy(
                employee_name=employee_name,
                date=day,
                field=field,
                expected=_format_expected(normalized),
                actual=None,
                error_type="missing_entry",
            )
        )
        return True
    if actual is not None and normalized:
        for expected in normalized:
            if abs(expected - actual) <= TOLERANCE_MINUTES:
                return False
        discrepancies.append(
            Discrepancy(
                employee_name=employee_name,
                date=day,
                field=field,
                expected=_format_expected(normalized),
                actual=format_minutes(actual),
                error_type="mismatch",
            )
        )
        return True
    return False


def _has_any_time(recorded: RecordedTimes) -> bool:
    return any(
        value is not None
        for value in (recorded.clock_in, recorded.lunch_out, recorded.lunch_in, recorded.clock_out)
    )


def _validate_manual_lunch(expected: ExpectedTimes, recorded: RecordedTimes) -> bool:
    if recorded.lunch_out is None or recorded.lunch_in is None:
        return False
    if recorded.lunch_in - recorded.lunch_out != 30:
        return False
    if expected.clock_in is not None and recorded.lunch_out < expected.clock_in:
        return False
    if expected.clock_out is not None and recorded.lunch_in > expected.clock_out:
        return False
    return True


def _format_lunch(recorded: RecordedTimes) -> str:
    if recorded.lunch_out is None or recorded.lunch_in is None:
        return "missing"
    return f"{format_minutes(recorded.lunch_out)}-{format_minutes(recorded.lunch_in)}"


def _allowed_values(*values: Optional[int]) -> list[Optional[int]]:
    return list(values)


def _normalize_expected(values: list[Optional[int]]) -> list[int]:
    unique: list[int] = []
    for value in values:
        if value is None:
            continue
        if value not in unique:
            unique.append(value)
    return unique


def _format_expected(values: list[int]) -> str:
    formatted = [format_minutes(value) for value in values]
    return " | ".join(val for val in formatted if val)


def _enforced_lunch_in(raw_times: RecordedTimes) -> Optional[int]:
    if raw_times.lunch_out is None or raw_times.lunch_in is None:
        return None
    return max(raw_times.lunch_in, raw_times.lunch_out + 30)


def _allowed_lunch_in(raw_times: RecordedTimes, expected: ExpectedTimes) -> list[Optional[int]]:
    values: list[Optional[int]] = []
    if raw_times.lunch_out is None or raw_times.lunch_in is None:
        values.extend([raw_times.lunch_in, expected.lunch_in, _enforced_lunch_in(raw_times)])
        return values

    min_return = raw_times.lunch_out + 30
    if raw_times.lunch_in >= min_return:
        values.append(raw_times.lunch_in)
    values.append(expected.lunch_in)
    values.append(max(raw_times.lunch_in, min_return))
    return values


def _build_name_index(
    punches: Dict[Tuple[str, date], DailyPunches]
) -> Tuple[Dict[str, set[str]], Dict[str, set[str]]]:
    index: Dict[str, set[str]] = {}
    first_index: Dict[str, set[str]] = {}
    for (employee_key, _day), daily in punches.items():
        tokens = _name_tokens(daily.employee_name)
        if tokens:
            first_index.setdefault(tokens[0], set()).add(employee_key)
        for variant in _name_variants(daily.employee_name):
            index.setdefault(variant, set()).add(employee_key)
    return index, first_index


def _resolve_employee_key(
    block: EmployeeBlock, name_index: Dict[str, set[str]], first_index: Dict[str, set[str]]
) -> Optional[str]:
    tokens = _name_tokens(block.name)
    if not tokens:
        return None
    variants: list[str] = [" ".join(tokens)]
    if len(tokens) >= 2:
        variants.append(" ".join(tokens[:2]))
        variants.append(" ".join([tokens[0], tokens[-1]]))
    variants.append(tokens[0])
    seen: set[str] = set()
    for variant in variants:
        if variant in seen:
            continue
        seen.add(variant)
        candidates = name_index.get(variant, set())
        if block.key in candidates:
            return block.key
        if len(candidates) == 1:
            return next(iter(candidates))

    if len(tokens) >= 2:
        first = tokens[0]
        last = tokens[-1]
        fuzzy: set[str] = set()
        for employee_key in first_index.get(first, set()):
            key_tokens = employee_key.split()
            if not key_tokens:
                continue
            if _within_edit_distance(last, key_tokens[-1]):
                fuzzy.add(employee_key)
        if len(fuzzy) == 1:
            return next(iter(fuzzy))
    return None


def _name_variants(name: str) -> set[str]:
    tokens = _name_tokens(name)
    if not tokens:
        return set()
    variants = {" ".join(tokens), tokens[0]}
    if len(tokens) >= 2:
        variants.add(" ".join(tokens[:2]))
        variants.add(" ".join([tokens[0], tokens[-1]]))
    return variants


def _name_tokens(name: str) -> list[str]:
    return [token for token in normalize_name(name).split() if len(token) > 1]


def _within_edit_distance(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        mismatches = sum(1 for x, y in zip(a, b) if x != y)
        return mismatches <= 1
    # ensure a is shorter
    if len(a) > len(b):
        a, b = b, a
    i = j = 0
    edits = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1
            j += 1
            continue
        edits += 1
        if edits > 1:
            return False
        j += 1
    return True
