from __future__ import annotations

import html
import mimetypes
import os
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import unquote, urlparse

from src.runner import run_validation

HOST = "127.0.0.1"
PORT_START = 8000
PORT_END = 8010
OUTPUTS_DIR = Path.home() / "PayrollValidatorOutputs"


class UploadHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(self._index_page())
            return
        if parsed.path.startswith("/outputs/"):
            self._serve_file(parsed.path[len("/outputs/") :])
            return
        self._send_html(self._error_page("Not found."), status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/upload":
            self._send_html(self._error_page("Not found."), status=404)
            return

        try:
            files = self._parse_multipart()
        except ValueError as exc:
            self._send_html(self._error_page(str(exc)), status=400)
            return

        csv_file = files.get("csv")
        xlsx_file = files.get("xlsx")
        if csv_file is None or xlsx_file is None:
            self._send_html(
                self._error_page("Please upload both a CSV and XLSX file."), status=400
            )
            return

        run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        run_dir = OUTPUTS_DIR / f"run-{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)

        csv_path = run_dir / _safe_filename(csv_file[0], "punches.csv")
        xlsx_path = run_dir / _safe_filename(xlsx_file[0], "timesheet.xlsx")
        csv_path.write_bytes(csv_file[1])
        xlsx_path.write_bytes(xlsx_file[1])

        try:
            report_path, validated_path, count, ok_count, needs_attention = run_validation(
                csv_path, xlsx_path, run_dir
            )
        except Exception as exc:
            self._send_html(self._error_page(f"Validation failed: {exc}"), status=500)
            return

        report_link = f"/outputs/{report_path.relative_to(OUTPUTS_DIR)}"
        validated_link = f"/outputs/{validated_path.relative_to(OUTPUTS_DIR)}"
        self._send_html(
            self._result_page(
                report_link,
                validated_link,
                count,
                ok_count,
                needs_attention,
            )
        )

    def _parse_multipart(self) -> Dict[str, Tuple[str, bytes]]:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            raise ValueError("Invalid form submission.")
        if "boundary=" not in content_type:
            raise ValueError("Missing multipart boundary.")

        boundary = content_type.split("boundary=")[-1].strip()
        if boundary.startswith("\"") and boundary.endswith("\""):
            boundary = boundary[1:-1]
        boundary_bytes = ("--" + boundary).encode()

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        parts = body.split(boundary_bytes)
        files: Dict[str, Tuple[str, bytes]] = {}

        for part in parts:
            if not part or part in (b"--\r\n", b"--"):
                continue
            if part.startswith(b"\r\n"):
                part = part[2:]
            if part.endswith(b"--\r\n"):
                part = part[:-4]
            elif part.endswith(b"\r\n"):
                part = part[:-2]
            header_bytes, _, data = part.partition(b"\r\n\r\n")
            if not data:
                continue
            headers = header_bytes.decode("utf-8", errors="replace").split("\r\n")
            disposition = next(
                (line for line in headers if line.lower().startswith("content-disposition")),
                "",
            )
            name = _extract_field(disposition, "name")
            filename = _extract_field(disposition, "filename")
            if name and filename:
                files[name] = (filename, data)
        return files

    def _serve_file(self, relative_path: str) -> None:
        relative_path = unquote(relative_path)
        if ".." in Path(relative_path).parts:
            self._send_html(self._error_page("Invalid path."), status=400)
            return
        full_path = OUTPUTS_DIR / relative_path
        full_path = full_path.resolve()
        if OUTPUTS_DIR.resolve() not in full_path.parents:
            self._send_html(self._error_page("Invalid path."), status=400)
            return
        if not full_path.exists():
            self._send_html(self._error_page("File not found."), status=404)
            return

        mime_type, _ = mimetypes.guess_type(full_path.as_posix())
        mime_type = mime_type or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header(
            "Content-Disposition", f"attachment; filename={full_path.name}"
        )
        self.end_headers()
        with full_path.open("rb") as handle:
            self.wfile.write(handle.read())

    def _send_html(self, body: str, status: int = 200) -> None:
        content = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _index_page(self) -> str:
        return f"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Payroll Timesheet Validator</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 40px; color: #1a1a1a; }}
      h1 {{ margin-bottom: 8px; }}
      .card {{ max-width: 640px; padding: 20px; border: 1px solid #ddd; border-radius: 12px; }}
      label {{ display: block; margin-top: 12px; font-weight: 600; }}
      input[type=file] {{ display: block; margin-top: 6px; }}
      button {{ margin-top: 16px; padding: 10px 16px; background: #0c66e4; color: #fff; border: none; border-radius: 6px; cursor: pointer; }}
      button:hover {{ background: #0a55c5; }}
      .note {{ font-size: 0.9em; color: #555; margin-top: 12px; }}
    </style>
  </head>
  <body>
    <h1>Payroll Timesheet Validator</h1>
    <p>Upload your punch CSV and filled timesheet XLSX to generate a validation report.</p>
    <div class="card">
      <form action="/upload" method="post" enctype="multipart/form-data">
        <label> Punch report (.csv)
          <input type="file" name="csv" accept=".csv" required />
        </label>
        <label> Timesheet (.xlsx)
          <input type="file" name="xlsx" accept=".xlsx" required />
        </label>
        <button type="submit">Validate</button>
      </form>
      <div class="note">This tool runs locally on your computer; files never leave your machine.</div>
      <div class="note">Output files are stored in: {html.escape(str(OUTPUTS_DIR))}</div>
    </div>
  </body>
</html>
"""

    def _result_page(
        self,
        report_link: str,
        validated_link: str,
        count: int,
        ok_count: int,
        needs_attention: int,
    ) -> str:
        return f"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Validation Results</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 40px; color: #1a1a1a; }}
      a {{ color: #0c66e4; }}
      .card {{ max-width: 640px; padding: 20px; border: 1px solid #ddd; border-radius: 12px; }}
      ul {{ padding-left: 18px; }}
    </style>
  </head>
  <body>
    <h1>Validation Results</h1>
    <div class="card">
      <p><strong>Discrepancies:</strong> {count}</p>
      <p><strong>Employees OK:</strong> {ok_count}</p>
      <p><strong>Needs Attention:</strong> {needs_attention}</p>
      <ul>
        <li><a href="{html.escape(report_link)}">Download validation report</a></li>
        <li><a href="{html.escape(validated_link)}">Download validated timesheet</a></li>
      </ul>
      <p><a href="/">Run another validation</a></p>
    </div>
  </body>
</html>
"""

    def _error_page(self, message: str) -> str:
        escaped = html.escape(message)
        return f"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Validation Error</title>
  </head>
  <body>
    <h1>Something went wrong</h1>
    <p>{escaped}</p>
    <p><a href="/">Back</a></p>
  </body>
</html>
"""


def _safe_filename(filename: str, fallback: str) -> str:
    cleaned = Path(filename).name
    return cleaned or fallback


def _extract_field(header: str, key: str) -> Optional[str]:
    key_token = f'{key}="'
    if key_token not in header:
        return None
    start = header.index(key_token) + len(key_token)
    end = header.find('"', start)
    if end == -1:
        return None
    return header[start:end]


def main() -> None:
    server, port = _start_server()
    url = f"http://{HOST}:{port}"
    try:
        import webbrowser

        webbrowser.open(url)
    except Exception:
        pass
    print(f"Open {url} in your browser.")
    server.serve_forever()


def _start_server() -> Tuple[HTTPServer, int]:
    last_error: Optional[OSError] = None
    for port in range(PORT_START, PORT_END + 1):
        try:
            return HTTPServer((HOST, port), UploadHandler), port
        except OSError as exc:
            last_error = exc
            if exc.errno in (48, 98):  # address in use
                continue
            raise
    raise OSError("No available port found.") from last_error


if __name__ == "__main__":
    main()
