import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from src.xlsx_writer import write_statuses

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


class XlsxWriterTests(unittest.TestCase):
    def test_writes_status_cell(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path("data/Chef & Amazing time sheet - checking purposes.xlsx")
            out = Path(tmpdir) / "validated.xlsx"
            write_statuses(src, out, {15: "needs attention"})

            with zipfile.ZipFile(out) as zf:
                shared = []
                shared_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                for si in shared_root.findall("a:si", NS):
                    texts = []
                    for node in si.findall(".//a:t", NS):
                        texts.append(node.text or "")
                    shared.append("".join(texts))

                sheet_root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
                cell = sheet_root.find(".//a:c[@r='H15']/a:v", NS)
                self.assertIsNotNone(cell)
                value = shared[int(cell.text)]
                self.assertEqual(value, "needs attention")


if __name__ == "__main__":
    unittest.main()
