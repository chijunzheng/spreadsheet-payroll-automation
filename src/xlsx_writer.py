from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

NS_URI = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS = {"a": NS_URI}


def write_statuses(
    input_path: str | Path,
    output_path: str | Path,
    status_by_row: Dict[int, str],
) -> None:
    input_path = Path(input_path)
    output_path = Path(output_path)
    with zipfile.ZipFile(input_path) as zin:
        shared_strings, shared_root = _load_shared_strings(zin)
        status_indices = _ensure_status_strings(shared_strings, shared_root)

        sheet_root = ET.fromstring(zin.read("xl/worksheets/sheet1.xml"))
        _apply_statuses(sheet_root, status_by_row, status_indices)

        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "xl/sharedStrings.xml":
                    xml_bytes = _shared_strings_xml(shared_root)
                    zout.writestr(item, xml_bytes)
                elif item.filename == "xl/worksheets/sheet1.xml":
                    zout.writestr(item, ET.tostring(sheet_root, encoding="utf-8", xml_declaration=True))
                else:
                    zout.writestr(item, zin.read(item.filename))


def _load_shared_strings(
    zin: zipfile.ZipFile,
) -> tuple[List[str], ET.Element]:
    if "xl/sharedStrings.xml" in zin.namelist():
        root = ET.fromstring(zin.read("xl/sharedStrings.xml"))
        values: List[str] = []
        for si in root.findall("a:si", NS):
            texts = []
            for node in si.findall(".//a:t", NS):
                texts.append(node.text or "")
            values.append("".join(texts))
        return values, root

    root = ET.Element(_tag("sst"), {"xmlns": NS_URI})
    return [], root


def _ensure_status_strings(values: List[str], root: ET.Element) -> Dict[str, int]:
    indices = {}
    for text in ("ok", "needs attention"):
        if text in values:
            indices[text] = values.index(text)
            continue
        values.append(text)
        si = ET.SubElement(root, _tag("si"))
        t = ET.SubElement(si, _tag("t"))
        t.text = text
        indices[text] = len(values) - 1
    root.set("count", str(len(values)))
    root.set("uniqueCount", str(len(values)))
    return indices


def _apply_statuses(
    root: ET.Element, status_by_row: Dict[int, str], status_indices: Dict[str, int]
) -> None:
    sheet_data = root.find("a:sheetData", NS)
    if sheet_data is None:
        sheet_data = ET.SubElement(root, _tag("sheetData"))

    rows = sheet_data.findall("a:row", NS)
    row_map = {int(row.get("r", "0")): row for row in rows}

    for row_idx, status in status_by_row.items():
        row = row_map.get(row_idx)
        if row is None:
            row = ET.Element(_tag("row"), {"r": str(row_idx)})
            _insert_row(sheet_data, row)
            row_map[row_idx] = row

        cell_ref = f"H{row_idx}"
        cell = _find_cell(row, cell_ref)
        if cell is None:
            cell = ET.Element(_tag("c"), {"r": cell_ref, "t": "s"})
            row.append(cell)
        cell.set("t", "s")
        for inline in cell.findall("a:is", NS):
            cell.remove(inline)
        v = cell.find("a:v", NS)
        if v is None:
            v = ET.SubElement(cell, _tag("v"))
        v.text = str(status_indices[status])
        _sort_row_cells(row)


def _find_cell(row: ET.Element, cell_ref: str) -> ET.Element | None:
    for cell in row.findall("a:c", NS):
        if cell.get("r") == cell_ref:
            return cell
    return None


def _insert_row(sheet_data: ET.Element, row: ET.Element) -> None:
    rows = sheet_data.findall("a:row", NS)
    row_idx = int(row.get("r", "0"))
    insert_at = len(rows)
    for idx, existing in enumerate(rows):
        if int(existing.get("r", "0")) > row_idx:
            insert_at = idx
            break
    sheet_data.insert(insert_at, row)


def _sort_row_cells(row: ET.Element) -> None:
    cells = row.findall("a:c", NS)
    cells.sort(key=lambda c: _col_index(_col_letters(c.get("r", ""))))
    for cell in list(row):
        if cell.tag == _tag("c"):
            row.remove(cell)
    for cell in cells:
        row.append(cell)


def _col_letters(cell_ref: str) -> str:
    return "".join(ch for ch in cell_ref if ch.isalpha())


def _col_index(col: str) -> int:
    result = 0
    for char in col:
        result = result * 26 + (ord(char.upper()) - ord("A") + 1)
    return result


def _shared_strings_xml(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _tag(name: str) -> str:
    return f"{{{NS_URI}}}{name}"
