# Spreadsheet Payroll Automation

Validate payroll timesheets by comparing punch data (`.csv`) with a filled payroll spreadsheet (`.xlsx`). The app flags discrepancies, writes `ok` / `needs attention` status cells, and outputs a validation report plus a validated XLSX copy.

## Quick Start (Non-CLI)
1. Open the DMG in `dist/PayrollTimesheetValidator.dmg`.
2. Drag the app to Applications (optional).
3. Double-click **Payroll Timesheet Validator**.
4. Your browser opens to a local page. Upload the CSV + XLSX and download the outputs.

Outputs are saved to: `~/PayrollValidatorOutputs`

## Run Locally (Developer)
```bash
python3 app.py
```
Then open `http://127.0.0.1:8000` (the app will auto-pick 8000–8010 if busy).

## CLI Usage
```bash
python3 cli.py --csv path/to/Punch_Report.csv --xlsx path/to/Timesheet.xlsx --out-dir outputs
```

## Build the DMG
```bash
scripts/package_dmg.sh
```
The DMG is created at `dist/PayrollTimesheetValidator.dmg`.

## Troubleshooting
- **macOS Gatekeeper warning**: Right-click the app → Open (first launch only).
- **Python not found**: Install Python 3 from https://www.python.org/downloads/mac-osx/
- **Address already in use**: The app will auto-select a free port between 8000–8010.

## What the App Produces
- `validation_report.csv`: all discrepancies with expected vs actual values.
- `*-validated.xlsx`: original timesheet with status cells filled.
