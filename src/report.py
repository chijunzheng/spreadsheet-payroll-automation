from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .models import Discrepancy


def write_report(path: str | Path, discrepancies: Iterable[Discrepancy]) -> None:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["employee", "date", "field", "expected", "actual", "error_type"])
        for item in discrepancies:
            writer.writerow(
                [
                    item.employee_name,
                    item.date.isoformat() if item.date else "",
                    item.field,
                    item.expected or "",
                    item.actual or "",
                    item.error_type,
                ]
            )
