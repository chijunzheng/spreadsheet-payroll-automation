from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .models import EmployeeBlock, RecordedTimes
from .utils import excel_fraction_to_minutes, excel_serial_to_date, normalize_name

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
WEEKDAY_COLUMNS = ["B", "C", "D", "E", "F", "G"]
TIME_LABELS = {
    "Clock In": "clock_in",
    "Clock Out (Lunch)": "lunch_out",
    "Clock In (Work)": "lunch_in",
    "Clock Out": "clock_out",
}


def read_timesheet(
    xlsx_path: str | Path,
    target_dates: Optional[Set[date]] = None,
    sheet_hint: Optional[str] = None,
) -> List[EmployeeBlock]:
    path = Path(xlsx_path)
    with zipfile.ZipFile(path) as workbook:
        shared_strings = _load_shared_strings(workbook)
        sheet_paths = _load_sheet_paths(workbook)
        if sheet_hint:
            sheet_paths = _filter_sheet_paths(sheet_paths, sheet_hint)
            if not sheet_paths:
                raise ValueError(f"No worksheet matches hint {sheet_hint}.")
        blocks: List[EmployeeBlock] = []
        for _sheet_name, sheet_path in sheet_paths:
            if sheet_path not in workbook.namelist():
                continue
            sheet_xml = workbook.read(sheet_path)
            root = ET.fromstring(sheet_xml)
            blocks.extend(_parse_sheet(root, shared_strings, target_dates))

    return blocks


def _load_shared_strings(workbook: zipfile.ZipFile) -> List[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []
    root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    values: List[str] = []
    for si in root.findall("a:si", NS):
        texts = []
        for node in si.findall(".//a:t", NS):
            texts.append(node.text or "")
        values.append("".join(texts))
    return values


def _load_sheet_paths(workbook: zipfile.ZipFile) -> List[Tuple[str, str]]:
    workbook_root = ET.fromstring(workbook.read("xl/workbook.xml"))
    rels_root = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    sheet_map: Dict[str, str] = {}
    rels_ns = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
    for rel in rels_root.findall("r:Relationship", rels_ns):
        if rel.get("Type", "").endswith("/worksheet"):
            sheet_map[rel.get("Id")] = f"xl/{rel.get('Target')}"

    sheets: List[Tuple[str, str]] = []
    for sheet in workbook_root.findall("a:sheets/a:sheet", NS):
        name = sheet.get("name") or ""
        rel_id = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        if not rel_id:
            continue
        target = sheet_map.get(rel_id)
        if target:
            sheets.append((name, target))
    return sheets


def _filter_sheet_paths(
    sheet_paths: List[Tuple[str, str]], sheet_hint: str
) -> List[Tuple[str, str]]:
    hint = sheet_hint.strip()
    matches: List[Tuple[str, str]] = []
    for name, path in sheet_paths:
        if name == hint:
            matches.append((name, path))
            continue
        digits = "".join(ch for ch in name if ch.isdigit())
        if hint in digits:
            matches.append((name, path))
    return matches


def _parse_sheet(
    root: ET.Element,
    shared_strings: List[str],
    target_dates: Optional[Set[date]],
) -> List[EmployeeBlock]:
    cells = _load_cells(root, shared_strings)
    rows = sorted({row for (row, _col) in cells.keys()})
    weekday_rows = [r for r in rows if _cell_str(cells.get((r, "B"))) == "monday"]
    blocks: List[EmployeeBlock] = []

    for week_row in weekday_rows:
        name = _find_employee_name(cells, week_row)
        if not name:
            continue
        date_row = week_row + 1
        dates_by_col: Dict[str, date] = {}
        for col in WEEKDAY_COLUMNS:
            val = cells.get((date_row, col))
            if isinstance(val, (float, int)):
                day = excel_serial_to_date(float(val))
                if target_dates is None or day in target_dates:
                    dates_by_col[col] = day
        if not dates_by_col:
            continue

        label_rows = _find_label_rows(cells, week_row + 2, week_row + 12)
        times_by_date: Dict[date, RecordedTimes] = {}
        for col, day in dates_by_col.items():
            times_by_date[day] = RecordedTimes(
                clock_in=_value_to_minutes(cells.get((label_rows.get("Clock In"), col))),
                lunch_out=_value_to_minutes(
                    cells.get((label_rows.get("Clock Out (Lunch)"), col))
                ),
                lunch_in=_value_to_minutes(
                    cells.get((label_rows.get("Clock In (Work)"), col))
                ),
                clock_out=_value_to_minutes(cells.get((label_rows.get("Clock Out"), col))),
            )

        status_row = _find_status_row(cells, week_row + 2, week_row + 25)
        blocks.append(
            EmployeeBlock(
                name=name,
                key=normalize_name(name),
                dates_by_col=dates_by_col,
                times_by_date=times_by_date,
                status_row=status_row,
            )
        )
    return blocks


def _load_cells(
    root: ET.Element, shared_strings: List[str]
) -> Dict[tuple[int, str], object]:
    cells: Dict[tuple[int, str], object] = {}
    for row in root.findall(".//a:row", NS):
        row_idx = int(row.get("r", "0"))
        for cell in row.findall("a:c", NS):
            ref = cell.get("r")
            if not ref:
                continue
            col = "".join(ch for ch in ref if ch.isalpha())
            val = _cell_value(cell, shared_strings)
            if val is None or val == "":
                continue
            cells[(row_idx, col)] = val
    return cells


def _cell_value(cell: ET.Element, shared_strings: List[str]) -> Optional[object]:
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        text = cell.find(".//a:t", NS)
        return text.text if text is not None else ""
    v = cell.find("a:v", NS)
    if v is None:
        return None
    raw = v.text or ""
    if cell_type == "s":
        try:
            return shared_strings[int(raw)]
        except (ValueError, IndexError):
            return raw
    try:
        return float(raw)
    except ValueError:
        return raw


def _cell_str(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    return str(value).strip().lower()


def _find_employee_name(cells: Dict[tuple[int, str], object], week_row: int) -> str | None:
    for row in range(week_row - 1, week_row - 10, -1):
        value = cells.get((row, "A"))
        if isinstance(value, str):
            stripped = value.strip()
            if stripped and stripped.lower() != "name":
                return stripped
    return None


def _find_label_rows(
    cells: Dict[tuple[int, str], object], start: int, end: int
) -> Dict[str, int]:
    label_rows: Dict[str, int] = {}
    for row in range(start, end + 1):
        label = cells.get((row, "A"))
        if isinstance(label, str):
            cleaned = label.strip()
            if cleaned in TIME_LABELS:
                label_rows[cleaned] = row
    return label_rows


def _find_status_row(
    cells: Dict[tuple[int, str], object], start: int, end: int
) -> Optional[int]:
    for row in range(start, end + 1):
        value = cells.get((row, "F"))
        if isinstance(value, str) and value.strip().lower() == "total":
            return row
    return None


def _value_to_minutes(value: Optional[object]) -> Optional[int]:
    if isinstance(value, (float, int)):
        if abs(float(value)) < 1e-9:
            return None
        return excel_fraction_to_minutes(float(value))
    return None
