## Relevant Files

- `cli.py` - Entry point for running the validation from the command line.
- `src/models.py` - Data structures for punches, shifts, and validation results.
- `src/csv_reader.py` - CSV parsing, header skipping, and punch normalization.
- `src/xlsx_reader.py` - XLSX parsing and extraction of timesheet values.
- `src/validator.py` - Core comparison logic and rounding/lunch rules.
- `src/report.py` - Discrepancy report formatting and output.
- `src/xlsx_writer.py` - Writes per-employee status cells into a validated XLSX copy.
- `src/runner.py` - Shared validation runner used by both CLI and web UI.
- `app.py` - Local web UI for file upload and result downloads.
- `tests/test_csv_reader.py` - Unit tests for CSV parsing and grouping.
- `tests/test_xlsx_reader.py` - Unit tests for XLSX extraction and normalization.
- `tests/test_validator.py` - Unit tests for rounding rules and validation outcomes.
- `tests/test_xlsx_writer.py` - Unit tests for status-cell writing in XLSX output.
- `tests/test_integration.py` - End-to-end test using sample files.

### Notes

- Unit tests should typically be placed alongside the code files they are testing (e.g., `MyComponent.tsx` and `MyComponent.test.tsx` in the same directory).
- Use `npx jest [optional/path/to/test/file]` to run tests. Running without a path executes all tests found by the Jest configuration.

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

## Tasks

- [ ] 0.0 Create feature branch
  - [ ] 0.1 Create and checkout a new branch for this feature (e.g., `git checkout -b feature/payroll-time-validation`)
- [x] 1.0 Define data model and parsing rules (CSV header skip, XLSX layout mapping)
  - [x] 1.1 Inspect the example files in `data/` and document CSV header rows and column names
  - [x] 1.2 Document XLSX layout mapping (days in columns `B`–`G`, time rows in column `A`)
  - [x] 1.3 Define normalized time representation (e.g., minutes since midnight) and rounding rules
- [x] 2.0 Implement CSV ingestion and punch grouping/normalization
  - [x] 2.1 Implement CSV reader to skip report headers and extract name/ID/date/IN/OUT
  - [x] 2.2 Group punches by employee/date and derive the daily sequence (start, lunch out, lunch in, end)
  - [x] 2.3 Handle missing/extra punches and flag invalid sequences
  - [x] 2.4 Add unit tests for CSV parsing and grouping behavior
- [x] 3.0 Implement XLSX reading and timesheet extraction
  - [x] 3.1 Implement XLSX reader to locate each employee block and day columns
  - [x] 3.2 Extract values for `Clock In`, `Clock Out (Lunch)`, `Clock In (Work)`, `Clock Out`
  - [x] 3.3 Normalize Excel serial dates and fractional day times to the same representation as CSV
  - [x] 3.4 Add unit tests for XLSX extraction and normalization
- [x] 4.0 Implement validation logic and discrepancy reporting/CLI output
  - [x] 4.1 Apply rounding rules and 30-minute lunch enforcement to compute expected times
  - [x] 4.2 Handle the >6 hour shift with no lunch punches as a valid 30-minute lunch insertion
  - [x] 4.3 Compare expected vs. recorded values and classify discrepancy types
  - [x] 4.4 Generate a discrepancy report (CSV or XLSX) with employee/date/field/expected/actual
  - [x] 4.5 Write a validated XLSX copy with status cells set to `ok` or `needs attention`
  - [x] 4.6 Build CLI to run validation, write outputs, and print a summary
  - [x] 4.7 Add unit/integration tests for validation outcomes and status-cell writing
- [x] 5.0 Add user-friendly upload UI
  - [x] 5.1 Create a shared runner to reuse validation logic for CLI and UI
  - [x] 5.2 Implement a local web server with a file upload form (CSV + XLSX)
  - [x] 5.3 Save outputs to a run-specific folder and return download links
  - [x] 5.4 Provide basic instructions on the page for non-CLI users
